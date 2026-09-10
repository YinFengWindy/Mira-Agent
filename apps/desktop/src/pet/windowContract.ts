import { desktopPetViewport } from "./geometry.js";

/**
 * Construction options for the desktop-pet surface.
 *
 * Kept in a dependency-free module so the "always on top, never elevated to the
 * screen-saver level" contract can be asserted directly — `window.ts` itself
 * resolves packaged asset paths through Electron and cannot be imported by a
 * plain Node test process.
 */
export function desktopPetWindowOptions(preload: string) {
  return {
    width: desktopPetViewport.width,
    height: desktopPetViewport.height,
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    webPreferences: {
      preload,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      spellcheck: false,
    },
  };
}
