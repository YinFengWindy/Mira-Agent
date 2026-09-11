// Registers every plugin's `background/index.ts` before the host reads the registry.
import "./pluginBackgroundModules";
import { createPluginBridgeClient } from "../plugins/pluginBridgeClient";
import { createBackgroundCtx } from "./pluginBackgroundCtx";
import { PluginBackgroundHost } from "./pluginBackgroundHost";
import { pluginBackgroundRegistry } from "./pluginBackgroundRegistry";

/**
 * Entry point for `plugin-host.html`: the dedicated hidden renderer window
 * (#226 item 1) that owns every plugin's always-resident `app.background`
 * contribution. See `apps/desktop/src/pluginHost/window.ts` for why this runs
 * in its own window rather than the main window's renderer.
 *
 * There is no DOM to mount here — a background module is a controller, not a
 * component — so unlike `surface/main.tsx` this file wires plain objects, not
 * React.
 */
const invoke = window.miraDesktop.invoke;
const onEvent = window.miraDesktop.onEvent;
const pluginBridge = createPluginBridgeClient(invoke);

const host = new PluginBackgroundHost({
  registry: pluginBackgroundRegistry,
  async listEnabledPluginIds() {
    const plugins = await pluginBridge.listPlugins();
    return new Set(plugins.filter((plugin) => plugin.enabled).map((plugin) => plugin.id));
  },
  subscribeRosterChanged(listener) {
    // `runtime.applied` already fires for a plugin enable/disable toggle,
    // since `plugins.setEnabled` routes through the same
    // `RuntimeSettingsApplication.apply` that publishes it (see
    // `apps/backend/desktop_bridge/runtime/plugin_management.py`). Reusing it
    // means this window needs no new backend event to learn its roster
    // changed — it just re-fetches `plugins.list` whenever settings apply.
    return onEvent((event) => {
      if (event.method === "runtime.applied") listener();
    });
  },
  createCtx(pluginId, scope) {
    return createBackgroundCtx({
      pluginId,
      surfaces: window.miraDesktop.surfaces,
      invoke,
      onEvent,
      scope,
    });
  },
  onError(pluginId, phase, error) {
    // This window is invisible, so a failure here has nowhere on screen to
    // show up — logging is the only surface it has.
    console.error(`[plugin-host] ${pluginId} 的 ${phase === "setup" ? "setup" : "卸载"} 失败`, error);
  },
});

void host.start();
