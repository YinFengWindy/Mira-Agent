import type { DesktopApi, SettingsFormData, SettingsSaveOptions, SettingsSnapshot } from "../../../src/bridge/shared.js";
import { cloneSettings, saveSettingsPageData, settingsEqual } from "./settingsPersistence.js";
import type { SettingsSavePhase } from "./settingsPageTypes.js";

type SaveQueueOptions = {
  api: Pick<DesktopApi, "readSettings" | "saveSettings">;
  onApplied: (snapshot: SettingsSnapshot, submitted: SettingsFormData, nextDraft: SettingsFormData) => void;
  onStatus: (phase: SettingsSavePhase, message: string) => void;
};

/** Serializes automatic saves and retains a failed transaction's identity for explicit retries. */
export class SettingsSaveQueue {
  private generation?: number;
  private running = false;
  private failed = false;
  private paused = false;
  private queued: SettingsFormData | null = null;
  private attempted: SettingsFormData | null = null;
  private attemptOptions: SettingsSaveOptions | null = null;

  constructor(private readonly options: SaveQueueOptions) {}

  /** Seeds the version from a freshly loaded backend snapshot. */
  reset(generation: number | undefined) {
    this.generation = generation;
    this.failed = false;
    this.paused = false;
    this.queued = null;
    this.attempted = null;
    this.attemptOptions = null;
  }

  /** Schedules the newest draft; failed requests pause subsequent writes until retry or reload. */
  enqueue(draft: SettingsFormData, persisted?: SettingsFormData) {
    if (!this.running && !this.failed && settingsEqual(persisted ?? null, draft)) {
      this.queued = null;
      return;
    }
    if (settingsEqual(this.attempted, draft)) {
      this.queued = null;
      return;
    }
    this.queued = cloneSettings(draft);
    if (!this.running && !this.paused) void this.drain();
  }

  /** Retries the exact failed transaction before processing any newer queued edits. */
  retry() {
    if (this.running || !this.failed || !this.attempted) return;
    this.failed = false;
    void this.drain(this.attempted);
  }

  private async drain(retry?: SettingsFormData) {
    const draft = retry ?? this.queued;
    if (!draft) return;
    if (!retry) {
      this.queued = null;
      this.attempted = cloneSettings(draft);
      this.attemptOptions = { expectedGeneration: this.generation, operationId: crypto.randomUUID() };
    }
    this.running = true;
    this.failed = false;
    this.options.onStatus("saving", "");
    try {
      const result = await saveSettingsPageData(this.options.api, draft, this.attemptOptions ?? undefined);
      if (!result.saveResult.ok || !result.snapshot) {
        this.failed = true;
        this.paused = !["settings_validation_error", "runtime_config_invalid", "runtime_apply_failed", "runtime_invalid_request"].includes(result.saveResult.error?.code ?? "");
        this.options.onStatus("error", result.saveResult.error?.message ?? "配置应用失败。");
        return;
      }
      this.generation = result.saveResult.generation;
      this.paused = false;
      this.options.onApplied(result.snapshot, draft, result.nextDraft);
      this.options.onStatus("idle", "");
    } catch (error) {
      this.failed = true;
      this.paused = true;
      this.options.onStatus("error", error instanceof Error ? error.message : String(error));
    } finally {
      this.running = false;
      if (!this.paused && this.queued) void this.drain();
    }
  }
}
