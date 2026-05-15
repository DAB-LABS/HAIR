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
import { customElement, property, state } from "lit/decorators.js";
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

    /** For create mode: optional source references. */
    @property() public sourceDeviceId: string | null = null;
    @property() public sourceCommandId: string | null = null;

    /** For edit mode: pass the existing trigger. */
    @property({ attribute: false }) public trigger: IRTrigger | null = null;

    @state() private _name = "";
    @state() private _minHits = 1;
    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.trigger) {
            this._name = this.trigger.name;
            this._minHits = this.trigger.min_hits;
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
                };
                if (this.signalFingerprint) {
                    payload.signal_fingerprint = this.signalFingerprint;
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

    /** Render S/L diamond pattern from a pattern string like "SLLSLLS". */
    private _renderDiamonds(pattern: string) {
        return html`<span class="diamonds">${[...pattern].map((ch) =>
            ch === "L"
                ? html`<span class="diamond long">&#9670;</span>`
                : html`<span class="diamond short">&#9671;</span>`
        )}</span>`;
    }

    render() {
        const isEdit = !!this.trigger;
        const displayProtocol = isEdit
            ? this.trigger!.protocol
            : this.protocol;
        const displayPattern = isEdit
            ? null  // triggers don't store sl_pattern directly
            : this.slPattern;

        return html`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${(e: Event) => e.stopPropagation()}>
                    <h3 class="heading">
                        ${isEdit ? "Edit Trigger" : "Create Trigger"}
                    </h3>

                    <!-- Signal info (read-only) -->
                    <div class="signal-info">
                        ${displayPattern
                            ? this._renderDiamonds(displayPattern)
                            : displayProtocol
                              ? html`<span class="proto">${displayProtocol}</span>`
                              : html`<span class="proto">IR Signal</span>`}
                    </div>

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

    static styles = css`
        .overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 100;
        }
        .dialog {
            background: var(--card-background-color, #fff);
            border-radius: 12px;
            padding: 24px;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .heading {
            margin: 0 0 16px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
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
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-trigger-dialog": IrTriggerDialog;
    }
}
