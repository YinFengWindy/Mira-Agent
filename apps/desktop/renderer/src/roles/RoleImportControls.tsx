import { useEffect, useState } from "react";
import { FileText, UploadSimple } from "@phosphor-icons/react";
import type React from "react";
import type { RoleCardImportState } from "../app/roleCardImportState";
import type { NewRoleFormState } from "../shared/types";
import { RoleCardImportPreviewDialog } from "./RoleCardImportPreview";
import { selectRoleCreateState } from "./roleCreateSelectors";

/** Shares import actions and preview/asset choices across both creation screens. */
export function RoleImportControls({ imported, form, disabled, onImport, onCancel, onUpdateForm }: {
  imported: RoleCardImportState;
  form: NewRoleFormState;
  disabled: boolean;
  onImport: () => void;
  onCancel: () => void;
  onUpdateForm: React.Dispatch<React.SetStateAction<NewRoleFormState>>;
}) {
  const [open, setOpen] = useState(false);
  const previewId = imported.preview?.import_id;
  useEffect(() => { if (previewId) setOpen(true); }, [previewId]);
  const { previewImagePath } = selectRoleCreateState(form, imported);
  return (
    <div className="flex items-center gap-2">
      <button type="button" data-testid="import-role-card-button" disabled={disabled || imported.status !== "idle"}
        onClick={onImport} className="inline-flex min-h-9 items-center gap-2 rounded-md px-3 text-sm text-[#52606D] hover:bg-[#F3F6FA] disabled:opacity-50">
        <UploadSimple size={18} />{imported.status === "previewing" ? "正在导入角色" : "导入角色"}
      </button>
      {imported.preview ? <>
        <button type="button" aria-label="查看角色卡预览" title="查看角色卡预览" disabled={disabled}
          onClick={() => setOpen(true)} className="grid h-9 w-9 place-items-center rounded-md hover:bg-[#F3F6FA]"><FileText size={18} /></button>
        <RoleCardImportPreviewDialog open={open} preview={imported.preview} selections={form.emotionSelections ?? {}}
          onSelectEmotion={(name, assetId) => onUpdateForm((current) => ({ ...current, emotionSelections: { ...current.emotionSelections, [name]: assetId } }))}
          sourceUrl={previewImagePath ? window.miraDesktop.localAssetUrl(previewImagePath) : ""}
          onClose={() => setOpen(false)} onCancel={() => { setOpen(false); onCancel(); }} />
      </> : null}
    </div>
  );
}
