import type React from "react";
import type { SettingsSubsection, StandaloneSettingsSectionProps } from "../settings/settingsPageTypes";
import { createPluginSchemaSettingsSection } from "./PluginSchemaSettingsSection";
import { pluginUiRegistry, type PluginNavPageProps } from "./pluginUiRegistry";

/** One plugin's settings.section contribution: either a schema auto-form or a custom component. */
export type PluginSettingsSectionContribution =
  | { kind: "schema"; label: string; subsections?: SettingsSubsection[] }
  | {
    kind: "component";
    label: string;
    subsections?: SettingsSubsection[];
    component: React.ComponentType<StandaloneSettingsSectionProps>;
  };

export type PluginNavPageContribution = {
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  component: React.ComponentType<PluginNavPageProps>;
};

/**
 * The shape a plugin's `ui/index.tsx` default-exports to participate in
 * `settings.section` and/or `nav.page`. A plugin id is required (it scopes
 * both its own RPC namespace and hot enable/disable filtering); both slots
 * are optional since a plugin may only need one, or a config-only plugin
 * may only need the schema form.
 */
export type PluginUiModule = {
  pluginId: string;
  settingsSection?: PluginSettingsSectionContribution;
  navPage?: PluginNavPageContribution;
};

function isPluginUiModule(value: unknown): value is PluginUiModule {
  return Boolean(value) && typeof value === "object" && typeof (value as { pluginId?: unknown }).pluginId === "string";
}

/**
 * Registers every plugin UI module found by the build-time glob into
 * `pluginUiRegistry`. Pure and DOM-free (only mutates the passed registry)
 * so it is unit-testable with a hand-built `modules` record instead of a
 * real `import.meta.glob` result, which only Vite can produce.
 */
export function applyPluginUiModules(
  modules: Record<string, { default: PluginUiModule }>,
  registry = pluginUiRegistry,
): void {
  for (const [path, mod] of Object.entries(modules)) {
    const uiModule = mod.default;
    if (!isPluginUiModule(uiModule)) {
      console.error(`[pluginUiModules] ${path} 的默认导出不是合法的 PluginUiModule，已跳过`);
      continue;
    }
    const { pluginId, settingsSection, navPage } = uiModule;
    if (settingsSection) {
      const id = pluginId;
      registry.registerSettingsSection({
        kind: "standalone",
        slot: "settings.section",
        id,
        label: settingsSection.label,
        subsections: settingsSection.subsections ?? [{ id: "default", label: settingsSection.label }],
        pluginId,
        Component: settingsSection.kind === "schema"
          ? createPluginSchemaSettingsSection(pluginId)
          : settingsSection.component,
      });
    }
    if (navPage) {
      registry.registerNavPage({
        slot: "nav.page",
        id: pluginId,
        label: navPage.label,
        icon: navPage.icon,
        pluginId,
        Component: navPage.component,
      });
    }
  }
}
