import { PluginDataStoreError, type PluginDataStore } from "./dataStore.js";

/**
 * IPC channels for the plugin data store.
 *
 * The caller states which plugin it is acting for, and nothing verifies it —
 * the same property `src/surface/ipc.ts::readKey` documents, for the same
 * reason: under the trust model in #210 every plugin's renderer code shares one
 * realm with the host, so a stated id keeps honest bugs local but is not a
 * boundary. The id is still validated for *shape* (`dataStore.ts`), because a
 * malformed one would escape the store directory, which is a different problem
 * from an impersonated one.
 */
export const pluginDataChannels = {
  read: "desktop:plugin-data-read",
  write: "desktop:plugin-data-write",
} as const;

/** The bits of the IPC boundary this module needs, mirroring `DesktopIpcHost`. */
export type PluginDataIpcHost = {
  handle(channel: string, listener: (event: unknown, payload: unknown) => unknown): void;
};

export function registerPluginDataIpc(host: PluginDataIpcHost, store: PluginDataStore): void {
  host.handle(pluginDataChannels.read, async (_event, payload) => {
    return await store.read(readPluginId(payload));
  });
  host.handle(pluginDataChannels.write, async (_event, payload) => {
    await store.write(readPluginId(payload), (payload as { value?: unknown }).value ?? null);
  });
}

function readPluginId(payload: unknown): string {
  if (payload === null || typeof payload !== "object") {
    throw new PluginDataStoreError("插件数据请求缺少插件 id");
  }
  const { pluginId } = payload as { pluginId?: unknown };
  if (typeof pluginId !== "string" || !pluginId) {
    throw new PluginDataStoreError("插件数据请求缺少插件 id");
  }
  return pluginId;
}
