import { reportBackgroundFailure } from "../../../apps/desktop/renderer/src/background/backgroundDiagnostics";
import type { BackgroundCtx } from "../../../apps/desktop/renderer/src/background/pluginBackgroundRegistry";
import { readDesktopPetBinding } from "./binding";
import { DesktopPetController, desktopPetSurfaceId } from "./controller";
import { normalizeDesktopPetSettings } from "./settings";

/**
 * Bridge events the host still sends the pet, and what removes each.
 *
 * These are *host-originated* events published into the same `desktop:event`
 * stream the backend uses (`main.ts::publishDesktopEvent`), so they arrive
 * through `ctx.events.on` with no extra plugin-facing API. They exist because
 * three host features still hold the pet's leash while #174 finishes:
 *
 * - `desktop.pet.command` — the role detail form's "sync" (`desktop:pet-sync`).
 *   The tray entry no longer comes through here: since #181-D the pet owns its
 *   own menu item via `ctx.tray`. The sync call becomes a plugin RPC with
 *   #181-D's backend work, at which point this event can go too.
 * - `desktop.pet.observation` — screen observation, which becomes a plugin of
 *   its own in #220 and will then talk to the pet over plugin-to-plugin
 *   messaging (#218).
 *
 * The host declares the same two strings in
 * `apps/desktop/src/pluginCoupling/desktopPet.ts`. They are duplicated rather
 * than shared because the dependency would have to point from the host into a
 * plugin; `hostContract.test.ts` beside this file pins the two copies together
 * so they cannot drift apart silently.
 */
export const desktopPetCommandMethod = "desktop.pet.command";
export const desktopPetObservationMethod = "desktop.pet.observation";
/** The backend event carrying one already-authorized `pet_action` tool call. */
export const desktopPetActionMethod = "desktop.pet.action";

/** Identifies the pet's own item in the host tray menu. */
export const desktopPetTrayEntryId = "toggle";

function reportError(operation: string, error: unknown): void {
  // Routed to the host's diagnostic log rather than to this window's console,
  // which nobody can open: `show` failing is exactly what the user is looking
  // at when they report "点了托盘没反应".
  reportBackgroundFailure(`desktop_pet ${operation}`, error);
}

/**
 * The desktop pet's `app.background` contribution: its always-resident
 * controller.
 *
 * Runs in the dedicated hidden `plugin-host.html` renderer, started when the
 * plugin is enabled and torn down when it is disabled — which is what makes
 * #181's "停用桌宠插件后 surface、订阅全部回收" true rather than aspirational.
 * The `ctx.effect` below is what reclaims the window; the subscriptions are
 * reclaimed by `BackgroundEffectScope` regardless of the order they were
 * registered in (#227), so the `effect`/`on` ordering here is a readability
 * choice, not a correctness one.
 */
export default {
  pluginId: "desktop_pet",
  async setup(ctx: BackgroundCtx): Promise<void> {
    const controller = new DesktopPetController({
      surfaces: ctx.surfaces,
      settings: normalizeDesktopPetSettings(await ctx.store.read()),
      saveSettings: (settings) => ctx.store.write(settings),
      resolveBinding: async () => readDesktopPetBinding(
        await ctx.rpc.call("binding.get"),
        (path) => ctx.assets.url(path),
      ),
      onError: reportError,
      onChanged: () => refreshTrayEntry(),
    });

    /**
     * Keeps the tray item in step with the pet.
     *
     * The label and the enabled state are both pet domain facts — is it
     * showing, and is there a role with a package to show — which is exactly
     * why this moved out of the host in #181-D. The host used to read them out
     * of the pet's settings blob and build the item itself.
     */
    const refreshTrayEntry = () => {
      const settings = controller.currentSettings;
      const available = Boolean(settings.roleId && settings.packageId);
      ctx.tray.setEntry(desktopPetTrayEntryId, {
        label: settings.visible ? "隐藏桌宠" : "显示桌宠",
        enabled: available,
        onClick: () => {
          const operation = settings.visible ? "hide" : "show";
          void (settings.visible ? controller.hide() : controller.show())
            .catch((error) => reportError(operation, error));
        },
      });
    };
    // Contributed once up front, so the item exists from the moment the plugin
    // is enabled rather than only after the pet's first state change.
    refreshTrayEntry();

    ctx.effect("desktop_pet_controller", () => controller.terminate());
    ctx.surfaces.onSettled(desktopPetSurfaceId, (settled) => controller.handleSettled(settled));
    ctx.events.on(desktopPetActionMethod, (payload) => controller.handleAgentAction(payload));
    ctx.events.on(desktopPetCommandMethod, (payload) => {
      const kind = payload.kind;
      if (kind === "show") void controller.show().catch((error) => reportError("show", error));
      else if (kind === "hide") void controller.hide().catch((error) => reportError("hide", error));
      else if (kind === "sync") {
        const forceVisible = typeof payload.forceVisible === "boolean" ? payload.forceVisible : undefined;
        void controller.sync(forceVisible).catch((error) => reportError("sync", error));
      }
    });
    ctx.events.on(desktopPetObservationMethod, (payload) => controller.publishObservation(payload));

    // Reported rather than rethrown: a failed restore (the bridge answering
    // late, say) must not fail `setup`, because a thrown `setup` tears the
    // whole contribution down and nothing retries it — the pet would then stay
    // dead until the app restarted. Letting it fail leaves the pet hidden,
    // which the tray entry can undo.
    try {
      await controller.restore();
    } catch (error) {
      reportError("restore", error);
    }
  },
};
