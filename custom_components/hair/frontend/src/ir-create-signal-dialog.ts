/**
 * Dialog for adding a manually-pasted Pronto signal to a clipped remote.
 *
 * Live-validates the pasted Pronto (debounced) against the backend
 * validator and shows confidence feedback: valid/invalid, carrier
 * frequency, burst pair count, an S/L diamond preview, and any
 * error/warning messages. An optional alias names the signal up front.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { ProntoValidation, UnknownSignal } from "./types.js";

// Mirrors PRONTO_SL_THRESHOLD / PRONTO_GAP_THRESHOLD in const.py. Used
// only for the dialog's S/L preview; the stored signal's authoritative
// pattern is computed server-side.
const SL_THRESHOLD = 0x30;
const GAP_THRESHOLD = 0x0400;

@customElement("ir-create-signal-dialog")
export class IrCreateSignalDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;

    @state() private _pronto = "";
    @state() private _alias = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _validation: ProntoValidation | null = null;

    private _debounce: ReturnType<typeof setTimeout> | null = null;

    disconnectedCallback(): void {
        super.disconnectedCallback();
        if (this._debounce !== null) {
            clearTimeout(this._debounce);
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _onProntoInput(e: Event): void {
        this._pronto = (e.target as HTMLTextAreaElement).value;
        if (this._debounce !== null) {
            clearTimeout(this._debounce);
        }
        if (!this._pronto.trim()) {
            this._validation = null;
            return;
        }
        this._debounce = setTimeout(() => void this._validate(), 250);
    }

    private _onKeydown(e: KeyboardEvent): void {
        // Enter creates the signal when it is valid; Shift+Enter still
        // inserts a newline in the Pronto field if ever needed.
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (this._validation?.valid && !this._busy) {
                void this._create();
            }
        }
    }

    private async _validate(): Promise<void> {
        try {
            this._validation = await this.api.validatePronto(this._pronto);
        } catch {
            this._validation = null;
        }
    }

    private _slPreview(): string[] | null {
        const norm = this._validation?.normalized;
        if (!norm) return null;
        const words = norm.split(" ").map((w) => parseInt(w, 16));
        if (words.length < 5 || words.some((n) => Number.isNaN(n))) return null;
        const out: string[] = [];
        for (const t of words.slice(4)) {
            if (t >= GAP_THRESHOLD) break;
            out.push(t < SL_THRESHOLD ? "S" : "L");
        }
        return out.length ? out : null;
    }

    private async _create(): Promise<void> {
        if (!this._validation?.valid) {
            this._error = "Fix the Pronto code before saving.";
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const result: { signal: UnknownSignal } = await this.api.createSignal({
                device_id: this.deviceId,
                pronto: this._pronto,
                alias: this._alias.trim() || undefined,
            });
            this.dispatchEvent(
                new CustomEvent("signal-created", {
                    detail: result.signal,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private _renderFeedback() {
        const v = this._validation;
        if (!v) return "";
        const sl = this._slPreview();
        return html`
            <div class="feedback">
                <div class="status ${v.valid ? "ok" : "bad"}">
                    <span class="mark">${v.valid ? "✓" : "✗"}</span>
                    ${v.valid ? "Valid Pronto code" : "Not valid yet"}
                </div>
                ${v.valid
                    ? html`
                          <div class="metrics">
                              ${v.frequency_khz !== null
                                  ? html`<span>${v.frequency_khz} kHz</span>`
                                  : ""}
                              ${v.burst_pair_count !== null
                                  ? html`<span
                                        >${v.burst_pair_count} burst
                                        ${v.burst_pair_count === 1 ? "pair" : "pairs"}</span
                                    >`
                                  : ""}
                          </div>
                          ${sl
                              ? html`<div class="diamonds">
                                    ${sl.map((c) =>
                                        c === "L"
                                            ? html`<span class="diamond long">◆</span>`
                                            : html`<span class="diamond short">◇</span>`,
                                    )}
                                </div>`
                              : ""}
                      `
                    : ""}
                ${v.errors.map((msg) => html`<div class="msg err">${msg}</div>`)}
                ${v.warnings.map((msg) => html`<div class="msg warn">${msg}</div>`)}
            </div>
        `;
    }

    render() {
        const canCreate = this._validation?.valid === true && !this._busy;
        return html`
            <ha-dialog
                open
                heading="Create Signal"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <div class="field">
                    <label>Pronto code</label>
                    <div class="helper">Paste the Pronto hex code.</div>
                    <textarea
                        rows="4"
                        .value=${this._pronto}
                        placeholder="0000 006D ..."
                        autofocus
                        spellcheck="false"
                        @input=${this._onProntoInput}
                        @keydown=${this._onKeydown}
                    ></textarea>
                </div>

                ${this._renderFeedback()}

                <div class="field">
                    <label>Alias (optional)</label>
                    <input
                        type="text"
                        .value=${this._alias}
                        placeholder="e.g. Power"
                        @input=${(e: Event) =>
                            (this._alias = (e.target as HTMLInputElement).value)}
                        @keydown=${this._onKeydown}
                    />
                </div>

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        Cancel
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${!canCreate}
                    >
                        ${this._busy ? "Creating..." : "Create"}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = css`
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        .helper {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        input[type="text"],
        textarea {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        textarea {
            font-family: monospace;
            resize: vertical;
        }
        input[type="text"]:focus,
        textarea:focus {
            outline: none;
            border-color: #b87333;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
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
            color: #2e7d32;
        }
        .status.bad {
            color: #e65100;
        }
        .metrics {
            display: flex;
            gap: 14px;
            margin-top: 6px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
        }
        .diamonds {
            display: flex;
            flex-wrap: wrap;
            gap: 1px;
            margin-top: 8px;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .msg {
            margin-top: 6px;
            font-size: 0.8rem;
        }
        .msg.err {
            color: #e65100;
        }
        .msg.warn {
            color: #b89930;
        }
        .dialog-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid var(--divider-color);
        }
        .action-btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .cancel-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .create-btn {
            background: #b87333;
            color: #fff;
            border-color: #b87333;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-create-signal-dialog": IrCreateSignalDialog;
    }
}
