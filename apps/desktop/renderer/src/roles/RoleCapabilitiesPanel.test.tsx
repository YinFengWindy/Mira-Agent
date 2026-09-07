import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { createEmptyRoleForm } from "../app/appState";
import { RoleCapabilitiesPanel } from "./RoleCapabilitiesPanel";

describe("RoleCapabilitiesPanel", () => {
  it("renders compact capability rows with state labels instead of a wrapping card", () => {
    const markup = renderToStaticMarkup(<RoleCapabilitiesPanel activeRole={null} bridgeReady roleForm={{ ...createEmptyRoleForm(), nsfwMemoryEnabled: true }} onUpdate={() => undefined} />);

    assert.match(markup, /运行能力/);
    assert.match(markup, /已启用/);
    assert.match(markup, /未配置桌宠/);
    assert.match(markup, /rounded-2xl/);
    assert.match(markup, /sm:grid-cols-2/);
    assert.doesNotMatch(markup, /shadow-\[0_12px_30px/);
  });
});
