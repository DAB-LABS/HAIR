/**
 * Dialog for creating or editing an IR trigger.
 *
 * Create mode: pass signalFingerprint, protocol, code (read-only signal info).
 * Edit mode: pass an existing trigger object.
 *
 * Emits:
 *   trigger-saved  -- { detail: IRTrigger }
 *   closed         -- dialog dismissed
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-receiver-picker.js";
import type { HairApi } from "./api.js";
import type { IRTrigger } from "./types.js";

@customElement("ir-trigger-dialog")
export class IrTriggerDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;

    /** For create mode: signal details. */
    @property() public signalFingerprint = "";
    @property() public protocol: string | null = null;
    @property() public code: string | null = null;
    @property() public slPattern: string | null = null;
    /** Optional signal alias, shown instead of bare diamonds when set. */
    @property() public alias: string | null = null;
    /** Byte-level identity of the source signal (v0.5.8). Distinguishes
     * sub-threshold sibling buttons that share an S/L fingerprint. */
    @property() public byteHash: string | null = null;
    /** Decoded protocol identity of the source signal (v0.5.8 unified
     * identity). Jitter-immune tier-1 matching where a decoder exists. */
    @property() public decodedFingerprint: string | null = null;

    /** For create mode: optional source references. */
    @property() public sourceDeviceId: string | null = null;
    @property() public sourceCommandId: string | null = null;

    /** For edit mode: pass the existing trigger. */
    @property({ attribute: false }) public trigger: IRTrigger | null = null;

    // Set when opened from a Mirror row (v0.6.6): renders a one-line note
    // that the echo gate keeps the house's own sends from firing triggers.
    @property({ type: Boolean }) public mirrorContext = false;

    @state() private _name = "";
    @state() private _minHits = 1;
    @state() private _receiverIds: string[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.trigger) {
            this._name = this.trigger.name;
            this._minHits = this.trigger.min_hits;
            this._receiverIds = [...(this.trigger.receiver_entity_ids ?? [])];
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _save(): Promise<void> {
        const name = this._name.trim();
        if (!name) {
            this._error = "Name is required.";
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            let saved: IRTrigger;
            if (this.trigger) {
                // Edit mode
                saved = await this.api.updateTrigger(this.trigger.id, {
                    name,
                    min_hits: this._minHits,
                    receiver_entity_ids: this._receiverIds,
                });
            } else {
                // Create mode -- signalFingerprint may be empty when
                // creating from a HAIR command; the backend computes it.
                const payload: Parameters<HairApi["createTrigger"]>[0] = {
                    name,
                    protocol: this.protocol,
                    code: this.code,
                    min_hits: this._minHits,
                    source_device_id: this.sourceDeviceId,
                    source_command_id: this.sourceCommandId,
                    receiver_entity_ids: this._receiverIds,
                };
                if (this.signalFingerprint) {
                    payload.signal_fingerprint = this.signalFingerprint;
                }
                if (this.byteHash) {
                    payload.byte_hash = this.byteHash;
                }
                if (this.decodedFingerprint) {
                    payload.decoded_fingerprint = this.decodedFingerprint;
                }
                saved = await this.api.createTrigger(payload);
            }
            this.dispatchEvent(
                new CustomEvent("trigger-saved", {
                    detail: saved,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = (err as Error).message ?? "Save failed";
        } finally {
            this._busy = false;
        }
    }

    private _emitDelete(): void {
        if (!this.trigger) return;
        this.dispatchEvent(
            new CustomEvent("trigger-delete", {
                detail: { triggerId: this.trigger.id },
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** Compute S/L boolean array from Pronto hex (mirrors backend logic). */
    private _prontoSlArray(hex: string): boolean[] | null {
        const words = hex.trim().split(/\s+/);
        if (words.length < 6) return null;
        const burst1 = parseInt(words[2], 16);
        const burst2 = parseInt(words[3], 16);
        const total = burst1 + burst2;
        const timings = words.slice(4);
        if (timings.length < total * 2) return null;
        const result: boolean[] = [];
        for (let i = 0; i < total * 2; i++) {
            const val = parseInt(timings[i], 16);
            result.push(val >= 0x30); // true = Long, false = Short
        }
        return result.length > 0 ? result : null;
    }

    /** Render diamonds from an S/L pattern string or Pronto hex code. */
    private _renderSignalInfo() {
        const isEdit = !!this.trigger;

        // Named signal: show the alias instead of bare diamonds so the
        // user recognizes which signal this trigger is for.
        if (!isEdit && this.alias) {
            return html`<span class="alias-inline"
                ><span class="alias-tag">alias</span
                ><span class="alias-name">${this.alias}</span></span
            >`;
        }

        // Try S/L pattern string first (from sniffer create mode).
        const patternStr = isEdit ? null : this.slPattern;
        if (patternStr) {
            return html`<span class="diamonds">${[...patternStr].map((ch) =>
                ch === "L"
                    ? html`<span class="diamond long">&#9670;</span>`
                    : html`<span class="diamond short">&#9671;</span>`
            )}</span>`;
        }

        // Try computing from Pronto hex code.
        const prontoCode = isEdit ? this.trigger!.code : this.code;
        const protocol = isEdit ? this.trigger!.protocol : this.protocol;
        if (protocol?.toUpperCase() === "PRONTO" && prontoCode) {
            const arr = this._prontoSlArray(prontoCode);
            if (arr) {
                return html`<span class="diamonds">${arr.map((isLong) =>
                    isLong
                        ? html`<span class="diamond long">&#9670;</span>`
                        : html`<span class="diamond short">&#9671;</span>`
                )}</span>`;
            }
        }

        // Fallback.
        return html`<span class="proto">Trigger Event</span>`;
    }

    render() {
        const isEdit = !!this.trigger;

        return html`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${(e: Event) => e.stopPropagation()}>
                    <h3 class="heading">
                        ${isEdit ? "Edit Trigger" : "Create Trigger"}
                    </h3>

                    <!-- Signal info (read-only) -->
                    <div class="signal-info">
                        ${this._renderSignalInfo()}
                    </div>

                    ${this.mirrorContext
                        ? html`<p class="field-hint scope-hint">
                              Fires when this signal arrives from outside
                              Home Assistant (a physical remote or another
                              app), never on the house's own sends.
                          </p>`
                        : ""}

                    <!-- Name -->
                    <label class="field-label">Trigger Name</label>
                    <input
                        class="field-input"
                        type="text"
                        placeholder="e.g. TV Power"
                        .value=${this._name}
                        @input=${(e: Event) => {
                            this._name = (e.target as HTMLInputElement).value;
                        }}
                        ?disabled=${this._busy}
                    />

                    <!-- Min Hits -->
                    <label class="field-label">
                        Min Hits
                        <span class="field-hint">
                            Number of presses within 5s to fire
                        </span>
                    </label>
                    <input
                        class="field-input hits-input"
                        type="number"
                        min="1"
                        max="10"
                        .value=${String(this._minHits)}
                        @input=${(e: Event) => {
                            const v = parseInt(
                                (e.target as HTMLInputElement).value,
                                10,
                            );
                            if (v >= 1 && v <= 10) this._minHits = v;
                        }}
                        ?disabled=${this._busy}
                    />

                    <!-- Receiver scope -->
                    <div class="receiver-field">
                        <ir-receiver-picker
                            .api=${this.api}
                            .value=${this._receiverIds}
                            ?disabled=${this._busy}
                            @receivers-changed=${(e: CustomEvent) => {
                                this._receiverIds = e.detail.value;
                            }}
                        ></ir-receiver-picker>
                        <p class="field-hint scope-hint">
                            Fires once per press, regardless of how many scoped
                            receivers observe the signal.
                        </p>
                    </div>

                    ${this._error
                        ? html`<p class="error">${this._error}</p>`
                        : ""}

                    <div class="actions">
                        ${isEdit
                            ? html`<button
                                  class="btn delete-btn"
                                  @click=${this._emitDelete}
                                  ?disabled=${this._busy}
                              >Delete</button>`
                            : ""}
                        <span class="actions-spacer"></span>
                        <button
                            class="btn cancel"
                            @click=${this._close}
                            ?disabled=${this._busy}
                        >Cancel</button>
                        <button
                            class="btn save"
                            @click=${this._save}
                            ?disabled=${this._busy || !this._name.trim()}
                        >${this._busy
                            ? "Saving..."
                            : isEdit
                              ? "Update"
                              : "Create"}</button>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
        .signal-info {
            padding: 8px 12px;
            background: var(--secondary-background-color);
            border-radius: 6px;
            margin-bottom: 16px;
            font-family: var(--code-font-family, monospace);
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .proto {
            text-transform: uppercase;
            font-weight: 500;
        }
        .alias-inline {
            display: inline-flex;
            align-items: baseline;
            gap: 7px;
        }
        .alias-tag {
            font-size: 0.6rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: #ba7517;
        }
        .alias-name {
            font-size: 0.9rem;
            color: var(--primary-color);
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
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
        .field-label {
            display: block;
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--primary-text-color);
            margin-bottom: 4px;
        }
        .field-hint {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.78rem;
            margin-left: 4px;
        }
        .field-input {
            display: block;
            width: 100%;
            box-sizing: border-box;
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            font-size: 0.9rem;
            font-family: inherit;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            margin-bottom: 14px;
            outline: none;
            transition: border-color 150ms ease;
        }
        .field-input:focus {
            border-color: var(--primary-color);
        }
        .field-input:disabled {
            opacity: 0.5;
        }
        .hits-input {
            width: 80px;
        }
        .receiver-field {
            margin-bottom: 14px;
        }
        .scope-hint {
            margin: 6px 0 0;
            margin-left: 0;
        }
        .error {
            color: #e65100;
            font-size: 0.85rem;
            margin: 0 0 12px;
        }
        .actions {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 4px;
        }
        .actions-spacer {
            flex: 1;
        }
        .btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .btn:hover {
            background: var(--secondary-background-color);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel {
            color: var(--secondary-text-color);
        }
        .save {
            color: #fff;
            background: #b89930;
            border-color: #b89930;
        }
        .save:hover {
            background: #a08328;
        }
        .delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.3);
        }
        .delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-trigger-dialog": IrTriggerDialog;
    }
}
