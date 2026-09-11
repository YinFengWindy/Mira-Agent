import assert from "node:assert/strict";
import { test } from "node:test";
import { PluginTrayError, PluginTrayRegistry } from "./registry.js";

test("entries render in the order they were contributed", () => {
  const registry = new PluginTrayRegistry();

  registry.setEntry("desktop_pet", "toggle", { label: "显示桌宠" });
  registry.setEntry("novelai", "open", { label: "打开图库" });

  assert.deepEqual(registry.list().map((entry) => entry.entryId), ["toggle", "open"]);
});

test("updating an entry keeps its place in the menu", () => {
  const registry = new PluginTrayRegistry();
  registry.setEntry("desktop_pet", "toggle", { label: "显示桌宠" });
  registry.setEntry("novelai", "open", { label: "打开图库" });

  // The pet rewrites this label every time it is shown or hidden; re-inserting
  // would make the item jump to the bottom of the menu each time.
  registry.setEntry("desktop_pet", "toggle", { label: "隐藏桌宠", enabled: false });

  assert.deepEqual(registry.list(), [
    { pluginId: "desktop_pet", entryId: "toggle", label: "隐藏桌宠", enabled: false },
    { pluginId: "novelai", entryId: "open", label: "打开图库", enabled: true },
  ]);
});

test("two plugins may use the same entry id without colliding", () => {
  const registry = new PluginTrayRegistry();

  registry.setEntry("a", "toggle", { label: "A" });
  registry.setEntry("b", "toggle", { label: "B" });

  assert.deepEqual(registry.list().map((entry) => entry.label), ["A", "B"]);
});

test("ids that would collide under a joined key stay distinct", () => {
  const registry = new PluginTrayRegistry();

  // Neither id is validated for content, so a separator-joined key would make
  // these two the same entry and one would silently overwrite the other.
  registry.setEntry("a", "b:c", { label: "first" });
  registry.setEntry("a:b", "c", { label: "second" });

  assert.deepEqual(registry.list().map((entry) => entry.label), ["first", "second"]);
});

test("removing one entry leaves the plugin's others alone", () => {
  const registry = new PluginTrayRegistry();
  registry.setEntry("desktop_pet", "toggle", { label: "显示桌宠" });
  registry.setEntry("desktop_pet", "settings", { label: "桌宠设置" });

  registry.removeEntry("desktop_pet", "toggle");

  assert.deepEqual(registry.list().map((entry) => entry.entryId), ["settings"]);
});

test("disabling a plugin drops everything it contributed and nothing else", () => {
  const registry = new PluginTrayRegistry();
  registry.setEntry("desktop_pet", "toggle", { label: "显示桌宠" });
  registry.setEntry("desktop_pet", "settings", { label: "桌宠设置" });
  registry.setEntry("novelai", "open", { label: "打开图库" });

  // #181's "停用桌宠插件后...托盘...全部回收": the host holds the entries, so
  // reclaiming them does not depend on disabled plugin code running.
  registry.removeAllForPlugin("desktop_pet");

  assert.deepEqual(registry.list().map((entry) => entry.pluginId), ["novelai"]);
});

test("observers are notified exactly when the menu would render differently", () => {
  const registry = new PluginTrayRegistry();
  let notifications = 0;
  const unsubscribe = registry.onChanged(() => { notifications += 1; });

  registry.setEntry("desktop_pet", "toggle", { label: "显示桌宠" });
  assert.equal(notifications, 1);

  registry.setEntry("desktop_pet", "toggle", { label: "隐藏桌宠" });
  assert.equal(notifications, 2);

  // Re-setting an entry to the value it already has is not a change. The pet
  // recomputes its item after every remembered position — every drag, glide
  // and role-requested move — and each notify rebuilds a native menu.
  registry.setEntry("desktop_pet", "toggle", { label: "隐藏桌宠" });
  registry.setEntry("desktop_pet", "toggle", { label: "隐藏桌宠", enabled: true });
  assert.equal(notifications, 2);

  // Only `enabled` differing is still a change.
  registry.setEntry("desktop_pet", "toggle", { label: "隐藏桌宠", enabled: false });
  assert.equal(notifications, 3);

  // Nothing to remove: the menu is unchanged, so the tray must not rebuild.
  registry.removeEntry("desktop_pet", "missing");
  registry.removeAllForPlugin("novelai");
  assert.equal(notifications, 3);

  unsubscribe();
  registry.removeEntry("desktop_pet", "toggle");
  assert.equal(notifications, 3);
});

test("an entry with no usable label is refused rather than rendered blank", () => {
  const registry = new PluginTrayRegistry();

  assert.throws(() => registry.setEntry("desktop_pet", "toggle", { label: "   " }), PluginTrayError);
  assert.deepEqual(registry.list(), []);
});

test("entries default to enabled", () => {
  const registry = new PluginTrayRegistry();

  registry.setEntry("desktop_pet", "toggle", { label: "显示桌宠" });

  assert.equal(registry.list()[0].enabled, true);
});
