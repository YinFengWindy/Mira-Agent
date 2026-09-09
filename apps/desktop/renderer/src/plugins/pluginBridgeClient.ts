import type { JsonSchema } from "./jsonSchemaForm";

type DesktopInvoke = typeof window.miraDesktop.invoke;

/** Stable error exposed by the plugin bridge client. */
export class PluginBridgeError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "PluginBridgeError";
  }
}

export type PluginConfigSnapshot = {
  pluginId: string;
  schema: JsonSchema | null;
  values: Record<string, unknown>;
};

export type PluginConfigSaveResult = {
  pluginId: string;
  values: Record<string, unknown>;
  generation: number;
};

/** One row of the plugin management list (`plugins.list`). */
export type PluginSummary = {
  id: string;
  name: string;
  version: string;
  description: string;
  enabled: boolean;
  state: string;
  error: string;
  hasConfigSchema: boolean;
};

export type PluginSetEnabledResult = {
  pluginId: string;
  enabled: boolean;
  generation: number;
};

async function invokePayload<T>(invoke: DesktopInvoke, method: string, payload: Record<string, unknown>): Promise<T> {
  const response = await invoke({ method, payload });
  if (response.error) throw new PluginBridgeError(response.error.message, response.error.code, response.error.details);
  return response.payload as T;
}

/** Calls the `plugin.config.*` and `plugins.*` management bridge contracts. */
export interface PluginBridgeClient {
  getConfig(pluginId: string): Promise<PluginConfigSnapshot>;
  setConfig(
    pluginId: string,
    values: Record<string, unknown>,
    options: { operationId: string },
  ): Promise<PluginConfigSaveResult>;
  listPlugins(): Promise<PluginSummary[]>;
  setEnabled(
    pluginId: string,
    enabled: boolean,
    options: { operationId: string },
  ): Promise<PluginSetEnabledResult>;
}

/** Creates the renderer client for the plugin config and management bounded context. */
export function createPluginBridgeClient(invoke: DesktopInvoke = window.miraDesktop.invoke): PluginBridgeClient {
  return {
    async getConfig(pluginId) {
      const payload = await invokePayload<{ plugin_id: string; schema: JsonSchema | null; values: Record<string, unknown> }>(
        invoke, "plugin.config.get", { plugin_id: pluginId },
      );
      return { pluginId: payload.plugin_id, schema: payload.schema, values: payload.values };
    },
    async setConfig(pluginId, values, options) {
      const payload = await invokePayload<{ plugin_id: string; values: Record<string, unknown>; generation: number }>(
        invoke, "plugin.config.set", { plugin_id: pluginId, values, operation_id: options.operationId },
      );
      return { pluginId: payload.plugin_id, values: payload.values, generation: payload.generation };
    },
    async listPlugins() {
      const payload = await invokePayload<{ plugins: Array<{
        id: string; name: string; version: string; description: string;
        enabled: boolean; state: string; error: string; has_config_schema: boolean;
      }> }>(invoke, "plugins.list", {});
      return payload.plugins.map((item) => ({
        id: item.id,
        name: item.name,
        version: item.version,
        description: item.description,
        enabled: item.enabled,
        state: item.state,
        error: item.error,
        hasConfigSchema: item.has_config_schema,
      }));
    },
    async setEnabled(pluginId, enabled, options) {
      const payload = await invokePayload<{ plugin_id: string; enabled: boolean; generation: number }>(
        invoke, "plugins.setEnabled", { plugin_id: pluginId, enabled, operation_id: options.operationId },
      );
      return { pluginId: payload.plugin_id, enabled: payload.enabled, generation: payload.generation };
    },
  };
}

/** Creates a client scoped to one plugin's own `plugin.<id>.*` RPC namespace. */
export function createPluginRpcClient(pluginId: string, invoke: DesktopInvoke = window.miraDesktop.invoke) {
  return {
    async call<T>(method: string, payload: Record<string, unknown> = {}): Promise<T> {
      return invokePayload<T>(invoke, `plugin.${pluginId}.${method}`, payload);
    },
  };
}
