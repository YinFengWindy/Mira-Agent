import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { act, useState } from "react";
import { changeInputValue, mountTestComponent } from "../shared/testing/domTestHarness";
import type { RoleKnowledgeEntry } from "../shared/types";
import { RoleKnowledgeEntryOptions } from "./RoleKnowledgeEntryOptions";

describe("RoleKnowledgeEntryOptions", () => {
  it("updates disabled, constant, case-sensitive, priority and insertion settings in the parent draft", async () => {
    let current: RoleKnowledgeEntry = { id: "rain", content: "rain", enabled: false };
    function Editor() {
      const [entry, setEntry] = useState(current);
      current = entry;
      return <RoleKnowledgeEntryOptions entry={entry} onUpdate={setEntry} />;
    }
    const view = await mountTestComponent(<Editor />);
    try {
      for (const label of ["启用条目", "常驻", "区分大小写"]) {
        const toggle = view.container.querySelector<HTMLButtonElement>(`[aria-label="${label}"]`);
        assert.ok(toggle);
        await act(async () => toggle.click());
        assert.equal(toggle.getAttribute("aria-checked"), "true");
      }
      const numbers = view.container.querySelectorAll<HTMLInputElement>('input[type="number"]');
      await changeInputValue(numbers[0], "12");
      await changeInputValue(numbers[1], "3");
      assert.deepEqual(current, { id: "rain", content: "rain", enabled: true, always_active: true, case_sensitive: true, priority: 12, insertion_order: 3 });
    } finally {
      await view.cleanup();
    }
  });
});
