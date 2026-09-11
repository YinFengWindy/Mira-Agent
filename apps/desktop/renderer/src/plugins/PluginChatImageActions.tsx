import { pluginChatImageActionsRegistry, type PluginChatImageActionProps } from "./pluginFeatureRegistry";
import { usePluginEnabledState } from "./usePluginEnabledState";

/** Mounts plugin-authored image actions, removing them when their plugin becomes unavailable. */
export function PluginChatImageActions(props: Omit<PluginChatImageActionProps, "client">) {
  const enabled = usePluginEnabledState();
  return pluginChatImageActionsRegistry.list().filter((entry) => enabled(entry.pluginId)).map((entry) => (
    <entry.Component {...props} key={entry.pluginId} client={entry.client} />
  ));
}
