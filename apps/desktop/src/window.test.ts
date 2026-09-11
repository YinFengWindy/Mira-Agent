import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import test from "node:test";
import type { BrowserWindow } from "electron";
import { attachDesktopWindowLifecycle, shouldHideDesktopWindowOnClose } from "./windowLifecycle.js";

class FakeWindow extends EventEmitter {
  hidden = false;

  hide(): void {
    this.hidden = true;
  }
}

test("main window close is hidden while any plugin surface is on screen", () => {
  assert.equal(shouldHideDesktopWindowOnClose({
    isQuitting: false,
    trayLifecycleEnabled: false,
    pluginSurfacesAlive: true,
  }), true);
});

test("with no tray and no plugin surface, closing the main window really closes it", () => {
  // Otherwise a platform without a tray lifecycle would have a window that
  // cannot be closed and nothing left on screen to reopen it from.
  assert.equal(shouldHideDesktopWindowOnClose({
    isQuitting: false,
    trayLifecycleEnabled: false,
    pluginSurfacesAlive: false,
  }), false);
});

test("explicit app quit still allows the main window to close", () => {
  assert.equal(shouldHideDesktopWindowOnClose({
    isQuitting: true,
    trayLifecycleEnabled: true,
    pluginSurfacesAlive: true,
  }), false);
});

test("closing the main window hides the shell instead of allowing a native close", () => {
  const window = new FakeWindow();
  let prevented = false;
  attachDesktopWindowLifecycle(window as unknown as BrowserWindow, {
    shouldHideOnClose: () => true,
  });

  window.emit("close", {
    preventDefault: () => {
      prevented = true;
    },
  });

  assert.equal(prevented, true);
  assert.equal(window.hidden, true);
});
