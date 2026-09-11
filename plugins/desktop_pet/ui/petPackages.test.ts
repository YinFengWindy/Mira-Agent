import assert from "node:assert/strict";
import { test } from "node:test";
import { noPetPackages, readPetPackages } from "./petPackages";

const url = (path: string) => `shiori-asset://local/${path}`;

test("a pets.list response becomes rows with displayable preview URLs", () => {
  const parsed = readPetPackages({
    selected_package_id: "pet-1",
    packages: [
      { id: "pet-1", display_name: "小猫", preview_abs: "C:/roles/mira/preview.png" },
      { id: "pet-2", display_name: "小狗", preview_abs: null },
    ],
  }, url);

  assert.deepEqual(parsed, {
    selectedPackageId: "pet-1",
    packages: [
      { id: "pet-1", displayName: "小猫", previewUrl: "shiori-asset://local/C:/roles/mira/preview.png" },
      // No preview file: an empty URL, so the component renders the placeholder
      // rather than a broken image.
      { id: "pet-2", displayName: "小狗", previewUrl: "" },
    ],
  });
});

test("the raw filesystem path never reaches the row", () => {
  const parsed = readPetPackages({
    packages: [{ id: "pet-1", display_name: "小猫", preview_abs: "C:/roles/mira/preview.png" }],
  }, url);

  // The renderer must not display or keep a filesystem path; only the opaque
  // granted URL is allowed past this boundary.
  assert.equal(parsed.packages[0].previewUrl.includes("C:/roles"), true);
  assert.equal(Object.values(parsed.packages[0]).includes("C:/roles/mira/preview.png"), false);
});

test("a malformed row is dropped rather than rendered with holes in it", () => {
  const parsed = readPetPackages({
    selected_package_id: "",
    packages: [
      null,
      "nope",
      { display_name: "没有 id" },
      { id: "", display_name: "空 id" },
      { id: "pet-1" },
    ],
  }, url);

  assert.equal(parsed.selectedPackageId, null);
  // The only survivor falls back to its id for a label rather than `undefined`.
  assert.deepEqual(parsed.packages, [{ id: "pet-1", displayName: "pet-1", previewUrl: "" }]);
});

test("anything that is not a pets.list response reads as no packages", () => {
  for (const value of [null, undefined, "nope", 7, [], {}, { packages: "nope" }]) {
    assert.deepEqual(readPetPackages(value, url), noPetPackages, JSON.stringify(value ?? null));
  }
});
