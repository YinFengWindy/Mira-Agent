import { useCallback, useEffect, useRef, useState } from "react";
import { loadOnboardingData } from "./onboardingData";
import type { useDesktopBridgeLifecycle } from "../app/useDesktopBridgeLifecycle";

/** Refreshes first-run prerequisites and invalidates stale responses across bridge restarts. */
export function useOnboardingSnapshot(enabled: boolean, bridgeLifecycle: ReturnType<typeof useDesktopBridgeLifecycle>) {
  const [data, setData] = useState<Awaited<ReturnType<typeof loadOnboardingData>> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const request = useRef(0);
  const refresh = useCallback(async () => {
    const id = ++request.current;
    setLoading(true);
    setError("");
    try {
      const loaded = await loadOnboardingData(window.miraDesktop);
      if (id !== request.current) return;
      setData(loaded);
      return loaded;
    } catch (error) {
      if (id !== request.current) return;
      setData(null);
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      if (id === request.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    if (!enabled) return;
    void refresh();
    const off = window.miraDesktop.onEvent((event) => {
      if (event.method === "runtime.applied") void refresh();
      if (event.method === "bridge.exit") {
        request.current += 1;
        setData(null);
        setLoading(false);
        setError(String(event.payload.message ?? "连接桥已停止。"));
      }
    });
    const onFocus = () => { void refresh(); };
    window.addEventListener("focus", onFocus);
    return () => { request.current += 1; off(); window.removeEventListener("focus", onFocus); };
  }, [enabled, refresh]);
  const retry = async () => {
    setLoading(true);
    setError("");
    try {
      const status = await window.miraDesktop.bridgeStatus();
      if (!status.running) {
        await bridgeLifecycle.restartBridge();
      } else await bridgeLifecycle.refreshBridge();
      await refresh();
    } catch (error) {
      setLoading(false);
      setError(error instanceof Error ? error.message : String(error));
    }
  };
  return { data, error, loading, refresh, retry };
}
