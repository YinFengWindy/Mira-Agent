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
 *
 * `sectionId` is expected to already be a resolved, currently-visible
 * "editor" section id — `EditableSettingsPage` only renders this component
 * once it has confirmed that itself. If that invariant is ever violated
 * this throws instead of silently rendering nothing, per this repo's
 * "fail fast, no unnecessary fallback" convention: a settings page that
 * goes blank with no error is much harder to diagnose than one that crashes
 * with a clear cause.
 */
export function SettingsSectionContent({
  sectionId,
  ...editorProps
}: SettingsSectionContentProps) {
  const entry = pluginUiRegistry.getSettingsSection(sectionId);
  if (!entry || entry.kind !== "editor") {
    throw new Error(
      `SettingsSectionContent: "${sectionId}" 不是一个已注册的 editor 类型 settings.section；`
      + "调用方必须保证只在该 section 存在且可见时才渲染。",
    );
  }
  const Component = entry.Component;
  return <Component {...editorProps} />;
}
