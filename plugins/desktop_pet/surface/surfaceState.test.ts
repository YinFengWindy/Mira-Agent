import assert from "node:assert/strict";
import test from "node:test";
import {
  petSurfaceLoadSignature,
  readPetSurfaceMessage,
  readPetSurfaceState,
} from "./surfaceState";

const load = { package: { spritesheetUrl: "mira-asset://pet" }, state: "idle" };

test("a retained payload carries the package, the sprite state and the observation", () => {
  assert.deepEqual(
    readPetSurfaceState({
      load,
      observation: { status: "observing", enabled: true, bubble: "继续写吧", persistent: false },
    }),
    {
      load: { package: { spritesheetUrl: "mira-asset://pet" }, state: "idle" },
      observation: { status: "observing", enabled: true, bubble: "继续写吧", persistent: false },
    },
  );
});

test("a payload without an observation is still usable", () => {
  const parsed = readPetSurfaceState({ load });
  assert.equal(parsed?.observation, null);
  assert.equal(parsed?.load.state, "idle");
});

test("a payload with no recognizable sprite state is rejected outright", () => {
  assert.equal(readPetSurfaceState({ load: { ...load, state: "dancing" } }), null);
  assert.equal(readPetSurfaceState({ load: { package: {}, state: "idle" } }), null);
  assert.equal(readPetSurfaceState({ load: null }), null);
  assert.equal(readPetSurfaceState(null), null);
  assert.equal(readPetSurfaceState("idle"), null);
});

test("a malformed observation degrades to none rather than rejecting the package", () => {
  const parsed = readPetSurfaceState({ load, observation: { status: "nonsense", enabled: true } });
  assert.equal(parsed?.observation, null);
  assert.equal(parsed?.load.package.spritesheetUrl, "mira-asset://pet");
});

test("a bubble that is not a string becomes empty instead of rendering as an object", () => {
  const parsed = readPetSurfaceState({
    load,
    observation: { status: "failed", enabled: true, bubble: { toString: 1 }, persistent: "yes" },
  });
  assert.deepEqual(parsed?.observation, {
    status: "failed",
    enabled: true,
    bubble: "",
    persistent: false,
  });
});

test("a transient play request is distinguished from a base state change", () => {
  assert.deepEqual(readPetSurfaceMessage({ state: "waving", transient: true }), {
    state: "waving",
    transient: true,
  });
  assert.deepEqual(readPetSurfaceMessage({ state: "waving" }), {
    state: "waving",
    transient: false,
  });
  assert.equal(readPetSurfaceMessage({ state: "dancing" }), null);
  assert.equal(readPetSurfaceMessage(undefined), null);
});

test("the load signature changes with the package and with the sprite state", () => {
  assert.equal(
    petSurfaceLoadSignature({ package: { spritesheetUrl: "a" }, state: "idle" }),
    petSurfaceLoadSignature({ package: { spritesheetUrl: "a" }, state: "idle" }),
  );
  assert.notEqual(
    petSurfaceLoadSignature({ package: { spritesheetUrl: "a" }, state: "idle" }),
    petSurfaceLoadSignature({ package: { spritesheetUrl: "b" }, state: "idle" }),
  );
  assert.notEqual(
    petSurfaceLoadSignature({ package: { spritesheetUrl: "a" }, state: "idle" }),
    petSurfaceLoadSignature({ package: { spritesheetUrl: "a" }, state: "waiting" }),
  );
});
