import React from "react";

type DesktopErrorBoundaryProps = {
  children: React.ReactNode;
};

type DesktopErrorBoundaryState = {
  hasError: boolean;
};

function reportBoundaryError(error: Error, componentStack: string): void {
  window.miraDesktop.reportRendererDiagnostic({
    kind: "error-boundary",
    message: error.message,
    stack: error.stack,
    componentStack,
  });
}

/** Catches renderer tree failures so desktop crashes degrade into a visible fallback instead of a blank window. */
export class DesktopErrorBoundary extends React.Component<
  DesktopErrorBoundaryProps,
  DesktopErrorBoundaryState
> {
  state: DesktopErrorBoundaryState = {
    hasError: false,
  };

  static getDerivedStateFromError(): DesktopErrorBoundaryState {
    return {
      hasError: true,
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    reportBoundaryError(error, info.componentStack ?? "");
  }

  render(): React.ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }
    return (
      <div className="grid h-screen place-items-center bg-gradient-app bg-fixed px-6 text-center text-ink-secondary">
        <div className="max-w-[320px] rounded-xl border border-line-soft bg-white/86 px-6 py-7 shadow-panel">
          <div className="text-sm font-semibold">界面暂时不可用</div>
          <div className="mt-2 text-[13px] leading-6 text-ink-muted">
            请重新打开桌面端。如果再次出现，诊断日志已经记录到本地。
          </div>
        </div>
      </div>
    );
  }
}
