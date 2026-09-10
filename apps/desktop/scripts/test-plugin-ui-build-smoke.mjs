#!/usr/bin/env node
/**
 * Reproducible build smoke check for the plugin UI glob consumed by
 * `renderer/src/plugins/pluginUiModules.ts`.
 *
 * The repo currently ships no `plugins/<id>/ui/` directory, so the
 * `import.meta.glob` pattern in that file (one wildcard segment for `<id>`,
 * then a fixed `ui/index.tsx` suffix) matches zero files, and a plain
 * `pnpm run build:renderer` succeeding proves nothing about whether that
 * glob resolves to the right place. This script creates a
 * throwaway plugin UI module under the real top-level `plugins/` tree with a
 * recognizable marker string, runs a real renderer build against it, asserts
 * the marker made it into the bundled output, and removes the throwaway
 * plugin directory afterwards (on success or failure) so it is safe to
 * re-run repeatedly on a clean checkout.
 */
import { randomUUID } from "node:crypto";
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build as viteBuild } from "vite";

const here = dirname(fileURLToPath(import.meta.url));
const desktopRoot = resolve(here, "..");
const repoRoot = resolve(desktopRoot, "..", "..");

const suffix = randomUUID().replace(/-/g, "").slice(0, 12);
const marker = `PLUGIN_UI_BUILD_SMOKE_${suffix}`;
const pluginId = `plugin_ui_build_smoke_${suffix}`;
const pluginDir = join(repoRoot, "plugins", pluginId);
const uiDir = join(pluginDir, "ui");

/** Recursively searches built JS output for the marker string. */
async function bundleContainsMarker(dir, needle) {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (await bundleContainsMarker(path, needle)) return true;
      continue;
    }
    if (!/\.m?js$/.test(entry.name)) continue;
    const content = await readFile(path, "utf-8");
    if (content.includes(needle)) return true;
  }
  return false;
}

async function main() {
  await mkdir(uiDir, { recursive: true });
  await writeFile(
    join(uiDir, "index.tsx"),
    [
      "// Throwaway fixture written by test-plugin-ui-build-smoke.mjs; not meant to be committed.",
      `const MARKER = ${JSON.stringify(marker)};`,
      "",
      "export default {",
      `  pluginId: ${JSON.stringify(pluginId)},`,
      "  settingsSection: { kind: \"component\", label: MARKER, component: () => null },",
      "  navPage: { label: MARKER, component: () => null },",
      "};",
      "",
    ].join("\n"),
    "utf-8",
  );

  const outDir = await mkdtemp(join(tmpdir(), "plugin-ui-build-smoke-"));
  try {
    await viteBuild({
      configFile: resolve(desktopRoot, "renderer", "vite.config.ts"),
      logLevel: "warn",
      build: { outDir, emptyOutDir: true },
    });

    const found = await bundleContainsMarker(outDir, marker);
    if (!found) {
      throw new Error(
        `expected marker ${marker} to appear in the built renderer bundle, but it did not. ` +
          "The plugins/<id>/ui/index.tsx glob in pluginUiModules.ts is not matching real build output.",
      );
    }
    console.log(`[plugin-ui-build-smoke] passed: marker for ${pluginId} found in the built bundle.`);
  } finally {
    await rm(outDir, { recursive: true, force: true });
  }
}

main()
  .catch((error) => {
    console.error("[plugin-ui-build-smoke] FAILED");
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await rm(pluginDir, { recursive: true, force: true });
  });
