import type { PluginUiModule } from "../../../apps/desktop/renderer/src/plugins/pluginUiModuleContract";

/**
 * qqbot's own settings.section contribution (#183): its App ID/Client
 * Secret used to live hardcoded in the core Channels settings tab and were
 * threaded through the shared settings draft. Now that the plugin declares
 * `config_model` (see backend/plugin.py, backend/manifest.yaml), the
 * generic schema-driven form (`PluginSchemaSettingsSection`, wired in by
 * `kind: "schema"` below) reads/writes `[plugins.qqbot]` directly through
 * `plugin.config.get/set`, independent of the core settings save
 * transaction.
 */
const qqbotUiModule: PluginUiModule = {
  pluginId: "qqbot",
  settingsSection: { kind: "schema", label: "QQBot" },
};

export default qqbotUiModule;
