import assert from "node:assert/strict";
import { test } from "node:test";
import {
  advanceSurfaceMomentum,
  shouldStopSurfaceMomentum,
  surfaceMomentumMaximumDurationMs,
  surfaceMomentumMaximumElapsedMs,
  surfaceMomentumMinimumSpeed,
} from "./momentum.js";

const start = { position: { x: 100, y: 100 }, velocity: { x: 600, y: -300 } };

test("integrates position from velocity and decays the velocity", () => {
  const next = advanceSurfaceMomentum(start, 16);
  assert.ok(Math.abs(next.position.x - (100 + 600 * 0.016)) < 1e-9);
  assert.ok(Math.abs(next.position.y - (100 - 300 * 0.016)) < 1e-9);
  assert.ok(Math.hypot(next.velocity.x, next.velocity.y) < Math.hypot(600, 300));
});

test("a stalled event loop cannot teleport the surface", () => {
  // Without the elapsed cap, a 5s pause would advance the glide by 3000px.
  const stalled = advanceSurfaceMomentum(start, 5000);
  const capped = advanceSurfaceMomentum(start, surfaceMomentumMaximumElapsedMs);
  assert.deepEqual(stalled, capped);
});

test("negative elapsed time never moves the surface backwards", () => {
  const next = advanceSurfaceMomentum(start, -100);
  assert.deepEqual(next.position, start.position);
});

test("settles once speed drops below the perceptible threshold", () => {
  const slow = { position: { x: 0, y: 0 }, velocity: { x: surfaceMomentumMinimumSpeed - 1, y: 0 } };
  assert.equal(shouldStopSurfaceMomentum(slow, 0), true);
  const fast = { position: { x: 0, y: 0 }, velocity: { x: surfaceMomentumMinimumSpeed + 1, y: 0 } };
  assert.equal(shouldStopSurfaceMomentum(fast, 0), false);
});

test("settles at the duration ceiling however fast it is still moving", () => {
  const fast = { position: { x: 0, y: 0 }, velocity: { x: 10_000, y: 10_000 } };
  assert.equal(shouldStopSurfaceMomentum(fast, surfaceMomentumMaximumDurationMs), true);
});

test("a caller may tighten the glide without touching the host defaults", () => {
  const fast = { position: { x: 0, y: 0 }, velocity: { x: 200, y: 0 } };
  assert.equal(shouldStopSurfaceMomentum(fast, 0), false);
  assert.equal(shouldStopSurfaceMomentum(fast, 0, { minimumSpeed: 500 }), true);
  assert.equal(shouldStopSurfaceMomentum(fast, 100, { maximumDurationMs: 50 }), true);
});
