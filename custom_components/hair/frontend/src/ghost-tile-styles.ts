/**
 * The ghost tile's look, shared (Plucker ghosts, 1.4.1).
 *
 * Moved here verbatim from ir-ghost-tile.ts so the Plucker's ghosts
 * wear the SAME sheet as the Devices page add tiles and the two cannot
 * drift apart. Only the tile's `:host { display: contents }` stayed behind,
 * since it describes that element and would collapse any host that
 * adopted it.
 *
 * Everything below is keyed on `.gt-*` classes. The kind colours
 * (`.gt-tile.device`, `.gt-tile.remote`) are the Devices page's; a
 * consumer that wants another hover colour sets the tile's three edge
 * properties itself, as the Plucker does with its own slate.
 */
import { css, unsafeCSS } from "lit";
import { ORIGIN_COLORS } from "./ir-origin-colors.js";

export const ghostTileStyles = css`
    .gt-tile.gt-busy {
        cursor: progress;
    }
    .gt-spinner {
        width: 16px;
        height: 16px;
        border: 2px solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        opacity: 0.7;
        animation: gt-spin 900ms linear infinite;
    }
    @keyframes gt-spin {
        to {
            transform: rotate(360deg);
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .gt-spinner {
            animation: none;
        }
    }
    /* THE EDGE. The tile's border is three custom properties, and
       the two buttons draw their own border from the same three
       (owner, 2026-11-14 on VM999: the buttons dashed like the card
       around them). Hover and drag-over change the properties, not
       the border, so the buttons follow the tile and the two
       cannot drift apart. */
    .gt-tile {
        --gt-edge-width: 1.5px;
        --gt-edge-style: dashed;
        --gt-edge-color: var(--divider-color);
        border-radius: 8px;
        border: var(--gt-edge-width) var(--gt-edge-style) var(--gt-edge-color);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 2px;
        /* Not a control any more: only the two buttons take the
           pointer (owner, 2026-11-13). */
        cursor: default;
        transition: border-color 150ms ease, background 150ms ease,
            color 150ms ease;
        color: var(--secondary-text-color);
        padding: 12px;
    }
    /* At rest the tile is a faded grey and nothing more (punch
       list item 22). It sits in a grid of real cards carrying real
       names and counts, and at full strength it competed with them
       for attention it has not earned -- it is an invitation, not
       a thing that exists yet. One rule dims the whole tile, so
       the border, the glyph and the hint fade together and cannot
       drift apart. Opacity rather than three dimmer colors: the
       glyph already inherits currentColor and the hint already
       inherits on hover, so a single value keeps all three in step
       through every state, including whatever the theme does with
       them.

       Full strength returns on hover, focus and dragover, where
       the kind color takes over exactly as before -- item 21
       closed those states as built, and this does not touch them
       beyond restoring the tile to 1. */
    .gt-tile {
        opacity: 0.55;
        transition: border-color 150ms ease, background 150ms ease,
            color 150ms ease, opacity 150ms ease;
    }
    /* Focus now lands on a button inside the tile, not on the
       tile, so the tile answers a button's :focus-visible where it
       used to answer its own. Keyboard focus only: a mouse click
       leaves the button focused, and :focus-within would keep the
       tile lit after it. */
    .gt-tile:hover,
    .gt-tile:has(.gt-btn:focus-visible),
    .gt-tile.gt-dragover {
        opacity: 1;
    }
    .gt-tile:hover,
    .gt-tile:has(.gt-btn:focus-visible) {
        background: var(--secondary-background-color);
        outline: none;
    }
    .gt-tile.device:hover,
    .gt-tile.device:has(.gt-btn:focus-visible) {
        --gt-edge-color: ${unsafeCSS(ORIGIN_COLORS.device)};
        color: ${unsafeCSS(ORIGIN_COLORS.device)};
    }
    .gt-tile.remote:hover,
    .gt-tile.remote:has(.gt-btn:focus-visible) {
        --gt-edge-color: ${unsafeCSS(ORIGIN_COLORS.remote)};
        color: ${unsafeCSS(ORIGIN_COLORS.remote)};
    }
    /* The compact tile takes its height from the row and carries no
       floor of its own: with one, it became the tallest item in the
       Remotes grid and set the row instead of following it (punch
       list item 12, ~92px against ~72px cards). Devices never
       showed that -- those cards are taller than the floor was. */
    .gt-tile-full {
        grid-column: 1 / -1;
        min-height: 120px;
        padding: 24px;
    }
    .gt-tile-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--primary-text-color);
    }
    /* Readability pass (punch list item 14): a 65-character
       sentence set italic at 11.5px was the actual cause of the
       owner's "hard to read", not a rendering artifact. Italic
       strokes cost disproportionately at this size, so it goes
       entirely, the size comes up, and the line box gets room to
       breathe. */
    .gt-tile-hint {
        font-size: 0.8rem;
        color: var(--secondary-text-color);
        line-height: 1.35;
    }
    /* The hint was the one part of the tile that stayed grey while
       everything around it took the kind color on hover. */
    .gt-tile:hover .gt-tile-hint,
    .gt-tile:has(.gt-btn:focus-visible) .gt-tile-hint {
        color: inherit;
    }
    /* The plus and the folder (owner, 2026-11-13): two squares
       with rounded corners, a little tighter than the tile's 8px
       so they read as the tile's own. Stroke icons inline, in
       currentColor, as the round plus was: rendered through
       ha-svg-icon a stroke icon comes out as hairline garbage,
       because that element paints path data as fill
       (edit-button-pass.md). Their border is the tile's own edge
       (THE EDGE, above), dashed at rest and solid on drag-over, and
       their icon takes the tile's color, so the kind color on hover
       carries both.
       Both layouts get them; the full layout's are larger, where
       its text "+" was. Owner, 2026-11-14 on VM999: about 20%
       smaller than first built (32 and 40 px), so 26 and 32 px. On a
       touch screen each button's hit area reaches 4 px past its
       edge, so the small pair is 34 px to a finger without looking
       bigger; the 8 px gap keeps the two hit areas from touching. */
    .gt-buttons {
        display: flex;
        gap: 8px;
        margin-bottom: 4px;
    }
    .gt-btn {
        position: relative;
        width: 26px;
        height: 26px;
        padding: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 5px;
        border: var(--gt-edge-width) var(--gt-edge-style) var(--gt-edge-color);
        background: transparent;
        color: inherit;
        cursor: pointer;
        transition: background 150ms ease;
    }
    .gt-buttons-lg .gt-btn {
        width: 32px;
        height: 32px;
        border-radius: 6px;
    }
    @media (pointer: coarse) {
        .gt-btn::after {
            content: "";
            position: absolute;
            inset: -4px;
        }
    }
    .gt-btn svg {
        width: 14px;
        height: 14px;
        fill: none;
        stroke: currentColor;
        stroke-width: 1.8;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .gt-buttons-lg .gt-btn svg {
        width: 18px;
        height: 18px;
    }
    .gt-btn:hover {
        background: color-mix(in srgb, currentColor 14%, transparent);
    }
    .gt-btn:focus-visible {
        outline: 2px solid currentColor;
        outline-offset: 2px;
    }
    .gt-tile.gt-dragover {
        --gt-edge-style: solid;
    }
    .gt-tile.device.gt-dragover {
        --gt-edge-color: ${unsafeCSS(ORIGIN_COLORS.device)};
        background: rgba(46, 125, 50, 0.12);
        color: ${unsafeCSS(ORIGIN_COLORS.device)};
    }
    .gt-tile.remote.gt-dragover {
        --gt-edge-color: ${unsafeCSS(ORIGIN_COLORS.remote)};
        background: rgba(245, 166, 35, 0.12);
        color: ${unsafeCSS(ORIGIN_COLORS.remote)};
    }
`;
