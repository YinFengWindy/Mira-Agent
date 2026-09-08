import { useRef, useState } from "react";
import { ArrowRight } from "@phosphor-icons/react";
import { ModelRegistrationFields } from "../settings/ModelRegistrationFields";
import { createModelRegistration } from "../settings/modelRegistration";
import { registerOnboardingModel } from "./onboardingData";
import { onboardingActionClass } from "./onboardingStyles";

/** Submits one explicit model registration without auto-saving incomplete credentials. */
export function OnboardingModelStep({ onSaved, onBusyChange }: { onSaved: () => Promise<unknown>; onBusyChange: (busy: boolean) => void }) {
  const [registration, setRegistration] = useState(createModelRegistration);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  async function save() {
    if (pending.current) return;
    pending.current = true;
    setSaving(true);
    onBusyChange(true);
    setError("");
    try {
      await registerOnboardingModel(window.miraDesktop, registration);
      await onSaved();
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      pending.current = false;
      setSaving(false);
      onBusyChange(false);
    }
  }
  return (
    <form onSubmit={(event) => { event.preventDefault(); void save(); }}>
      <fieldset disabled={saving} className="min-w-0"><ModelRegistrationFields registration={registration} onChange={setRegistration} /></fieldset>
      {error ? <p role="alert" className="mt-4 text-sm text-red-700">{error}</p> : null}
      <div className="mt-8 flex justify-end"><button type="submit" className={onboardingActionClass} disabled={saving || !registration.model.trim() || !registration.provider.trim()}>
        {saving ? "正在保存" : "保存并继续"}<ArrowRight size={18} />
      </button></div>
    </form>
  );
}
