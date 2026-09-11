import { pluginRoleSettingsRegistry, type PluginRoleValues } from "./pluginFeatureRegistry";

/** All plugin-owned role drafts, keyed by the contributing plugin id. */
export type PluginRoleSettingsDraft = Record<string, PluginRoleValues>;

/** Reads installed plugins' values without putting provider-specific keys in the host form. */
export function readPluginRoleSettings(runtimeConfig: Record<string, unknown> = {}): PluginRoleSettingsDraft {
  return Object.fromEntries(pluginRoleSettingsRegistry.list().map((entry) => [entry.pluginId, entry.read(runtimeConfig)]));
}

/** Merges only the keys owned by each installed role extension. */
export function writePluginRoleSettings(runtimeConfig: Record<string, unknown>, drafts: PluginRoleSettingsDraft) {
  return pluginRoleSettingsRegistry.list().reduce((current, entry) => (
    drafts[entry.pluginId] ? entry.write(current, drafts[entry.pluginId]) : current
  ), runtimeConfig);
}

/** Compares plugin form values against the latest persisted role snapshot. */
export function pluginRoleSettingsDirty(drafts: PluginRoleSettingsDraft, runtimeConfig: Record<string, unknown> = {}) {
  return pluginRoleSettingsRegistry.list().some((entry) => (
    drafts[entry.pluginId] !== undefined
    && JSON.stringify(drafts[entry.pluginId]) !== JSON.stringify(entry.read(runtimeConfig))
  ));
}
