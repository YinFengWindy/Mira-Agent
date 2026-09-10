import assert from "node:assert/strict";
import { test } from "node:test";
import { noSurfaceExtension } from "./contract.js";
import {
  clampSurfaceAnchor,
  surfaceAnchorFromCursor,
  surfaceAnchorFromWindowBounds,
  surfaceBodyOffset,
  surfaceWindowBounds,
} from "./geometry.js";

const body = { width: 192, height: 208 };
const workArea = { x: 0, y: 0, width: 1920, height: 1040 };

test("clamps a surface body inside the work area on both axes", () => {
  assert.deepEqual(clampSurfaceAnchor({ x: -50, y: -50 }, body, workArea), { x: 0, y: 0 });
  assert.deepEqual(clampSurfaceAnchor({ x: 5000, y: 5000 }, body, workArea), {
    x: 1920 - body.width,
    y: 1040 - body.height,
  });
  assert.deepEqual(clampSurfaceAnchor({ x: 300, y: 400 }, body, workArea), { x: 300, y: 400 });
});

test("clamps against a work area offset by another display's origin", () => {
  const secondary = { x: 1920, y: -200, width: 1280, height: 720 };
  assert.deepEqual(clampSurfaceAnchor({ x: -9_999, y: -9_999 }, body, secondary), { x: 1920, y: -200 });
  // A negative origin is a real layout (a display placed above the primary one),
  // so coordinates that look out of bounds against a 0-based work area must be
  // left alone here.
  assert.deepEqual(clampSurfaceAnchor({ x: 2_000, y: -100 }, body, secondary), { x: 2_000, y: -100 });
  assert.deepEqual(clampSurfaceAnchor({ x: 99_999, y: 99_999 }, body, secondary), {
    x: 1920 + 1280 - body.width,
    y: -200 + 720 - body.height,
  });
});

test("a body larger than the work area falls back to the work-area origin", () => {
  // A naive two-sided clamp yields origin + available - size here, which is
  // *outside* the work area on the near edge: the surface's top-left corner
  // would be unreachable and, with a title-less transparent window, unmovable.
  const tiny = { x: 100, y: 100, width: 100, height: 100 };
  assert.deepEqual(clampSurfaceAnchor({ x: 150, y: 150 }, body, tiny), { x: 100, y: 100 });
});

test("an extension below only grows the window height", () => {
  const bounds = surfaceWindowBounds({ x: 300, y: 400 }, body, { side: "below", size: 60 });
  assert.deepEqual(bounds, { x: 300, y: 400, width: 192, height: 268 });
  assert.deepEqual(surfaceBodyOffset({ side: "below", size: 60 }), { x: 0, y: 0 });
});

test("an extension above moves the window origin up so the body stays put", () => {
  const extension = { side: "above", size: 60 } as const;
  const bounds = surfaceWindowBounds({ x: 300, y: 400 }, body, extension);
  assert.deepEqual(bounds, { x: 300, y: 340, width: 192, height: 268 });
  // The renderer draws its body at this window-local offset, so the pixels the
  // user sees do not move when the panel opens.
  assert.deepEqual(surfaceBodyOffset(extension), { x: 0, y: 60 });
  assert.deepEqual(surfaceAnchorFromWindowBounds(bounds, extension), { x: 300, y: 400 });
});

test("window bounds round-trip back to the anchor for both sides", () => {
  for (const extension of [
    noSurfaceExtension,
    { side: "below", size: 41 } as const,
    { side: "above", size: 41 } as const,
  ]) {
    const anchor = { x: 123, y: 456 };
    const bounds = surfaceWindowBounds(anchor, body, extension);
    assert.deepEqual(surfaceAnchorFromWindowBounds(bounds, extension), anchor);
  }
});

test("fractional and negative extension sizes never reach the window bounds", () => {
  assert.equal(surfaceWindowBounds({ x: 0, y: 0 }, body, { side: "below", size: 12.3 }).height, body.height + 13);
  assert.equal(surfaceWindowBounds({ x: 0, y: 0 }, body, { side: "below", size: -5 }).height, body.height);
  assert.equal(
    surfaceWindowBounds({ x: 0, y: 0 }, body, { side: "above", size: Number.NaN }).y,
    0,
    "a NaN measurement must not produce NaN window bounds",
  );
});

test("a drag anchor keeps the pointer's grab offset inside the body", () => {
  assert.deepEqual(surfaceAnchorFromCursor({ x: 500, y: 600 }, { x: 96, y: 104 }), { x: 404, y: 496 });
});
