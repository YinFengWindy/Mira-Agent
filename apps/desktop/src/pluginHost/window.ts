import { BrowserWindow } from "electron";
import { rendererDevServerUrl, rendererPluginHostDist, preloadScript } from "../paths.js";
import {
  attachDesktopWindowSecurity,
  resolveRendererEntryUrl,
  validateRendererDevServerUrl,
} from "../windowSecurity.js";

/**
 * Creates the single, never-shown renderer window that owns every plugin's
 * always-resident `app.background` code (#226 item 1, unblocking #181-C).
 *
 * # Why a dedicated window, not the main window's renderer
 *
 * `trayLifecycleEnabled = process.platform === "win32"`, and
 * `shouldHideDesktopWindowOnClose` is
 * `!isQuitting && (trayLifecycleEnabled || desktopPetRunning)`. On Windows
 * closing the main window only hides it — its renderer survives to app
 * quit — but on macOS (`trayLifecycleEnabled` false) closing it actually
 * destroys the renderer, while `window-all-closed` does not quit the app on
 * darwin. A controller hosted in the main window's renderer would die there
 * and orphan whatever surfaces it owned. This window's lifetime is the
 * app's, independent of the main window, so that hole does not apply to it.
 * It also removes a circular dependency the main-window approach would
 * otherwise have (the main window kept alive *because* background code runs,
 * while that code lives *inside* the main window), and gives the background
 * code crash isolation from the main window's renderer.
 *
 * Modeled on `createVoiceCaptureWindow` (`src/voice/window.ts`): hidden,
 * frameless, not resizable, no taskbar entry. Unlike the voice window, no
 * "ready" promise is exposed — nothing outside this window needs to know
 * when its script has finished loading; each plugin's `setup(ctx)` runs
 * independently as soon as the bundle executes.
 */
export type CreatePluginHostWindowOptions = {
  /**
   * Called when this renderer dies unexpectedly.
   *
   * Since #181-C this window owns every plugin's surface, so its death orphans
   * them all — see `DesktopSurfaceHost.destroyAll`. It is also invisible, which
   * means a crash here has no other way of being noticed: without this the app
   * would simply stop having a desktop pet, with nothing logged.
   */
  onRenderProcessGone?: (details: { reason: string; exitCode: number }) => void;
};

export function createPluginHostWindow(options: CreatePluginHostWindowOptions = {}): BrowserWindow {
  const window = new BrowserWindow({
    width: 1,
    height: 1,
    show: false,
    frame: false,
    resizable: false,
    skipTaskbar: true,
    webPreferences: {
      preload: preloadScript,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      spellcheck: false,
      backgroundThrottling: false,
    },
  });
  attachDesktopWindowSecurity(window.webContents, {
    rendererEntryUrl: resolveRendererEntryUrl(rendererPluginHostDist, rendererDevServerUrl),
    // Nothing in the plugin-host window is user-facing, so there is nothing
    // it should ever hand off to the OS shell.
    openLocalAttachment: () => undefined,
  });
  window.webContents.on("render-process-gone", (_event, details) => {
    options.onRenderProcessGone?.({ reason: details.reason, exitCode: details.exitCode ?? 0 });
  });
  const devUrl = validateRendererDevServerUrl(rendererDevServerUrl);
  if (devUrl) {
    void window.loadURL(new URL("plugin-host.html", devUrl).toString());
  } else {
    void window.loadFile(rendererPluginHostDist);
  }
  return window;
}
