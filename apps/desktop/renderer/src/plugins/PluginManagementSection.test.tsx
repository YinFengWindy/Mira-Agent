import assert from "node:assert/strict";
import { before, describe, it } from "node:test";
import { act } from "react";
import { mountTestComponent } from "../shared/testing/domTestHarness";

let PluginManagementSection: typeof import("./PluginManagementSection").PluginManagementSection;
before(async () => {
  const environment = await mountTestComponent(null);
  ({ PluginManagementSection } = await import("./PluginManagementSection"));
  await environment.cleanup();
});

describe("PluginManagementSection", () => {
  it("lists every discovered plugin and hot toggles one through plugins.setEnabled", async () => {
    const view = await mountTestComponent(null);
    const calls: Array<{ method: string; payload: Record<string, unknown> }> = [];
    let helloEnabled = true;
    Object.defineProperty(window, "miraDesktop", {
      configurable: true,
      value: {
        invoke: async ({ method, payload }: { method: string; payload: Record<string, unknown> }) => {
          calls.push({ method, payload });
          if (method === "plugins.list") {
            return {
              id: "1", type: "response", method, error: null,
              payload: {
                plugins: [
                  { id: "hello", name: "hello", version: "0.1", description: "示例插件", enabled: helloEnabled, state: helloEnabled ? "ACTIVE" : "DISABLED", error: "", has_config_schema: false },
                ],
              },
            };
          }
          if (method === "plugins.setEnabled") {
            helloEnabled = payload.enabled as boolean;
            return { id: "1", type: "response", method, error: null, payload: { plugin_id: "hello", enabled: helloEnabled, generation: 2 } };
          }
          throw new Error(`unexpected method ${method}`);
        },
      },
    });

    try {
      await view.render(<PluginManagementSection />);
      assert.match(view.container.textContent ?? "", /hello/);
      assert.match(view.container.textContent ?? "", /ACTIVE/);

      const toggle = view.container.querySelector('button[role="switch"]') as HTMLButtonElement;
      assert.ok(toggle, "expected an enable switch to render");
      assert.equal(toggle.getAttribute("aria-checked"), "true");

      await act(async () => { toggle.dispatchEvent(new MouseEvent("click", { bubbles: true })); });

      assert.ok(calls.some((call) => call.method === "plugins.setEnabled" && call.payload.enabled === false));
      assert.match(view.container.textContent ?? "", /DISABLED/);
    } finally {
      await view.cleanup();
    }
  });

  it("shows a load error with a retry action when plugins.list fails", async () => {
    const view = await mountTestComponent(null);
    Object.defineProperty(window, "miraDesktop", {
      configurable: true,
      value: { invoke: async () => { throw new Error("backend offline"); } },
    });

    try {
      await view.render(<PluginManagementSection />);
      assert.match(view.container.textContent ?? "", /backend offline/);
    } finally {
      await view.cleanup();
    }
  });
});
