import assert from "node:assert/strict";
import test from "node:test";
import { readDesktopPetBinding } from "./binding";

const grantedUrl = "shiori-asset://local/token-1";
const grant = (path: string) => (path === "C:/roles/mira/sheet.webp" ? grantedUrl : null);

const response = (overrides: Record<string, unknown> = {}) => ({
  binding: {
    role_id: "mira",
    package: {
      id: "pet-1",
      display_name: "Pet",
      spritesheet_abs: "C:/roles/mira/sheet.webp",
    },
    actions: { greeting: "waving" },
    ...overrides,
  },
});

test("a complete response becomes a binding with an opaque asset URL", () => {
  assert.deepEqual(readDesktopPetBinding(response(), grant), {
    roleId: "mira",
    package: { id: "pet-1", displayName: "Pet", spritesheetUrl: grantedUrl },
    actions: { greeting: "waving" },
  });
});

test("an ungranted spritesheet is no binding at all, not a pet with a broken image", () => {
  const ungranted = response({
    package: { id: "pet-1", display_name: "Pet", spritesheet_abs: "C:/somewhere/else.webp" },
  });

  assert.equal(readDesktopPetBinding(ungranted, grant), null);
});

test("action states the sprite atlas cannot play are dropped, not passed through", () => {
  const binding = readDesktopPetBinding(
    response({ actions: { greeting: "waving", bogus: "moonwalk", wrongType: 7 } }),
    grant,
  );

  // An unknown state would leave the pet frozen mid-action with nothing on
  // screen to explain it.
  assert.deepEqual(binding?.actions, { greeting: "waving" });
});

test("every shape the backend can legitimately answer with resolves to no binding", () => {
  for (const value of [
    null,
    undefined,
    "nope",
    {},
    { binding: null },
    { binding: {} },
    { binding: { role_id: "", package: { id: "p", display_name: "P", spritesheet_abs: "C:/roles/mira/sheet.webp" } } },
    { binding: { role_id: "mira" } },
    { binding: { role_id: "mira", package: { display_name: "P", spritesheet_abs: "C:/roles/mira/sheet.webp" } } },
    { binding: { role_id: "mira", package: { id: "p", spritesheet_abs: "C:/roles/mira/sheet.webp" } } },
    { binding: { role_id: "mira", package: { id: "p", display_name: "P" } } },
  ]) {
    assert.equal(readDesktopPetBinding(value, grant), null, JSON.stringify(value ?? null));
  }
});

test("a package with no declared actions still binds", () => {
  const binding = readDesktopPetBinding(response({ actions: undefined }), grant);

  assert.deepEqual(binding?.actions, {});
});
