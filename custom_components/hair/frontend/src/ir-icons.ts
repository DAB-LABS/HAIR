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
