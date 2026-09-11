import { PluginTrayError, type PluginTrayRegistry } from "./registry.js";

/**
 * IPC channels for the tray capability.
 *
 * Same trust property as `src/surface/ipc.ts::readKey` and the plugin data
 * store: the caller states which plugin it is acting for and nothing verifies
 * it, because under #210's trust model every plugin's renderer code shares one
 * realm with the host. The stated id keeps honest bugs local; it is not a
 * boundary. Shape is still validated, because a malformed request would put a
 * blank or unclickable item in a menu the user actually sees.
 */
export const trayChannels = {
  setEntry: "desktop:tray-set-entry",
  removeEntry: "desktop:tray-remove-entry",
  removeAllEntries: "desktop:tray-remove-all-entries",
  /** Main → plugin host: the user picked a plugin's item. */
  entryClicked: "desktop:tray-entry-clicked",
} as const;

/** What the host pushes when one of a plugin's tray items is chosen. */
export type TrayEntryClickedPayload = { pluginId: string; entryId: string };

/** The bits of the IPC boundary this module needs, mirroring `DesktopIpcHost`. */
export type TrayIpcHost = {
  on(channel: string, listener: (event: unknown, payload: unknown) => void): void;
  /** Reports a refused request; a malformed one must never take the main process down. */
  onError?: (channel: string, error: unknown) => void;
};

export function registerTrayIpc(host: TrayIpcHost, registry: PluginTrayRegistry): void {
  const report = host.onError ?? (() => {});

  host.on(trayChannels.setEntry, (_event, payload) => {
    try {
      const request = readEntryRequest(payload);
      registry.setEntry(request.pluginId, request.entryId, {
        label: String((payload as { label?: unknown }).label ?? ""),
        enabled: (payload as { enabled?: unknown }).enabled !== false,
      });
    } catch (error) {
      report(trayChannels.setEntry, error);
    }
  });

  host.on(trayChannels.removeAllEntries, (_event, payload) => {
    try {
      const { pluginId } = (payload ?? {}) as { pluginId?: unknown };
      if (typeof pluginId !== "string" || !pluginId) throw new PluginTrayError("托盘请求缺少插件 id");
      registry.removeAllForPlugin(pluginId);
    } catch (error) {
      report(trayChannels.removeAllEntries, error);
    }
  });

  host.on(trayChannels.removeEntry, (_event, payload) => {
    try {
      const request = readEntryRequest(payload);
      registry.removeEntry(request.pluginId, request.entryId);
    } catch (error) {
      report(trayChannels.removeEntry, error);
    }
  });
}

function readEntryRequest(payload: unknown): { pluginId: string; entryId: string } {
  if (payload === null || typeof payload !== "object") {
    throw new PluginTrayError("托盘请求不合法");
  }
  const { pluginId, entryId } = payload as { pluginId?: unknown; entryId?: unknown };
  if (typeof pluginId !== "string" || !pluginId) throw new PluginTrayError("托盘请求缺少插件 id");
  if (typeof entryId !== "string" || !entryId) throw new PluginTrayError("托盘请求缺少条目 id");
  return { pluginId, entryId };
}
