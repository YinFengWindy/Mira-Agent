import assert from "node:assert/strict";
import { test } from "node:test";
import { BackgroundEffectScope } from "./backgroundEffectScope";

test("disposes event effects before generic effects, even when the effect was registered first", () => {
  const order: string[] = [];
  const scope = new BackgroundEffectScope();
  // Registration order is deliberately the *safe* order (effect, then event) —
  // the opposite of the #227 shape below — to prove the phase split isn't
  // just coincidentally matching LIFO here.
  scope.addEffect("terminate", () => { order.push("terminate"); });
  scope.addEventEffect("unsubscribe", () => { order.push("unsubscribe"); });

  return scope.disposeAll().then(() => {
    assert.deepEqual(order, ["unsubscribe", "terminate"]);
  });
});

test("#227 shape: subscribe-then-terminate registration order still disposes unsubscribe first", async () => {
  // This is exactly the order that broke scene_awareness and novelai on the
  // backend: ctx.events.on(...) called first, ctx.effect("...terminate", ...)
  // registered after. A plain LIFO scope would run terminate() first here.
  const order: string[] = [];
  const scope = new BackgroundEffectScope();
  scope.addEventEffect("event:one", () => { order.push("unsubscribe:one"); });
  scope.addEventEffect("event:two", () => { order.push("unsubscribe:two"); });
  scope.addEffect("controller_terminate", () => { order.push("terminate"); });

  const errors = await scope.disposeAll();

  assert.deepEqual(errors, []);
  assert.equal(order.indexOf("terminate"), order.length - 1, "terminate must run last");
  assert.ok(order.indexOf("unsubscribe:one") < order.indexOf("terminate"));
  assert.ok(order.indexOf("unsubscribe:two") < order.indexOf("terminate"));
});

test("within a phase, disposal is LIFO", async () => {
  const order: string[] = [];
  const scope = new BackgroundEffectScope();
  scope.addEffect("first", () => { order.push("first"); });
  scope.addEffect("second", () => { order.push("second"); });

  await scope.disposeAll();

  assert.deepEqual(order, ["second", "first"]);
});

test("a throwing dispose does not block the remaining effects and its error is collected", async () => {
  const order: string[] = [];
  const scope = new BackgroundEffectScope();
  scope.addEffect("ok-1", () => { order.push("ok-1"); });
  scope.addEffect("boom", () => { throw new Error("boom"); });
  scope.addEventEffect("ok-2", () => { order.push("ok-2"); });

  const realWarn = console.warn;
  const warnings: unknown[][] = [];
  console.warn = (...args: unknown[]) => { warnings.push(args); };
  try {
    const errors = await scope.disposeAll();
    assert.equal(errors.length, 1);
    assert.equal(errors[0]?.message, "boom");
    assert.deepEqual(order, ["ok-2", "ok-1"]);
    assert.equal(warnings.length, 1);
  } finally {
    console.warn = realWarn;
  }
});

test("registering after disposeAll throws instead of silently leaking", async () => {
  const scope = new BackgroundEffectScope();
  await scope.disposeAll();
  assert.throws(() => scope.addEffect("late", () => {}), /已处置/);
  assert.throws(() => scope.addEventEffect("late-event", () => {}), /已处置/);
});
