import React from "react";
import type { IconProps } from "./types";

/** Round chat bubble with a small tail and three inner dots; replaces Phosphor `ChatCircleDots`. */
export function ChatCircleDotsIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M4.95 14.07 A7.5 7.5 0 1 1 8.25 18 C7.3 19.3 6 20.3 5.3 20.8 C4.5 19 4.3 16.3 4.95 14.07 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M4.95 14.07 A7.5 7.5 0 1 1 8.25 18 C7.3 19.3 6 20.3 5.3 20.8 C4.5 19 4.3 16.3 4.95 14.07 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="8.6" cy="11.5" r="1" fill="currentColor" />
      <circle cx="12" cy="11.5" r="1" fill="currentColor" />
      <circle cx="15.4" cy="11.5" r="1" fill="currentColor" />
    </svg>
  );
}

/** Two staggered speech bubbles; the back one is a duotone silhouette. Replaces Phosphor `Chats`. */
export function ChatsIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M8 8.4 L8 6.8 C8 4.8 9.3 3.5 11.3 3.5 L16.7 3.5 C18.7 3.5 20 4.8 20 6.8 L20 8.4 C20 10.4 18.7 11.7 16.7 11.7 L16.4 11.7 C16.6 12.6 16.9 13.5 17.3 14.3 C16 13.6 14.9 12.7 14.1 11.7"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.45}
      />
      <path
        d="M7.2 8.8 L12.3 8.8 Q15.5 8.8 15.5 12.0 L15.5 14.4 Q15.5 17.6 12.3 17.6 L9.0 17.6
           C7.8 18.8 6.4 19.9 5.3 20.6 C5.7 19.4 6.0 18.3 6.2 17.6 L7.2 17.6
           Q4 17.6 4 14.4 L4 12.0 Q4 8.8 7.2 8.8 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <path
        d="M7.2 8.8 L12.3 8.8 Q15.5 8.8 15.5 12.0 L15.5 14.4 Q15.5 17.6 12.3 17.6 L9.0 17.6
           C7.8 18.8 6.4 19.9 5.3 20.6 C5.7 19.4 6.0 18.3 6.2 17.6 L7.2 17.6
           Q4 17.6 4 14.4 L4 12.0 Q4 8.8 7.2 8.8 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Paper plane tilted toward the upper right, with a crease splitting the wings; replaces Phosphor `PaperPlaneTilt`. */
export function PaperPlaneTiltIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M19.5 4.5 L11.5 12.8 L8 19.5 Z" fill="currentColor" opacity={0.15} />
      <path
        d="M19.5 4.5 L4.5 9.5 L11.5 12.8 L8 19.5 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M19.5 4.5 L11.5 12.8"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Two rounded comma marks; the only fully solid icon in this set. Replaces Phosphor `Quote`. */
export function QuoteIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle cx="7.2" cy="9" r="2.4" fill="currentColor" />
      <path
        d="M8.9 10.2 C9.3 12.3 8.2 14.5 6.1 15.9 C5.8 16.1 5.5 15.8 5.7 15.5 C7.3 13.4 7.7 11.1 6.7 9.3 C7.4 9.9 8.2 10.2 8.9 10.2 Z"
        fill="currentColor"
      />
      <circle cx="14.7" cy="9" r="2.4" fill="currentColor" />
      <path
        d="M16.4 10.2 C16.8 12.3 15.7 14.5 13.6 15.9 C13.3 16.1 13 15.8 13.2 15.5 C14.8 13.4 15.2 11.1 14.2 9.3 C14.9 9.9 15.7 10.2 16.4 10.2 Z"
        fill="currentColor"
      />
    </svg>
  );
}

/** Round smiling face with dot eyes and an upturned mouth; replaces Phosphor `Smiley`. */
export function SmileyIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <circle
        cx="12"
        cy="12"
        r="7.4"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M9 9.9 L9 10.6" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      <path d="M15 9.9 L15 10.6" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      <path
        d="M8.7 14.8 Q12 17.5 15.3 14.8"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Rounded document with a folded corner and two text lines; replaces Phosphor `FileText`. */
export function FileTextIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d="M13 3.5 L17.5 3.5 L17.5 8 Z" fill="currentColor" opacity={0.15} />
      <path
        d="M8.5 3.5 L13 3.5 L17.5 8 L17.5 17.5 Q17.5 20.5 14.5 20.5 L8.5 20.5
           Q5.5 20.5 5.5 17.5 L5.5 6.5 Q5.5 3.5 8.5 3.5 Z"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M8 12.7 L15 12.7" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      <path d="M8 16.2 L13 16.2" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
    </svg>
  );
}

/** Open book with a center spine and a line of text per page; the left page is duotone. Replaces Phosphor `BookOpenText`. */
export function BookOpenTextIcon({ className = "h-4 w-4" }: IconProps) {
  const leftPage =
    "M12 6.4 C10.2 4.9 6.9 4.7 4.2 5.8 L4.2 16.6 C6.9 15.6 10.2 15.9 12 17.4 Z";
  const rightPage =
    "M12 6.4 C13.8 4.9 17.1 4.7 19.8 5.8 L19.8 16.6 C17.1 15.6 13.8 15.9 12 17.4 Z";
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path d={leftPage} fill="currentColor" opacity={0.15} />
      <path d={leftPage} stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" />
      <path d={rightPage} stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6.4 9.6 L9.6 9.6" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      <path d="M14.4 9.6 L17.6 9.6" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
    </svg>
  );
}

/** Rounded calendar with binding tabs and three date dots; the header strip is duotone. Replaces Phosphor `CalendarDots`. */
export function CalendarDotsIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <path
        d="M7.2 5 L16.8 5 Q20 5 20 8.2 L20 9.5 L4 9.5 L4 8.2 Q4 5 7.2 5 Z"
        fill="currentColor"
        opacity={0.15}
      />
      <rect
        x="4"
        y="5"
        width="16"
        height="15"
        rx="3.2"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M4 9.5 L20 9.5" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      <path d="M8.5 3.2 L8.5 6.5" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      <path d="M15.5 3.2 L15.5 6.5" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" />
      <circle cx="8" cy="14.5" r="1" fill="currentColor" />
      <circle cx="12" cy="14.5" r="1" fill="currentColor" />
      <circle cx="16" cy="14.5" r="1" fill="currentColor" />
    </svg>
  );
}
