import assert from "node:assert/strict";
import test from "node:test";
import petBackground, {
  desktopPetCommandMethod as pluginCommandMethod,
  desktopPetObservationMethod as pluginObservationMethod,
} from "../../../../plugins/desktop_pet/background/index.js";
import { desktopPetSurfaceId } from "../../../../plugins/desktop_pet/background/controller.js";
import {
  desktopPetCommandMethod,
  desktopPetObservationMethod,
  desktopPetPluginId,
  desktopPetSurfaceKey,
  isDesktopPetWindow,
  noDesktopPetPresence,
  readDesktopPetPresence,
} from "./desktopPet.js";
import type { SurfaceKey } from "../surface/host.js";

/**
 * Pins the host's copy of the pet coupling to the plugin's.
 *
 * The two sides declare these strings separately on purpose — sharing them
 * would mean the host importing from a plugin — which leaves exactly one
 * failure mode: renaming one copy and not the other. Nothing would break at
 * build time; the tray entry and observation bubbles would simply stop working
 * at runtime, with no error anywhere. A test is the only thing that catches
 * it, and a test may import across the boundary a dependency must not.
 */
test("the host and the plugin agree on the pet's identity and event names", () => {
  assert.equal(desktopPetPluginId, petBackground.pluginId);
  assert.equal(desktopPetSurfaceKey.surfaceId, desktopPetSurfaceId);
  assert.equal(desktopPetCommandMethod, pluginCommandMethod);
  assert.equal(desktopPetObservationMethod, pluginObservationMethod);
});

test("presence reads the three fields the host needs out of the pet's stored blob", () => {
  assert.deepEqual(
    readDesktopPetPresence({ visible: true, roleId: "mira", packageId: "pet-1", positions: {} }),
    { visible: true, roleId: "mira", available: true },
  );
});

test("a pet with no package is unavailable, so the tray entry stays disabled", () => {
  assert.deepEqual(
    readDesktopPetPresence({ visible: true, roleId: "mira", packageId: null }),
    { visible: false, roleId: "mira", available: false },
  );
});

test("anything the host cannot read as pet settings degrades to no pet", () => {
  for (const value of [null, undefined, "nope", 7, [], {}, { visible: true }]) {
    assert.deepEqual(readDesktopPetPresence(value), noDesktopPetPresence, JSON.stringify(value ?? null));
  }
});

test("visible is only believed when there is something to show", () => {
  // The plugin normalizes this too, but the host must not depend on that: it
  // reads the file the plugin wrote, and a hand-edited one would otherwise
  // leave the tray offering to hide a pet that cannot exist.
  assert.equal(readDesktopPetPresence({ visible: true, roleId: "mira", packageId: "" }).visible, false);
});

test("only the pet's own surface window is attributed to the pet", () => {
  const keys = new Map<number, SurfaceKey>([
    [1, desktopPetSurfaceKey],
    [2, { pluginId: "novelai", surfaceId: "pet" }],
    [3, { pluginId: "desktop_pet", surfaceId: "other" }],
  ]);
  const surfaces = { keyForWindowId: (id: number | null | undefined) => keys.get(id ?? -1) ?? null };

  assert.equal(isDesktopPetWindow(surfaces, { id: 1 }), true);
  // Another plugin naming its surface "pet" must not inherit the pet's voice
  // and observation channels.
  assert.equal(isDesktopPetWindow(surfaces, { id: 2 }), false);
  assert.equal(isDesktopPetWindow(surfaces, { id: 3 }), false);
  assert.equal(isDesktopPetWindow(surfaces, { id: 4 }), false);
  assert.equal(isDesktopPetWindow(surfaces, null), false);
});
