import React from "react";
import type { IconProps } from "./types";

/** Rounded camera body with viewfinder bump and duotone lens; replaces Phosphor `Camera`. */
export function CameraIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="9" y="4.5" width="6" height="4" rx="3" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <rect x="3" y="7.5" width="18" height="12" rx="3.5" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <circle cx="12" cy="13.5" r="3.3" fill="currentColor" opacity={0.15} />
      <circle cx="12" cy="13.5" r="3.3" stroke="currentColor" strokeWidth={1.7} />
    </svg>
  );
}

/** Rounded picture frame with a duotone hill and a sun dot; replaces Phosphor `ImageSquare`. */
export function ImageSquareIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="4" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <circle cx="8.4" cy="8.4" r="1.6" stroke="currentColor" strokeWidth={1.7} />
      <path
        d="M5.5 17 Q7.2 12.8 9 12.3 Q10 13.8 11.5 13.3 Q13.5 9.3 15.5 9.6 Q17.5 12.3 18.5 17 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M5.5 17 Q7.2 12.8 9 12.3 Q10 13.8 11.5 13.3 Q13.5 9.3 15.5 9.6 Q17.5 12.3 18.5 17"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Picture frame with a torn bottom-right corner; replaces Phosphor `ImageBroken`. */
export function ImageBrokenIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M14 21 H7 A4 4 0 0 1 3 17 V7 A4 4 0 0 1 7 3 H17 A4 4 0 0 1 21 7 V13"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
      <path
        d="M21 13 L18.6 14.7 L20.2 16.5 L17.2 18.4 L18.7 20.2 L14 21"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
      <circle cx="8.3" cy="8.3" r="1.6" stroke="currentColor" strokeWidth={1.7} />
      <path d="M5.5 17 Q7.3 13 9.3 12.5 Q10.1 13.7 11.1 13.3" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <path d="M15.3 15.6 Q16.4 14.1 17.7 14.4" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
    </svg>
  );
}

/** Two beamed eighth notes; replaces Phosphor `MusicNotes`. */
export function MusicNotesIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle cx="7" cy="18" r="2.2" stroke="currentColor" strokeWidth={1.7} />
      <path d="M9.1 18 V6.3" stroke="currentColor" strokeWidth={1.7} />
      <circle cx="16" cy="16.4" r="2.2" stroke="currentColor" strokeWidth={1.7} />
      <path d="M18.1 16.4 V5.1" stroke="currentColor" strokeWidth={1.7} />
      <path d="M9.1 6.3 L18.1 5.1" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
    </svg>
  );
}

/** Rounded speaker with two sound-wave arcs; replaces Phosphor `SpeakerHigh`. */
export function SpeakerHighIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M4 9.5 H7.5 C9 9.5 10.7 8 12 6.3 V17.7 C10.7 16 9 14.5 7.5 14.5 H4 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
      <path d="M14.5 9 Q16.5 12 14.5 15" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <path d="M17 6.3 Q20.7 12 17 17.7" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
    </svg>
  );
}

/** Capsule microphone with a U-stand and base; replaces Phosphor `Microphone`. */
export function MicrophoneIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="9" y="3" width="6" height="10" rx="3" fill="currentColor" opacity={0.15} />
      <rect x="9" y="3" width="6" height="10" rx="3" stroke="currentColor" strokeWidth={1.7} />
      <path d="M17 13 V13.5 A5 5 0 0 1 7 13.5 V13" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <path d="M12 18.5 V20.5" stroke="currentColor" strokeWidth={1.7} />
      <path d="M9 20.5 H15" stroke="currentColor" strokeWidth={1.7} />
    </svg>
  );
}

/** Five rounded bars rising and falling like a sound wave; replaces Phosphor `Waveform`. */
export function WaveformIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M4 9 V15" stroke="currentColor" strokeWidth={1.7} />
      <path d="M8 7 V17" stroke="currentColor" strokeWidth={1.7} />
      <path d="M12 4 V20" stroke="currentColor" strokeWidth={1.7} />
      <path d="M16 7 V17" stroke="currentColor" strokeWidth={1.7} />
      <path d="M20 9 V15" stroke="currentColor" strokeWidth={1.7} />
    </svg>
  );
}

/** Rounded monitor with a duotone screen and a small base; replaces Phosphor `Monitor`. */
export function MonitorIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="3" y="4" width="18" height="13" rx="3.5" fill="currentColor" opacity={0.15} />
      <rect x="3" y="4" width="18" height="13" rx="3.5" stroke="currentColor" strokeWidth={1.7} />
      <path d="M12 17 V19.5" stroke="currentColor" strokeWidth={1.7} />
      <path d="M8 20.5 H16" stroke="currentColor" strokeWidth={1.7} />
    </svg>
  );
}

/** Rounded duotone square; replaces Phosphor `Stop`. */
export function StopIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="5" y="5" width="14" height="14" rx="4" fill="currentColor" opacity={0.15} />
      <rect x="5" y="5" width="14" height="14" rx="4" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
    </svg>
  );
}

/** Spinner ring: a faint full circle plus a solid quarter arc; replaces Phosphor `CircleNotch`. */
export function CircleNotchIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M4 12 A8 8 0 1 1 20 12 A8 8 0 1 1 4 12" stroke="currentColor" strokeWidth={1.7} opacity={0.2} />
      <path d="M12 4 A8 8 0 0 1 20 12" stroke="currentColor" strokeWidth={1.7} />
    </svg>
  );
}

/** Tilted wand with a solid tip and a small sparkle; replaces Phosphor `MagicWand`. */
export function MagicWandIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M4.5 19.5 L12.9 11.1" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      <path
        d="M16.2 4 Q17 6.9 20 7.8 Q17 8.7 16.2 11.6 Q15.4 8.7 12.4 7.8 Q15.4 6.9 16.2 4 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M16.2 4 Q17 6.9 20 7.8 Q17 8.7 16.2 11.6 Q15.4 8.7 12.4 7.8 Q15.4 6.9 16.2 4 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinejoin="round"
      />
      <circle cx="7" cy="10.5" r="0.9" fill="currentColor" opacity={0.5} />
    </svg>
  );
}

/** Three shelved book spines, the middle one leaning, the last one duotone; for the prompt library. */
export function PromptLibraryIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M3 20.5 H21" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      {/* thin spines: rx intentionally below the SPEC's rx>=3 container rule — full rounding turns a book into a pill */}
      <rect x="3.5" y="5" width="4" height="15.5" rx="1.4" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <rect x="9" y="5" width="4" height="15.5" rx="1.4" fill="currentColor" opacity={0.15} />
      <rect x="9" y="5" width="4" height="15.5" rx="1.4" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
      <path d="M13.8 5.9 L17.1 5.05 L20.85 19.6 L17.55 20.45 Z" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" />
    </svg>
  );
}
