import { BrowserWindow, dialog, ipcMain, shell } from "electron";
import { logDesktopDiagnostic } from "../diagnostics.js";
import { desktopDragFileIcon } from "../paths.js";
import { registerVoiceIpc } from "../voice/ipc.js";
import {
  registerDesktopIpcHandlers,
  type DesktopIpcHost,
  type RegisterDesktopIpcOptions,
} from "./ipcRegistrations.js";

export type { RegisterDesktopIpcOptions };

/** Binds the IPC boundary to the real Electron main process. */
const electronHost: DesktopIpcHost = {
  handle: (channel, listener) => { ipcMain.handle(channel, listener); },
  on: (channel, listener) => { ipcMain.on(channel, listener); },
  windowFromWebContents: (sender) => BrowserWindow.fromWebContents(sender),
  showOpenDialog: (options) => dialog.showOpenDialog(options),
  openExternal: (url) => shell.openExternal(url),
  logDiagnostic: logDesktopDiagnostic,
  dragFileIcon: desktopDragFileIcon,
  registerVoiceIpc,
};

/** Registers all IPC handlers exposed through the desktop preload bridge. */
export function registerDesktopIpc(options: RegisterDesktopIpcOptions): void {
  registerDesktopIpcHandlers(electronHost, options);
}
