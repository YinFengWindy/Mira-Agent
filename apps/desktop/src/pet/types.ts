/** Runtime state supported by the Codex-compatible sprite atlas. */
export type DesktopPetState =
  | "idle"
  | "running-right"
  | "running-left"
  | "waving"
  | "jumping"
  | "failed"
  | "waiting"
  | "running"
  | "review";

/** States a role-owned package may expose as a temporary action overlay. */
export type DesktopPetActionState =
  | "idle"
  | "running-right"
  | "running-left"
  | "waving"
  | "jumping";

export type DesktopPetActionPayload = {
  action_id: string;
  role_id: string;
  session_key: string;
  channel: "desktop";
  kind: "move" | "play";
  name?: string;
  target?: "top_left" | "top_right" | "center" | "bottom_left" | "bottom_right";
  animation?: "" | "idle" | "run";
  state?: DesktopPetState;
};

/** One validated role-owned pet package available to the desktop shell. */
export type DesktopPetPackage = {
  id: string;
  displayName: string;
  /** Opaque trusted local-asset URL, never a renderer-visible filesystem path. */
  spritesheetUrl: string;
};

/** Resolved binding used to load one desktop pet window. */
export type DesktopPetBinding = {
  roleId: string;
  package: DesktopPetPackage;
  actions?: Record<string, DesktopPetActionState>;
};

export type DesktopPetPosition = { x: number; y: number };

/**
 * The pet's fixed surface body, matching one cell of the Codex sprite atlas.
 *
 * The host clamps and positions this rectangle; a speech bubble grows the
 * window beyond it through a surface extension without changing the body.
 * Kept in step with `spriteCell` in `plugins/desktop_pet/surface/spriteContract.ts`.
 */
export const desktopPetBody = { width: 192, height: 208 };

/** Available display area for positioning the transparent desktop-pet window. */
export type DesktopPetWorkArea = {
  x: number;
  y: number;
  width: number;
  height: number;
};

/** Persisted application-level desktop-pet configuration. */
export type DesktopPetSettings = {
  visible: boolean;
  roleId: string | null;
  packageId: string | null;
  positions: Record<string, DesktopPetPosition>;
};

export const defaultDesktopPetSettings: DesktopPetSettings = {
  visible: false,
  roleId: null,
  packageId: null,
  positions: {},
};
