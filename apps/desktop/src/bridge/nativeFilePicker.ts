import type { OpenDialogOptions, OpenDialogReturnValue } from "electron";
import { normalizeFilePickerOptions } from "../assets/filePickerContract.js";
import { stagePickedFiles } from "../assets/pickedFileStaging.js";

/** Opens a constrained native dialog and stages only the paths it returned. */
export async function pickNativeFiles(
  options: unknown,
  importsRoot: string,
  showOpenDialog: (options: OpenDialogOptions) => Promise<OpenDialogReturnValue>,
) {
  const policy = normalizeFilePickerOptions(options);
  const selected = await showOpenDialog({
    properties: policy.multiple ? ["openFile", "multiSelections"] : ["openFile"],
    filters: policy.filters,
  });
  if (selected.canceled) return [];
  return stagePickedFiles(selected.filePaths, importsRoot, policy);
}
