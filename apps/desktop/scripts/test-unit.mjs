import { readdir, stat } from "node:fs/promises";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const desktopRoot = resolve(here, "..");
const repoRoot = resolve(desktopRoot, "..", "..");

/**
 * Renderer code owned by plugins rather than by the host.
 *
 * A plugin's `ui/` and `surface/` directories are compiled into the renderer
 * bundle (#174, #181) but live outside `apps/desktop/`, so their colocated
 * tests are invisible to a fixed list of desktop test roots. Discovering them
 * here is what keeps moving renderer code into a plugin from silently dropping
 * its coverage.
 */
async function pluginTestRoots() {
  const pluginsRoot = resolve(repoRoot, "plugins");
  let entries;
  try {
    entries = await readdir(pluginsRoot, { withFileTypes: true });
  } catch {
    return [];
  }
  const roots = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    for (const area of ["ui", "surface"]) {
      const candidate = join(pluginsRoot, entry.name, area);
      try {
        if ((await stat(candidate)).isDirectory()) roots.push(candidate);
      } catch {
        // A plugin without that area is the normal case, not a problem.
      }
    }
  }
  return roots;
}

const testRoots = [
  resolve(desktopRoot, "src"),
  resolve(desktopRoot, "renderer", "src"),
  // 跨模块集成回归；e2e 脚本用 *.e2e.ts 命名，不会被这里收集
  resolve(desktopRoot, "tests", "integration"),
  ...(await pluginTestRoots()),
];

async function findTestFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(entries.map(async (entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return await findTestFiles(path);
    }
    return /\.test\.tsx?$/.test(entry.name) ? [path] : [];
  }));
  return files.flat();
}

const testFiles = (await Promise.all(testRoots.map(findTestFiles))).flat().sort();
if (!testFiles.length) {
  throw new Error("no desktop unit tests found");
}

const tsxCli = resolve(repoRoot, "node_modules", "tsx", "dist", "cli.mjs");
const rendererTsconfig = resolve(desktopRoot, "renderer", "tsconfig.json");
const child = spawn(
  process.execPath,
  [tsxCli, "--tsconfig", rendererTsconfig, "--test", ...testFiles],
  { cwd: repoRoot, stdio: "inherit" },
);

child.on("error", (error) => {
  throw error;
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exitCode = code ?? 1;
});
