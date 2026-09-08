import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { completeOnboarding, readOnboardingProgress, reconcileOnboarding } from "./onboardingState";

describe("onboarding progress", () => {
  it("enrolls only an empty installation and resumes using actual prerequisites", () => {
    const first = reconcileOnboarding(null, false, false);
    assert.equal(first.completed, false);
    assert.equal(first.step, "model");
    const restored = readOnboardingProgress({ getItem: () => JSON.stringify(first) });
    assert.equal(reconcileOnboarding(restored, true, false).step, "role");
    const ready = reconcileOnboarding(restored, true, true);
    assert.equal(ready.step, "workspace");
    assert.equal(ready.completed, false);
    assert.equal(reconcileOnboarding(ready, false, true).step, "model");
  });
  it("does not interrupt existing installations with either prerequisite", () => {
    for (const [model, role] of [[true, false], [false, true], [true, true]]) {
      assert.equal(reconcileOnboarding(null, model, role).completed, true);
    }
  });
  it("keeps completion after deleting resources and retains history on a new tutorial version", () => {
    const done = completeOnboarding(reconcileOnboarding(null, false, false));
    assert.equal(reconcileOnboarding(done, false, false).completed, true);
    const next = reconcileOnboarding(done, true, true, 2);
    assert.equal(next.completed, false);
    assert.deepEqual(next.completedVersions, [1]);
    assert.deepEqual(completeOnboarding(next).completedVersions, [1, 2]);
  });
  it("rejects corrupt local progress instead of reporting completion", () => {
    assert.throws(() => readOnboardingProgress({ getItem: () => '{"completed":true}' }), /状态无效/);
  });
});
