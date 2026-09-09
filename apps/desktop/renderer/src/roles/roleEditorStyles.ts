/** Underline-style identity field (name/intro) shared by detail and create pages; opts out of the global focus halo. */
export const roleIdentityInputClass =
  "w-full border-0 border-b border-transparent bg-transparent px-0 py-1 transition hover:border-line focus:border-accent focus:shadow-none focus:outline-none";

/** Unified input/select surface for the role editor tabs and create page. */
export const roleFieldClass =
  "w-full rounded-md border border-transparent bg-surface-soft px-3.5 py-2.5 text-body text-ink transition placeholder:text-ink-faint hover:bg-surface-hover focus:bg-surface";

/** Input/select surface rendered inside tinted capability and delivery tiles. */
export const roleTileFieldClass =
  "w-full rounded-md border border-transparent bg-white/75 px-3.5 py-2.5 text-body text-ink transition placeholder:text-ink-faint focus:bg-surface";

/** Field label wrapper with the shared caption color. */
export const roleFieldLabelClass = "grid gap-1.5 text-xs text-ink-muted";

/** Section heading used at the top of each role editor group. */
export const roleSectionTitleClass = "text-sm font-semibold text-ink";

/** Muted description line rendered under section headings. */
export const roleSectionDescriptionClass = "mt-1 text-xs text-ink-muted";

/** Small keyword chip used by knowledge entries. */
export const roleChipClass =
  "inline-flex max-w-full items-center truncate rounded-full bg-surface-soft px-2.5 py-1 text-[11px] leading-4 text-ink-secondary";

/** Compact ghost action rendered beside section headings. */
export const rolePanelGhostButtonClass =
  "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-ink-secondary transition hover:bg-surface-hover hover:text-ink focus:outline-none disabled:cursor-not-allowed disabled:text-ink-faint";
