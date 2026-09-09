import { createPluginBridgeClient, type PluginBridgeClient, type PluginSummary } from "./pluginBridgeClient";

type Listener = () => void;

// Module-level singleton: nav.page and settings.section visibility needs the
// same "is plugin X enabled" answer in several unrelated places (nav rail,
// settings sidebar, the settings page itself) that don't share a common
// mounted ancestor close enough for prop threading, and the plugin
// management list that flips the flag lives in yet another one. A small
// shared store (subscribe/notify, no external state library) is the
// narrowest thing that lets all of them agree on one answer immediately
// after a toggle, matching "停用后其 UI 入口...立即消失" (issue #174 AC 3).
let cache: Map<string, boolean> | null = null;
let inflight: Promise<void> | null = null;
const listeners = new Set<Listener>();

function notify(): void {
  for (const listener of listeners) listener();
}

/** Replaces the cached enabled flags wholesale (after a full `plugins.list` fetch). */
export function setPluginEnabledSnapshot(plugins: Pick<PluginSummary, "id" | "enabled">[]): void {
  cache = new Map(plugins.map((item) => [item.id, item.enabled]));
  notify();
}

/** Optimistically updates one plugin's flag immediately after a successful toggle. */
export function setPluginEnabledCache(pluginId: string, enabled: boolean): void {
  cache = new Map(cache ?? []);
  cache.set(pluginId, enabled);
  notify();
}

/** Synchronous read; a plugin not yet known to the cache is treated as enabled. */
export function isPluginEnabled(pluginId: string): boolean {
  return cache?.get(pluginId) ?? true;
}

/** Fetches the roster once (memoized); safe to call from multiple consumers. */
export async function ensurePluginEnabledStateLoaded(
  client: Pick<PluginBridgeClient, "listPlugins"> = createPluginBridgeClient(),
): Promise<void> {
  if (cache) return;
  if (!inflight) {
    inflight = client.listPlugins()
      .then((plugins) => setPluginEnabledSnapshot(plugins))
      .finally(() => { inflight = null; });
  }
  await inflight;
}

export function subscribePluginEnabledState(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Test-only: clears memoized state so each test starts from a clean cache. */
export function resetPluginEnabledStateForTests(): void {
  cache = null;
  inflight = null;
}
