import electronUpdater from "electron-updater";
import electron from "electron";
import { DesktopUpdateController } from "./updateController.js";

/** Connects the updater to desktop IPC and starts the packaged-only background check. */
export function registerDesktopUpdates(
  packaged: boolean,
  version: string,
  onError: (error: unknown) => void,
) {
  const { BrowserWindow, ipcMain, Notification } = electron;
  const controller = new DesktopUpdateController({
    version,
    engine: packaged ? electronUpdater.autoUpdater : null,
    publish: (state) => {
      for (const window of BrowserWindow.getAllWindows()) window.webContents.send("desktop:update-state", state);
      if (state.phase === "downloaded" && Notification.isSupported()) {
        new Notification({ title: "Shiori 更新已就绪", body: `v${state.latestVersion} 已下载，可在设置中重启安装。` }).show();
      }
    },
    onError,
  });
  ipcMain.handle("desktop:update-state", () => controller.getState());
  ipcMain.handle("desktop:update-check", () => controller.check());
  ipcMain.handle("desktop:update-install", () => controller.install());
  if (packaged) void controller.check().catch(() => { /* The controller publishes and logs startup failures. */ });
  return controller;
}
