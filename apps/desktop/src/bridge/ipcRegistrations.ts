import { copyFile, mkdir, stat } from "node:fs/promises";
import { basename, extname, join } from "node:path";
import { randomUUID } from "node:crypto";
import type {
  BrowserWindow,
  IpcMain,
  OpenDialogOptions,
  OpenDialogReturnValue,
  WebContents,
} from "electron";
import type { logDesktopDiagnostic } from "../diagnostics.js";
import type { DesktopBridgeClient } from "./bridgeClient.js";
import { importLocalAssets } from "../assets/localAssetImport.js";
import type { LocalAssetRegistry } from "../assets/localAssetRegistry.js";
import { maxLocalAssetBytes } from "../assets/localAssetContract.js";
import { applyRuntimeSettings, readRuntimeSettings } from "../settingsRuntime.js";
import type { DesktopObservationController } from "../observation/controller.js";
import type { DesktopPetCommand } from "../pluginCoupling/desktopPet.js";
import type { BrowserVoiceRecorder } from "../voice/recorder.js";
import type { DesktopVoiceController } from "../voice/controller.js";
import type { BrowserVoicePlayback } from "../voice/playback.js";
import type { registerVoiceIpc } from "../voice/ipc.js";
import { openExternalLink } from "../externalLinks.js";
import type {
  LocalAssetOpenRequest,
  LocalAssetOpenResult,
  LocalAssetReference,
  LocalAssetTransport,
  RendererDiagnosticPayload,
  SettingsFormData,
  SettingsSaveOptions,
} from "./shared.js";
import type { WindowControlAction } from "./shared.js";

/**
 * Main-process capabilities the IPC boundary needs.
 *
 * Everything that would otherwise be reached through a module-level `electron`
 * import lives here, so this module stays importable — and therefore testable —
 * outside an Electron process. `ipc.ts` supplies the production implementation.
 */
export type DesktopIpcHost = {
  handle(channel: string, listener: Parameters<IpcMain["handle"]>[1]): void;
  on(channel: string, listener: Parameters<IpcMain["on"]>[1]): void;
  /** Resolves the window that sent the request, so handlers never act on an arbitrary one. */
  windowFromWebContents(sender: WebContents): BrowserWindow | null;
  showOpenDialog(options: OpenDialogOptions): Promise<OpenDialogReturnValue>;
  openExternal(url: string): Promise<void>;
  logDiagnostic: typeof logDesktopDiagnostic;
  dragFileIcon: string;
  registerVoiceIpc: typeof registerVoiceIpc;
};

export type RegisterDesktopIpcOptions = {
  bridge: DesktopBridgeClient;
  localAssets: LocalAssetRegistry;
  localAssetImportsRoot: string;
  openLocalAttachment: (value: string) => Promise<LocalAssetOpenResult>;
  /** Issues one pet lifecycle command to the plugin that owns the pet. See `pluginCoupling/desktopPet.ts`. */
  requestDesktopPetCommand: (command: DesktopPetCommand) => void;
  /** Whether a sending window is the pet's surface, supplied by `main.ts`. */
  isPetWindow: (window: { readonly id: number } | null) => boolean;
  desktopObservation: DesktopObservationController;
  voiceRecorder: BrowserVoiceRecorder;
  voiceController: DesktopVoiceController;
  voicePlayback: BrowserVoicePlayback;
  onVoiceSettingsChanged?: () => void;
};

function assetTransport<T>(value: T, assets: LocalAssetReference[]): LocalAssetTransport<T> {
  return { value, assets };
}

async function importPickerSelection(
  paths: string[],
  importsRoot: string,
  localAssets: LocalAssetRegistry,
): Promise<LocalAssetTransport<string[]>> {
  const importedPaths = await importLocalAssets(paths, importsRoot);
  const assets: LocalAssetReference[] = [];
  for (const path of importedPaths) {
    const reference = localAssets.grantPath(path);
    if (!reference) {
      throw new Error("imported local asset is outside the trusted workspace");
    }
    assets.push(reference);
  }
  return assetTransport(importedPaths, assets);
}

async function importPetPackageSelection(paths: string[], importsRoot: string): Promise<string[]> {
  const imported: string[] = [];
  for (const source of paths) {
    if (extname(source).toLowerCase() !== ".zip") throw new Error("桌宠包必须是 ZIP 文件");
    const sourceStats = await stat(source);
    if (!sourceStats.isFile() || sourceStats.size > maxLocalAssetBytes) throw new Error("桌宠包无效或超过 32MB");
    const destinationDirectory = join(importsRoot, "pets");
    await mkdir(destinationDirectory, { recursive: true });
    const destination = join(destinationDirectory, `${randomUUID()}-${basename(source)}`);
    await copyFile(source, destination);
    imported.push(destination);
  }
  return imported;
}

async function stageRoleCardSelection(paths: string[], importsRoot: string): Promise<string[]> {
  const staged: string[] = [];
  const destinationDirectory = join(importsRoot, "role-cards");
  await mkdir(destinationDirectory, { recursive: true });
  for (const source of paths) {
    const extension = extname(source).toLowerCase();
    if (![".png", ".apng", ".json", ".charx"].includes(extension)) {
      throw new Error("角色卡必须是 PNG、APNG、JSON 或 CHARX 文件");
    }
    const sourceStats = await stat(source);
    if (!sourceStats.isFile() || sourceStats.size > maxLocalAssetBytes) {
      throw new Error("角色卡无效或超过 32MB");
    }
    const destination = join(destinationDirectory, `${randomUUID()}-${basename(source)}`);
    await copyFile(source, destination);
    staged.push(destination);
  }
  return staged;
}

/** Registers all IPC handlers exposed through the desktop preload bridge. */
export function registerDesktopIpcHandlers(
  host: DesktopIpcHost,
  {
    bridge,
    localAssets,
    localAssetImportsRoot,
    openLocalAttachment,
    requestDesktopPetCommand,
    isPetWindow,
    desktopObservation,
    voiceRecorder,
    voiceController,
    voicePlayback,
    onVoiceSettingsChanged,
  }: RegisterDesktopIpcOptions,
): void {
  const applicationSessionId = randomUUID();
  host.handle("desktop:application-session-id", () => applicationSessionId);
  host.handle("desktop:invoke", async (_event, request: { method: string; payload: Record<string, unknown> }) => {
    if (request.method.startsWith("observation.")) {
      throw new Error("observation bridge methods are restricted to the main process");
    }
    const response = await bridge.invoke(request);
    return assetTransport(response, localAssets.grantTrustedPayload(response.payload));
  });
  host.on("desktop:start-attachment-drag", (event, request?: { path?: unknown }) => {
    const filePath = String(request?.path ?? "").trim();
    const grant = localAssets.resolveReference(filePath);
    if (!grant) {
      return;
    }
    event.sender.startDrag({
      file: grant.canonicalPath,
      icon: host.dragFileIcon,
    });
  });
  host.on("desktop:renderer-diagnostic", (_event, payload?: RendererDiagnosticPayload) => {
    const diagnostic = payload ?? {
      kind: "error",
      message: "renderer emitted an empty diagnostic payload",
    };
    host.logDiagnostic({
      scope: "renderer",
      event: `renderer.${diagnostic.kind}`,
      payload: {
        message: diagnostic.message,
        stack: diagnostic.stack,
        componentStack: diagnostic.componentStack,
        filename: diagnostic.filename,
        lineno: diagnostic.lineno,
        colno: diagnostic.colno,
        details: diagnostic.details ?? {},
      },
    });
  });
  host.handle("desktop:bridge-status", async () => {
    return {
      running: bridge.isRunning(),
      lastError: bridge.getLastError(),
    };
  });
  host.handle("desktop:bridge-restart", async () => {
    try {
      await bridge.restart();
      return {
        ok: true,
        running: bridge.isRunning(),
        lastError: bridge.getLastError(),
      };
    } catch (error) {
      return {
        ok: false,
        running: false,
        lastError: String(error),
      };
    }
  });
  host.handle("desktop:settings-read", async () => {
    return readRuntimeSettings(bridge);
  });
  host.handle("desktop:settings-save", async (_event, formData: SettingsFormData, options?: SettingsSaveOptions) => {
    const result = await applyRuntimeSettings(bridge, formData, options);
    if (result.ok) onVoiceSettingsChanged?.();
    return result;
  });
  host.handle("desktop:window-control", (event, action: WindowControlAction) => {
    const window = host.windowFromWebContents(event.sender);
    if (!window) {
      return;
    }
    if (action === "minimize") {
      window.minimize();
      return;
    }
    if (action === "toggleMaximize") {
      if (window.isMaximized()) {
        window.unmaximize();
        return;
      }
      window.maximize();
      return;
    }
    if (action === "close") {
      window.close();
    }
  });
  host.handle("desktop:window-state", (event) => {
    const window = host.windowFromWebContents(event.sender);
    return {
      isMaximized: window?.isMaximized() ?? false,
      isVisible: window?.isVisible() ?? false,
    };
  });
  host.handle("desktop:pick-images", async (_event, options?: { multiple?: boolean }) => {
    const result = await host.showOpenDialog({
      properties: options?.multiple ? ["openFile", "multiSelections"] : ["openFile"],
      filters: [
        {
          name: "Images",
          extensions: ["png", "jpg", "jpeg", "webp", "gif"],
        },
      ],
    });
    if (result.canceled) {
      return assetTransport([], []);
    }
    return await importPickerSelection(result.filePaths, localAssetImportsRoot, localAssets);
  });
  host.handle("desktop:pick-role-card", async () => {
    const result = await host.showOpenDialog({
      properties: ["openFile"],
      filters: [{ name: "Role cards", extensions: ["png", "apng", "json", "charx"] }],
    });
    if (result.canceled) return assetTransport([], []);
    const stagedPaths = await stageRoleCardSelection(result.filePaths, localAssetImportsRoot);
    const assets = stagedPaths.map((path) => {
      const reference = localAssets.grantPath(path);
      if (!reference) throw new Error("staged role card is outside the trusted workspace");
      return reference;
    });
    return assetTransport(stagedPaths, assets);
  });
  // Fire-and-forget since #181-C: the pet's controller lives in the plugin
  // host renderer, so this can no longer await the sync and then refresh the
  // tray. The refresh happens instead when the plugin writes its settings back
  // — see `main.ts`'s `pluginData.onChanged`, which is also what makes the
  // tray correct after a change the pet made on its own.
  host.handle("desktop:pet-sync", (_event, forceVisible?: unknown) => {
    requestDesktopPetCommand({
      kind: "sync",
      forceVisible: typeof forceVisible === "boolean" ? forceVisible : undefined,
    });
  });
  host.handle("desktop:pet-observation-dismiss", (event) => {
    const petWindow = host.windowFromWebContents(event.sender);
    if (!isPetWindow(petWindow)) return;
    desktopObservation.dismissBubble();
  });
  // The pet's ready / bubble-height / drag / open / context-menu channels are
  // gone. Since #181-B the pet is a plugin surface, so those requests arrive on
  // the generic DesktopSurface channels in `src/surface/ipc.ts`, where the host
  // attributes them by the sending window's identity rather than by a
  // pet-specific check here.
  host.registerVoiceIpc({ isPetWindow, voiceRecorder, voiceController, voicePlayback });
  host.handle("desktop:pick-chat-attachments", async (_event, options?: { multiple?: boolean }) => {
    const result = await host.showOpenDialog({
      properties: options?.multiple ? ["openFile", "multiSelections"] : ["openFile"],
      filters: [
        {
          name: "Chat Attachments",
          extensions: ["png", "jpg", "jpeg", "webp", "gif", "md", "txt"],
        },
      ],
    });
    if (result.canceled) {
      return assetTransport([], []);
    }
    return await importPickerSelection(result.filePaths, localAssetImportsRoot, localAssets);
  });
  host.handle("desktop:pick-pet-package", async () => {
    const result = await host.showOpenDialog({
      properties: ["openFile"],
      filters: [{ name: "Codex Pet Package", extensions: ["zip"] }],
    });
    if (result.canceled) return assetTransport([], []);
    return assetTransport(await importPetPackageSelection(result.filePaths, localAssetImportsRoot), []);
  });
  host.handle("desktop:open-attachment", async (_event, request: LocalAssetOpenRequest) => {
    const value = String(request?.url || request?.path || "").trim();
    return await openLocalAttachment(value);
  });
  host.handle("desktop:open-external", async (_event, request?: { url?: unknown }) => {
    return await openExternalLink(String(request?.url ?? ""), (url) => host.openExternal(url));
  });
}
