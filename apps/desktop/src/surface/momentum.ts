import type { SurfacePoint } from "./contract.js";

/**
 * The release glide a surface performs after a flick.
 *
 * This lives in the host rather than in plugin code for a concrete reason
 * recorded in #181: the integration ticks every 8ms and writes window bounds
 * on each tick. A plugin renderer driving that would cross the IPC boundary
 * ~125 times a second per surface. The plugin hands over a release velocity
 * once and the host runs the glide.
 */

/** How often the glide integrates. */
export const surfaceMomentumIntervalMs = 8;
/** Caps a delayed tick so a stalled event loop cannot teleport the surface. */
export const surfaceMomentumMaximumElapsedMs = 32;
/** Velocity retained per sixteen milliseconds. */
export const surfaceMomentumDecayPerFrame = 0.88;
/** Speed (px/s) below which the glide is imperceptible and settles. */
export const surfaceMomentumMinimumSpeed = 65;
/** Hard ceiling on a single glide. */
export const surfaceMomentumMaximumDurationMs = 900;

/** Tunables a caller may override per flick; omitted fields use the host defaults. */
export type SurfaceMomentumConfig = {
  decayPerFrame?: number;
  minimumSpeed?: number;
  maximumDurationMs?: number;
};

export type SurfaceMomentum = {
  position: SurfacePoint;
  velocity: SurfacePoint;
};

/** Advances one release-momentum integration step. */
export function advanceSurfaceMomentum(
  momentum: SurfaceMomentum,
  elapsedMs: number,
  config: SurfaceMomentumConfig = {},
): SurfaceMomentum {
  const clampedElapsedMs = Math.min(Math.max(elapsedMs, 0), surfaceMomentumMaximumElapsedMs);
  const elapsedSeconds = clampedElapsedMs / 1000;
  const decayPerFrame = config.decayPerFrame ?? surfaceMomentumDecayPerFrame;
  const decay = decayPerFrame ** (clampedElapsedMs / 16);
  return {
    position: {
      x: momentum.position.x + momentum.velocity.x * elapsedSeconds,
      y: momentum.position.y + momentum.velocity.y * elapsedSeconds,
    },
    velocity: {
      x: momentum.velocity.x * decay,
      y: momentum.velocity.y * decay,
    },
  };
}

/** Returns whether a glide should settle and hand the final position back to the plugin. */
export function shouldStopSurfaceMomentum(
  momentum: SurfaceMomentum,
  elapsedSinceReleaseMs: number,
  config: SurfaceMomentumConfig = {},
): boolean {
  const maximumDurationMs = config.maximumDurationMs ?? surfaceMomentumMaximumDurationMs;
  const minimumSpeed = config.minimumSpeed ?? surfaceMomentumMinimumSpeed;
  return elapsedSinceReleaseMs >= maximumDurationMs
    || Math.hypot(momentum.velocity.x, momentum.velocity.y) < minimumSpeed;
}
