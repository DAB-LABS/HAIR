/**
 * The add window's question for raw timings: infrared or radio.
 *
 * Raw timings say nothing about their medium (`medium` is "either"), so
 * the window shows HAIR's guess first (`guess`, `paste_medium.
 * timings_guess`) and these two chips at the top of the validation box,
 * the shown editor's one picked. Clicking the other one hands the text
 * to the other editor. The chips look like the radio editor's band
 * pills: one look for "this is the one picked".
 */
import { html, css } from "lit";
import { t } from "./localize.js";
import type { Medium } from "./paste-formats.js";

export function renderMediumChips(picked: Medium, onPick: (medium: Medium) => void) {
    const chip = (medium: Medium, key: string) => html`<button
        type="button"
        class="medium-chip ${picked === medium ? "on" : ""}"
        aria-pressed=${picked === medium ? "true" : "false"}
        @click=${() => {
            if (picked !== medium) onPick(medium);
        }}
    >
        ${t(key)}
    </button>`;
    return html`<div class="medium-chips" role="group" aria-label=${t("addcode.which")}>
        <span class="medium-which">${t("addcode.which")}</span>
        ${chip("ir", "addcode.as_ir")} ${chip("rf", "addcode.as_rf")}
    </div>`;
}

export const mediumChipStyles = css`
    .medium-chips {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
        margin-bottom: 6px;
    }
    .medium-which {
        font-size: 0.85rem;
        color: var(--secondary-text-color);
    }
    .medium-chip {
        padding: 5px 12px;
        border-radius: 14px;
        border: 1px solid var(--divider-color);
        background: none;
        color: var(--primary-text-color);
        font: inherit;
        font-size: 0.85rem;
        cursor: pointer;
    }
    .medium-chip.on {
        border-color: #03a9f4;
        background: color-mix(in srgb, #03a9f4 14%, transparent);
    }
`;
