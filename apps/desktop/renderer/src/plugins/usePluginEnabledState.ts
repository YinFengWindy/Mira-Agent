import { useEffect, useReducer } from "react";
import { ensurePluginEnabledStateLoaded, isPluginEnabled, subscribePluginEnabledState } from "./pluginEnabledStateStore";

/** Subscribes to the shared plugin-enabled cache; triggers its first load. */
export function usePluginEnabledState(): (pluginId: string) => boolean {
  const [, forceRerender] = useReducer((count: number) => count + 1, 0);
  useEffect(() => {
    const unsubscribe = subscribePluginEnabledState(forceRerender);
    void ensurePluginEnabledStateLoaded();
    return unsubscribe;
  }, []);
  return isPluginEnabled;
}
