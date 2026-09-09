import assert from "node:assert/strict";
import test from "node:test";
import { act } from "react";
import type { DesktopUpdateApi, DesktopUpdateState } from "../../../src/updateContract.js";
import { mountTestComponent } from "../shared/testing/domTestHarness";
import { AboutSettingsPage } from "./AboutSettingsPage";

test("the visible update action checks, reports progress and installs only a ready update", async () => {
  const view = await mountTestComponent(null);
  let notify!: (state: DesktopUpdateState) => void;
  let checks = 0;
  let installs = 0;
  const snapshot: DesktopUpdateState = { revision: 0, currentVersion: "0.2.0", phase: "idle", latestVersion: null, progress: 0, error: null };
  const api: DesktopUpdateApi = {
    getState: async () => snapshot,
    check: async () => { checks += 1; return { ...snapshot, revision: 1, phase: "current" }; },
    install: async () => { installs += 1; },
    onState: (listener) => { notify = listener; return () => undefined; },
  };
  Object.defineProperty(window, "miraDesktop", { configurable: true, value: { updates: api } });
  try {
    await view.render(<AboutSettingsPage />);
    assert.match(view.container.textContent ?? "", /当前版本 v0.2.0/);
    const button = view.container.querySelector("button");
    assert.ok(button);
    await act(async () => button.click());
    assert.equal(checks, 1);
    assert.match(view.container.textContent ?? "", /已是最新版本/);
    await act(async () => notify({ ...snapshot, revision: 2, phase: "downloading", latestVersion: "0.3.0", progress: 45 }));
    assert.equal(button.disabled, true);
    assert.equal(view.container.querySelector("progress")?.value, 45);
    await act(async () => notify({ ...snapshot, revision: 3, phase: "downloaded", latestVersion: "0.3.0", progress: 100 }));
    assert.equal(button.textContent?.trim(), "重启并安装");
    assert.equal(button.disabled, false);
    await act(async () => button.click());
    assert.equal(installs, 1);
  } finally { await view.cleanup(); }
});

test("failed status loading remains retryable", async () => {
  const view = await mountTestComponent(null);
  const api: DesktopUpdateApi = {
    getState: async () => { throw new Error("connection lost"); },
    check: async () => ({ revision: 1, currentVersion: "0.2.0", phase: "current", latestVersion: null, progress: 0, error: null }),
    install: async () => undefined,
    onState: () => () => undefined,
  };
  Object.defineProperty(window, "miraDesktop", { configurable: true, value: { updates: api } });
  try {
    await view.render(<AboutSettingsPage />);
    assert.match(view.container.querySelector('[role="alert"]')?.textContent ?? "", /connection lost/);
    const button = view.container.querySelector("button");
    assert.ok(button);
    assert.equal(button.disabled, false);
    await act(async () => button.click());
    assert.equal(view.container.querySelector('[role="alert"]'), null);
    assert.match(view.container.textContent ?? "", /已是最新版本/);
  } finally { await view.cleanup(); }
});
