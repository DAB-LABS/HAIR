/**
 * The pin scope split's one visibility gate (signpost 3 coding plan,
 * section 0b): the header `Pin:` chip-group component and its mint-
 * flow prompt are BUILT this signpost, but the binding machinery
 * (digest derivation, retransmit, echo defense) is signpost 4 / Release
 * B. Rather than ship a control that visibly does nothing -- a broken
 * promise if the signpost 3 boundary becomes a public release -- every
 * bit of pin UI renders behind this one const.
 *
 * FLIPPED 2026-08-16 (signpost 4, Track 4). The machinery this was
 * waiting for is built and benched: derivation stores which command
 * each trigger drives, a confirmed fire retransmits it, and the echo
 * defense keeps a pinned remote from hearing itself. The chip groups
 * are live controls now -- toggling one pins or unpins, and the rows
 * read stored state rather than rendering every chip off.
 *
 * PIN_BLUE is `#4dabf7`, the Remote detail Pin group's color (owner-
 * ruled 2026-08-15, section 0 item 4 of the coding plan): "distinct
 * from Sniffer's #2196f3 -- do not merge the tokens." The Device
 * detail Pin group uses the existing `ORIGIN_COLORS.remote` gold
 * instead (pinned items ARE Remotes there, same token every other
 * Remote-kind surface already uses) -- no new constant needed for
 * that half.
 */
export const PINNING_UI_ENABLED = true;

export const PIN_BLUE = "#4dabf7";
