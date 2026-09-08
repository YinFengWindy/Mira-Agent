import React from "react";

type DesktopIconProps = {
  className?: string;
};

/**
 * Legacy icon entry point. Most drawings now live in `shared/ui/icons`
 * (the Shiori custom set) and are aliased below so pre-restyle call
 * sites render the new artwork without changes.
 *
 * Plus / Reset / Back / Send keep the original pre-restyle glyphs by
 * user request (the redrawn versions were rejected at acceptance).
 */
export {
  CaretRightIcon,
  CheckIcon as SaveIcon,
  CircleNotchIcon as SpinnerIcon,
  CopyIcon,
  FileTextIcon as DocumentIcon,
  LocateIcon,
  PromptLibraryIcon,
  QuoteIcon,
  SmileyIcon,
  UploadSimpleIcon as UploadIcon,
  XIcon as CloseIcon,
  XIcon as DeleteIcon,
} from "./ui/icons";

/** Renders the original desktop reset/refresh glyph. */
export function ResetIcon({ className = "h-4 w-4 fill-current" }: DesktopIconProps) {
  return (
    <svg viewBox="0 0 1024 1024" className={className} aria-hidden="true">
      <path d="M958.72 225.856l-82.688 211.136-13.76 35.2c-3.776 9.728-14.784 14.528-24.512 10.688l-35.2-13.76L591.36 386.368C581.632 382.528 576.832 371.584 580.672 361.856l13.76-35.2c3.776-9.728 14.784-14.528 24.512-10.688l174.912 68.544c-50.56-124.416-171.584-212.672-314.112-212.672-187.84 0-340.16 152.32-340.16 340.16s152.256 340.16 340.16 340.16c148.032 0 273.6-94.72 320.384-226.752l79.296 0c-49.408 174.4-209.408 302.336-399.68 302.336C250.112 927.744 64 741.632 64 512s186.112-415.744 415.744-415.744c157.056 0 293.376 87.296 363.968 215.872l44.608-113.856c3.776-9.728 14.784-14.528 24.512-10.688l35.2 13.76C957.696 205.184 962.496 216.128 958.72 225.856z" />
    </svg>
  );
}

/** Renders the original desktop send glyph. */
export function SendIcon({ className = "h-4 w-4 fill-current" }: DesktopIconProps) {
  return (
    <svg viewBox="0 0 1024 1024" className={className} aria-hidden="true">
      <path d="M392.021333 925.013333a34.133333 34.133333 0 0 1-34.133333-34.133333V579.242667c0-10.24 4.608-19.968 12.629333-26.453334l276.48-224.085333a34.0992 34.0992 0 0 1 43.008 52.906667L426.154667 595.456v192.853333l82.944-110.592c10.069333-13.482667 28.672-17.578667 43.52-9.557333l137.557333 73.728L853.333333 156.16c3.242667-11.434667-3.413333-18.602667-6.485333-21.162667-3.072-2.56-11.093333-7.850667-21.845333-2.901333L206.336 422.4l80.213333 46.08c16.384 9.386667 22.016 30.208 12.629334 46.592s-30.208 22.016-46.592 12.629333l-137.045334-78.677333a33.979733 33.979733 0 0 1-17.066666-31.061333c0.512-12.8 8.021333-24.064 19.626666-29.525334L795.989333 70.314667c31.744-14.848 68.096-10.069333 94.890667 12.629333a87.790933 87.790933 0 0 1 28.16 91.477333L744.277333 801.28a34.082133 34.082133 0 0 1-48.981333 20.821333L546.133333 742.058667l-126.805333 169.301333c-6.656 8.704-16.896 13.653333-27.306667 13.653333z" />
    </svg>
  );
}

/** Renders the original desktop plus glyph used by creation actions. */
export function PlusIcon({ className = "h-4 w-4 fill-current" }: DesktopIconProps) {
  return (
    <svg viewBox="0 0 1024 1024" className={className} aria-hidden="true">
      <path d="M847.0528 491.52H532.48V176.9472c0-11.264-9.216-20.48-20.48-20.48s-20.48 9.216-20.48 20.48V491.52H176.9472c-11.264 0-20.48 9.216-20.48 20.48s9.216 20.48 20.48 20.48H491.52v314.5728c0 11.264 9.216 20.48 20.48 20.48s20.48-9.216 20.48-20.48V532.48h314.5728c11.264 0 20.48-9.216 20.48-20.48s-9.216-20.48-20.48-20.48z" />
    </svg>
  );
}

/** Renders the original desktop back-navigation glyph. */
export function BackIcon({ className = "h-4 w-4 fill-current" }: DesktopIconProps) {
  return (
    <svg viewBox="0 0 1024 1024" className={className} aria-hidden="true">
      <path d="M631.04 161.941333a42.666667 42.666667 0 0 1 63.061333 57.386667l-2.474666 2.730667-289.962667 292.245333 289.706667 287.402667a42.666667 42.666667 0 0 1 2.730666 57.6l-2.474666 2.752a42.666667 42.666667 0 0 1-57.6 2.709333l-2.752-2.474667-320-317.44a42.666667 42.666667 0 0 1-2.709334-57.6l2.474667-2.752 320-322.56z" />
    </svg>
  );
}
