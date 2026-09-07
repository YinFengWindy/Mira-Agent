import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { act, useState } from "react";
import { changeInputValue, mountTestComponent } from "../shared/testing/domTestHarness";
import { RoleKeywordInput } from "./RoleKeywordInput";

describe("RoleKeywordInput", () => {
  it("keeps a trailing comma while typing and exposes current keywords before blur or save", async () => {
    let saved: string[] = [];
    function Editor() {
      const [keywords, setKeywords] = useState(["rain"]);
      return <>
        <RoleKeywordInput label="关键词" keywords={keywords} onChange={setKeywords} />
        <button disabled={keywords.join() === "rain"} onClick={() => { saved = keywords; }}>保存</button>
      </>;
    }
    const view = await mountTestComponent(<Editor />);
    try {
      const input = view.container.querySelector("input");
      const save = view.container.querySelector("button");
      assert.ok(input && save);
      for (const character of ",snow") {
        await changeInputValue(input, input.value + character);
      }
      assert.equal(input.value, "rain,snow");
      assert.equal(save.disabled, false);
      await act(async () => save.click());
      assert.deepEqual(saved, ["rain", "snow"]);
      await act(async () => input.dispatchEvent(new FocusEvent("focusout", { bubbles: true })));
      assert.equal(input.value, "rain, snow");
    } finally {
      await view.cleanup();
    }
  });

  it("normalizes on Enter and resets to externally replaced keyword values", async () => {
    function Editor({ initial }: { initial: string[] }) {
      const [keywords, setKeywords] = useState(initial);
      return <RoleKeywordInput label="次关键词" keywords={keywords} onChange={setKeywords} />;
    }
    const view = await mountTestComponent(<Editor initial={["rain"]} />);
    try {
      const input = view.container.querySelector("input");
      assert.ok(input);
      await changeInputValue(input, "rain, night, rain,");
      await act(async () => input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true })));
      assert.equal(input.value, "rain, night");
      await view.render(<RoleKeywordInput label="次关键词" keywords={["sun", "sun"]} onChange={() => undefined} />);
      assert.equal(view.container.querySelector("input")?.value, "sun, sun");
      await view.render(<RoleKeywordInput label="次关键词" keywords={["snow"]} onChange={() => undefined} />);
      assert.equal(view.container.querySelector("input")?.value, "snow");
    } finally {
      await view.cleanup();
    }
  });
});
