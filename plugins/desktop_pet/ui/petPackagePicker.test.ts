import assert from "node:assert/strict";
import { test } from "node:test";
import { pickPetPackageFile } from "./petPackagePicker";

test("the pet helper owns ZIP filtering, staging namespace and its 32MB limit", async () => {
  const source = await pickPetPackageFile(async (options) => {
    assert.deepEqual(options, { namespace: "desktop_pet-pets", multiple: false,
      filters: [{ name: "Codex Pet Package", extensions: ["zip"] }], maxFileBytes: 32 * 1024 * 1024 });
    return ["/private/imports/package.zip"];
  });
  assert.equal(source, "/private/imports/package.zip");
  assert.equal(await pickPetPackageFile(async () => []), null);
  await assert.rejects(pickPetPackageFile(async () => { throw new Error("native dialog failed"); }), /native dialog failed/);
});
