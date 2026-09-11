import { Menu, Tray } from "electron";
import { desktopWindowIcon } from "../paths.js";
import type { PluginTrayEntry } from "./registry.js";
import { buildTrayMenuTemplate } from "./menuTemplate.js";

type CreateDesktopTrayOptions = {
  onShowWindow: () => void;
  onQuitRequested: () => void;
  /**
   * Plugin-contributed items, rendered between the two host items.
   *
   * Read on every refresh rather than captured once: a plugin rewrites its own
   * label as its state changes (the desktop pet alternates 显示桌宠/隐藏桌宠),
   * and `PluginTrayRegistry.onChanged` is what triggers the refresh.
   */
  pluginEntries?: () => PluginTrayEntry[];
  onPluginEntryClick?: (pluginId: string, entryId: string) => void;
};

/** Electron tray handle with an explicit state refresh hook for async startup changes. */
export type DesktopTray = Tray & { refresh(): void };

/**
 * Creates the Windows tray entry used to restore or quit the desktop shell.
 *
 * Since #181-D this file knows nothing about the desktop pet. It used to build
 * a 显示桌宠/隐藏桌宠 item out of a pet-shaped state getter, which meant the
 * host had to know whether a pet was visible and whether it could be started —
 * the last of the pet's domain state living in the main process. The pet now
 * contributes that item itself through `ctx.tray`, and this renders whatever
 * any plugin has registered.
 *
 * The refresh on click is also gone with it. It used to fire after the toggle
 * promise settled, which was optimistic: the menu was rebuilt whether or not
 * the pet had actually changed. Refreshes now come from the registry, i.e.
 * when a plugin really does change what its item should say.
 */
export function createDesktopTray({
  onShowWindow,
  onQuitRequested,
  pluginEntries,
  onPluginEntryClick,
}: CreateDesktopTrayOptions): DesktopTray {
  const tray = new Tray(desktopWindowIcon);
  const refresh = () => {
    tray.setContextMenu(Menu.buildFromTemplate(buildTrayMenuTemplate(
      pluginEntries?.() ?? [],
      { onShowWindow, onQuitRequested, onPluginEntryClick },
    )));
  };
  tray.setToolTip("Shiori");
  refresh();
  tray.on("click", () => onShowWindow());
  tray.on("right-click", refresh);
  return Object.assign(tray, { refresh });
}
