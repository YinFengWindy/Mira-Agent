/** Time limits shared by the Electron bridge command boundary. */
export const bridgeTimeoutPolicy = Object.freeze({
  health: 5_000,
  startup: 60_000,
  defaultRequest: 30_000,
  voiceRequest: 30_000,
  imageGeneration: 5 * 60_000,
  observation: 2 * 60_000,
  gracefulStop: 5_000,
  forcedStop: 2_000,
});

const imageGenerationMethods = new Set([
  // Issue #180: novelai's generation methods moved onto the plugin RPC
  // namespace (plugin.<id>.<method>), called through the injected
  // PluginRpcClient which always prefixes with "plugin.novelai.".
  "plugin.novelai.generate",
  "plugin.novelai.regenerateMessageMedia",
  "roles.differences.generate",
]);

/** Returns a deadline, or null for a transaction that must await its committed outcome. */
export function bridgeRequestTimeoutMs(method: string): number | null {
  if (method === "runtime.apply") return null;
  if (method === "health") return bridgeTimeoutPolicy.health;
  if (imageGenerationMethods.has(method)) return bridgeTimeoutPolicy.imageGeneration;
  if (method === "observation.analyze") return bridgeTimeoutPolicy.observation;
  if (method.startsWith("voice.")) return bridgeTimeoutPolicy.voiceRequest;
  return bridgeTimeoutPolicy.defaultRequest;
}
