import { Select } from "../shared/ui/Select";
import { PencilSimple, Waveform } from "@phosphor-icons/react";
import type React from "react";
import { useState } from "react";
import { minimaxVoiceEmotionOptions } from "./roleVoiceConfig";
import type { RoleFormState } from "../shared/types";
import { SettingsToggleCard } from "../settings/SettingsToggleCard";
import { roleTileFieldClass as voiceFieldClass } from "./roleEditorStyles";

type RoleVoiceSettingsPanelProps = {
  roleForm: RoleFormState;
  onUpdate: (next: React.SetStateAction<RoleFormState>) => void;
};

/** Renders role-owned voice selection, speed, and mood mapping fields. */
export function RoleVoiceSettingsPanel({ roleForm, onUpdate }: RoleVoiceSettingsPanelProps) {
  const [technicalFieldsOpen, setTechnicalFieldsOpen] = useState(false);
  const moods = Array.from(new Set([
    ...roleForm.moodCatalog,
    ...Object.keys(roleForm.voiceMoodEmotions),
  ].filter(Boolean)));
  const voiceName = roleForm.voiceName.trim() || "尚未选择音色";
  const voiceSource = roleForm.voiceOwnership === "shiori_managed" ? "Shiori 管理音色" : `${roleForm.voiceProvider || "MiniMax"} 外部音色`;

  return (
    <section aria-labelledby="role-voice-heading" className="grid gap-5 rounded-2xl bg-[#EEF6F2] p-5" data-testid="role-voice-config">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/75 text-[#2E7D5B]" aria-hidden="true">
            <Waveform className="h-5 w-5" weight="duotone" />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-ink" id="role-voice-heading">当前音色</h2>
            <p className="mt-1 truncate text-sm text-ink-secondary">{voiceName}</p>
            <p className="mt-0.5 text-xs text-ink-muted">{voiceSource}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button className="inline-flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-ink-secondary transition hover:bg-white/70 hover:text-ink focus:outline-none" type="button" aria-expanded={technicalFieldsOpen} onClick={() => setTechnicalFieldsOpen((current) => !current)}>
            <PencilSimple className="h-4 w-4" weight="bold" />编辑参数
          </button>
          <span className={roleForm.voiceEnabled ? "text-xs text-success-text" : "text-xs text-ink-muted"}>{roleForm.voiceEnabled ? "已启用" : "未启用"}</span>
          <SettingsToggleCard checked={roleForm.voiceEnabled} ariaLabel="角色语音" onChange={(checked) => onUpdate((current) => ({ ...current, voiceEnabled: checked }))} />
        </div>
      </div>

      {technicalFieldsOpen ? (
        <div className="grid gap-4 border-t border-[#DCEAE2] pt-4 sm:grid-cols-2">
            <label className="grid gap-1.5 text-xs text-ink-muted"><span>音色名称</span><input className={voiceFieldClass} value={roleForm.voiceName} onChange={(event) => onUpdate((current) => ({ ...current, voiceName: event.target.value }))} placeholder="显示名称" /></label>
            <label className="grid gap-1.5 text-xs text-ink-muted"><span>语速（0.5 - 2.0）</span><input className={voiceFieldClass} type="number" min="0.5" max="2" step="0.1" value={String(roleForm.voiceSpeed)} onChange={(event) => onUpdate((current) => ({ ...current, voiceSpeed: Number(event.target.value) }))} /></label>
            <label className="grid gap-1.5 text-xs text-ink-muted"><span>Provider</span><input className={voiceFieldClass} value={roleForm.voiceProvider} readOnly={roleForm.voiceOwnership === "shiori_managed"} onChange={(event) => onUpdate((current) => ({ ...current, voiceProvider: event.target.value, voiceOwnership: "external" }))} placeholder="minimax" /></label>
            <label className="grid gap-1.5 text-xs text-ink-muted"><span>音色 ID</span><input className={voiceFieldClass} value={roleForm.voiceId} readOnly={roleForm.voiceOwnership === "shiori_managed"} onChange={(event) => onUpdate((current) => ({ ...current, voiceId: event.target.value, voiceOwnership: "external" }))} placeholder="MiniMax voice_id" /></label>
        </div>
      ) : null}

      {moods.length > 0 ? (
        <div className="grid gap-3 border-t border-[#DCEAE2] pt-4">
          <div><h3 className="text-sm font-medium text-ink">情绪映射</h3><p className="mt-1 text-xs text-ink-muted">为角色状态选择优先使用的语音情绪。</p></div>
          <div className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
            {moods.map((mood) => (
              <label className="grid grid-cols-[minmax(0,1fr)_132px] items-center gap-3 border-b border-[#E2EEE7] py-2.5 text-sm last:border-b-0" key={mood}>
                <span className="truncate text-ink-secondary">{mood}</span>
                <Select aria-label={mood} className="rounded-md border border-transparent bg-white/75 px-2.5 py-2 text-xs text-ink-secondary transition focus:bg-white focus:outline-none" value={roleForm.voiceMoodEmotions[mood] ?? ""} onValueChange={(value) => onUpdate((current) => {
                  const next = { ...current.voiceMoodEmotions };
                  if (value) next[mood] = value;
                  else delete next[mood];
                  return { ...current, voiceMoodEmotions: next };
                })} options={[{ value: "", label: "自动判断" }, ...minimaxVoiceEmotionOptions.map((emotion) => ({ value: emotion, label: emotion }))]} />
              </label>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
