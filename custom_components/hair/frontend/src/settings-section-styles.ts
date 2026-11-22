/**
 * The settings dialogs' sections: cards that open.
 *
 * THE RULE. Every section is a card. Its heading is a button holding
 * the section's name over a one-line summary of what is set; pressing
 * it opens the section's fields under it. A section with nothing to
 * open (an action, such as Make a Remote) is a card with its button in
 * the heading row instead.
 *
 * One accent, --section-accent from hair-colors.ts (a dark and a light
 * value), and only on the edges of a card: the open card's outline, its
 * action buttons and the focus ring. Everything inside a card is the
 * panel's neutral colours: names in the text colour, borders in the
 * divider colour, chevrons in the secondary text colour, and the open
 * card's heading and the live readout on the secondary background.
 * Field and check labels are bold; explainers are the secondary text
 * colour. A new section adds a card and its summary, and no colour of
 * its own.
 *
 * The host sets the "dark" attribute from hass.themes.darkMode, as
 * the Devices list does, and lays its cards out in this order: where
 * the state comes from (Power, Climate sensors), how the device is
 * driven (Speed cycle), other remotes (Pinned remotes), then actions.
 */
import { css, unsafeCSS } from "lit";
import { SECTION_ACCENT_DARK, SECTION_ACCENT_LIGHT } from "./hair-colors.js";

/** The one chevron, drawn as a mask so it takes a CSS colour. */
const CHEVRON = unsafeCSS(
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E\")",
);

export const settingsSectionStyles = css`
    :host {
        --section-accent: ${unsafeCSS(SECTION_ACCENT_LIGHT)};
    }
    :host([dark]) {
        --section-accent: ${unsafeCSS(SECTION_ACCENT_DARK)};
    }

    /* The cards. */
    .card {
        --section-wash: color-mix(
            in srgb,
            var(--secondary-background-color) 60%,
            transparent
        );
        margin: 10px 0;
        border: 1px solid var(--divider-color);
        border-radius: 10px;
    }
    .card.open {
        border-color: var(--section-accent);
    }
    .card-heading {
        margin: 0;
        font: inherit;
    }
    .card-head,
    .card-row {
        display: flex;
        align-items: center;
        gap: 12px;
        box-sizing: border-box;
        width: 100%;
        padding: 12px 14px;
    }
    .card-head {
        border: 0;
        border-radius: 9px;
        background: none;
        color: inherit;
        font: inherit;
        text-align: left;
        cursor: pointer;
    }
    .card.open .card-head {
        border-radius: 9px 9px 0 0;
        background: var(--section-wash);
    }
    .card-head:focus-visible {
        outline: 2px solid var(--section-accent);
        outline-offset: -2px;
    }
    .card-text {
        display: flex;
        flex: 1;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
    }
    .card-title {
        color: var(--primary-text-color);
        font-size: 1rem;
        font-weight: 500;
    }
    .card-sum {
        color: var(--secondary-text-color);
        font-size: 0.82rem;
        overflow-wrap: anywhere;
    }
    .card-fold,
    .select-chevron {
        width: 18px;
        height: 18px;
        flex: none;
        background-color: var(--secondary-text-color);
        -webkit-mask: ${CHEVRON} center / 18px no-repeat;
        mask: ${CHEVRON} center / 18px no-repeat;
        pointer-events: none;
    }
    .card-fold {
        width: 22px;
        height: 22px;
        -webkit-mask-size: 22px;
        mask-size: 22px;
        transform: rotate(-90deg);
    }
    .card.open .card-fold {
        transform: none;
    }
    .card-body {
        padding: 10px 14px 4px;
    }

    /* The fields inside a card. */
    .settings-section {
        margin: 0;
    }
    .settings-section .field > label,
    .settings-section .pair-grid label,
    .settings-section .check-row span {
        font-weight: 600;
    }
    .settings-section select,
    .settings-section input[type="text"],
    .settings-section input[type="number"],
    .settings-section .source-field {
        border-color: var(--divider-color);
    }
    .settings-section select {
        appearance: none;
        -webkit-appearance: none;
        padding-right: 32px;
    }
    .select-wrap {
        position: relative;
    }
    .settings-section .select-chevron {
        position: absolute;
        top: 50%;
        right: 10px;
        transform: translateY(-50%);
    }
    .settings-section .live-readout {
        background: var(--section-wash);
    }
    .settings-section input[type="checkbox"] {
        accent-color: var(--primary-text-color);
    }
    .card-action-btn {
        flex: none;
        white-space: nowrap;
        border-color: var(--section-accent);
        color: var(--section-accent);
    }
`;
