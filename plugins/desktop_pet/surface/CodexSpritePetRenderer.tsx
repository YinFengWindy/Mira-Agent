import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { X } from "@phosphor-icons/react";
import { spriteActionDurationMs, spriteCell, spriteFramePosition, spritePlaybackFrameAt, type SpriteState } from "./spriteContract";
import { useCodexPetInteraction } from "./useCodexPetInteraction";
import { noPetBubble, type PetBubblePlacement } from "./bubbleExtension";
import { openPetContextMenu } from "./petMenu";
import type { SurfaceHandle } from "../../../apps/desktop/renderer/src/surface/pluginSurfaceRegistry";
// TEMPORARY COUPLING: screen observation is still a host feature. It becomes a
// plugin in #220, and then reaches the pet through plugin-to-plugin messaging
// (#218); until then the pet consumes the host's payload type directly.
import type { PetObservationPayload } from "../../../apps/desktop/src/observation/types";
import type { VoiceStatePayload } from "../../../apps/desktop/src/bridge/shared";

type CodexSpritePetRendererProps = {
  spritesheetUrl: string;
  state: SpriteState;
  transientState?: SpriteState | null;
  onTransientFinished?: () => void;
  observation: PetObservationPayload;
  /** Which side the bubble occupies; chosen by this plugin, not by the host. */
  bubbleLayout?: PetBubblePlacement;
  voice?: VoiceStatePayload;
  /** The window this pet is rendering inside; null in a plain render test. */
  surface?: SurfaceHandle | null;
  /** Reports the measured bubble height so the surface can be resized around it. */
  onBubbleHeight?: (height: number) => void;
};

/** Renders the fixed Codex sprite atlas with its documented state rows and cadence. */
export function CodexSpritePetRenderer({ spritesheetUrl, state, transientState = null, onTransientFinished = noop, observation, bubbleLayout = noPetBubble, voice = { status: "idle" }, surface = null, onBubbleHeight = noop }: CodexSpritePetRendererProps) {
  const [frame, setFrame] = useState(0);
  const { interactionState, isDragging, pointerHandlers } = useCodexPetInteraction(
    surface,
    typeof window === "undefined" ? null : window.miraDesktop,
  );
  const observationState: SpriteState | null = observation.status === "reviewing"
    ? "review"
    : observation.status === "paused"
      ? "waiting"
      : observation.status === "failed"
        ? "failed"
        : null;
  const voicePlaybackState: SpriteState | null = voice.status === "recording"
    || voice.status === "transcribing"
    || voice.status === "sending"
    || voice.status === "waiting_reply"
    || voice.status === "speaking_prepare"
    ? "waiting"
    : null;
  const voiceBubble = voice.status === "recording"
    ? "我在听"
    : voice.status === "transcribing" || voice.status === "sending" || voice.status === "waiting_reply" || voice.status === "speaking_prepare"
      ? "正在理解"
      : voice.status === "error"
        ? voice.message || "没听清，再试一次"
        : "";
  const bubbleText = voiceBubble || observation.bubble;
  const activeState = transientState ?? observationState ?? interactionState ?? voicePlaybackState ?? state;
  const activePlaybackFrame = spritePlaybackFrameAt(activeState, frame);

  useEffect(() => {
    setFrame(0);
  }, [activeState]);

  useEffect(() => {
    if (!transientState) return;
    const durationMs = spriteActionDurationMs(transientState);
    if (durationMs <= 0) {
      onTransientFinished();
      return;
    }
    const timer = window.setTimeout(onTransientFinished, durationMs);
    return () => window.clearTimeout(timer);
  }, [onTransientFinished, transientState]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFrame((current) => current + 1);
    }, activePlaybackFrame.duration);
    return () => window.clearTimeout(timer);
  }, [activePlaybackFrame.duration, activeState, frame]);

  useEffect(() => {
    if (!bubbleText) onBubbleHeight(0);
  }, [bubbleText, onBubbleHeight]);

  const surfaceClass = bubbleText
    ? `pet-surface pet-bubble-${bubbleLayout.placement}`
    : "pet-surface";

  return (
    <div className={surfaceClass}>
      {bubbleText ? <PetBubble text={bubbleText} persistent={!voiceBubble && observation.persistent} onHeight={onBubbleHeight} /> : null}
      <div
        aria-label="桌宠"
        className={isDragging ? "pet-drag-region pet-dragging" : "pet-drag-region"}
        {...pointerHandlers}
        onLostPointerCapture={pointerHandlers.onPointerCancel}
        onContextMenu={(event) => {
          event.preventDefault();
          if (surface) void openPetContextMenu(surface, window.miraDesktop);
        }}
        style={{
          width: spriteCell.width,
          height: spriteCell.height,
          backgroundImage: `url(${JSON.stringify(spritesheetUrl)})`,
          backgroundPosition: spriteFramePosition(activePlaybackFrame.state, activePlaybackFrame.frame),
          backgroundRepeat: "no-repeat",
          touchAction: "none",
        }}
      />
    </div>
  );
}

function noop(): void {}

function PetBubble({ text, persistent, onHeight }: { text: string; persistent: boolean; onHeight: (height: number) => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const reportHeight = () => onHeight(element.scrollHeight);
    reportHeight();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(reportHeight);
    observer?.observe(element);
    return () => observer?.disconnect();
  }, [onHeight, persistent, text]);

  return (
    <div
      ref={ref}
      className="pet-bubble"
      role="status"
    >
      <span>{text}</span>
      {persistent ? (
        <button
          type="button"
          className="pet-bubble-dismiss"
          aria-label="关闭消息"
          title="关闭消息"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={() => {
            // TEMPORARY COUPLING: dismissing an observation bubble is still a
            // host call. Observation becomes a plugin in #220 and then reaches
            // the pet over plugin-to-plugin messaging (#218).
            void window.miraDesktop.dismissPetObservationBubble();
          }}
        >
          <X size={12} weight="bold" />
        </button>
      ) : null}
    </div>
  );
}
