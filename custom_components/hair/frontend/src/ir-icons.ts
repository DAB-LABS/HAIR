import { css, html } from "lit";

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
 * The disclosure chevron on a detangle card (owner ruled 2026-09-03).
 *
 * MDI's own, in MDI's 24x24 viewBox rather than the comb's 512 one.
 * Drawn pointing DOWN and turned 180 degrees for the open state, so
 * the two directions are one path and cannot drift into two glyphs
 * that disagree about which way is closed.
 */
export const ICON_CHEVRON_DOWN =
    "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";

/**
 * Its other half (owner ruled 2026-09-04).
 *
 * The Sniffer and Clipper cards do not turn one arrow, they swap two:
 * ICON_EXPAND and ICON_COLLAPSE, declared locally in each of those
 * files. The detangle card wears the same pair now, so a disclosure on
 * this surface and a disclosure on those is the same gesture and the
 * same glyph. The pair lives here rather than as a sixth private copy.
 */
export const ICON_CHEVRON_UP =
    "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z";

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
 *
 * NO rest-state opacity multiplier (owner bugfix ruling 2026-08-12,
 * user reports of the buttons reading as nearly invisible on a light
 * theme). `--disabled-text-color` is already a theme-correct muted
 * tone -- HA computes it separately for light and dark so it has
 * adequate contrast against each theme's own card background.
 * Layering a flat `opacity: 0.55` on top doesn't dim the COLOR, it
 * blends the rendered pixel toward whatever is behind it: on a dark
 * card that still reads as a visible light-grey icon, but on a white
 * or near-white card the same blend washes out toward white, which
 * is exactly the "too light to see" report. Every button in this
 * file that shares this anatomy (trash/settings/edit/download) had
 * the same multiplier and the same bug; all four had it removed
 * together. The hover and :disabled opacities are untouched --
 * :disabled's 0.25 is a real backdrop-independent "this doesn't
 * work" cue, not a rest-state color choice, so it stays.
 *
 * HOVER WASH STRENGTH, ROUND 2 (owner bugfix ruling 2026-08-12, same
 * session): the rgba() background washes on hover have the identical
 * problem the rest-state opacity did -- their visible strength is
 * whatever the alpha blend produces against the card behind them, not
 * a fixed, guaranteed contrast. Trash's ember (230, 81, 0) survived at
 * 12% alpha by luck of the hue: orange is dark and saturated enough
 * that even diluted, it reads as a tint on white. Edit/settings'
 * light pastel blue (100, 181, 246) is already close to white in
 * luminance, so the same 12% diluted it to within a few RGB units of
 * white -- no visible box, just the icon itself turning blue (owner
 * report: "doesn't get a box... just turns the whole glyph blue").
 * All four washes bumped from 12%/16% to a uniform 20% so the box
 * reads reliably on a light card without needing per-hue tuning; a
 * bit more vivid on dark as a side effect, same trade the rest-state
 * fix already made and the owner accepted there.
 *
 * Download's hover icon color was the more broken case: a literal
 * `#fff`, not a wash-alpha problem at all. White-on-white has no
 * contrast full stop, regardless of the background wash -- it was
 * only ever legible against a dark card. Swapped to
 * `var(--primary-text-color)`, HA's own strongest text token: near-
 * black on light theme, near-white on dark, computed by HA itself so
 * it never needs to know which theme is active. Keeps the "gray
 * family, no accent hue" rule the download button was built under
 * (owner ruling 2026-08-11) -- this is neutral in both directions,
 * not a new color.
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
        transition: background 150ms ease, color 150ms ease,
            opacity 150ms ease;
    }
    .trash-btn:hover:not(:disabled) {
        background: rgba(230, 81, 0, 0.2);
        color: #e65100;
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
 * Sized as a plain square, fixed at 29px in both rest and hover --
 * the same 29px the earlier size-bump-on-hover affordance grew INTO
 * on hover (RULED 2026-08-09, bench pass): a fixed icon size reads
 * cleaner than a size change, since growing the icon on hover shifts
 * the emitter chips beside it. Hover now only changes background/
 * color/opacity, same as .trash-btn.
 *
 * SIZE BUMP (owner ruling 2026-08-09, bench pass after the mustache
 * gear went live): the original 16px/18px sizing -- inherited as-is
 * from the wrench drawing's own box -- was too small to read the
 * gear teeth or the mustache at a glance. Icon and padding both
 * scaled up ~60% together (16->26, 3->5) so the hit-area keeps the
 * same proportions rather than the icon outgrowing its box. A second
 * bench pass the same day dropped the rest/hover split entirely
 * (26->29 rest, so both states land on the hover size, the one that
 * read best) once the size CHANGE itself -- not just the small
 * resting size -- turned out to be the thing that read as unclean.
 *
 * BOTTOM-ALIGNED (owner ruling 2026-08-15, reverses the 2026-08-09
 * top-alignment ruling above): explicit align-self so this button
 * stays pinned to the BOTTOM of its containing cell instead --
 * .device-meta's grid row on the Device side, .trh-header's flex row
 * on the Remote side -- so it stays low against the commands/triggers
 * list that follows, regardless of how tall the Emitters/Receivers
 * chip group above it grows. One shared style, both call sites, so
 * this single change covers both settings gears per the owner's own
 * framing ("both ... should be justified to the bottom of the cell
 * that they're in").
 */
export const settingsButtonStyles = css`
    .settings-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        align-self: end;
        background: none;
        border: none;
        padding: 5px;
        border-radius: 4px;
        cursor: pointer;
        color: var(--disabled-text-color, #999);
        transition: background 150ms ease, color 150ms ease,
            opacity 150ms ease;
    }
    .settings-btn:hover:not(:disabled) {
        background: rgba(100, 181, 246, 0.2);
        color: #64b5f6;
    }
    .settings-btn:disabled {
        cursor: default;
        opacity: 0.25;
    }
    .settings-btn .settings-icon {
        display: block;
        width: 29px;
        height: 29px;
    }
`;

/**
 * The row-level edit pencil, from images/text-edit-hair.svg -- the
 * real edit glyph that replaces every ICON_COPY-as-edit-button
 * across the panel (edit-button-pass.md). One path, one place, so a
 * size or treatment change updates every installed surface at once.
 *
 * NOT the stroke-based two-path drawing edit-button-pass.md
 * describes -- the asset actually on disk is a filled single path
 * (fill, not stroke; native viewBox 144 144 512 512, not 0 0 24 24),
 * the same shape ICON_TRASH/ICON_COMB/ICON_SETTINGS already are.
 * Owner-confirmed 2026-08-11: render it through ha-svg-icon like
 * those three rather than building the inline-svg stroke handling
 * the spec assumed -- that handling doesn't apply to this asset.
 *
 *   <ha-svg-icon .path=${ICON_EDIT} .viewBox=${EDIT_VIEWBOX}></ha-svg-icon>
 */
export const ICON_EDIT =
    "m537.43 321.7c10.555-9.9219 16.66-23.68 16.938-38.16 0.27734-14.484-5.2969-28.465-15.465-38.781-10.168-10.316-24.07-16.094-38.555-16.027-14.672 0.44141-28.617 6.5078-38.941 16.941l-202.73 202.73-13.5 89.523 89.523-13.5zm-61.777-61.777c6.1797-6.8438 14.898-10.852 24.117-11.086 9.2188-0.23047 18.129 3.3281 24.648 9.8477 6.5234 6.5195 10.082 15.43 9.8477 24.648s-4.2422 17.938-11.086 24.117l-17.504 17.504-47.52-47.535zm-206.46 253.99 8.4219-55.949 166.3-166.3 47.52 47.535-166.29 166.29zm322.26 37.195v20.152h-382.89v-20.152z";

/** The viewBox ICON_EDIT is drawn in. */
export const EDIT_VIEWBOX = "144 144 512 512";

/**
 * The row-level edit button, shared by every surface that swaps its
 * copy-glyph edit affordance for the real pencil (edit-button-pass.md
 * commit 1). RULED (owner 2026-08-11): the helper -- glyph, markup,
 * tooltip wiring, treatment, and size all live here, so one change
 * updates every installed surface. Only PLACEMENT (the helper call
 * site, immediately left of that row's trash can) stays per-surface;
 * a button cannot position itself in someone else's row.
 *
 * Treatment is .trash-btn's anatomy (grey rest, same radius/
 * transitions/disabled state) with the settings button's blue hover
 * (edit opens an editor, same non-destructive family as settings,
 * not delete) rather than minting a third copy of that hover pair.
 * FOURTH bench ruling (2026-08-11): edit and trash now also sit in
 * their own .edit-trash-group wrapper (ir-command-row.ts) with a
 * zero flex gap, so the two buttons' hover boxes butt directly
 * against each other rather than sitting the row's shared 4px gap
 * apart.
 *
 * FIFTH bench ruling (2026-08-11): box matched to .trash-btn's
 * exactly -- 24x24 hover box, same as the can beside it (was 26x28
 * against trash's 24x24, i.e. 2px wider from the padding asymmetry,
 * 4px taller from the 22px icon that pass dropped back down from).
 * Three earlier bench passes (19->20->22px) chased visual parity
 * with the trash can's weight before landing here; the box-match
 * ruling took priority over that pursuit.
 *
 * SIXTH bench ruling (2026-08-11): box held fixed at 24x24, glyph
 * bumped back up within it -- 18px icon / 3px padding to 20px icon /
 * 2px padding (18+2*3=20+2*2=24, box unchanged). Lets the pencil
 * claw back a little of the visual weight the fifth pass's box-match
 * cost it, without reopening the box-size question. Still a shade
 * lighter than the can at equal box size either way (ink fills
 * ~75% x 67% of its viewBox vs the can's ~72% x 76%, confirmed via
 * getBBox on both paths in the second bench pass -- not a CSS
 * stretch, the rendered icon box remains a verified 1:1 square at
 * every size checked).
 *
 * SEVENTH bench ruling (2026-08-11): vertical padding split
 * asymmetric -- 2px both sides unchanged, but top/bottom goes from
 * an even 2px/2px to 3px/1px (3+20+1=24, box still unchanged). The
 * even split was landing the pencil's bottom edge about a pixel
 * above the trash can's, reading as a hairline misalignment along
 * the row; nudging the icon down within its own box by shaving a
 * pixel off the bottom padding and adding it to the top brings the
 * two glyphs' bottom edges into line without touching the box
 * itself.
 */
export const editButtonStyles = css`
    .edit-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: none;
        border: none;
        padding: 3px 2px 1px;
        border-radius: 4px;
        cursor: pointer;
        color: var(--disabled-text-color, #999);
        transition: background 150ms ease, color 150ms ease,
            opacity 150ms ease;
    }
    .edit-btn:hover:not(:disabled) {
        background: rgba(100, 181, 246, 0.2);
        color: #64b5f6;
    }
    .edit-btn:disabled {
        cursor: default;
        opacity: 0.25;
    }
    .edit-btn ha-svg-icon {
        --mdc-icon-size: 20px;
    }
`;

/**
 * Exit-to-entity's own treatment -- split out from editButtonStyles
 * (owner bench pass, 2026-08-12): the glyph read too big at edit's
 * 20px/24x24, so this button now diverges rather than sharing edit's
 * box. Owner ruling: 20% smaller glyph (20px -> 16px) and 2px padding
 * on every side (was inheriting edit's 3px/2px/1px top/side/bottom,
 * tuned for edit's own bottom-edge alignment against trash -- a
 * concern that doesn't apply here), landing on a 20x20 box, centered
 * on both axes as the owner originally asked for this button.
 * Hover/rest color treatment (grey rest, blue #64b5f6 hover) is
 * unchanged and still matches edit's own -- only size and padding
 * split off.
 */
export const exitToEntityButtonStyles = css`
    .exit-to-entity-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: none;
        border: none;
        padding: 2px;
        border-radius: 4px;
        cursor: pointer;
        color: var(--disabled-text-color, #999);
        transition: background 150ms ease, color 150ms ease,
            opacity 150ms ease;
    }
    .exit-to-entity-btn:hover {
        background: rgba(100, 181, 246, 0.2);
        color: #64b5f6;
    }
    .exit-to-entity-btn ha-svg-icon {
        --mdc-icon-size: 14px;
    }
`;

/**
 * Shared edit-button template. Placement is the only thing left to
 * the caller: put this immediately left of the row's trash can.
 * `disabled` mirrors the row's own busy state so the edit button
 * dims exactly like the trash can beside it.
 */
export function renderEditBtn(
    onClick: (e: Event) => void,
    title: string,
    disabled = false,
) {
    return html`
        <button
            class="edit-btn"
            ?disabled=${disabled}
            @click=${onClick}
            title=${title}
            aria-label=${title}
        >
            <ha-svg-icon .path=${ICON_EDIT} .viewBox=${EDIT_VIEWBOX}></ha-svg-icon>
        </button>
    `;
}

/**
 * The climate-preset star, from images/star.svg
 * (climate-presets-star-handoff.md, owner-approved 2026-08-17).
 *
 * The source file is ONE path holding two overlapping star shapes in
 * the same rotation, wound in opposite directions: an outer point and
 * a slightly smaller inset one. Rendered together under the default
 * nonzero fill rule they cancel in the middle and draw a hollow
 * outline star; rendered with only the first subpath (everything up
 * to the first `z`) the same asset draws a solid star. One file, two
 * looks -- the same technique ICON_EDIT/ICON_TRASH already rely on
 * here, and the reason there is no second SVG asset for the filled
 * state.
 *
 * Fill-based, so both render through ha-svg-icon like every other
 * glyph in this file, never as inline stroke SVG:
 *
 *   <ha-svg-icon .path=${ICON_STAR} .viewBox=${STAR_VIEWBOX}></ha-svg-icon>
 */
export const ICON_STAR =
    "M19.38 12.803l-3.38-10.398-3.381 10.398h-11.013l8.925 6.397-3.427 10.395 8.896-6.448 8.895 6.448-3.426-10.395 8.925-6.397h-11.014zM20.457 19.534l2.394 7.261-6.85-4.965-6.851 4.965 2.64-8.005-0.637-0.456-6.228-4.464h8.471l2.606-8.016 2.605 8.016h8.471l-6.864 4.92 0.245 0.744z";

/** The same asset's first subpath alone: the solid, starred look. */
export const ICON_STAR_FILLED =
    "M19.38 12.803l-3.38-10.398-3.381 10.398h-11.013l8.925 6.397-3.427 10.395 8.896-6.448 8.895 6.448-3.426-10.395 8.925-6.397h-11.014z";

/** The viewBox both star paths are drawn in (the asset's native one). */
export const STAR_VIEWBOX = "0 0 32 32";

/**
 * The star's own delta on top of editButtonStyles' box.
 *
 * RULED (climate-presets-star-handoff.md): the star reuses
 * `.edit-btn`'s box WHOLESALE rather than copying its numbers, so a
 * future bench pass on the pencil's box carries the star along for
 * free instead of drifting out of sync -- which is why the button
 * below wears `class="edit-btn star-btn"` and this block adds only
 * what edit does not already say. Rest colour, hover wash, radius,
 * padding and the 20px glyph all come from editButtonStyles; a
 * surface using this must include BOTH.
 *
 * The starred colour (#4dabf7, the app's focus-ring blue) is
 * deliberately NOT the hover wash's #64b5f6: a starred row has to
 * still read as starred once the mouse has moved off it and nothing
 * is hovered. Specificity keeps them in the right order without
 * !important -- `.edit-btn:hover:not(:disabled)` outranks
 * `.star-btn.on`, so hovering a starred star still washes blue, and
 * `.star-btn.on` outranks `.edit-btn`, so a starred star at rest is
 * never grey.
 *
 * No gold anywhere: the plan's original #f5a623 fill is retired by
 * the handoff, not parked, and must not come back as a dead variable.
 */
export const starButtonStyles = css`
    /* Owner bench ruling 2026-08-17, third look: the GLYPH loses a
       pixel and gains a pixel of height above it; the BOX does not
       move. 19px icon with 2px above and 3px below still totals
       edit's 24, and 2.5px either side still totals 24 across, so the
       star keeps the same 24x24 hover target and the same x position
       in the row -- only the drawing inside it shifts. This is the
       one place the star stops inheriting edit's geometry; colour,
       hover, radius, transition and disabled state all still come
       from editButtonStyles, so a future pass on those still carries
       the star along. */
    .star-btn {
        padding: 2px 2.5px 3px;
    }
    .star-btn ha-svg-icon {
        --mdc-icon-size: 19px;
    }
    .star-btn.on {
        color: #4dabf7;
    }
    .star-btn:focus-visible {
        outline: 2px solid #4dabf7;
        outline-offset: 2px;
    }
`;

/**
 * Shared star-button template. Placement is the caller's (the row's
 * .actions cluster, immediately left of the edit/trash pair, one
 * normal 4px gap away from it -- it is deliberately NOT fused into
 * that pair's zero-gap treatment, which was a ruling about edit and
 * trash's own relationship).
 *
 * One click toggles, no dialog and no confirmation, like every other
 * toggle-style control in this panel. A real <button>, so Enter and
 * Space work and the focus ring above has something to draw on.
 */
export function renderStarBtn(
    onClick: (e: Event) => void,
    title: string,
    starred: boolean,
    disabled = false,
) {
    return html`
        <button
            class="edit-btn star-btn${starred ? " on" : ""}"
            ?disabled=${disabled}
            @click=${onClick}
            title=${title}
            aria-label=${title}
            aria-pressed=${starred ? "true" : "false"}
        >
            <ha-svg-icon
                .path=${starred ? ICON_STAR_FILLED : ICON_STAR}
                .viewBox=${STAR_VIEWBOX}
            ></ha-svg-icon>
        </button>
    `;
}

/**
 * The exit-to-entity glyph, from images/exit-to-entity.svg
 * (owner-supplied, verified 2026-08-12): fill-based single path,
 * native viewBox 0 0 512 512, arrow-out-of-box. Renders through
 * ha-svg-icon like ICON_EDIT/ICON_TRASH/ICON_COMB -- not the stroke
 * trap edit-button-pass.md warned about for ICON_EDIT's own asset.
 * The source file's hardcoded fill="#000000" and 800px width/height
 * are dropped on export; currentColor and --mdc-icon-size drive it
 * exactly like every other shared glyph here.
 *
 * docs/internal/plans/exit-to-entity-link.md (owner go 2026-08-12):
 * the go-to-HA link on the controlled-device detail header. Same
 * one-spot family rule as edit -- glyph, helper, and treatment all
 * live here so the later trigger-remote header install (Track B,
 * signpost 1) is a call site, not a second implementation.
 */
export const ICON_EXIT_TO_ENTITY =
    "M421.24,269.93h30V429.84a48.72,48.72,0,0,1-48.66,48.66H82.77a48.72,48.72,0,0,1-48.66-48.66V110A48.72,48.72,0,0,1,82.77,61.37H242.68v30H82.77A18.68,18.68,0,0,0,64.11,110V429.84A18.68,18.68,0,0,0,82.77,448.5H402.58a18.68,18.68,0,0,0,18.66-18.66Zm-69-236.43v30h74.4L249.5,240.68l21.21,21.21L447.89,84.71v74.4h30V33.5Z";

/** The viewBox ICON_EXIT_TO_ENTITY is drawn in -- its own native one,
 * unlike ICON_DOWNLOAD's, needed no adjustment (measured margins
 * already read close to ICON_EDIT/ICON_TRASH's own ~13-16%). */
export const EXIT_TO_ENTITY_VIEWBOX = "0 0 512 512";

/**
 * SPA-navigate to an in-app HA path without a full page reload --
 * the standard history.pushState + location-changed event idiom the
 * HA frontend itself listens for (there is no existing helper or
 * navigate() call anywhere else in this codebase to reuse; this is
 * that idiom reimplemented locally rather than a new invention).
 */
function _spaNavigate(href: string): void {
    history.pushState(null, "", href);
    window.dispatchEvent(
        new CustomEvent("location-changed", { bubbles: true, composed: true }),
    );
}

/**
 * Shared exit-to-entity template: a REAL <a href> so middle-click and
 * ctrl/cmd-click open a new tab natively, with a plain left click
 * intercepted for in-app SPA navigation instead of a full reload.
 * Guard is the caller's job (docs/internal/plans/exit-to-entity-
 * link.md: no ha_device_id -> don't call this at all, no dead
 * buttons) -- href is always assumed real here.
 */
export function renderExitToEntityBtn(href: string, title: string) {
    return html`
        <a
            class="exit-to-entity-btn"
            href=${href}
            title=${title}
            aria-label=${title}
            @click=${(e: MouseEvent) => {
                if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
                    return;
                }
                e.preventDefault();
                _spaNavigate(href);
            }}
        >
            <ha-svg-icon
                .path=${ICON_EXIT_TO_ENTITY}
                .viewBox=${EXIT_TO_ENTITY_VIEWBOX}
            ></ha-svg-icon>
        </a>
    `;
}

/**
 * The download arrow, from images/dl.svg (owner-supplied hand-drawn
 * glyph, same provenance as ICON_TRASH/ICON_EDIT -- second version
 * uploaded 2026-08-11, the first was swapped before use). Two
 * subpaths (the arrow, the tray) concatenated into one constant in
 * source order, same technique ICON_SETTINGS's five subpaths use --
 * both carry the same fill, so one combined `d` renders identically
 * to the two separate `<path>` elements the source file draws them
 * as. The source also wraps both paths in a `<g clip-path>` against a
 * tight bounding rect; dropping it renders pixel-identical (checked
 * by rendering both), so ha-svg-icon's plain .path/.viewBox handles
 * this one same as the other three, no inline-svg detour required.
 *
 * The path data itself is untouched below -- what changes between
 * revisions is DOWNLOAD_VIEWBOX, not this constant.
 *
 *   <ha-svg-icon .path=${ICON_DOWNLOAD} .viewBox=${DOWNLOAD_VIEWBOX}></ha-svg-icon>
 */
export const ICON_DOWNLOAD =
    "M70.5399 108.42C69.3338 107.513 68.0817 106.668 66.79 105.887L66.5124 105.725C63.2036 103.8 59.7827 101.808 56.3215 100.016C55.4321 99.5562 54.5374 99.0465 53.672 98.5523C51.2995 97.1989 48.8472 95.8003 46.0348 95.1284C45.911 95.0987 45.7812 95.1052 45.6609 95.1472C45.5406 95.1885 45.4349 95.2635 45.3562 95.3636L44.0191 97.0516C43.9434 97.1472 43.8957 97.2622 43.881 97.3837C43.8664 97.5045 43.8854 97.6272 43.9361 97.7377C44.0282 97.9399 44.1047 98.1453 44.18 98.345C44.3355 98.8443 44.5789 99.312 44.8989 99.7262C52.189 108.197 61.1179 115.771 73.8466 124.285C74.6232 124.777 75.4361 125.213 76.2775 125.586C77.3986 126.147 78.6319 126.451 79.8866 126.475C81.5714 126.454 83.192 125.825 84.4467 124.705C84.7153 124.48 84.9891 124.259 85.2628 124.038C85.8532 123.565 86.4631 123.074 87.0236 122.528C88.5696 121.024 90.1227 119.527 91.683 118.036C95.8188 114.066 100.095 109.961 104.095 105.722C106.573 102.979 108.877 100.085 110.993 97.0555C111.699 96.0865 112.405 95.1168 113.123 94.1614L113.203 94.0554C113.618 93.514 114.587 92.2466 113.158 90.7652C113.04 90.6438 112.881 90.5714 112.711 90.5624C110.291 90.4429 108.679 91.8544 107.124 93.2285C106.542 93.7686 105.923 94.2673 105.271 94.7202C102.835 96.3946 100.509 98.2235 98.3094 100.196L97.9078 100.541C96.7835 101.506 95.6982 102.54 94.6485 103.54C93.6455 104.495 92.6075 105.483 91.5487 106.399C90.8195 107.028 90.1344 107.726 89.4726 108.401C88.2361 109.778 86.8134 110.977 85.2447 111.963C85.2356 111.892 85.2272 111.823 85.2187 111.754C85.1311 111.197 85.0864 110.634 85.0844 110.07C85.1876 106.449 85.2998 102.827 85.4218 99.2048C85.6093 93.4204 85.8033 87.4389 85.9311 81.5517C85.9713 79.7112 86.0128 77.8694 86.0563 76.0276C86.4378 59.5541 86.8315 42.526 85.3355 25.7877C84.799 19.7797 83.8888 13.7171 83.0091 7.8519L82.6399 5.38326C82.4154 4.44906 82.0035 3.56993 81.428 2.79919C81.0764 2.23457 80.6781 1.59443 80.2324 0.77786C80.172 0.667915 80.0825 0.577258 79.9729 0.516044C79.8632 0.45483 79.7387 0.425157 79.6128 0.431506C79.4876 0.437856 79.3663 0.479415 79.2638 0.551373C79.1606 0.623332 79.0802 0.722988 79.0322 0.838425C77.5134 4.44062 77.4641 7.54543 77.4206 10.2839C77.4057 11.2406 77.3914 12.1454 77.3201 13.0434C77.1975 14.5886 77.0482 16.132 76.899 17.674C76.7102 19.6205 76.5156 21.6335 76.38 23.6219C76.1854 26.4857 76.0634 29.3997 75.9466 32.217C75.909 33.1111 75.8707 34.0048 75.8325 34.8988L75.7909 35.8369C75.6411 39.2247 75.4867 42.7273 75.3731 46.1764C75.2687 49.3703 75.1882 52.7459 75.1221 56.7997C75.0793 59.3838 75.0572 61.9716 75.0351 64.5589L75.0027 68.0823C74.991 69.2541 74.9768 70.426 74.9605 71.5979C74.9274 74.1438 74.8957 76.777 74.8957 79.3688C74.8989 82.7029 74.9197 86.6514 75.0429 90.6651C75.0935 92.3267 75.1915 94.0095 75.2869 95.6394C75.3946 97.4832 75.5055 99.3863 75.5464 101.26C75.5717 102.388 75.6644 103.539 75.754 104.651C76.0258 107.03 76.0401 109.432 75.7961 111.814C73.9556 110.825 72.1981 109.69 70.5399 108.42Z M154.191 82.8574C153.744 82.6106 153.249 82.4626 152.739 82.4239C152.229 82.3858 151.717 82.4581 151.238 82.6351C151.144 82.661 151.057 82.7068 150.984 82.7689C150.91 82.8315 150.851 82.9097 150.81 82.9975C149.077 86.7444 148.595 106.976 148.244 121.748C148.106 127.519 147.995 132.178 147.842 134.431C147.03 134.508 146.264 134.589 145.533 134.667C143.717 134.86 142.147 135.026 140.568 135.063C134.253 135.214 126.785 135.366 119.282 135.366H119.171C114.222 135.366 109.273 135.373 104.323 135.386C88.7155 135.414 72.5763 135.446 56.7109 135.16C47.361 134.991 37.8547 134.392 28.6611 133.812C24.7952 133.568 20.7976 133.316 16.8635 133.102C16.1358 133.045 15.4119 132.948 14.6953 132.809C14.4358 132.765 14.1699 132.72 13.8902 132.676C13.839 132.333 13.7844 131.996 13.7306 131.661C13.552 130.672 13.4266 129.674 13.3549 128.671C13.1928 125.566 13.0585 122.46 12.9236 119.352C12.6887 113.939 12.4461 108.341 12.0555 102.841C11.6403 96.9761 11.0487 87.1269 10.734 81.7804C10.68 80.7727 10.2445 79.8217 9.51493 79.1208C8.78547 78.4199 7.81622 78.02 6.80248 78.0019C5.76165 77.9799 4.75243 78.3578 3.98434 79.0575C3.21626 79.7578 2.74829 80.7248 2.67764 81.7591C2.03731 91.7162 0.623654 116.375 1.32302 130.28L1.36784 131.236C1.39112 133.382 1.6372 135.521 2.10221 137.617C3.06562 141.327 5.29413 142.991 9.55198 143.181C12.9314 143.333 16.3101 143.512 19.6882 143.691C25.0729 143.976 30.6451 144.272 36.131 144.446C48.1596 144.834 59.051 145.054 69.4272 145.129C74.0522 145.163 78.6766 145.205 83.3016 145.257C91.5928 145.343 100.003 145.431 108.457 145.431C119.85 145.431 131.324 145.272 142.687 144.74C145.152 144.671 147.609 144.442 150.044 144.055C153.921 143.366 156.099 140.985 156.341 137.169C156.435 135.68 156.557 134.072 156.681 132.447C156.848 130.243 157.022 127.964 157.13 125.881C157.052 111.441 155.603 86.7373 155.324 84.7993C155.288 84.413 155.169 84.0396 154.973 83.7043C154.777 83.369 154.51 83.0796 154.191 82.8574Z";

/**
 * The viewBox ICON_DOWNLOAD is drawn in.
 *
 * NOT the source file's own "0 -6 158 158" -- dl.svg's ink runs
 * almost edge to edge in its native viewBox (under 1% clearance on
 * the left/right, ~4% top/bottom, measured by rendering the path and
 * finding its ink bounding box), unlike ICON_EDIT and ICON_TRASH,
 * whose own source drawings carry ~13-16% breathing room baked in on
 * every side. At matching --mdc-icon-size and identical CSS padding,
 * that difference is exactly why the download glyph read larger and
 * its padding read as "almost zero" next to edit/trash (owner
 * observation, 2026-08-12) -- the CSS padding numbers were never
 * wrong, the source artwork just had nothing built in around it the
 * way the other two do.
 *
 * Fix is here, not in the padding: this viewBox pads the SAME path
 * data out to margins of ~12.5% left/right and ~16.5% top/bottom,
 * matched by rendering both against ICON_EDIT's own measured margins
 * and checking the fractions land within a point of each other. The
 * path string above is untouched -- widening the viewBox around
 * identical coordinates is what makes the ink occupy a smaller,
 * centered fraction of the icon box, the same way edit and trash's
 * source files already draw their glyphs with room to spare.
 */
export const DOWNLOAD_VIEWBOX = "-25 -36 209 217";

/**
 * The download button. HAIR Closet only for now, sitting inside the
 * shared edit-trash-group between edit and trash (owner ruling
 * 2026-08-11: "I want to place it between the edit and delete
 * buttons"). Padding is .edit-btn's own 3px/2px/1px, unchanged --
 * owner ruling 2026-08-12 was explicit that the padding should stay
 * "similar to the edit button" rather than grow to force a literal
 * 24x24 box; icon is 19px (20->18->17->18->19: a fourth single-pixel
 * bench nudge), so the button sits at 23x23, a shade under edit/
 * trash's 24x24 the same way it has through every pass.
 *
 * Deliberately its own third hover treatment rather than reusing
 * edit's blue or trash's ember: gray at rest, gray wash on hover, no
 * accent hue at all ("we'll keep it in the gray family," owner ruling
 * 2026-08-11) -- download is neither the destructive act trash is nor
 * the editing act edit is, so it earns neither of those two meanings.
 * Hover icon color started as a literal white (fine against the dark
 * card it was designed against) and was later swapped to
 * `var(--primary-text-color)` once it turned out to be invisible on a
 * light theme -- see the hover-wash doc comment above trashButtonStyles
 * for the full fix (owner bugfix ruling 2026-08-12). Still gray-
 * family: that token is neutral in both directions, not a new hue.
 *
 * Sizing history (owner bench passes, 2026-08-12): first pass dropped
 * --mdc-icon-size from 20px (edit/trash's own size) to 18px, since
 * the glyph read visibly larger even at an identical nominal size --
 * see DOWNLOAD_VIEWBOX's own doc comment for why (near-zero built-in
 * margin in the source artwork). A second pass, after the viewBox fix
 * above gave the glyph real margin, took it down one pixel further to
 * 17px and confirmed the padding numbers should stay exactly what
 * .edit-btn already uses rather than grow to force a matching 24x24
 * box. A third pass judged 17px too small once the margin fix was
 * live -- brought back up to 18px. A fourth pass judged 18px still a
 * shade light next to edit/trash's weight -- 19px, still .edit-btn's
 * padding untouched (owner ruling: "just do the padding 1 on the
 * bottom and 3 on the top like the edit button" -- already exactly
 * what this padding is and has been since the viewBox fix, confirmed
 * rather than changed).
 */
export const downloadButtonStyles = css`
    .download-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: none;
        border: none;
        padding: 3px 2px 1px;
        border-radius: 4px;
        cursor: pointer;
        color: var(--disabled-text-color, #999);
        transition: background 150ms ease, color 150ms ease,
            opacity 150ms ease;
    }
    .download-btn:hover:not(:disabled) {
        background: rgba(153, 153, 153, 0.2);
        color: var(--primary-text-color);
    }
    .download-btn:disabled {
        cursor: default;
        opacity: 0.25;
    }
    .download-btn ha-svg-icon {
        --mdc-icon-size: 19px;
    }
`;

/**
 * Shared download-button template, same shape as renderEditBtn.
 */
export function renderDownloadBtn(
    onClick: (e: Event) => void,
    title: string,
    disabled = false,
) {
    return html`
        <button
            class="download-btn"
            ?disabled=${disabled}
            @click=${onClick}
            title=${title}
            aria-label=${title}
        >
            <ha-svg-icon .path=${ICON_DOWNLOAD} .viewBox=${DOWNLOAD_VIEWBOX}></ha-svg-icon>
        </button>
    `;
}
