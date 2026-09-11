import type { PluginUiModule } from "../../../apps/desktop/renderer/src/plugins/pluginUiModuleContract";
import { NovelAIPage } from "./NovelAIPage";
import { NovelAIPageSidebar } from "./NovelAIPageSidebar";
import { canSelectNovelAiPage } from "./novelAiPageStore";

const novelAiLogoDark = new URL(
  "../../../apps/desktop/renderer/src/assets/novelai-logo-dark.svg",
  import.meta.url,
).href;

/** Nav-rail icon: the plugin's own brand mark, kept from before the nav.page migration. */
function NovelAIIcon({ className }: { className?: string }) {
  return <img className={className} src={novelAiLogoDark} alt="" />;
}

/**
 * novelai's plugin UI module (issue #180): Image Studio as a `nav.page`
 * (manual generation, prompt-tag library, generation history), and its
 * settings as an auto-generated `settings.section` form driven by the
 * plugin's own `NovelAIConfig` JSON Schema — the core settings page no
 * longer has any novelai-specific code.
 *
 * `sidebar` and `canSelect` (issue #226 gaps A/B) restore two behaviours
 * the nav.page slot from #179 couldn't express when Image Studio moved off
 * the desktop shell in #180: a drag-resizable sidebar owned by the host's
 * track, and a nav-rail entry that refuses to navigate while no role
 * exists yet. See `novelAiPageStore.ts` and `NovelAIPage.tsx`'s docstrings.
 */
const novelAiUiModule: PluginUiModule = {
  pluginId: "novelai",
  navPage: {
    label: "生图",
    icon: NovelAIIcon,
    component: NovelAIPage,
    sidebar: NovelAIPageSidebar,
    canSelect: canSelectNovelAiPage,
  },
  settingsSection: {
    kind: "schema",
    label: "NovelAI",
  },
};

export default novelAiUiModule;
