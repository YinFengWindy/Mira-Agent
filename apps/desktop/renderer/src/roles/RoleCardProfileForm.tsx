import { cx } from "../shared/styles";
import type { RoleProfileDraft } from "../shared/types";
import { SettingsToggleCard } from "../settings/SettingsToggleCard";
import {
  roleChipClass,
  roleFieldClass,
  roleSectionDescriptionClass,
  roleSectionTitleClass,
} from "./roleEditorStyles";

type RoleCardProfileFormProps = {
  profile: RoleProfileDraft;
  onUpdate: (next: RoleProfileDraft) => void;
  showKnowledge?: boolean;
};

type ProfileFieldProps = {
  label: string;
  hint: string;
  value: string;
  placeholder?: string;
  heightClass?: string;
  onChange: (value: string) => void;
};

/** One labeled long-form profile field with wheel scrolling instead of a resize handle. */
function ProfileField({ label, hint, value, placeholder, heightClass = "h-40", onChange }: ProfileFieldProps) {
  return (
    <label className="grid content-start gap-2">
      <span className="grid gap-0.5">
        <span className="text-sm font-medium text-[#182230]">{label}</span>
        <span className="text-xs text-[#7B8794]">{hint}</span>
      </span>
      <textarea
        className={cx(roleFieldClass, "scrollbar-soft resize-none overflow-y-auto leading-6", heightClass)}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}

/** Edits structured role fields without flattening their persisted profile. */
export function RoleCardProfileForm({
  profile,
  onUpdate,
  showKnowledge = true,
}: RoleCardProfileFormProps) {
  const character = profile.character ?? {};
  const knowledge = profile.knowledge_base ?? {};
  const entries = knowledge.entries ?? [];

  function updateCharacter(field: keyof NonNullable<RoleProfileDraft["character"]>, value: string): void {
    onUpdate({ ...profile, character: { ...character, [field]: value } });
  }

  return (
    <div className="grid gap-7">
      <div className="grid gap-5">
        <ProfileField
          label="角色设定"
          hint="外貌、身份、背景与关系设定。"
          value={character.profile ?? ""}
          placeholder="这个角色是谁？从哪里来？和用户是什么关系？"
          heightClass="h-56"
          onChange={(value) => updateCharacter("profile", value)}
        />
        <div className="grid gap-5 lg:grid-cols-2">
          <ProfileField
            label="性格"
            hint="说话方式、气质与情绪倾向。"
            value={character.personality ?? ""}
            onChange={(value) => updateCharacter("personality", value)}
          />
          <ProfileField
            label="执行规则"
            hint="行为边界、输出要求、禁止事项。"
            value={character.behavior_rules ?? ""}
            onChange={(value) => updateCharacter("behavior_rules", value)}
          />
        </div>
      </div>

      {showKnowledge ? (
        <section className="grid gap-4 border-t border-[#E7ECF1] pt-6" data-testid="role-card-profile-knowledge">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className={roleSectionTitleClass}>知识库 · {entries.length}</h3>
              <p className={roleSectionDescriptionClass}>随角色卡导入的 Lorebook 条目。</p>
            </div>
            <div className="flex shrink-0 items-center gap-2.5 pt-0.5">
              <span className={knowledge.enabled === true ? "text-xs text-[#2E7D5B]" : "text-xs text-[#7B8794]"}>{knowledge.enabled === true ? "已启用" : "未启用"}</span>
              <SettingsToggleCard compact checked={knowledge.enabled === true} ariaLabel="启用知识库" onChange={(checked) => onUpdate({ ...profile, knowledge_base: { ...knowledge, enabled: checked } })} />
            </div>
          </div>
          <label className="grid max-w-48 gap-1.5 text-xs text-[#667085]">
            <span>Token 预算</span>
            <input className={roleFieldClass} type="number" min={0} value={knowledge.token_budget ?? 2000} onChange={(event) => onUpdate({ ...profile, knowledge_base: { ...knowledge, token_budget: Number(event.target.value) || 0 } })} />
          </label>
          {entries.length ? (
            <div className="grid gap-0">
              {entries.map((entry, index) => (
                <div className="grid gap-2 border-b border-[#EEF2F5] py-3 text-xs last:border-b-0" key={entry.id ?? index}>
                  <p className="whitespace-pre-wrap leading-5 text-[#475467]">{entry.content || "空条目"}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {(entry.primary_keys ?? entry.keywords ?? []).length
                      ? (entry.primary_keys ?? entry.keywords ?? []).map((keyword) => <span className={roleChipClass} key={keyword}>{keyword}</span>)
                      : <span className="text-[11px] text-[#98A2B3]">未设置关键词</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : <p className="text-xs text-[#98A2B3]">无条目</p>}
        </section>
      ) : null}
    </div>
  );
}
