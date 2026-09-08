import React from "react";
import type { IconProps } from "./types";

/** Four-point sparkle; replaces Phosphor `Sparkle` and doubles as brand motif. */
export function SparkleIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M12 4.2 Q13.1 10.4 19.3 12 Q13.1 13.6 12 19.8 Q10.9 13.6 4.7 12 Q10.9 10.4 12 4.2 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M12 4.2 Q13.1 10.4 19.3 12 Q13.1 13.6 12 19.8 Q10.9 13.6 4.7 12 Q10.9 10.4 12 4.2 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
      <path
        d="M18.6 3.4 Q19 5.2 20.8 5.7 Q19 6.2 18.6 8 Q18.2 6.2 16.4 5.7 Q18.2 5.2 18.6 3.4 Z"
        fill="currentColor"
        opacity={0.5}
      />
    </svg>
  );
}

/** Little-devil wing, lifted from the app icon's hair ornament. Brand motif. */
export function WingIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M5 7.5 C10 4.8 16.5 6.2 19.6 11.6 C17.8 11.3 16.3 12.2 15.7 13.9 C14.3 12.9 12.4 13.4 11.4 15 C10.1 14.1 8.3 14.6 7.4 16.3 C7.1 12.9 6.3 9.9 5 7.5 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M5 7.5 C10 4.8 16.5 6.2 19.6 11.6 C17.8 11.3 16.3 12.2 15.7 13.9 C14.3 12.9 12.4 13.4 11.4 15 C10.1 14.1 8.3 14.6 7.4 16.3 C7.1 12.9 6.3 9.9 5 7.5 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Ribbon bow, echoing the choker in the app icon. Brand motif. */
export function RibbonIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M10.4 12 C9.4 9.6 7 8.2 5.1 9.1 C3.6 10 3.6 14 5.1 14.9 C7 15.8 9.4 14.4 10.4 12 Z M13.6 12 C14.6 9.6 17 8.2 18.9 9.1 C20.4 10 20.4 14 18.9 14.9 C17 15.8 14.6 14.4 13.6 12 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M10.4 12 C9.4 9.6 7 8.2 5.1 9.1 C3.6 10 3.6 14 5.1 14.9 C7 15.8 9.4 14.4 10.4 12 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
      <path
        d="M13.6 12 C14.6 9.6 17 8.2 18.9 9.1 C20.4 10 20.4 14 18.9 14.9 C17 15.8 14.6 14.4 13.6 12 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
      <rect x="10.5" y="10.3" width="3" height="3.4" rx="1.3" stroke="currentColor" strokeWidth={1.7} />
    </svg>
  );
}

/** Sakura petal with the classic notched tip. Brand motif. */
export function PetalIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M12 20.5 C8.5 17 6.6 13.2 7.6 9.6 C8.3 7.2 10 5.2 11 4.6 C11.6 5.6 12.4 5.6 13 4.6 C14 5.2 15.7 7.2 16.4 9.6 C17.4 13.2 15.5 17 12 20.5 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M12 20.5 C8.5 17 6.6 13.2 7.6 9.6 C8.3 7.2 10 5.2 11 4.6 C11.6 5.6 12.4 5.6 13 4.6 C14 5.2 15.7 7.2 16.4 9.6 C17.4 13.2 15.5 17 12 20.5 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
    </svg>
  );
}
