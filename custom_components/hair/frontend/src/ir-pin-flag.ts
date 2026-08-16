/**
 * The pin scope split's one visibility gate (signpost 3 coding plan,
 * section 0b): the header `Pin:` chip-group component and its mint-
 * flow prompt are BUILT this signpost, but the binding machinery
 * (digest derivation, retransmit, echo defense) is signpost 4 / Release
 * B. Rather than ship a control that visibly does nothing -- a broken
 * promise if the signpost 3 boundary becomes a public release -- every
 * bit of pin UI renders behind this one const.
 *
 * Flip to true only at the owner's bench checkpoint (coding plan
 * section 5: "SIGNPOST BOUNDARY... rules on flipping
 * PINNING_UI_ENABLED early if holding"), and only once Track 2 item 5
 * (pin storage: `pinned_device_ids` on TriggerRemote, WS set/unset
 * commands) has actually landed -- until then the Pin groups this
 * const gates are `readonly` previews with nothing behind them (see
 * ir-header-chip-group.ts's `readonly` prop), not live controls.
 *
 * PIN_BLUE is `#4dabf7`, the Remote detail Pin group's color (owner-
 * ruled 2026-08-15, section 0 item 4 of the coding plan): "distinct
 * from Sniffer's #2196f3 -- do not merge the tokens." The Device
 * detail Pin group uses the existing `ORIGIN_COLORS.remote` gold
 * instead (pinned items ARE Remotes there, same token every other
 * Remote-kind surface already uses) -- no new constant needed for
 * that half.
 */
export const PINNING_UI_ENABLED = false;

export const PIN_BLUE = "#4dabf7";
