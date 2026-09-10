import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { desktopPetViewport } from "./geometry.js";
import { desktopPetWindowOptions } from "./windowContract.js";

describe("desktop pet window options", () => {
  it("creates the pet on top without elevating it to the screen-saver level", () => {
    const options = desktopPetWindowOptions("preload.js");

    assert.equal(options.alwaysOnTop, true);
    // BrowserWindow 构造参数里没有层级字段；提升到 screen-saver 只能靠随后
    // 调用 setAlwaysOnTop(flag, level)，所以这里锁定「构造即置顶」这一条。
    assert.equal("level" in options, false);
    assert.equal("type" in options, false);
  });

  it("keeps the pet surface frameless, transparent and out of the taskbar", () => {
    const options = desktopPetWindowOptions("preload.js");

    assert.equal(options.frame, false);
    assert.equal(options.transparent, true);
    assert.equal(options.resizable, false);
    assert.equal(options.skipTaskbar, true);
    assert.equal(options.hasShadow, false);
    assert.equal(options.width, desktopPetViewport.width);
    assert.equal(options.height, desktopPetViewport.height);
  });

  it("isolates the pet renderer behind the shared preload", () => {
    const options = desktopPetWindowOptions("preload.js");

    assert.equal(options.webPreferences.preload, "preload.js");
    assert.equal(options.webPreferences.contextIsolation, true);
    assert.equal(options.webPreferences.nodeIntegration, false);
  });
});
