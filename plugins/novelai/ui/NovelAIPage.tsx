import { useEffect, useState } from "react";
import type { PluginRpcClient } from "../../../apps/desktop/renderer/src/plugins/pluginBridgeClient";
import type { RoleRecord } from "../../../apps/desktop/renderer/src/shared/types";
import { ImageStudioPage } from "./ImageStudioPage";
import { ImageStudioSidebar } from "./ImageStudioSidebar";
import { PromptTagLibraryPage } from "./PromptTagLibraryPage";
import { PromptTagWorkspaceSidebar, type PromptTagWorkspaceSectionId } from "./PromptTagWorkspaceSidebar";
import { useImageStudioState } from "./useImageStudioState";

type NovelAIPageProps = {
  client: PluginRpcClient;
  /** The role currently open in chat, if any — see `PluginNavPageProps`. */
  activeRoleId?: string;
};

type ViewId = "studio" | "prompt-tags";

/**
 * The novelai plugin's single `nav.page` entry: manual generation, the
 * prompt-tag library, and generation history, composed as one self-contained
 * page (issue #180). Previously these were three of the desktop shell's
 * built-in views (`image-studio` / `image-prompt-tags`, with a dedicated
 * resizable sidebar track owned by the app frame); now the plugin owns its
 * own layout end to end, so the sidebar here is fixed-width instead of
 * drag-resizable (see ImageStudioPage's docstring).
 *
 * The role picker reads `roles.list` directly through the desktop bridge
 * (not the injected `client`, which is scoped to `plugin.novelai.*` only):
 * there is currently no generic mechanism for a nav.page to receive host
 * lists like this as a prop, and building one is out of scope here.
 *
 * Zero-role guard: pre-migration, the nav rail's "生图" button itself
 * refused to navigate (and showed a toast) when no role existed yet, via a
 * check inside `useNavigationHistory.openImageStudio`. The `nav.page`
 * registry (#179) has no equivalent hook — `NavPageEntry`/
 * `PluginNavPageContribution` are static (label/icon/Component fixed at
 * plugin-UI-module registration, before any role exists), so there is no
 * way to make the rail entry conditionally unselectable or to intercept its
 * `onSelect` from plugin code. What this page restores instead is the
 * underlying guarantee (you cannot reach the generation form without a
 * role): the nav icon stays clickable, but the page itself renders a
 * guidance message in place of the studio/library UI until at least one
 * role exists.
 */
export function NovelAIPage({ client, activeRoleId }: NovelAIPageProps) {
  const [view, setView] = useState<ViewId>("studio");
  const [promptTagSection, setPromptTagSection] = useState<PromptTagWorkspaceSectionId>("list");
  const [roles, setRoles] = useState<RoleRecord[]>([]);
  const [bridgeReady, setBridgeReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await window.miraDesktop.invoke({ method: "roles.list", payload: {} });
      if (cancelled) return;
      if (!response.error && Array.isArray(response.payload?.roles)) {
        setRoles(response.payload.roles as RoleRecord[]);
      }
      setBridgeReady(true);
    })();
    return () => { cancelled = true; };
  }, []);

  const activeRole = roles.find((role) => role.id === activeRoleId) ?? null;
  const state = useImageStudioState({ client, activeRole, roles });

  if (bridgeReady && roles.length === 0) {
    return (
      <div className="grid h-full place-items-center bg-gradient-app bg-fixed p-6 text-center text-sm text-ink-muted">
        请先创建至少一个角色，再进入生图。
      </div>
    );
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[240px_minmax(0,1fr)]">
      {view === "prompt-tags" ? (
        <PromptTagWorkspaceSidebar
          activeSection={promptTagSection}
          onOpenSection={setPromptTagSection}
          onBackToStudio={() => setView("studio")}
        />
      ) : (
        <ImageStudioSidebar
          bridgeReady={bridgeReady}
          form={state.form}
          nsfwEnabled={state.nsfwEnabled}
          addQualityTags={state.addQualityTags}
          undesiredContentPreset={state.undesiredContentPreset}
          roleItems={state.roleItems}
          submitting={state.submitting}
          validationError={state.validationError}
          onOpenPromptTagLibrary={() => setView("prompt-tags")}
          onChange={state.onChange}
          onPickBaseImage={state.onPickBaseImage}
          onSubmit={state.onSubmit}
          onToggleAddQualityTags={state.onToggleAddQualityTags}
          onChangeUndesiredContentPreset={state.onChangeUndesiredContentPreset}
          onToggleNsfwEnabled={state.onToggleNsfwEnabled}
        />
      )}
      <div className="min-h-0">
        {view === "prompt-tags" ? (
          <PromptTagLibraryPage
            client={client}
            bridgeReady={bridgeReady}
            section={promptTagSection}
            onOpenSection={(section) => {
              if (section === "list") setView("prompt-tags");
              setPromptTagSection(section);
            }}
          />
        ) : (
          <ImageStudioPage
            activeRecord={state.activeRecord}
            error={state.error}
            generating={state.submitting}
            history={state.history}
            latestResult={state.latestResult}
            selectedRecordId={state.selectedRecordId}
            onSelectRecord={state.onSelectRecord}
          />
        )}
      </div>
    </div>
  );
}
