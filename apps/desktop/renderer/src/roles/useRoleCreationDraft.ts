import { useState } from "react";
import { createEmptyNewRoleForm } from "../app/appState";
import { useRoleCardImport } from "../app/useRoleCardImport";
import type { RoleCreationControllerArgs } from "../app/roleCreationWorkflow";
import type { NewRoleFormState } from "../shared/types";
import { useLatestRef } from "../shared/useLatestRef";

/** Shares role draft and import staging between creation entry points. */
export function useRoleCreationDraft(setWorkspaceFeedback: RoleCreationControllerArgs["setWorkspaceFeedback"]) {
  const [newRoleForm, setNewRoleForm] = useState(createEmptyNewRoleForm);
  const newRoleFormRef = useLatestRef(newRoleForm);
  function updateNewRoleForm(next: React.SetStateAction<NewRoleFormState>) {
    const resolved = typeof next === "function" ? next(newRoleFormRef.current) : next;
    newRoleFormRef.current = resolved;
    setNewRoleForm(resolved);
  }
  const imports = useRoleCardImport({ updateNewRoleForm, setWorkspaceFeedback });
  return { newRoleForm, newRoleFormRef, updateNewRoleForm, ...imports };
}
