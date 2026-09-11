import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { act, useState } from "react";
import { mountTestComponent } from "../shared/testing/domTestHarness";
import { useDesktopUiEffects } from "./useDesktopUiEffects";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => { setTimeout(resolve, ms); });
}

/**
 * Mounts a minimal harness exercising only the `navBlockedMessage`
 * auto-dismiss effect (issue #226 follow-up: 拦住 + 给提示). Every other
 * `useDesktopUiEffectsArgs` field is a static, inert value so this test
 * isolates the one behaviour it cares about.
 */
async function mountHarness() {
  let setMessage!: (value: string) => void;
  let currentMessage = "";

  function Harness() {
    const [navBlockedMessage, setNavBlockedMessage] = useState("");
    setMessage = setNavBlockedMessage;
    currentMessage = navBlockedMessage;
    useDesktopUiEffects({
      sidebarAnimating: false,
      setSidebarAnimating: () => undefined,
      pendingMessageNavigation: null,
      setHighlightedMessageKey: () => undefined,
      notice: "",
      setNotice: () => undefined,
      workspaceFeedback: null,
      setWorkspaceFeedback: () => undefined,
      navBlockedMessage,
      setNavBlockedMessage,
      highlightedMessageKey: "",
      previewIllustrations: [],
      activeIllustration: "",
      persistedChatBackground: "",
      setActiveIllustration: () => undefined,
      sidebarAnimationDurationMs: 480,
      sidebarAutoCollapseWindowWidth: 980,
      setSidebarCollapsed: () => undefined,
    });
    return null;
  }

  const view = await mountTestComponent(<Harness />);
  return {
    view,
    setMessage: (value: string) => { act(() => setMessage(value)); },
    getMessage: () => currentMessage,
  };
}

describe("useDesktopUiEffects navBlockedMessage auto-dismiss (issue #226 follow-up)", () => {
  it("clears the message on its own after the same 2200ms timeout notice/workspaceFeedback already use", async () => {
    const { view, setMessage, getMessage } = await mountHarness();
    try {
      setMessage("请先创建至少一个角色，再进入生图。");
      assert.equal(getMessage(), "请先创建至少一个角色，再进入生图。");

      await act(async () => { await sleep(2500); });
      assert.equal(getMessage(), "", "the message must have cleared itself by now");
    } finally {
      await view.cleanup();
    }
  });
});
