import { pluginRoleSettingsRegistry } from "./pluginFeatureRegistry";
import type { PluginRoleSettingsDraft } from "./pluginRoleSettings";
import { usePluginEnabledState } from "./usePluginEnabledState";

/** Mounts active plugins' role settings while preserving all stored drafts. */
export function PluginRoleSettingsSlot({ drafts, onChange }: {
  drafts: PluginRoleSettingsDraft;
  onChange: (drafts: PluginRoleSettingsDraft) => void;
}) {
  const enabled = usePluginEnabledState();
  return pluginRoleSettingsRegistry.list().filter((entry) => enabled(entry.pluginId)).map((entry) => (
    <entry.Component key={entry.pluginId} values={drafts[entry.pluginId] ?? entry.read({})}
      onChange={(values) => onChange({ ...drafts, [entry.pluginId]: values })} />
  ));
}
