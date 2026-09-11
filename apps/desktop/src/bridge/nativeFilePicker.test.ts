import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import type { OpenDialogOptions } from "electron";
import { pickNativeFiles } from "./nativeFilePicker";

const options = { namespace: "sample-package", multiple: false, maxFileBytes: 64,
  filters: [{ name: "Package files", extensions: ["zip"] }] };

test("uses plugin-supplied native filters and returns only copied dialog selections", async () => {
  const root = await mkdtemp(join(tmpdir(), "shiori-picker-dialog-"));
  try {
    const source = join(root, "selected.zip"); await writeFile(source, "selected bytes", "utf8");
    const dialogs: OpenDialogOptions[] = [];
    const staged = await pickNativeFiles(options, join(root, "imports"), async (value) => {
      dialogs.push(value); return { canceled: false, filePaths: [source] };
    });
    assert.deepEqual(dialogs, [{ properties: ["openFile"], filters: options.filters }]);
    assert.notEqual(staged[0], source);
    assert.equal(await readFile(staged[0], "utf8"), "selected bytes");
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("native cancellation discards even supplied result paths and multiple selection is explicit", async () => {
  const dialogs: OpenDialogOptions[] = [];
  const result = await pickNativeFiles({ ...options, multiple: true }, "unused-imports", async (value) => {
    dialogs.push(value); return { canceled: true, filePaths: ["/must-not-be-read.zip"] };
  });
  assert.deepEqual(result, []);
  assert.deepEqual(dialogs[0].properties, ["openFile", "multiSelections"]);
  let opened = false;
  await assert.rejects(pickNativeFiles({ ...options, source: "/arbitrary/path.zip" }, "unused-imports", async () => {
    opened = true; return { canceled: false, filePaths: [] };
  }), /不支持/);
  assert.equal(opened, false);
});
