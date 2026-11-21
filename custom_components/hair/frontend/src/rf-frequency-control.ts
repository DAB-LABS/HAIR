/**
 * The radio frequency control, one for every place HAIR asks for a radio
 * frequency: the radio code editor and the listening picker on a
 * receiver's pill. It has two forms.
 *
 * form="pills" (the radio code editor):
 *
 *   the band pills   315 and 433.92 (RF_PRESETS_HZ); the picked one blue.
 *   Other            a free field for any other frequency, in MHz. Empty,
 *                    it shows "e.g. 433.92"; clicked, it offers a short
 *                    list of common bands; typing anything still works,
 *                    by the same rule as always (rf-code.ts mhzToHz).
 *                    When it holds the frequency it wears the same blue
 *                    as a picked pill.
 *
 * form="list" (the listening picker):
 *
 *   the rows         the host's `rows` (a receiver's presets, or the
 *                    common bands for one that takes any value), the
 *                    current one marked; a greyed row is still a pick,
 *                    unless the host marks it blocked (a band the
 *                    receiver doesn't accept): then it can't be picked.
 *                    Without `rows`, every common band in order
 *                    (RF_SUGGESTIONS_MHZ), greyed outside minHz..maxHz.
 *                    One click picks.
 *   Other...         the last row, when `other` is set; a click turns it
 *                    into a field in place, focused. Enter sets what is
 *                    typed, Escape goes back to the row. With `accepts`,
 *                    a value outside them is refused: it stays, outlined
 *                    red, and `frequency-refused` fires with `{ hz }`
 *                    (`{ hz: null }` once it is fixed). Nothing is set
 *                    while typing, so a half-typed number never becomes
 *                    a frequency.
 *
 * With `rows`, a pick fires `frequency-pick` with `{ hz, option }`: the
 * row's preset by name, or a frequency (a band or Other). A pick of the
 * current row is no change and fires nothing but `frequency-done`.
 *
 * Both forms fire `frequency-done` after any pick, a change or not, so a
 * host that shows the list in a menu can close it.
 *
 * It fires `frequency-changed` with `{ hz }` only when the frequency
 * really changes: a click on the band already picked, or typing the
 * value it already holds, is not a change, so a saved row's frequency
 * is never marked as the user's when nothing changed. It fires
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

/** The bands the Other field offers on a click: the common bands for
 *  remote controls. Typing any other frequency still works. */
export const RF_SUGGESTIONS_MHZ = [
    "300", "303.875", "310", "315", "390", "418", "433.42", "433.92", "868.35", "915",
] as const;

/** The new frequency a pick or a typed value makes, or null when it is no
 *  change. Pure, for the node tests. */
export function frequencyChange(currentHz: number | null, nextHz: number | null): number | null {
    if (nextHz === null) return null;
    return nextHz === currentHz ? null : nextHz;
}

/** The list form's rows: the common bands in order, with the current
 *  frequency added in its place when it is not one of them. Pure, for
 *  the node tests. */
export function listBands(valueHz: number | null): number[] {
    const bands = RF_SUGGESTIONS_MHZ.map((mhz) => mhzToHz(mhz)).filter((hz): hz is number => hz !== null);
    if (valueHz !== null && !bands.includes(valueHz)) bands.push(valueHz);
    return bands.sort((a, b) => a - b);
}

/** Whether a band is outside the limits the host knows; unknown limits
 *  are never "outside". Pure, for the node tests. */
export function outsideRange(hz: number, minHz: number | null, maxHz: number | null): boolean {
    return (minHz !== null && hz < minHz) || (maxHz !== null && hz > maxHz);
}

/** One row of the list form, as the host builds it. */
export interface ListRow {
    key: string;
    label: string;
    hz: number | null;
    option: string | null;
    current: boolean;
    dim: boolean;
    /** Greyed and not a pick: a band the receiver doesn't accept. */
    blocked?: boolean;
    /** The row's hover line, when it has one. */
    title?: string;
}

/** Whether a frequency is in what the host says is accepted; an empty
 *  list accepts anything. Pure, for the node tests. */
export function acceptedHz(accepts: readonly (readonly [number, number])[], hz: number): boolean {
    return accepts.length === 0 || accepts.some(([lo, hi]) => hz >= lo && hz <= hi);
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
    /** "pills" (the default) or "list"; see the header. */
    @property() public form: "pills" | "list" = "pills";
    /** The list form greys bands outside these, when known. */
    @property({ attribute: false }) public minHz: number | null = null;
    @property({ attribute: false }) public maxHz: number | null = null;
    /** The list form's rows from the host, or null for the common bands. */
    @property({ attribute: false }) public rows: ListRow[] | null = null;
    /** Whether the list form ends with "Other...". */
    @property({ type: Boolean }) public other = true;
    /** The list form's Other field: what the receiver accepts, in Hz.
     *  A typed value outside is refused (outlined red, nothing picked,
     *  `frequency-refused` fired). Empty is no check. */
    @property({ attribute: false }) public accepts: [number, number][] = [];
    /** The list form's Other field: its hint when empty (what the
     *  receiver accepts, before the field's own "MHz"), in place of the
     *  example value. The field widens to show it whole. */
    @property({ attribute: false }) public otherHint = "";

    @state() private _typed = "";
    /** The list form's Other row is a field. */
    @state() private _otherOpen = false;

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
        this._fire("frequency-done", {});
    }

    /** A host row picked: its preset by name, or its frequency. */
    private _pickRow(row: ListRow): void {
        if (!row.current) {
            this._fire("frequency-pick", row.option !== null ? { option: row.option } : { hz: row.hz });
        }
        this._fire("frequency-done", {});
    }

    /** The list form's field: kept as typed, set only on Enter. */
    private _onListInput(e: Event): void {
        this._typed = (e.target as HTMLInputElement).value;
        const hz = mhzToHz(this._typed);
        const refused = hz !== null && !acceptedHz(this.accepts, hz);
        // Red while what is typed is a frequency the receiver doesn't
        // take; a half-typed number is only judged on Enter.
        if (refused !== this._listInvalid && (refused || hz !== null || this._typed.trim() === "")) {
            this._listInvalid = refused;
            if (!refused) this._fire("frequency-refused", { hz: null });
        }
    }

    private _onListKey(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            e.preventDefault();
            const hz = mhzToHz(this._typed);
            if (hz === null) {
                this._listInvalid = true;
                return;
            }
            if (!acceptedHz(this.accepts, hz)) {
                // Refused before anything is sent: the value stays, red,
                // and the host says what the receiver takes.
                this._listInvalid = true;
                this._fire("frequency-refused", { hz });
                return;
            }
            this._listInvalid = false;
            this._otherOpen = false;
            if (this.rows !== null) {
                this._fire("frequency-pick", { hz });
                this._fire("frequency-done", {});
            } else {
                this._pick(hz);
            }
        } else if (e.key === "Escape") {
            // Back to the row; the host's menu stays open.
            e.stopPropagation();
            this._otherOpen = false;
            this._listInvalid = false;
            this._typed = "";
            void this.updateComplete.then(() =>
                this.renderRoot.querySelector<HTMLElement>(".row.other-row")?.focus(),
            );
        }
    }

    @state() private _listInvalid = false;

    private _openOther(): void {
        this._otherOpen = true;
        this._typed = "";
        this._listInvalid = false;
        void this.updateComplete.then(() =>
            this.renderRoot.querySelector<HTMLInputElement>(".row.other-field input")?.focus(),
        );
    }

    /** Up and down move between the rows, as in a menu. */
    private _onListNav(e: KeyboardEvent): void {
        if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
        const rows = [...this.renderRoot.querySelectorAll<HTMLElement>(".row:not(:disabled)")];
        const at = rows.indexOf((this.renderRoot as ShadowRoot).activeElement as HTMLElement);
        const step = e.key === "ArrowDown" ? 1 : -1;
        const next = rows[Math.max(0, Math.min(rows.length - 1, at + step))];
        if (next) {
            e.preventDefault();
            next.focus();
        }
    }

    /** The list form puts the current band in view once it is drawn. */
    protected firstUpdated(): void {
        if (this.form !== "list") return;
        const on = this.renderRoot.querySelector<HTMLElement>(".row.on");
        on?.scrollIntoView({ block: "nearest" });
        (on ?? this.renderRoot.querySelector<HTMLElement>(".row"))?.focus({ preventScroll: true });
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
        return this.form === "list" ? this._renderList() : this._renderPills();
    }

    private _renderList() {
        const bands = listBands(this.valueHz);
        return html`<div class="list" role="listbox" aria-label=${this.label} @keydown=${this._onListNav}>
            ${this.rows !== null ? this._renderRows(this.rows) : bands.map((hz) => {
                const on = hz === this.valueHz;
                const dim = outsideRange(hz, this.minHz, this.maxHz);
                return html`<button
                    class="row ${on ? "on" : ""} ${dim ? "dim" : ""}"
                    role="option"
                    aria-selected=${on ? "true" : "false"}
                    ?disabled=${this.disabled}
                    @click=${() => this._pick(hz)}
                >
                    <span class="check">${on ? "✓" : ""}</span>${t("rfedit.mhz", { mhz: hzToMhz(hz) })}
                </button>`;
            })}
            ${!this.other
                ? ""
                : this._otherOpen
                ? html`<span class="row other-field">
                      <input
                          type="text"
                          inputmode="decimal"
                          class=${this._listInvalid ? "invalid" : ""}
                          placeholder=${this.otherHint || t("rfedit.other_placeholder")}
                          aria-label=${t("rfedit.other_mhz")}
                          title=${this.otherHint}
                          style=${this.otherHint ? `width:${Math.min(this.otherHint.length + 1, 30)}ch` : ""}
                          ?disabled=${this.disabled}
                          .value=${this._typed}
                          @input=${this._onListInput}
                          @keydown=${this._onListKey}
                      />
                      <span class="unit">MHz</span>
                  </span>`
                : html`<button class="row other-row" ?disabled=${this.disabled} @click=${this._openOther}>
                      <span class="check"></span>${t("listen.tune_other")}
                  </button>`}
        </div>`;
    }

    private _renderRows(rows: ListRow[]) {
        return rows.map(
            (row) => html`<button
                class="row ${row.current ? "on" : ""} ${row.dim ? "dim" : ""}"
                role="option"
                aria-selected=${row.current ? "true" : "false"}
                aria-disabled=${row.blocked ? "true" : "false"}
                title=${row.title ?? ""}
                ?disabled=${this.disabled || row.blocked === true}
                @click=${() => this._pickRow(row)}
            >
                <span class="check">${row.current ? "✓" : ""}</span>${row.label}
            </button>`,
        );
    }

    private _renderPills() {
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
        /* As tall as the band pills beside it, and narrower: the pills'
           padding, type size and rounding. */
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
        /* The list form: a menu of bands, like the pill pickers' menus. */
        .list {
            display: flex;
            flex-direction: column;
            max-height: 264px;
            overflow-y: auto;
            overscroll-behavior: contain;
        }
        .row {
            display: flex;
            align-items: center;
            gap: 6px;
            min-height: 32px;
            padding: 0 10px 0 6px;
            border: none;
            border-radius: 6px;
            background: none;
            color: var(--primary-text-color);
            font: inherit;
            font-size: 0.85rem;
            text-align: left;
            cursor: pointer;
            flex-shrink: 0;
        }
        button.row:hover,
        button.row:focus-visible {
            outline: none;
            background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
        }
        .row.on {
            color: #03a9f4;
            font-weight: 500;
        }
        /* Outside what the receiver says it does: greyed, still a pick. */
        .row.dim {
            color: var(--secondary-text-color);
            opacity: 0.6;
        }
        .check {
            display: inline-block;
            width: 14px;
            text-align: center;
        }
        .row.other-row {
            border-top: 1px solid var(--divider-color);
            border-radius: 0 0 6px 6px;
            margin-top: 2px;
        }
        .row.other-field {
            gap: 4px;
            padding-left: 26px;
            cursor: default;
        }
        .row.other-field input {
            width: 7em;
            box-sizing: border-box;
            padding: 4px 8px;
            border-radius: 12px;
            border: 1px solid var(--primary-color, #03a9f4);
            background: var(--card-background-color, transparent);
            color: var(--primary-text-color);
            font: inherit;
            font-size: 0.85rem;
        }
        .row.other-field input:focus {
            outline: none;
        }
        .row.other-field input.invalid {
            border-color: var(--error-color, #db4437);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "hair-frequency-control": HairFrequencyControl;
    }
}
