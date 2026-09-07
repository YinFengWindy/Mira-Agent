import { toFileUrl } from "../shared/format";
import type { RoleFormState, RoleProfileDraft, RoleRecord } from "../shared/types";
import { TiltedCard } from "../shared/ui/reactBits/TiltedCard";
import { RoleCardProfileForm } from "./RoleCardProfileForm";

type RoleProfilePanelProps = {
  activeRole: RoleRecord | null;
  previewAvatar: string | null;
  roleForm: RoleFormState;
  onOpenAssetsPage: () => void;
  onUpdate: (next: React.SetStateAction<RoleFormState>) => void;
};

/** Edits persisted role identity and structured runtime fields. */
export function RoleProfilePanel({
  activeRole,
  previewAvatar,
  roleForm,
  onOpenAssetsPage,
  onUpdate,
}: RoleProfilePanelProps) {
  const profile: RoleProfileDraft = roleForm.profile ?? {
    character: { behavior_rules: roleForm.systemPrompt },
  };

  function updateProfile(nextProfile: RoleProfileDraft): void {
    onUpdate((current) => ({
      ...current,
      profile: nextProfile,
      systemPrompt: nextProfile.character?.behavior_rules ?? current.systemPrompt,
    }));
  }

  return (
    <div className="grid gap-7" data-testid="role-detail-form-panel">
      <div className="grid gap-5 border-b border-[#E5E7EB] pb-7 sm:grid-cols-[104px_minmax(0,1fr)]">
        <TiltedCard className="h-fit overflow-hidden rounded-md border border-[#E5E7EB] shadow-[0_10px_24px_rgba(15,23,42,0.1)]">
          <button
            className="group relative block h-[104px] w-[104px] overflow-hidden bg-[rgba(37,24,18,0.3)] text-left focus:outline-none"
            data-testid="open-role-assets-button"
            data-has-preview-avatar={previewAvatar ? "true" : "false"}
            type="button"
            onClick={onOpenAssetsPage}
          >
            {previewAvatar ? (
              <img className="h-full w-full object-cover transition duration-500 group-hover:scale-105" src={toFileUrl(previewAvatar)} alt={`${activeRole?.name || "角色"} avatar`} />
            ) : (
              <div className="grid h-full w-full place-items-center bg-[#F3F4F6] text-4xl font-semibold text-[#6B7280]">
                {activeRole?.name.slice(0, 1).toUpperCase() || "R"}
              </div>
            )}
          </button>
        </TiltedCard>
        <div className="grid content-start gap-4">
          <input aria-label="角色名称" className="w-full border-0 border-b border-transparent bg-transparent px-0 py-1 text-2xl font-semibold text-[#111827] placeholder:text-[#9CA3AF] transition focus:border-[#2176FF] focus:outline-none" data-testid="edit-role-name" value={roleForm.name} placeholder="未命名角色" onChange={(event) => onUpdate((current) => ({ ...current, name: event.target.value }))} />
          <input aria-label="角色简介" className="w-full border-0 border-b border-transparent bg-transparent px-0 py-1 text-sm leading-6 text-[#6B7280] placeholder:text-[#9CA3AF] transition focus:border-[#2176FF] focus:outline-none" data-testid="edit-role-description" value={roleForm.description} placeholder="添加一行角色简介" onChange={(event) => onUpdate((current) => ({ ...current, description: event.target.value }))} />
        </div>
      </div>
      <RoleCardProfileForm profile={profile} onUpdate={updateProfile} showKnowledge={false} />
    </div>
  );
}
