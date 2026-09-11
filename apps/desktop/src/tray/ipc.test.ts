import assert from "node:assert/strict";
import { test } from "node:test";
import { PluginTrayRegistry } from "./registry.js";
import { registerTrayIpc, trayChannels } from "./ipc.js";

class FakeIpc {
  readonly listeners = new Map<string, (event: unknown, payload: unknown) => void>();
  on(channel: string, listener: (event: unknown, payload: unknown) => void) {
    this.listeners.set(channel, listener);
  }
  send(channel: string, payload: unknown) {
    const listener = this.listeners.get(channel);
    assert.ok(listener, `no listener registered for ${channel}`);
    listener({ sender: null }, payload);
  }
}

function setup() {
  const registry = new PluginTrayRegistry();
  const errors: string[] = [];
  const ipc = new FakeIpc();
  registerTrayIpc({ on: (c, l) => ipc.on(c, l), onError: (channel) => errors.push(channel) }, registry);
  return { ipc, registry, errors };
}

test("a plugin contributes and updates its item over IPC", () => {
  const { ipc, registry } = setup();

  ipc.send(trayChannels.setEntry, { pluginId: "desktop_pet", entryId: "toggle", label: "显示桌宠" });
  assert.deepEqual(registry.list(), [
    { pluginId: "desktop_pet", entryId: "toggle", label: "显示桌宠", enabled: true },
  ]);

  ipc.send(trayChannels.setEntry, {
    pluginId: "desktop_pet", entryId: "toggle", label: "隐藏桌宠", enabled: false,
  });
  assert.deepEqual(registry.list(), [
    { pluginId: "desktop_pet", entryId: "toggle", label: "隐藏桌宠", enabled: false },
  ]);
});

test("removing one item and removing them all are different requests", () => {
  const { ipc, registry } = setup();
  ipc.send(trayChannels.setEntry, { pluginId: "desktop_pet", entryId: "toggle", label: "显示桌宠" });
  ipc.send(trayChannels.setEntry, { pluginId: "desktop_pet", entryId: "settings", label: "桌宠设置" });
  ipc.send(trayChannels.setEntry, { pluginId: "novelai", entryId: "open", label: "打开图库" });

  ipc.send(trayChannels.removeEntry, { pluginId: "desktop_pet", entryId: "toggle" });
  assert.deepEqual(registry.list().map((entry) => entry.entryId), ["settings", "open"]);

  ipc.send(trayChannels.removeAllEntries, { pluginId: "desktop_pet" });
  assert.deepEqual(registry.list().map((entry) => entry.pluginId), ["novelai"]);
});

test("a malformed request is reported instead of taking the main process down", () => {
  const { ipc, registry, errors } = setup();

  for (const payload of [null, {}, { pluginId: "a" }, { entryId: "b" }, { pluginId: 1, entryId: "b" }]) {
    ipc.send(trayChannels.setEntry, payload);
    ipc.send(trayChannels.removeEntry, payload);
    ipc.send(trayChannels.removeAllEntries, payload);
  }

  assert.deepEqual(registry.list(), []);
  assert.ok(errors.length > 0, "every refusal is reported");
});

test("an item with no usable label never reaches the menu", () => {
  const { ipc, registry, errors } = setup();

  // A blank menu item is worse than none: the user sees a clickable nothing.
  ipc.send(trayChannels.setEntry, { pluginId: "desktop_pet", entryId: "toggle", label: "  " });
  ipc.send(trayChannels.setEntry, { pluginId: "desktop_pet", entryId: "toggle" });

  assert.deepEqual(registry.list(), []);
  assert.deepEqual(errors, [trayChannels.setEntry, trayChannels.setEntry]);
});
