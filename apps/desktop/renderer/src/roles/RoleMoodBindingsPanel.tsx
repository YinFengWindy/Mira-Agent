import { useEffect, useState } from "react";
import { inputClass } from "../shared/styles";

type RoleMoodBindingsPanelProps = {
  selectedAssetPath: string;
  selectedAssetAbsPath: string;
  selectedMood: string;
  onSaveMoodBinding: (nextMood: string) => void;
  onClearSelectedAsset: () => void;
};

/** Renders the role asset-side mood binding panel. */
export function RoleMoodBindingsPanel({
  selectedAssetPath,
  selectedAssetAbsPath,
  selectedMood,
  onSaveMoodBinding,
  onClearSelectedAsset,
}: RoleMoodBindingsPanelProps) {
  const [draftMood, setDraftMood] = useState(selectedMood);

  useEffect(() => {
    setDraftMood(selectedMood);
  }, [selectedMood]);

  function handleMoodBlur(): void {
    const normalizedDraft = draftMood.trim();
    if (normalizedDraft === selectedMood.trim()) {
      return;
    }
    onSaveMoodBinding(normalizedDraft);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="grid min-h-[360px] flex-1 gap-4 rounded-xl bg-white p-5">
        <div className="relative grid min-h-[260px] place-items-center overflow-hidden rounded-lg bg-surface-soft">
          {selectedAssetPath ? (
            <>
              <button
                className="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-full border border-line-soft bg-white/92 text-ink-secondary transition hover:border-line-strong hover:bg-white hover:text-ink focus:outline-none"
                type="button"
                onClick={onClearSelectedAsset}
                aria-label="取消选中差分图"
              >
                ×
              </button>
              <img
                className="max-h-full max-w-full object-contain"
                src={selectedAssetAbsPath}
                alt={`${selectedMood || "差分"} preview`}
              />
            </>
          ) : (
            <div className="px-6 text-center text-sm text-ink-muted">请先在左侧选中一张差分立绘</div>
          )}
        </div>
        <label className="grid w-[240px] gap-1.5 text-xs text-ink-secondary">
          <span>对应差分</span>
          <input
            className={`${inputClass} h-10 px-3 py-2 border-line-soft bg-white text-ink placeholder:text-ink-faint`}
            value={draftMood}
            onChange={(event) => setDraftMood(event.target.value.trimStart())}
            onBlur={handleMoodBlur}
            placeholder="例如：平静"
            disabled={!selectedAssetPath}
          />
        </label>
      </div>
    </div>
  );
}
