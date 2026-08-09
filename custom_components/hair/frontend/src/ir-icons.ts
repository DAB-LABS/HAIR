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
 * The mustache gear, from images/mustache-gear.svg. Opens the device
 * settings dialog (Device Settings, 0.9.8). RULED 2026-08-09: replaces
 * the wrench-and-screwdriver drawing (images/tools.svg) the button
 * shipped with -- owner swap, same reasoning as that drawing's own
 * replacement of the earlier comb-and-scissors concept before it: a
 * glyph that reads clearly at small size against the grey rest state.
 * The "NEVER an MDI gear" ruling that ruled out a plain gear for the
 * wrench drawing does not apply here -- this IS a gear, just not
 * MDI's, and the mustache is what keeps it a HAIR house glyph rather
 * than a generic settings cog.
 *
 * SOURCE: images/mustache-gear.svg carries an in-file comment
 * crediting "SVG Repo, www.svgrepo.com" -- a third-party asset, not an
 * in-house drawing (unlike ICON_TRASH/ICON_COMB), same provenance as
 * the wrench drawing it replaces.
 *
 * viewBox is 382.673x382.673 -- square, unlike the wrench drawing's
 * tall-and-narrow 157x256, so none of that drawing's aspect-ratio
 * distortion workaround applies: no `preserveAspectRatio="none"`, and
 * .settings-icon below sizes it as a plain square. Still rendered as
 * an inline `<svg>` rather than through `ha-svg-icon`, matching the
 * wrench drawing's own choice, so a future non-square swap doesn't
 * have to re-plumb the render site.
 *
 * The source file has five `<path>` elements -- the mustache, two
 * screw-hole rings, the gear body (which already carries its own
 * outer-ring subpath), and the inner ring -- all geometry-bearing,
 * concatenated into this one constant in source order (multiple
 * subpaths in one `d` string is exactly how the source already draws
 * the gear body plus its outer ring).
 *
 *   <svg viewBox=${SETTINGS_VIEWBOX}>
 *       <path d=${ICON_SETTINGS} fill="currentColor"></path>
 *   </svg>
 */
export const ICON_SETTINGS =
    "M249.888,188.385c-4.823-24.522-46.884-39.054-56.646-20.663c-9.762-18.392-51.829-3.859-56.658,20.663 c-6.323,25.654-39.754,32.719-58.338,19.337c0,28.971,31.219,29.356,50.533,31.202c45.745-2.01,60.189-23.098,64.463-32.731 c4.262,9.646,18.707,30.722,64.458,32.731c19.325-1.846,50.526-2.242,50.526-31.202 C289.636,221.104,256.216,214.028,249.888,188.385z M193.242,88.324c7.987,0,14.479,6.486,14.479,14.485c0,7.993-6.493,14.479-14.479,14.479 c-7.999,0-14.486-6.486-14.486-14.479C178.756,94.811,185.244,88.324,193.242,88.324z M193.254,268.934c7.987,0,14.468,6.469,14.468,14.468c0,7.987-6.481,14.468-14.468,14.468 c-7.993,0-14.474-6.48-14.474-14.468C178.78,275.403,185.261,268.934,193.254,268.934z M370.687,199.07c0.105-2.499,0.374-4.963,0.374-7.485c0-2.242-0.245-4.432-0.327-6.668 c0.888-4.326,3.06-8.752,5.139-12.839c2.055-4.572,4.215-8.659,4.67-10.977c1.893-7.678-2.568-12.284-7.473-15.273 c-3.492-2.161-7.17-3.573-9.482-5.179c-1.308-4.396-2.86-8.676-4.495-12.933c-0.468-4.595-0.023-9.604,0.374-14.182 c0.595-5.074,1.389-9.687,1.132-12.057c-2.184-13.464-16.371-12.086-23.038-13.762c-2.651-3.708-5.372-7.38-8.291-10.86 c-4.391-8.285-4.776-21.188-7.158-25.036c-6.002-12.424-19.35-6.06-26.087-5.634c-3.725-2.674-7.555-5.162-11.479-7.532 c-6.551-6.901-11.549-18.176-14.818-21.574c-5.406-5.698-11.841-4.227-16.896-2.032c-3.702,1.605-6.901,3.97-9.54,5.155 c-4.602-1.36-9.271-2.61-14.024-3.625c-8.279-4.169-16.301-13.44-20.4-15.192c-7.006-3.206-12.553-0.351-16.64,3.404 c-2.954,2.966-5.214,6.276-7.31,8.238c-4.735,0.204-9.447,0.467-14.071,1.027c-9.295-1.016-20.125-7.578-24.621-7.695 c-7.724-0.969-12.115,3.346-14.602,8.676c-1.875,3.719-2.966,7.573-4.35,10.031c-4.321,1.676-8.513,3.556-12.652,5.564 c-9.353,1.711-21.498-0.274-26.092,0.619c-7.76,1.413-10.019,7.607-10.941,13.037c-0.678,4.017-0.444,8.046-0.894,10.889 c-3.626,3.088-7.176,6.229-10.539,9.593c-7.975,4.735-20.47,6.218-24.032,8.833c-11.765,7.152-4.483,19.816-3.433,26.536 c-2.365,3.959-4.578,7.999-6.65,12.15c-2.843,3.439-7.029,6.323-10.714,9.026c-4.017,3.036-7.853,5.605-9.382,7.426 c-5.395,5.821-3.386,12.098-0.648,16.99c2.067,3.585,4.507,6.54,5.827,9.026c-0.958,4.595-1.618,9.266-2.225,13.966 c-3.772,8.67-11.695,17.662-13.703,21.941c-4.367,12.792,8.478,18.374,13.592,23.01c0.602,4.822,1.255,9.656,2.248,14.351 c-0.455,9.226-6.014,20.295-5.728,24.674c-0.432,13.768,14.1,14.585,20.341,17.364c2.032,4.156,4.221,8.197,6.551,12.179 c1.354,4.263,1.494,9.354,1.733,13.931c0.333,5.021,0.409,9.657,1.075,11.911c1.938,7.706,8.291,9.435,13.873,9.832 c4.151,0.233,7.976-0.21,10.812,0.069c3.299,3.293,6.791,6.365,10.317,9.389c5.354,7.742,8.25,19.828,10.93,23.576 c4.647,6.143,10.895,6.283,16.283,4.904c4.041-1.214,7.643-3.07,10.416-3.771c4.187,2.066,8.431,3.994,12.769,5.733 c3.661,2.511,6.936,6.224,9.855,9.879c3.299,3.877,6.253,7.286,8.192,8.677c3.129,2.276,6.229,3,9.073,2.768 c2.896-0.456,5.535-1.857,7.905-3.492c3.392-2.336,6.16-5.185,8.524-6.68c4.607,0.572,9.277,0.888,13.989,1.121 c8.991,3.002,18.636,10.404,23.074,11.795c7.485,2.65,12.425-1.904,15.822-6.225c2.453-3.246,4.181-6.703,5.921-8.934 c4.694-0.98,9.271-2.241,13.837-3.572c9.354-0.176,20.891,3.9,25.456,3.736c7.684-0.537,11.21-5.71,12.985-10.977 c1.203-4.028,1.611-8.08,2.545-10.801c3.877-2.301,7.684-4.707,11.374-7.299c4.192-1.833,9.225-2.627,14.024-3.082 c5.044-0.689,9.54-1.25,11.747-2.114c7.415-2.662,8.921-8.815,8.688-14.608c-0.093-4.145-0.958-8.057-0.876-10.859 c2.92-3.434,5.629-7.018,8.279-10.685c1.623-1.354,3.352-2.627,5.348-3.725c2.195-1.413,4.543-2.651,6.82-3.772 c4.577-2.265,8.886-4.133,10.73-5.628c10.055-9.167,1.227-20.271-1.027-26.775c1.693-4.344,3.316-8.7,4.694-13.195 c4.554-8.104,15.04-15.367,16.896-19.454C387.246,212.102,374.891,204.488,370.687,199.07z M192.168,350.744 c-87.759,0-159.159-71.405-159.159-159.159c0-87.748,71.399-159.147,159.159-159.147c87.765,0,159.17,71.411,159.17,159.159 C351.338,279.35,279.933,350.744,192.168,350.744z M193.254,41.038c-82.89,0-150.319,67.424-150.319,150.313c0,82.884,67.429,150.296,150.319,150.296 c82.873,0,150.296-67.424,150.296-150.296C343.55,108.45,276.126,41.038,193.254,41.038z M193.254,332.038 c-77.571,0-140.692-63.104-140.692-140.687c0-77.577,63.109-140.691,140.692-140.691c77.571,0,140.685,63.115,140.685,140.691 C333.939,268.934,270.813,332.038,193.254,332.038z";

/** The viewBox ICON_SETTINGS is drawn in. */
export const SETTINGS_VIEWBOX = "0 0 382.673 382.673";

/**
 * The device-meta-row settings button. Copied verbatim from
 * .trash-btn above (same anatomy: grey at rest, same transitions,
 * same disabled state) with ONE difference, per owner ruling
 * 2026-08-08: hover is house blue instead of ember, since this
 * button opens a dialog rather than deleting anything.
 *
 * Sized as a plain square, 26px at rest growing to 29px on hover --
 * the same size-bump-on-hover affordance the button always had, just
 * without the non-square width/height split the wrench drawing
 * needed (RULED 2026-08-09, ICON_SETTINGS above: that drawing was
 * tall and narrow and got stretched wider on purpose; the mustache
 * gear that replaced it is square, so a square box is the correct
 * rendering, not a leftover distortion carried over from the old
 * icon).
 *
 * SIZE BUMP (owner ruling 2026-08-09, bench pass after the mustache
 * gear went live): the original 16px/18px sizing -- inherited as-is
 * from the wrench drawing's own box -- was too small to read the
 * gear teeth or the mustache at a glance. Icon and padding both
 * scaled up ~60% together (16->26, 3->5) so the hit-area keeps the
 * same proportions rather than the icon outgrowing its box.
 */
export const settingsButtonStyles = css`
    .settings-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: none;
        border: none;
        padding: 5px;
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
        width: 26px;
        height: 26px;
    }
    .settings-btn:hover:not(:disabled) .settings-icon {
        width: 29px;
        height: 29px;
    }
`;
