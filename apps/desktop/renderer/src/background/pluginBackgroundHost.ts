import { BackgroundEffectScope } from "./backgroundEffectScope";
import type { BackgroundCtx, PluginBackgroundEntry } from "./pluginBackgroundRegistry";

/** A registry surface narrow enough to fake in tests without the real singleton. */
export type PluginBackgroundRegistryLike = { list(): PluginBackgroundEntry[] };

export type PluginBackgroundHostDeps = {
  registry: PluginBackgroundRegistryLike;
  /** Fetches the current enabled-plugin roster; called at startup and on every reconcile. */
  listEnabledPluginIds(): Promise<Set<string>>;
  /** Subscribes to whatever signals "the enabled roster may have changed"; returns an unsubscribe. */
  subscribeRosterChanged(listener: () => void): () => void;
  createCtx(pluginId: string, scope: BackgroundEffectScope): BackgroundCtx;
  onError?(pluginId: string, phase: "setup" | "dispose", error: unknown): void;
};

/**
 * Runs every registered `app.background` contribution whose plugin is
 * currently enabled, and tears it down the moment it is not.
 *
 * This is the piece that makes "停用插件后...订阅全部回收" (#181's acceptance
 * criterion) real rather than aspirational: disabling a plugin disposes its
 * `BackgroundEffectScope`, which — per that type's own contract — always
 * unsubscribes its backend event listeners before running any other cleanup
 * (#227).
 *
 * This window has no `pluginEnabledStateStore` of its own (that store is
 * populated by the *main window's* plugin management UI — see
 * `usePluginManagementController.ts` — and this is a different renderer
 * entirely). Instead of duplicating that store, this host asks the backend
 * directly (`listEnabledPluginIds`, backed by `plugins.list`) at startup and
 * again whenever `subscribeRosterChanged` fires. In `main.ts` that signal is
 * the existing `runtime.applied` bridge event, which already fires for a
 * plugin enable/disable toggle (`RuntimePluginManagement.set_enabled` routes
 * through the same `RuntimeSettingsApplication.apply` that publishes it) —
 * no new backend event was needed for this PR.
 */
export class PluginBackgroundHost {
  private readonly running = new Map<string, BackgroundEffectScope>();
  private unsubscribeRosterChanged: (() => void) | null = null;
  // Serializes reconcile() calls: a `runtime.applied` burst (e.g. several
  // settings changes landing close together) must not run two reconciles
  // concurrently against the same `running` map.
  private queue: Promise<void> = Promise.resolve();

  constructor(private readonly deps: PluginBackgroundHostDeps) {}

  /** Runs the first reconcile and starts listening for roster changes. */
  async start(): Promise<void> {
    await this.reconcile();
    this.unsubscribeRosterChanged = this.deps.subscribeRosterChanged(() => {
      this.enqueue(() => this.reconcile());
    });
  }

  /** Tears down every currently running plugin and stops listening for roster changes. */
  async stop(): Promise<void> {
    this.unsubscribeRosterChanged?.();
    this.unsubscribeRosterChanged = null;
    await this.enqueue(async () => {
      await Promise.all([...this.running.keys()].map((pluginId) => this.teardown(pluginId)));
    });
  }

  /** Plugin ids with a currently running background scope; test/diagnostic use. */
  runningPluginIds(): string[] {
    return [...this.running.keys()];
  }

  private enqueue(task: () => Promise<void>): Promise<void> {
    this.queue = this.queue.then(task, task);
    return this.queue;
  }

  private async reconcile(): Promise<void> {
    const enabled = await this.deps.listEnabledPluginIds();
    for (const entry of this.deps.registry.list()) {
      const shouldRun = enabled.has(entry.pluginId);
      const isRunning = this.running.has(entry.pluginId);
      if (shouldRun && !isRunning) {
        await this.setup(entry);
      } else if (!shouldRun && isRunning) {
        await this.teardown(entry.pluginId);
      }
    }
  }

  private async setup(entry: PluginBackgroundEntry): Promise<void> {
    const scope = new BackgroundEffectScope();
    this.running.set(entry.pluginId, scope);
    try {
      await entry.setup(this.deps.createCtx(entry.pluginId, scope));
    } catch (error) {
      this.running.delete(entry.pluginId);
      this.deps.onError?.(entry.pluginId, "setup", error);
    }
  }

  private async teardown(pluginId: string): Promise<void> {
    const scope = this.running.get(pluginId);
    if (!scope) return;
    this.running.delete(pluginId);
    const errors = await scope.disposeAll();
    for (const error of errors) this.deps.onError?.(pluginId, "dispose", error);
  }
}
