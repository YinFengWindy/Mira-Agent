import { useState } from "react";
import { createEmptyNewRoleForm } from "./appState";
import { useLatestRef } from "../shared/useLatestRef";
import { cancelRoleCreation, resetRoleCreationForm, runRoleCreation } from "./roleCreationWorkflow";
import type { RoleCreationControllerArgs } from "./roleCreationWorkflow";
import { useRoleCardImport } from "./useRoleCardImport";
import type { NewRoleFormState } from "../shared/types";

/** Assembles the new-role draft, import lifecycle, and creation workflow. */
export function useRoleCreationController(args: RoleCreationControllerArgs) {
  const [newRoleForm, setNewRoleForm] = useState(createEmptyNewRoleForm);
  const [creating, setCreating] = useState(false);
  const newRoleFormRef = useLatestRef(newRoleForm);
  const creatingRef = useLatestRef(creating);

  function updateNewRoleForm(next: React.SetStateAction<NewRoleFormState>) {
    const resolved = typeof next === "function" ? next(newRoleFormRef.current) : next;
    newRoleFormRef.current = resolved;
    setNewRoleForm(resolved);
  }

  const imports = useRoleCardImport({ updateNewRoleForm, setWorkspaceFeedback: args.setWorkspaceFeedback });
  const formActions = { ...args, updateNewRoleForm };

  function resetNewRoleForm() {
    if (creatingRef.current) return;
    void imports.cancelRoleCardImport();
    resetRoleCreationForm(formActions);
  }

  function cancelCreateRole() {
    if (creatingRef.current) return;
    void imports.cancelRoleCardImport();
    cancelRoleCreation({ ...formActions, creating: false });
  }

  async function createRole() {
    if (creatingRef.current || imports.roleCardImport.status === "previewing") return;
    creatingRef.current = true;
    try {
      const created = await runRoleCreation(newRoleFormRef.current, {
        ...args, setCreating, invoke: window.miraDesktop.invoke,
      });
      if (created) {
        imports.clearRoleCardImport();
        updateNewRoleForm(createEmptyNewRoleForm());
      }
    } finally {
      creatingRef.current = false;
    }
  }

  return {
    creating, newRoleForm, updateNewRoleForm, resetNewRoleForm, cancelCreateRole, createRole,
    roleCardImport: imports.roleCardImport,
    previewRoleCard: imports.previewRoleCard,
    cancelRoleCardImport: () => { if (!creatingRef.current) return imports.cancelRoleCardImport(); },
  };
}
