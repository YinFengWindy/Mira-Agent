import { useMemo } from "react";
import { pluginUiRegistry, type RoleAssetsPanelEntry } from "./pluginUiRegistry";
import { usePluginEnabledState } from "./usePluginEnabledState";

/**
 * The `role.assets` panels visible right now.
 *
 * Kept apart from `usePluginUiVisibility`, which bundles the answers the shell
 * frame needs (nav rail, settings sidebar, active plugin page) and is
 * documented as centralizing them for that one consumer. The role asset page
 * is a different consumer that needs exactly one of those answers; pulling the
 * whole bundle in to use a fifth of it would read worse than this.
 *
 * The enablement filter is the same rule every slot uses, so disabling a
 * plugin removes its panel immediately rather than at the next reload (#174
 * acceptance criterion 3).
 */
export function useRoleAssetsPanels(): RoleAssetsPanelEntry[] {
  const isPluginEnabled = usePluginEnabledState();
  return useMemo(() => pluginUiRegistry.listRoleAssetsPanels(isPluginEnabled), [isPluginEnabled]);
}
