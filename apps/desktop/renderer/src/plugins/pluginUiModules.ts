import { applyPluginUiModules, type PluginUiModule } from "./pluginUiModuleContract";

/**
 * Compiles every plugin's UI entry point straight into the renderer bundle
 * (no runtime dynamic import of third-party code, per the issue #174
 * decision). `import.meta.glob` is a Vite build-time macro: it cannot be
 * exercised by the plain node:test/tsx unit test runner this repo uses for
 * everything else, so this file has no unit test of its own — the glob's
 * path resolution and bundling are covered by `pnpm run build` succeeding,
 * and the actual merge logic it delegates to (`applyPluginUiModules`) is
 * unit tested against a hand-built module record in
 * `pluginUiModuleContract.test.ts`. See the Testing Decisions section of
 * docs/specs/2026-09-09-issue-174-plugin-system-restructure.md.
 */
const modules = import.meta.glob<{ default: PluginUiModule }>(
  "/../../../plugins/*/ui/index.tsx",
  { eager: true },
);

applyPluginUiModules(modules);
