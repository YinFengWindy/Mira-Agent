import assert from "node:assert/strict";
import { test } from "node:test";
import { desktopPluginHostServices } from "./pluginHostServices";
import type { NativeFilePickerOptions } from "../../../src/assets/filePickerContract";

test("the host service forwards generic native selection and preserves staging failures", async () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  const options: NativeFilePickerOptions = { namespace: "sample", maxFileBytes: 8, filters: [{ name: "Archive", extensions: ["zip"] }] };
  let failed = false;
  const calls: NativeFilePickerOptions[] = [];
  Object.defineProperty(globalThis, "window", { configurable: true, value: { miraDesktop: {
    pickFiles: async (request: NativeFilePickerOptions) => {
      calls.push(request); if (failed) throw new Error("staging failed"); return ["/private/selected.zip"];
    },
  } } });
  try {
    assert.deepEqual(await desktopPluginHostServices.pickFiles(options), ["/private/selected.zip"]);
    assert.deepEqual(calls, [options]);
    failed = true;
    await assert.rejects(desktopPluginHostServices.pickFiles(options), /staging failed/);
  } finally {
    if (previous) Object.defineProperty(globalThis, "window", previous);
    else Reflect.deleteProperty(globalThis, "window");
  }
});
