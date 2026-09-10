import type React from "react";
import type { PluginRpcClient } from "../plugins/pluginBridgeClient";

/**
 * Placement the host pushes after a surface settles: where the body ended up,
 * where it sits inside its own window, and the work area it was clamped into.
 */
export type SurfacePlacement = {
  anchor: { x: number; y: number };
  bodyOffset: { x: number; y: number };
  workArea: { x: number; y: number; width: number; height: number };
};

/**
 * The self-directed half of the DesktopSurface capability, handed to a
 * plugin's surface component.
 *
 * Every call acts on the window the component is already rendering inside —
 * there is no surface id to pass, because the host attributes the request by
 * window identity rather than by anything the renderer claims.
 */
export type SurfaceHandle = {
  /** Starts host-driven cursor following; `offset` is where inside the body the pointer grabbed. */
  beginDrag(offset: { x: number; y: number }): void;
  /** Releases the drag, optionally handing over a velocity (px/s) for the host to glide out. */
  endDrag(velocity?: { x: number; y: number }): void;
  /** Grows or shrinks the window on one side without moving the body. */
  setExtension(extension: { side: "above" | "below"; size: number }): void;
  setClickThrough(clickThrough: boolean): void;
  /** Subscribes to placement updates; returns an unsubscribe function. */
  onPlacement(listener: (placement: SurfacePlacement) => void): () => void;
  /** Subscribes to payloads the plugin's own backend relayed to this surface. */
  onMessage(listener: (payload: unknown) => void): () => void;
};

/** Props a plugin-authored surface component receives. */
export type PluginSurfaceComponentProps = {
  surfaceId: string;
  surface: SurfaceHandle;
  client: PluginRpcClient;
};

/** One plugin's `desktop.surface` contribution. */
export type PluginSurfaceContribution = {
  component: React.ComponentType<PluginSurfaceComponentProps>;
};

export type PluginSurfaceEntry = {
  slot: "desktop.surface";
  pluginId: string;
  Component: React.ComponentType<PluginSurfaceComponentProps>;
};

/**
 * Plugin-owned desktop surfaces, kept in a registry of their own rather than
 * in `pluginUiRegistry`.
 *
 * The two serve different bundles: `pluginUiRegistry` is loaded by the main
 * window and pulls in the whole settings UI with it, while this one is loaded
 * by `surface.html` — a transparent always-on-top window that should carry
 * only what it draws. Sharing one registry would drag the entire main-window
 * UI into every surface window's bundle.
 */
class PluginSurfaceRegistry {
  private readonly entries = new Map<string, PluginSurfaceEntry>();

  register(entry: PluginSurfaceEntry): void {
    if (this.entries.has(entry.pluginId)) {
      console.warn(`[pluginSurfaceRegistry] desktop.surface 重复注册，已跳过: ${entry.pluginId}`);
      return;
    }
    this.entries.set(entry.pluginId, entry);
  }

  get(pluginId: string): PluginSurfaceEntry | undefined {
    return this.entries.get(pluginId);
  }

  unregister(pluginId: string): void {
    this.entries.delete(pluginId);
  }

  list(): PluginSurfaceEntry[] {
    return [...this.entries.values()];
  }
}

/** Process-wide surface registry; populated at module load by `pluginSurfaceModules.ts`. */
export const pluginSurfaceRegistry = new PluginSurfaceRegistry();

/** Exposed for tests that need an isolated registry instead of the shared singleton. */
export { PluginSurfaceRegistry };
