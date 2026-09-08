/** Joins conditional Tailwind class names without pulling in a runtime dependency. */
export function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

/** Shared card surface used by empty states and diagnostic rows. */
export const cardClass = "rounded-lg border border-line-soft bg-surface shadow-soft";

/** Shared background for secondary workspace navigation sidebars. */
export const secondarySidebarSurfaceClass = "bg-surface-soft";

/** Shared interaction styling for sidebar navigation entries. */
export const sidebarNavItemClass =
  "rounded-md transition-colors hover:bg-surface-hover focus-visible:bg-surface-hover";

/** Shared small-body text class for non-titlebar desktop content. */
export const bodyTextClass = "text-body-sm";

/** Shared input styling for form controls outside the chat composer. */
export const inputClass =
  "w-full rounded-md border border-line bg-surface px-3.5 py-2.5 text-body text-ink transition placeholder:text-ink-faint hover:border-line-strong";

/** Shared textarea styling for role prompt fields. */
export const textareaClass = cx(inputClass, "min-h-24 resize-y");

/** Shared primary action button styling. */
export const primaryButtonClass =
  "cursor-pointer rounded-md border border-transparent bg-gradient-accent px-[18px] py-3 text-white shadow-soft transition-[box-shadow,filter] duration-150 hover:brightness-105 hover:shadow-panel active:brightness-95 disabled:cursor-default disabled:opacity-50 disabled:shadow-none";

/** Shared secondary action button styling. */
export const ghostButtonClass =
  "cursor-pointer rounded-md border border-line bg-surface px-[18px] py-3 text-ink-secondary transition-colors hover:border-line-accent hover:bg-accent-softer hover:text-accent-text disabled:cursor-default disabled:opacity-50";

/** Shared destructive action button styling. */
export const dangerButtonClass =
  "cursor-pointer rounded-md border border-transparent bg-danger px-[18px] py-3 text-white transition-[filter] hover:brightness-105 active:brightness-95 disabled:cursor-default disabled:opacity-50";

/** Shared quiet destructive styling for inline delete affordances. */
export const dangerGhostButtonClass =
  "cursor-pointer rounded-md border border-line bg-surface px-[18px] py-3 text-danger-text transition-colors hover:border-danger/40 hover:bg-danger-soft disabled:cursor-default disabled:opacity-50";

/** Shared focus reset for controls that rely on their existing state styling. */
export const focusResetClass = "focus:outline-none";

/** Reusable panel header layout. */
export const panelHeadClass = "panel-head mb-3 flex items-center justify-between";

/** Reusable display-face panel title. */
export const panelTitleClass = "m-0 font-display text-title text-ink";

/** Soft pill badge for statuses and tags. */
export const badgeClass =
  "inline-flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-0.5 text-caption text-accent-text";
