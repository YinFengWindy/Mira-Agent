import { useEffect } from "react";

import { CloseIcon, DocumentIcon } from "../shared/icons";
import type { RoleCardImportPreview } from "../shared/types";

type RoleCardImportPreviewDialogProps = {
  open: boolean;
  preview: RoleCardImportPreview;
  sourceUrl: string;
  onClose: () => void;
  onCancel: () => void;
};

function fieldList(values: string[] | undefined): string {
  return values?.filter(Boolean).join("、") || "无";
}

function assetLabel(kind: string | undefined): string {
  if (kind === "avatar") return "头像";
  if (kind === "background") return "背景";
  if (kind === "emotion") return "心情";
  return "素材";
}

function reportSection(title: string, values: string[] | undefined) {
  if (!values?.length) return null;
  return (
    <section className="grid gap-2 rounded-md border border-[#E3E8EE] bg-white p-3" key={title}>
      <h4 className="text-xs font-medium text-[#344054]">{title}</h4>
      <ul className="grid gap-1 text-xs leading-5 text-[#667085]">
        {values.map((value) => <li key={value}>{value}</li>)}
      </ul>
    </section>
  );
}

/** Displays a scrollable staged-card inspection dialog before creation. */
export function RoleCardImportPreviewDialog({
  open,
  preview,
  sourceUrl,
  onClose,
  onCancel,
}: RoleCardImportPreviewDialogProps) {
  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [onClose, open]);

  if (!open) return null;

  const character = preview.profile?.character;
  const greetings = preview.profile?.greetings;
  const knowledge = preview.profile?.knowledge_base;
  const assets = (preview.assets ?? []).filter((asset) => asset.size !== undefined);
  const entries = knowledge?.entries ?? [];

  return (
    <div className="role-card-import-dialog fixed inset-0 z-40 flex items-center justify-center px-4 py-6">
      <button className="absolute inset-0 border-0 bg-[rgba(15,23,42,0.34)] p-0 backdrop-blur-[6px]" type="button" aria-label="关闭角色卡预览" onClick={onClose} />
      <section className="relative z-[1] grid max-h-[min(88vh,960px)] w-full max-w-[1080px] grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden rounded-md bg-white shadow-[0_28px_80px_rgba(15,23,42,0.18)]" role="dialog" aria-modal="true" aria-label="角色卡导入预览" data-testid="role-card-import-preview">
        <header className="flex items-start justify-between gap-4 border-b border-[#E3E8EE] px-5 py-4">
          <div className="flex min-w-0 items-center gap-3">
            {sourceUrl ? (
              <img className="h-16 w-16 shrink-0 rounded-md border border-[#D8E1EB] object-cover" src={sourceUrl} alt={`${preview.name ?? "角色卡"}预览`} />
            ) : (
              <div className="grid h-16 w-16 shrink-0 place-items-center rounded-md border border-[#D8E1EB] bg-white text-[#667085]">
                <DocumentIcon className="h-6 w-6 stroke-current" />
              </div>
            )}
            <div className="min-w-0">
              <h3 className="truncate text-base font-medium text-[#101828]">{preview.name || "未命名角色"}</h3>
              <p className="mt-1 text-xs text-[#667085]">{[preview.provenance?.format, preview.provenance?.card_version].filter(Boolean).join(" · ") || "角色卡"}</p>
            </div>
          </div>
          <button className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-[#667085] transition hover:bg-[#F2F4F7] hover:text-[#344054] focus:outline-none" type="button" onClick={onClose} aria-label="关闭角色卡预览" title="关闭角色卡预览">
            <CloseIcon className="h-4 w-4 stroke-current" />
          </button>
        </header>

        <div className="role-card-import-dialog-content scrollbar-soft min-h-0 overflow-y-auto p-5">
          <div className="grid gap-4">
            <div className="grid gap-3 lg:grid-cols-2">
              <section className="grid gap-2 rounded-md border border-[#E3E8EE] bg-white p-3">
                <h4 className="text-xs font-medium text-[#344054]">角色资料</h4>
                <dl className="grid gap-2 text-xs leading-5 text-[#667085]">
                  <div><dt className="text-[#98A2B3]">资料</dt><dd className="max-h-64 overflow-y-auto whitespace-pre-wrap text-[#475467]">{character?.profile || preview.description || "无"}</dd></div>
                  <div><dt className="text-[#98A2B3]">性格</dt><dd className="whitespace-pre-wrap text-[#475467]">{character?.personality || "无"}</dd></div>
                  <div><dt className="text-[#98A2B3]">规则</dt><dd className="whitespace-pre-wrap text-[#475467]">{character?.behavior_rules || "无"}</dd></div>
                </dl>
              </section>
              <section className="grid gap-2 rounded-md border border-[#E3E8EE] bg-white p-3">
                <h4 className="text-xs font-medium text-[#344054]">开场白</h4>
                <p className="max-h-64 overflow-y-auto whitespace-pre-wrap text-xs leading-5 text-[#475467]">{greetings?.default || "无"}</p>
                <p className="text-xs leading-5 text-[#667085]">备用：{fieldList(greetings?.alternates)}</p>
              </section>
            </div>

            <section className="grid gap-2 rounded-md border border-[#E3E8EE] bg-white p-3">
              <h4 className="text-xs font-medium text-[#344054]">知识库 · {entries.length}</h4>
              {entries.length ? (
                <div className="grid gap-2 md:grid-cols-2">
                  {entries.map((entry, index) => (
                    <div className="rounded-md bg-[#F8FAFC] p-2 text-xs" key={entry.id ?? index}>
                      <p className="whitespace-pre-wrap text-[#475467]">{entry.content || "空条目"}</p>
                      <p className="mt-1 text-[#98A2B3]">{fieldList(entry.primary_keys ?? entry.keywords)}</p>
                    </div>
                  ))}
                </div>
              ) : <p className="text-xs text-[#98A2B3]">无</p>}
            </section>

            <section className="grid gap-2 rounded-md border border-[#E3E8EE] bg-white p-3">
              <h4 className="text-xs font-medium text-[#344054]">素材 · {assets.length}</h4>
              {assets.length ? <ul className="flex flex-wrap gap-2">{assets.map((asset, index) => <li className="rounded-md border border-[#E3E8EE] bg-[#F8FAFC] px-2 py-1 text-xs text-[#667085]" key={`${asset.kind ?? "asset"}-${asset.path ?? index}`}>{assetLabel(asset.kind)}{asset.name ? ` · ${asset.name}` : ""}</li>)}</ul> : <p className="text-xs text-[#98A2B3]">无</p>}
            </section>

            <div className="grid gap-3 lg:grid-cols-2">
              {reportSection("已适配", preview.report?.adapted_fields)}
              {reportSection("已舍弃", preview.report?.discarded_fields)}
              {reportSection("未支持的宏", preview.report?.unsupported_macros)}
              {reportSection("未支持的资源与规则", [...(preview.report?.unsupported_resources ?? []), ...(preview.report?.unsupported_rules ?? [])])}
            </div>
          </div>
        </div>

        <footer className="flex justify-end gap-2 border-t border-[#E3E8EE] px-5 py-3">
          <button className="rounded-md border border-[#D8DFE7] bg-white px-3 py-2 text-sm text-[#344054] transition hover:bg-[#F8FAFC] focus:outline-none" type="button" onClick={onCancel}>取消导入</button>
          <button className="rounded-md bg-[#1F2937] px-3 py-2 text-sm text-white transition hover:bg-[#344054] focus:outline-none" type="button" onClick={onClose}>继续编辑</button>
        </footer>
      </section>
    </div>
  );
}
