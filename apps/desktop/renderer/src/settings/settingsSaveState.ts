import type { SettingsSavePhase } from "./settingsPageTypes";

/** Returns whether the page should render its terminal save feedback. */
export function shouldShowSettingsFeedback(phase: SettingsSavePhase, message: string): boolean {
  return phase === "error" && Boolean(message);
}
