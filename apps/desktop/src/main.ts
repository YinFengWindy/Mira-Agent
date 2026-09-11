import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { app, BrowserWindow, powerMonitor, protocol, session, shell } from "electron";
import { localAssetSchemePrivileges, registerLocalAssetProtocol } from "./assets/assetProtocol.js";
import { DesktopBridgeClient } from "./bridge/bridgeClient.js";
import { startBridge, wireBridgeEvents } from "./bridge/bridgeLifecycle.js";
import { logDesktopDiagnostic } from "./diagnostics.js";
import { registerDesktopIpc, registerDesktopPluginDataIpc, registerDesktopSurfaceIpc } from "./bridge/ipc.js";
import { DesktopSurfaceHost, surfaceSettledChannel } from "./surface/host.js";
import {
  createDesktopSurfaceWindow,
  cursorScreenPoint,
  displayIdForSurface,
  showSurfaceContextMenu,
  workAreaForSurface,
} from "./surface/window.js";
import { createPluginHostWindow } from "./pluginHost/window.js";
import { openGrantedLocalAsset } from "./assets/localAssetOpen.js";
import { LocalAssetRegistry, localAssetScheme } from "./assets/localAssetRegistry.js";
import { ensureDesktopRuntimeConfig, resolveDesktopRuntimePaths } from "./runtimePaths.js";
import { registerDesktopUpdates } from "./updater.js";
import { createDesktopTray } from "./tray.js";
import { createDesktopWindow, showDesktopWindow } from "./window.js";
import {
  attachDesktopWindowLifecycle,
  shouldHideDesktopWindowOnClose as shouldHideDesktopWindowOnClosePolicy,
} from "./windowLifecycle.js";
import { registerDesktopContentSecurityPolicy } from "./windowSecurity.js";
import { PluginDataStore } from "./plugins/dataStore.js";
import {
  desktopPetCommandMethod,
  desktopPetObservationMethod,
  desktopPetPluginId,
  desktopPetSurfaceKey,
  isDesktopPetWindow,
  noDesktopPetPresence,
  readDesktopPetPresence,
  type DesktopPetCommand,
  type DesktopPetPresence,
} from "./pluginCoupling/desktopPet.js";
import { DesktopObservationController } from "./observation/controller.js";
import { wireRoleReplyBubbles } from "./observation/roleBubble.js";
import { createVoiceCaptureWindow } from "./voice/window.js";
import { BrowserVoiceRecorder } from "./voice/recorder.js";
import { DesktopVoiceController } from "./voice/controller.js";
import { VoiceHotkeyController } from "./voice/hotkey.js";
import { BrowserVoicePlayback } from "./voice/playback.js";
import { cancelVoiceTurn, createVoicePlaybackCallbacks, handleVoiceBridgeEvent, selectVoiceTurn } from "./voice/bridgeEvents.js";
import { applyVoiceAvailability, isVoiceHotkeyAvailable } from "./voice/availability.js";
import { configureSettingsConfigPath, loadSettingsData } from "./settings.js";
import type {
  BridgeEvent,
  LocalAssetTransport,
  SettingsFormData,
  SurfaceSettledPayload,
  VoiceStatePayload,
} from "./bridge/shared.js";

// Voice replies are played from a trusted hidden renderer without a DOM user gesture.
app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");

const runtimePaths = resolveDesktopRuntimePaths({
  packaged: app.isPackaged,
  appPath: app.getAppPath(),
  homePath: app.getPath("home"),
});
const bridge = new DesktopBridgeClient(runtimePaths.bridge);
const localAssets = new LocalAssetRegistry();
const trayLifecycleEnabled = process.platform === "win32";
const hasSingleInstanceLock = app.requestSingleInstanceLock();
let desktopWindow: BrowserWindow | null = null;
let pluginHostWindow: BrowserWindow | null = null;
let desktopTray: ReturnType<typeof createDesktopTray> | null = null;
let desktopSurfaces: DesktopSurfaceHost | null = null;
/** The pet's state as the host sees it; refreshed whenever the plugin writes. */
let desktopPetPresence: DesktopPetPresence = noDesktopPetPresence;
let desktopObservation: DesktopObservationController | null = null;
let voiceRecorder: BrowserVoiceRecorder | null = null;
let voiceController: DesktopVoiceController | null = null;
let voicePlayback: BrowserVoicePlayback | null = null;
let voiceHotkey: VoiceHotkeyController | null = null;
let voiceSettings: SettingsFormData["voice"];
let isQuitting = false;
let bridgeShutdownStarted = false;

if (!hasSingleInstanceLock) {
  app.quit();
}

protocol.registerSchemesAsPrivileged([
  {
    scheme: localAssetScheme,
    privileges: localAssetSchemePrivileges,
  },
]);

function configureUserDataPath(): void {
  const requestedUserDataDir = process.env.SHIORI_DESKTOP_USER_DATA_DIR;
  if (!requestedUserDataDir) {
    return;
  }
  const userDataDir = resolve(requestedUserDataDir);
  mkdirSync(userDataDir, { recursive: true });
  app.setPath("userData", userDataDir);
}

configureUserDataPath();

process.on("uncaughtException", (error) => {
  logDesktopDiagnostic({
    scope: "main",
    event: "process.uncaughtException",
    payload: {
      error,
    },
  });
});

process.on("unhandledRejection", (reason) => {
  logDesktopDiagnostic({
    scope: "main",
    event: "process.unhandledRejection",
    payload: {
      reason,
    },
  });
});

app.on("child-process-gone", (_event, details) => {
  logDesktopDiagnostic({
    scope: "main",
    event: "app.child-process-gone",
    payload: {
      type: details.type,
      reason: details.reason,
      exitCode: details.exitCode,
      serviceName: details.serviceName,
      name: details.name,
    },
  });
});

app.on("second-instance", () => {
  logDesktopDiagnostic({
    scope: "main",
    event: "app.second-instance",
    payload: {},
  });
  showOrCreateDesktopWindow();
});

async function openLocalAttachment(value: string) {
  const result = await openGrantedLocalAsset(localAssets, value, (path) => shell.openPath(path));
  if (result.error) {
    logDesktopDiagnostic({
      scope: "main",
      event: "asset.open.failed",
      payload: { error: result.error },
    });
  }
  return result;
}

/**
 * Where the pet's data lived before plugins had a store.
 *
 * Handed to `PluginDataStore` as a one-off migration source so an existing
 * installation keeps its remembered positions and its visible/hidden choice
 * when the pet's settings move into `plugin-data/desktop_pet.json` (#181-C).
 * Nothing else in the host reads this path.
 */
function legacyPluginDataPath(pluginId: string): string | null {
  if (pluginId !== desktopPetPluginId) return null;
  return resolve(app.getPath("userData"), "desktop-pet.json");
}

/**
 * Publishes a host-originated event into the same stream backend events use.
 *
 * This is how the host still reaches the pet's background code (the tray entry,
 * `desktop:pet-sync`, observation) now that no pet object exists in this
 * process. Deliberately the *same* envelope `wireBridgeEvents` sends, so a
 * plugin receives it on the ordinary `ctx.events.on` with no second mechanism
 * to learn. See `pluginCoupling/desktopPet.ts` for what removes each caller.
 */
function publishDesktopEvent(method: string, payload: Record<string, unknown>): void {
  const transport: LocalAssetTransport<BridgeEvent> = {
    value: { id: `host-${method}-${Date.now()}`, type: "event", method, payload },
    assets: [],
  };
  for (const window of BrowserWindow.getAllWindows()) {
    window.webContents.send("desktop:event", transport);
  }
}

function requestDesktopPetCommand(command: DesktopPetCommand): void {
  publishDesktopEvent(desktopPetCommandMethod, { ...command });
}

/** Whether the pet's surface window currently exists, asked of the capability that owns it. */
function isDesktopPetRunning(): boolean {
  return Boolean(desktopSurfaces?.has(desktopPetSurfaceKey));
}

function requestAppQuit(): void {
  isQuitting = true;
  app.quit();
}

function publishVoiceState(payload: VoiceStatePayload): void {
  for (const window of BrowserWindow.getAllWindows()) {
    window.webContents.send("desktop:voice-state", payload);
  }
}

function syncVoiceAvailability(cancelCurrentTurn = true): void {
  const hotkey = voiceHotkey;
  if (!hotkey) return;
  const available = isVoiceHotkeyAvailable({
    voiceEnabled: Boolean(voiceSettings?.enabled),
    petRunning: isDesktopPetRunning(),
    petVisible: desktopPetPresence.visible,
  });
  applyVoiceAvailability(available, cancelCurrentTurn, {
    start: () => hotkey.start(),
    stop: () => hotkey.stop(),
    stopAfterCurrentPress: () => hotkey.stopAfterCurrentPress(),
    cancelCurrentTurn: () => voiceController?.cancel(),
  });
}

function syncDesktopPetRuntimeState(): void {
  desktopTray?.refresh();
  syncVoiceAvailability();
}

function reloadVoiceSettings(): void {
  voiceSettings = loadSettingsData().formData.voice;
  voiceHotkey?.setHotkey(voiceSettings.hotkey);
  // Applying settings changes admission of new input; existing voice work keeps its owner.
  syncVoiceAvailability(false);
}

/**
 * Reacts to the pet plugin having written its settings.
 *
 * Since #181-C the host cannot await a pet operation — it publishes a command
 * and the plugin acts on it. This is the other half: the plugin's store write
 * is what tells the host the pet started or stopped, and it lands *after* the
 * surface was created or destroyed, so `isDesktopPetRunning()` is already
 * correct by the time anything here reads it. It also covers changes the host
 * never asked for, which the old `await pet.hide()` path did not.
 */
function handleDesktopPetSettingsChanged(stored: unknown): void {
  desktopPetPresence = readDesktopPetPresence(stored);
  syncDesktopPetRuntimeState();
  void desktopObservation?.restore().catch((error) => {
    logDesktopDiagnostic({ scope: "main", event: "desktop-observation.restore.failed", payload: { error } });
  });
}

function shouldHideDesktopWindowOnClose(): boolean {
  return shouldHideDesktopWindowOnClosePolicy({
    isQuitting,
    trayLifecycleEnabled,
    desktopPetRunning: isDesktopPetRunning() || desktopPetPresence.visible,
  });
}

function wireDesktopWindow(window: BrowserWindow): BrowserWindow {
  attachDesktopWindowLifecycle(window, {
    shouldHideOnClose: shouldHideDesktopWindowOnClose,
  });
  window.on("closed", () => {
    if (desktopWindow === window) {
      desktopWindow = null;
    }
  });
  return window;
}

function getOrCreateDesktopWindow(): BrowserWindow {
  if (desktopWindow) {
    return desktopWindow;
  }
  desktopWindow = wireDesktopWindow(createDesktopWindow({
    openLocalAttachment,
  }));
  return desktopWindow;
}

function showOrCreateDesktopWindow(): BrowserWindow {
  const window = getOrCreateDesktopWindow();
  showDesktopWindow(window);
  return window;
}

void app.whenReady().then(async () => {
  ensureDesktopRuntimeConfig(runtimePaths);
  configureSettingsConfigPath(runtimePaths.configPath);
  reloadVoiceSettings();
  process.env.SHIORI_DESKTOP_USER_DATA_DIR = app.getPath("userData");
  // Per-plugin persisted state (#181-C). Read before the tray exists so its
  // "显示桌宠/隐藏桌宠" entry is right on the first paint rather than after the
  // pet plugin's first write.
  const activePluginData = new PluginDataStore({
    directory: resolve(app.getPath("userData"), "plugin-data"),
    legacyPathFor: legacyPluginDataPath,
    onError: (pluginId, operation, error) => {
      logDesktopDiagnostic({ scope: "main", event: "plugin-data.failed", payload: { pluginId, operation, error } });
    },
  });
  activePluginData.onChanged((pluginId, value) => {
    if (pluginId === desktopPetPluginId) handleDesktopPetSettingsChanged(value);
  });
  registerDesktopPluginDataIpc(activePluginData);
  desktopPetPresence = readDesktopPetPresence(await activePluginData.read(desktopPetPluginId));
  const activeVoiceRecorder = new BrowserVoiceRecorder(createVoiceCaptureWindow);
  voiceRecorder = activeVoiceRecorder;
  const privateWorkspaceRoot = runtimePaths.workspacePath;
  const localAssetImportsRoot = resolve(privateWorkspaceRoot, "private_runtime", "imports");
  localAssets.addTrustedRoot(privateWorkspaceRoot);
  registerDesktopContentSecurityPolicy(
    session.defaultSession.webRequest,
    process.env.SHIORI_RENDERER_DEV_SERVER_URL,
  );
  registerLocalAssetProtocol(protocol, localAssets);
  void startBridge(bridge);
  const currentVersion = !app.isPackaged && process.env.SHIORI_DEV_VERSION || app.getVersion();
  registerDesktopUpdates(app.isPackaged, currentVersion, (error) => {
    logDesktopDiagnostic({ scope: "main", event: "updater.check.failed", payload: { error } });
  });
  // DesktopSurface (#181). No pet-specific code remains on this side: since
  // #181-C the pet's controller lives in `plugins/desktop_pet/background/` and
  // reaches these primitives over IPC like any other plugin would.
  const activeDesktopSurfaces = new DesktopSurfaceHost({
    createWindow: (key, spec) => createDesktopSurfaceWindow(key, spec, { openLocalAttachment }),
    workAreaFor: workAreaForSurface,
    displayIdFor: displayIdForSurface,
    cursorScreenPoint,
    showContextMenu: showSurfaceContextMenu,
    activateMainWindow: showOrCreateDesktopWindow,
    // Forwarded to the plugin-host renderer rather than handled here: the code
    // that decides whether a settle is worth remembering belongs to whichever
    // plugin owns the surface. Only that window is sent it — it is the only one
    // running `app.background` code, and the surface's own renderer already
    // gets its placement on `surfacePositionChannel`.
    onSettled: (key, placement, reason) => {
      if (!pluginHostWindow || pluginHostWindow.isDestroyed()) return;
      const payload: SurfaceSettledPayload = {
        pluginId: key.pluginId,
        surfaceId: key.surfaceId,
        placement,
        reason,
        displayId: activeDesktopSurfaces.displayId(key),
      };
      pluginHostWindow.webContents.send(surfaceSettledChannel, payload);
    },
  });
  desktopSurfaces = activeDesktopSurfaces;
  registerDesktopSurfaceIpc(activeDesktopSurfaces);
  // Dedicated hidden window for plugin `app.background` code (#226 item 1).
  // Created once here, after the surface IPC it depends on is registered but
  // before any plugin could possibly need it; destroyed in `before-quit`.
  //
  // Side effect worth knowing before touching `window-all-closed` below:
  // because this window is always alive from here to quit, Electron's
  // `window-all-closed` event (which fires only once *every* BrowserWindow
  // is gone) can no longer fire from the main window closing alone — there
  // is always at least this one left. On Windows that is invisible:
  // `trayLifecycleEnabled` is `true`, so the handler below already returns
  // early before checking window count. It would matter on Linux, where
  // `trayLifecycleEnabled` is `false` and that handler currently calls
  // `app.quit()` on this event — closing the main window would no longer
  // quit the app there. The repo only packages Windows today, so this is
  // deliberately left as-is rather than fixed; if Linux/macOS packaging
  // ever happens, this is the first place to revisit.
  pluginHostWindow = createPluginHostWindow();
  desktopObservation = new DesktopObservationController({
    pet: {
      get isRunning() { return isDesktopPetRunning(); },
      publishObservation: (payload) => publishDesktopEvent(desktopPetObservationMethod, { ...payload }),
    },
    getRoleId: () => desktopPetPresence.roleId,
  });
  const activeVoiceController = new DesktopVoiceController({
    recorder: activeVoiceRecorder,
    bridge,
    isEnabled: () => Boolean(
      voiceSettings?.enabled
      && isDesktopPetRunning()
      && desktopPetPresence.visible
      && !activeVoiceRecorder.isBusy
    ),
    roleId: () => desktopPetPresence.roleId,
    microphoneDeviceId: () => voiceSettings?.microphoneDeviceId ?? "",
    publishState: publishVoiceState,
    onNewInput: (previousTurnId, nextTurnId) => {
      void selectVoiceTurn(bridge, activeVoicePlayback, previousTurnId, nextTurnId).catch((error) => {
        logDesktopDiagnostic({
          scope: "main",
          event: "voice-turn.cancel.failed",
          payload: { error, previousTurnId, nextTurnId },
        });
      });
    },
    onCancelTurn: (turnId) => {
      activeVoicePlayback.cancelTurn(turnId);
      void cancelVoiceTurn(bridge, turnId).catch((error) => {
        logDesktopDiagnostic({
          scope: "main",
          event: "voice-turn.cancel.failed",
          payload: { error, turnId },
        });
      });
    },
  });
  voiceController = activeVoiceController;
  const activeVoicePlayback = new BrowserVoicePlayback(
    createVoiceCaptureWindow,
    createVoicePlaybackCallbacks(activeVoiceController),
  );
  voicePlayback = activeVoicePlayback;
  if (process.platform === "win32") {
    voiceHotkey = new VoiceHotkeyController({
      onPress: (source) => activeVoiceController.startPress(source),
      onRelease: (source) => activeVoiceController.release(source),
      onCancel: () => activeVoiceController.cancel(),
    });
    voiceHotkey.setHotkey(voiceSettings.hotkey);
  }
  // `desktop.pet.action` is no longer intercepted here: since #181-C the pet
  // subscribes to it itself through `ctx.events.on`, and `wireBridgeEvents`
  // already broadcasts every backend event to the plugin-host window.
  wireBridgeEvents(bridge, localAssets, (event) => {
    if (handleVoiceBridgeEvent(event, activeVoiceController, activeVoicePlayback)) return;
  });
  wireRoleReplyBubbles(bridge, desktopObservation);
  powerMonitor.on("lock-screen", () => {
    void desktopObservation?.suspend("Windows 已锁定，屏幕观察已暂停").catch((error) => {
      logDesktopDiagnostic({ scope: "main", event: "desktop-observation.suspend.failed", payload: { error } });
    });
  });
  powerMonitor.on("unlock-screen", () => {
    void desktopObservation?.resume().catch((error) => {
      logDesktopDiagnostic({ scope: "main", event: "desktop-observation.resume.failed", payload: { error } });
    });
  });
  registerDesktopIpc({
    bridge,
    localAssets,
    localAssetImportsRoot,
    openLocalAttachment,
    requestDesktopPetCommand,
    isPetWindow: (window) => isDesktopPetWindow(activeDesktopSurfaces, window),
    desktopObservation,
    voiceRecorder: activeVoiceRecorder,
    voiceController: activeVoiceController,
    voicePlayback: activeVoicePlayback,
    onVoiceSettingsChanged: reloadVoiceSettings,
  });
  getOrCreateDesktopWindow();
  if (trayLifecycleEnabled) {
    desktopTray = createDesktopTray({
      onShowWindow: () => {
        showOrCreateDesktopWindow();
      },
      onQuitRequested: requestAppQuit,
      getDesktopPetState: () => ({
        visible: desktopPetPresence.visible,
        available: desktopPetPresence.available,
      }),
      // Fire-and-forget: the toggle is a request to the pet plugin, not a call
      // into an object this process owns. The menu label catches up when the
      // plugin writes its settings back (`handleDesktopPetSettingsChanged`),
      // which the tray's own `refresh` after this promise settles also picks
      // up on the next open.
      onToggleDesktopPet: async () => {
        requestDesktopPetCommand({ kind: desktopPetPresence.visible ? "hide" : "show" });
      },
    });
    // No `restore()` call here any more: the pet restores itself in its
    // `setup(ctx)` when the plugin host starts it, and tells the host what it
    // decided through its settings write.
  }
  app.on("activate", () => {
    showOrCreateDesktopWindow();
  });
}).catch((error) => {
  logDesktopDiagnostic({
    scope: "main",
    event: "app.whenReady.failed",
    payload: {
      error,
    },
  });
  app.exit(1);
});

// Since #226 this fires far less than it reads: the plugin-host window is
// created at startup and lives until quit, so "all windows closed" is no
// longer true merely because the user closed the main window. On Windows that
// is invisible — `trayLifecycleEnabled` is true, so this handler already
// returned early there. On Linux, where the tray lifecycle is off, closing the
// main window would previously have quit the app through here and now will not.
// Nothing packages Linux today; see `createPluginHostWindow`'s call site.
app.on("window-all-closed", () => {
  if (!isQuitting && trayLifecycleEnabled) {
    return;
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", (event) => {
  isQuitting = true;
  desktopTray?.destroy();
  if (pluginHostWindow && !pluginHostWindow.isDestroyed()) {
    pluginHostWindow.destroy();
  }
  pluginHostWindow = null;
  voiceHotkey?.stop();
  voiceController?.dispose();
  voicePlayback?.dispose();
  voiceRecorder?.dispose();
  if (bridgeShutdownStarted || !bridge.isRunning()) {
    return;
  }
  event.preventDefault();
  bridgeShutdownStarted = true;
  void (async () => {
    try {
      await desktopObservation?.shutdown();
    } catch (error) {
      logDesktopDiagnostic({ scope: "main", event: "desktop-observation.shutdown.failed", payload: { error } });
    } finally {
      await bridge.stop();
      app.quit();
    }
  })();
});

export { bridge };
