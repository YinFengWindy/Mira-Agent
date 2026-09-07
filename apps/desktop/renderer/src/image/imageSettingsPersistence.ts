import type { DesktopApi, SettingsFormData } from "../../../src/bridge/shared.js";
import { saveSettingsPageData } from "../settings/settingsPersistence.js";

/** Applies image preferences against the latest version without overwriting unrelated settings. */
export async function saveImageSettings(
  api: Pick<DesktopApi, "readSettings" | "saveSettings">,
  patch: Partial<SettingsFormData["integrations"]>,
) {
  const current = await api.readSettings();
  const result = await saveSettingsPageData(api, {
    ...current.formData,
    integrations: { ...current.formData.integrations, ...patch },
  }, { expectedGeneration: current.generation, operationId: crypto.randomUUID() });
  if (!result.saveResult.ok) throw new Error(result.saveResult.error?.message ?? "配置应用失败。");
  return result.nextDraft;
}
