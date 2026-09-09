import { ArrowClockwise, ArrowSquareOut } from "@phosphor-icons/react";
import { cx, ghostButtonClass, primaryButtonClass } from "../shared/styles";
import { useDesktopUpdates } from "./useDesktopUpdates";

const releaseUrl = "https://github.com/YinFengWindy/Shiori-Agent/releases/latest";
const statusLabels = {
  unsupported: "开发模式", idle: "尚未检查更新", checking: "正在检查更新…",
  current: "已是最新版本", downloading: "正在下载更新…", downloaded: "更新已就绪",
  installing: "正在重启安装…", error: "更新失败",
};

/** Shows the installed version and the desktop-owned update lifecycle. */
export function AboutSettingsPage() {
  const { state, error, check, install } = useDesktopUpdates();
  const busy = state ? ["unsupported", "checking", "downloading", "installing"].includes(state.phase) : !error;
  const downloaded = state?.phase === "downloaded";

  return (
    <section className="settings-page scrollbar-soft h-full overflow-y-auto bg-gradient-app bg-fixed px-4 py-8 sm:px-10 lg:px-16 lg:py-10" data-testid="about-settings">
      <div className="mx-auto w-full max-w-[840px]">
        <h2 className="m-0 font-display text-headline text-ink">关于</h2>
        <div className="mt-8 flex items-center gap-4 border-b border-line-soft pb-8">
          <img src={new URL("../../../../../assets/shiori-app-icon.png", import.meta.url).href} alt="" className="h-16 w-16 shrink-0 object-contain" />
          <div className="min-w-0">
            <h3 className="font-display text-title text-ink">Shiori</h3>
            <p className="mt-1 break-all text-sm text-ink-muted">当前版本 {state ? `v${state.currentVersion}` : "…"}</p>
          </div>
        </div>
        <div className="py-8">
          <h3 className="text-base font-medium text-ink">应用更新</h3>
          <p className="mt-3 text-sm text-ink-secondary" role="status">{state ? statusLabels[state.phase] : "正在读取版本…"}</p>
          {state?.latestVersion ? <p className="mt-2 break-all text-sm text-ink-muted">新版本 v{state.latestVersion}</p> : null}
          {state?.phase === "downloading" ? (
            <div className="mt-4 flex max-w-md items-center gap-3">
              <progress aria-label="更新下载进度" max={100} value={state.progress} className="h-2 min-w-0 flex-1 accent-accent" />
              <span className="w-12 text-right text-sm tabular-nums text-ink-secondary">{Math.floor(state.progress)}%</span>
            </div>
          ) : null}
          {error ? <p role="alert" className="mt-3 break-words text-sm text-danger-text">{error}</p> : null}
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" disabled={busy} onClick={() => void (downloaded ? install() : check())} className={cx(primaryButtonClass, "inline-flex min-h-11 items-center justify-center gap-2 text-sm")}>
              <ArrowClockwise size={18} aria-hidden="true" />
              {downloaded ? "重启并安装" : state?.phase === "error" || error ? "重新检查" : "检查更新"}
            </button>
            <a href={releaseUrl} target="_blank" rel="noreferrer" className={cx(ghostButtonClass, "inline-flex min-h-11 items-center justify-center gap-2 text-sm no-underline")}>
              <ArrowSquareOut size={18} aria-hidden="true" />更新日志
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
