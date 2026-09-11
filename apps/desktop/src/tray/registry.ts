/** One tray menu item contributed by a plugin. */
export type PluginTrayEntry = {
  pluginId: string;
  entryId: string;
  label: string;
  enabled: boolean;
};

/** What a plugin supplies when it adds or updates its entry. */
export type PluginTrayEntryInput = {
  label: string;
  enabled?: boolean;
};

export class PluginTrayError extends Error {}

/**
 * Holds the tray menu items plugins have contributed, independently of whether
 * a tray actually exists.
 *
 * Separate from `tray.ts` for two reasons, both load-bearing:
 *
 * - **Ordering.** The plugin-host window is created well before the tray
 *   (`main.ts`), so a plugin's `setup(ctx)` can contribute an entry while
 *   `desktopTray` is still `null`. Holding the entries here means that is
 *   ordinary rather than a race to get right.
 * - **Platform.** `trayLifecycleEnabled` is Windows-only; elsewhere no `Tray`
 *   is ever constructed. A plugin must not have to know that, so contributing
 *   an entry on a platform with no tray is accepted and simply never rendered.
 *
 * It is also the seam that keeps `tray.ts` free of plugin concepts: that file
 * renders a list and reports clicks, and has no idea the desktop pet exists.
 */
export class PluginTrayRegistry {
  /** Keyed by `entryKey`; a Map, so menu order is contribution order. */
  private readonly entries = new Map<string, PluginTrayEntry>();
  private readonly listeners = new Set<() => void>();

  /**
   * Adds an entry, or updates one already contributed under the same id.
   *
   * Updating in place rather than remove-then-add is deliberate: the desktop
   * pet rewrites its label every time it is shown or hidden, and re-inserting
   * would make the item jump to the bottom of the menu each time.
   */
  setEntry(pluginId: string, entryId: string, entry: PluginTrayEntryInput): void {
    const key = entryKey(pluginId, entryId);
    const label = entry.label.trim();
    if (!label) throw new PluginTrayError(`托盘条目缺少标签: ${key}`);
    this.entries.set(key, {
      pluginId,
      entryId,
      label,
      enabled: entry.enabled ?? true,
    });
    this.notify();
  }

  removeEntry(pluginId: string, entryId: string): void {
    if (this.entries.delete(entryKey(pluginId, entryId))) this.notify();
  }

  /**
   * Drops everything one plugin contributed.
   *
   * This is what makes #181's "停用桌宠插件后...托盘...全部回收" true: the host
   * holds the entries, so reclaiming them does not depend on disabled plugin
   * code running. The plugin's own effect calls this, and the host can also
   * call it directly when the plugin host renderer dies.
   */
  removeAllForPlugin(pluginId: string): void {
    let removed = false;
    for (const [key, entry] of [...this.entries]) {
      if (entry.pluginId !== pluginId) continue;
      this.entries.delete(key);
      removed = true;
    }
    if (removed) this.notify();
  }

  /**
   * Drops every entry from every plugin.
   *
   * For the case where the process that owns all of them is gone: every entry
   * is driven from the plugin-host renderer, so that renderer crashing leaves
   * a menu of items whose click handlers can never run again — worse than no
   * item, because the user clicks and nothing happens.
   */
  clear(): void {
    if (!this.entries.size) return;
    this.entries.clear();
    this.notify();
  }

  /** Every contributed entry, in contribution order. */
  list(): PluginTrayEntry[] {
    return [...this.entries.values()];
  }

  /** Notified whenever the menu would render differently. */
  onChanged(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    for (const listener of this.listeners) listener();
  }
}

/**
 * Identifies one entry by both ids, serialized rather than joined.
 *
 * Same reasoning as `petSurfaceLoadSignature` in the pet's surface code:
 * neither id is validated for content here, so any separator we picked could
 * in principle appear inside one of them — plugin `a` with entry `b:c` and
 * plugin `a:b` with entry `c` would collide, and one would silently overwrite
 * the other's menu item. JSON has no such ambiguity.
 */
function entryKey(pluginId: string, entryId: string): string {
  return JSON.stringify([pluginId, entryId]);
}
