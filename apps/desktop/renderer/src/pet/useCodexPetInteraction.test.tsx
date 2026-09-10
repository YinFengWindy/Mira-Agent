import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { act } from "react";
import { mountTestComponent } from "../shared/testing/domTestHarness";
import { useCodexPetInteraction } from "./useCodexPetInteraction";

type BridgeCall = { name: string; args: unknown[] };

/** Records every bridge call so tests can assert on the exact main-process commands. */
function fakeBridge(calls: BridgeCall[]) {
  const record = (name: string) => (...args: unknown[]) => { calls.push({ name, args }); };
  return {
    beginPetDrag: record("beginPetDrag"),
    movePet: record("movePet"),
    endPetDrag: record("endPetDrag"),
    openPetRole: record("openPetRole"),
    startVoicePress: record("startVoicePress"),
    voicePointerMoved: record("voicePointerMoved"),
    voiceRelease: record("voiceRelease"),
    voiceCancel: record("voiceCancel"),
  } as unknown as Parameters<typeof useCodexPetInteraction>[0];
}

async function mountPet() {
  const calls: BridgeCall[] = [];
  const bridge = fakeBridge(calls);
  let hook!: ReturnType<typeof useCodexPetInteraction>;

  function Harness() {
    hook = useCodexPetInteraction(bridge);
    return <div data-pet="true" {...hook.pointerHandlers} />;
  }

  const view = await mountTestComponent(<Harness />);
  const element = view.container.querySelector("[data-pet]");
  assert.ok(element, "pet element should be rendered");
  // happy-dom 不实现指针捕获，这里补一个最小实现，让 hook 的捕获/释放分支能真实跑到
  const captured = new Set<number>();
  Object.assign(element, {
    setPointerCapture: (pointerId: number) => { captured.add(pointerId); },
    hasPointerCapture: (pointerId: number) => captured.has(pointerId),
    releasePointerCapture: (pointerId: number) => { captured.delete(pointerId); },
  });

  async function pointer(type: string, init: Record<string, unknown> = {}) {
    await act(async () => {
      element!.dispatchEvent(
        new PointerEvent(type, { bubbles: true, pointerId: 1, button: 0, ...init }),
      );
    });
  }

  async function doubleClick() {
    await act(async () => {
      element!.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
    });
  }

  function callNames() {
    return calls.map((call) => call.name);
  }

  return {
    ...view,
    calls,
    callNames,
    capturedPointers: captured,
    pointer,
    doubleClick,
    get state() { return hook.interactionState; },
    get isDragging() { return hook.isDragging; },
  };
}

describe("codex pet interaction", () => {
  it("captures the pointer and starts a drag on primary press", async () => {
    const pet = await mountPet();
    try {
      await pet.pointer("pointerdown", { screenX: 100, screenY: 200 });

      assert.equal(pet.isDragging, true);
      assert.deepEqual(pet.callNames(), ["startVoicePress", "beginPetDrag"]);
      assert.equal(pet.capturedPointers.has(1), true);
    } finally {
      await pet.cleanup();
    }
  });

  it("ignores non-primary buttons", async () => {
    const pet = await mountPet();
    try {
      await pet.pointer("pointerdown", { button: 2, screenX: 100, screenY: 200 });

      assert.equal(pet.isDragging, false);
      assert.deepEqual(pet.callNames(), []);
    } finally {
      await pet.cleanup();
    }
  });

  it("moves the pet and faces the drag direction once past the slop threshold", async () => {
    const pet = await mountPet();
    try {
      await pet.pointer("pointerdown", { screenX: 100, screenY: 200 });
      await pet.pointer("pointermove", { screenX: 101, screenY: 200 });

      assert.equal(pet.state, null, "a sub-threshold move must not move the pet");
      assert.deepEqual(pet.callNames(), ["startVoicePress", "beginPetDrag"]);

      await pet.pointer("pointermove", { screenX: 140, screenY: 200 });
      assert.equal(pet.state, "running-right");

      await pet.pointer("pointermove", { screenX: 60, screenY: 200 });
      assert.equal(pet.state, "running-left");
      assert.deepEqual(pet.callNames().slice(2), [
        "voicePointerMoved", "movePet", "voicePointerMoved", "movePet",
      ]);
    } finally {
      await pet.cleanup();
    }
  });

  it("releases the drag and the pointer capture on pointer up", async () => {
    const pet = await mountPet();
    try {
      await pet.pointer("pointerdown", { screenX: 100, screenY: 200 });
      await pet.pointer("pointermove", { screenX: 160, screenY: 200 });
      await pet.pointer("pointerup", { screenX: 160, screenY: 200 });

      assert.equal(pet.isDragging, false);
      assert.equal(pet.state, "jumping");
      assert.deepEqual(pet.callNames().slice(-2), ["endPetDrag", "voiceRelease"]);
      assert.equal(pet.capturedPointers.has(1), false);
    } finally {
      await pet.cleanup();
    }
  });

  it("cancels the voice press without an end position when the pointer is cancelled", async () => {
    const pet = await mountPet();
    try {
      await pet.pointer("pointerdown", { screenX: 100, screenY: 200 });
      await pet.pointer("pointercancel", { screenX: 100, screenY: 200 });

      assert.equal(pet.isDragging, false);
      assert.equal(pet.state, null);
      const endDrag = pet.calls.find((call) => call.name === "endPetDrag");
      assert.deepEqual(endDrag?.args, []);
      assert.deepEqual(pet.callNames().slice(-1), ["voiceCancel"]);
    } finally {
      await pet.cleanup();
    }
  });

  it("opens the main window when a double click follows a click that never moved", async () => {
    const pet = await mountPet();
    try {
      await pet.pointer("pointerdown", { screenX: 100, screenY: 200 });
      await pet.pointer("pointerup", { screenX: 100, screenY: 200 });
      await pet.doubleClick();

      assert.equal(pet.callNames().includes("openPetRole"), true);
    } finally {
      await pet.cleanup();
    }
  });

  it("does not open the main window when the gesture before the double click was a drag", async () => {
    const pet = await mountPet();
    try {
      await pet.pointer("pointerdown", { screenX: 100, screenY: 200 });
      await pet.pointer("pointermove", { screenX: 400, screenY: 200 });
      await pet.pointer("pointerup", { screenX: 400, screenY: 200 });
      await pet.doubleClick();

      assert.equal(pet.callNames().includes("openPetRole"), false);
    } finally {
      await pet.cleanup();
    }
  });

  it("shows the hover state only while no drag is in flight", async () => {
    const pet = await mountPet();
    try {
      // React 把 enter/leave 从 over/out 派生出来，所以这里派发的是原生事件
      await pet.pointer("pointerover", { relatedTarget: null });
      assert.equal(pet.state, "jumping");

      await pet.pointer("pointerout", { relatedTarget: null });
      assert.equal(pet.state, null);

      await pet.pointer("pointerdown", { screenX: 100, screenY: 200 });
      await pet.pointer("pointerover", { relatedTarget: null });
      assert.equal(pet.state, null, "hover must not override an in-flight drag");
    } finally {
      await pet.cleanup();
    }
  });
});
