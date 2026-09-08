import React from "react";
import type { IconProps } from "./types";

/** Horizontal arrow pointing left; replaces Phosphor `ArrowLeft`. */
export function ArrowLeftIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M20 12 H4 M4 12 L8 8 M4 12 L8 16"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Horizontal arrow pointing right; replaces Phosphor `ArrowRight`. */
export function ArrowRightIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M4 12 H20 M20 12 L16 8 M20 12 L16 16"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** ~300° arc with a leading arrowhead, reads as a single clockwise refresh; replaces Phosphor `ArrowClockwise`. */
export function ArrowClockwiseIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M17.6 8.8 A6.5 6.5 0 1 1 12 5.5 M12 5.5 L7.7 2.5 M12 5.5 L7.7 8.5"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Two symmetric arcs chasing each other, reads as a sync loop; replaces Phosphor `ArrowsClockwise`. */
export function ArrowsClockwiseIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M5.2 10.5 A6.8 6.8 0 0 1 18.8 10.5 M18.8 10.5 L16 7.7 M18.8 10.5 L21.6 7.7"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M18.8 13.5 A6.8 6.8 0 0 1 5.2 13.5 M5.2 13.5 L2.4 16.3 M5.2 13.5 L8 16.3"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Single chevron pointing down, ~90° opening; replaces Phosphor `CaretDown`. */
export function CaretDownIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M8 11 L12 15 L16 11"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Single chevron pointing up, ~90° opening; replaces Phosphor `CaretUp`. */
export function CaretUpIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M8 13 L12 9 L16 13"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Single chevron pointing left, ~90° opening; replaces Phosphor `CaretLeft`. */
export function CaretLeftIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M13 8 L9 12 L13 16"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Single chevron pointing right, ~90° opening; replaces Phosphor `CaretRight`. */
export function CaretRightIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M11 8 L15 12 L11 16"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Half-open rounded door frame with an arrow stepping out through it; replaces Phosphor `SignOut`. */
export function SignOutIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M10 5 H8 Q5 5 5 8 V16 Q5 19 8 19 H10"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9 12 H20 M20 12 L16 8 M20 12 L16 16"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Upward arrow rising off a flat tray line; replaces Phosphor `UploadSimple`. */
export function UploadSimpleIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M12 17 V5 M12 5 L8 9 M12 5 L16 9 M5 19 H19"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
