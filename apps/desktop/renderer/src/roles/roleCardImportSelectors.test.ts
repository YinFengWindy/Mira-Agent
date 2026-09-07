import assert from "node:assert/strict";
import { it } from "node:test";
import { duplicateEmotionAssets, hasUnselectedEmotions } from "./roleCardImportSelectors";

it("requires choices only for decoded duplicate emotions and rejects stale choices", () => {
  const assets = [
    { asset_id: "a", kind: "emotion", name: "neutral", size: 1 },
    { asset_id: "b", kind: "emotion", name: "neutral", size: 1 },
    { asset_id: "c", kind: "emotion", name: "happy", size: 1 },
    { asset_id: "d", kind: "emotion", name: "happy" },
  ];
  assert.deepEqual(duplicateEmotionAssets(assets).map(([name]) => name), ["neutral"]);
  assert.equal(hasUnselectedEmotions(assets, {}), true);
  assert.equal(hasUnselectedEmotions(assets, { neutral: "c" }), true);
  assert.equal(hasUnselectedEmotions(assets, { neutral: "a" }), false);
});
