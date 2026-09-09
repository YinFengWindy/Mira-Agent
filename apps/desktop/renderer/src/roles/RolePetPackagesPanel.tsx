import { toFileUrl } from "../shared/format";
import { CheckCircleIcon, TrashIcon } from "@phosphor-icons/react";
import { UploadIcon } from "../shared/icons";
import { cx } from "../shared/styles";
import type { RoleRecord } from "../shared/types";

type RolePetPackagesPanelProps = {
  role: RoleRecord | null;
  disabled: boolean;
  onImport: () => void;
  onRemove: (packageId: string) => void;
  onSelect: (packageId: string) => void;
};

/** Manages desktop-pet packages inside the owning role's asset library. */
export function RolePetPackagesPanel({ role, disabled, onImport, onRemove, onSelect }: RolePetPackagesPanelProps) {
  const packages = role?.pet_packages ?? [];
  return (
    <section className="border-t border-line-soft px-4 py-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-medium text-ink">桌宠素材包</div>
        <button className="grid h-8 w-8 place-items-center rounded-md border border-line-soft bg-white text-ink-secondary transition hover:bg-surface-hover focus:outline-none" type="button" aria-label="导入桌宠素材包" title="导入桌宠素材包" disabled={disabled} onClick={onImport}>
          <UploadIcon className="h-4 w-4 fill-current" />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {packages.map((item) => (
          <div
            className={cx(
              "group relative overflow-hidden rounded-md border bg-white",
              role?.selected_pet_package_id === item.id ? "border-accent shadow-soft" : "border-line-soft",
            )}
            key={item.id}
          >
            <button
              className="grid w-full gap-2 p-2 text-left transition hover:bg-surface-hover focus:outline-none"
              type="button"
              disabled={disabled}
              aria-pressed={role?.selected_pet_package_id === item.id}
              onClick={() => onSelect(item.id)}
            >
              <span className="relative block aspect-square w-full overflow-hidden bg-surface-soft">
                {item.preview_abs ? <img className="h-full w-full object-contain" src={toFileUrl(item.preview_abs)} alt={item.display_name} /> : null}
              </span>
              <span className="min-w-0 truncate text-xs text-ink">{item.display_name}</span>
            </button>
            <button
              className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-md border border-line-soft bg-white/92 text-ink-secondary opacity-0 shadow-soft transition hover:border-[var(--danger-300)] hover:bg-danger-soft hover:text-danger-text focus:opacity-100 group-hover:opacity-100 focus:outline-none"
              type="button"
              aria-label={`删除桌宠素材 ${item.display_name}`}
              disabled={disabled}
              onClick={() => onRemove(item.id)}
            >
              <TrashIcon className="h-4 w-4" weight="bold" />
            </button>
            {role?.selected_pet_package_id === item.id ? <CheckCircleIcon className="absolute left-2 top-2 h-5 w-5 text-ink-secondary" weight="fill" aria-label="已选中" /> : null}
          </div>
        ))}
      </div>
    </section>
  );
}
