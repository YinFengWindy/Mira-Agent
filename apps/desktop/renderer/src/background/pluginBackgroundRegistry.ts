import { PluginContributionRegistry } from "../plugins/pluginContributionRegistry";
import type { BackgroundEffectDispose } from "./backgroundEffectScope";
import type { SurfacePlacementPayload, SurfaceSpecPayload } from "../../../src/bridge/shared";
import type { PluginRpcClient } from "../plugins/pluginBridgeClient";

/**
 * The plugin's own view of the DesktopSurface capability, pre-bound to its
 * plugin id — the same treatment `createPluginRpcClient` gives `ctx.rpc`, so
 * a background module never passes its own id around by hand. Mirrors
 * `DesktopSurfacesApi` one for one, minus the leading `pluginId` argument.
 */
export type PluginBackgroundSurfaces = {
  create(
    surfaceId: string,
    spec: SurfaceSpecPayload,
    anchor: { x: number; y: number },
  ): Promise<{ x: number; y: number }>;
  destroy(surfaceId: string): Promise<void>;
  show(surfaceId: string): void;
  hide(surfaceId: string): void;
  workArea(surfaceId: string): Promise<SurfacePlacementPayload["workArea"]>;
  setPosition(surfaceId: string, position: { x: number; y: number }): void;
  moveTo(surfaceId: string, position: { x: number; y: number }, durationMs: number): void;
  post(surfaceId: string, message: unknown): void;
  setState(surfaceId: string, state: unknown): void;
};

/**
 * Backend event subscriptions for a background module.
 *
 * `on` filters the shared `desktop:event` stream (broadcast to every renderer
 * window, see `wireBridgeEvents`) down to one `method` name and auto-registers
 * its unsubscribe as an event-phase effect — see `BackgroundEffectScope` for
 * why that phase exists and what it prevents (#227).
 *
 * **This is not scoped to the calling plugin.** `BridgeEvent` carries no
 * per-plugin envelope today, so `method` is a flat, global string matched by
 * exact equality against every event on the bus — the same way the existing
 * `desktop.pet.action` event is named. Every background plugin's `events.on`
 * sees every plugin's events; nothing here restricts a handler to events its
 * own plugin caused. Do not assume `ctx.events` is namespaced the way
 * `ctx.rpc`/`ctx.surfaces` are (both are pre-bound to the calling plugin's
 * id) — it is reasonable to expect that from the shape of `ctx`, but it is
 * not true here. A plugin author must pick a method name namespaced to its
 * own id (e.g. `"<pluginId>.thing.happened"`) to avoid colliding with, or
 * accidentally reacting to, another plugin's events.
 */
export type PluginBackgroundEvents = {
  on(method: string, handler: (payload: Record<string, unknown>) => void): void;
};

/**
 * The handle a plugin's `background/index.ts` receives in `setup(ctx)`.
 *
 * Deliberately narrow — see the issue this shipped under (#226): no `tray`
 * capability yet (that arrives with #181-D, once the pet is its first real
 * consumer), and no access to the main window's DOM or React state, because
 * this code may not even be running in the same renderer as the main window.
 */
export type BackgroundCtx = {
  surfaces: PluginBackgroundSurfaces;
  rpc: PluginRpcClient;
  events: PluginBackgroundEvents;
  /**
   * Registers a disposable side effect (a controller's `terminate()`, a
   * timer, a connection). Always disposed *after* every `events.on`
   * subscription has been unsubscribed — see `BackgroundEffectScope`.
   */
  effect(label: string, dispose: BackgroundEffectDispose): void;
};

/** One plugin's `app.background` contribution: its always-resident setup function. */
export type PluginBackgroundEntry = {
  slot: "app.background";
  pluginId: string;
  setup(ctx: BackgroundCtx): void | Promise<void>;
};

/**
 * Plugin-owned headless background contributions, kept in a registry of their
 * own rather than in `pluginUiRegistry` or `pluginSurfaceRegistry`.
 *
 * Same reasoning as `pluginSurfaceRegistry.ts`: this registry is loaded by the
 * `plugin-host.html` bundle, which must not carry the main window's settings
 * UI (`pluginUiRegistry`) or any surface component (`pluginSurfaceRegistry`) —
 * it has no DOM to render either of those into.
 */
export class PluginBackgroundRegistry extends PluginContributionRegistry<PluginBackgroundEntry> {
  constructor() {
    super("pluginBackgroundRegistry", "app.background");
  }
}

/** Process-wide background registry; populated at module load by `pluginBackgroundModules.ts`. */
export const pluginBackgroundRegistry = new PluginBackgroundRegistry();
