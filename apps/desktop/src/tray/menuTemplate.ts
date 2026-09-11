import type { PluginTrayEntry } from "./registry.js";

/** One menu row, in the shape `Menu.buildFromTemplate` accepts. */
export type TrayMenuItem = { label: string; enabled?: boolean; click: () => void };

export type TrayMenuActions = {
  onShowWindow: () => void;
  onQuitRequested: () => void;
  onPluginEntryClick?: (pluginId: string, entryId: string) => void;
};

/**
 * Lays out the menu: the host's own two items with the plugins' between them.
 *
 * In its own module, free of any `electron` import, because that is the only
 * thing that makes it testable — the unit runner has no Electron, so anything
 * reachable from `menu.ts` is not. Same seam `surface/host.ts` uses, and the
 * reason the rest of `tray/menu.ts` (which genuinely needs a `Tray`) has no
 * tests and does not need any: what is left there is glue.
 */
export function buildTrayMenuTemplate(
  entries: PluginTrayEntry[],
  { onShowWindow, onQuitRequested, onPluginEntryClick }: TrayMenuActions,
): TrayMenuItem[] {
  return [
    { label: "显示主窗口", click: () => onShowWindow() },
    ...entries.map((entry) => ({
      label: entry.label,
      enabled: entry.enabled,
      click: () => onPluginEntryClick?.(entry.pluginId, entry.entryId),
    })),
    { label: "退出 Shiori", click: () => onQuitRequested() },
  ];
}
