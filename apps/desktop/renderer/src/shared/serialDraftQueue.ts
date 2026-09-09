import type { SettingsSavePhase } from "../settings/settingsPageTypes.js";

/** Outcome of one submission attempt against the backend. */
export type DraftAttemptOutcome<TResult> =
  | { ok: true; result: TResult }
  | { ok: false; message: string; retryable: boolean };

export type SerialDraftQueueOptions<TDraft, TResult> = {
  /** Structural equality used to collapse no-op edits and detect obsolete queued drafts. */
  isEqual: (a: TDraft | null, b: TDraft | null) => boolean;
  /** Deep-clones a draft before it is queued or handed to a caller. */
  clone: (draft: TDraft) => TDraft;
  /** Submits one draft; `operationId` stays stable across retries of the same attempt. */
  attempt: (draft: TDraft, operationId: string) => Promise<DraftAttemptOutcome<TResult>>;
  /** Called once an attempt succeeds, with the backend result and the draft that produced it. */
  onApplied: (result: TResult, submitted: TDraft) => void;
  onStatus: (phase: SettingsSavePhase, message: string) => void;
};

/**
 * Serializes draft submissions, coalesces superseded edits, and preserves a
 * failed attempt's identity so an explicit retry reuses the same operation
 * id. Extracted so the "call backend -> refresh local state -> surface
 * status" autosave pattern is implemented once and shared by every domain
 * that needs it (see AGENTS.md on not duplicating this flow), rather than
 * being copy-pasted per settings domain.
 */
export class SerialDraftQueue<TDraft, TResult> {
  private running = false;
  private failed = false;
  private paused = false;
  private queued: TDraft | null = null;
  private attempted: TDraft | null = null;
  private attemptOperationId: string | null = null;

  constructor(private readonly options: SerialDraftQueueOptions<TDraft, TResult>) {}

  /** Clears in-flight bookkeeping; callers reseed any external version state separately. */
  reset(): void {
    this.failed = false;
    this.paused = false;
    this.queued = null;
    this.attempted = null;
    this.attemptOperationId = null;
  }

  /** Schedules the newest draft; failed requests pause subsequent writes until retry or reload. */
  enqueue(draft: TDraft, persisted?: TDraft): void {
    if (!this.running && !this.failed && this.options.isEqual(persisted ?? null, draft)) {
      this.queued = null;
      return;
    }
    if (this.options.isEqual(this.attempted, draft)) {
      this.queued = null;
      return;
    }
    this.queued = this.options.clone(draft);
    if (!this.running && !this.paused) void this.drain();
  }

  /** Retries the exact failed transaction before processing any newer queued edits. */
  retry(): void {
    if (this.running || !this.failed || !this.attempted) return;
    this.failed = false;
    void this.drain(this.attempted);
  }

  private async drain(retry?: TDraft): Promise<void> {
    const draft = retry ?? this.queued;
    if (!draft) return;
    if (!retry) {
      this.queued = null;
      this.attempted = this.options.clone(draft);
      this.attemptOperationId = crypto.randomUUID();
    }
    this.running = true;
    this.failed = false;
    this.options.onStatus("saving", "");
    try {
      const outcome = await this.options.attempt(draft, this.attemptOperationId!);
      if (!outcome.ok) {
        this.failed = true;
        this.paused = !outcome.retryable;
        this.options.onStatus("error", outcome.message);
        return;
      }
      this.paused = false;
      this.options.onApplied(outcome.result, draft);
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
