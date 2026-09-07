import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { configureSettingsConfigPath } from "./settings.js";
import { applyRuntimeSettings, readRuntimeSettings } from "./settingsRuntime.js";
import { createSettingsDraft } from "../renderer/src/settings/testFixtures.js";

describe("runtime settings transport", () => {
  it("reads the configuration text and version from the same runtime snapshot", async () => {
    configureSettingsConfigPath("unused-local-config.toml");
    const snapshot = await readRuntimeSettings({ invoke: async (request) => {
      assert.equal(request.method, "runtime.status");
      return { id: "1", type: "response", method: request.method, error: null, payload: {
        generation: 7, config_toml: '[llm]\nregistrations = []\n[agent]\nmax_tokens = 1234\n',
      } };
    } });
    assert.equal(snapshot.generation, 7);
    assert.equal(snapshot.formData.advanced.maxTokens, 1234);
    assert.deepEqual(snapshot.formData.models.registrations, []);
  });

  it("preserves structured apply errors and invokes only runtime.apply", async () => {
    const error = { code: "runtime_generation_conflict", message: "version changed", details: { generation: 8 } };
    const result = await applyRuntimeSettings({ invoke: async (request) => {
      assert.equal(request.method, "runtime.apply");
      assert.equal(request.payload.expected_generation, 7);
      assert.equal(request.payload.operation_id, "fixed-operation");
      return { id: "1", type: "response", method: request.method, error, payload: {} };
    } }, createSettingsDraft(), { expectedGeneration: 7, operationId: "fixed-operation" });
    assert.deepEqual(result, { ok: false, error });
  });
});
