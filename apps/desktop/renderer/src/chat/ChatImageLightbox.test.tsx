/// <reference types="node" />

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { ChatImageLightbox } from "./ChatImageLightbox";

function renderLightbox(withPluginAction: boolean): string {
  return renderToStaticMarkup(
    <ChatImageLightbox
      canAddToAssetLibrary
      canGoToNext={false}
      canGoToPrevious={false}
      canLocateMessage
      imagePath="D:\\images\\scene.png"
      addingToAssetLibrary={false}
      pluginActions={withPluginAction ? <button aria-label="插件图片操作" /> : null}
      open
      onAddToAssetLibrary={() => undefined}
      onClose={() => undefined}
      onGoToNext={() => undefined}
      onGoToPrevious={() => undefined}
      onLocateMessage={() => undefined}
    />,
  );
}

describe("ChatImageLightbox", () => {
  it("renders a plugin-owned image action when contributed", () => {
    assert.match(renderLightbox(true), /aria-label="插件图片操作"/);
  });
  it("has no generation control when no plugin contributes one", () => {
    assert.doesNotMatch(renderLightbox(false), /插件图片操作|重新生成图片/);
    assert.match(renderLightbox(false), /定位到对应消息/);
  });
});
