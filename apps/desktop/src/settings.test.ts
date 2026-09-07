import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { describe, it } from "node:test";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { configureSettingsConfigPath, loadSettingsData, saveSettings } from "./settings.js";
import { desktopSettingsDefaults } from "./settingsContract.js";

describe("desktop settings config path", () => {
  it("requires the runtime path contract instead of falling back to the repository root", () => {
    assert.throws(() => loadSettingsData(), /桌面配置路径尚未初始化/);
  });

  it("loads settings from the configured workspace path", () => {
    const directory = mkdtempSync(join(tmpdir(), "shiori-settings-"));
    const configPath = join(directory, "workspace", "config.toml");
    try {
      mkdirSync(join(directory, "workspace"), { recursive: true });
      writeFileSync(configPath, "[llm]\n", { encoding: "utf-8" });
      configureSettingsConfigPath(configPath);

      const snapshot = loadSettingsData();

      assert.equal(snapshot.configPath, configPath);
      assert.deepEqual(snapshot.formData.voice, {
        enabled: false,
        hotkey: "Ctrl+Space",
        microphoneDeviceId: "",
        asrEnabled: false,
        asrProvider: desktopSettingsDefaults.asrProvider,
        asrBaseUrl: desktopSettingsDefaults.asrBaseUrl,
        asrSecretId: "",
        asrSecretKey: "",
        ttsEnabled: false,
        ttsProvider: desktopSettingsDefaults.ttsProvider,
        ttsBaseUrl: desktopSettingsDefaults.ttsBaseUrl,
        ttsModel: desktopSettingsDefaults.ttsModel,
        ttsApiKey: "",
        ttsVolume: desktopSettingsDefaults.ttsVolume,
      });
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });

  it("submits a candidate and deferred bindings without overwriting the active file", async () => {
    const directory = mkdtempSync(join(tmpdir(), "shiori-settings-save-"));
    const configPath = join(directory, "workspace", "config.toml");
    try {
      mkdirSync(join(directory, "workspace"), { recursive: true });
      writeFileSync(configPath, "[llm]\n", { encoding: "utf-8" });
      configureSettingsConfigPath(configPath);
      const formData = loadSettingsData().formData;
      formData.models.registrations = [{
        id: "00000000-0000-4000-a000-000000000001",
        provider: "openai",
        baseUrl: "",
        apiKey: "",
        model: "test-model",
        effort: "none",
      }];
      formData.pendingRoleModelUpdates = [{ roleId: "role-1", runtimeConfig: { dialogue_model_registration_id: "" } }];
      let applyCalls = 0;

      const result = await saveSettings(formData, async (request) => {
        applyCalls += 1;
        assert.match(request.config_toml, /model = "test-model"/);
        assert.equal(request.expected_generation, 3);
        assert.equal(request.operation_id, "retry-operation");
        assert.deepEqual(request.role_model_updates, [{ role_id: "role-1", runtime_config: { dialogue_model_registration_id: "" } }]);
        return { ok: false, error: { code: "runtime_apply_failed", message: "candidate failed" } };
      }, { expectedGeneration: 3, operationId: "retry-operation" });

      assert.equal(applyCalls, 1);
      assert.equal(result.ok, false);
      assert.equal(readFileSync(configPath, "utf-8"), "[llm]\n");
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });

  it("serializes empty registrations explicitly and accepts incomplete connection details", async () => {
    configureSettingsConfigPath(join(tmpdir(), "unused-config-path.toml"));
    const formData = loadSettingsData("[llm]\nregistrations = []\n").formData;
    await saveSettings(formData, async (request) => {
      assert.match(request.config_toml, /\[llm\]\nregistrations = \[\]/);
      assert.deepEqual(request.role_model_updates, []);
      return { ok: true, generation: 2, changed: true };
    });
    formData.models.registrations = [{ id: "00000000-0000-4000-a000-000000000001", model: "", provider: "openai", apiKey: "", baseUrl: "", effort: "none" }];
    const result = await saveSettings(formData, async () => ({ ok: true, generation: 3 }));
    assert.equal(result.ok, true);
  });
});
