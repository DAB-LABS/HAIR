/**
 * Origin color system: one small module, single source of truth for the
 * four origin colors, so the tab row, the picker's selected-row
 * highlight, the preview line, and the Create button never drift out of
 * sync with each other (they did briefly in the add-popups mockup's
 * a1/a2 rounds, per-dialog instead of per-tab -- a3 fixed it, this
 * module is how the fix survives into code).
 *
 * Manual = blue (var(--primary-color), HA's own accent, no new token).
 * The owner's own message carried both readings ("Manual will stay
 * green" earlier, then "any manual entry blue color... any device
 * green" later, fuller); blue shipped across two review rounds with no
 * correction back and is treated as confirmed by standing silence plus
 * "this is perfect" (add-popups-signpost-2-coding-plan.md, "Rulings
 * recorded this round").
 */
import { css, unsafeCSS } from "lit";

export const ORIGIN_COLORS = {
    manual: "var(--primary-color)", // HA's own accent -- no new token
    device: "#2e7d32", // ir-add-controlled-device-dialog.ts's create-btn
                        // (originally ir-add-device-dialog.ts's; that file
                        // retired in Track 4)
    remote: "#f5a623", // matches HAIR Triggers card/drawer gold (t2a)
    closet: "#8e3b3b", // ir-wigs.ts's --wigs-accent, verbatim
} as const;

export type OriginKind = keyof typeof ORIGIN_COLORS;

/**
 * Group-header / filter-chip colors for the Remote tab (Track 1c).
 * Trigger reuses `remote` (gold, since triggers ARE remotes); the other
 * three are each an existing app color pulled from the surface that
 * already owns it, not invented for this picker:
 *   - Sniffer: the radio-icon blue in ir-signal-monitor.ts.
 *   - Clipper: the main nav's .clipper-tab.active, ha-panel-ir-devices.ts.
 *   - Plucker: the slate in ir-pluck.ts's own header comment.
 */
export const REMOTE_KIND_COLORS = {
    trigger: ORIGIN_COLORS.remote,
    sniffer: "#2196f3",
    clipper: "#b87333",
    plucker: "#455a64",
} as const;

export type RemoteKind = keyof typeof REMOTE_KIND_COLORS;

/**
 * `#43a047` -- the s10 mockup's `--green-peak`, confirmed against its
 * own stylesheet (`.hdr-chip.on-green { border-color: var(--green-peak)
 * }`). NOT the same token as `ORIGIN_COLORS.device` (`#2e7d32`, the
 * pre-existing create-button green) -- the two read close on a swatch
 * but are genuinely different values in the mockup, and mixing them up
 * was an actual bug in this component's first landing (Track 1 item 5,
 * caught while re-reading the mockup for item 6's Duplicate button,
 * which uses this same token). Used by: ir-header-chip-group.ts's
 * Emitters:/Receivers: groups on both detail-page headers, and the
 * Settings dialog's outlined Duplicate button (Track 1 item 6).
 */
export const GREEN_PEAK = "#43a047";

/**
 * CSS custom properties exposing every origin/kind color, for consumers
 * that would rather write `var(--origin-manual)` in a `css` template
 * than thread the JS constant through an inline `style=`. Both are
 * supported -- pick whichever reads better at the call site.
 */
export const originColorVars = css`
    :host {
        --origin-manual: ${unsafeCSS(ORIGIN_COLORS.manual)};
        --origin-device: ${unsafeCSS(ORIGIN_COLORS.device)};
        --origin-remote: ${unsafeCSS(ORIGIN_COLORS.remote)};
        --origin-closet: ${unsafeCSS(ORIGIN_COLORS.closet)};
        --remote-kind-trigger: ${unsafeCSS(REMOTE_KIND_COLORS.trigger)};
        --remote-kind-sniffer: ${unsafeCSS(REMOTE_KIND_COLORS.sniffer)};
        --remote-kind-clipper: ${unsafeCSS(REMOTE_KIND_COLORS.clipper)};
        --remote-kind-plucker: ${unsafeCSS(REMOTE_KIND_COLORS.plucker)};
    }
`;
