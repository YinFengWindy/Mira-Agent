import type { BrowserWindow } from "electron";

type DesktopWindowClosePolicy = {
  isQuitting: boolean;
  trayLifecycleEnabled: boolean;
  /**
   * Whether any plugin still owns a desktop window.
   *
   * Was `desktopPetRunning` until #181-D. The policy never cared that it was a
   * pet — it cared that closing the shell would strand a window the user can
   * still see with no way to get back to it — and naming it after one plugin
   * made it silently wrong for the next plugin to own a surface.
   */
  pluginSurfacesAlive: boolean;
};

/** Keeps the main shell alive while the tray or a plugin surface still owns the app lifecycle. */
export function shouldHideDesktopWindowOnClose({
  isQuitting,
  trayLifecycleEnabled,
  pluginSurfacesAlive,
}: DesktopWindowClosePolicy): boolean {
  return !isQuitting && (trayLifecycleEnabled || pluginSurfacesAlive);
}

/** Keeps the desktop renderer alive when the user closes into the tray. */
export function attachDesktopWindowLifecycle(
  window: BrowserWindow,
  { shouldHideOnClose }: { shouldHideOnClose: () => boolean },
): void {
  window.on("close", (event: { preventDefault(): void }) => {
    if (!shouldHideOnClose()) {
      return;
    }
    event.preventDefault();
    window.hide();
  });
}
