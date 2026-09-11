import type { SurfaceKey } from "../surface/host.js";

/**
 * What the host still has to know about the `desktop_pet` plugin, and what
 * removes each piece.
 *
 * #181-C moved the pet's controller, settings and role binding into
 * `plugins/desktop_pet/background/`; `apps/desktop/src/pet/` is gone. This file
 * is the residue — deliberately collected in one place instead of scattered
 * back through `main.ts`, `tray.ts` and `voice/` — because three host features
 * are not plugins yet and cannot ask the pet anything through a capability:
 *
 * | What the host needs | Who needs it | Removed by |
 * | --- | --- | --- |
 * | the pet's surface key | voice IPC, observation dismiss | #221 / #220 |
 * | a way to start/stop the pet | the tray entry, `desktop:pet-sync` | #181-D |
 * | the pet's visible/bound state | tray label, voice admission, close policy | #181-D, #221 |
 *
 * What the *main process* no longer knows: roles, packages, sprite states,
 * positions, window geometry. That is the part of #181's "宿主不感知桌宠领域"
 * that #181-C delivers, and it is the whole of what this file's scope is.
 *
 * **It is not the whole of the host's pet knowledge.** The host's *renderer*
 * still owns the pet package manager on the role detail page —
 * `roles/RolePetPackagesPanel.tsx`, the pet toggle in `RoleCapabilitiesPanel`,
 * `pet_packages` in `shared/types.ts`, the `roles.pets.*` calls in
 * `app/useRoleManagement.ts`, and `pickPetPackage` on the preload API. That UI
 * knows exactly what a pet package is. It could not move here or into the
 * plugin in #181-C: #179's slots are `settings.section` and `nav.page`, and
 * this is neither — it is a section of the role detail page, for which no slot
 * exists yet. Whoever runs #181-D's final acceptance needs to count it: the
 * criterion is not met for the renderer, and no issue claims it yet.
 */

export const desktopPetPluginId = "desktop_pet";

/** Identifies the pet's window to the DesktopSurface capability. */
export const desktopPetSurfaceKey: SurfaceKey = { pluginId: desktopPetPluginId, surfaceId: "pet" };

/**
 * Host-originated bridge events the pet's background code subscribes to.
 *
 * Published through `main.ts::publishDesktopEvent` into the same
 * `desktop:event` stream the backend uses, so the plugin receives them on the
 * ordinary `ctx.events.on` — no extra plugin-facing API exists for "the host
 * wants to tell one plugin something", and inventing one for a coupling that
 * three issues are already scheduled to delete would be the wrong trade.
 *
 * The plugin declares the same strings in
 * `plugins/desktop_pet/background/index.ts`; they are duplicated because a
 * shared constant would mean the host importing from a plugin.
 * `plugins/desktop_pet/background/hostContract.test.ts` pins the two copies
 * together — it lives on the plugin side because this file is in the
 * main-process tsc program, which cannot reach renderer code at all.
 */
export const desktopPetCommandMethod = "desktop.pet.command";
export const desktopPetObservationMethod = "desktop.pet.observation";

/** One host-issued pet lifecycle command. */
export type DesktopPetCommand =
  | { kind: "show" }
  | { kind: "hide" }
  | { kind: "sync"; forceVisible?: boolean };

/**
 * The pet's state as far as the host is concerned.
 *
 * `available` answers "can the tray entry be clicked", `visible` answers "what
 * should it say", and `roleId` is who voice input and observation belong to.
 */
export type DesktopPetPresence = {
  visible: boolean;
  roleId: string | null;
  available: boolean;
};

export const noDesktopPetPresence: DesktopPetPresence = {
  visible: false,
  roleId: null,
  available: false,
};

/**
 * Reads the three fields the host needs out of the pet's own store blob.
 *
 * Reading a plugin's private data is not a pattern to copy. It is here because
 * the alternative during the migration is worse: a second, host-only channel
 * carrying the same three facts, which would then have to be kept in step with
 * the plugin's own writes and would outlive the coupling it exists for. The
 * store already updates on every write the plugin makes, and everything below
 * is defensive about what it finds, so a plugin that changed its own format
 * degrades to "no pet" rather than to a crash.
 */
export function readDesktopPetPresence(stored: unknown): DesktopPetPresence {
  if (!stored || typeof stored !== "object") return noDesktopPetPresence;
  const source = stored as { visible?: unknown; roleId?: unknown; packageId?: unknown };
  const roleId = typeof source.roleId === "string" && source.roleId ? source.roleId : null;
  const available = Boolean(roleId && typeof source.packageId === "string" && source.packageId);
  return {
    visible: source.visible === true && available,
    roleId,
    available,
  };
}

/**
 * Whether two presences differ in anything the host reacts to.
 *
 * Extracted so it can be tested: the plugin writes its settings on *every*
 * remembered position — once per drag, per release glide, per role-requested
 * move — and the host's reaction to a write includes republishing observation
 * state, which clears any reply bubble currently on screen. Reacting only to a
 * real change is what keeps dragging the pet from wiping the bubble it is
 * talking through.
 */
export function desktopPetPresenceChanged(
  before: DesktopPetPresence,
  after: DesktopPetPresence,
): boolean {
  return before.visible !== after.visible
    || before.roleId !== after.roleId
    || before.available !== after.available;
}

/** Whether an IPC sender's window is the pet's surface. */
export function isDesktopPetWindow(
  surfaces: { keyForWindowId(windowId: number | null | undefined): SurfaceKey | null },
  window: { readonly id: number } | null,
): boolean {
  const key = surfaces.keyForWindowId(window?.id);
  return Boolean(
    key
    && key.pluginId === desktopPetSurfaceKey.pluginId
    && key.surfaceId === desktopPetSurfaceKey.surfaceId,
  );
}
