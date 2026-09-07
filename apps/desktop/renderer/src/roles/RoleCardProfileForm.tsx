import type React from "react";

import { inputClass } from "../shared/styles";
import type { RoleProfileDraft } from "../shared/types";

type RoleCardProfileFormProps = {
  profile: RoleProfileDraft;
  onUpdate: (next: RoleProfileDraft) => void;
};

/** Edits the fields imported from a character card without flattening its profile. */
export function RoleCardProfileForm({ profile, onUpdate }: RoleCardProfileFormProps) {
  const character = profile.character ?? {};
  const knowledge = profile.knowledge_base ?? {};
  const entries = knowledge.entries ?? [];

  function updateCharacter(field: keyof NonNullable<RoleProfileDraft["character"]>, value: string): void {
    onUpdate({ ...profile, character: { ...character, [field]: value } });
  }

  return (
    <div className="grid gap-5 border-t border-[#E5E7EB] pt-5">
      <div className="grid gap-4">
        <label className="grid gap-2 text-xs text-[#6B7280]">
          <span>角色资料</span>
          <textarea className={`${inputClass} min-h-56 resize-y`} value={character.profile ?? ""} onChange={(event) => updateCharacter("profile", event.target.value)} />
        </label>
        <div className="grid gap-4 lg:grid-cols-2">
          <label className="grid gap-2 text-xs text-[#6B7280]">
            <span>性格</span>
            <textarea className={`${inputClass} min-h-32 resize-y`} value={character.personality ?? ""} onChange={(event) => updateCharacter("personality", event.target.value)} />
          </label>
          <label className="grid gap-2 text-xs text-[#6B7280]">
            <span>执行规则</span>
            <textarea className={`${inputClass} min-h-32 resize-y`} value={character.behavior_rules ?? ""} onChange={(event) => updateCharacter("behavior_rules", event.target.value)} />
          </label>
        </div>
      </div>

      <section className="grid gap-3 rounded-md border border-[#E5E7EB] p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-medium text-[#344054]">知识库 · {entries.length}</h3>
          <label className="flex items-center gap-2 text-xs text-[#475467]">
            <input type="checkbox" checked={knowledge.enabled === true} onChange={(event) => onUpdate({ ...profile, knowledge_base: { ...knowledge, enabled: event.target.checked } })} />
            启用
          </label>
        </div>
        <label className="grid max-w-48 gap-1 text-xs text-[#6B7280]">
          <span>Token 预算</span>
          <input className={inputClass} type="number" min={0} value={knowledge.token_budget ?? 2000} onChange={(event) => onUpdate({ ...profile, knowledge_base: { ...knowledge, token_budget: Number(event.target.value) || 0 } })} />
        </label>
        {entries.length ? (
          <div className="grid max-h-64 gap-2 overflow-y-auto">
            {entries.map((entry, index) => <div className="rounded-md bg-[#F8FAFC] p-2 text-xs" key={entry.id ?? index}><p className="text-[#475467]">{entry.content || "空条目"}</p><p className="mt-1 text-[#98A2B3]">{(entry.primary_keys ?? entry.keywords ?? []).join("、") || "未设置关键词"}</p></div>)}
          </div>
        ) : <p className="text-xs text-[#98A2B3]">无</p>}
      </section>
    </div>
  );
}
