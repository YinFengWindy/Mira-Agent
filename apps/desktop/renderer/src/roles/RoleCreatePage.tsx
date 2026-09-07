import { useEffect, useState } from "react";
import { BackIcon, DocumentIcon, ResetIcon, SaveIcon, UploadIcon } from "../shared/icons";
import { cx } from "../shared/styles";
import type { NewRoleFormState } from "../shared/types";
import type { RoleCardImportState } from "../app/useRoleCreationController";
import { RoleCardImportPreviewDialog } from "./RoleCardImportPreview";
import { RoleCardProfileForm } from "./RoleCardProfileForm";
import {
  roleFieldClass,
  roleFieldLabelClass,
  roleSectionDescriptionClass,
  roleSectionTitleClass,
} from "./roleEditorStyles";

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

const floatingActionClass = "grid h-10 w-10 shrink-0 place-items-center rounded-full border border-[#E5E7EB] bg-white text-[#1F2937] shadow-[0_6px_16px_rgba(15,23,42,0.08)] transition hover:border-[#CBD5E1] hover:bg-[#F8FAFC] disabled:cursor-not-allowed disabled:border-[#E5E7EB] disabled:bg-[#F3F4F6] disabled:text-[#9CA3AF] disabled:opacity-100 disabled:shadow-none";

/** Renders the standalone create-role subpage inside role management. */
export function RoleCreatePage({
  bridgeReady,
  creating,
  form,
  onBackToList,
  onCreateRole,
  onResetForm,
  onUpdateForm,
  roleCardImport,
  onPreviewRoleCard,
  onCancelRoleCardImport,
}: RoleCreatePageProps) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const profileDirty = Boolean(
    form.profile?.character?.profile?.trim()
    || form.profile?.character?.personality?.trim()
    || form.profile?.character?.behavior_rules?.trim()
    || form.profile?.knowledge_base?.entries?.length,
  );
  const formDirty = Boolean(
    form.name.trim() || form.description.trim() || form.systemPrompt.trim() || profileDirty,
  );

  useEffect(() => {
    if (roleCardImport.preview) setPreviewOpen(true);
  }, [roleCardImport.preview?.import_id]);

  return (
    <section
      className="role-create-page scrollbar-soft scrollbar-soft-accent relative h-full overflow-y-auto bg-white"
      data-testid="role-create-page"
    >
      <div className="relative mx-auto flex min-h-full w-full max-w-[1120px] flex-col px-5 pb-8 pt-6 sm:px-8">
        <div className="mb-7 flex items-center justify-between gap-3 border-b border-[#E5E7EB] pb-4">
          <button
            className={cx(floatingActionClass, "hover:-translate-x-0.5")}
            type="button"
            onClick={onBackToList}
            aria-label="返回角色列表"
          >
            <BackIcon className="h-5 w-5 fill-current" />
          </button>
          <div className="flex items-center gap-2">
            <button
              data-testid="import-role-card-button"
              className={cx(floatingActionClass, "w-auto grid-cols-[18px_auto] gap-1.5 px-3.5 text-sm text-[#4B5563]")}
              type="button"
              onClick={onPreviewRoleCard}
              disabled={roleCardImport.status !== "idle" || !bridgeReady}
              aria-label={roleCardImport.status === "previewing" ? "正在导入角色" : "导入角色"}
            >
              <UploadIcon className="h-[18px] w-[18px] fill-current" />
              <span>导入角色</span>
            </button>
            {roleCardImport.preview ? (
              <button
                className={floatingActionClass}
                type="button"
                onClick={() => setPreviewOpen(true)}
                aria-label="查看角色卡预览"
                title="查看角色卡预览"
              >
                <DocumentIcon className="h-[18px] w-[18px] stroke-current" />
              </button>
            ) : null}
            <button
              className={floatingActionClass}
              type="button"
              onClick={onResetForm}
              disabled={!formDirty}
              aria-label="重置新建角色表单"
            >
              <ResetIcon className="h-[18px] w-[18px] fill-current" />
            </button>
            <button
              data-testid="create-role-button"
              className={cx(floatingActionClass, "bg-[#fff7f0] hover:shadow-[0_10px_28px_rgba(255,217,184,0.32)]")}
              type="button"
              onClick={onCreateRole}
              disabled={creating || !bridgeReady}
              aria-label={creating ? "正在创建角色" : "创建角色"}
            >
              <SaveIcon className="h-5 w-5 fill-current" />
            </button>
          </div>
        </div>
        <div className="grid gap-7">
          <section className="grid gap-4">
            <div>
              <h2 className={roleSectionTitleClass}>基本信息</h2>
              <p className={roleSectionDescriptionClass}>为角色取名，并用一句话介绍它。</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-[minmax(0,240px)_minmax(0,1fr)]">
              <label className={roleFieldLabelClass}>
                <span>名称</span>
                <input
                  data-testid="new-role-name"
                  className={roleFieldClass}
                  value={form.name}
                  onChange={(event) => onUpdateForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="输入角色名称"
                />
              </label>
              <label className={roleFieldLabelClass}>
                <span>简介</span>
                <input
                  data-testid="new-role-description"
                  className={roleFieldClass}
                  value={form.description}
                  onChange={(event) => onUpdateForm((current) => ({ ...current, description: event.target.value }))}
                  placeholder="简短描述这个角色"
                />
              </label>
            </div>
          </section>
          {!form.profile ? (
            <section className="grid gap-4 border-t border-[#E7ECF1] pt-6">
              <div>
                <h2 className={roleSectionTitleClass}>系统提示词</h2>
                <p className={roleSectionDescriptionClass}>定义这个角色的行为、语气和边界；导入角色卡后会替换为结构化资料。</p>
              </div>
              <textarea
                aria-label="系统提示词"
                data-testid="new-role-prompt"
                className={cx(roleFieldClass, "scrollbar-soft h-40 resize-none overflow-y-auto leading-6")}
                value={form.systemPrompt}
                onChange={(event) => onUpdateForm((current) => ({ ...current, systemPrompt: event.target.value }))}
                placeholder="定义这个角色的行为、语气和边界"
              />
            </section>
          ) : (
            <div className="border-t border-[#E7ECF1] pt-6">
              <RoleCardProfileForm
                profile={form.profile}
                onUpdate={(profile) => onUpdateForm((current) => ({ ...current, profile }))}
              />
            </div>
          )}
        </div>
      </div>
      {roleCardImport.preview ? (
        <RoleCardImportPreviewDialog
          open={previewOpen}
          preview={roleCardImport.preview}
          sourceUrl={roleCardImport.source ? window.miraDesktop.localAssetUrl(roleCardImport.source) : ""}
          onClose={() => setPreviewOpen(false)}
          onCancel={() => {
            setPreviewOpen(false);
            onCancelRoleCardImport();
          }}
        />
      ) : null}
    </section>
  );
}
