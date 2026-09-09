import type React from "react";
import type {
  SettingsSectionEditorProps,
  SettingsSubsection,
  StandaloneSettingsSectionProps,
} from "../settings/settingsPageTypes";

/** The two first-batch UI extension points a plugin (or the core) can contribute to. */
export type PluginUiSlot = "settings.section" | "nav.page";

/**
 * A settings section backed by the shared settings draft (`SettingsFormData`)
 * and its autosave queue. Only the built-in, TOML-backed domains use this —
 * they are the only sections that share one document and one save
 * transaction across every section at once.
 */
export type EditorSettingsSectionEntry = {
  kind: "editor";
  slot: "settings.section";
  id: string;
  label: string;
  subsections: SettingsSubsection[];
  /** Absent for built-in sections; present for plugin-contributed ones. */
  pluginId?: string;
  Component: React.ComponentType<SettingsSectionEditorProps>;
};

/**
 * A settings section that owns its own data end to end (schema-driven
 * plugin forms, custom plugin React components, and the built-in About
 * page). It never touches the shared settings draft, so it can render
 * before that draft has loaded and never blocks on it.
 */
export type StandaloneSettingsSectionEntry = {
  kind: "standalone";
  slot: "settings.section";
  id: string;
  label: string;
  subsections: SettingsSubsection[];
  pluginId?: string;
  Component: React.ComponentType<StandaloneSettingsSectionProps>;
};

export type SettingsSectionEntry = EditorSettingsSectionEntry | StandaloneSettingsSectionEntry;

/** Props injected into a plugin-contributed full-page navigation surface. */
export type PluginNavPageProps = {
  pageId: string;
};

export type NavPageEntry = {
  slot: "nav.page";
  id: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  pluginId?: string;
  Component: React.ComponentType<PluginNavPageProps>;
};

type Origin = "builtin" | "plugin";

/**
 * Aggregates settings.section and nav.page contributions from the core
 * (built-in entries) and from plugins (compiled in at build time via
 * `pluginUiModules.ts`). Built-in sections are registered through this same
 * registry rather than switched on directly, so the dynamic settings page
 * and the plugin slot mechanism share one real consumption path instead of
 * the slot machinery going unexercised by anything but plugins.
 */
class PluginUiRegistry {
  private readonly settingsSections = new Map<string, { origin: Origin; entry: SettingsSectionEntry }>();
  private readonly navPages = new Map<string, { origin: Origin; entry: NavPageEntry }>();

  /** Registers a settings.section entry; a duplicate id is warned about and skipped. */
  registerSettingsSection(entry: SettingsSectionEntry, origin: Origin = "plugin"): void {
    if (this.settingsSections.has(entry.id)) {
      console.warn(`[pluginUiRegistry] settings.section id 重复，已跳过: ${entry.id}`);
      return;
    }
    this.settingsSections.set(entry.id, { origin, entry });
  }

  /** Registers a nav.page entry; a duplicate id is warned about and skipped. */
  registerNavPage(entry: NavPageEntry, origin: Origin = "plugin"): void {
    if (this.navPages.has(entry.id)) {
      console.warn(`[pluginUiRegistry] nav.page id 重复，已跳过: ${entry.id}`);
      return;
    }
    this.navPages.set(entry.id, { origin, entry });
  }

  /** Removes every contribution owned by one plugin (used by tests and hot-toggle cleanup). */
  unregisterPlugin(pluginId: string): void {
    for (const [id, { entry }] of this.settingsSections) {
      if (entry.pluginId === pluginId) this.settingsSections.delete(id);
    }
    for (const [id, { entry }] of this.navPages) {
      if (entry.pluginId === pluginId) this.navPages.delete(id);
    }
  }

  /**
   * Lists settings.section entries, built-ins first, each group in
   * registration order; optionally filtered to entries that are either
   * built-in or owned by a currently-enabled plugin.
   */
  listSettingsSections(isPluginEnabled?: (pluginId: string) => boolean): SettingsSectionEntry[] {
    return this.listOrdered(this.settingsSections, isPluginEnabled);
  }

  /** Lists nav.page entries with the same built-in-first ordering and filtering. */
  listNavPages(isPluginEnabled?: (pluginId: string) => boolean): NavPageEntry[] {
    return this.listOrdered(this.navPages, isPluginEnabled);
  }

  getSettingsSection(id: string): SettingsSectionEntry | undefined {
    return this.settingsSections.get(id)?.entry;
  }

  getNavPage(id: string): NavPageEntry | undefined {
    return this.navPages.get(id)?.entry;
  }

  private listOrdered<T extends { pluginId?: string }>(
    source: Map<string, { origin: Origin; entry: T }>,
    isPluginEnabled?: (pluginId: string) => boolean,
  ): T[] {
    const visible = [...source.values()].filter(({ entry }) => (
      !entry.pluginId || !isPluginEnabled || isPluginEnabled(entry.pluginId)
    ));
    const builtins = visible.filter((item) => item.origin === "builtin").map((item) => item.entry);
    const plugins = visible.filter((item) => item.origin === "plugin").map((item) => item.entry);
    return [...builtins, ...plugins];
  }
}

/** Process-wide plugin UI registry; populated at module load by builtins and plugin modules. */
export const pluginUiRegistry = new PluginUiRegistry();

/** Exposed for tests that need an isolated registry instead of the shared singleton. */
export { PluginUiRegistry };
