import assert from "node:assert/strict";
import { test } from "node:test";
import { maxNativeFileBytes, normalizeFilePickerOptions } from "./filePickerContract";

const valid = { namespace: "sample-packages", maxFileBytes: 1024, filters: [{ name: "Packages", extensions: ["ZIP"] }] };

test("normalizes constrained file filters without accepting path-bearing IPC fields", () => {
  assert.deepEqual(normalizeFilePickerOptions(valid), { ...valid, filters: [{ name: "Packages", extensions: ["zip"] }], multiple: false });
  for (const patch of [
    { namespace: "../outside" }, { namespace: "/absolute" }, { namespace: "sample/../../outside" },
    { namespace: "C:/outside" }, { namespace: ".." }, { maxFileBytes: maxNativeFileBytes + 1 },
    { maxFileBytes: NaN }, { maxFileBytes: 0 }, { maxFileBytes: 1.5 }, { multiple: "yes" },
    { source: "/secret.txt" }, { defaultPath: "/secret.txt" }, { properties: ["openDirectory"] },
    { filters: [] }, { filters: [{ name: "All", extensions: ["*"] }] },
    { filters: [{ name: "Bad", extensions: ["../zip"] }] },
  ]) assert.throws(() => normalizeFilePickerOptions({ ...valid, ...patch }), /无效|不支持/);
});
