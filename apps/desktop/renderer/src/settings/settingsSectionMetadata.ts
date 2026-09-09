import { pluginUiRegistry, type SettingsSectionEntry } from "../plugins/pluginUiRegistry";
import { registerBuiltinSettingsSections } from "./registerBuiltinSettingsSections";
import type { SettingsSectionId } from "./SettingsSidebar";
import type { SettingsSubsection } from "./settingsPageTypes";

export type { SettingsSubsection };

registerBuiltinSettingsSections();

/** Lists every currently registered settings section, built-ins first. */
export function listSettingsSections(
  isPluginEnabled?: (pluginId: string) => boolean,
): SettingsSectionEntry[] {
  return pluginUiRegistry.listSettingsSections(isPluginEnabled);
}

/** Returns the sub-navigation tabs a section declared; empty when unregistered. */
export function getSettingsSubsections(sectionId: SettingsSectionId): SettingsSubsection[] {
  return pluginUiRegistry.getSettingsSection(sectionId)?.subsections ?? [];
}

/**
 * Builds the initial active subsection for every currently registered
 * section. Keyed by plain `string` (not `SettingsSectionId`): this is a
 * dynamic lookup map, not an exhaustively-cased record, and section ids
 * include plugin ids only known at runtime.
 */
export function createInitialSettingsSubsectionState(
  sections: SettingsSectionEntry[] = listSettingsSections(),
): Record<string, string> {
  return Object.fromEntries(
    sections.map((section) => [section.id, section.subsections[0]?.id ?? ""]),
  );
}

/** Resolves an active subsection, falling back to the first available option. */
export function resolveSettingsSubsectionId(
  sectionId: SettingsSectionId,
  activeSubsections: Record<string, string>,
): string | null {
  const subsections = getSettingsSubsections(sectionId);
  const activeId = activeSubsections[sectionId];
  return subsections.some((item) => item.id === activeId)
    ? activeId
    : (subsections[0]?.id ?? null);
}
