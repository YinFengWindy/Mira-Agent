import { createPluginRpcClient } from "../plugins/pluginBridgeClient";
// The main process builds this query string; sharing the parser keeps the two
// sides from drifting. `entry.ts` only imports a *type* from `host.ts`, so
// nothing main-process-only is pulled into the surface bundle.
import { surfaceKeyFromSearch } from "../../../src/surface/entry";
import {
  pluginSurfaceRegistry,
  type PluginSurfaceRegistry,
  type SurfaceHandle,
} from "./pluginSurfaceRegistry";

/**
 * Mounts whichever plugin owns this surface window.
 *
 * A surface window is transparent and always on top, so a failure here would
 * otherwise be *invisible* — an empty rectangle floating over the desktop with
 * nothing to click and no error anywhere the user can reach. Every failure
 * path below therefore renders something readable and logs, rather than
 * returning null.
 */
export function SurfaceRoot(props: {
  search: string;
  surface: SurfaceHandle;
  registry?: PluginSurfaceRegistry;
}) {
  const key = surfaceKeyFromSearch(props.search);
  if (!key) {
    console.error("[surface] 窗口 URL 缺少 plugin/surface 参数，无法确定要挂载哪个插件");
    return <SurfaceFailure detail="窗口参数缺失" />;
  }
  const entry = (props.registry ?? pluginSurfaceRegistry).get(key.pluginId);
  if (!entry) {
    console.error(`[surface] 插件 ${key.pluginId} 没有注册 desktop.surface`);
    return <SurfaceFailure detail={`插件 ${key.pluginId} 未提供桌面窗口`} />;
  }
  const Component = entry.Component;
  return (
    <Component
      surfaceId={key.surfaceId}
      surface={props.surface}
      client={createPluginRpcClient(key.pluginId)}
    />
  );
}

/** A deliberately visible, draggable-free failure card; see `SurfaceRoot`. */
function SurfaceFailure(props: { detail: string }) {
  return (
    <div
      role="alert"
      style={{
        padding: "8px 12px",
        borderRadius: 8,
        background: "rgba(24, 24, 27, 0.92)",
        color: "#fca5a5",
        font: "12px/1.5 system-ui, sans-serif",
      }}
    >
      桌面窗口加载失败：{props.detail}
    </div>
  );
}
