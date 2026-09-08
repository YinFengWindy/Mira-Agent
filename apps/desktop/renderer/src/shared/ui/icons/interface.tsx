import React from "react";
import type { IconProps } from "./types";

/** Replaces Phosphor `Plus`. */
export function PlusIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M12 5.5 V18.5 M5.5 12 H18.5"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Replaces Phosphor `Minus`. */
export function MinusIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M5.5 12 H18.5" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Replaces Phosphor `X`. */
export function XIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M6.5 6.5 L17.5 17.5 M17.5 6.5 L6.5 17.5"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Replaces Phosphor `Check`. */
export function CheckIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M5 12.5 L9.5 17.5 L19 6"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Replaces Phosphor `CheckCircle`. Duotone disc with a checkmark. */
export function CheckCircleIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle cx="12" cy="12" r="8" fill="currentColor" opacity={0.15} />
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth={1.7} />
      <path
        d="M8.3 12.3 L11 15.2 L15.9 9.3"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Replaces Phosphor `MagnifyingGlass`. Duotone lens with a round-headed handle. */
export function MagnifyingGlassIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle cx="10.5" cy="10.5" r="5.5" fill="currentColor" opacity={0.15} />
      <circle cx="10.5" cy="10.5" r="5.5" stroke="currentColor" strokeWidth={1.7} />
      <path d="M14.6 14.6 L19.3 19.3" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
    </svg>
  );
}

/** Replaces Phosphor `SlidersHorizontal`. Three tracks with staggered round knobs. */
export function SlidersHorizontalIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M4 6 H6 M10 6 H20 M4 12 H14 M18 12 H20 M4 18 H9.5 M13.5 18 H20"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="8" cy="6" r="2" stroke="currentColor" strokeWidth={1.7} />
      <circle cx="16" cy="12" r="2" stroke="currentColor" strokeWidth={1.7} />
      <circle cx="11.5" cy="18" r="2" stroke="currentColor" strokeWidth={1.7} />
    </svg>
  );
}

/** Replaces Phosphor `Gear`. Six rounded teeth (round line joins soften every vertex) with a duotone body and a center hole. */
export function GearIcon({ className = "h-4 w-4" }: IconProps) {
  const gear =
    "M 10.44 3.14 L 13.56 3.14 L 14.51 5.79 L 16.12 6.72 L 18.89 6.21 L 20.46 8.92 L 18.63 11.07 L 18.63 12.93 L 20.46 15.08 L 18.89 17.79 L 16.12 17.28 L 14.51 18.21 L 13.56 20.86 L 10.44 20.86 L 9.49 18.21 L 7.88 17.28 L 5.11 17.79 L 3.54 15.08 L 5.37 12.93 L 5.37 11.07 L 3.54 8.92 L 5.11 6.21 L 7.88 6.72 L 9.49 5.79 Z";
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d={gear} fill="currentColor" opacity={0.15} />
      <path d={gear} stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <circle cx="12" cy="12" r="2.3" stroke="currentColor" strokeWidth={1.7} />
    </svg>
  );
}

/** Replaces Phosphor `PencilSimple`. Slanted pencil with a duotone body and a tip split line. */
export function PencilSimpleIcon({ className = "h-4 w-4" }: IconProps) {
  const body = "M3.8 20.2 L4.5 16.7 L12.6 8.5 C14.5 6.6 17.4 9.5 15.5 11.4 L7.3 19.5 Z";
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d={body} fill="currentColor" opacity={0.15} />
      <path d={body} stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <path
        d="M5.6 16 L8 18.4"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Replaces Phosphor `Trash`. Rounded lid, loop handle, and a tapered duotone bucket. */
export function TrashIcon({ className = "h-4 w-4" }: IconProps) {
  const body = "M6.4 7.3 H17.6 L16.8 19.3 Q16.65 20.4 15.4 20.4 H8.6 Q7.35 20.4 7.2 19.3 Z";
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d={body} fill="currentColor" opacity={0.15} />
      <path
        d="M5 7.3 H19"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <rect
        x="9.2"
        y="4.3"
        width="5.6"
        height="3.4"
        rx="1.7"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
      <path d={body} stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <path
        d="M10 10.5 V17.5 M14 10.5 V17.5"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Replaces Phosphor `Copy`. Two staggered rounded rectangles; the back one is duotone-filled, the front one outlined. */
export function CopyIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M14 4 L7.2 4 A3.2 3.2 0 0 0 4 7.2 L4 14"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        opacity={0.45}
      />
      <rect x="7" y="7" width="13" height="13" rx="3.2" fill="currentColor" opacity={0.15} />
      <rect
        x="7"
        y="7"
        width="13"
        height="13"
        rx="3.2"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Replaces Phosphor `Locate`. Crosshair rings with four tick marks and a solid center dot. */
export function LocateIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth={1.7} />
      <path
        d="M12 3.2 V5.2 M12 18.8 V20.8 M3.2 12 H5.2 M18.8 12 H20.8"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" opacity={0.5} />
    </svg>
  );
}
