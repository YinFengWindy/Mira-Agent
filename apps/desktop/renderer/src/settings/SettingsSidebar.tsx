import type React from "react";
import { pluginUiRegistry } from "../plugins/pluginUiRegistry";
import { cx, secondarySidebarSurfaceClass, sidebarNavItemClass } from "../shared/styles";
import { registerBuiltinSettingsSections } from "./registerBuiltinSettingsSections";

registerBuiltinSettingsSections();

/**
 * Identifies a settings.section registry entry. Widened from a fixed
 * literal union to a plain string because sections are no longer an
 * exhaustive, hand-enumerated set: plugins register their own ids into
 * `pluginUiRegistry` at build time.
 */
export type SettingsSectionId = string;

/** Sidebar entries for every currently registered settings section. */
export function listSettingsSidebarSections(
  isPluginEnabled?: (pluginId: string) => boolean,
): Array<{ id: SettingsSectionId; label: string }> {
  return pluginUiRegistry
    .listSettingsSections(isPluginEnabled)
    .map((entry) => ({ id: entry.id, label: entry.label }));
}

type SettingsSidebarProps = {
  sections?: Array<{ id: SettingsSectionId; label: string }>;
  activeSection: SettingsSectionId;
  collapsed: boolean;
  animating: boolean;
  width: number;
  onOpenSection: (section: SettingsSectionId) => void;
  onBeginResize: (event: React.PointerEvent<HTMLDivElement>) => void;
};

export function SettingsSidebar({
  sections = listSettingsSidebarSections(),
  activeSection,
  collapsed,
  animating,
  width,
  onOpenSection,
  onBeginResize,
}: SettingsSidebarProps) {
  const sidebarActionClass = cx(
    sidebarNavItemClass,
    "flex min-h-[38px] items-center px-3 text-left text-sm text-ink-secondary",
  );

  return (
    <aside
      className={cx(
        "settings-sidebar relative grid h-full min-h-0 min-w-0 grid-rows-[minmax(0,1fr)] py-5",
        secondarySidebarSurfaceClass,
        animating && "transition-[opacity,transform] duration-[480ms] ease-[cubic-bezier(0.22,1,0.36,1)]",
        collapsed ? "pointer-events-none -translate-x-4 px-0 opacity-0" : "translate-x-0 pl-[10px] pr-[6px] opacity-100",
      )}
      aria-hidden={collapsed}
      style={{ width }}
    >
      <nav className="scrollbar-soft grid min-h-0 content-start gap-1 overflow-y-auto px-2 pr-0">
        <div className="grid gap-1">
          {sections.map((section) => <button
              key={section.id}
              className={cx(
                sidebarActionClass,
                activeSection === section.id
                  && "bg-white/80 font-medium text-ink shadow-soft hover:bg-white focus-visible:bg-white",
              )}
              type="button"
              onClick={() => onOpenSection(section.id)}
            >
              <span>{section.label}</span>
            </button>)}
        </div>
      </nav>
      <div
        className={cx(
          "sidebar-resize-handle absolute bottom-0 right-0 top-0 cursor-col-resize bg-transparent",
          collapsed ? "w-0" : "w-2",
        )}
        role="separator"
        aria-label="调整侧边栏宽度"
        aria-orientation="vertical"
        onPointerDown={onBeginResize}
      />
    </aside>
  );
}
