import assert from "node:assert/strict";
import { test } from "node:test";
import { buildTrayMenuTemplate } from "./menuTemplate.js";
import type { PluginTrayEntry } from "./registry.js";

const entry = (overrides: Partial<PluginTrayEntry> = {}): PluginTrayEntry => ({
  pluginId: "desktop_pet",
  entryId: "toggle",
  label: "显示桌宠",
  enabled: true,
  ...overrides,
});

function actions() {
  const calls: string[] = [];
  return {
    calls,
    handlers: {
      onShowWindow: () => calls.push("show-window"),
      onQuitRequested: () => calls.push("quit"),
      onPluginEntryClick: (pluginId: string, entryId: string) => calls.push(`${pluginId}/${entryId}`),
    },
  };
}

test("plugin items sit between the host's own two, in contribution order", () => {
  const template = buildTrayMenuTemplate(
    [entry(), entry({ pluginId: "novelai", entryId: "open", label: "打开图库" })],
    actions().handlers,
  );

  assert.deepEqual(template.map((item) => item.label), ["显示主窗口", "显示桌宠", "打开图库", "退出 Shiori"]);
});

test("with no plugin items the menu is exactly what it was before #181-D", () => {
  const template = buildTrayMenuTemplate([], actions().handlers);

  // The baseline menu on a platform where no plugin contributes anything.
  assert.deepEqual(template.map((item) => item.label), ["显示主窗口", "退出 Shiori"]);
});

test("a disabled entry stays disabled in the menu", () => {
  const template = buildTrayMenuTemplate([entry({ enabled: false })], actions().handlers);

  assert.equal(template[1].enabled, false);
});

test("each row invokes the action it belongs to, with the entry that owns it", () => {
  const { calls, handlers } = actions();
  const template = buildTrayMenuTemplate(
    [entry(), entry({ pluginId: "novelai", entryId: "open", label: "打开图库" })],
    handlers,
  );

  for (const item of template) item.click();

  assert.deepEqual(calls, ["show-window", "desktop_pet/toggle", "novelai/open", "quit"]);
});
