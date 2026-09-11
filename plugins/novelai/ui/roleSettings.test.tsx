import assert from "node:assert/strict";
import { test } from "node:test";
import { novelAiRoleSettings } from "./roleSettings";

test("NovelAI retains the persisted automatic CG preference and preserves unrelated role values", () => {
  assert.deepEqual(novelAiRoleSettings.read({}), { autoSceneCgEnabled: false });
  const runtime = { auto_scene_cg_enabled: true, nsfw_memory_enabled: true };
  assert.deepEqual(novelAiRoleSettings.read(runtime), { autoSceneCgEnabled: true });
  assert.deepEqual(novelAiRoleSettings.write(runtime, { autoSceneCgEnabled: false }), {
    auto_scene_cg_enabled: false, nsfw_memory_enabled: true,
  });
});
