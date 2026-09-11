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


describe("core proactive strategy settings round-trip", () => {
  const cases = [
    {
      name: "keeps marker-migrated disabled preferences after an unrelated save",
      source: "[agent.proactive_strategies]\nscene_followup = false\nrelationship = false\n",
      preferences: { sceneFollowup: false, relationship: false },
      expectedLines: ["scene_followup = false", "relationship = false"],
      absentLines: [],
    },
    {
      name: "keeps explicit core enablement above an old disabled plugin preference",
      source: "[plugins.relationship_proactive]\nenabled = false\n[agent.proactive_strategies]\nscene_followup = true\nrelationship = true\n",
      preferences: { sceneFollowup: true, relationship: true },
      expectedLines: ["scene_followup = true", "relationship = true", "[plugins.relationship_proactive]\nenabled = false"],
      absentLines: [],
    },
    {
      name: "leaves absent core preferences to backend defaults and marker migration",
      source: "[agent]\nmax_tokens = 4096\n",
      preferences: {},
      expectedLines: [],
      absentLines: ["[agent.proactive_strategies]", "scene_followup =", "relationship ="],
    },
    {
      name: "preserves unmigrated plugin disablement without forcing core defaults",
      source: "[plugins.relationship_proactive]\nenabled = false\n",
      preferences: {},
      expectedLines: ["[plugins.relationship_proactive]\nenabled = false"],
      absentLines: ["[agent.proactive_strategies]", "scene_followup =", "relationship ="],
    },
    {
      name: "keeps per-key core precedence and legacy fallback for a missing key",
      source: "[plugins.relationship_proactive]\nenabled = false\n[agent.proactive_strategies]\nscene_followup = true\n",
      preferences: { sceneFollowup: true },
      expectedLines: ["scene_followup = true", "[plugins.relationship_proactive]\nenabled = false"],
      absentLines: ["relationship ="],
    },
  ];

  for (const scenario of cases) {
    it(scenario.name, async () => {
      configureSettingsConfigPath(join(tmpdir(), "unused-proactive-settings.toml"));
      const draft = loadSettingsData(scenario.source).formData;
      assert.deepEqual(draft.proactiveStrategies, scenario.preferences);
      draft.advanced.maxTokens += 1;
      let applyCalls = 0;
      const result = await saveSettings(draft, async (request) => {
        applyCalls += 1;
        for (const line of scenario.expectedLines) assert.ok(request.config_toml.includes(line), line);
        for (const line of scenario.absentLines) assert.ok(!request.config_toml.includes(line), line);
        assert.deepEqual(loadSettingsData(request.config_toml).formData.proactiveStrategies, scenario.preferences);
        return { ok: true, generation: 2, changed: true };
      });
      assert.equal(result.ok, true);
      assert.equal(applyCalls, 1);
    });
  }

  it("rejects invalid core switches rather than replacing them with a default", () => {
    configureSettingsConfigPath(join(tmpdir(), "unused-proactive-settings.toml"));
    assert.throws(() => loadSettingsData('[agent.proactive_strategies]\nrelationship = "false"\n'), /必须是布尔值/);
  });
});


describe("settings TOML comments", () => {
  it("round-trips commented booleans and quoted hashes without changing their values", async () => {
    configureSettingsConfigPath(join(tmpdir(), "unused-commented-settings.toml"));
    const source = String.raw`
[agent.proactive_strategies] # core preferences
scene_followup = false # disabled
relationship = true # enabled
[channels.telegram] # channel token
 token = "token\"#inside" # outside
[channels.qq]
bot_uin = 'literal#inside' # literal value
[plugins.example]
tags = ["item#one", "item#two"] # tags
path = "C:\\" # escaped slash before closing quote
`;
    const draft = loadSettingsData(source).formData;
    assert.deepEqual(draft.proactiveStrategies, { sceneFollowup: false, relationship: true });
    assert.equal(draft.channels.telegramToken, 'token"#inside');
    assert.equal(draft.channels.qqBotUin, "literal#inside");
    assert.match(draft.advanced.pluginsRawToml, /tags = \["item#one", "item#two"\]/);
    assert.ok(draft.advanced.pluginsRawToml.includes(String.raw`path = "C:\\"`));
    let applyCalls = 0;
    const result = await saveSettings(draft, async (request) => {
      applyCalls += 1;
      assert.match(request.config_toml, /scene_followup = false/);
      assert.match(request.config_toml, /relationship = true/);
      const saved = loadSettingsData(request.config_toml).formData;
      assert.deepEqual(saved.proactiveStrategies, draft.proactiveStrategies);
      assert.deepEqual(saved.channels, draft.channels);
      assert.equal(saved.advanced.pluginsRawToml, draft.advanced.pluginsRawToml);
      return { ok: true, generation: 2, changed: true };
    });
    assert.equal(result.ok, true);
    assert.equal(applyCalls, 1);
  });

  for (const value of ['"false" # still a string', "'false' # still a literal string"]) {
    it(`rejects a quoted boolean with an inline comment: ${value}`, () => {
      configureSettingsConfigPath(join(tmpdir(), "unused-commented-settings.toml"));
      assert.throws(() => loadSettingsData(`[agent.proactive_strategies]\nrelationship = ${value}\n`), /必须是布尔值/);
    });
  }
});
