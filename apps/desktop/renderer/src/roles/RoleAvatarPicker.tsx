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
      <div className="flex items-end gap-2">
        <button type="button" aria-label={source ? "更换头像" : "上传头像"} title={source ? "更换头像" : "上传头像"}
          disabled={disabled || picking} onClick={() => void pick()}
          className="group relative grid h-24 w-24 shrink-0 place-items-center overflow-hidden rounded-md border border-[#D8DCE2] bg-[#F2F5F9] text-[#667085] transition hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50">
          {source ? <img src={window.miraDesktop.localAssetUrl(source)} alt="角色头像预览" className="h-full w-full object-cover" /> : <Camera size={28} />}
        </button>
        {source ? <button type="button" aria-label="移除头像" title="移除头像" disabled={disabled || picking}
          onClick={() => onChange("")} className="grid h-8 w-8 place-items-center rounded-md text-[#667085] hover:bg-red-50 hover:text-red-600 disabled:opacity-50"><Trash size={18} /></button> : null}
      </div>
      <span className="text-xs text-[#667085]">头像（选填）</span>
      {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
