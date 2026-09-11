import type { SurfaceHandle } from "../../../apps/desktop/renderer/src/surface/pluginSurfaceRegistry";

/**
 * The pet's own right-click menu.
 *
 * Before #181 the host built this menu in `main.ts`, which meant the host had
 * to know what a desktop pet is and which of its commands belong in a menu.
 * Now the plugin owns the items and the host only knows how to pop a native
 * menu over a surface — something a transparent window's DOM cannot do,
 * because it cannot draw outside its own bounds.
 */

/** What the host asks the plugin to close over when a hide is requested. */
export type PetMenuHost = {
  /**
   * TEMPORARY COUPLING: hiding the pet detours through the host.
   *
   * Since #181-C the host does none of the work — it publishes
   * `desktop.pet.command` and this plugin's own `background/index.ts` performs
   * the hide, persists `visible: false`, and the host refreshes its tray from
   * that write. What is still missing is a *direct* route: a surface renderer
   * has no way to reach its own plugin's background code, so the request has to
   * go out through the main process and come back.
   *
   * `surfaces.hide` is not a substitute — it would make the window invisible
   * without recording that the user turned the pet off, so the next launch
   * would bring it back.
   *
   * The detour disappears with surface-to-background messaging (#218).
   */
  syncPet(forceVisible?: boolean): Promise<void>;
};

export const petMenuMainWindowId = "show-main-window";
export const petMenuHidePetId = "hide-pet";

export const petContextMenuItems = [
  { id: petMenuMainWindowId, label: "显示主窗口" },
  { id: petMenuHidePetId, label: "隐藏桌宠" },
];

/**
 * Opens the pet menu and performs the chosen command.
 *
 * A dismissal resolves `null` rather than hanging, so nothing here has to
 * distinguish "closed without choosing" from "still open".
 */
export async function openPetContextMenu(surface: SurfaceHandle, host: PetMenuHost): Promise<void> {
  const choice = await surface.showContextMenu(petContextMenuItems.map((item) => ({ ...item })));
  if (choice === petMenuMainWindowId) {
    surface.activateMainWindow();
    return;
  }
  if (choice === petMenuHidePetId) await host.syncPet(false);
}
