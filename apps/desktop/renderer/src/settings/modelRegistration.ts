import type { ModelRegistrationFormData } from "../../../src/bridge/shared";

/** Creates an unsaved model registration with the settings catalog defaults. */
export function createModelRegistration(): ModelRegistrationFormData {
  return { id: crypto.randomUUID(), provider: "openai", baseUrl: "", apiKey: "", model: "", effort: "none" };
}
