import { randomUUID } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";

import type {
  ModelRegistrationFormData,
  RuntimeApplyRequest,
  SaveSettingsResult,
  SettingsFormData,
  SettingsSaveOptions,
  SettingsSnapshot,
} from "./bridge/shared.js";
import { parseHotkey } from "./voice/hotkey.js";
import { desktopSettingsDefaults } from "./settingsContract.js";

type RuntimeSettingsApplier = (request: RuntimeApplyRequest) => Promise<SaveSettingsResult>;

let configPath: string | null = null;

/** Sets the user-writable configuration path before settings or the bridge are initialized. */
export function configureSettingsConfigPath(path: string): void {
  configPath = path;
}

function requireConfigPath(): string {
  if (!configPath) {
    throw new Error("桌面配置路径尚未初始化");
  }
  return configPath;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function parseTomlValue(raw: string): unknown {
  const value = raw.trim();
  if (value.startsWith("\"") && value.endsWith("\"")) {
    return JSON.parse(value);
  }
  if (value === "true") return true;
  if (value === "false") return false;
  if (/^-?\d+(\.\d+)?$/.test(value)) return Number(value);
  if (value.startsWith("[") && value.endsWith("]")) {
    return JSON.parse(value);
  }
  return value;
}

function parseToml(content: string): Record<string, unknown> {
  const root: Record<string, unknown> = {};
  let current = root;

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    if (line.startsWith("[[") && line.endsWith("]]")) {
      const path = line.slice(2, -2).trim().split(".");
      let cursor: Record<string, unknown> = root;
      for (let index = 0; index < path.length - 1; index += 1) {
        const segment = path[index]!;
        const next = asRecord(cursor[segment]);
        cursor[segment] = next;
        cursor = next;
      }
      const key = path[path.length - 1]!;
      const list = Array.isArray(cursor[key])
        ? (cursor[key] as Record<string, unknown>[])
        : [];
      const entry: Record<string, unknown> = {};
      list.push(entry);
      cursor[key] = list;
      current = entry;
      continue;
    }

    if (line.startsWith("[") && line.endsWith("]")) {
      const path = line.slice(1, -1).trim().split(".");
      let cursor: Record<string, unknown> = root;
      for (const segment of path) {
        const next = asRecord(cursor[segment]);
        cursor[segment] = next;
        cursor = next;
      }
      current = cursor;
      continue;
    }

    const separatorIndex = line.indexOf("=");
    if (separatorIndex < 0) continue;
    const key = line.slice(0, separatorIndex).trim();
    const rawValue = line.slice(separatorIndex + 1).trim();
    current[key] = parseTomlValue(rawValue);
  }

  return root;
}

function quote(value: string): string {
  return JSON.stringify(value ?? "");
}

function renderStringArray(values: string[]): string {
  return `[${values.map((item) => quote(item)).join(", ")}]`;
}

function renderPluginBlocks(rawToml: string): string {
  const trimmed = rawToml.trim();
  return trimmed ? `${trimmed}\n` : "";
}

function renderPluginSection(name: string, value: Record<string, unknown>): string {
  const lines = [`[plugins.${name}]`];
  for (const [key, rawValue] of Object.entries(value)) {
    if (Array.isArray(rawValue)) {
      lines.push(
        `${key} = ${renderStringArray(rawValue.map((item) => String(item ?? "")))}`,
      );
      continue;
    }
    if (typeof rawValue === "boolean") {
      lines.push(`${key} = ${rawValue ? "true" : "false"}`);
      continue;
    }
    if (typeof rawValue === "number") {
      lines.push(`${key} = ${rawValue}`);
      continue;
    }
    lines.push(`${key} = ${quote(String(rawValue ?? ""))}`);
  }
  return lines.join("\n");
}

function optionalBoolean(value: unknown, field: string): boolean | undefined {
  if (value === undefined || typeof value === "boolean") return value;
  throw new Error(`${field} 必须是布尔值`);
}

function loadProactiveStrategies(values: Record<string, unknown>): SettingsFormData["proactiveStrategies"] {
  const sceneFollowup = optionalBoolean(values.scene_followup, "agent.proactive_strategies.scene_followup");
  const relationship = optionalBoolean(values.relationship, "agent.proactive_strategies.relationship");
  // Absence is meaningful: the backend may still need to migrate a legacy disabled marker.
  return {
    ...(sceneFollowup === undefined ? {} : { sceneFollowup }),
    ...(relationship === undefined ? {} : { relationship }),
  };
}

function renderProactiveStrategies(values: SettingsFormData["proactiveStrategies"]): string[] {
  const lines: string[] = [];
  if (values.sceneFollowup !== undefined) lines.push(`scene_followup = ${values.sceneFollowup}`);
  if (values.relationship !== undefined) lines.push(`relationship = ${values.relationship}`);
  return lines.length ? ["[agent.proactive_strategies]", ...lines, ""] : [];
}

function loadModelRegistrations(llm: Record<string, unknown>): ModelRegistrationFormData[] {
  const raw = Array.isArray(llm.registrations) ? llm.registrations : [];
  return raw.map((value) => {
    const item = asRecord(value);
    return {
      id: String(item.id ?? ""),
      provider: String(item.provider ?? "openai"),
      baseUrl: String(item.base_url ?? ""),
      apiKey: String(item.api_key ?? ""),
      model: String(item.model ?? ""),
      effort: String(item.effort ?? "none") as "none" | "low" | "high" | "max",
    };
  });
}

/** Reads persisted settings without requiring a model or a running bridge. */
export function loadSettingsData(contentOverride?: string): SettingsSnapshot {
  const configuredPath = requireConfigPath();
  const content = contentOverride ?? (existsSync(configuredPath) ? readFileSync(configuredPath, "utf-8") : "");
  const parsed = parseToml(content);
  const llm = asRecord(parsed.llm);
  const channels = asRecord(parsed.channels);
  const telegram = asRecord(channels.telegram);
  const qq = asRecord(channels.qq);
  const memory = asRecord(parsed.memory);
  const embedding = asRecord(memory.embedding);
  const agent = asRecord(parsed.agent);
  const agentContext = asRecord(agent.context);
  const agentTools = asRecord(agent.tools);
  const agentMaintenance = asRecord(agent.maintenance);
  const proactiveStrategies = asRecord(agent.proactive_strategies);
  const voice = asRecord(parsed.voice);
  const voiceAsr = asRecord(voice.asr);
  const voiceTts = asRecord(voice.tts);
  const plugins = asRecord(parsed.plugins);
  return {
    configPath: configuredPath,
    formData: {
      proactiveStrategies: loadProactiveStrategies(proactiveStrategies),
      models: {
        registrations: loadModelRegistrations(llm),
      },
      channels: {
        telegramToken: String(telegram.token ?? ""),
        qqBotUin: String(qq.bot_uin ?? ""),
      },
      memory: {
        enabled: Boolean(memory.enabled),
        engine: String(memory.engine ?? ""),
        embeddingModel: String(embedding.model ?? ""),
        embeddingApiKey: String(embedding.api_key ?? ""),
        embeddingBaseUrl: String(embedding.base_url ?? ""),
        outputDimensionality:
          embedding.output_dimensionality == null
            ? ""
            : String(embedding.output_dimensionality),
      },
      voice: {
        enabled: Boolean(voice.enabled),
        hotkey: String(voice.hotkey ?? "Ctrl+Space"),
        microphoneDeviceId: String(voice.microphone_device_id ?? ""),
        asrEnabled: Boolean(voiceAsr.enabled ?? voice.enabled),
        asrProvider: String(voiceAsr.provider ?? desktopSettingsDefaults.asrProvider),
        asrBaseUrl: String(voiceAsr.base_url ?? desktopSettingsDefaults.asrBaseUrl),
        asrSecretId: String(voiceAsr.secret_id ?? ""),
        asrSecretKey: String(voiceAsr.secret_key ?? ""),
        ttsEnabled: Boolean(voiceTts.enabled ?? voice.enabled),
        ttsProvider: String(voiceTts.provider ?? desktopSettingsDefaults.ttsProvider),
        ttsBaseUrl: String(voiceTts.base_url ?? desktopSettingsDefaults.ttsBaseUrl),
        ttsModel: String(voiceTts.model ?? desktopSettingsDefaults.ttsModel),
        ttsApiKey: String(voiceTts.api_key ?? ""),
        ttsVolume: Number(voiceTts.volume ?? desktopSettingsDefaults.ttsVolume),
      },
      advanced: {
        maxTokens: Number(agent.max_tokens ?? 8192),
        maxIterations: Number(agent.max_iterations ?? 40),
        devMode: Boolean(agent.dev_mode),
        streamingEnabled: Boolean(asRecord(asRecord(parsed.desktop).chat).streaming_enabled),
        memoryWindow: Number(agentContext.memory_window ?? 40),
        searchEnabled: Boolean(agentTools.search_enabled),
        spawnEnabled: Boolean(agentTools.spawn_enabled ?? true),
        memoryOptimizerEnabled: Boolean(
          agentMaintenance.memory_optimizer_enabled ?? true,
        ),
        memoryOptimizerIntervalSeconds: Number(
          agentMaintenance.memory_optimizer_interval_seconds ?? 64800,
        ),
        // feishu is excluded because that surface was retired from the runtime
        // (the backend rejects [plugins.feishu] outright). qqbot used to be
        // excluded too, back when its app_id/client_secret had a bespoke
        // round-trip through channels.qqBot*; now that it owns a schema-driven
        // settings.section (plugins/qqbot/ui/index.tsx) instead, it flows
        // through this generic catch-all like any other plugin without
        // dedicated UI (#183) — dropping it here would silently lose
        // [plugins.qqbot] on the next unrelated settings save, since this
        // whole document is rebuilt from formData on every save.
        pluginsRawToml: renderPluginBlocks(
          Object.entries(plugins)
            .filter(([name]) => name !== "feishu")
            .map(([name, value]) => renderPluginSection(name, asRecord(value)))
            .join("\n"),
        ).trimEnd(),
      },
    },
  };
}

function renderSettingsToml(formData: SettingsFormData): string {
  const outputDimensionality = formData.memory.outputDimensionality.trim();

  return [
    "[llm]",
    ...(formData.models.registrations.length === 0 ? ["registrations = []"] : []),
    "",
    ...formData.models.registrations.flatMap((registration) => [
      "[[llm.registrations]]",
      `id = ${quote(registration.id)}`,
      `provider = ${quote(registration.provider.trim())}`,
      `base_url = ${quote(registration.baseUrl.trim())}`,
      `api_key = ${quote(registration.apiKey)}`,
      `model = ${quote(registration.model.trim())}`,
      `effort = ${quote(registration.effort)}`,
      "",
    ]),
    "[agent]",
    `max_tokens = ${formData.advanced.maxTokens}`,
    `max_iterations = ${formData.advanced.maxIterations}`,
    `dev_mode = ${formData.advanced.devMode ? "true" : "false"}`,
    "",
    "[desktop.chat]",
    `streaming_enabled = ${formData.advanced.streamingEnabled ? "true" : "false"}`,
    "",
    ...renderProactiveStrategies(formData.proactiveStrategies),
    "[agent.context]",
    `memory_window = ${formData.advanced.memoryWindow}`,
    "",
    "[agent.tools]",
    `search_enabled = ${formData.advanced.searchEnabled ? "true" : "false"}`,
    `spawn_enabled = ${formData.advanced.spawnEnabled ? "true" : "false"}`,
    "",
    "[agent.maintenance]",
    `memory_optimizer_enabled = ${
      formData.advanced.memoryOptimizerEnabled ? "true" : "false"
    }`,
    `memory_optimizer_interval_seconds = ${formData.advanced.memoryOptimizerIntervalSeconds}`,
    "",
    "[agent.wiring]",
    'context = "default"',
    'memory = "default"',
    "toolsets = []",
    "",
    "[channels.telegram]",
    `token = ${quote(formData.channels.telegramToken)}`,
    'channel_name = "telegram"',
    "",
    "[channels.qq]",
    `bot_uin = ${quote(formData.channels.qqBotUin)}`,
    "websocket_open_timeout_seconds = 5",
    "",
    "[memory]",
    `enabled = ${formData.memory.enabled ? "true" : "false"}`,
    `engine = ${quote(formData.memory.engine)}`,
    "",
    "[memory.embedding]",
    `model = ${quote(formData.memory.embeddingModel)}`,
    `api_key = ${quote(formData.memory.embeddingApiKey)}`,
    `base_url = ${quote(formData.memory.embeddingBaseUrl)}`,
    outputDimensionality
      ? `output_dimensionality = ${Number(outputDimensionality)}`
      : "",
    "",
    "[voice]",
    `enabled = ${formData.voice.enabled ? "true" : "false"}`,
    `hotkey = ${quote(formData.voice.hotkey.trim())}`,
    `microphone_device_id = ${quote(formData.voice.microphoneDeviceId.trim())}`,
    "",
    "[voice.asr]",
    `provider = ${quote(formData.voice.asrProvider.trim())}`,
    `base_url = ${quote(formData.voice.asrBaseUrl.trim())}`,
    `enabled = ${(formData.voice.asrEnabled ?? formData.voice.enabled) ? "true" : "false"}`,
    `secret_id = ${quote(formData.voice.asrSecretId)}`,
    `secret_key = ${quote(formData.voice.asrSecretKey)}`,
    "",
    "[voice.tts]",
    `provider = ${quote(formData.voice.ttsProvider.trim())}`,
    `base_url = ${quote(formData.voice.ttsBaseUrl.trim())}`,
    `model = ${quote(formData.voice.ttsModel.trim())}`,
    `enabled = ${(formData.voice.ttsEnabled ?? formData.voice.enabled) ? "true" : "false"}`,
    `api_key = ${quote(formData.voice.ttsApiKey)}`,
    `volume = ${formData.voice.ttsVolume}`,
    "",
    formData.advanced.pluginsRawToml.trim(),
    "",
  ]
    .filter((line, index, array) => {
      if (line !== "") return true;
      return index > 0 && array[index - 1] !== "";
    })
    .join("\n")
    .trim()
    .concat("\n");
}

function validateSettings(formData: SettingsFormData): void {
  const registrationIds = new Set<string>();
  for (const registration of formData.models.registrations) {
    if (!registration.id) {
      throw new Error("模型注册 ID 不能为空");
    }
    if (registrationIds.has(registration.id)) {
      throw new Error("模型注册 ID 不能重复");
    }
    if (!["none", "low", "high", "max"].includes(registration.effort)) {
      throw new Error("Effort 必须是 none、low、high 或 max");
    }
    registrationIds.add(registration.id);
  }
  if (formData.advanced.maxTokens <= 0) {
    throw new Error("max_tokens 必须大于 0");
  }
  if (formData.advanced.maxIterations < 0) {
    throw new Error("max_iterations 不能小于 0");
  }
  if (formData.memory.outputDimensionality.trim()) {
    const value = Number(formData.memory.outputDimensionality);
    if (!Number.isInteger(value) || value <= 0) {
      throw new Error("embedding output_dimensionality 必须是正整数");
    }
  }
  if (formData.voice.enabled && !parseHotkey(formData.voice.hotkey)) {
    throw new Error("语音快捷键格式无效");
  }
  if (!["tencent"].includes(formData.voice.asrProvider.trim())) {
    throw new Error("ASR Provider 不受支持");
  }
  if (!["minimax"].includes(formData.voice.ttsProvider.trim())) {
    throw new Error("TTS Provider 不受支持");
  }
  if (!Number.isFinite(formData.voice.ttsVolume) || formData.voice.ttsVolume < 0.1 || formData.voice.ttsVolume > 10) {
    throw new Error("TTS 音量必须在 0.1 到 10.0 之间");
  }
}

/** Submits a candidate configuration; only the backend transaction writes the file. */
export async function saveSettings(
  formData: SettingsFormData,
  applySettings: RuntimeSettingsApplier,
  options: SettingsSaveOptions = {},
): Promise<SaveSettingsResult> {
  try {
    validateSettings(formData);
  } catch (error) {
    return { ok: false, error: { code: "settings_validation_error", message: error instanceof Error ? error.message : String(error) } };
  }
  return applySettings({
    config_toml: renderSettingsToml(formData),
    expected_generation: options.expectedGeneration,
    operation_id: options.operationId ?? randomUUID(),
    role_model_updates: (formData.pendingRoleModelUpdates ?? []).map((update) => ({
      role_id: update.roleId,
      runtime_config: update.runtimeConfig,
    })),
  });
}
