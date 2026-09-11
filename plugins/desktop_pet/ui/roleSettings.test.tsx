import assert from "node:assert/strict";
import { test } from "node:test";
import { act } from "react";
import { DesktopPetRoleSettings, desktopPetRoleSettings } from "./roleSettings";
import { mountTestComponent } from "../../../apps/desktop/renderer/src/shared/testing/domTestHarness";

test("pet toggle edits only its draft and gates enablement on selected packages", async () => {
  const changes: unknown[] = [];
  const synced: unknown[] = [];
  const view = await mountTestComponent(null, { windowGlobals: {
    miraDesktop: { syncPet: async (enabled: boolean) => { synced.push(enabled); } },
  } });
  try {
    await view.render(<DesktopPetRoleSettings values={{ enabled: false }} snapshot={{ available: false }} onChange={(values) => changes.push(values)} />);
    let toggle = view.container.querySelector<HTMLButtonElement>('[aria-label="桌宠"]');
    assert.ok(toggle?.disabled);
    await view.render(<DesktopPetRoleSettings values={{ enabled: false }} snapshot={{ available: true }} onChange={(values) => changes.push(values)} />);
    toggle = view.container.querySelector<HTMLButtonElement>('[aria-label="桌宠"]');
    assert.ok(toggle && !toggle.disabled);
    await act(async () => { toggle.click(); });
    assert.deepEqual(changes, [{ enabled: true }]);
    assert.deepEqual(synced, []);
    await desktopPetRoleSettings.afterSave?.({ enabled: true });
    assert.deepEqual(synced, [true]);
  } finally { await view.cleanup(); }
});
