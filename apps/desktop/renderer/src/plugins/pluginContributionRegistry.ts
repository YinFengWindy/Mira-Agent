/** Anything registered per plugin id: one contribution of a given slot. */
export type PluginContribution = { pluginId: string };

/**
 * One plugin contribution per plugin id, first registration wins.
 *
 * Extracted because `pluginSurfaceRegistry` and `pluginBackgroundRegistry` had
 * become the same class twice over, differing only in entry type and log
 * prefix. (`pluginUiRegistry` is deliberately NOT built on this: it keeps two
 * maps, tracks builtin-vs-plugin origin, and orders and filters what it
 * returns — genuinely different behaviour, not the same shape.)
 *
 * The *instances* still have to stay separate, and that is the point worth
 * remembering: `plugin-host.html`, `surface.html` and the main window are
 * separate Electron renderer processes with separate module state, so sharing
 * one singleton across slots would not work even if the bundles allowed it.
 * What is shared here is the logic, not the storage.
 *
 * A duplicate id is warned about and skipped rather than replacing the
 * incumbent: two plugins claiming one id is a packaging mistake, and silently
 * letting whichever loaded last win would make the resulting behaviour depend
 * on glob ordering.
 */
export class PluginContributionRegistry<TEntry extends PluginContribution> {
  private readonly entries = new Map<string, TEntry>();

  /**
   * @param logLabel Identifies this registry in the duplicate-registration warning.
   * @param slotLabel The slot name shown in that warning, e.g. `desktop.surface`.
   */
  constructor(
    private readonly logLabel: string,
    private readonly slotLabel: string,
  ) {}

  register(entry: TEntry): void {
    if (this.entries.has(entry.pluginId)) {
      console.warn(`[${this.logLabel}] ${this.slotLabel} 重复注册，已跳过: ${entry.pluginId}`);
      return;
    }
    this.entries.set(entry.pluginId, entry);
  }

  get(pluginId: string): TEntry | undefined {
    return this.entries.get(pluginId);
  }

  unregister(pluginId: string): void {
    this.entries.delete(pluginId);
  }

  list(): TEntry[] {
    return [...this.entries.values()];
  }
}
