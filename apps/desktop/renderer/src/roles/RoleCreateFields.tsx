import type React from "react";
import type { NewRoleFormState } from "../shared/types";
import { RoleAvatarPicker } from "./RoleAvatarPicker";
import { RoleCardProfileForm } from "./RoleCardProfileForm";
import { roleFieldClass, roleFieldLabelClass } from "./roleEditorStyles";
import { cx } from "../shared/styles";

/** Shared editable role identity for regular creation and first-run setup. */
export function RoleCreateFields({ form, disabled, importedAvatar, onUpdateForm }: {
  form: NewRoleFormState;
  disabled: boolean;
  importedAvatar: string;
  onUpdateForm: React.Dispatch<React.SetStateAction<NewRoleFormState>>;
}) {
  const inputClass = roleFieldClass;
  return (
    <fieldset disabled={disabled} className="grid min-w-0 gap-6">
      <RoleAvatarPicker source={form.avatarSource ?? importedAvatar} disabled={disabled}
        onChange={(avatarSource) => onUpdateForm((current) => ({ ...current, avatarSource }))} />
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <label className={roleFieldLabelClass}>
          <span>名称</span>
          <input data-testid="new-role-name" className={inputClass} value={form.name} placeholder="输入角色名称"
            onChange={(event) => onUpdateForm((current) => ({ ...current, name: event.target.value }))} />
        </label>
        <label className={roleFieldLabelClass}>
          <span>简介</span>
          <input data-testid="new-role-description" className={inputClass} value={form.description} placeholder="简短描述这个角色"
            onChange={(event) => onUpdateForm((current) => ({ ...current, description: event.target.value }))} />
        </label>
      </div>
      {form.profile ? <RoleCardProfileForm collapseDetails profile={form.profile} onUpdate={(profile) => onUpdateForm((current) => ({ ...current, profile }))} /> : (
        <label className={roleFieldLabelClass}>
          <span>角色设定</span>
          <textarea aria-label="角色设定" data-testid="new-role-prompt" className={cx(inputClass, "scrollbar-soft h-40 resize-y leading-6")}
            value={form.systemPrompt} placeholder="角色的性格、语气与行为"
            onChange={(event) => onUpdateForm((current) => ({ ...current, systemPrompt: event.target.value }))} />
        </label>
      )}
    </fieldset>
  );
}
