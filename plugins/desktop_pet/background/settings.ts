import type { DesktopPetBinding, DesktopPetSettings } from "./types";

function asFiniteCoordinate(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/**
 * Parses persisted desktop-pet data and normalizes unusable enable states.
 *
 * The file I/O this used to sit next to is gone: since #181-C the pet's
 * settings live in `ctx.store`, which the host reads and writes on the
 * plugin's behalf. What is left here is pure, which is also what makes it
 * testable without a filesystem.
 */
export function normalizeDesktopPetSettings(value: unknown): DesktopPetSettings {
  const source = value && typeof value === "object" ? value as Record<string, unknown> : {};
  const roleId = typeof source.roleId === "string" && source.roleId.trim() ? source.roleId.trim() : null;
  const packageId = typeof source.packageId === "string" && source.packageId.trim() ? source.packageId.trim() : null;
  const positions: DesktopPetSettings["positions"] = {};
  if (source.positions && typeof source.positions === "object") {
    for (const [key, position] of Object.entries(source.positions as Record<string, unknown>)) {
      if (!position || typeof position !== "object") continue;
      const point = position as Record<string, unknown>;
      const x = asFiniteCoordinate(point.x);
      const y = asFiniteCoordinate(point.y);
      if (x !== null && y !== null) positions[key] = { x, y };
    }
  }
  return {
    // A stored `visible` only counts when there is something to show: a role
    // whose package was deleted must not come back as a blank pet window.
    visible: Boolean(source.visible ?? source.enabled) && Boolean(roleId && packageId),
    roleId,
    packageId,
    positions,
  };
}

/** Replaces the single active role/package slot while retaining per-role window positions. */
export function bindDesktopPetSettings(
  settings: DesktopPetSettings,
  binding: DesktopPetBinding,
  visible: boolean,
): DesktopPetSettings {
  return {
    ...settings,
    visible,
    roleId: binding.roleId,
    packageId: binding.package.id,
  };
}
