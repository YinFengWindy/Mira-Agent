import { pluginUiRegistry } from "../plugins/pluginUiRegistry";
import { registerBuiltinSettingsSections } from "./registerBuiltinSettingsSections";
import type { SettingsSectionId } from "./SettingsSidebar";
import type { SettingsSectionEditorProps } from "./settingsPageTypes";

registerBuiltinSettingsSections();

type SettingsSectionContentProps = SettingsSectionEditorProps & {
  sectionId: SettingsSectionId;
};

/**
 * Routes the active settings domain to its registered "editor" component.
 * Replaces the previous exhaustive switch: sections are looked up in
 * `pluginUiRegistry` instead of being an enumerable, hand-maintained set,
 * so a plugin's own draft-backed section (if it ever needs one) resolves
 * the same way a built-in one does.
 */
export function SettingsSectionContent({
  sectionId,
  ...editorProps
}: SettingsSectionContentProps) {
  const entry = pluginUiRegistry.getSettingsSection(sectionId);
  if (!entry || entry.kind !== "editor") return null;
  const Component = entry.Component;
  return <Component {...editorProps} />;
}
