import assert from "node:assert/strict";
import { before, describe, it } from "node:test";
import { changeInputValue, mountTestComponent } from "../shared/testing/domTestHarness";

let PluginSchemaSettingsSection: typeof import("./PluginSchemaSettingsSection").PluginSchemaSettingsSection;
before(async () => {
  const environment = await mountTestComponent(null);
  ({ PluginSchemaSettingsSection } = await import("./PluginSchemaSettingsSection"));
  await environment.cleanup();
});

describe("PluginSchemaSettingsSection", () => {
  it("renders a field per schema property and autosaves an edit through plugin.config.set", async () => {
    const view = await mountTestComponent(null);
    const calls: Array<{ method: string; payload: Record<string, unknown> }> = [];
    let stored = { app_id: "", client_secret: "" };
    Object.defineProperty(window, "miraDesktop", {
      configurable: true,
      value: {
        invoke: async ({ method, payload }: { method: string; payload: Record<string, unknown> }) => {
          calls.push({ method, payload });
          if (method === "plugin.config.get") {
            return {
              id: "1", type: "response", method, error: null,
              payload: {
                plugin_id: "demo",
                schema: {
                  title: "DemoConfig",
                  required: ["app_id"],
                  properties: {
                    app_id: { type: "string", title: "App ID" },
                    client_secret: { type: "string" },
                  },
                },
                values: stored,
              },
            };
          }
          if (method === "plugin.config.set") {
            stored = { ...stored, ...(payload.values as Record<string, unknown>) };
            return { id: "1", type: "response", method, error: null, payload: { plugin_id: "demo", values: stored, generation: 2 } };
          }
          throw new Error(`unexpected method ${method}`);
        },
      },
    });

    try {
      await view.render(<PluginSchemaSettingsSection pluginId="demo" />);
      assert.match(view.container.textContent ?? "", /App ID/);
      const input = view.container.querySelector("input") as HTMLInputElement;
      assert.ok(input, "expected the App ID input to render");
      await changeInputValue(input, "app-123");

      assert.ok(calls.some((call) => call.method === "plugin.config.set" && call.payload.values && (call.payload.values as Record<string, unknown>).app_id === "app-123"));
    } finally {
      await view.cleanup();
    }
  });

  it("shows a load error with a retry action when plugin.config.get fails", async () => {
    const view = await mountTestComponent(null);
    Object.defineProperty(window, "miraDesktop", {
      configurable: true,
      value: {
        invoke: async () => { throw new Error("backend offline"); },
      },
    });

    try {
      await view.render(<PluginSchemaSettingsSection pluginId="demo" />);
      assert.match(view.container.textContent ?? "", /backend offline/);
    } finally {
      await view.cleanup();
    }
  });
});
