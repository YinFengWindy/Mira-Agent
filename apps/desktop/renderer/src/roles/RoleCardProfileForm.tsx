import { cx } from "../shared/styles";
import type { RoleProfileDraft } from "../shared/types";
import { roleFieldClass } from "./roleEditorStyles";

type RoleCardProfileFormProps = {
  profile: RoleProfileDraft;
  onUpdate: (next: RoleProfileDraft) => void;
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

/** Edits structured character fields; the knowledge base is managed in the detail tab. */
export function RoleCardProfileForm({
  profile,
  onUpdate,
}: RoleCardProfileFormProps) {
  const character = profile.character ?? {};

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
    </div>
  );
}
