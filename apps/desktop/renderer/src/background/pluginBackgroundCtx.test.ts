import assert from "node:assert/strict";
import { test } from "node:test";
import type {
  BridgeEvent,
  DesktopApi,
  DesktopSurfacesApi,
  SurfaceSettledPayload,
} from "../../../src/bridge/shared";
import { unavailableLocalAssetUrl } from "../../../src/assets/localAssetContract";
import type { DesktopInvoke } from "../shared/bridgeInvoke";
import { BackgroundEffectScope } from "./backgroundEffectScope";
import { createBackgroundCtx, type SurfaceSettledSource } from "./pluginBackgroundCtx";

function fakeSurfaces(): DesktopSurfacesApi & { calls: unknown[][] } {
  const calls: unknown[][] = [];
  return {
    calls,
    create: (...args) => { calls.push(["create", ...args]); return Promise.resolve({ x: 0, y: 0, displayId: "d1" }); },
    destroy: (...args) => { calls.push(["destroy", ...args]); return Promise.resolve(); },
    show: (...args) => { calls.push(["show", ...args]); },
    hide: (...args) => { calls.push(["hide", ...args]); },
    workArea: (...args) => { calls.push(["workArea", ...args]); return Promise.resolve({ x: 0, y: 0, width: 0, height: 0 }); },
    setPosition: (...args) => { calls.push(["setPosition", ...args]); },
    moveTo: (...args) => { calls.push(["moveTo", ...args]); },
    post: (...args) => { calls.push(["post", ...args]); },
    setState: (...args) => { calls.push(["setState", ...args]); },
  };
}

/** A fake bridge event source that lets a test push events and inspect subscriber count. */
function fakeEventSource() {
  const listeners = new Set<(event: BridgeEvent) => void>();
  return {
    listenerCount: () => listeners.size,
    onEvent: (listener: (event: BridgeEvent) => void) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    emit: (event: BridgeEvent) => { for (const listener of listeners) listener(event); },
  };
}

/** A fake settle source with the same shape as the preload's broadcast. */
function fakeSettledSource() {
  const listeners = new Set<(settled: SurfaceSettledPayload) => void>();
  return {
    listenerCount: () => listeners.size,
    onSurfaceSettled: ((listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    }) as SurfaceSettledSource,
    emit: (settled: SurfaceSettledPayload) => { for (const listener of listeners) listener(settled); },
  };
}

function fakePluginData(): DesktopApi["pluginData"] & { calls: unknown[][]; stored: Map<string, unknown> } {
  const calls: unknown[][] = [];
  const stored = new Map<string, unknown>();
  return {
    calls,
    stored,
    read: (pluginId) => { calls.push(["read", pluginId]); return Promise.resolve(stored.get(pluginId) ?? null); },
    write: (pluginId, value) => { calls.push(["write", pluginId, value]); stored.set(pluginId, value); return Promise.resolve(); },
  };
}

const failingInvoke = (() => Promise.reject(new Error("unused"))) as DesktopInvoke;

function makeCtx(overrides: Partial<Parameters<typeof createBackgroundCtx>[0]> = {}) {
  const scope = overrides.scope ?? new BackgroundEffectScope();
  return createBackgroundCtx({
    pluginId: "demo",
    surfaces: fakeSurfaces(),
    invoke: failingInvoke,
    onEvent: () => () => {},
    onSurfaceSettled: () => () => {},
    pluginData: fakePluginData(),
    localAssetUrl: () => unavailableLocalAssetUrl,
    ...overrides,
    scope,
  });
}

test("ctx.surfaces binds the plugin id ahead of every call", async () => {
  const surfaces = fakeSurfaces();
  const ctx = makeCtx({ surfaces });

  await ctx.surfaces.create("main", { body: { width: 1, height: 1 } }, { x: 0, y: 0 });
  ctx.surfaces.show("main");
  ctx.surfaces.setPosition("main", { x: 1, y: 2 });

  assert.deepEqual(surfaces.calls, [
    ["create", "demo", "main", { body: { width: 1, height: 1 } }, { x: 0, y: 0 }],
    ["show", "demo", "main"],
    ["setPosition", "demo", "main", { x: 1, y: 2 }],
  ]);
});

test("ctx.rpc scopes calls to plugin.<id>.* and returns the unwrapped payload", async () => {
  const requests: unknown[] = [];
  const invoke: DesktopInvoke = (request) => {
    requests.push(request);
    return Promise.resolve({ id: "x", type: "response", method: request.method, payload: { ok: true }, error: null });
  };
  const ctx = makeCtx({ invoke });

  const result = await ctx.rpc.call<{ ok: boolean }>("doThing", { a: 1 });

  assert.deepEqual(requests, [{ method: "plugin.demo.doThing", payload: { a: 1 } }]);
  assert.deepEqual(result, { ok: true });
});

test("ctx.events.on filters by method and ignores everything else", () => {
  const source = fakeEventSource();
  const ctx = makeCtx({ onEvent: source.onEvent });

  const received: unknown[] = [];
  ctx.events.on("demo.thing.happened", (payload) => received.push(payload));

  source.emit({ id: "1", type: "event", method: "demo.thing.happened", payload: { n: 1 } });
  source.emit({ id: "2", type: "event", method: "unrelated.event", payload: { n: 2 } });

  assert.deepEqual(received, [{ n: 1 }]);
});

test("ctx.events.on registers its unsubscribe as an event-phase effect, released on disposeAll", async () => {
  const source = fakeEventSource();
  const scope = new BackgroundEffectScope();
  const ctx = makeCtx({ onEvent: source.onEvent, scope });

  ctx.events.on("demo.thing.happened", () => {});
  assert.equal(source.listenerCount(), 1);

  await scope.disposeAll();
  assert.equal(source.listenerCount(), 0, "subscription must be released on teardown");
});

test("ctx.effect's terminate always runs after ctx.events.on's unsubscribe, in #227's exact registration order", async () => {
  const order: string[] = [];
  // Wraps the fake source so unsubscribing is independently observable in
  // `order`, not just inferable from listener count.
  const source = fakeEventSource();
  const observedOnEvent = (listener: Parameters<typeof source.onEvent>[0]) => {
    const unsubscribe = source.onEvent(listener);
    return () => { order.push("unsubscribe"); unsubscribe(); };
  };
  const scope = new BackgroundEffectScope();
  const ctx = makeCtx({ onEvent: observedOnEvent, scope });

  // Natural, "readable" authoring order that broke the backend twice (#227):
  // subscribe first, register the terminate-style effect after.
  ctx.events.on("demo.thing.happened", () => {});
  ctx.effect("controller_terminate", () => { order.push("terminate"); });

  await scope.disposeAll();
  assert.deepEqual(order, ["unsubscribe", "terminate"]);
  assert.equal(source.listenerCount(), 0);
});

const settled = (overrides: Partial<SurfaceSettledPayload> = {}): SurfaceSettledPayload => ({
  pluginId: "demo",
  surfaceId: "main",
  placement: {
    anchor: { x: 3, y: 4 },
    bodyOffset: { x: 0, y: 0 },
    workArea: { x: 0, y: 0, width: 100, height: 100 },
  },
  reason: "drag",
  displayId: "d1",
  ...overrides,
});

test("ctx.surfaces.onSettled sees its own surface and nothing else", () => {
  const source = fakeSettledSource();
  const ctx = makeCtx({ onSurfaceSettled: source.onSurfaceSettled });

  const received: unknown[] = [];
  ctx.surfaces.onSettled("main", (value) => received.push(value));

  source.emit(settled());
  // Another surface of the same plugin, and another plugin's surface with the
  // same surface id: neither is this subscription's business.
  source.emit(settled({ surfaceId: "other" }));
  source.emit(settled({ pluginId: "rival" }));

  assert.deepEqual(received, [{
    placement: settled().placement,
    reason: "drag",
    displayId: "d1",
  }]);
});

test("ctx.surfaces.onSettled releases its subscription in the event phase, before ctx.effect", async () => {
  const order: string[] = [];
  const source = fakeSettledSource();
  const observed: SurfaceSettledSource = (listener) => {
    const unsubscribe = source.onSurfaceSettled(listener);
    return () => { order.push("unsubscribe"); unsubscribe(); };
  };
  const scope = new BackgroundEffectScope();
  const ctx = makeCtx({ onSurfaceSettled: observed, scope });

  ctx.surfaces.onSettled("main", () => {});
  ctx.effect("controller_terminate", () => { order.push("terminate"); });
  assert.equal(source.listenerCount(), 1);

  await scope.disposeAll();
  assert.deepEqual(order, ["unsubscribe", "terminate"]);
  assert.equal(source.listenerCount(), 0);
});

test("ctx.store binds the plugin id, so a plugin cannot read another's data by mistake", async () => {
  const pluginData = fakePluginData();
  const ctx = makeCtx({ pluginData });

  assert.equal(await ctx.store.read(), null);
  await ctx.store.write({ visible: true });

  assert.deepEqual(pluginData.calls, [
    ["read", "demo"],
    ["write", "demo", { visible: true }],
  ]);
  assert.deepEqual(pluginData.stored.get("demo"), { visible: true });
});

test("ctx.assets.url answers null for a path the host never granted", () => {
  const granted = new Map([["C:/roles/mira/sheet.webp", "shiori-asset://local/token-1"]]);
  const ctx = makeCtx({
    localAssetUrl: (path) => granted.get(path) ?? unavailableLocalAssetUrl,
  });

  assert.equal(ctx.assets.url("C:/roles/mira/sheet.webp"), "shiori-asset://local/token-1");
  // The placeholder URL means "no grant", and a plugin deciding whether it can
  // show a package must not mistake it for one.
  assert.equal(ctx.assets.url("C:/roles/mira/missing.webp"), null);
  assert.equal(ctx.assets.url(""), null);
});
