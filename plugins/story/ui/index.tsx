import { BookOpenText } from "@phosphor-icons/react";
import type { PluginUiModule } from "../../../apps/desktop/renderer/src/plugins/pluginUiModuleContract";
import { StoryPage } from "./StoryPage";
import "./story.css";

/** Story is a full-window plugin page; backend dependency state controls its visibility. */
const storyUi: PluginUiModule = {
  pluginId: "story",
  navPage: { label: "故事", icon: BookOpenText, component: StoryPage, presentation: "fullscreen" },
};

export default storyUi;
