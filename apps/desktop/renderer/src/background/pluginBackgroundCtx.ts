import type { BridgeEvent, DesktopSurfacesApi } from "../../../src/bridge/shared";
import type { DesktopInvoke } from "../shared/bridgeInvoke";
import { createPluginRpcClient } from "../plugins/pluginBridgeClient";
import type { BackgroundEffectScope } from "./backgroundEffectScope";
import type { BackgroundCtx, PluginBackgroundSurfaces } from "./pluginBackgroundRegistry";

/** Binds the shared `surfaces` bridge API to one plugin id, dropping it from every call. */
function createPluginBackgroundSurfaces(pluginId: string, api: DesktopSurfacesApi): PluginBackgroundSurfaces {
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
 */
export function createBackgroundCtx(options: {
  pluginId: string;
  surfaces: DesktopSurfacesApi;
  invoke: DesktopInvoke;
  onEvent: (listener: (event: BridgeEvent) => void) => () => void;
  scope: BackgroundEffectScope;
}): BackgroundCtx {
  const { pluginId, surfaces, invoke, onEvent, scope } = options;
  return {
    surfaces: createPluginBackgroundSurfaces(pluginId, surfaces),
    rpc: createPluginRpcClient(pluginId, invoke),
    events: {
      on(method, handler) {
        const unsubscribe = onEvent((event) => {
          if (event.method === method) handler(event.payload);
        });
        scope.addEventEffect(`event:${method}`, unsubscribe);
      },
    },
    effect(label, dispose) {
      scope.addEffect(label, dispose);
    },
  };
}
