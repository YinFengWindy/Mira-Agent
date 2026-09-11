import { useEffect } from "react";
import type { PluginRpcClient } from "../../../apps/desktop/renderer/src/plugins/pluginBridgeClient";
import { ImageStudioPage } from "./ImageStudioPage";
import { PromptTagLibraryPage } from "./PromptTagLibraryPage";
import {
  openPromptTagWorkspaceSection,
  refreshRoles,
  selectActiveHistoryRecord,
  selectRecord,
  setActiveRoleId,
  useNovelAiPageStore,
} from "./novelAiPageStore";

type NovelAIPageProps = {
  client: PluginRpcClient;
  /** The role currently open in chat, if any — see `PluginNavPageProps`. */
  activeRoleId?: string;
};

/**
 * The novelai plugin's single `nav.page` entry: manual generation, the
 * prompt-tag library, and generation history (issue #180). Its sidebar
 * (`NovelAIPageSidebar`, registered alongside this component in
 * `index.tsx`) renders separately into the host's resizable sidebar track
 * (issue #226 gap A) instead of inline here; the two mount points share
 * state through `novelAiPageStore` (see that file's docstring for why).
 *
 * The role picker reads `roles.list` directly through the desktop bridge
 * (not the injected `client`, which is scoped to `plugin.novelai.*` only):
 * there is currently no generic mechanism for a nav.page to receive host
 * lists like this as a prop, and building one is out of scope here.
 *
 * Zero-role guard: the nav rail now refuses to navigate here at all while
 * no role exists, and shows why (`selectBlockedReasonForNovelAiPage`, issue
 * #226 gap B, owner decision: 拦住 + 给提示), restoring the pre-migration
 * `useNavigationHistory.openImageStudio` behaviour and its exact message.
 * That check is necessarily best-effort — it answers synchronously from a
 * locally cached role count that may not have loaded yet on a cold first
 * click, and it is bypassed entirely by history back/forward navigation
 * (`useNavigationHistory.navigateHistory` calls `openPluginPage` directly).
 * The empty-state guard below stays as the real backstop for both cases.
 */
export function NovelAIPage({ client, activeRoleId }: NovelAIPageProps) {
  const store = useNovelAiPageStore();

  useEffect(() => {
    setActiveRoleId(activeRoleId ?? "");
  }, [activeRoleId]);

  useEffect(() => {
    void refreshRoles();
  }, []);

  if (store.rolesLoaded && store.roles.length === 0) {
    return (
      <div className="grid h-full place-items-center bg-gradient-app bg-fixed p-6 text-center text-sm text-ink-muted">
        请先创建至少一个角色，再进入生图。
      </div>
    );
  }

  if (store.view === "prompt-tags") {
    return (
      <PromptTagLibraryPage
        client={client}
        bridgeReady={store.rolesLoaded}
        section={store.promptTagSection}
        onOpenSection={openPromptTagWorkspaceSection}
      />
    );
  }

  return (
    <ImageStudioPage
      activeRecord={selectActiveHistoryRecord(store.history, store.selectedRecordId)}
      error={store.error}
      generating={store.submitting}
      history={store.history}
      latestResult={store.latestResult}
      selectedRecordId={store.selectedRecordId}
      onSelectRecord={(record) => selectRecord(record.id)}
    />
  );
}
