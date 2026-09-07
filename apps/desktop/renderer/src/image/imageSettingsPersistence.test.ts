import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { saveImageSettings } from "./imageSettingsPersistence.js";
import { createSettingsDraft } from "../settings/testFixtures.js";

describe("saveImageSettings", () => {
  it("patches the latest settings version and reports apply failure", async () => {
    const latest = createSettingsDraft();
    latest.channels.telegramToken = "external-edit";
    await assert.rejects(saveImageSettings({
      readSettings: async () => ({ configPath: "config.toml", generation: 9, formData: latest }),
      saveSettings: async (draft, options) => {
        assert.equal(options?.expectedGeneration, 9);
        assert.equal(draft.channels.telegramToken, "external-edit");
        assert.equal(draft.integrations.novelaiNsfwEnabled, true);
        return { ok: false, error: { code: "runtime_apply_failed", message: "candidate rejected" } };
      },
    }, { novelaiNsfwEnabled: true }), /candidate rejected/);
  });
});
