import { useSyncExternalStore } from "react";
import type { PluginRpcClient } from "../../../apps/desktop/renderer/src/plugins/pluginBridgeClient";
import type { RoleRecord } from "../../../apps/desktop/renderer/src/shared/types";
import type { PromptTagWorkspaceSectionId } from "./PromptTagWorkspaceSidebar";
import type { ImageGenerateResult, ImageHistoryRecord } from "./types";

export type NovelAiView = "studio" | "prompt-tags";

type NovelAiPageState = {
  view: NovelAiView;
  promptTagSection: PromptTagWorkspaceSectionId;
  /** Mirrors `PluginNavPageProps.activeRoleId` — relayed here so the Sidebar mount point (which the host does not inject it into) can read it too. */
  activeRoleId: string;
  roles: RoleRecord[];
  /** Whether `roles` reflects a real fetch yet, vs. the initial empty placeholder. */
  rolesLoaded: boolean;
  submitting: boolean;
  history: ImageHistoryRecord[];
  selectedRecordId: string;
  latestResult: ImageGenerateResult | null;
  error: string;
};

// This plugin's `nav.page` entry now has two mount points that render as
// siblings under the host's `DesktopAppFrame` (the page in `<main>`, its
// Sidebar in the host's resizable track — see issue #226 gap A/B). They are
// not a React context away from each other (the host owns everything in
// between), so state either of them can both read and write — which role's
// generation history is showing, which prompt-tag section is open, the
// roster of roles used for both the role picker and the nav-rail
// `selectBlockedReason` guard — has to live outside either component. A module-level
// store notified via `useSyncExternalStore` is the smallest thing that
// works for two components the host may mount/unmount independently,
// without asking the host to plumb cross-slot state (issue #226 explicitly
// rules that out).
//
// Deliberately NOT shared here: the generation form fields and the NSFW/
// quality-tag/undesired-content config toggles. Only the Sidebar reads or
// writes those, so they stay local `useState`/`usePluginConfigController`
// state inside `NovelAIPageSidebar` — per AGENTS.md, this store only holds
// what genuinely crosses the two mount points.
function initialState(): NovelAiPageState {
  return {
    view: "studio",
    promptTagSection: "list",
    activeRoleId: "",
    roles: [],
    rolesLoaded: false,
    submitting: false,
    history: [],
    selectedRecordId: "",
    latestResult: null,
    error: "",
  };
}

let state: NovelAiPageState = initialState();
const listeners = new Set<() => void>();

function commit(next: NovelAiPageState): void {
  state = next;
  for (const listener of listeners) listener();
}

function getSnapshot(): NovelAiPageState {
  return state;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Subscribes a component to every field of the shared novelai page state. */
export function useNovelAiPageStore(): NovelAiPageState {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export function setView(view: NovelAiView): void {
  if (state.view === view) return;
  commit({ ...state, view });
}

export function openPromptTagLibrary(): void {
  setView("prompt-tags");
}

export function backToStudio(): void {
  setView("studio");
}

export function setPromptTagSection(section: PromptTagWorkspaceSectionId): void {
  if (state.promptTagSection === section) return;
  commit({ ...state, promptTagSection: section });
}

/** Used by the main page's content (`PromptTagLibraryPage`), which can also navigate back to "list" from a state where the sidebar isn't showing prompt-tags yet. */
export function openPromptTagWorkspaceSection(section: PromptTagWorkspaceSectionId): void {
  if (section === "list") setView("prompt-tags");
  setPromptTagSection(section);
}

/** Relays the host's `activeRoleId` prop (only given to the page component) into the shared store so the Sidebar mount point can see it too. */
export function setActiveRoleId(nextActiveRoleId: string): void {
  if (state.activeRoleId === nextActiveRoleId) return;
  commit({
    ...state,
    activeRoleId: nextActiveRoleId,
    error: "",
    latestResult: null,
  });
}

let rolesInflight: Promise<void> | null = null;

/**
 * Fetches the role roster via the host bridge (not the plugin's own `client`
 * — `roles.list` is a host method, matching the pre-existing exception
 * documented on `NovelAIPage`). Always re-fetches (this plugin page's data
 * can go stale while the page is closed), but concurrent callers within one
 * in-flight request share it instead of issuing duplicate calls.
 */
export async function refreshRoles(): Promise<void> {
  if (rolesInflight) return rolesInflight;
  rolesInflight = (async () => {
    try {
      const response = await window.miraDesktop.invoke({ method: "roles.list", payload: {} });
      const roles = !response.error && Array.isArray(response.payload?.roles)
        ? (response.payload.roles as RoleRecord[])
        : state.roles;
      commit({ ...state, roles, rolesLoaded: true });
    } finally {
      rolesInflight = null;
    }
  })();
  return rolesInflight;
}

/**
 * The exact string the pre-migration `useNavigationHistory.openImageStudio`
 * passed to `setError` for this same check — kept verbatim now that a
 * refusal is shown again (owner decision: 拦住 + 给提示, not silent).
 */
const ZERO_ROLES_BLOCKED_REASON = "请先创建至少一个角色，再进入生图。";

/**
 * Synchronous nav-rail guard (issue #226 gap B): refuses to navigate into
 * this page while zero roles exist, matching the pre-migration
 * `useNavigationHistory.openImageStudio` check and its message.
 * `selectBlockedReason` must return synchronously, so a role fetch already
 * in flight or just kicked off here cannot be awaited; before the roster
 * has ever loaded this fails *open* (returns `null`, permits navigation)
 * rather than closed, because the in-page empty state (`NovelAIPage`) is
 * kept as a safety net for exactly this race — silently letting a
 * zero-role user in once on a cold first click is a harmless one-time
 * flash of that empty state, not a real regression.
 */
export function selectBlockedReasonForNovelAiPage(): string | null {
  void refreshRoles();
  if (!state.rolesLoaded || state.roles.length > 0) return null;
  return ZERO_ROLES_BLOCKED_REASON;
}

export async function loadHistory(client: PluginRpcClient, roleId: string): Promise<void> {
  try {
    const payload = await client.call<{ records: ImageHistoryRecord[] }>("history", {
      role_id: roleId,
      limit: 24,
    });
    const records = Array.isArray(payload.records) ? payload.records : [];
    const selectedRecordId = records.some((record) => record.id === state.selectedRecordId)
      ? state.selectedRecordId
      : (records[0]?.id ?? "");
    commit({ ...state, history: records, selectedRecordId });
  } catch (loadError) {
    commit({ ...state, error: loadError instanceof Error ? loadError.message : String(loadError) });
  }
}

/** Submits a generation request already fully resolved by the Sidebar (model/mode/role id etc.), then refreshes history for the same role. */
export async function submitGenerate(client: PluginRpcClient, payload: Record<string, unknown>): Promise<void> {
  commit({ ...state, submitting: true, error: "" });
  try {
    const response = await client.call<{ result: ImageGenerateResult }>("generate", payload);
    const result = response.result;
    commit({ ...state, submitting: false, latestResult: result });
    await loadHistory(client, String(payload.role_id ?? ""));
    commit({ ...state, selectedRecordId: result.record_id });
  } catch (submitError) {
    commit({ ...state, submitting: false, error: submitError instanceof Error ? submitError.message : String(submitError) });
  }
}

export function selectRecord(recordId: string): void {
  if (state.selectedRecordId === recordId) return;
  commit({ ...state, selectedRecordId: recordId });
}

/** Test-only: resets every module-level field so each test starts from a clean store. */
export function resetNovelAiPageStoreForTests(): void {
  state = initialState();
  rolesInflight = null;
}

/** Test-only: a synchronous read outside React, for assertions between store calls. */
export function __getSnapshotForTests(): NovelAiPageState {
  return state;
}
