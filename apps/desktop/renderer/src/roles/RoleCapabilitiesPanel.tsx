import { Brain, ImageSquare, Monitor } from "@phosphor-icons/react";
import { SettingsToggleCard } from "../settings/SettingsToggleCard";
import { cx } from "../shared/styles";
import type { RoleFormState, RoleRecord } from "../shared/types";
import { roleSectionDescriptionClass, roleSectionTitleClass } from "./roleEditorStyles";
import { RoleVoiceSettingsPanel } from "./RoleVoiceSettingsPanel";

type RoleCapabilitiesPanelProps = {
  activeRole: RoleRecord | null;
  bridgeReady: boolean;
  roleForm: RoleFormState;
  onUpdate: (next: React.SetStateAction<RoleFormState>) => void;
};

type CapabilityTileProps = {
  icon: typeof Brain;
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  disabledStatus?: string;
  tintClass: string;
  iconClass: string;
  onChange: (checked: boolean) => void;
};

/** Renders one runtime feature as a tinted tile with its toggle and status. */
function CapabilityTile({
  icon: Icon,
  label,
  description,
  checked,
  disabled = false,
  disabledStatus,
  tintClass,
  iconClass,
  onChange,
}: CapabilityTileProps) {
  const status = disabled ? (disabledStatus ?? "不可用") : checked ? "已启用" : "未启用";

  return (
    <div className={cx("grid content-start gap-3 rounded-2xl p-5", disabled ? "bg-surface-soft" : tintClass)}>
      <div className="flex items-start justify-between gap-3">
        <span className={cx("grid h-10 w-10 place-items-center rounded-xl bg-white/75", disabled ? "text-ink-faint" : iconClass)} aria-hidden="true">
          <Icon className="h-5 w-5" weight="duotone" />
        </span>
        <SettingsToggleCard checked={checked} ariaLabel={label} disabled={disabled} onChange={onChange} />
      </div>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-ink">{label}</span>
          <span className={cx("rounded-full bg-white/75 px-2 py-0.5 text-[11px] leading-4", disabled ? "text-ink-faint" : checked ? "text-success-text" : "text-ink-muted")}>{status}</span>
        </div>
        <p className="mt-1.5 text-xs leading-5 text-ink-muted">{description}</p>
      </div>
    </div>
  );
}

/** Groups runtime-facing role capabilities away from the core profile fields. */
export function RoleCapabilitiesPanel({ activeRole, bridgeReady, roleForm, onUpdate }: RoleCapabilitiesPanelProps) {
  const desktopPetUnavailable = !bridgeReady || (!activeRole?.selected_pet_package_id && !roleForm.desktopPetEnabled);

  return (
    <div className="grid gap-7 text-sm text-ink">
      <section aria-labelledby="role-capabilities-heading" className="grid gap-4">
        <div>
          <h2 className={roleSectionTitleClass} id="role-capabilities-heading">运行能力</h2>
          <p className={roleSectionDescriptionClass}>控制角色在对话和桌面中的表现。</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <CapabilityTile
            icon={Brain}
            tintClass="bg-[#FBF1F4]"
            iconClass="text-[#B4536F]"
            label="NSFW 记忆"
            description="允许角色保留成人内容相关的对话记忆。"
            checked={roleForm.nsfwMemoryEnabled}
            onChange={(checked) => onUpdate((current) => ({ ...current, nsfwMemoryEnabled: checked }))}
          />
          <CapabilityTile
            icon={ImageSquare}
            tintClass="bg-[#F4F1FB]"
            iconClass="text-[#7A5EC2]"
            label="自动场景 CG"
            description="在合适的剧情节点生成场景画面。"
            checked={roleForm.autoSceneCgEnabled}
            onChange={(checked) => onUpdate((current) => ({ ...current, autoSceneCgEnabled: checked }))}
          />
          <CapabilityTile
            icon={Monitor}
            tintClass="bg-[#FBF5EB]"
            iconClass="text-[#B08340]"
            label="桌宠"
            description="让角色以桌面宠物形式陪伴和互动。"
            checked={roleForm.desktopPetEnabled}
            disabled={desktopPetUnavailable}
            disabledStatus={!bridgeReady ? "桌面服务不可用" : "未配置桌宠"}
            onChange={(checked) => onUpdate((current) => ({ ...current, desktopPetEnabled: checked }))}
          />
        </div>
      </section>
      <RoleVoiceSettingsPanel roleForm={roleForm} onUpdate={onUpdate} />
    </div>
  );
}
