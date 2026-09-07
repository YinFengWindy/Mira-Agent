import { BookOpenText, CaretDown } from "@phosphor-icons/react";
import { useState } from "react";
import { SettingsToggleCard } from "../settings/SettingsToggleCard";
import { cx } from "../shared/styles";
import type { RoleKnowledgeBase, RoleKnowledgeEntry, RoleRecord } from "../shared/types";
import {
  roleChipClass,
  roleFieldClass,
  rolePanelPrimaryButtonClass,
  roleSectionDescriptionClass,
  roleSectionTitleClass,
} from "./roleEditorStyles";

type KnowledgeEntryRowProps = {
  entry: RoleKnowledgeEntry;
  index: number;
  expanded: boolean;
  onToggle: () => void;
};

/** One collapsible Lorebook entry with its keyword chips. */
function KnowledgeEntryRow({ entry, index, expanded, onToggle }: KnowledgeEntryRowProps) {
  const keywords = entry.primary_keys ?? entry.keywords ?? [];

  return (
    <div className="border-b border-[#EEF2F5] last:border-b-0">
      <button
        className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 py-3 text-left focus:outline-none"
        type="button"
        aria-expanded={expanded}
        onClick={onToggle}
      >
        <span className="grid min-w-0 gap-1.5">
          <span className="truncate text-sm font-medium text-[#182230]">{entry.name || entry.id || `条目 ${index + 1}`}</span>
          <span className="flex flex-wrap gap-1.5">
            {keywords.length
              ? keywords.map((keyword) => <span className={roleChipClass} key={keyword}>{keyword}</span>)
              : <span className="text-[11px] leading-4 text-[#98A2B3]">未设置关键词</span>}
          </span>
        </span>
        <CaretDown className={cx("h-4 w-4 shrink-0 text-[#98A2B3] transition-transform", expanded && "rotate-180")} weight="bold" />
      </button>
      {expanded ? (
        <p className="whitespace-pre-wrap pb-4 text-xs leading-5 text-[#4B5563]">{entry.content || "空条目"}</p>
      ) : null}
    </div>
  );
}

export function RoleKnowledgePanel({ activeRole, bridgeReady }: { activeRole: RoleRecord | null; bridgeReady: boolean }) {
  const initial = activeRole?.profile?.knowledge_base ?? {};
  const [draft, setDraft] = useState<RoleKnowledgeBase>(initial);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ text: string; error: boolean } | null>(null);
  const [expandedEntries, setExpandedEntries] = useState<ReadonlySet<number>>(new Set());
  const entries = draft.entries ?? [];
  const enabled = draft.enabled !== false;

  async function save(): Promise<void> {
    if (!activeRole) return;
    setSaving(true);
    setFeedback(null);
    const response = await window.miraDesktop.invoke({
      method: "roles.update",
      payload: { role_id: activeRole.id, profile: { knowledge_base: draft } },
    });
    setSaving(false);
    setFeedback(response.error ? { text: response.error.message, error: true } : { text: "知识库已保存", error: false });
  }

  function toggleEntry(index: number): void {
    setExpandedEntries((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  return (
    <div className="grid gap-6" data-testid="role-knowledge-panel">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#F0F5FB] text-[#4B6B88]" aria-hidden="true">
            <BookOpenText className="h-5 w-5" weight="duotone" />
          </span>
          <div>
            <h2 className={roleSectionTitleClass}>知识库</h2>
            <p className={roleSectionDescriptionClass}>导入的 Lorebook 条目会在运行时按关键词匹配。</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3 pt-0.5">
          {feedback ? <span className={feedback.error ? "text-xs text-[#B54747]" : "text-xs text-[#2E7D5B]"}>{feedback.text}</span> : null}
          <button type="button" className={rolePanelPrimaryButtonClass} disabled={!bridgeReady || saving} onClick={() => void save()}>{saving ? "保存中" : "保存"}</button>
        </div>
      </div>

      <div className="grid gap-4 border-y border-[#E7ECF1] py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-medium text-[#182230]">启用知识库</h3>
            <p className={roleSectionDescriptionClass}>{enabled ? "对话时会按关键词注入匹配条目。" : "关闭后条目保留，但不参与对话。"}</p>
          </div>
          <SettingsToggleCard checked={enabled} ariaLabel="启用知识库" onChange={(checked) => setDraft((current) => ({ ...current, enabled: checked }))} />
        </div>
        <label className="grid max-w-48 gap-1.5 text-xs text-[#667085]">
          <span>Token 预算</span>
          <input className={roleFieldClass} type="number" min={0} value={draft.token_budget ?? 1200} onChange={(event) => setDraft((current) => ({ ...current, token_budget: Number(event.target.value) || 0 }))} />
        </label>
      </div>

      <div className="grid gap-1">
        <h3 className="text-sm font-medium text-[#182230]">条目 · {entries.length}</h3>
        {entries.length ? (
          <div>
            {entries.map((entry, index) => (
              <KnowledgeEntryRow entry={entry} index={index} expanded={expandedEntries.has(index)} onToggle={() => toggleEntry(index)} key={entry.id ?? index} />
            ))}
          </div>
        ) : (
          <div className="mt-2 grid justify-items-center gap-2 border-y border-dashed border-[#DDE5EC] py-8 text-center">
            <BookOpenText className="h-6 w-6 text-[#C3CDD7]" weight="duotone" aria-hidden="true" />
            <p className="text-xs text-[#7B8794]">当前没有知识库条目</p>
            <p className="text-[11px] text-[#98A2B3]">导入角色卡时会自动带入 Lorebook 条目。</p>
          </div>
        )}
      </div>
    </div>
  );
}
