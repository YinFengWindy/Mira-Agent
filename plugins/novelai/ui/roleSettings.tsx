import { ImageSquare } from "@phosphor-icons/react";
import { SettingsToggleField } from "../../../apps/desktop/renderer/src/settings/SettingsFieldPrimitives";
import { cardClass, cx } from "../../../apps/desktop/renderer/src/shared/styles";
import type { PluginRoleSettingsContribution, PluginRoleSettingsProps } from "../../../apps/desktop/renderer/src/plugins/pluginFeatureRegistry";

/** NovelAI's per-role preference stays independent of the global plugin enable switch. */
export function NovelAiRoleSettings({ values, onChange }: PluginRoleSettingsProps) {
  return <div className={cx(cardClass, "p-5")}>
    <ImageSquare className="mb-3 h-5 w-5 text-ink-muted" aria-hidden="true" />
    <SettingsToggleField label="自动场景 CG" checked={Boolean(values.autoSceneCgEnabled)}
      onChange={(checked) => onChange({ ...values, autoSceneCgEnabled: checked })} />
  </div>;
}

/** Keeps the existing stored key so upgrading or disabling the plugin never loses role preferences. */
export const novelAiRoleSettings: PluginRoleSettingsContribution = {
  read: (runtime) => ({ autoSceneCgEnabled: Boolean(runtime.auto_scene_cg_enabled) }),
  write: (runtime, values) => ({ ...runtime, auto_scene_cg_enabled: Boolean(values.autoSceneCgEnabled) }),
  Component: NovelAiRoleSettings,
};
