import type { SettingsSnapshot } from "../../src/bridge/shared";

/** Installs a persistent fake bridge before the renderer loads; state survives page reloads. */
export function installOnboardingFakeBridge(initial: SettingsSnapshot) {
  const stateKey = "qa.onboarding.bridge";
  const state = JSON.parse(localStorage.getItem(stateKey) ?? "null") ?? {
    settings: initial, roles: [], sessionId: "launch-1", offline: false, failCreate: false, failSave: false, createCalls: 0,
  };
  const persist = () => localStorage.setItem(stateKey, JSON.stringify(state));
  persist();
  window.addEventListener("qa:bridge", (event) => { Object.assign(state, (event as CustomEvent).detail); persist(); });
  const listeners = new Set<(event: unknown) => void>();
  const role = (fields: Record<string, unknown>) => ({
    id: "qa-role", name: fields.name, description: fields.description, system_prompt: fields.system_prompt,
    runtime_config: {}, channel_bindings: [], avatar: fields.avatar_source ?? null, avatar_abs: fields.avatar_source ?? null,
    chat_background: null, chat_background_abs: null, illustrations: [], illustrations_abs: [],
    asset_categories: [{ id: "default", name: "Default", allow_role_send: false }], asset_category_bindings: {},
    created_at: "2026-09-08T00:00:00Z", updated_at: "2026-09-08T00:00:00Z",
  });
  const fail = (message: string) => ({ code: "qa_failure", message });
  Object.defineProperty(window, "miraDesktop", { configurable: true, value: {
    applicationSessionId: async () => state.sessionId,
    onEvent: (callback: (event: unknown) => void) => { listeners.add(callback); return () => listeners.delete(callback); },
    windowState: async () => ({ isMaximized: false, isVisible: true }),
    windowControl: async () => undefined,
    bridgeStatus: async () => ({ running: !state.offline, lastError: state.offline ? "测试连接失败" : null }),
    restartBridge: async () => ({ ok: !state.offline, running: !state.offline, lastError: state.offline ? "测试连接失败" : null }),
    readSettings: async () => { if (state.offline) throw new Error("测试连接失败"); return structuredClone(state.settings); },
    saveSettings: async (formData: SettingsSnapshot["formData"]) => {
      if (state.failSave) return { ok: false, error: fail("测试模型保存失败") };
      state.settings = { ...state.settings, formData, generation: (state.settings.generation ?? 0) + 1 };
      persist();
      return { ok: true, generation: state.settings.generation, changed: true };
    },
    invoke: async ({ method, payload }: { method: string; payload: Record<string, unknown> }) => {
      let result: Record<string, unknown> = {};
      let error = state.offline ? fail("测试连接失败") : null;
      if (!error) {
        if (method === "roles.list") result = { roles: state.roles };
        if (method === "roles.create") {
          state.createCalls += 1;
          if (state.failCreate) error = fail("测试头像保存失败");
          else {
            const created = role(payload);
            state.roles.push(created);
            result = { role: created };
            if (state.failReadsAfterCreate) state.offline = true;
          }
          persist();
        }
        if (method === "session.openByRole") result = { session: { key: `role:${payload.role_id}`, last_consolidated: 0,
          messages: [], metadata: { role_id: payload.role_id }, created_at: "2026-09-08T00:00:00Z", updated_at: "2026-09-08T00:00:00Z" },
          page: { messages: [], limit: 50, has_more: false, oldest_seq: null, newest_seq: null, total_count: 0, before_seq: null, next_before_seq: null } };
        if (method === "roles.tasks.list") result = { tasks: [] };
      }
      return { id: "qa", type: "response", method, payload: result, error };
    },
    pickImages: async () => ["qa-avatar"],
    localAssetUrl: () => "/qa-avatar.png",
    reportRendererDiagnostic: () => undefined,
    onVoiceState: () => () => undefined,
  } });
}
