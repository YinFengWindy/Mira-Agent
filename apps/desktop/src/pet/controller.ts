import type { DesktopSurfaceHost, SurfaceKey, SurfaceSettleReason } from "../surface/host.js";
import { bindDesktopPetSettings } from "./settings.js";
import {
  desktopPetBody,
  type DesktopPetBinding,
  type DesktopPetActionPayload,
  type DesktopPetPosition,
  type DesktopPetSettings,
  type DesktopPetState,
  type DesktopPetWorkArea,
} from "./types.js";
import type { PetObservationPayload } from "../observation/types.js";

/** Keeps role-requested moves visible as a short, deliberate desktop animation. */
export const desktopPetAgentMoveDurationMs = 900;

/** Identifies the pet's window to the DesktopSurface capability. */
export const desktopPetSurfaceKey: SurfaceKey = { pluginId: "desktop_pet", surfaceId: "pet" };

/**
 * A deliberately unreachable anchor, used when the pet has no remembered
 * position: the host clamps the body into the work area, which lands it in the
 * bottom-right corner of whichever display the surface opened on — the same
 * fallback the pet had before it moved onto surfaces.
 */
const desktopPetFallbackAnchor: DesktopPetPosition = {
  x: Number.MAX_SAFE_INTEGER,
  y: Number.MAX_SAFE_INTEGER,
};

/** Settle reasons that mean the user (or a role) actually relocated the pet. */
const persistedSettleReasons = new Set<SurfaceSettleReason>(["drag", "momentum", "move"]);

type DesktopPetControllerOptions = {
  getSettings: () => DesktopPetSettings;
  saveSettings: (settings: DesktopPetSettings) => Promise<void>;
  resolveBinding: (roleId?: string) => Promise<DesktopPetBinding | null>;
  surfaces: DesktopSurfaceHost;
};

/**
 * Serializes desktop-pet lifecycle operations so a stale enable cannot recreate
 * a disabled pet.
 *
 * Since #181-B this controller owns no window code at all: it drives the
 * generic DesktopSurface capability, which holds the window handle and every
 * timer that writes bounds. That is what makes "the pet's window is gone when
 * the pet is off" true rather than aspirational — reclaiming it does not depend
 * on this class still running. What remains here is pet *domain* state: which
 * role and package are bound, what the sprite should be doing, and where the
 * user left it on each display. That moves into the plugin in 181-C/D.
 */
export class DesktopPetController {
  private readonly surfaces: DesktopSurfaceHost;
  private queue = Promise.resolve();
  private activeRoleId = "";
  private activeLoad: { binding: DesktopPetBinding; state: DesktopPetState } | null = null;
  private latestObservation: PetObservationPayload | null = null;

  constructor(private readonly options: DesktopPetControllerOptions) {
    this.surfaces = options.surfaces;
  }

  get isRunning(): boolean {
    // Derived from the host rather than mirrored locally: the host destroys the
    // surface on app shutdown or an OS-level close, and a cached flag here
    // would then disagree with reality.
    return this.surfaces.has(desktopPetSurfaceKey);
  }

  /** Returns whether an IPC sender owns the pet's surface window. */
  isPetWindow(window: { readonly id: number } | null): boolean {
    const key = this.surfaces.keyForWindowId(window?.id);
    return Boolean(
      key
      && key.pluginId === desktopPetSurfaceKey.pluginId
      && key.surfaceId === desktopPetSurfaceKey.surfaceId,
    );
  }

  /**
   * Records where the surface came to rest.
   *
   * Wired to the host's settle observer rather than driven from here, because
   * a drag or release glide is started by the surface renderer talking to the
   * host directly; this controller never sees those calls.
   */
  handleSettled(reason: SurfaceSettleReason, anchor: DesktopPetPosition): void {
    if (!persistedSettleReasons.has(reason) || !this.activeRoleId) return;
    this.persistPosition(this.activeRoleId, anchor);
  }

  show(): Promise<void> {
    return this.enqueue(async () => {
      const binding = await this.options.resolveBinding();
      if (!binding) throw new Error("没有已启用且已选择素材的桌宠角色");
      const nextSettings = bindDesktopPetSettings(this.options.getSettings(), binding, true);
      await this.load(binding, nextSettings, "idle");
      await this.options.saveSettings(nextSettings);
    });
  }

  hide(): Promise<void> {
    return this.enqueue(async () => {
      this.destroySurface();
      await this.options.saveSettings({ ...this.options.getSettings(), visible: false });
    });
  }

  sync(forceVisible?: boolean): Promise<void> {
    return this.enqueue(async () => {
      const binding = await this.options.resolveBinding();
      if (!binding) {
        this.destroySurface();
        await this.options.saveSettings({ ...this.options.getSettings(), visible: false, roleId: null, packageId: null });
        return;
      }
      const current = this.options.getSettings();
      const changedBinding = current.roleId !== binding.roleId || current.packageId !== binding.package.id;
      const nextSettings = bindDesktopPetSettings(
        current,
        binding,
        forceVisible ?? (changedBinding || current.visible),
      );
      if (nextSettings.visible) await this.load(binding, nextSettings, "idle");
      else this.destroySurface();
      await this.options.saveSettings(nextSettings);
    });
  }

  restore(): Promise<void> {
    return this.sync();
  }

  play(state: DesktopPetState): void {
    this.postPlay(state, false);
  }

  /** Executes one already-authorized role action without exposing window APIs to the renderer. */
  handleAgentAction(value: unknown): void {
    if (!isDesktopPetActionPayload(value)) return;
    if (!this.isRunning || value.role_id !== this.activeRoleId || value.channel !== "desktop") return;
    if (value.kind === "play") {
      const state = value.name ? this.activeLoad?.binding.actions?.[value.name] : undefined;
      if (state) this.postPlay(state, true);
      return;
    }
    if (!value.target) return;
    const current = this.surfaces.anchorFromWindow(desktopPetSurfaceKey);
    const next = desktopPetTargetPosition(value.target, this.surfaces.workArea(desktopPetSurfaceKey));
    // The host runs the tween and reports the landing through `handleSettled`.
    this.surfaces.moveTo(desktopPetSurfaceKey, next, desktopPetAgentMoveDurationMs);
    if (value.animation === "run") {
      const state = next.x < current.x ? "running-left" : next.x > current.x ? "running-right" : "idle";
      this.postPlay(state, true);
    }
  }

  /** Publishes observation state without exposing frames or model output internals. */
  publishObservation(payload: PetObservationPayload): void {
    this.latestObservation = payload;
    this.pushRetainedState();
  }

  private enqueue(operation: () => Promise<void>): Promise<void> {
    const next = this.queue.then(operation, operation);
    this.queue = next.catch(() => undefined);
    return next;
  }

  private async load(binding: DesktopPetBinding, settings: DesktopPetSettings, state: DesktopPetState): Promise<void> {
    const created = !this.isRunning;
    this.activeRoleId = binding.roleId;
    this.activeLoad = { binding, state };
    if (created) {
      // Created at the fallback corner first: only once the window exists can
      // the host say which display it landed on, and the remembered position is
      // per display. Both happen before the renderer has painted anything.
      this.surfaces.create(desktopPetSurfaceKey, { body: desktopPetBody }, desktopPetFallbackAnchor);
      const remembered = settings.positions[this.positionKey(binding.roleId)];
      if (remembered) this.surfaces.setPosition(desktopPetSurfaceKey, remembered);
    }
    // Retained, so a renderer that mounts or reloads later still gets it.
    this.pushRetainedState();
  }

  private pushRetainedState(): void {
    if (!this.activeLoad || !this.isRunning) return;
    this.surfaces.setState(desktopPetSurfaceKey, {
      load: {
        package: this.activeLoad.binding.package,
        state: this.activeLoad.state,
      },
      observation: this.latestObservation,
    });
  }

  /** One-shot sprite command; never retained, so a reload does not replay it. */
  private postPlay(state: DesktopPetState, transient: boolean): void {
    if (!this.isRunning) return;
    this.surfaces.postMessage(desktopPetSurfaceKey, { state, transient });
  }

  private persistPosition(roleId: string, position: DesktopPetPosition): void {
    const settings = this.options.getSettings();
    void this.options.saveSettings({
      ...settings,
      positions: { ...settings.positions, [this.positionKey(roleId)]: position },
    }).catch(() => undefined);
  }

  private positionKey(roleId: string): string {
    return `${roleId}:${this.surfaces.displayId(desktopPetSurfaceKey)}`;
  }

  private destroySurface(): void {
    this.surfaces.destroy(desktopPetSurfaceKey);
    this.activeRoleId = "";
    this.activeLoad = null;
  }
}

function isDesktopPetActionPayload(value: unknown): value is DesktopPetActionPayload {
  if (!value || typeof value !== "object") return false;
  const payload = value as Partial<DesktopPetActionPayload>;
  return payload.channel === "desktop"
    && typeof payload.role_id === "string"
    && (payload.kind === "move" || payload.kind === "play");
}

/**
 * Resolves a named corner or the centre of a work area.
 *
 * The corners deliberately overshoot: the host clamps the body into the work
 * area, so `{ workArea.x + workArea.width, ... }` lands exactly at the right
 * edge without this function having to repeat the body arithmetic. Only the
 * centre genuinely needs the body size.
 */
function desktopPetTargetPosition(
  target: NonNullable<DesktopPetActionPayload["target"]>,
  workArea: DesktopPetWorkArea,
): DesktopPetPosition {
  const right = workArea.x + workArea.width;
  const bottom = workArea.y + workArea.height;
  if (target === "top_left") return { x: workArea.x, y: workArea.y };
  if (target === "top_right") return { x: right, y: workArea.y };
  if (target === "bottom_left") return { x: workArea.x, y: bottom };
  if (target === "bottom_right") return { x: right, y: bottom };
  return {
    x: workArea.x + (workArea.width - desktopPetBody.width) / 2,
    y: workArea.y + (workArea.height - desktopPetBody.height) / 2,
  };
}
