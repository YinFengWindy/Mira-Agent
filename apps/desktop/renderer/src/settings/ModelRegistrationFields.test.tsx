import assert from "node:assert/strict";
import { it } from "node:test";
import type { ModelRegistrationFormData } from "../../../src/bridge/shared";
import { mountTestComponent } from "../shared/testing/domTestHarness";
import { chooseSelectOption } from "../shared/testing/selectTestActions";

it("ModelRegistrationFields changes effort while preserving the registered connection", async () => {
  const view = await mountTestComponent(null);
  const { ModelRegistrationFields } = await import("./ModelRegistrationFields");
  const initial: ModelRegistrationFormData = { id: "test", provider: "openai", model: "test-model", baseUrl: "https://example.test", apiKey: "key", effort: "none" };
  let registration = initial;
  try {
    await view.render(<ModelRegistrationFields registration={registration} onChange={(mutate) => { registration = mutate(registration); }} />);
    await chooseSelectOption("Effort", "max");
    assert.deepEqual(registration, { ...initial, effort: "max" });
  } finally { await view.cleanup(); }
});
