import assert from "node:assert/strict";
import test from "node:test";
import { mountTestComponent } from "../shared/testing/domTestHarness";
import { SettingsPage } from "./SettingsPage";

test("the about route stays available while the backend is offline", async () => {
  const view = await mountTestComponent(null);
  let settingsReads = 0;
  Object.defineProperty(window, "miraDesktop", {
    configurable: true,
    value: {
      updates: {
        getState: async () => ({ revision: 0, currentVersion: "0.2.0", phase: "unsupported", latestVersion: null, progress: 0, error: null }),
        onState: () => () => undefined,
      },
      readSettings: async () => { settingsReads += 1; throw new Error("backend offline"); },
    },
  });
  try {
    await view.render(<SettingsPage bridgeReady={false} section="about" />);
    assert.match(view.container.textContent ?? "", /当前版本 v0.2.0/);
    assert.doesNotMatch(view.container.textContent ?? "", /开发模式/);
    assert.equal(view.container.querySelector("button")?.disabled, true);
    assert.equal(settingsReads, 0);
  } finally { await view.cleanup(); }
});
