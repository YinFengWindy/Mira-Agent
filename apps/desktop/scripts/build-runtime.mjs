import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { cp, mkdir, rm } from "node:fs/promises";
import { basename, delimiter, join, resolve } from "node:path";
import { resolveReleaseManifest } from "./release-manifest.mjs";

const releaseManifest = resolveReleaseManifest();
const { backendRoot, repositoryRoot } = releaseManifest;
const runtimeRoot = releaseManifest.runtimeOutput;
const workRoot = releaseManifest.pyinstallerWork;
const python = resolve(repositoryRoot, ".venv", "Scripts", "python.exe");
if (!existsSync(python)) {
  throw new Error(`Repository Python environment not found: ${python}`);
}

await rm(runtimeRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(runtimeRoot, { recursive: true });

// Plugin packages keep their own `tests/` alongside their source (see
// plugins/<id>/tests/), so a plain directory copy would ship pytest-only
// modules (~925K) to end users and make PyInstaller's submodule collector
// try to import them. Stage a filtered copy of `plugins/` that drops each
// plugin's `tests/` directory and `__pycache__`, then point PyInstaller at
// the staging copy instead of the real source tree.
const stagingRoot = resolve(workRoot, "plugins-staging");
await mkdir(stagingRoot, { recursive: true });
const stagedPluginsDir = join(stagingRoot, "plugins");
await cp(join(repositoryRoot, "plugins"), stagedPluginsDir, {
  recursive: true,
  filter: (source) => {
    const name = basename(source);
    return name !== "tests" && name !== "__pycache__";
  },
});

const dataSeparator = delimiter;
const args = [
  "-m",
  "PyInstaller",
  "--noconfirm",
  "--clean",
  "--onedir",
  "--name",
  "shiori-runtime",
  "--distpath",
  runtimeRoot,
  "--workpath",
  workRoot,
  "--specpath",
  workRoot,
  "--paths",
  backendRoot,
  "--paths",
  stagingRoot,
  "--add-data",
  `${stagedPluginsDir}${dataSeparator}plugins`,
  "--add-data",
  `${join(backendRoot, "skills")}${dataSeparator}skills`,
  "--add-data",
  `${join(repositoryRoot, "apps", "desktop", "renderer", "src", "chat", "common_emojis.json")}${dataSeparator}.`,
  "--collect-submodules",
  "plugins",
  "--collect-submodules",
  "desktop_bridge",
  "--collect-submodules",
  "agent",
  join(backendRoot, "main.py"),
];

const child = spawn(python, args, { cwd: backendRoot, stdio: "inherit" });
child.once("error", (error) => {
  throw new Error(`Unable to start PyInstaller with ${python}: ${error.message}`);
});
const exitCode = await new Promise((resolveExit) => child.once("exit", (code) => resolveExit(code ?? 1)));
if (exitCode !== 0) {
  throw new Error(`PyInstaller failed with exit code ${exitCode}`);
}
