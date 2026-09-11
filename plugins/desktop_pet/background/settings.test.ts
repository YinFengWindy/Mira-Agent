import assert from "node:assert/strict";
import test from "node:test";
import { desktopPetBindingPatch, normalizeDesktopPetSettings } from "./settings";

test("desktop-pet settings disable incomplete bindings and retain valid positions", () => {
  assert.deepEqual(normalizeDesktopPetSettings({ enabled: true, roleId: "role-1", positions: { broken: { x: 1, y: 2 } } }), {
    visible: false,
    roleId: "role-1",
    packageId: null,
    positions: { broken: { x: 1, y: 2 } },
  });
});

test("an unreadable store blob normalizes to the default rather than throwing", () => {
  // `ctx.store.read()` answers `null` for a plugin that never wrote and for a
  // file the host could not parse; both have to land on the defaults here.
  for (const value of [null, undefined, "not an object", 7, []]) {
    assert.deepEqual(normalizeDesktopPetSettings(value), {
      visible: false,
      roleId: null,
      packageId: null,
      positions: {},
    });
  }
});

test("positions that are not finite points are dropped instead of poisoning window bounds", () => {
  const settings = normalizeDesktopPetSettings({
    visible: true,
    roleId: "role-1",
    packageId: "pet-1",
    positions: {
      good: { x: 10, y: 20 },
      nan: { x: Number.NaN, y: 20 },
      infinite: { x: 1, y: Number.POSITIVE_INFINITY },
      missing: { x: 5 },
      notAnObject: "nope",
    },
  });

  assert.deepEqual(settings.positions, { good: { x: 10, y: 20 } });
});

test("a binding patch names only the binding, so it cannot carry stale positions", () => {
  const patch = desktopPetBindingPatch({
    roleId: "role-b",
    package: { id: "pet-b", displayName: "Pet B", spritesheetUrl: "shiori-asset://local/pet-b" },
  }, false);

  // `positions` is absent on purpose: the caller computes this before an await
  // and saves it after, and a settle landing in that gap writes a position that
  // a full snapshot would silently roll back. See `desktopPetBindingPatch`.
  assert.deepEqual(patch, { visible: false, roleId: "role-b", packageId: "pet-b" });
  assert.equal("positions" in patch, false);
});

test("merging a binding patch keeps the positions already remembered", () => {
  const current = normalizeDesktopPetSettings({
    visible: false,
    roleId: "role-a",
    packageId: "pet-a",
    positions: { "role-a:1": { x: 10, y: 20 } },
  });

  const merged = { ...current, ...desktopPetBindingPatch({
    roleId: "role-b",
    package: { id: "pet-b", displayName: "Pet B", spritesheetUrl: "shiori-asset://local/pet-b" },
  }, false) };

  assert.deepEqual(merged, {
    visible: false,
    roleId: "role-b",
    packageId: "pet-b",
    positions: { "role-a:1": { x: 10, y: 20 } },
  });
});
