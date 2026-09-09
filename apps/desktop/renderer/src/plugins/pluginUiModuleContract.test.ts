import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { applyPluginUiModules, type PluginUiModule } from "./pluginUiModuleContract.js";
import { PluginUiRegistry } from "./pluginUiRegistry.js";

describe("applyPluginUiModules", () => {
  it("registers a schema-driven settings.section under the plugin's own id", () => {
    const registry = new PluginUiRegistry();
    const modules: Record<string, { default: PluginUiModule }> = {
      "/plugins/demo/ui/index.tsx": {
        default: { pluginId: "demo", settingsSection: { kind: "schema", label: "Demo" } },
      },
    };

    applyPluginUiModules(modules, registry);

    const entry = registry.getSettingsSection("demo");
    assert.ok(entry, "expected a settings.section entry for the demo plugin");
    assert.equal(entry?.kind, "standalone");
    assert.equal(entry?.pluginId, "demo");
    assert.equal(entry?.label, "Demo");
  });

  it("registers a custom-component settings.section and a nav.page from the same module", () => {
    const registry = new PluginUiRegistry();
    function CustomSection() { return null; }
    function NavPage() { return null; }
    const modules: Record<string, { default: PluginUiModule }> = {
      "/plugins/demo/ui/index.tsx": {
        default: {
          pluginId: "demo",
          settingsSection: { kind: "component", label: "Demo", component: CustomSection },
          navPage: { label: "Demo Page", component: NavPage },
        },
      },
    };

    applyPluginUiModules(modules, registry);

    assert.equal(registry.getSettingsSection("demo")?.Component, CustomSection);
    assert.equal(registry.getNavPage("demo")?.Component, NavPage);
  });

  it("skips a malformed module instead of throwing", () => {
    const registry = new PluginUiRegistry();
    const modules = { "/plugins/broken/ui/index.tsx": { default: { settingsSection: {} } } } as unknown as Record<
      string, { default: PluginUiModule }
    >;

    assert.doesNotThrow(() => applyPluginUiModules(modules, registry));
    assert.equal(registry.listSettingsSections().length, 0);
  });
});
