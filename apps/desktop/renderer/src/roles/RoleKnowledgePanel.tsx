import { useState } from "react";
import type { RoleKnowledgeBase, RoleRecord } from "../shared/types";

export function RoleKnowledgePanel({ activeRole, bridgeReady }: { activeRole: RoleRecord | null; bridgeReady: boolean }) {
  const initial = activeRole?.profile?.knowledge_base ?? {};
  const [draft, setDraft] = useState<RoleKnowledgeBase>(initial);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState("");

  async function save(): Promise<void> {
    if (!activeRole) return;
    setSaving(true);
    setFeedback("");
    const response = await window.miraDesktop.invoke({
      method: "roles.update",
      payload: { role_id: activeRole.id, profile: { knowledge_base: draft } },
    });
    setSaving(false);
    setFeedback(response.error ? response.error.message : "知识库已保存");
  }

  return (
    <div className="grid gap-5" data-testid="role-knowledge-panel">
      <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-4">
        <div><h2 className="text-base font-medium text-[#111827]">知识库</h2><p className="mt-1 text-xs text-[#6B7280]">导入的 Lorebook 条目会在运行时按关键词匹配。</p></div>
        <button type="button" className="rounded-md border border-[#D8DCE2] px-3 py-2 text-xs text-[#374151] disabled:opacity-50" disabled={!bridgeReady || saving} onClick={() => void save()}>保存</button>
      </div>
      <label className="flex items-center gap-2 text-sm text-[#374151]"><input type="checkbox" checked={draft.enabled !== false} onChange={(event) => setDraft((current) => ({ ...current, enabled: event.target.checked }))} />启用知识库</label>
      <label className="grid max-w-[240px] gap-1 text-xs text-[#6B7280]">Token 预算<input className="rounded-md border border-[#D8DCE2] px-3 py-2 text-sm text-[#111827]" type="number" min={0} value={draft.token_budget ?? 1200} onChange={(event) => setDraft((current) => ({ ...current, token_budget: Number(event.target.value) || 0 }))} /></label>
      <div className="grid gap-2">
        {(draft.entries ?? []).map((entry, index) => <div className="grid gap-1 rounded-md border border-[#E5E7EB] p-3 text-xs" key={entry.id ?? index}><span className="font-medium text-[#111827]">{entry.name || entry.id || `条目 ${index + 1}`}</span><span className="text-[#6B7280]">关键词：{(entry.keywords ?? []).join("、") || "未设置"}</span><span className="whitespace-pre-wrap text-[#4B5563]">{entry.content || "空条目"}</span></div>)}
        {!draft.entries?.length ? <p className="text-sm text-[#6B7280]">当前没有知识库条目。</p> : null}
      </div>
      {feedback ? <p className="text-xs text-[#6B7280]">{feedback}</p> : null}
    </div>
  );
}
