import type { PluginRpcClient } from "../../../apps/desktop/renderer/src/plugins/pluginBridgeClient";
import { PromptTagLibraryPanel } from "./PromptTagLibraryPanel";
import type { PromptTagWorkspaceSectionId } from "./PromptTagWorkspaceSidebar";

type PromptTagLibraryPageProps = {
  client: PluginRpcClient;
  bridgeReady: boolean;
  section: PromptTagWorkspaceSectionId;
  onOpenSection: (section: PromptTagWorkspaceSectionId) => void;
};

/** Renders the full-screen prompt-tag knowledge-base page. */
export function PromptTagLibraryPage({ client, bridgeReady, section, onOpenSection }: PromptTagLibraryPageProps) {
  return (
    <section className="h-full overflow-hidden bg-gradient-app bg-fixed" data-testid="prompt-tag-library-page">
      <div className="h-full w-full">
        <PromptTagLibraryPanel client={client} bridgeReady={bridgeReady} section={section} onOpenSection={onOpenSection} />
      </div>
    </section>
  );
}
