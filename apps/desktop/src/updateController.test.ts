import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import test from "node:test";
import type { UpdateCheckResult, UpdateInfo } from "electron-updater";
import { DesktopUpdateController } from "./updateController.js";

const info: UpdateInfo = { version: "0.3.0", files: [], path: "setup.exe", sha512: "hash", releaseDate: "2026-09-09" };
const result: UpdateCheckResult = { isUpdateAvailable: false, updateInfo: info, versionInfo: info };

class FakeUpdater extends EventEmitter {
  autoDownload = false;
  checks = 0;
  installs: boolean[][] = [];
  checkResult: () => Promise<UpdateCheckResult | null> = async () => {
    this.emit("update-not-available", info);
    return result;
  };
  checkForUpdates() { this.checks += 1; return this.checkResult(); }
  quitAndInstall(silent = false, relaunch = false) { this.installs.push([silent, relaunch]); }
}

function fixture(engine: FakeUpdater | null = new FakeUpdater()) {
  const errors: unknown[] = [];
  const controller = new DesktopUpdateController({ version: "0.2.0", engine, publish: () => undefined, onError: (error) => errors.push(error) });
  return { controller, errors };
}

test("development builds expose version without creating an update engine", async () => {
  const { controller } = fixture(null);
  assert.equal(controller.getState().currentVersion, "0.2.0");
  assert.equal(controller.getState().phase, "unsupported");
  await assert.rejects(controller.check(), /开发模式/);
  assert.throws(() => controller.install(), /尚未下载完成/);
});

test("startup and manual checks share one request and expose current status", async () => {
  const engine = new FakeUpdater();
  const { controller } = fixture(engine);
  const first = controller.check();
  assert.equal(controller.check(), first);
  await first;
  assert.equal(engine.checks, 1);
  assert.equal(engine.autoDownload, true);
  assert.equal(controller.getState().phase, "current");
});

test("download progress survives manual checks and installation requires a ready update", async () => {
  const engine = new FakeUpdater();
  const { controller } = fixture(engine);
  engine.emit("update-available", info);
  engine.emit("download-progress", { percent: 42.5 });
  assert.equal(controller.getState().progress, 42.5);
  assert.equal(controller.getState().latestVersion, "0.3.0");
  await controller.check();
  assert.equal(engine.checks, 0);
  assert.throws(() => controller.install(), /尚未下载完成/);
  engine.emit("update-downloaded", info);
  controller.install();
  assert.deepEqual(engine.installs, [[false, true]]);
  assert.equal(controller.getState().phase, "installing");
  assert.throws(() => controller.install(), /尚未下载完成/);
  controller.dispose();
  assert.equal(engine.listenerCount("download-progress"), 0);
});

test("failed checks publish an error once and can be retried", async () => {
  const engine = new FakeUpdater();
  const { controller, errors } = fixture(engine);
  engine.checkResult = async () => {
    const error = new Error("network unavailable");
    engine.emit("error", error);
    throw error;
  };
  await assert.rejects(controller.check(), /network unavailable/);
  assert.equal(controller.getState().error, "network unavailable");
  assert.equal(errors.length, 1);
  engine.checkResult = async () => { engine.emit("update-not-available", info); return result; };
  await controller.check();
  assert.equal(controller.getState().phase, "current");
  assert.equal(controller.getState().error, null);
});

test("asynchronous download failures are observable and do not become unhandled rejections", async () => {
  const engine = new FakeUpdater();
  const { controller } = fixture(engine);
  engine.checkResult = async () => {
    engine.emit("update-available", info);
    return { ...result, isUpdateAvailable: true, downloadPromise: Promise.reject(new Error("download failed")) };
  };
  await controller.check();
  assert.equal(controller.getState().phase, "error");
  assert.equal(controller.getState().error, "download failed");
});
