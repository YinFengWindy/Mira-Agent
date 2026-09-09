import type React from "react";
import { BookOpenText, Chats, GearSix, MagnifyingGlass, Users } from "@phosphor-icons/react";
import { cx } from "../shared/styles";

const novelAiLogoDark = new URL("../assets/novelai-logo-dark.svg", import.meta.url).href;

/**
 * Identifies the workspace a rail entry points to; null when no view entry
 * is active. Widened to a plain string so a plugin's nav.page (identified
 * as `plugin:<id>`) can be an active target alongside the fixed built-in
 * surfaces without another exhaustive union to maintain.
 */
export type NavRailViewId = string;

/** Builds the stable rail id for a plugin's nav.page entry. */
export function pluginNavRailViewId(pageId: string): NavRailViewId {
  return `plugin:${pageId}`;
}

/** Icon contract shared by built-in phosphor icons and a plugin's own icon component. */
type NavRailIcon = React.ComponentType<{ className?: string }>;

type NavRailEntry = {
  id: NavRailViewId | "search";
  label: string;
  icon?: NavRailIcon;
  imageSrc?: string;
  onSelect: () => void;
  showUnreadBadge?: boolean;
};

/** A plugin-contributed nav.page entry rendered alongside the built-in rail icons. */
export type NavRailPluginEntry = {
  pageId: string;
  label: string;
  icon?: NavRailIcon;
  onSelect: () => void;
};

type NavRailProps = {
  activeView: NavRailViewId | null;
  unreadTotal: number;
  pluginEntries?: NavRailPluginEntry[];
  onOpenSearch: () => void;
  onBackToChat: () => void;
  onOpenRolesWorkspace: () => void;
  onOpenImageStudio: () => void;
  onOpenStory: () => void;
  onOpenSettings: () => void;
};

const railButtonClass =
  "relative grid h-9 w-9 place-items-center rounded-md text-ink-muted transition-colors focus-visible:bg-white/70 hover:bg-white/70 hover:text-ink";

/** Renders the primary icon navigation rail shown across every workspace. */
export function NavRail({
  activeView,
  unreadTotal,
  pluginEntries = [],
  onOpenSearch,
  onBackToChat,
  onOpenRolesWorkspace,
  onOpenImageStudio,
  onOpenStory,
  onOpenSettings,
}: NavRailProps) {
  const entries: NavRailEntry[] = [
    { id: "search", label: "搜索", icon: MagnifyingGlass, onSelect: onOpenSearch },
    { id: "messages", label: "消息", icon: Chats, onSelect: onBackToChat, showUnreadBadge: true },
    { id: "roles", label: "角色", icon: Users, onSelect: onOpenRolesWorkspace },
    { id: "image", label: "生图", imageSrc: novelAiLogoDark, onSelect: onOpenImageStudio },
    { id: "story", label: "故事", icon: BookOpenText, onSelect: onOpenStory },
    ...pluginEntries.map((entry) => ({
      id: pluginNavRailViewId(entry.pageId),
      label: entry.label,
      icon: entry.icon,
      onSelect: entry.onSelect,
    })),
  ];

  function renderEntry(entry: NavRailEntry): React.ReactNode {
    const active = entry.id === activeView;
    const showBadge = Boolean(entry.showUnreadBadge && unreadTotal > 0);
    const Icon = entry.icon;
    return (
      <button
        key={entry.id}
        className={cx(
          railButtonClass,
          active
            && "bg-white text-accent shadow-soft hover:bg-white hover:text-accent",
        )}
        type="button"
        aria-label={showBadge ? `${entry.label}（${unreadTotal} 条未读）` : entry.label}
        aria-current={active ? "page" : undefined}
        title={entry.label}
        onClick={entry.onSelect}
      >
        {entry.imageSrc ? <img className="h-[19px] w-[19px]" src={entry.imageSrc} alt="" /> : null}
        {!entry.imageSrc && Icon ? <span aria-hidden="true"><Icon className="h-[19px] w-[19px]" /></span> : null}
        {showBadge ? (
          <span className="absolute right-0.5 top-0.5 h-2 w-2 rounded-full bg-danger" aria-hidden="true" />
        ) : null}
      </button>
    );
  }

  return (
    <nav className="nav-rail flex w-12 shrink-0 flex-col items-center gap-1 py-2.5" aria-label="主导航">
      {entries.map(renderEntry)}
      <div className="mt-auto">{renderEntry({ id: "settings", label: "设置", icon: GearSix, onSelect: onOpenSettings })}</div>
    </nav>
  );
}
