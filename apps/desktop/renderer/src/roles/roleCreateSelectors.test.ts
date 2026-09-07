import assert from "node:assert/strict";
import { it } from "node:test";
import { createEmptyNewRoleForm } from "../app/appState";
import { selectRoleCreateState } from "./roleCreateSelectors";

it("uses only a decoded avatar preview for a CHARX header and requires an emotion choice", () => {
  const state = selectRoleCreateState(createEmptyNewRoleForm(), {
    status: "ready", source: "card.charx", preview: {
      import_id: "card", assets: [
        { asset_id: "icon", kind: "avatar", preview_abs: "preview.png", size: 12 },
        { asset_id: "a", kind: "emotion", name: "neutral", size: 12 },
        { asset_id: "b", kind: "emotion", name: "neutral", size: 12 },
      ],
    },
  });
  assert.equal(state.previewImagePath, "preview.png");
  assert.equal(state.needsEmotionChoice, true);
});

it("allows resetting a draft containing only reply constraints", () => {
  const form = createEmptyNewRoleForm();
  form.profile = { character: { response_constraints: "Reply briefly" } };
  const state = selectRoleCreateState(form, { status: "idle", preview: null, source: "" });
  assert.equal(state.formDirty, true);
  assert.equal(state.previewImagePath, "");
});
