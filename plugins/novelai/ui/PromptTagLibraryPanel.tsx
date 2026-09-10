import { useCallback, useEffect, useState } from "react";
import { toFileUrl } from "../../../apps/desktop/renderer/src/shared/format";
import { DeleteIcon, PromptLibraryIcon } from "../../../apps/desktop/renderer/src/shared/icons";
import type { PluginRpcClient } from "../../../apps/desktop/renderer/src/plugins/pluginBridgeClient";
import { PromptTagEntryEditor, type PromptTagDraft } from "./PromptTagEntryEditor";
import type { PromptTagWorkspaceSectionId } from "./PromptTagWorkspaceSidebar";
import type { PromptTagEntry } from "./types";

type PromptTagLibraryPanelProps = {
  client: PluginRpcClient;
  bridgeReady: boolean;
  section: PromptTagWorkspaceSectionId;
  onOpenSection: (section: PromptTagWorkspaceSectionId) => void;
};
const emptyDraft: PromptTagDraft = { id: "", name: "", enabled: true, category: "composition", match_terms: [], positive_tags: [], negative_tags: [], rating: "general", image_path: "" };
function draftSignature(draft: PromptTagDraft): string { return JSON.stringify({ id: draft.id.trim(), name: draft.name.trim(), enabled: draft.enabled, category: draft.category.trim(), match_terms: draft.match_terms, positive_tags: draft.positive_tags, negative_tags: draft.negative_tags, rating: draft.rating, image_path: draft.image_path }); }

/** Manages prompt-tag workspace data and routes between its list and editor views. */
export function PromptTagLibraryPanel({ client, bridgeReady, section, onOpenSection }: PromptTagLibraryPanelProps) {
  const [entries, setEntries] = useState<PromptTagEntry[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [draft, setDraft] = useState<PromptTagDraft>(emptyDraft);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const loadEntries = useCallback(async (): Promise<void> => {
    try {
      const payload = await client.call<{ entries: PromptTagEntry[] }>("prompt_tags.list", {});
      const nextEntries = Array.isArray(payload.entries) ? payload.entries : [];
      setEntries(nextEntries);
      if (!isCreating && selectedId) {
        const selected = nextEntries.find((entry) => entry.id === selectedId);
        if (selected) setDraft(selected);
      }
      setError("");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    }
  }, [client, isCreating, selectedId]);
  useEffect(() => { if (bridgeReady) void loadEntries(); }, [bridgeReady, loadEntries]);
  useEffect(() => { if (section !== "create") return; setDraft(emptyDraft); setSelectedId(""); setIsCreating(true); setError(""); }, [section]);
  const originalDraft = selectedId ? entries.find((entry) => entry.id === selectedId) ?? emptyDraft : emptyDraft;
  const dirty = draftSignature(draft) !== draftSignature(originalDraft);
  async function saveEntry(): Promise<void> {
    const payload = { ...draft, id: draft.id.trim(), name: draft.name.trim(), category: draft.category.trim() };
    if (!payload.id || !payload.name || !payload.category || !payload.match_terms.length || !payload.positive_tags.length) { setError("ID、名称、分类、匹配词和正向 tag 不能为空"); return; }
    setSaving(true);
    setError("");
    try {
      await client.call("prompt_tags.upsert", payload);
      setSelectedId(payload.id);
      setIsCreating(false);
      onOpenSection("detail");
      await loadEntries();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : String(saveError));
    } finally { setSaving(false); }
  }
  async function deleteEntry(id: string): Promise<void> {
    try {
      await client.call("prompt_tags.delete", { id });
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : String(deleteError));
      return;
    }
    if (selectedId === id) { setSelectedId(""); setDraft(emptyDraft); setIsCreating(false); onOpenSection("list"); }
    await loadEntries();
  }
  function openEntry(entry: PromptTagEntry): void { setDraft(entry); setSelectedId(entry.id); setIsCreating(false); setError(""); onOpenSection("detail"); }
  return <section className="scrollbar-soft h-full overflow-y-auto bg-gradient-app bg-fixed p-8" data-testid="prompt-tag-library">
    {section === "list" ? <div className="mx-auto grid w-full max-w-[1120px] grid-cols-3 gap-5">{entries.map((entry) => <div className="group relative h-[420px] overflow-hidden rounded-xl border border-line-soft bg-surface-soft shadow-pop transition hover:-translate-y-0.5 hover:shadow-pop" key={entry.id}><button className="h-full w-full" type="button" title={entry.name} onClick={() => openEntry(entry)}>{entry.image_path ? <img className="h-full w-full object-cover" src={toFileUrl(entry.image_path)} alt={entry.name} /> : <span className="grid h-full place-items-center text-ink-faint"><PromptLibraryIcon className="h-12 w-12 fill-current" /></span>}</button><div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 via-black/25 to-transparent px-5 pb-5 pt-14 text-white"><div className="truncate text-[22px] font-semibold leading-none">{entry.name}</div><div className="mt-2 line-clamp-2 text-sm leading-6 text-white/75">{entry.category}</div></div><button className="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-full border border-white/24 bg-[rgba(15,23,42,0.62)] text-white opacity-0 transition hover:bg-danger group-hover:opacity-100" type="button" aria-label={`删除 ${entry.name}`} onClick={() => void deleteEntry(entry.id)}><DeleteIcon className="h-[15px] w-[15px] fill-current" /></button></div>)}</div> : <div className="mx-auto w-full max-w-[1120px]"><PromptTagEntryEditor draft={draft} error={error} saving={saving} bridgeReady={bridgeReady} dirty={dirty} onChange={setDraft} onSave={() => void saveEntry()} onBack={() => onOpenSection("list")} onReset={() => setDraft(selectedId ? entries.find((entry) => entry.id === selectedId) ?? emptyDraft : emptyDraft)} /></div>}
  </section>;
}
