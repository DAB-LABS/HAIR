/**
 * The header chip group's look, shared (BroadSniff Listen, 2026-10-17).
 *
 * Moved out of ir-header-chip-group.ts unchanged, so the Sniffer's
 * Listen row (ir-listen-row.ts) wears exactly the same label column,
 * chip anatomy and tone rules as the device pages' Emitters, Receivers
 * and Pin rows. The two components differ in behaviour (the chip group
 * collapses to its "on" chips and toggles only while expanded; a Listen
 * chip toggles on one tap and carries a countdown), not in look, and
 * one style module keeps them from drifting apart. Change the look
 * here, once.
 */
import { css } from "lit";

export const headerChipStyles = css`
    /* The host fills the header's row column rather than shrinking
       to its own content: the label's fixed width plus a flexible
       chips column is the whole mechanism, and an inline-block host
       would collapse the flexible half. */
    :host {
        display: block;
    }
    .hdr-row {
        display: flex;
        align-items: flex-start;
        gap: 12px;
    }
    /* Fixed width comes from the consumer (labelWidth), so every row
       on a header shares one colon line. Right-justified against
       that width; padding-top lines the cap height up with the first
       row of chips rather than their box tops. */
    .hdr-row-label {
        flex-shrink: 0;
        text-align: right;
        padding-top: 5px;
        font-size: 0.66rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--secondary-text-color);
        white-space: nowrap;
    }
    /* min-width: 0 is load-bearing -- without it the column takes a
       content-based minimum from its own nowrap chips and overflows
       sideways instead of wrapping in place. */
    .hdr-row-pills {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 7px;
    }
    .chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px 3px 8px;
        border: 1px solid var(--divider-color);
        border-radius: 14px;
        background: none;
        font-family: inherit;
        font-size: 11.5px;
        color: var(--secondary-text-color);
        cursor: default;
        transition: border-color 140ms ease, background 140ms ease,
            color 140ms ease;
    }
    .hdr-row-pills.expanded .chip {
        cursor: pointer;
    }
    .hdr-row-pills.expanded .chip:hover:not(:disabled) {
        border-color: var(--tone);
    }
    .chip:disabled {
        cursor: default;
        opacity: 0.55;
    }
    .chip.readonly {
        opacity: 0.7;
        cursor: default !important;
    }
    .chip-name {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 160px;
    }
    .dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #4d5359;
        flex: none;
    }
    .chip.on {
        border-color: var(--tone);
        background: color-mix(in srgb, var(--tone) 14%, transparent);
        color: var(--primary-text-color);
    }
    .chip.on .dot {
        background: var(--tone);
        box-shadow: 0 0 5px color-mix(in srgb, var(--tone) 65%, transparent);
    }
    /* Assigned but unreachable (emitters only) -- amber, same
     *  treatment ir-emitter-picker.ts uses, deliberately NOT the
     *  group's own tone color (this state means "trouble", not
     *  "on", regardless of which group it's in). */
    .chip.down {
        border-color: rgba(217, 164, 65, 0.45);
        color: #e8dcc2;
    }
    .chip.down .dot {
        background: #d9a441;
        box-shadow: none;
    }
    .add-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        border: 1px dashed var(--divider-color);
        background: none;
        color: var(--secondary-text-color);
        font-size: 13px;
        line-height: 1;
        cursor: pointer;
        font-family: inherit;
    }
    .add-btn:hover:not(:disabled) {
        border-color: var(--tone);
        color: var(--tone);
    }
    .add-btn:disabled {
        cursor: default;
        opacity: 0.55;
    }
    /* Filter chips (chip size pass, 2026-10-17). The Mirror's and the
       Closet's filter rows, and the Closet picker in the Add Device
       dialog, wear this same .chip at this same size (22px: 3px of
       padding over 11.5px text, a 1px border, the 14px radius) instead
       of three bigger copies of their own. The "on" state and the dot
       are the ones above, toned by the consumer's --tone, as here.
       What differs is behaviour: a filter chip toggles on one tap, so
       it is clickable at rest and shows its tone on hover, where a
       header chip only does while its group is expanded. */
    .chip.filter {
        cursor: pointer;
    }
    .chip.filter:hover:not(:disabled) {
        border-color: var(--tone);
    }
    .chip.filter:disabled {
        cursor: default;
    }
    .chip.filter:focus-visible {
        outline: 2px solid #4dabf7;
        outline-offset: 2px;
    }
    /* The search box beside a filter row, at the chip's height, radius
       and text size, so each row reads as one height. A consumer with
       an icon inside the box keeps its own left padding. Written as
       input.chip-search so it also outranks the dialog styles' generic
       input[type="text"] rule in a component that loads those first
       (the Closet does). */
    input.chip-search {
        height: 22px;
        box-sizing: border-box;
        padding: 0 10px;
        border: 1px solid var(--divider-color);
        border-radius: 14px;
        background: none;
        color: var(--primary-text-color);
        font-family: inherit;
        font-size: 11.5px;
    }
    input.chip-search:focus {
        outline: none;
        border-color: var(--tone, var(--primary-color));
    }
`;
