import { ImageFormPanel } from "./ImageFormPanel";
import type { ImageStudioFormState } from "./types";
import { PromptLibraryIcon } from "../../../apps/desktop/renderer/src/shared/icons";
import { cx, secondarySidebarSurfaceClass, sidebarNavItemClass } from "../../../apps/desktop/renderer/src/shared/styles";

type ImageStudioSidebarProps = {
  bridgeReady: boolean;
  form: ImageStudioFormState;
  nsfwEnabled: boolean;
  addQualityTags: boolean;
  undesiredContentPreset: number;
  roleItems: Array<{ id: string; label: string; avatarAbs: string | null }>;
  submitting: boolean;
  validationError: string;
  onOpenPromptTagLibrary: () => void;
  onChange: (next: Partial<ImageStudioFormState>) => void;
  onPickBaseImage: () => void;
  onSubmit: () => void;
  onToggleNsfwEnabled: () => void;
  onToggleAddQualityTags: () => void;
  onChangeUndesiredContentPreset: (value: number) => void;
};

/** Renders the image studio workspace sidebar with generation parameters. */
export function ImageStudioSidebar({
  bridgeReady,
  form,
  nsfwEnabled,
  addQualityTags,
  undesiredContentPreset,
  roleItems,
  submitting,
  validationError,
  onOpenPromptTagLibrary,
  onChange,
  onPickBaseImage,
  onSubmit,
  onToggleNsfwEnabled,
  onToggleAddQualityTags,
  onChangeUndesiredContentPreset,
}: ImageStudioSidebarProps) {
  const promptLibraryClass = cx(
    sidebarNavItemClass,
    "mb-3 flex h-9 items-center gap-2 px-2 text-left text-sm text-ink-muted",
  );

  return (
    <aside
      className={cx(
        "image-studio-sidebar grid h-full min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)] py-3 pl-[10px] pr-[6px]",
        secondarySidebarSurfaceClass,
      )}
    >
      <button
        data-testid="open-prompt-tag-library-button"
        className={promptLibraryClass}
        type="button"
        onClick={onOpenPromptTagLibrary}
      >
        <PromptLibraryIcon className="h-4 w-4 fill-current" />
        <span>提示词库</span>
      </button>
      <div className="scrollbar-soft min-h-0 min-w-0 overflow-x-hidden overflow-y-auto px-2 pb-1">
        <ImageFormPanel
          bridgeReady={bridgeReady}
          form={form}
          nsfwEnabled={nsfwEnabled}
          addQualityTags={addQualityTags}
          undesiredContentPreset={undesiredContentPreset}
          roleItems={roleItems}
          validationError={validationError}
          submitting={submitting}
          onChange={onChange}
          onPickBaseImage={onPickBaseImage}
          onSubmit={onSubmit}
          onToggleNsfwEnabled={onToggleNsfwEnabled}
          onToggleAddQualityTags={onToggleAddQualityTags}
          onChangeUndesiredContentPreset={onChangeUndesiredContentPreset}
        />
      </div>
    </aside>
  );
}
