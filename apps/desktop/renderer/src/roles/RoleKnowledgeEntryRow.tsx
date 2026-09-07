import { CaretDown } from "@phosphor-icons/react";
import { DeleteIcon } from "../shared/icons";
import { cx } from "../shared/styles";
import type { RoleKnowledgeEntry } from "../shared/types";
import { roleChipClass, roleFieldClass } from "./roleEditorStyles";

type RoleKnowledgeEntryRowProps = {
  entry: RoleKnowledgeEntry;
  index: number;
  expanded: boolean;
  onToggle: () => void;
  onUpdate: (update: (current: RoleKnowledgeEntry) => RoleKnowledgeEntry) => void;
  onRemove: () => void;
};

/** Renders one editable Lorebook entry with its keyword chips. */
export function RoleKnowledgeEntryRow({ entry, index, expanded, onToggle, onUpdate, onRemove }: RoleKnowledgeEntryRowProps) {
  const keywords = entry.primary_keys ?? entry.keywords ?? [];

  return (
    <div className="border-b border-[#EEF2F5] last:border-b-0" data-testid={`knowledge-entry-${index}`}>
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
        <div className="grid gap-3 pb-4">
          <label className="grid gap-1.5 text-xs text-[#667085]">
            <span>关键词</span>
            <input
              className={roleFieldClass}
              value={keywords.join(", ")}
              placeholder="用逗号分隔多个关键词"
              onChange={(event) => onUpdate((current) => ({
                ...current,
                primary_keys: event.target.value.split(",").map((keyword) => keyword.trim()).filter(Boolean),
              }))}
            />
          </label>
          <label className="grid gap-1.5 text-xs text-[#667085]">
            <span>内容</span>
            <textarea
              className={cx(roleFieldClass, "min-h-32 resize-none leading-6")}
              value={entry.content ?? ""}
              placeholder="输入会注入角色上下文的内容"
              onChange={(event) => onUpdate((current) => ({ ...current, content: event.target.value }))}
            />
          </label>
          <button
            className="inline-flex w-fit items-center gap-1.5 text-xs text-[#B54747] transition hover:text-[#963B3B] focus:outline-none"
            type="button"
            onClick={onRemove}
            aria-label={`删除条目 ${index + 1}`}
            title="删除条目"
          >
            <DeleteIcon className="h-3.5 w-3.5 fill-current" />
            删除条目
          </button>
        </div>
      ) : null}
    </div>
  );
}
