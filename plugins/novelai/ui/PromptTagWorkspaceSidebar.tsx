import { cx, secondarySidebarSurfaceClass, sidebarNavItemClass } from "../../../apps/desktop/renderer/src/shared/styles";

export type PromptTagWorkspaceSectionId = "list" | "create" | "detail";

type PromptTagWorkspaceSidebarProps = {
  activeSection: PromptTagWorkspaceSectionId;
  onOpenSection: (section: PromptTagWorkspaceSectionId) => void;
  onBackToStudio: () => void;
};

/** Renders prompt-tag workspace navigation inside the plugin's own page. */
export function PromptTagWorkspaceSidebar({ activeSection, onOpenSection, onBackToStudio }: PromptTagWorkspaceSidebarProps) {
  const actionClass = cx(
    sidebarNavItemClass,
    "flex min-h-[38px] items-center justify-between px-3 text-left text-sm text-ink-secondary",
  );
  const activeClass =
    "bg-white/90 font-medium text-ink shadow-soft hover:bg-white focus-visible:bg-white";
  return (
    <aside className={cx("grid h-full min-h-0 min-w-0 content-start gap-1 py-3 pl-[10px] pr-[6px]", secondarySidebarSurfaceClass)}>
      <div className="grid gap-1 px-2">
        <button className={actionClass} type="button" onClick={onBackToStudio}>返回生图</button>
        <button className={cx(actionClass, activeSection === "list" && activeClass)} type="button" onClick={() => onOpenSection("list")}>提示词列表</button>
        <button className={cx(actionClass, activeSection === "create" && activeClass)} type="button" onClick={() => onOpenSection("create")}>新建提示词</button>
      </div>
    </aside>
  );
}
