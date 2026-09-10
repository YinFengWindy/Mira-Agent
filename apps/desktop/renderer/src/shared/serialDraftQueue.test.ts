import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { setImmediate } from "node:timers/promises";
import { SerialDraftQueue } from "./serialDraftQueue.js";

describe("SerialDraftQueue", () => {
  it("coalesces edits made while a submission is in flight", async () => {
    let release!: (value: { ok: true; result: string }) => void;
    const calls: string[] = [];
    const queue = new SerialDraftQueue<string, string>({
      isEqual: (a, b) => a === b,
      clone: (draft) => draft,
      attempt: async (draft) => {
        calls.push(draft);
        return new Promise((resolve) => { release = resolve; });
      },
      onApplied: () => undefined,
      onStatus: () => undefined,
    });

    queue.enqueue("first");
    queue.enqueue("obsolete");
    queue.enqueue("second");
    release({ ok: true, result: "first" });
    await setImmediate();

    assert.deepEqual(calls, ["first", "second"]);
  });

  it("keeps a failure that does not resume automatically paused until an explicit retry", async () => {
    const attempts: string[] = [];
    const statuses: string[] = [];
    const queue = new SerialDraftQueue<string, string>({
      isEqual: (a, b) => a === b,
      clone: (draft) => draft,
      attempt: async (draft) => {
        attempts.push(draft);
        return { ok: false, resumesAutomatically: false, message: "boom" };
      },
      onApplied: () => assert.fail("should not apply a failed attempt"),
      onStatus: (phase) => statuses.push(phase),
    });

    queue.enqueue("first");
    await setImmediate();
    queue.enqueue("second");
    await setImmediate();
    assert.deepEqual(attempts, ["first"]);

    queue.retry();
    await setImmediate();
    assert.deepEqual(attempts, ["first", "first"]);
    assert.deepEqual(statuses, ["saving", "error", "saving", "error"]);
  });

  it("keeps trying new edits after a failure that resumes automatically, without an explicit retry", async () => {
    const attempts: string[] = [];
    const queue = new SerialDraftQueue<string, string>({
      isEqual: (a, b) => a === b,
      clone: (draft) => draft,
      attempt: async (draft) => {
        attempts.push(draft);
        return draft === "invalid"
          ? { ok: false, resumesAutomatically: true, message: "invalid" }
          : { ok: true, result: draft };
      },
      onApplied: () => undefined,
      onStatus: () => undefined,
    });

    queue.enqueue("invalid");
    await setImmediate();
    queue.enqueue("corrected");
    await setImmediate();

    assert.deepEqual(attempts, ["invalid", "corrected"]);
  });

  it("reuses the same operation id when retrying the identical failed draft", async () => {
    const operationIds: string[] = [];
    let shouldFail = true;
    const queue = new SerialDraftQueue<string, string>({
      isEqual: (a, b) => a === b,
      clone: (draft) => draft,
      attempt: async (draft, operationId) => {
        operationIds.push(operationId);
        if (shouldFail) return { ok: false, resumesAutomatically: false, message: "boom" };
        return { ok: true, result: draft };
      },
      onApplied: () => undefined,
      onStatus: () => undefined,
    });

    queue.enqueue("first");
    await setImmediate();
    shouldFail = false;
    queue.retry();
    await setImmediate();

    assert.equal(operationIds.length, 2);
    assert.equal(operationIds[0], operationIds[1]);
  });
});
