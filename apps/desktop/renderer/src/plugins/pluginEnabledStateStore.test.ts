import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import {
  ensurePluginEnabledStateLoaded,
  isPluginEnabled,
  resetPluginEnabledStateForTests,
  setPluginEnabledCache,
  setPluginEnabledSnapshot,
  subscribePluginEnabledState,
} from "./pluginEnabledStateStore.js";

afterEach(() => resetPluginEnabledStateForTests());

describe("pluginEnabledStateStore", () => {
  it("treats a plugin unknown to the cache as enabled", () => {
    assert.equal(isPluginEnabled("never-seen"), true);
  });

  it("fetches the roster once and memoizes it across callers", async () => {
    let calls = 0;
    const client = { listPlugins: async () => { calls += 1; return [{ id: "demo", enabled: false } as never]; } };

    await ensurePluginEnabledStateLoaded(client);
    await ensurePluginEnabledStateLoaded(client);

    assert.equal(calls, 1);
    assert.equal(isPluginEnabled("demo"), false);
  });

  it("coalesces concurrent loads into a single request", async () => {
    let calls = 0;
    let resolveFetch!: (value: Array<{ id: string; enabled: boolean }>) => void;
    const client = {
      listPlugins: async () => {
        calls += 1;
        return new Promise<Array<{ id: string; enabled: boolean }>>((resolve) => { resolveFetch = resolve; });
      },
    };

    const first = ensurePluginEnabledStateLoaded(client as never);
    const second = ensurePluginEnabledStateLoaded(client as never);
    resolveFetch([{ id: "demo", enabled: true }]);
    await Promise.all([first, second]);

    assert.equal(calls, 1);
  });

  it("notifies subscribers when the snapshot or a single flag changes", () => {
    let notifications = 0;
    const unsubscribe = subscribePluginEnabledState(() => { notifications += 1; });

    setPluginEnabledSnapshot([{ id: "demo", enabled: true }]);
    assert.equal(isPluginEnabled("demo"), true);
    setPluginEnabledCache("demo", false);
    assert.equal(isPluginEnabled("demo"), false);

    assert.equal(notifications, 2);
    unsubscribe();
  });
});
