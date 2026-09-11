import assert from "node:assert/strict";
import { test } from "node:test";
import type { BridgeEvent, DesktopSurfacesApi } from "../../../src/bridge/shared";
import type { DesktopInvoke } from "../shared/bridgeInvoke";
import { BackgroundEffectScope } from "./backgroundEffectScope";
import { createBackgroundCtx } from "./pluginBackgroundCtx";

function fakeSurfaces(): DesktopSurfacesApi & { calls: unknown[][] } {
  const calls: unknown[][] = [];
  return {
    calls,
    create: (...args) => { calls.push(["create", ...args]); return Promise.resolve({ x: 0, y: 0 }); },
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

test("ctx.surfaces binds the plugin id ahead of every call", async () => {
  const surfaces = fakeSurfaces();
  const scope = new BackgroundEffectScope();
  const ctx = createBackgroundCtx({
    pluginId: "demo",
    surfaces,
    invoke: (() => Promise.resolve({ id: "x", type: "response", method: "x", payload: {}, error: null })) as DesktopInvoke,
    onEvent: () => () => {},
    scope,
  });

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
  const scope = new BackgroundEffectScope();
  const ctx = createBackgroundCtx({ pluginId: "demo", surfaces: fakeSurfaces(), invoke, onEvent: () => () => {}, scope });

  const result = await ctx.rpc.call<{ ok: boolean }>("doThing", { a: 1 });

  assert.deepEqual(requests, [{ method: "plugin.demo.doThing", payload: { a: 1 } }]);
  assert.deepEqual(result, { ok: true });
});

test("ctx.events.on filters by method and ignores everything else", () => {
  const source = fakeEventSource();
  const scope = new BackgroundEffectScope();
  const ctx = createBackgroundCtx({
    pluginId: "demo",
    surfaces: fakeSurfaces(),
    invoke: (() => Promise.reject(new Error("unused"))) as DesktopInvoke,
    onEvent: source.onEvent,
    scope,
  });

  const received: unknown[] = [];
  ctx.events.on("demo.thing.happened", (payload) => received.push(payload));

  source.emit({ id: "1", type: "event", method: "demo.thing.happened", payload: { n: 1 } });
  source.emit({ id: "2", type: "event", method: "unrelated.event", payload: { n: 2 } });

  assert.deepEqual(received, [{ n: 1 }]);
});

test("ctx.events.on registers its unsubscribe as an event-phase effect, released on disposeAll", async () => {
  const source = fakeEventSource();
  const scope = new BackgroundEffectScope();
  const ctx = createBackgroundCtx({
    pluginId: "demo",
    surfaces: fakeSurfaces(),
    invoke: (() => Promise.reject(new Error("unused"))) as DesktopInvoke,
    onEvent: source.onEvent,
    scope,
  });

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
  const ctx = createBackgroundCtx({
    pluginId: "demo",
    surfaces: fakeSurfaces(),
    invoke: (() => Promise.reject(new Error("unused"))) as DesktopInvoke,
    onEvent: observedOnEvent,
    scope,
  });

  // Natural, "readable" authoring order that broke the backend twice (#227):
  // subscribe first, register the terminate-style effect after.
  ctx.events.on("demo.thing.happened", () => {});
  ctx.effect("controller_terminate", () => { order.push("terminate"); });

  await scope.disposeAll();
  assert.deepEqual(order, ["unsubscribe", "terminate"]);
  assert.equal(source.listenerCount(), 0);
});
