import { ArrowLeft, Trash } from "@phosphor-icons/react";
import type { ModelRegistrationFormData } from "../../../src/bridge/shared";
import { ModelRegistrationFields } from "./ModelRegistrationFields";

type ModelRegistrationDetailsProps = {
  registration: ModelRegistrationFormData;
  canDelete: boolean;
  onBack: () => void;
  onChange: (
    mutate: (registration: ModelRegistrationFormData) => ModelRegistrationFormData,
  ) => void;
  onDelete: () => void;
};

/** Renders the focused editor for one model registration. */
export function ModelRegistrationDetails({
  registration,
  canDelete,
  onBack,
  onChange,
  onDelete,
}: ModelRegistrationDetailsProps) {
  return (
    <section className="grid">
      <header className="flex min-h-10 items-center gap-3 border-b border-[#E7ECF1] pb-3">
        <button
          className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-[#667085] transition hover:bg-[#F3F6FA] hover:text-[#182230] focus:outline-none"
          type="button"
          aria-label="返回模型注册列表"
          title="返回模型注册列表"
          onClick={onBack}
        >
          <ArrowLeft className="h-3.5 w-3.5" weight="bold" />
        </button>
        <strong className="min-w-0 flex-1 truncate text-[13px] font-semibold text-[#182230]">
          {registration.model || "未配置模型"}
        </strong>
        <button
          className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-[#8A94A3] transition hover:bg-[#FFF1F1] hover:text-[#C83E3E] focus:outline-none disabled:cursor-not-allowed disabled:opacity-35"
          type="button"
          aria-label="删除模型注册"
          title="删除模型注册"
          disabled={!canDelete}
          onClick={onDelete}
        >
          <Trash className="h-3.5 w-3.5" weight="bold" />
        </button>
      </header>
      <ModelRegistrationFields registration={registration} onChange={onChange} />
    </section>
  );
}
