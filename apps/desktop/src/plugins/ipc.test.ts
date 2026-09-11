import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { PluginDataStore, PluginDataStoreError } from "./dataStore.js";
import { pluginDataChannels, registerPluginDataIpc } from "./ipc.js";

class FakeIpc {
  readonly handlers = new Map<string, (event: unknown, payload: unknown) => unknown>();
  handle(channel: string, listener: (event: unknown, payload: unknown) => unknown) {
    this.handlers.set(channel, listener);
  }
  invoke(channel: string, payload: unknown) {
    const handler = this.handlers.get(channel);
    assert.ok(handler, `no handler registered for ${channel}`);
    return handler({ sender: null }, payload);
  }
}

async function withIpc(run: (ipc: FakeIpc, store: PluginDataStore) => Promise<void>): Promise<void> {
  const root = await mkdtemp(join(tmpdir(), "shiori-plugin-data-ipc-"));
  try {
    const store = new PluginDataStore({ directory: join(root, "plugin-data") });
    const ipc = new FakeIpc();
    registerPluginDataIpc(ipc, store);
    await run(ipc, store);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

test("a renderer round-trips its plugin's value over IPC", async () => {
  await withIpc(async (ipc) => {
    await ipc.invoke(pluginDataChannels.write, { pluginId: "desktop_pet", value: { visible: true } });

    assert.deepEqual(await ipc.invoke(pluginDataChannels.read, { pluginId: "desktop_pet" }), {
      visible: true,
    });
  });
});

test("a write with no value clears the plugin's data rather than storing undefined", async () => {
  await withIpc(async (ipc, store) => {
    await ipc.invoke(pluginDataChannels.write, { pluginId: "desktop_pet", value: { visible: true } });
    await ipc.invoke(pluginDataChannels.write, { pluginId: "desktop_pet" });

    // `undefined` is not representable in JSON; storing it would write the
    // literal text `undefined` and make the file unreadable on the next launch.
    assert.equal(store.snapshot("desktop_pet"), null);
    assert.equal(await ipc.invoke(pluginDataChannels.read, { pluginId: "desktop_pet" }), null);
  });
});

test("a request without a usable plugin id is refused on both channels", async () => {
  await withIpc(async (ipc) => {
    for (const payload of [null, {}, { pluginId: "" }, { pluginId: 7 }]) {
      await assert.rejects(
        Promise.resolve().then(() => ipc.invoke(pluginDataChannels.read, payload)),
        PluginDataStoreError,
      );
      await assert.rejects(
        Promise.resolve().then(() => ipc.invoke(pluginDataChannels.write, payload)),
        PluginDataStoreError,
      );
    }
  });
});
