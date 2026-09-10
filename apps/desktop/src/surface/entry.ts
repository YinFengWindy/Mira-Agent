import type { SurfaceKey } from "./host.js";

/**
 * How a surface window learns which plugin it is rendering.
 *
 * Shared by the main process (which builds the URL) and the renderer entry
 * (which reads it back), so the two can never drift into disagreeing about
 * parameter names. Dependency-free: the renderer imports this too.
 */

const pluginParam = "plugin";
const surfaceParam = "surface";

/** Builds the query string identifying a surface, including the leading `?`. */
export function surfaceQueryString(key: SurfaceKey): string {
  const params = new URLSearchParams();
  params.set(pluginParam, key.pluginId);
  params.set(surfaceParam, key.surfaceId);
  return `?${params.toString()}`;
}

/**
 * Reads a surface key back out of a window location.
 *
 * Returns null rather than a partially-filled key when either half is missing,
 * so a surface entry loaded without its query string fails visibly instead of
 * mounting whichever plugin happens to sort first.
 */
export function surfaceKeyFromSearch(search: string): SurfaceKey | null {
  const params = new URLSearchParams(search);
  const pluginId = params.get(pluginParam) ?? "";
  const surfaceId = params.get(surfaceParam) ?? "";
  if (!pluginId || !surfaceId) return null;
  return { pluginId, surfaceId };
}
