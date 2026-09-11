import type React from "react";
import { useState } from "react";
import { flushSync } from "react-dom";
import { clampSidebarWidth, hasSidebarCollapseChanged } from "./sidebarResize";

type UseLeftSidebarStateArgs = {
  minWidth: number;
  maxWidth: number;
  defaultWidth: number;
  collapseThreshold: number;
};

/**
 * Resolves one left-sidebar drag sample from the grab offset.
 *
 * Deliberately expressed as "the width it had when you grabbed it, plus how
 * far the pointer has travelled since" rather than as the pointer's absolute
 * `clientX`. The sidebar does not start at the viewport's left edge — the nav
 * rail occupies the shell grid's first column — so treating `clientX` as the
 * width made the sidebar jump right by the rail's width the moment a drag
 * began. Measuring the delta keeps this correct no matter what sits to the
 * left of the track, how wide the grab handle is, or where inside it the
 * pointer landed.
 *
 * `startWidth` is the *rendered* width, so it is 0 while collapsed: dragging
 * the collapsed sidebar open then grows from nothing under the pointer
 * instead of snapping back to the width it had before it was collapsed.
 */
export function resolveLeftSidebarDragUpdate(
  startWidth: number,
  startX: number,
  clientX: number,
  minWidth: number,
  maxWidth: number,
  collapseThreshold: number,
) {
  const requestedWidth = startWidth + (clientX - startX);
  if (requestedWidth <= collapseThreshold) {
    return { collapsed: true, width: null };
  }
  return { collapsed: false, width: clampSidebarWidth(requestedWidth, minWidth, maxWidth) };
}

/** Manages the desktop shell's collapsible and resizable left sidebar. */
export function useLeftSidebarState({
  minWidth,
  maxWidth,
  defaultWidth,
  collapseThreshold,
}: UseLeftSidebarStateArgs) {
  const [width, setWidth] = useState(defaultWidth);
  const [collapsed, setCollapsed] = useState(false);
  const [resizing, setResizing] = useState(false);
  const [animating, setAnimating] = useState(false);

  function toggle(): void {
    setAnimating(true);
    if (collapsed) {
      setWidth((current) => clampSidebarWidth(current, minWidth, maxWidth));
      setCollapsed(false);
      return;
    }
    setCollapsed(true);
  }

  function beginResize(event: React.PointerEvent<HTMLDivElement>): void {
    event.preventDefault();
    flushSync(() => {
      setAnimating(false);
      setResizing(true);
    });
    let dragCollapsed = collapsed;
    // Captured once, at the grab: everything below is relative to these.
    const startX = event.clientX;
    const startWidth = collapsed ? 0 : width;

    function stopResize(): void {
      setResizing(false);
      window.removeEventListener("pointermove", resize);
      window.removeEventListener("pointerup", stopResize);
      window.removeEventListener("pointercancel", stopResize);
    }

    function resize(moveEvent: PointerEvent): void {
      const update = resolveLeftSidebarDragUpdate(
        startWidth,
        startX,
        moveEvent.clientX,
        minWidth,
        maxWidth,
        collapseThreshold,
      );
      if (hasSidebarCollapseChanged(dragCollapsed, update.collapsed)) {
        setAnimating(true);
        dragCollapsed = update.collapsed;
      }
      setCollapsed(update.collapsed);
      if (update.width !== null) setWidth(update.width);
    }

    window.addEventListener("pointermove", resize);
    window.addEventListener("pointerup", stopResize);
    window.addEventListener("pointercancel", stopResize);
  }

  return {
    width,
    collapsed,
    resizing,
    animating,
    setWidth,
    setCollapsed,
    setAnimating,
    toggle,
    beginResize,
  };
}
