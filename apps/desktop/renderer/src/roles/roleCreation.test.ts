import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildRoleCreationRequest, createRoleFromDraft } from "./roleCreation";

const form = { name: "小诗", description: "", systemPrompt: "安静、细心" };
describe("role creation", () => {
  it("sends the selected avatar in the same manual creation request", () => {
    assert.deepEqual(buildRoleCreationRequest({ ...form, avatarSource: "avatar.png" }), {
      method: "roles.create", payload: { name: form.name, description: "", system_prompt: form.systemPrompt, avatar_source: "avatar.png" },
    });
  });
  it("distinguishes keeping, replacing, and removing an imported avatar", () => {
    const imported = { ...form, importId: "import-1" };
    for (const avatarSource of [undefined, "new.png", ""]) {
      const { payload } = buildRoleCreationRequest({ ...imported, avatarSource });
      assert.ok("overrides" in payload);
      assert.equal(payload.overrides.avatar_source, avatarSource);
      assert.equal("avatar_source" in payload.overrides, avatarSource !== undefined);
    }
  });
  it("rejects persistence failures without pretending a role was created", async () => {
    await assert.rejects(createRoleFromDraft(form, async () => ({ id: "1", type: "response", method: "roles.create", payload: {}, error: { code: "asset_error", message: "头像保存失败" } })), /头像保存失败/);
    await assert.rejects(createRoleFromDraft(form, async () => ({ id: "1", type: "response", method: "roles.create", payload: {}, error: null })), /缺少角色信息/);
  });
});
