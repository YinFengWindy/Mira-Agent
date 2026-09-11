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
 * | relaying `desktop:pet-sync` | the role form's save, the pet's own panel | #218 |
 * | whether the pet is showing, and whose | voice admission, observation | #221 / #220 |
 *
 * #181-D took two rows off this table: the tray entry is the pet's own now
 * (`ctx.tray`), and the main window's close policy asks "does any plugin still
 * own a surface" instead of "is the pet running".
 *
 * The remaining `desktop:pet-sync` row changed meaning rather than leaving. It
 * is no longer "the host starts the pet" — the host has no reason to — it is
 * the only route from *any* main-window renderer to the pet's background code,
 * which lives in a different renderer. Both callers are pet-owned code
 * (`plugins/desktop_pet/ui/RolePetPackagesPanel.tsx`) or about to be; it goes
 * with surface-to-background messaging (#218).
 *
 * What the host no longer knows at all: roles, packages, sprite states,
 * positions, window geometry — in the main process since #181-C, and in the
 * bridge and the package-manager UI since #181-D.
 *
 * **Still outstanding, and not this file's scope.** The pet's data is still on
 * `RoleRecord` (`pet_packages` / `selected_pet_package_id` /
 * `desktop_pet_enabled`), so the role capability toggle
 * (`roles/RoleCapabilitiesPanel.tsx`) and `roles.update` still carry it, and
 * `desktop_bridge/server.py` still bridges `DesktopPetActionRequested` to
 * `desktop.pet.action`. Those move when the pet's data leaves the role record;
 * until then "宿主不感知桌宠领域" is true of the main process, the package
 * manager and the role bridge, but not of the role *model*.
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

/**
 * One host-issued pet lifecycle command.
 *
 * Only `sync` is left. `show` and `hide` existed for the tray entry, whose
 * only producer was the host's own menu builder — since #181-D the pet owns
 * that item and calls its controller directly, with no round trip through the
 * main process. `sync` survives because its caller is the *main window's*
 * role form, and there is still no route from there to a plugin's background
 * code; it goes when #181-D's backend work turns it into a plugin RPC.
 */
export type DesktopPetCommand = { kind: "sync"; forceVisible?: boolean };

/**
 * The pet's state as far as the host is concerned.
 *
 * Two facts, both for features that are not plugins yet: `visible` gates voice
 * admission (`voice/availability.ts`) and `roleId` says whose turn a voice
 * press or an observation reply belongs to. `available` used to be here too,
 * for the tray item's enabled state — that left with #181-D.
 */
export type DesktopPetPresence = {
  visible: boolean;
  roleId: string | null;
};

export const noDesktopPetPresence: DesktopPetPresence = {
  visible: false,
  roleId: null,
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
  // A stored `visible` only counts when there is something to show. The plugin
  // normalizes this too, but the host reads the file the plugin wrote, and a
  // hand-edited one would otherwise admit voice input for a pet that cannot
  // exist.
  const bound = Boolean(roleId && typeof source.packageId === "string" && source.packageId);
  return {
    visible: source.visible === true && bound,
    roleId,
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
  return before.visible !== after.visible || before.roleId !== after.roleId;
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
