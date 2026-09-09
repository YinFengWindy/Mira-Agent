import type { DesktopApi, SettingsFormData, SettingsSaveOptions, SettingsSnapshot } from "../../../src/bridge/shared.js";
import { SerialDraftQueue } from "../shared/serialDraftQueue.js";
import { cloneSettings, saveSettingsPageData, settingsEqual } from "./settingsPersistence.js";
import type { SettingsSavePhase } from "./settingsPageTypes.js";

type SaveQueueOptions = {
  api: Pick<DesktopApi, "readSettings" | "saveSettings">;
  onApplied: (snapshot: SettingsSnapshot, submitted: SettingsFormData, nextDraft: SettingsFormData) => void;
  onStatus: (phase: SettingsSavePhase, message: string) => void;
};

// Error codes the user can still fix by editing further, without reloading first.
const RECOVERABLE_WITHOUT_RELOAD = [
  "settings_validation_error", "runtime_config_invalid", "runtime_apply_failed", "runtime_invalid_request",
];

type Applied = { snapshot: SettingsSnapshot; nextDraft: SettingsFormData };

/** Serializes automatic saves and retains a failed transaction's identity for explicit retries. */
export class SettingsSaveQueue {
  private generation?: number;
  private readonly core: SerialDraftQueue<SettingsFormData, Applied>;

  constructor(private readonly options: SaveQueueOptions) {
    this.core = new SerialDraftQueue<SettingsFormData, Applied>({
      isEqual: settingsEqual,
      clone: cloneSettings,
      attempt: (draft, operationId) => this.attempt(draft, operationId),
      onApplied: (applied, submitted) => this.options.onApplied(applied.snapshot, submitted, applied.nextDraft),
      onStatus: (phase, message) => this.options.onStatus(phase, message),
    });
  }

  /** Seeds the version from a freshly loaded backend snapshot. */
  reset(generation: number | undefined): void {
    this.generation = generation;
    this.core.reset();
  }

  /** Schedules the newest draft; failed requests pause subsequent writes until retry or reload. */
  enqueue(draft: SettingsFormData, persisted?: SettingsFormData): void {
    this.core.enqueue(draft, persisted);
  }

  /** Retries the exact failed transaction before processing any newer queued edits. */
  retry(): void {
    this.core.retry();
  }

  private async attempt(draft: SettingsFormData, operationId: string) {
    const attemptOptions: SettingsSaveOptions = { expectedGeneration: this.generation, operationId };
    const result = await saveSettingsPageData(this.options.api, draft, attemptOptions);
    if (!result.saveResult.ok || !result.snapshot) {
      const code = result.saveResult.error?.code ?? "";
      return {
        ok: false as const,
        resumesAutomatically: RECOVERABLE_WITHOUT_RELOAD.includes(code),
        message: result.saveResult.error?.message ?? "配置应用失败。",
      };
    }
    this.generation = result.saveResult.generation;
    return { ok: true as const, result: { snapshot: result.snapshot, nextDraft: result.nextDraft } };
  }
}
