import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { usePluginConfigController } from "../../../apps/desktop/renderer/src/plugins/usePluginConfigController";
import type { PluginRpcClient } from "../../../apps/desktop/renderer/src/plugins/pluginBridgeClient";
import { ImageStudioSidebar } from "./ImageStudioSidebar";
import { PromptTagWorkspaceSidebar } from "./PromptTagWorkspaceSidebar";
import {
  backToStudio,
  clearError,
  loadHistory,
  openPromptTagLibrary,
  setPromptTagSection,
  submitGenerate,
  useNovelAiPageStore,
} from "./novelAiPageStore";
import type { ImageStudioFormState } from "./types";

type NovelAIPageSidebarProps = {
  pageId: string;
  animating: boolean;
  collapsed: boolean;
  width: number;
  onBeginResize: (event: React.PointerEvent<HTMLDivElement>) => void;
  client: PluginRpcClient;
};

const initialForm: ImageStudioFormState = {
  roleId: "",
  prompt: "",
  negativePrompt: "",
  mode: "txt2img",
  baseImagePath: "",
  strength: 0.7,
  noise: 0.2,
  sizePreset: "square",
  customWidth: "",
  customHeight: "",
  model: "nai-diffusion-4-5-curated",
};

/**
 * Fallbacks for the two configured model ids, used only until the plugin's
 * config has loaded. See the identical constants this replaces in the old
 * `useImageStudioState` for why resolving from config (not a hardcoded
 * literal) matters.
 */
const NOVELAI_DEFAULT_MODEL_FALLBACK = "nai-diffusion-4-5-curated";
const NOVELAI_NSFW_MODEL_FALLBACK = "nai-diffusion-4-5-full";

function parsePositiveInteger(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return null;
  return parsed;
}

/**
 * The novelai `nav.page` entry's `Sidebar` contribution (issue #226 gap A):
 * mounted by the host into its resizable sidebar track, as a sibling of
 * `NovelAIPage` rather than a child of it. Switches between the generation
 * form and the prompt-tag nav depending on the shared store's `view`
 * (issue #226's "real complication" — see `novelAiPageStore.ts`).
 *
 * Owns the generation form and NSFW/quality-tag/undesired-content config
 * locally (only this component reads or writes them); publishes submit
 * results and role-scoped history into the shared store, which
 * `NovelAIPage` displays.
 */
export function NovelAIPageSidebar({ animating, collapsed, width, onBeginResize, client }: NovelAIPageSidebarProps) {
  const store = useNovelAiPageStore();
  const [form, setForm] = useState<ImageStudioFormState>(initialForm);
  const config = usePluginConfigController("novelai");

  const nsfwEnabled = Boolean(config.draft?.nsfw_enabled);
  const addQualityTags = Boolean(config.draft?.add_quality_tags);
  const undesiredContentPreset = Number(config.draft?.undesired_content_preset ?? 0);

  const roleItems = useMemo(() => (
    store.roles.map((role) => ({ id: role.id, label: role.name, avatarAbs: role.avatar_abs }))
  ), [store.roles]);

  // Keeps the selected role valid as the roster or the ambient "role open in
  // chat" changes, defaulting an empty selection rather than overwriting a
  // deliberate one — mirrors the old `useImageStudioState` role-sync effect.
  useEffect(() => {
    setForm((current) => {
      const roleId = current.roleId && store.roles.some((role) => role.id === current.roleId)
        ? current.roleId
        : (store.activeRoleId || store.roles[0]?.id || "");
      return current.roleId === roleId ? current : { ...current, roleId };
    });
  }, [store.activeRoleId, store.roles]);

  useEffect(() => {
    void loadHistory(client, form.roleId);
  }, [client, form.roleId]);

  const resolvedMode = form.baseImagePath.trim() ? "img2img" : "txt2img";
  const configuredDefaultModel = typeof config.draft?.default_model === "string" ? config.draft.default_model : "";
  const configuredNsfwModel = typeof config.draft?.nsfw_model === "string" ? config.draft.nsfw_model : "";
  const resolvedModel = nsfwEnabled
    ? (configuredNsfwModel || NOVELAI_NSFW_MODEL_FALLBACK)
    : (configuredDefaultModel || NOVELAI_DEFAULT_MODEL_FALLBACK);

  const validationError = useMemo(() => {
    if (resolvedMode === "img2img" && !form.baseImagePath.trim()) {
      return "img2img 需要输入图";
    }
    if (form.sizePreset === "custom") {
      const width2 = parsePositiveInteger(form.customWidth);
      const height2 = parsePositiveInteger(form.customHeight);
      if (width2 == null || height2 == null) return "";
      if (width2 * height2 > 1024 * 1024) return "自定义尺寸总像素不能超过 1024 × 1024";
    }
    return "";
  }, [form.baseImagePath, form.customHeight, form.customWidth, form.sizePreset, resolvedMode]);

  async function handlePickBaseImage(): Promise<void> {
    const files = await window.miraDesktop.pickImages({ multiple: false });
    if (!files[0]) return;
    setForm((current) => ({ ...current, baseImagePath: files[0] }));
  }

  async function handleSubmit(): Promise<void> {
    // An empty prompt clears any error still on screen rather than just
    // bailing: the user has plainly abandoned the attempt that produced it, so
    // leaving the old message up reads as if this submit failed too.
    if (!form.prompt.trim()) {
      clearError();
      return;
    }
    if (validationError) return;
    await submitGenerate(client, {
      role_id: form.roleId,
      session_key: form.roleId ? `role:${form.roleId}` : "desktop:image-studio",
      prompt: form.prompt,
      mode: resolvedMode,
      base_image_path: form.baseImagePath,
      strength: resolvedMode === "img2img" ? form.strength : undefined,
      noise: resolvedMode === "img2img" ? form.noise : undefined,
      negative_prompt: form.negativePrompt,
      size_preset: form.sizePreset,
      custom_width: form.sizePreset === "custom" ? parsePositiveInteger(form.customWidth) : undefined,
      custom_height: form.sizePreset === "custom" ? parsePositiveInteger(form.customHeight) : undefined,
      model: resolvedModel,
    });
  }

  if (store.view === "prompt-tags") {
    return (
      <PromptTagWorkspaceSidebar
        activeSection={store.promptTagSection}
        animating={animating}
        collapsed={collapsed}
        width={width}
        onOpenSection={setPromptTagSection}
        onBackToStudio={backToStudio}
        onBeginResize={onBeginResize}
      />
    );
  }

  return (
    <ImageStudioSidebar
      bridgeReady={store.rolesLoaded}
      animating={animating}
      collapsed={collapsed}
      width={width}
      form={form}
      nsfwEnabled={nsfwEnabled}
      addQualityTags={addQualityTags}
      undesiredContentPreset={undesiredContentPreset}
      roleItems={roleItems}
      submitting={store.submitting}
      validationError={validationError}
      onOpenPromptTagLibrary={openPromptTagLibrary}
      onBeginResize={onBeginResize}
      onChange={(next) => setForm((current) => ({ ...current, ...next }))}
      onPickBaseImage={() => void handlePickBaseImage()}
      onSubmit={() => void handleSubmit()}
      onToggleNsfwEnabled={() => config.updateDraft((current) => ({ ...current, nsfw_enabled: !nsfwEnabled }))}
      onToggleAddQualityTags={() => config.updateDraft((current) => ({ ...current, add_quality_tags: !addQualityTags }))}
      onChangeUndesiredContentPreset={(value) => config.updateDraft((current) => ({ ...current, undesired_content_preset: value }))}
    />
  );
}
