import type {
  BridgeEvent,
  DesktopApi,
  DesktopSurfacesApi,
  SurfaceSettledPayload,
} from "../../../src/bridge/shared";
import { unavailableLocalAssetUrl } from "../../../src/assets/localAssetContract";
import type { DesktopInvoke } from "../shared/bridgeInvoke";
import { createPluginRpcClient } from "../plugins/pluginBridgeClient";
import type { BackgroundEffectScope } from "./backgroundEffectScope";
import type {
  BackgroundCtx,
  PluginBackgroundAssets,
  PluginBackgroundStore,
  PluginBackgroundSurfaces,
} from "./pluginBackgroundRegistry";

/** Subscribes to every surface settle this window is told about. */
export type SurfaceSettledSource = (
  listener: (settled: SurfaceSettledPayload) => void,
) => () => void;

/** Binds the shared `surfaces` bridge API to one plugin id, dropping it from every call. */
function createPluginBackgroundSurfaces(
  pluginId: string,
  api: DesktopSurfacesApi,
  onSurfaceSettled: SurfaceSettledSource,
  scope: BackgroundEffectScope,
): PluginBackgroundSurfaces {
  return {
    create: (surfaceId, spec, anchor) => api.create(pluginId, surfaceId, spec, anchor),
    destroy: (surfaceId) => api.destroy(pluginId, surfaceId),
    show: (surfaceId) => api.show(pluginId, surfaceId),
    hide: (surfaceId) => api.hide(pluginId, surfaceId),
    workArea: (surfaceId) => api.workArea(pluginId, surfaceId),
    setPosition: (surfaceId, position) => api.setPosition(pluginId, surfaceId, position),
    moveTo: (surfaceId, position, durationMs) => api.moveTo(pluginId, surfaceId, position, durationMs),
    post: (surfaceId, message) => api.post(pluginId, surfaceId, message),
    setState: (surfaceId, state) => api.setState(pluginId, surfaceId, state),
    onSettled(surfaceId, handler) {
      const unsubscribe = onSurfaceSettled((settled) => {
        if (settled.pluginId !== pluginId || settled.surfaceId !== surfaceId) return;
        handler({
          placement: settled.placement,
          reason: settled.reason,
          displayId: settled.displayId,
        });
      });
      // Event phase, exactly like `events.on`: a settle arriving while a
      // plugin's `ctx.effect` teardown is running would hand it work nothing
      // is left to undo. See `BackgroundEffectScope` (#227).
      scope.addEventEffect(`surface-settled:${surfaceId}`, unsubscribe);
    },
  };
}

/** Binds the host's plugin data store to one plugin id. */
function createPluginBackgroundStore(
  pluginId: string,
  pluginData: DesktopApi["pluginData"],
): PluginBackgroundStore {
  return {
    read: () => pluginData.read(pluginId),
    write: (value) => pluginData.write(pluginId, value),
  };
}

/** Maps the preload's "no grant" sentinel onto `null` for plugin code. */
function createPluginBackgroundAssets(localAssetUrl: (path: string) => string): PluginBackgroundAssets {
  return {
    url(path) {
      if (!path) return null;
      const url = localAssetUrl(path);
      // The preload answers an ungranted path with a fixed placeholder URL
      // rather than throwing. That is right for an `<img src>`, which needs
      // *something*, but wrong for a plugin deciding whether it can show a
      // package at all — so the sentinel becomes `null` here, at the one place
      // that knows what it means.
      return url && url !== unavailableLocalAssetUrl ? url : null;
    },
  };
}

/**
 * Builds the `ctx` handed to one plugin's `background/index.ts` `setup(ctx)`.
 *
 * `onEvent` is the raw, unfiltered `desktop:event` stream (see
 * `apps/desktop/src/bridge/bridgeLifecycle.ts::wireBridgeEvents`, which
 * broadcasts to every open renderer window, including this hidden one).
 * `ctx.events.on` filters it to one `method` and — this is the part that
 * matters for #227 — registers its own unsubscribe into `scope`'s
 * event phase rather than handing the caller an unsubscribe function to
 * manage itself, so a plugin cannot forget to release it, and it is always
 * released before `ctx.effect` entries regardless of call order.
 * `ctx.surfaces.onSettled` follows the same rule for the same reason.
 */
export function createBackgroundCtx(options: {
  pluginId: string;
  surfaces: DesktopSurfacesApi;
  invoke: DesktopInvoke;
  onEvent: (listener: (event: BridgeEvent) => void) => () => void;
  onSurfaceSettled: SurfaceSettledSource;
  pluginData: DesktopApi["pluginData"];
  localAssetUrl: (path: string) => string;
  scope: BackgroundEffectScope;
}): BackgroundCtx {
  const { pluginId, surfaces, invoke, onEvent, onSurfaceSettled, pluginData, localAssetUrl, scope } = options;
  return {
    surfaces: createPluginBackgroundSurfaces(pluginId, surfaces, onSurfaceSettled, scope),
    rpc: createPluginRpcClient(pluginId, invoke),
    events: {
      on(method, handler) {
        const unsubscribe = onEvent((event) => {
          if (event.method === method) handler(event.payload);
        });
        scope.addEventEffect(`event:${method}`, unsubscribe);
      },
    },
    store: createPluginBackgroundStore(pluginId, pluginData),
    assets: createPluginBackgroundAssets(localAssetUrl),
    effect(label, dispose) {
      scope.addEffect(label, dispose);
    },
  };
}
