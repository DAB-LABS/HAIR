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
 *
 * Chip health (ember, 2026-10-19) lives here too: healthDotStyles is
 * the one fragment every emitter and receiver chip reads for its
 * online dot, offline ring and selected-offline alarm, and
 * hairHealthTokens declares the colours on the panel host.
 */
import { css, unsafeCSS } from "lit";
import { EMBER, EMBER_RGB, ONLINE_GREEN } from "./entity-health.js";

/* Chip health (ember, 2026-10-19): the colours, read from the panel
   host's custom properties. The literal values live once, in
   entity-health.ts; they are only the fallback here, for a chip
   mounted outside the panel. */
export const EMBER_VAR = css`var(--hair-ember, ${unsafeCSS(EMBER)})`;
export const ONLINE_VAR = css`var(--hair-online, ${unsafeCSS(ONLINE_GREEN)})`;

/** The health colours as custom properties. The panel host
 *  (ha-panel-ir-devices.ts) declares them, so every surface under it
 *  reads one definition. */
export const hairHealthTokens = css`
    :host {
        --hair-ember: ${unsafeCSS(EMBER)};
        --hair-ember-rgb: ${unsafeCSS(EMBER_RGB)};
        --hair-online: ${unsafeCSS(ONLINE_GREEN)};
    }
`;

/** Selection on the pill, health on the dot (ember, 2026-10-19).
 *
 *  One fragment for every emitter and receiver chip: the device
 *  header's Emitters row, the Remote header's Receivers row, the
 *  emitter and receiver pickers and the Listen chip's offline ring. (The
 *  Devices tab's hardware cards carry health on their badges instead,
 *  in ember from the same token.) Each surface keeps its own dot size and its own
 *  "on" class for selection; this adds only the health states, and only
 *  to a dot that carries `online` or `offline`, so a filter chip's dot
 *  (Mirror, Closet) is never touched.
 *
 *    not selected, online   grey pill, solid green dot
 *    not selected, offline  grey pill, hollow ember ring
 *    selected, online       tone pill, green dot, glow
 *    selected, offline      ember edge and wash, ember ring, no glow
 *
 *  The ring is a shape change as well as a colour change, so it reads
 *  for red-green colour blindness. It is one pixel wider than the
 *  surface's dot (--hair-ring, 7px here, 8px in the pickers). Glow is
 *  the mark of live and in use, so nothing offline glows.
 *
 *  Load it after the surface's own chip rules: its selected-state
 *  rules tie on specificity with them and win on order. */
export const healthDotStyles = css`
    .dot.online {
        background: ${ONLINE_VAR};
        box-shadow: none;
    }
    .dot.offline {
        box-sizing: border-box;
        width: var(--hair-ring, 7px);
        height: var(--hair-ring, 7px);
        background: transparent;
        border: 1.6px solid ${EMBER_VAR};
        box-shadow: none;
    }
    .on .dot.online {
        background: ${ONLINE_VAR};
        box-shadow: 0 0 5px color-mix(in srgb, ${ONLINE_VAR} 65%, transparent);
    }
    .on .dot.offline {
        background: transparent;
        box-shadow: none;
    }
    /* The one alarm: selected and offline. */
    .on.down {
        border-color: color-mix(in srgb, ${EMBER_VAR} 60%, transparent);
        background: color-mix(in srgb, ${EMBER_VAR} 9%, transparent);
    }
`;

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
    ${healthDotStyles}
`;
