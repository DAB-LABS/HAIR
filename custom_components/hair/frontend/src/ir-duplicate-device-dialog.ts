/**
 * Dialog that clones a HAIR device under a new name. Inherits every
 * command, action mapping, and emitter assignment from the source.
 * Triggers are NOT copied (they live separately and reference specific
 * command ids).
 *
 * Dispatches:
 *   - ``device-duplicated`` with detail ``{ device: IRDevice }`` on success
 *   - ``closed`` on Cancel or after the parent drives a close
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { IRDevice } from "./types.js";

@customElement("ir-duplicate-device-dialog")
export class IrDuplicateDeviceDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;

    /** Id of the device being duplicated. */
    @property({ attribute: false }) public sourceId = "";

    /** Name of the source device (for the hint text and default name). */
    @property({ attribute: false }) public sourceName = "";

    @state() private _name = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        this._name = `${this.sourceName} (Copy)`;
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _duplicate(): Promise<void> {
        const name = this._name.trim();
        if (!name) {
            this._error = "Name is required.";
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const created = await this.api.duplicateDevice(this.sourceId, name);
            this.dispatchEvent(
                new CustomEvent<IRDevice>("device-duplicated", {
                    detail: created,
                    bubbles: true,
                    composed: true,
                }),
            );
            this._close();
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private _onKeyDown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            e.preventDefault();
            void this._duplicate();
        }
    }

    render() {
        return html`
            <ha-dialog
                open
                heading="Duplicate device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <p class="hint">
                    Duplicating <strong>${this.sourceName}</strong>. The new
                    device gets a copy of every command, action mapping, and
                    emitter assignment. You can change anything afterward.
                </p>

                <div class="field">
                    <label>Name</label>
                    <input
                        type="text"
                        .value=${this._name}
                        autofocus
                        required
                        @input=${(e: Event) =>
                            (this._name = (e.target as HTMLInputElement).value)}
                        @keydown=${this._onKeyDown}
                        @focus=${(e: Event) =>
                            (e.target as HTMLInputElement).select()}
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
                        @click=${this._duplicate}
                        ?disabled=${this._busy || !this._name.trim()}
                    >
                        ${this._busy ? "Duplicating..." : "Duplicate"}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = css`
        .hint {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 8px 0 16px;
        }
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 4px;
        }
        .field input {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        .field input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
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
        .create-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-duplicate-device-dialog": IrDuplicateDeviceDialog;
    }
}
