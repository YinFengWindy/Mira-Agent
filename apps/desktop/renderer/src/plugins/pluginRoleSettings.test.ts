import assert from "node:assert/strict";
import { test } from "node:test";
import { pluginRoleSettingsRegistry } from "./pluginFeatureRegistry";
import { pluginRoleSettingsDirty, readPluginRoleSettings, writePluginRoleSettings } from "./pluginRoleSettings";

test("role extensions round trip their keys without replacing another module's values", () => {
  pluginRoleSettingsRegistry.register({ pluginId: "sample", Component: () => null,
    read: (runtime) => ({ selected: Boolean(runtime.sample_selected) }),
    write: (runtime, values) => ({ ...runtime, sample_selected: values.selected }),
  });
  try {
    const runtime = { sample_selected: true, mood: "happy" };
    const drafts = readPluginRoleSettings(runtime);
    assert.equal(pluginRoleSettingsDirty(drafts, runtime), false);
    const changed = { ...drafts, sample: { selected: false } };
    assert.equal(pluginRoleSettingsDirty(changed, runtime), true);
    assert.deepEqual(writePluginRoleSettings(runtime, changed), { sample_selected: false, mood: "happy" });
  } finally {
    pluginRoleSettingsRegistry.unregister("sample");
  }
});
