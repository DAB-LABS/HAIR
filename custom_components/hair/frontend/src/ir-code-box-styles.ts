/**
 * The code box, the strip under it and the S/L diamonds, shared by both
 * code editors (owner, 2026-11-15: the radio editor takes the infrared
 * editor's look; docs/internal/plans/radio-editor-matches-ir-editor.md).
 *
 * The infrared editor (ir-signal-editor.ts) and the radio editor
 * (ir-rf-editor.ts) stay two components, because their engines differ:
 * Pronto, snap, ditto and repair on one side, the .sub, the frame vote
 * and the frequency ladder on the other. What they share is how the
 * code reads on screen, and that lives here, once:
 *
 *   codeBoxStyles   the box: monospace, the steady copper edge, the
 *                   corner copy icon and its "Copied" hint. The border
 *                   is on the wrapper, and the icon sits in a 24 px strip
 *                   above the text, so a box long enough to scroll draws
 *                   its scrollbar below the icon, never under it. With no
 *                   scrollbar it looks as the infrared box always has.
 *   feedbackStyles  the filled strip under the box: the check mark and
 *                   status line, the facts with the code's identity (its
 *                   pill), the messages.
 *   diamondStyles   the S/L diamonds, long and short, in
 *                   the --hair-diamond-* tokens (hair-colors.ts).
 *   recognizedAs    the words around the pill: "Recognized as", then
 *                   the pill, read the same way everywhere in HAIR.
 *   deleteStyles    Delete, bottom left, outlined ember, in both editors.
 *   fitCodeBox      the box's height: its content, between a floor and
 *                   a ceiling the caller passes (the infrared editor's
 *                   64 px to 45% of the viewport, or its held repair box).
 *
 * Load these before an editor's own rules, so a surface's own state
 * (a held repair box, a snap flash) still wins on order.
 */
import { css } from "lit";
import { t } from "./localize.js";
import { DIAMOND_LONG_VAR, DIAMOND_SHORT_VAR, EMBER_VAR, DEEP_GREEN_VAR } from "./ir-header-chip-styles.js";

/** The code box's copper stroke: the infrared box wore it in focus, and
 *  it opened focused, so it read as copper; now both boxes wear it
 *  always. */
const CODE_FOCUS = css`#b87333`;

export const codeBoxStyles = css`
    .code-wrap {
        position: relative;
        box-sizing: border-box;
        /* The icon's strip: the text starts below it, so the copy icon
           and a scrollbar never share a corner. */
        padding-top: 24px;
        border-radius: 4px;
        /* Copper, steady, focused or not (owner, 2026-11-16): the code
           box reads the same in both editors whether or not it has the
           cursor. Only a held repair box steps back to the divider
           (ir-signal-editor.ts). */
        border: 1px solid ${CODE_FOCUS};
        background: var(--card-background-color);
    }
    .code-wrap textarea {
        display: block;
        width: 100%;
        box-sizing: border-box;
        margin: 0;
        padding: 0 8px 8px;
        border: none;
        border-radius: 0 0 4px 4px;
        background: transparent;
        color: var(--primary-text-color);
        font-family: monospace;
        font-size: 0.95rem;
        resize: vertical;
        /* fitCodeBox sizes the height to the code, clamped, so a long
           code scrolls inside the box instead of overflowing the
           dialog. */
        overflow-y: auto;
    }
    .code-wrap textarea:focus {
        outline: none;
    }
    .copy-icon {
        position: absolute;
        top: 4px;
        right: 6px;
        z-index: 2;
        display: inline-flex;
        align-items: center;
        padding: 2px;
        border: none;
        background: none;
        color: var(--secondary-text-color);
        cursor: pointer;
        opacity: 0.55;
        transition: opacity 150ms ease;
    }
    .copy-icon:hover {
        opacity: 0.9;
    }
    .copy-icon ha-svg-icon {
        --mdc-icon-size: 12px;
    }
    .copy-flash {
        position: absolute;
        top: 3px;
        right: 30px;
        z-index: 2;
        font-size: 0.72rem;
        white-space: nowrap;
        color: var(--secondary-text-color);
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 1px 6px;
        pointer-events: none;
    }
`;

export const feedbackStyles = css`
    .feedback {
        margin: 4px 0 12px;
        padding: 10px 12px;
        border-radius: 6px;
        background: var(--secondary-background-color);
    }
    .status {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .status .mark {
        font-size: 1rem;
    }
    .status.ok {
        color: ${DEEP_GREEN_VAR};
    }
    .status.bad {
        color: ${EMBER_VAR};
    }
    .metrics {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 4px 14px;
        margin-top: 6px;
        font-size: 0.8rem;
        color: var(--secondary-text-color);
    }
    /* The code's identity, once, on the info line (owner, 2026-11-16):
       the pill, and for radio its fields beside it. It wraps as one
       piece at phone width. */
    .identity {
        display: inline-flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 4px 6px;
        min-width: 0;
    }
    .msg {
        margin-top: 6px;
        font-size: 0.8rem;
    }
    .msg.err {
        color: ${EMBER_VAR};
    }
`;

export const diamondStyles = css`
    .diamonds {
        display: flex;
        flex-wrap: wrap;
        gap: 1px;
        line-height: 1;
    }
    .feedback .diamonds {
        margin-top: 8px;
    }
    .diamond {
        font-size: 0.7rem;
    }
    .diamond.long {
        color: ${DIAMOND_LONG_VAR};
    }
    .diamond.short {
        color: ${DIAMOND_SHORT_VAR};
    }
`;

/** The recognition sentence around the pill (owner, 2026-11-16: "Recognized
 *  as", then the pill, so recognition reads the same way everywhere in
 *  HAIR). The pill takes the protocol's place in the sentence, so a
 *  language that puts the name first ("{protocol} として認識") keeps its
 *  order: the words before the name, then the words after it. */
export function recognizedAs(): [string, string] {
    const MARK = "\u0000";
    const sentence = t("editor.recognized_as", { protocol: MARK });
    const at = sentence.indexOf(MARK);
    if (at < 0) return [sentence, ""];
    return [sentence.slice(0, at).trimEnd(), sentence.slice(at + MARK.length).trimStart()];
}

/** Delete, bottom left in both editors (owner, 2026-11-16): outlined
 *  ember, as the other dialogs' Delete. The host opens the same
 *  confirmation the row's own delete opens. */
export const deleteStyles = css`
    .delete-btn {
        background: none;
        border-color: ${EMBER_VAR};
        color: ${EMBER_VAR};
    }
    .delete-btn:hover:not(:disabled) {
        background: color-mix(in srgb, ${EMBER_VAR} 14%, transparent);
    }
`;

/** What the wrapper adds around the textarea: the icon's 24 px strip
 *  and its 1 px border, top and bottom. */
export const CODE_BOX_FRAME_PX = 26;

/** Fit a code box to its content: reset to 0 first, so scrollHeight
 *  reports the content and not the box, then clamp between the floor
 *  and the ceiling. The floor and ceiling are the whole box's, wrapper
 *  included, so a box is as tall as it was before the icon got its strip
 *  (the strip took the textarea's old 24 px top padding). */
export function fitCodeBox(ta: HTMLTextAreaElement, minPx: number, maxPx: number): void {
    ta.style.height = "0px";
    ta.style.height = `${codeBoxHeight(ta.scrollHeight, minPx, maxPx)}px`;
}

/** The textarea's height for this content (pure, for the tests): the
 *  whole box clamped, less the wrapper's frame. */
export function codeBoxHeight(scrollHeight: number, minPx: number, maxPx: number): number {
    const whole = Math.min(Math.max(scrollHeight + CODE_BOX_FRAME_PX, minPx), maxPx);
    return whole - CODE_BOX_FRAME_PX;
}
