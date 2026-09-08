import { useState } from "react";
import { ArrowRight, User } from "@phosphor-icons/react";
import type { RoleRecord } from "../shared/types";
import { onboardingActionClass } from "./onboardingStyles";

/** Presents the created role and enters its real workspace before completion. */
export function OnboardingWorkspaceStep({ roles, entering, onEnter }: {
  roles: RoleRecord[];
  entering: boolean;
  onEnter: (role: RoleRecord) => Promise<void>;
}) {
  const [selectedId, setSelectedId] = useState(() => window.localStorage.getItem("miraDesktop.activeRoleId") ?? "");
  const role = roles.find((item) => item.id === selectedId) ?? roles[0];
  if (!role) return null;
  return (
    <div className="flex flex-col items-center gap-6 py-10 text-center">
      <div className="grid h-32 w-32 shrink-0 place-items-center overflow-hidden rounded-md bg-[#EDF4F0] text-[#286451]">
        {role.avatar_abs ? <img className="h-full w-full object-cover" src={window.miraDesktop.localAssetUrl(role.avatar_abs)} alt={role.name} /> : <User size={42} />}
      </div>
      <div className="w-full min-w-0">
        <h2 className="break-words text-2xl font-medium text-[#182230]">{role.name}</h2>
        {role.description ? <p className="mt-3 break-words text-sm leading-6 text-[#667085]">{role.description}</p> : null}
      </div>
      {roles.length > 1 ? <select aria-label="选择角色" value={role.id} onChange={(event) => setSelectedId(event.target.value)} disabled={entering}
        className="max-w-full rounded-md border border-line bg-surface p-2 text-sm">
        {roles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select> : null}
      <button type="button" className={onboardingActionClass} disabled={entering} onClick={() => void onEnter(role)}>
        {entering ? "正在进入" : "进入工作区"}<ArrowRight size={18} />
      </button>
    </div>
  );
}
