import { BrowserWindow, screen } from "electron";
import { rendererDevServerUrl, rendererSurfaceDist, preloadScript } from "../paths.js";
import {
  attachDesktopWindowSecurity,
  resolveRendererEntryUrl,
  validateRendererDevServerUrl,
} from "../windowSecurity.js";
import { desktopSurfaceWindowOptions, type SurfaceSpec, type SurfaceWorkArea } from "./contract.js";
import type { SurfaceKey, SurfaceWindowHandle } from "./host.js";
import { surfaceQueryString } from "./entry.js";

/**
 * The Electron half of the DesktopSurface capability.
 *
 * Everything here needs a live Electron process, so it is kept apart from
 * `host.ts` — which holds all the behaviour worth testing and is deliberately
 * importable from the plain node:test runner.
 */

/**
 * Creates one plugin-owned surface window.
 *
 * Every surface loads the *same* host-owned renderer entry, told which plugin
 * it belongs to through the query string. Giving each plugin its own HTML
 * entry would mean editing `renderer/vite.config.ts` for every new plugin that
 * wants a window — which is exactly the build-time coupling #181 removes (the
 * pet's hardcoded `pet.html` entry being the current example).
 */
export function createDesktopSurfaceWindow(
  key: SurfaceKey,
  spec: SurfaceSpec,
  options: { openLocalAttachment: (url: string) => Promise<unknown> | unknown },
): SurfaceWindowHandle {
  const window = new BrowserWindow(desktopSurfaceWindowOptions(spec, preloadScript));
  window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  attachDesktopWindowSecurity(window.webContents, {
    rendererEntryUrl: resolveRendererEntryUrl(rendererSurfaceDist, rendererDevServerUrl),
    openLocalAttachment: options.openLocalAttachment,
  });
  const query = surfaceQueryString(key);
  const devUrl = validateRendererDevServerUrl(rendererDevServerUrl);
  if (devUrl) {
    const url = new URL("surface.html", devUrl);
    url.search = query;
    void window.loadURL(url.toString());
  } else {
    void window.loadFile(rendererSurfaceDist, { search: query });
  }
  return adaptSurfaceWindow(window);
}

/** Wraps a `BrowserWindow` in the narrow handle `DesktopSurfaceHost` depends on. */
export function adaptSurfaceWindow(window: BrowserWindow): SurfaceWindowHandle {
  return {
    id: window.id,
    setBounds: (bounds) => window.setBounds(bounds),
    getBounds: () => window.getBounds(),
    isDestroyed: () => window.isDestroyed(),
    destroy: () => window.destroy(),
    showInactive: () => window.showInactive(),
    hide: () => window.hide(),
    setIgnoreMouseEvents: (ignore, ignoreOptions) => window.setIgnoreMouseEvents(ignore, ignoreOptions),
    send: (channel, payload) => {
      if (!window.isDestroyed()) window.webContents.send(channel, payload);
    },
    onClosed: (listener) => window.on("closed", listener),
  };
}

/** Resolves the work area of the display a surface currently sits on. */
export function workAreaForSurface(handle: SurfaceWindowHandle): SurfaceWorkArea {
  const window = BrowserWindow.fromId(handle.id);
  const display = window && !window.isDestroyed()
    ? screen.getDisplayMatching(window.getBounds())
    : screen.getPrimaryDisplay();
  return display.workArea;
}

/** The native cursor location, which only the main process can read. */
export function cursorScreenPoint() {
  return screen.getCursorScreenPoint();
}
