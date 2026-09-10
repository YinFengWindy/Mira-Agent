import { useEffect, useSyncExternalStore } from "react";
import {
  ensurePluginEnabledStateLoaded,
  getPluginEnabledPredicate,
  subscribePluginEnabledState,
} from "./pluginEnabledStateStore";

/**
 * Subscribes to the shared plugin-enabled cache and triggers its first
 * load. Uses `useSyncExternalStore` (rather than a hand-rolled
 * subscribe/`useReducer` pair) so React can correctly interleave this
 * external store with concurrent rendering, and returns the store's own
 * predicate reference — which changes identity on every update — instead of
 * a fixed module-level function, so a consumer that memoizes against it
 * recomputes instead of reading a stale result.
 */
export function usePluginEnabledState(): (pluginId: string) => boolean {
  const isPluginEnabled = useSyncExternalStore(
    subscribePluginEnabledState,
    getPluginEnabledPredicate,
    getPluginEnabledPredicate,
  );
  useEffect(() => {
    void ensurePluginEnabledStateLoaded();
  }, []);
  return isPluginEnabled;
}
