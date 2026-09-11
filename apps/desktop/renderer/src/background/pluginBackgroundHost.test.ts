import assert from "node:assert/strict";
import { test } from "node:test";
import type { BackgroundEffectScope } from "./backgroundEffectScope";
import { PluginBackgroundHost, type PluginBackgroundHostDeps } from "./pluginBackgroundHost";
import type { BackgroundCtx, PluginBackgroundEntry } from "./pluginBackgroundRegistry";

/** A fake ctx.effect-capable BackgroundCtx that just records what happened. */
function fakeCtx(pluginId: string, scope: BackgroundEffectScope, log: string[]): BackgroundCtx {
  return {
    surfaces: {} as BackgroundCtx["surfaces"],
    rpc: {} as BackgroundCtx["rpc"],
    events: { on: () => {} },
    effect(label, dispose) {
      scope.addEffect(label, () => { log.push(`${pluginId}:dispose:${label}`); return dispose(); });
    },
  };
}

function entry(pluginId: string, log: string[], onSetup?: (ctx: BackgroundCtx) => void): PluginBackgroundEntry {
  return {
    slot: "app.background",
    pluginId,
    setup(ctx) {
      log.push(`${pluginId}:setup`);
      // Every fixture plugin registers one teardown effect, so a test can
      // observe that disabling it actually disposes something rather than
      // merely removing it from `runningPluginIds()`.
      ctx.effect("noop", () => {});
      onSetup?.(ctx);
    },
  };
}

/** Roster + reconcile signal test double: lets a test flip enabled ids and fire the listener itself. */
function fakeRoster(initial: string[]) {
  let ids = new Set(initial);
  const listeners = new Set<() => void>();
  return {
    setEnabled: (next: string[]) => { ids = new Set(next); },
    fireRosterChanged: () => { for (const listener of listeners) listener(); },
    deps: {
      listEnabledPluginIds: () => Promise.resolve(new Set(ids)),
      subscribeRosterChanged: (listener: () => void) => { listeners.add(listener); return () => listeners.delete(listener); },
    },
  };
}

function makeDeps(overrides: Partial<PluginBackgroundHostDeps> & Pick<PluginBackgroundHostDeps, "registry">, log: string[]): PluginBackgroundHostDeps {
  return {
    listEnabledPluginIds: () => Promise.resolve(new Set()),
    subscribeRosterChanged: () => () => {},
    createCtx: (pluginId, scope) => fakeCtx(pluginId, scope, log),
    ...overrides,
  };
}

test("starts only registered plugins that are enabled", async () => {
  const log: string[] = [];
  const roster = fakeRoster(["a"]);
  const registry = { list: () => [entry("a", log), entry("b", log)] };
  const host = new PluginBackgroundHost(makeDeps({ registry, ...roster.deps }, log));

  await host.start();

  assert.deepEqual(log, ["a:setup"]);
  assert.deepEqual(host.runningPluginIds(), ["a"]);
});

test("disabling a plugin disposes its scope; a sibling keeps running", async () => {
  const log: string[] = [];
  const roster = fakeRoster(["a", "b"]);
  const registry = { list: () => [entry("a", log), entry("b", log)] };
  const host = new PluginBackgroundHost(makeDeps({ registry, ...roster.deps }, log));
  await host.start();
  log.length = 0;

  roster.setEnabled(["b"]);
  roster.fireRosterChanged();
  // reconcile() runs asynchronously off the roster-changed callback.
  await flushMicrotasks();

  assert.deepEqual(log, ["a:dispose:noop"]);
  assert.deepEqual(host.runningPluginIds(), ["b"], "the still-enabled sibling must not be touched");
});

test("a plugin enabled after startup gets setup called on the next reconcile", async () => {
  const log: string[] = [];
  const roster = fakeRoster([]);
  const registry = { list: () => [entry("a", log)] };
  const host = new PluginBackgroundHost(makeDeps({ registry, ...roster.deps }, log));
  await host.start();
  assert.deepEqual(host.runningPluginIds(), []);

  roster.setEnabled(["a"]);
  roster.fireRosterChanged();
  await flushMicrotasks();

  assert.deepEqual(host.runningPluginIds(), ["a"]);
});

test("a plugin with no background contribution is simply not in the registry, and is never touched", async () => {
  const log: string[] = [];
  const roster = fakeRoster(["a", "no-background-plugin"]);
  const registry = { list: () => [entry("a", log)] };
  const host = new PluginBackgroundHost(makeDeps({ registry, ...roster.deps }, log));

  await host.start();

  assert.deepEqual(host.runningPluginIds(), ["a"]);
});

test("stop() disposes every running plugin and unsubscribes from roster changes", async () => {
  const log: string[] = [];
  const roster = fakeRoster(["a", "b"]);
  const registry = { list: () => [entry("a", log), entry("b", log)] };
  const host = new PluginBackgroundHost(makeDeps({ registry, ...roster.deps }, log));
  await host.start();
  log.length = 0;

  await host.stop();

  assert.deepEqual(host.runningPluginIds(), []);
  assert.deepEqual(new Set(log), new Set(["a:dispose:noop", "b:dispose:noop"]));

  // A roster-changed fire after stop() must not resurrect anything: the
  // listener was unsubscribed.
  roster.fireRosterChanged();
  await flushMicrotasks();
  assert.deepEqual(host.runningPluginIds(), []);
});

test("a plugin whose setup() throws is reported and never counted as running", async () => {
  const log: string[] = [];
  const errors: Array<[string, string]> = [];
  const roster = fakeRoster(["broken", "ok"]);
  const registry = {
    list: () => [
      { slot: "app.background" as const, pluginId: "broken", setup: () => { throw new Error("boom"); } },
      entry("ok", log),
    ],
  };
  const host = new PluginBackgroundHost(makeDeps({
    registry,
    ...roster.deps,
    onError: (pluginId, phase) => errors.push([pluginId, phase]),
  }, log));

  await host.start();

  assert.deepEqual(host.runningPluginIds(), ["ok"]);
  assert.deepEqual(errors, [["broken", "setup"]]);
});

/** Lets queued microtasks (the host's internal reconcile chain) settle before assertions. */
function flushMicrotasks(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
