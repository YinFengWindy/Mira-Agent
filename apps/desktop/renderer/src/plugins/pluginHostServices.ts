import { invokeBridgePayload } from "../shared/bridgeInvoke";
import type { RoleRecord } from "../shared/types";

/** Narrow host services available to plugin UI without exposing raw IPC. */
export type PluginHostServices = {
  onEvent: typeof window.miraDesktop.onEvent;
  listRoles: () => Promise<RoleRecord[]>;
  pickImages: (options: { multiple: boolean }) => Promise<string[]>;
  /** Native user selection plus bounded private staging, without a media grant. */
  pickFiles: typeof window.miraDesktop.pickFiles;
};

/** Stable adapter supplied by the desktop composition boundary. */
export const desktopPluginHostServices: PluginHostServices = {
  onEvent: (listener) => window.miraDesktop.onEvent(listener),
  async listRoles() {
    const payload = await invokeBridgePayload<{ roles: RoleRecord[] }>(window.miraDesktop.invoke, "roles.list", {});
    return payload.roles;
  },
  pickImages: (options) => window.miraDesktop.pickImages(options),
  pickFiles: (options) => window.miraDesktop.pickFiles(options),
};
