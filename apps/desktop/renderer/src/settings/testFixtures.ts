import type { SettingsFormData } from "../../../src/bridge/shared.js";

/** Builds independent complete settings drafts for transaction tests. */
export function createSettingsDraft(): SettingsFormData {
  return {
    models: { registrations: [] },
    channels: { telegramToken: "", qqBotUin: "", qqBotAppId: "", qqBotClientSecret: "" },
    memory: { enabled: false, engine: "default", embeddingModel: "", embeddingApiKey: "", embeddingBaseUrl: "", outputDimensionality: "" },
    integrations: { novelaiEnabled: false, novelaiToken: "", novelaiNsfwEnabled: false, novelaiAddQualityTags: false, novelaiUndesiredContentPreset: 0, novelaiAutoWritebackRoleAssets: false },
    voice: { enabled: false, hotkey: "Ctrl+Space", microphoneDeviceId: "", asrProvider: "tencent", asrBaseUrl: "", asrSecretId: "", asrSecretKey: "", ttsProvider: "minimax", ttsBaseUrl: "", ttsModel: "", ttsApiKey: "", ttsVolume: 2 },
    advanced: { maxTokens: 4000, maxIterations: 10, devMode: false, streamingEnabled: false, memoryWindow: 20, searchEnabled: true, spawnEnabled: true, memoryOptimizerEnabled: false, memoryOptimizerIntervalSeconds: 3600, pluginsRawToml: "" },
  };
}
