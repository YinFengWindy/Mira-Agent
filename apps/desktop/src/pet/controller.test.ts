import assert from "node:assert/strict";
import test from "node:test";
import {
  DesktopPetController,
  desktopPetAgentMoveDurationMs,
  desktopPetSurfaceKey,
} from "./controller.js";
import { desktopPetBody, type DesktopPetSettings } from "./types.js";
import {
  DesktopSurfaceHost,
  surfaceMessageChannel,
  surfacePositionChannel,
  surfaceStateChannel,
  type SurfaceWindowHandle,
} from "../surface/host.js";

/**
 * These tests drive the *real* `DesktopSurfaceHost` over fake window handles
 * rather than a stubbed-out surface host.
 *
 * The controller no longer contains any geometry: clamping, the bubble
 * extension and the release glide all live in the host now, so a fake host
 * would assert only that the controller calls methods — not that the pet ends
 * up where it should. The window handle is the lowest seam that still exercises
 * the arithmetic this ticket moved.
 */

const workArea = { x: 0, y: 0, width: 1920, height: 1080 };

let nextWindowId = 1;

class FakeSurfaceWindow implements SurfaceWindowHandle {
  readonly id = nextWindowId++;
  readonly boundsWrites: { x: number; y: number; width: number; height: number }[] = [];
  readonly messages: { channel: string; payload: unknown }[] = [];
  showCount = 0;
  hideCount = 0;
  private destroyed = false;
  private closedListener: (() => void) | null = null;
  private bounds = { x: 0, y: 0, width: desktopPetBody.width, height: desktopPetBody.height };

  setBounds(bounds: { x: number; y: number; width: number; height: number }): void {
    this.bounds = bounds;
    this.boundsWrites.push(bounds);
  }

  getBounds() {
    return { ...this.bounds };
  }

  isDestroyed(): boolean {
    return this.destroyed;
  }

  destroy(): void {
    this.destroyed = true;
    this.closedListener?.();
  }

  showInactive(): void {
    this.showCount += 1;
  }

  hide(): void {
    this.hideCount += 1;
  }

  setIgnoreMouseEvents(): void {}

  send(channel: string, payload: unknown): void {
    this.messages.push({ channel, payload });
  }

  onClosed(listener: () => void): void {
    this.closedListener = listener;
  }

  /** Payloads sent on one channel, oldest first. */
  payloads(channel: string): unknown[] {
    return this.messages.filter((message) => message.channel === channel).map((message) => message.payload);
  }
}

type Harness = {
  controller: DesktopPetController;
  surfaces: DesktopSurfaceHost;
  windows: FakeSurfaceWindow[];
  window: () => FakeSurfaceWindow;
  settings: () => DesktopPetSettings;
  saveCount: () => number;
  resetSaveCount: () => void;
  setPackageId: (id: string) => void;
  advance: (ms: number) => void;
};

/**
 * Builds a controller wired to a real surface host with an injected clock, so
 * the release glide and the eased agent move run deterministically.
 */
function harness(initialSettings?: Partial<DesktopPetSettings>, actions?: Record<string, "waving">): Harness {
  let settings: DesktopPetSettings = {
    visible: false,
    roleId: null,
    packageId: null,
    positions: {},
    ...initialSettings,
  };
  let saveCount = 0;
  let packageId = "pet-1";
  const windows: FakeSurfaceWindow[] = [];

  let now = 0;
  const timers: { id: number; at: number; callback: () => void }[] = [];
  let nextTimerId = 1;

  const surfaces = new DesktopSurfaceHost({
    createWindow: () => {
      const window = new FakeSurfaceWindow();
      windows.push(window);
      return window;
    },
    workAreaFor: () => workArea,
    displayIdFor: () => "display-1",
    cursorScreenPoint: () => ({ x: 0, y: 0 }),
    now: () => now,
    setTimer: (callback, delayMs) => {
      const id = nextTimerId++;
      timers.push({ id, at: now + delayMs, callback });
      return id as unknown as ReturnType<typeof setTimeout>;
    },
    clearTimer: (handle) => {
      const index = timers.findIndex((timer) => timer.id === (handle as unknown as number));
      if (index >= 0) timers.splice(index, 1);
    },
    onSettled: (key, placement, reason) => {
      if (key.pluginId !== desktopPetSurfaceKey.pluginId) return;
      controller.handleSettled(reason, placement.anchor);
    },
  });

  const controller = new DesktopPetController({
    getSettings: () => settings,
    saveSettings: async (next) => {
      saveCount += 1;
      settings = next;
    },
    resolveBinding: async () => ({
      roleId: "role-1",
      package: { id: packageId, displayName: "Pet", spritesheetUrl: `mira-asset://${packageId}` },
      actions,
    }),
    surfaces,
  });

  return {
    controller,
    surfaces,
    windows,
    window: () => {
      const window = windows.at(-1);
      assert.ok(window, "a surface window should have been created");
      return window;
    },
    settings: () => settings,
    saveCount: () => saveCount,
    resetSaveCount: () => { saveCount = 0; },
    setPackageId: (id) => { packageId = id; },
    advance: (ms) => {
      const target = now + ms;
      for (;;) {
        const due = timers
          .filter((timer) => timer.at <= target)
          .sort((left, right) => left.at - right.at)[0];
        if (!due) break;
        timers.splice(timers.indexOf(due), 1);
        now = due.at;
        due.callback();
      }
      now = target;
    },
  };
}

test("the pet creates its surface and retains the package for a renderer that is not up yet", async () => {
  const pet = harness();

  await pet.controller.show();

  assert.equal(pet.controller.isRunning, true);
  assert.equal(pet.windows.length, 1);
  // Retained rather than fire-and-forget: the surface renderer mounts
  // asynchronously and may reload at any time.
  assert.deepEqual(pet.window().payloads(surfaceStateChannel), [{
    load: {
      package: { id: "pet-1", displayName: "Pet", spritesheetUrl: "mira-asset://pet-1" },
      state: "idle",
    },
    observation: null,
  }]);
});

test("the host replays retained state and reveals the surface when the renderer reports ready", async () => {
  const pet = harness();
  pet.controller.publishObservation({
    status: "paused",
    enabled: true,
    bubble: "屏幕观察已暂停",
    persistent: true,
  });

  await pet.controller.show();
  assert.equal(pet.window().showCount, 0, "an empty transparent window must not be shown");

  pet.surfaces.markReady(desktopPetSurfaceKey);

  assert.equal(pet.window().showCount, 1);
  const replayed = pet.window().payloads(surfaceStateChannel).at(-1) as { observation?: unknown };
  assert.deepEqual(replayed.observation, {
    status: "paused",
    enabled: true,
    bubble: "屏幕观察已暂停",
    persistent: true,
  });
});

test("an observation update resends the package alongside it in one retained payload", async () => {
  const pet = harness();
  await pet.controller.show();

  pet.controller.publishObservation({ status: "observing", enabled: true, bubble: "继续写吧", persistent: false });

  assert.deepEqual(pet.window().payloads(surfaceStateChannel).at(-1), {
    load: {
      package: { id: "pet-1", displayName: "Pet", spritesheetUrl: "mira-asset://pet-1" },
      state: "idle",
    },
    observation: { status: "observing", enabled: true, bubble: "继续写吧", persistent: false },
  });
});

test("the pet restores the position remembered for the display it opened on", async () => {
  const pet = harness({
    visible: true,
    roleId: "role-1",
    packageId: "pet-1",
    positions: { "role-1:display-1": { x: 510, y: 800 } },
  });

  await pet.controller.restore();

  assert.deepEqual(pet.window().boundsWrites.at(-1), {
    x: 510,
    y: 800,
    width: desktopPetBody.width,
    height: desktopPetBody.height,
  });
});

test("a pet with no remembered position lands in the work area's bottom-right corner", async () => {
  const pet = harness();

  await pet.controller.show();

  assert.deepEqual(pet.window().boundsWrites.at(-1), {
    x: workArea.width - desktopPetBody.width,
    y: workArea.height - desktopPetBody.height,
    width: desktopPetBody.width,
    height: desktopPetBody.height,
  });
});

test("a drag persists only the position the surface settled at", async () => {
  const pet = harness();
  await pet.controller.show();
  pet.resetSaveCount();

  // The renderer talks to the host directly; the controller never sees these.
  pet.surfaces.beginDrag(desktopPetSurfaceKey, { x: 72, y: 104 });
  pet.advance(100);
  assert.equal(pet.saveCount(), 0, "following the cursor must not write settings per frame");

  pet.surfaces.setPosition(desktopPetSurfaceKey, { x: 510, y: 460 });
  pet.surfaces.endDrag(desktopPetSurfaceKey);

  assert.equal(pet.saveCount(), 1);
  assert.deepEqual(pet.settings().positions["role-1:display-1"], { x: 510, y: 460 });
});

test("a release glide persists once, after the surface stops moving", async () => {
  const pet = harness();
  await pet.controller.show();
  pet.surfaces.setPosition(desktopPetSurfaceKey, { x: 900, y: 500 });
  pet.resetSaveCount();

  pet.surfaces.endDrag(desktopPetSurfaceKey, { x: -600, y: 0 });
  pet.advance(50);
  assert.equal(pet.saveCount(), 0, "a glide in flight must not write settings per frame");

  pet.advance(2_000);

  assert.equal(pet.saveCount(), 1);
  const persisted = pet.settings().positions["role-1:display-1"];
  assert.ok(persisted.x < 900, "the glide should have carried the pet leftward");
  assert.deepEqual(persisted, { x: pet.window().getBounds().x, y: 500 });
});

test("growing a bubble does not rewrite the persisted position", async () => {
  const pet = harness();
  await pet.controller.show();
  pet.resetSaveCount();

  // What the pet plugin does once it has measured its own bubble.
  pet.surfaces.setExtension(desktopPetSurfaceKey, { side: "above", size: 126 });

  assert.equal(pet.saveCount(), 0);
  // The body stays put; only the window grows upward around it.
  assert.deepEqual(pet.window().boundsWrites.at(-1), {
    x: workArea.width - desktopPetBody.width,
    y: workArea.height - desktopPetBody.height - 126,
    width: desktopPetBody.width,
    height: desktopPetBody.height + 126,
  });
});

test("the surface is attributed to the pet only while it is alive", async () => {
  const pet = harness();
  await pet.controller.show();
  const window = pet.window();

  assert.equal(pet.controller.isPetWindow(window), true);
  assert.equal(pet.controller.isPetWindow({ id: window.id + 1000 }), false);
  assert.equal(pet.controller.isPetWindow(null), false);

  await pet.controller.hide();

  assert.equal(pet.controller.isRunning, false);
  assert.equal(pet.controller.isPetWindow(window), false);
});

test("hiding the pet destroys its surface rather than leaving it invisible", async () => {
  const pet = harness();
  await pet.controller.show();

  await pet.controller.hide();

  assert.equal(pet.window().isDestroyed(), true);
  assert.equal(pet.settings().visible, false);
});

test("changing the package for one role reloads the active pet binding", async () => {
  const pet = harness({ visible: false, roleId: "role-1", packageId: "pet-1" });
  await pet.controller.show();
  pet.setPackageId("pet-2");

  await pet.controller.sync(true);

  const states = pet.window().payloads(surfaceStateChannel) as { load: { package: { id: string } } }[];
  assert.deepEqual(states.map((state) => state.load.package.id), ["pet-1", "pet-2"]);
  // Reusing the surface, not recreating it: the window survives a rebind.
  assert.equal(pet.windows.length, 1);
});

test("a play action is transient, so a reload does not replay a finished animation", async () => {
  const pet = harness(undefined, { greeting: "waving" });
  await pet.controller.show();

  pet.controller.handleAgentAction({
    action_id: "action-1",
    role_id: "role-1",
    session_key: "role:role-1",
    channel: "desktop",
    kind: "play",
    name: "greeting",
  });

  assert.deepEqual(pet.window().payloads(surfaceMessageChannel), [{ state: "waving", transient: true }]);
  const retained = pet.window().payloads(surfaceStateChannel).at(-1) as { load: { state: string } };
  assert.equal(retained.load.state, "idle", "a transient action must not enter the retained state");
});

test("an agent move eases to the target corner and persists only the landing", async () => {
  const pet = harness(undefined, { greeting: "waving" });
  await pet.controller.show();
  pet.surfaces.setPosition(desktopPetSurfaceKey, { x: 0, y: 0 });
  pet.resetSaveCount();

  pet.controller.handleAgentAction({
    action_id: "action-1",
    role_id: "role-1",
    session_key: "role:role-1",
    channel: "desktop",
    kind: "move",
    target: "bottom_right",
    animation: "run",
  });

  assert.deepEqual(pet.window().payloads(surfaceMessageChannel), [{ state: "running-right", transient: true }]);

  pet.advance(desktopPetAgentMoveDurationMs / 2);
  const midway = pet.window().getBounds();
  assert.ok(midway.x > 0 && midway.x < workArea.width - desktopPetBody.width, "the move should be animated, not instant");
  assert.equal(pet.saveCount(), 0, "a tween in flight must not write settings per frame");

  pet.advance(desktopPetAgentMoveDurationMs);

  assert.equal(pet.saveCount(), 1);
  assert.deepEqual(pet.settings().positions["role-1:display-1"], {
    x: workArea.width - desktopPetBody.width,
    y: workArea.height - desktopPetBody.height,
  });
});

test("an agent move to the centre accounts for the pet's own body size", async () => {
  const pet = harness();
  await pet.controller.show();

  pet.controller.handleAgentAction({
    action_id: "action-1",
    role_id: "role-1",
    session_key: "role:role-1",
    channel: "desktop",
    kind: "move",
    target: "center",
  });
  pet.advance(desktopPetAgentMoveDurationMs * 2);

  assert.deepEqual(pet.settings().positions["role-1:display-1"], {
    x: (workArea.width - desktopPetBody.width) / 2,
    y: (workArea.height - desktopPetBody.height) / 2,
  });
});

test("agent actions for another role or a stopped pet are ignored", async () => {
  const pet = harness();
  const action = {
    action_id: "action-1",
    role_id: "role-2",
    session_key: "role:role-2",
    channel: "desktop" as const,
    kind: "move" as const,
    target: "top_left" as const,
  };

  // Not running yet.
  pet.controller.handleAgentAction({ ...action, role_id: "role-1" });
  assert.equal(pet.windows.length, 0);

  await pet.controller.show();
  const writes = pet.window().boundsWrites.length;
  pet.controller.handleAgentAction(action);
  pet.advance(desktopPetAgentMoveDurationMs * 2);

  assert.equal(pet.window().boundsWrites.length, writes, "another role must not move this pet");
});

test("the settled placement is reported to the renderer as well as to the controller", async () => {
  const pet = harness();
  await pet.controller.show();

  const placements = pet.window().payloads(surfacePositionChannel) as {
    anchor: { x: number; y: number };
    bodyOffset: { x: number; y: number };
    workArea: typeof workArea;
  }[];
  assert.equal(placements.length, 1);
  assert.deepEqual(placements[0].workArea, workArea);
  assert.deepEqual(placements[0].bodyOffset, { x: 0, y: 0 });
});
