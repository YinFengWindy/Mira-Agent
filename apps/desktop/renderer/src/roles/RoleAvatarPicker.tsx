import { useRef, useState } from "react";
import { Camera, Trash } from "@phosphor-icons/react";

/** Selects and previews an optional avatar before a role is persisted. */
export function RoleAvatarPicker({ source, disabled, onChange }: {
  source: string;
  disabled: boolean;
  onChange: (source: string) => void;
}) {
  const [error, setError] = useState("");
  const [picking, setPicking] = useState(false);
  const pending = useRef(false);
  async function pick() {
    if (pending.current || disabled) return;
    pending.current = true;
    setPicking(true);
    setError("");
    try {
      const [path] = await window.miraDesktop.pickImages({ multiple: false });
      if (path) onChange(path);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      pending.current = false;
      setPicking(false);
    }
  }
  return (
    <div className="grid justify-items-start gap-2">
      <div className="group relative h-28 w-28 shrink-0 overflow-hidden rounded-xl border border-line-soft shadow-soft">
        <button type="button" aria-label={source ? "更换头像" : "上传头像"} title={source ? "更换头像" : "上传头像"}
          disabled={disabled || picking} onClick={() => void pick()}
          className="grid h-full w-full place-items-center bg-surface-soft text-ink-muted transition hover:text-ink disabled:opacity-50">
          {source ? <img src={window.miraDesktop.localAssetUrl(source)} alt="角色头像预览" className="h-full w-full object-cover" /> : <Camera size={28} />}
        </button>
        {source ? <button type="button" aria-label="移除头像" title="移除头像" disabled={disabled || picking}
          onClick={() => onChange("")}
          className="absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-full bg-white/92 text-ink-muted opacity-0 shadow-soft transition group-hover:opacity-100 hover:bg-danger-soft hover:text-danger-text focus-visible:opacity-100 disabled:opacity-50"><Trash size={14} /></button> : null}
      </div>
      <span className="text-xs text-ink-muted">头像（选填）</span>
      {error ? <p role="alert" className="text-sm text-danger-text">{error}</p> : null}
    </div>
  );
}
