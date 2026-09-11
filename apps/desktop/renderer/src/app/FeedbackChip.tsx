import { cx } from "../shared/styles";

export type FeedbackChipTone = "success" | "error";

type FeedbackChipProps = {
  tone: FeedbackChipTone;
  message: string;
  /**
   * Which top-center slot this chip occupies. `DesktopAppFrame` can have
   * two of these mounted at once — `workspaceFeedback` (role-workspace
   * flows) and `navBlockedMessage` (a refused nav.page selection, issue
   * #226) — plus `ChatSurface` renders its own `notice-chip` at the same
   * spot while on the chat view. All three are independent, differently
   * lived pieces of state that can be true at once, so instead of trying to
   * suppress one when another is showing, `"secondary"` simply renders one
   * row lower — cheap, deterministic, and needs no cross-component
   * coordination.
   */
  slot?: "primary" | "secondary";
};

const slotPositionClass: Record<NonNullable<FeedbackChipProps["slot"]>, string> = {
  primary: "top-4",
  secondary: "top-16",
};

/** The floating top-center feedback pill shared by every shell-level (non-chat) transient message. */
export function FeedbackChip({ tone, message, slot = "primary" }: FeedbackChipProps) {
  return (
    <div
      className={cx(
        "absolute left-1/2 z-[6] -translate-x-1/2 rounded-md border px-4 py-2.5 text-body-sm shadow-soft",
        slotPositionClass[slot],
        tone === "success"
          ? "border-[var(--success-300)] bg-success-soft text-success-text"
          : "border-[var(--danger-300)] bg-danger-soft text-danger-text",
      )}
      aria-live="polite"
    >
      {message}
    </div>
  );
}
