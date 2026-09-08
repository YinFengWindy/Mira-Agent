import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { configureSettingsConfigPath, loadSettingsData } from "../../../src/settings";
import { loadOnboardingData, registerOnboardingModel } from "./onboardingData";

const registration = { id: "first", provider: "openai", model: "test-model", apiKey: "test-key", baseUrl: "", effort: "none" as const };
configureSettingsConfigPath("onboarding-test.toml");
describe("onboarding data", () => {
  it("never interprets bridge errors as an empty role list", async () => {
    await assert.rejects(loadOnboardingData({
      readSettings: async () => loadSettingsData("[llm]\n"),
      invoke: async () => ({ id: "1", type: "response", method: "roles.list", payload: {}, error: { code: "offline", message: "offline" } }),
    }), /offline/);
  });
  it("preserves other settings and registrations across a retry with the same draft id", async () => {
    let snapshot = { ...loadSettingsData("[llm]\n"), generation: 3 };
    const existing = { ...registration, id: "existing" };
    snapshot.formData.models.registrations = [existing];
    const voice = structuredClone(snapshot.formData.voice);
    const api = {
      readSettings: async () => snapshot,
      saveSettings: async (draft: typeof snapshot.formData, options?: { expectedGeneration?: number }) => {
        assert.equal(options?.expectedGeneration, snapshot.generation);
        snapshot = { ...snapshot, formData: draft, generation: snapshot.generation + 1 };
        return { ok: true, generation: snapshot.generation, changed: true };
      },
    };
    await registerOnboardingModel(api, registration);
    await registerOnboardingModel(api, registration);
    assert.deepEqual(snapshot.formData.models.registrations.map((item) => item.id), ["existing", "first"]);
    assert.deepEqual(snapshot.formData.voice, voice);
  });
  it("surfaces a rejected settings transaction", async () => {
    await assert.rejects(registerOnboardingModel({ readSettings: async () => loadSettingsData("[llm]\n"),
      saveSettings: async () => ({ ok: false, error: { code: "invalid", message: "模型无效" } }),
    }, registration), /模型无效/);
  });
});
