import { startTransition, useCallback, useEffect, useMemo, useState } from "react";
import { usePluginConfigController } from "../../../apps/desktop/renderer/src/plugins/usePluginConfigController";
import type { PluginRpcClient } from "../../../apps/desktop/renderer/src/plugins/pluginBridgeClient";
import type { RoleRecord } from "../../../apps/desktop/renderer/src/shared/types";
import type {
  ImageGenerateResult,
  ImageHistoryRecord,
  ImageStudioFormState,
} from "./types";

type UseImageStudioStateArgs = {
  client: PluginRpcClient;
  activeRole: RoleRecord | null;
  roles: RoleRecord[];
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
 * config has loaded.
 *
 * `default_model` / `nsfw_model` are real fields on `NovelAIConfig`, so the
 * schema-generated settings section renders them as editable. Resolving the
 * model from the config draft rather than from these constants is what keeps
 * an edited value from being silently ignored here — before #180 those fields
 * existed in `[integrations.novelai]` but no settings UI surfaced them, so the
 * hardcoded literals happened to agree with the default.
 */
const NOVELAI_DEFAULT_MODEL_FALLBACK = "nai-diffusion-4-5-curated";
const NOVELAI_NSFW_MODEL_FALLBACK = "nai-diffusion-4-5-full";

function parsePositiveInteger(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return null;
  return parsed;
}

function resolvePresetSize(sizePreset: ImageStudioFormState["sizePreset"]): {
  width: string;
  height: string;
} {
  switch (sizePreset) {
    case "landscape":
      return { width: "1216", height: "832" };
    case "portrait":
      return { width: "832", height: "1216" };
    case "custom":
      return { width: "-", height: "-" };
    case "square":
    default:
      return { width: "1024", height: "1024" };
  }
}

/**
 * Manages image studio state so the plugin page's sidebar and preview area
 * stay in sync. Manual generation and history go through the injected
 * `plugin.novelai.*` RPC client; NSFW/quality-tag/undesired-content settings
 * go through the plugin's own `[plugins.novelai]` config channel (issue
 * #180) instead of the old shared settings draft.
 */
export function useImageStudioState({ client, activeRole, roles }: UseImageStudioStateArgs) {
  const [form, setForm] = useState<ImageStudioFormState>(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [history, setHistory] = useState<ImageHistoryRecord[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [latestResult, setLatestResult] = useState<ImageGenerateResult | null>(null);
  const [error, setError] = useState("");
  const config = usePluginConfigController("novelai");

  const roleItems = useMemo(() => (
    roles.map((role) => ({
      id: role.id,
      label: role.name,
      avatarAbs: role.avatar_abs,
    }))
  ), [roles]);

  const nsfwEnabled = Boolean(config.draft?.nsfw_enabled);
  const addQualityTags = Boolean(config.draft?.add_quality_tags);
  const undesiredContentPreset = Number(config.draft?.undesired_content_preset ?? 0);

  const loadHistory = useCallback(async (): Promise<void> => {
    try {
      const payload = await client.call<{ records: ImageHistoryRecord[] }>("history", {
        role_id: form.roleId,
        limit: 24,
      });
      const records = Array.isArray(payload.records) ? payload.records : [];
      setHistory(records);
      setSelectedRecordId((current) => (
        records.some((record) => record.id === current)
          ? current
          : (records[0]?.id ?? "")
      ));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    }
  }, [client, form.roleId]);

  // Runs once on mount plus whenever the active role changes. History is not
  // reloaded here: the effect below re-fires on its own once `form.roleId`
  // settles, so doing it here too would fetch twice for one role change.
  useEffect(() => {
    setLatestResult(null);
    setError("");
    setForm((current) => ({
      ...current,
      roleId: current.roleId || activeRole?.id || "",
    }));
  }, [activeRole?.id]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    setForm((current) => {
      const roleId = current.roleId && roles.some((role) => role.id === current.roleId)
        ? current.roleId
        : (activeRole?.id ?? roles[0]?.id ?? "");
      return current.roleId === roleId ? current : { ...current, roleId };
    });
  }, [activeRole?.id, roles]);

  const resolvedMode = form.baseImagePath.trim() ? "img2img" : "txt2img";
  const configuredDefaultModel = typeof config.draft?.default_model === "string"
    ? config.draft.default_model
    : "";
  const configuredNsfwModel = typeof config.draft?.nsfw_model === "string"
    ? config.draft.nsfw_model
    : "";
  const resolvedModel = useMemo(() => (
    nsfwEnabled
      ? configuredNsfwModel || NOVELAI_NSFW_MODEL_FALLBACK
      : configuredDefaultModel || NOVELAI_DEFAULT_MODEL_FALLBACK
  ), [configuredDefaultModel, configuredNsfwModel, nsfwEnabled]);

  const validationError = useMemo(() => {
    if (resolvedMode === "img2img" && !form.baseImagePath.trim()) {
      return "img2img 需要输入图";
    }
    if (form.sizePreset === "custom") {
      const width = parsePositiveInteger(form.customWidth);
      const height = parsePositiveInteger(form.customHeight);
      if (width == null || height == null) return "";
      if (width * height > 1024 * 1024) return "自定义尺寸总像素不能超过 1024 × 1024";
    }
    return "";
  }, [form.baseImagePath, form.customHeight, form.customWidth, form.sizePreset, resolvedMode]);

  const activeRecord = history.find((item) => item.id === selectedRecordId) ?? history[0] ?? null;
  const requestSummary = useMemo(() => {
    const presetSize = resolvePresetSize(form.sizePreset);
    return {
      mode: resolvedMode,
      width: form.sizePreset === "custom" ? (form.customWidth || "-") : presetSize.width,
      height: form.sizePreset === "custom" ? (form.customHeight || "-") : presetSize.height,
      model: resolvedModel || "-",
    };
  }, [form, resolvedMode, resolvedModel]);

  async function handlePickBaseImage(): Promise<void> {
    const files = await window.miraDesktop.pickImages({ multiple: false });
    if (!files[0]) return;
    setForm((current) => ({ ...current, baseImagePath: files[0] }));
  }

  async function handleSubmit(): Promise<void> {
    if (!form.prompt.trim()) {
      setError("");
      return;
    }
    if (validationError) return;
    setSubmitting(true);
    setError("");
    try {
      const payload = await client.call<{ result: ImageGenerateResult }>("generate", {
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
      const result = payload.result;
      setLatestResult(result);
      await loadHistory();
      startTransition(() => {
        setSelectedRecordId(result.record_id);
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : String(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  function handleToggleNsfwEnabled(): void {
    config.updateDraft((current) => ({ ...current, nsfw_enabled: !nsfwEnabled }));
  }

  function handleToggleAddQualityTags(): void {
    config.updateDraft((current) => ({ ...current, add_quality_tags: !addQualityTags }));
  }

  function handleChangeUndesiredContentPreset(value: number): void {
    config.updateDraft((current) => ({ ...current, undesired_content_preset: value }));
  }

  return {
    activeRecord,
    addQualityTags,
    error,
    form,
    history,
    latestResult,
    nsfwEnabled,
    undesiredContentPreset,
    requestSummary,
    roleItems,
    selectedRecordId,
    submitting,
    validationError,
    onChange: (next: Partial<ImageStudioFormState>) => {
      setForm((current) => ({ ...current, ...next }));
    },
    onPickBaseImage: () => void handlePickBaseImage(),
    onSelectRecord: (record: ImageHistoryRecord) => setSelectedRecordId(record.id),
    onSubmit: () => void handleSubmit(),
    onChangeUndesiredContentPreset: (value: number) => handleChangeUndesiredContentPreset(value),
    onToggleAddQualityTags: () => handleToggleAddQualityTags(),
    onToggleNsfwEnabled: () => handleToggleNsfwEnabled(),
  };
}
