import type React from "react";
import type { NewRoleFormState } from "../shared/types";
import { RoleAvatarPicker } from "./RoleAvatarPicker";
import { RoleCardProfileForm } from "./RoleCardProfileForm";
import { roleFieldClass, roleFieldLabelClass, roleIdentityInputClass } from "./roleEditorStyles";
import { cx } from "../shared/styles";

/** Shared editable role identity for regular creation and first-run setup; mirrors the role-detail layout. */
export function RoleCreateFields({ form, disabled, importedAvatar, onUpdateForm }: {
  form: NewRoleFormState;
  disabled: boolean;
  importedAvatar: string;
  onUpdateForm: React.Dispatch<React.SetStateAction<NewRoleFormState>>;
}) {
  return (
    <fieldset disabled={disabled} className="grid min-w-0 gap-7">
      <div className="grid gap-6 border-b border-line-soft pb-7 sm:grid-cols-[112px_minmax(0,1fr)]">
        <RoleAvatarPicker source={form.avatarSource ?? importedAvatar} disabled={disabled}
          onChange={(avatarSource) => onUpdateForm((current) => ({ ...current, avatarSource }))} />
        <div className="grid content-center gap-2">
          <input data-testid="new-role-name" aria-label="角色名称"
            className={cx(roleIdentityInputClass, "text-2xl font-semibold text-ink placeholder:text-ink-faint")}
            value={form.name} placeholder="未命名角色"
            onChange={(event) => onUpdateForm((current) => ({ ...current, name: event.target.value }))} />
          <input data-testid="new-role-description" aria-label="角色简介"
            className={cx(roleIdentityInputClass, "text-sm leading-6 text-ink-muted placeholder:text-ink-faint")}
            value={form.description} placeholder="添加一行角色简介"
            onChange={(event) => onUpdateForm((current) => ({ ...current, description: event.target.value }))} />
        </div>
      </div>
      {form.profile ? <RoleCardProfileForm collapseDetails profile={form.profile} onUpdate={(profile) => onUpdateForm((current) => ({ ...current, profile }))} /> : (
        <label className={roleFieldLabelClass}>
          <span>角色设定</span>
          <textarea aria-label="角色设定" data-testid="new-role-prompt" className={cx(roleFieldClass, "scrollbar-soft h-40 resize-y leading-6")}
            value={form.systemPrompt} placeholder="角色的性格、语气与行为"
            onChange={(event) => onUpdateForm((current) => ({ ...current, systemPrompt: event.target.value }))} />
        </label>
      )}
    </fieldset>
  );
}
