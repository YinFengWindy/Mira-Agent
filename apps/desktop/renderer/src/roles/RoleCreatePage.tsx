import { BackIcon, ResetIcon, SaveIcon } from "../shared/icons";
import { cx, iconButtonClass } from "../shared/styles";
import type { NewRoleFormState } from "../shared/types";
import type { RoleCardImportState } from "../app/roleCardImportState";
import { RoleCreateFields } from "./RoleCreateFields";
import { RoleImportControls } from "./RoleImportControls";
import { selectRoleCreateState } from "./roleCreateSelectors";

type RoleCreatePageProps = {
  bridgeReady: boolean;
  creating: boolean;
  form: NewRoleFormState;
  onBackToList: () => void;
  onCreateRole: () => void;
  onResetForm: () => void;
  onUpdateForm: React.Dispatch<React.SetStateAction<NewRoleFormState>>;
  roleCardImport: RoleCardImportState;
  onPreviewRoleCard: () => void;
  onCancelRoleCardImport: () => void;
};

const actionClass = iconButtonClass;

/** Renders regular role creation using the same identity and import editors as onboarding. */
export function RoleCreatePage({ bridgeReady, creating, form, onBackToList, onCreateRole, onResetForm,
  onUpdateForm, roleCardImport, onPreviewRoleCard, onCancelRoleCardImport }: RoleCreatePageProps) {
  const { formDirty, needsEmotionChoice, previewImagePath } = selectRoleCreateState(form, roleCardImport);
  return (
    <section className="role-create-page scrollbar-soft relative h-full overflow-y-auto bg-white" data-testid="role-create-page">
      <div className="mx-auto flex min-h-full w-full max-w-[1120px] flex-col px-5 pb-8 pt-6 sm:px-8">
        <div className="mb-7 flex items-center justify-between gap-3 border-b border-[#E5E7EB] pb-4">
          <button className={actionClass} type="button" onClick={onBackToList} disabled={creating} aria-label="返回角色列表" title="返回角色列表"><BackIcon className="h-5 w-5 fill-current" /></button>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <RoleImportControls imported={roleCardImport} form={form} disabled={creating || !bridgeReady}
              onImport={onPreviewRoleCard} onCancel={onCancelRoleCardImport} onUpdateForm={onUpdateForm} />
            <button className={actionClass} type="button" onClick={onResetForm} disabled={creating || !formDirty} aria-label="重置新建角色表单" title="重置新建角色表单"><ResetIcon className="h-[18px] w-[18px] fill-current" /></button>
            <button data-testid="create-role-button" className={cx(actionClass, "bg-[#F0F7F4]")} type="button" onClick={onCreateRole}
              disabled={creating || !bridgeReady || roleCardImport.status === "previewing" || needsEmotionChoice} aria-label={creating ? "正在创建角色" : "创建角色"} title="创建角色"><SaveIcon className="h-5 w-5 fill-current" /></button>
          </div>
        </div>
        <RoleCreateFields form={form} disabled={creating || roleCardImport.status === "previewing"} importedAvatar={previewImagePath} onUpdateForm={onUpdateForm} />
      </div>
    </section>
  );
}
