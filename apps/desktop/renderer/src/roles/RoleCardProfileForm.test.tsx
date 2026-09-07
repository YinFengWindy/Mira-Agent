import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { changeInputValue, mountTestComponent } from "../shared/testing/domTestHarness";
import type { RoleProfileDraft } from "../shared/types";
import { RoleCardProfileForm } from "./RoleCardProfileForm";

describe("RoleCardProfileForm", () => {
  it("edits response constraints independently while retaining imported knowledge", async () => {
    const profile: RoleProfileDraft = {
      character: { profile: "档案管理员", behavior_rules: "诚实", response_constraints: "简洁" },
      knowledge_base: { enabled: false, entries: [{ content: "图书馆位置" }] },
    };
    let updated = profile;
    const view = await mountTestComponent(<RoleCardProfileForm profile={profile} onUpdate={(next) => { updated = next; }} />);
    try {
      const label = Array.from(view.container.querySelectorAll("label")).find((item) => item.textContent?.includes("回复约束"));
      const field = label?.querySelector("textarea");
      assert.ok(field);
      assert.equal(field.value, "简洁");
      await changeInputValue(field, "每次回复一句");
      assert.equal(updated.character?.response_constraints, "每次回复一句");
      assert.equal(updated.character?.behavior_rules, "诚实");
      assert.equal(updated.character?.profile, "档案管理员");
      assert.deepEqual(updated.knowledge_base, profile.knowledge_base);
    } finally {
      await view.cleanup();
    }
  });
});
