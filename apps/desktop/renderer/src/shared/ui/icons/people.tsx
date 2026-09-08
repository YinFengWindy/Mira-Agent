import React from "react";
import type { IconProps } from "./types";

/** Single head + rounded shoulder arc; replaces Phosphor `User`. */
export function UserIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle cx="12" cy="8.3" r="3.3" fill="currentColor" opacity={0.15} />
      <circle
        cx="12"
        cy="8.3"
        r="3.3"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M5.2 20 C5.2 15.1 8.1 12.3 12 12.3 C15.9 12.3 18.8 15.1 18.8 20"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Outer ring containing a small head + shoulder arc; replaces Phosphor `UserCircle`. */
export function UserCircleIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle cx="12" cy="12" r="8.6" fill="currentColor" opacity={0.15} />
      <circle
        cx="12"
        cy="12"
        r="8.6"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx="12"
        cy="9.6"
        r="2.3"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M7.6 17.6 C7.6 14.6 9.5 12.7 12 12.7 C14.5 12.7 16.4 14.6 16.4 17.6"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Two overlapping people: a full figure in front, a sliver of a head/shoulder behind; replaces Phosphor `Users`. */
export function UsersIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M15.5 5.3 A2.5 2.5 0 0 1 15.5 10.3"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M17.8 18.8 C17.6 15.6 17.1 12.7 15.5 10.6"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="8.8" cy="9.3" r="3.1" fill="currentColor" opacity={0.15} />
      <circle
        cx="8.8"
        cy="9.3"
        r="3.1"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M3.6 19.5 C3.6 15.2 5.9 12.6 8.8 12.6 C11.7 12.6 13.6 14.7 14.1 17.8"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Rounded-rect robot face with an antenna, dot eyes, and a short mouth line; replaces Phosphor `Robot`. */
export function RobotIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="5" y="7" width="14" height="12" rx="4" fill="currentColor" opacity={0.15} />
      <rect
        x="5"
        y="7"
        width="14"
        height="12"
        rx="4"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 7 L12 4.9"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx="12"
        cy="3.9"
        r="1"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="9" cy="12.5" r="0.85" fill="currentColor" />
      <circle cx="15" cy="12.5" r="0.85" fill="currentColor" />
      <path
        d="M9.3 16.3 L14.7 16.3"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Two rounded brain lobes split by a center line, each edge dotted with soft bumps; replaces Phosphor `Brain`. */
export function BrainIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M12 5 C10.8 4.2 8.9 4.4 8.1 5.9 C6.4 6 5.2 7.5 5.6 9.1 C4.3 10 4.1 11.9 5.2 12.9 C4.6 14.5 5.5 16.2 7.1 16.6 C7.5 18.2 9.3 19.1 10.9 18.4 C11.3 18.6 11.7 18.7 12 18.7 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M12 5 C10.8 4.2 8.9 4.4 8.1 5.9 C6.4 6 5.2 7.5 5.6 9.1 C4.3 10 4.1 11.9 5.2 12.9 C4.6 14.5 5.5 16.2 7.1 16.6 C7.5 18.2 9.3 19.1 10.9 18.4 C11.3 18.6 11.7 18.7 12 18.7 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 5 C13.2 4.2 15.1 4.4 15.9 5.9 C17.6 6 18.8 7.5 18.4 9.1 C19.7 10 19.9 11.9 18.8 12.9 C19.4 14.5 18.5 16.2 16.9 16.6 C16.5 18.2 14.7 19.1 13.1 18.4 C12.7 18.6 12.3 18.7 12 18.7 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Almond eye with an iris ring and a soft pupil; replaces Phosphor `Eye`. */
export function EyeIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M4 12 Q12 5.2 20 12 Q12 18.8 4 12 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="2.6" fill="currentColor" opacity={0.15} />
      <circle
        cx="12"
        cy="12"
        r="2.6"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="1" fill="currentColor" opacity={0.5} />
    </svg>
  );
}

/** Same almond eye outline with the iris omitted and a diagonal slash; replaces Phosphor `EyeSlash`. */
export function EyeSlashIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M4 12 Q12 5.2 20 12 Q12 18.8 4 12 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M5.5 5.5 L18.5 18.5"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Circle with an exclamation mark; replaces Phosphor `WarningCircle`. */
export function WarningCircleIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle cx="12" cy="12" r="8.6" fill="currentColor" opacity={0.15} />
      <circle
        cx="12"
        cy="12"
        r="8.6"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 8 L12 13.6"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="16.4" r="0.95" fill="currentColor" />
    </svg>
  );
}
