import { Select } from "../shared/ui/Select";
import type { ModelRegistrationFormData } from "../../../src/bridge/shared";
import { SettingsField as Field } from "./SettingsField";
import { SettingsSecretInput, settingsInputClass } from "./SettingsFieldPrimitives";

/** Model registration fields shared by the catalog and first-run setup. */
export function ModelRegistrationFields({ registration, onChange }: {
  registration: ModelRegistrationFormData;
  onChange: (mutate: (registration: ModelRegistrationFormData) => ModelRegistrationFormData) => void;
}) {
  const inputClass = settingsInputClass;
  return (
    <div className="grid">
      <Field label="Provider">
        <input aria-label="Provider" className={inputClass} value={registration.provider} onChange={(event) => onChange((current) => ({ ...current, provider: event.target.value }))} />
      </Field>
      <Field label="模型">
        <input aria-label="模型" className={inputClass} value={registration.model} onChange={(event) => onChange((current) => ({ ...current, model: event.target.value }))} />
      </Field>
      <Field label="Effort">
        <Select aria-label="Effort" className={inputClass} value={registration.effort} onValueChange={(value) => onChange((current) => ({ ...current, effort: value as ModelRegistrationFormData["effort"] }))} options={[{ value: "none", label: "none" }, { value: "low", label: "low" }, { value: "high", label: "high" }, { value: "max", label: "max" }]} />
      </Field>
      <Field label="Base URL">
        <input aria-label="Base URL" className={inputClass} value={registration.baseUrl} onChange={(event) => onChange((current) => ({ ...current, baseUrl: event.target.value }))} />
      </Field>
      <Field label="API Key">
        <SettingsSecretInput ariaLabel="API Key" value={registration.apiKey} onChange={(value) => onChange((current) => ({ ...current, apiKey: value }))} />
      </Field>
    </div>
  );
}
