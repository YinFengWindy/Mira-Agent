import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { FeedbackChip } from "./FeedbackChip";

describe("FeedbackChip", () => {
  it("renders the message with success styling in the primary (default) slot", () => {
    const markup = renderToStaticMarkup(<FeedbackChip tone="success" message="角色保存成功。" />);
    assert.match(markup, /角色保存成功。/);
    assert.match(markup, /top-4/);
    assert.match(markup, /bg-success-soft/);
  });

  it("renders error styling one row lower in the secondary slot, so it cannot land on top of a primary-slot chip", () => {
    const markup = renderToStaticMarkup(
      <FeedbackChip tone="error" message="请先创建至少一个角色，再进入生图。" slot="secondary" />,
    );
    assert.match(markup, /请先创建至少一个角色，再进入生图。/);
    assert.match(markup, /top-16/);
    assert.doesNotMatch(markup, /\btop-4\b/);
    assert.match(markup, /bg-danger-soft/);
  });
});
