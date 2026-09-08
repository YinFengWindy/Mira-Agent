import { toFileUrl } from "../shared/format";
import type { ImageGenerateResult, ImageHistoryRecord } from "./types";

type ImagePreviewPanelProps = {
  activeRecord: ImageHistoryRecord | null;
  generating: boolean;
  latestResult: ImageGenerateResult | null;
  error: string;
};

export function ImagePreviewPanel({
  activeRecord,
  generating,
  latestResult,
  error,
}: ImagePreviewPanelProps) {
  const previewPath = activeRecord?.output_paths[0] ?? latestResult?.output_paths[0] ?? "";

  return (
    <section className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)_auto] gap-3">
      <div className="min-h-0 min-w-0 overflow-hidden bg-white">
        {previewPath ? (
          <div className="grid h-full min-h-[420px] w-full min-w-0 place-items-center overflow-hidden">
            <img
              className="block h-full w-full min-h-0 min-w-0 object-contain"
              src={toFileUrl(previewPath)}
              alt="generated result"
            />
          </div>
        ) : generating ? (
          <div className="grid h-full min-h-[420px] place-items-center text-sm text-ink-muted">生成中...</div>
        ) : (
          <div className="grid h-full min-h-[420px] place-items-center text-sm text-ink-muted">等待生成</div>
        )}
      </div>

      <div className="grid gap-3">
        {error ? (
          <div className="rounded-md border border-[var(--danger-300)] bg-danger-soft px-3 py-2 text-[12px] leading-5 text-danger-text">
            {error}
          </div>
        ) : null}
      </div>
    </section>
  );
}
