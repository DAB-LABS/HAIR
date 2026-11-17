/**
 * The radio frequency control, one for every place HAIR asks for a radio
 * frequency (owner, 2026-11-16 13:46 PT): the radio code editor today,
 * the listening picker on a receiver's chip next.
 *
 *   the band pills   315 and 433.92 (RF_PRESETS_HZ); the picked one blue.
 *   Other            a free field for any other frequency, in MHz. Empty,
 *                    it shows "e.g. 433.92"; clicked, it offers a short
 *                    list of common bands; typing anything still works,
 *                    by the same rule as always (rf-code.ts mhzToHz).
 *                    When it holds the frequency it wears the same blue
 *                    as a picked pill (owner, 14:33 PT: "the button
 *                    should be blue like it is when you pick any of the
 *                    other ones").
 *
 * It fires `frequency-changed` with `{ hz }` only when the frequency
 * really changes: a click on the band already picked, or typing the
 * value it already holds, is not a change (the "Set by you" finding,
 * gertrude-2026-11-16-frequency-control-plan.md section 1). It fires
 * `frequency-invalid` with `{ invalid }` whenever what is typed stops or
 * starts being a frequency, so the host can hold Save.
 *
 * The line under it (where the frequency came from, or a picker's own
 * notes) is the host's to give.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { RF_PRESETS_HZ, hzToMhz, mhzToHz, presetOf } from "./rf-code.js";

/** The bands the Other field offers on a click (owner, 13:46 PT: HARF's
 *  list). Typing any other frequency still works. */
export const RF_SUGGESTIONS_MHZ = [
    "300", "303.875", "310", "315", "390", "418", "433.42", "433.92", "868.35", "915",
] as const;

/** The new frequency a pick or a typed value makes, or null when it is no
 *  change. Pure, for the node tests. */
export function frequencyChange(currentHz: number | null, nextHz: number | null): number | null {
    if (nextHz === null) return null;
    return nextHz === currentHz ? null : nextHz;
}

/** Whether the Other field holds the frequency: a value that is not one
 *  of the band pills. Then it wears the picked look. */
export function otherHolds(valueHz: number | null): boolean {
    return valueHz !== null && presetOf(valueHz) === null;
}

/** What the Other field shows for a frequency set from outside (a paste,
 *  a saved row): the MHz for an odd band, nothing for a band pill. What
 *  the person is typing is left alone while it already means that
 *  frequency ("433.9" stays "433.9"). */
export function typedFor(valueHz: number | null, typed: string): string {
    if (valueHz === null) return mhzToHz(typed) === null ? typed : "";
    if (presetOf(valueHz) !== null) return mhzToHz(typed) === valueHz ? typed : "";
    return mhzToHz(typed) === valueHz ? typed : hzToMhz(valueHz);
}

@customElement("hair-frequency-control")
export class HairFrequencyControl extends LitElement {
    /** The frequency in Hz, or null when there is none yet. */
    @property({ attribute: false }) public valueHz: number | null = null;
    @property({ type: Boolean }) public disabled = false;
    /** The group's label, read out with the pills. */
    @property({ attribute: false }) public label = "";

    @state() private _typed = "";

    willUpdate(changed: Map<string, unknown>): void {
        if (!changed.has("valueHz")) return;
        const wasInvalid = this._invalid;
        this._typed = typedFor(this.valueHz, this._typed);
        // A frequency set from outside (a paste) can replace half-typed
        // text; the host hears that the field is no longer invalid.
        if (wasInvalid && !this._invalid) this._fire("frequency-invalid", { invalid: false });
    }

    private get _invalid(): boolean {
        return this._typed.trim() !== "" && mhzToHz(this._typed) === null;
    }

    private _pick(hz: number): void {
        const next = frequencyChange(this.valueHz, hz);
        const wasInvalid = this._invalid;
        this._typed = "";
        if (wasInvalid) this._fire("frequency-invalid", { invalid: false });
        if (next !== null) this._fire("frequency-changed", { hz: next });
    }

    private _onInput(e: Event): void {
        const wasInvalid = this._invalid;
        this._typed = (e.target as HTMLInputElement).value;
        if (this._invalid !== wasInvalid) this._fire("frequency-invalid", { invalid: this._invalid });
        const next = frequencyChange(this.valueHz, mhzToHz(this._typed));
        if (next !== null) this._fire("frequency-changed", { hz: next });
    }

    private _fire(name: string, detail: Record<string, unknown>): void {
        this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
    }

    render() {
        const preset = presetOf(this.valueHz);
        const holds = otherHolds(this.valueHz) && !this._invalid;
        return html`<div class="freq-row" role="group" aria-label=${this.label}>
            ${RF_PRESETS_HZ.map(
                (hz) => html`<button
                    class="preset ${preset === hz ? "on" : ""}"
                    aria-pressed=${preset === hz ? "true" : "false"}
                    ?disabled=${this.disabled}
                    @click=${() => this._pick(hz)}
                >
                    ${t("rfedit.mhz", { mhz: hzToMhz(hz) })}
                </button>`,
            )}
            <span class="other">
                <input
                    type="text"
                    inputmode="decimal"
                    list="rf-bands"
                    class="${this._invalid ? "invalid" : ""} ${holds ? "on" : ""}"
                    placeholder=${t("rfedit.other_placeholder")}
                    aria-label=${t("rfedit.other_mhz")}
                    ?disabled=${this.disabled}
                    .value=${this._typed}
                    @input=${this._onInput}
                />
                <datalist id="rf-bands">
                    ${RF_SUGGESTIONS_MHZ.map((mhz) => html`<option value=${mhz}></option>`)}
                </datalist>
                <span class="unit">MHz</span>
            </span>
        </div>`;
    }

    static styles = css`
        :host {
            display: block;
        }
        .freq-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
        }
        .preset {
            padding: 5px 12px;
            border-radius: 14px;
            border: 1px solid var(--divider-color);
            background: none;
            color: var(--primary-text-color);
            font: inherit;
            font-size: 0.85rem;
            cursor: pointer;
        }
        /* Picked: a band pill, or the Other field when it holds the
           frequency. One look for "this is the frequency". */
        .preset.on,
        .other input.on {
            border-color: #03a9f4;
            background: color-mix(in srgb, #03a9f4 14%, transparent);
        }
        .other {
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        /* As tall as the band pills beside it, and narrower (owner,
           2026-11-16): the pills' padding, type size and rounding. */
        .other input {
            width: 6em;
            box-sizing: border-box;
            padding: 5px 10px;
            border-radius: 14px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font: inherit;
            font-size: 0.85rem;
            line-height: normal;
        }
        .other input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .other input.invalid {
            border-color: var(--error-color, #db4437);
        }
        .unit {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "hair-frequency-control": HairFrequencyControl;
    }
}
