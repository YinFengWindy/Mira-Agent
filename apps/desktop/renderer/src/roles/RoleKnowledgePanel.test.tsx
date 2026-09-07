import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { createEmptyRoleForm } from "../app/appState";
import { RoleKnowledgePanel } from "./RoleKnowledgePanel";

describe("RoleKnowledgePanel", () => {
  it("renders add-entry controls in the shared role draft without an in-panel save action", () => {
    const markup = renderToStaticMarkup(
      <RoleKnowledgePanel
        roleForm={{
          ...createEmptyRoleForm(),
          profile: {
            knowledge_base: { enabled: true, token_budget: 1800, entries: [] },
          },
        }}
        onUpdate={() => undefined}
      />,
    );

    assert.match(markup, /data-testid="role-knowledge-panel"/);
    assert.match(markup, /data-testid="add-knowledge-entry-button"/);
    assert.match(markup, />添加条目</);
    assert.match(markup, /value="1800"/);
    assert.doesNotMatch(markup, />保存</);
    assert.doesNotMatch(markup, /roles\.update/);
  });
});
