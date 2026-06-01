/**
 * Dialog that asks the user which emitter(s) a sniffed signal should
 * be tested through. Replaces the old silent "first emitter on first
 * HAIR device" fallback. Send broadcasts through every picked emitter.
 *
 * Reuses ``ir-emitter-picker`` so the chip + dropdown UI is identical
 * to the picker shipping in Add Device / Promote / Assign-to-New-Device.
 *
 * Dispatches:
 *   - ``send`` with detail ``{ emitters: string[] }`` when the user
 *     clicks Send. Parent owns the actual WS call so it can fan out
 *     to multiple emitters and roll up the result onto the originating
 *     signal row.
 *   - ``closed`` on Cancel (or after a parent-driven close).
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import "./ir-emitter-picker.js";
import type { HairApi } from "./api.js";

@customElement("ir-test-emitter-dialog")
export class IrTestEmitterDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;

    /** Initial picked emitters (parent owns the persistent session state). */
    @property({ attribute: false }) public value: string[] = [];

    /** Set true while the parent's WS fan-out is in flight. */
    @property({ type: Boolean }) public busy = false;

    @state() private _local: string[] = [];

    connectedCallback(): void {
        super.connectedCallback();
        // Seed local state from parent so the picker shows the remembered chips.
        this._local = [...this.value];
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _send(): void {
        if (this._local.length === 0) return;
        this.dispatchEvent(
            new CustomEvent("send", {
                detail: { emitters: [...this._local] },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _onEmittersChanged(e: CustomEvent): void {
        this._local = e.detail.value as string[];
        // Bubble the change up so the parent's persistent state stays in sync.
        this.dispatchEvent(
            new CustomEvent("emitters-changed", {
                detail: { value: this._local },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const canSend = this._local.length > 0 && !this.busy;
        return html`
            <ha-dialog
                open
                heading="Send from"
                scrimClickAction=""
                @closed=${this._close}
            >
                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._local}
                    ?disabled=${this.busy}
                    @emitters-changed=${this._onEmittersChanged}
                ></ir-emitter-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this.busy}
                    >
                        Cancel
                    </button>
                    <button
                        class="action-btn send-btn"
                        @click=${this._send}
                        ?disabled=${!canSend}
                    >
                        ${this.busy ? "Sending..." : "Send"}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = css`
        .dialog-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 16px;
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
            transition: background 150ms ease, opacity 150ms ease;
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel-btn {
            color: var(--primary-text-color);
        }
        .cancel-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .send-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .send-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-test-emitter-dialog": IrTestEmitterDialog;
    }
}
