import { css } from "lit";

/**
 * One tree, one icon path.
 *
 * ICON_TRASH lived in ir-device-list.ts, which was fine while exactly
 * one surface drew a can. The polish pass turned nine more row-level
 * DELETEs into icons, and two definitions of a trash path is how they
 * drift: one gets a tweak, the other does not, and the panel quietly
 * ships two cans.
 *
 * This is the owner's own drawing rather than MDI's delete-outline. It
 * carries an argyle pattern that fills in below about 17px, which is
 * why every consumer renders it at 18 and not the 16 the rest of the
 * row's glyphs use.
 *
 * viewBox is 50x50, not MDI's 24x24. Consumers must say so:
 *
 *   <ha-svg-icon .path=${ICON_TRASH} viewBox="0 0 50 50"></ha-svg-icon>
 */

/** The house trash can, from images/trash_can.svg. */
export const ICON_TRASH =
    "M7.8125 8C7.335938 8.089844 6.992188 8.511719 7 9L7 13C7 13.550781 7.449219 14 8 14L8.1875 14L11.125 29.75C11.105469 29.957031 11.148438 30.164063 11.25 30.34375L12.59375 37.53125C12.585938 37.691406 12.617188 37.855469 12.6875 38L13.40625 41.875C13.40625 41.886719 13.40625 41.894531 13.40625 41.90625C13.898438 44.234375 15.921875 46 18.3125 46L31.6875 46C34.070313 46 36.203125 44.261719 36.59375 41.875C36.59375 41.863281 36.59375 41.855469 36.59375 41.84375L37.3125 38C37.3125 37.988281 37.3125 37.980469 37.3125 37.96875L37.34375 37.90625C37.390625 37.777344 37.414063 37.636719 37.40625 37.5L38.75 30.375C38.867188 30.175781 38.910156 29.945313 38.875 29.71875L41.8125 14L42 14C42.550781 14 43 13.550781 43 13L43 9C43 8.449219 42.550781 8 42 8L8 8C7.96875 8 7.9375 8 7.90625 8C7.875 8 7.84375 8 7.8125 8 Z M 9 10L41 10L41 12L32.21875 12C32.117188 11.972656 32.011719 11.960938 31.90625 11.96875C31.875 11.976563 31.84375 11.988281 31.8125 12L21.21875 12C21.117188 11.972656 21.011719 11.960938 20.90625 11.96875C20.875 11.976563 20.84375 11.988281 20.8125 12L9 12 Z M 12.4375 14L15.5625 14L14 15.5625 Z M 18.4375 14L20.5625 14L23.5625 17L19.5 21.09375L15.4375 17 Z M 23.4375 14L26.5625 14L25 15.5625 Z M 29.4375 14L31.5625 14L34.5625 17L30.5 21.0625L26.4375 17 Z M 34.4375 14L37.5625 14L36 15.5625 Z M 10.34375 14.78125L12.5625 17L11.0625 18.53125 Z M 39.65625 14.78125L38.96875 18.53125L37.4375 17 Z M 14 18.4375L18.09375 22.5L14 26.59375L12.40625 25C12.359375 24.953125 12.304688 24.910156 12.25 24.875L11.5 20.90625 Z M 25 18.4375L29.09375 22.5L25 26.59375L20.90625 22.5 Z M 36 18.4375L38.5 20.90625L37.78125 24.84375C37.710938 24.886719 37.648438 24.941406 37.59375 25L36 26.59375L31.90625 22.5 Z M 19.5 23.90625L23.59375 28L19.5 32.09375L15.40625 28 Z M 30.5 23.90625L34.59375 28L30.5 32.09375L26.40625 28 Z M 14 29.40625L18.09375 33.5L14.53125 37.0625L13.25 30.15625 Z M 25 29.40625L29.09375 33.5L25 37.59375L20.90625 33.5 Z M 36 29.40625L36.78125 30.1875L35.46875 37.0625L31.90625 33.5 Z M 19.5 34.90625L23.59375 39L20 42.59375L15.90625 38.5 Z M 30.5 34.90625L34.09375 38.5L30 42.59375L26.40625 39 Z M 25 40.40625L28.59375 44L21.40625 44 Z M 15.21875 40.625L18.59375 44L18.3125 44C16.902344 44 15.683594 42.972656 15.375 41.5 Z M 34.78125 40.625L34.625 41.5C34.625 41.511719 34.625 41.519531 34.625 41.53125C34.402344 42.929688 33.097656 44 31.6875 44L31.40625 44Z";

/** The viewBox ICON_TRASH is drawn in. */
export const TRASH_VIEWBOX = "0 0 50 50";

/**
 * The comb, from images/comb.svg. Marks a checklist row the comb
 * heuristic flagged (duplicate content, malformed frame, protocol
 * outlier) -- a diagnostic, not a verdict; the row's own check or a
 * device-side repair is what resolves it (the comb gate, RULED
 * 2026-08-08).
 *
 * viewBox is 512x512, not MDI's 24x24. Consumers must say so:
 *
 *   <ha-svg-icon .path=${ICON_COMB} viewBox="0 0 512 512"></ha-svg-icon>
 */
export const ICON_COMB =
    "M367.808,240.512c-37.163-31.232-58.475-60.565-58.475-80.512c0-23.019,5.568-37.077,10.944-50.667c5.099-12.885,10.389-26.24,10.389-45.333c0-43.669-23.723-64-74.667-64s-74.667,20.331-74.667,64c0,19.093,5.291,32.448,10.389,45.355c5.376,13.589,10.944,27.648,10.944,50.667c0,19.925-21.312,49.259-58.475,80.512c-17.067,14.357-26.859,35.264-26.859,57.344v203.456c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667v-160H160v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667S224,507.221,224,501.333v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160H288v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667V297.856C394.667,275.776,384.875,254.891,367.808,240.512z M373.333,320H138.667v-22.123c0-15.765,7.019-30.741,19.264-41.024C188.075,231.509,224,194.133,224,160c0-27.093-6.613-43.797-12.437-58.517c-4.779-12.075-8.896-22.464-8.896-37.483c0-27.669,8.491-42.667,53.333-42.667S309.333,36.331,309.333,64c0,15.019-4.117,25.408-8.896,37.483C294.613,116.203,288,132.885,288,160c0,34.133,35.925,71.509,66.069,96.853c12.245,10.304,19.264,25.259,19.264,41.024V320z";

/** The viewBox ICON_COMB is drawn in. */
export const COMB_VIEWBOX = "0 0 512 512";

/**
 * The row-level trash button, shared by all nine surfaces that draw
 * one, so there is one can and one behaviour rather than nine.
 *
 * GREY AT REST, EMBER ON HOVER (owner ruling 2026-08-03). Ember is
 * already the panel's delete colour on every text chip, so the icon
 * inherits the meaning rather than introducing a second one. Material
 * red is deliberately held back: nothing in HAIR is unrecoverable
 * enough to earn it, and every one of these sits behind a confirm
 * dialog anyway.
 *
 * The hover wash is 0.12 where the text chip uses 0.08. A smaller hit
 * target needs a slightly stronger cue to read as the same weight.
 */
export const trashButtonStyles = css`
    .trash-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: none;
        border: none;
        padding: 3px;
        border-radius: 4px;
        cursor: pointer;
        color: var(--disabled-text-color, #999);
        opacity: 0.55;
        transition: background 150ms ease, color 150ms ease,
            opacity 150ms ease;
    }
    .trash-btn:hover:not(:disabled) {
        background: rgba(230, 81, 0, 0.12);
        color: #e65100;
        opacity: 1;
    }
    .trash-btn:disabled {
        cursor: default;
        opacity: 0.25;
    }
    /* 18px, not the 16 the rest of the row's glyphs use: the argyle
       pattern fills in below about 17 and the detail that makes it the
       house can is the first thing lost. */
    .trash-btn ha-svg-icon {
        --mdc-icon-size: 18px;
    }
`;

/**
 * The wrench and screwdriver, from images/tools.svg. Opens the device
 * settings dialog (Device Settings, 0.9.8) -- NEVER an MDI gear;
 * RULED 2026-08-09 this replaced an earlier comb-and-scissors concept
 * (images/settings.svg) because it reads better at small size against
 * the grey rest state.
 *
 * SOURCE: images/tools.svg carries an in-file comment crediting "SVG
 * Repo, www.svgrepo.com" -- it is a third-party asset, not an in-house
 * drawing (unlike ICON_TRASH/ICON_COMB). Owner-confirmed 2026-08-09:
 * public domain / open source per SVG Repo's license terms, no
 * attribution required, clear to ship.
 *
 * viewBox is 157x256, not MDI's 24x24 -- and unlike ICON_TRASH/
 * ICON_COMB, it is tall and narrow rather than roughly square. RULED
 * 2026-08-09: every consumer stretches it wider than its native
 * proportions (`preserveAspectRatio="none"`) so it reads as a wrench
 * at a glance instead of a thin sliver next to the trash can --
 * deliberately distorted, not a defect. `ha-svg-icon` does not
 * reliably expose `preserveAspectRatio` as a settable property, so
 * this one icon is rendered as an inline `<svg>` (settingsButtonStyles
 * below), not through `ha-svg-icon` like ICON_TRASH/ICON_COMB.
 *
 * The source file has five `<path>` elements; two are degenerate
 * single-point paths (`M30.1,201` and `M88.9,201`) that draw nothing
 * and are skipped. The three geometry-bearing paths are concatenated
 * into this one constant (multiple subpaths in one `d` string is
 * exactly how the source already draws the two screw-hole rings).
 *
 *   <svg viewBox=${SETTINGS_VIEWBOX} preserveAspectRatio="none">
 *       <path d=${ICON_SETTINGS} fill="currentColor"></path>
 *   </svg>
 */
export const ICON_SETTINGS =
    "M129.7,31.6H92.7c-6.6-0.1-6.4,9.8,0,9.8h36.9v4.9H92.9c-6.7,0-6.5,9.8,0,9.8h36.8v4.9v0.2H92.9c-6.7,0-6.5,9.9,0,9.9h36.8 v4.9H92.9c-6.6,0-6.5,9.8,0,9.8h36.8v4.9H92.9c-6.6,0-6.6,9.9,0,9.8h36.8v5H92.9c-6.6-0.1-6.6,9.8,0,9.8h36.8v4.9H92.9 c-6.6,0-6.6,9.8,0,9.8h36.8v4.9H92.9c-6.6,0-6.5,9.9,0,9.9h36.8v95.5c-0.1,14.6,22.2,14.4,22.2,0V16.9c0-6.6-5.5-15-14.6-15 L92.7,1.8c-6.6,0.1-6.4,9.9,0,9.9h36.9v4.9H92.7c-6.6,0-6.4,9.9,0,9.8h36.9V31.6L129.7,31.6z M87,224.6c-1.3,8.1,1.5,22.6,7.2,27.9c6,5.5,13.1-1.5,10.2-7.2c-3-5.6-6.7-8.7-3.6-22.1L87,224.6L87,224.6z M75.2,177.5v-65.1L62.9,5.3c-0.4-2.9-2.1-3.6-3.8-3.6c-1.6,0-3.4,0.6-3.7,3.6l-12,107.1v65.1c-22.7-11.8-39.7,6.6-39.8,23.3 c0.1,14.9,11.1,27.2,26.8,27.2c15.7-0.1,26.4-13.8,26.4-27.2v-65.4h5v65.4c0,15.5,12.6,27,26,27c16.9,0,27.6-11.9,27.6-26.9 C115.5,184,97.9,165.7,75.2,177.5z M30.1,214.4c-7.4,0-13.3-6-13.4-13.4c0.1-7.3,6-13.3,13.4-13.3c7.4,0,13.4,5.9,13.4,13.3 C43.5,208.4,37.5,214.4,30.1,214.4z M88.9,214.4c-7.3,0-13.3-6-13.3-13.4c0-7.3,5.9-13.3,13.3-13.3c7.4,0,13.4,5.9,13.4,13.3 C102.3,208.4,96.4,214.4,88.9,214.4z";

/** The viewBox ICON_SETTINGS is drawn in. */
export const SETTINGS_VIEWBOX = "0 0 157 256";

/**
 * The device-meta-row settings button. Copied verbatim from
 * .trash-btn above (same anatomy: grey at rest, 3px padding, 4px
 * radius, same transitions, same disabled state) with ONE
 * difference, per owner ruling 2026-08-08: hover is house blue
 * instead of ember, since this button opens a dialog rather than
 * deleting anything.
 *
 * Sized in width AND height, not `width: auto` off a single height
 * value (RULED 2026-08-09, supersedes an earlier uniform-square
 * call): the source drawing is tall and narrow, so height-only
 * sizing read as a thin sliver next to the trash can. 17.6x18 at
 * rest, 19.8x20 on hover -- the explicit width stretches it wider on
 * purpose, via the inline-svg + preserveAspectRatio="none" pattern
 * above. Width bumped ~10% (owner ruling, post-launch bench pass:
 * 16->17.6 rest, 18->19.8 hover) over the original RULED figures;
 * height unchanged.
 */
export const settingsButtonStyles = css`
    .settings-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: none;
        border: none;
        padding: 3px;
        border-radius: 4px;
        cursor: pointer;
        color: var(--disabled-text-color, #999);
        opacity: 0.55;
        transition: background 150ms ease, color 150ms ease,
            opacity 150ms ease;
    }
    .settings-btn:hover:not(:disabled) {
        background: rgba(100, 181, 246, 0.12);
        color: #64b5f6;
        opacity: 1;
    }
    .settings-btn:disabled {
        cursor: default;
        opacity: 0.25;
    }
    .settings-btn .settings-icon {
        display: block;
        width: 17.6px;
        height: 18px;
    }
    .settings-btn:hover:not(:disabled) .settings-icon {
        width: 19.8px;
        height: 20px;
    }
`;
