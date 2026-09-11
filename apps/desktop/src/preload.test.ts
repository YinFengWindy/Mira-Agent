import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import ts from "typescript";
import type { DesktopApi } from "./bridge/shared";
import { PreloadLocalAssetCache } from "./assets/preloadLocalAssetCache";

/** Runs the actual preload with a mocked Electron boundary, without launching a desktop. */
async function loadPreload(invoke: (channel: string, options: unknown) => Promise<unknown>) {
  const source = await readFile(new URL("./preload.ts", import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } });
  const exposed: { api?: DesktopApi } = {};
  const constantModules = new Set(["./assets/localAssetContract.js", "./surface/host.js", "./surface/ipc.js", "./plugins/ipc.js", "./tray/ipc.js"]);
  runInNewContext(compiled.outputText, {
    exports: {}, window: { addEventListener: () => {} },
    require: (name: string) => {
      if (name === "electron") return { ipcRenderer: { invoke }, contextBridge: {
        exposeInMainWorld: (_name: string, api: DesktopApi) => { exposed.api = api; },
      } };
      if (name === "./assets/preloadLocalAssetCache.js") return { PreloadLocalAssetCache };
      if (constantModules.has(name)) return {};
      throw new Error(`unexpected preload import: ${name}`);
    },
  });
  assert.ok(exposed.api);
  return exposed.api;
}

test("preload exposes generic staged file selection without granting archive media URLs", async () => {
  const calls: unknown[] = [];
  let result: string[] = ["/private/archive.zip"];
  const api = await loadPreload(async (channel, options) => { calls.push({ channel, options }); return result; });
  const options = { namespace: "sample", maxFileBytes: 1024, filters: [{ name: "Archives", extensions: ["zip"] }] };
  assert.deepEqual(await api.pickFiles(options), result);
  assert.deepEqual(calls, [{ channel: "desktop:pick-files", options }]);
  assert.equal("pickPetPackage" in api, false);
  assert.notEqual(api.localAssetUrl(result[0]), result[0]);
  result = [];
  assert.deepEqual(await api.pickFiles(options), []);
  const failing = await loadPreload(async () => { throw new Error("copy failed"); });
  await assert.rejects(failing.pickFiles(options), /copy failed/);
});
