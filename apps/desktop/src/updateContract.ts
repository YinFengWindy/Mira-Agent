/** Serializable update status shared by the main process and settings UI. */
export type DesktopUpdateState = {
  revision: number;
  currentVersion: string;
  phase: "unsupported" | "idle" | "checking" | "current" | "downloading" | "downloaded" | "installing" | "error";
  latestVersion: string | null;
  progress: number;
  error: string | null;
};

/** Desktop-owned update commands; no backend bridge connection is required. */
export type DesktopUpdateApi = {
  getState(): Promise<DesktopUpdateState>;
  check(): Promise<DesktopUpdateState>;
  install(): Promise<void>;
  onState(listener: (state: DesktopUpdateState) => void): () => void;
};
