import { createEmptyNewRoleForm } from "./appState";
import type { RoleCardImportPreview } from "../shared/types";

/** Lifecycle state for a single role card awaiting confirmation. */
export type RoleCardImportState = {
  status: "idle" | "previewing" | "ready";
  preview: RoleCardImportPreview | null;
  source: string;
};

/** Stable empty state shared by reset and cancellation. */
export const idleRoleCardImport: RoleCardImportState = { status: "idle", preview: null, source: "" };

function isImportPreview(payload: unknown): payload is RoleCardImportPreview {
  return typeof payload === "object" && payload !== null
    && "import_id" in payload && typeof payload.import_id === "string" && Boolean(payload.import_id.trim());
}

/** Validates the bridge preview before a draft can reference its staging token. */
export function readRoleCardImportPreview(payload: unknown) {
  if (!isImportPreview(payload)) throw new Error("导入预览未返回 import_id");
  return payload;
}

/** Replaces a manual draft with all editable imported fields, including its description. */
export function createRoleFormFromImport(preview: RoleCardImportPreview) {
  return {
    ...createEmptyNewRoleForm(),
    importId: preview.import_id,
    name: preview.name ?? "",
    description: preview.description ?? "",
    systemPrompt: preview.system_prompt ?? "",
    profile: preview.profile,
    emotionSelections: {},
  };
}
