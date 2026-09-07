import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { RoleKnowledgeEntryRow } from "./RoleKnowledgeEntryRow";

describe("RoleKnowledgeEntryRow", () => {
  it("exposes title, keywords, and content fields without an empty-keyword label", () => {
    const markup = renderToStaticMarkup(
      <RoleKnowledgeEntryRow
        entry={{ id: "entry-1", title: "雨天", content: "她喜欢听雨。", primary_keys: [] }}
        index={0}
        expanded
        onToggle={() => undefined}
        onUpdate={() => undefined}
        onRemove={() => undefined}
      />,
    );

    assert.match(markup, />标题</);
    assert.match(markup, />关键词</);
    assert.match(markup, />内容</);
    assert.doesNotMatch(markup, /未设置关键词/);
  });
});
