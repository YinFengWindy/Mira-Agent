import type { SettingsSavePhase } from "./settingsPageTypes";
import { shouldShowSettingsFeedback } from "./settingsSaveState";
import { cx } from "../shared/styles";
import { ArrowClockwise, ArrowsClockwise } from "@phosphor-icons/react";

/** Renders terminal settings save feedback above the page content. */
export function SettingsSaveFeedback({
  phase,
  message,
  onRetry,
  onReload,
}: {
  phase: SettingsSavePhase;
  message: string;
  onRetry?: () => void;
  onReload?: () => void;
}) {
  if (!shouldShowSettingsFeedback(phase, message)) return null;
  return (
    <div
      className={cx(
        "mx-auto mt-4 flex w-[calc(100%-2rem)] max-w-[560px] items-start gap-2 rounded-md border px-4 py-2.5 text-sm leading-6",
        "border-[rgba(176,58,58,0.18)] bg-[rgba(255,241,241,0.96)] text-[#9a2f2f]",
      )}
      role="status"
      aria-live="polite"
    >
      <span className="min-w-0 flex-1 break-words">{message}</span>
      {onRetry ? <button className="shrink-0 rounded-md p-1 hover:bg-red-100" type="button" aria-label="重试保存" title="重试保存" onClick={onRetry}><ArrowClockwise size={18} /></button> : null}
      {onReload ? <button className="shrink-0 rounded-md p-1 hover:bg-red-100" type="button" aria-label="放弃草稿并重新加载" title="放弃草稿并重新加载" onClick={onReload}><ArrowsClockwise size={18} /></button> : null}
    </div>
  );
}
