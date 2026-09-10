import assert from "node:assert/strict";
import { it } from "node:test";
import { act } from "react";
import { mountTestComponent } from "../../../apps/desktop/renderer/src/shared/testing/domTestHarness";
import { chooseSelectOption } from "../../../apps/desktop/renderer/src/shared/testing/selectTestActions";
import type { ImageStudioFormState } from "./types";

it("ImageFormPanel commits a portalled preset without dismissing its parent and keeps size values intact", async () => {
  const view = await mountTestComponent(null);
  const { ImageFormPanel } = await import("./ImageFormPanel");
  const presets: number[] = [];
  const changes: Partial<ImageStudioFormState>[] = [];
  try {
    await view.render(<ImageFormPanel
      bridgeReady form={{ roleId: "", prompt: "portrait", negativePrompt: "", mode: "txt2img", baseImagePath: "", strength: 0.5, noise: 0.1, sizePreset: "square", customWidth: "", customHeight: "", model: "test" }}
      nsfwEnabled={false} addQualityTags undesiredContentPreset={0} roleItems={[]} validationError="" submitting={false}
      onChange={(value) => changes.push(value)} onPickBaseImage={() => undefined} onSubmit={() => undefined}
      onToggleNsfwEnabled={() => undefined} onToggleAddQualityTags={() => undefined} onChangeUndesiredContentPreset={(value) => presets.push(value)}
    />);
    const settings = view.container.querySelector<HTMLButtonElement>('[aria-label="Prompt 设置"]');
    assert.ok(settings);
    await act(async () => settings.click());
    await chooseSelectOption("Undesired Content Preset", "Heavy");
    assert.deepEqual(presets, [2]);
    assert.ok(view.container.querySelector('[aria-label="Undesired Content Preset"]'));
    await chooseSelectOption("尺寸", "自定义");
    assert.deepEqual(changes, [{ sizePreset: "custom" }]);
  } finally { await view.cleanup(); }
});
