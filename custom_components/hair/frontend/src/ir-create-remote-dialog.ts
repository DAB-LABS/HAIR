/**
 * Dialog for creating a new clipped (manual) remote in the Clips tab.
 *
 * Name only -- no device type. Type is chosen at Promote time, exactly
 * like the Sniffer flow, so the two pre-promote paths stay symmetric.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { UnknownDevice } from "./types.js";

@customElement("ir-create-remote-dialog")
export class IrCreateRemoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;

    @state() private _name = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _create(): Promise<void> {
        if (!this._name.trim()) {
            this._error = "Name is required.";
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const remote: UnknownDevice = await this.api.createRemote(
                this._name.trim(),
            );
            this.dispatchEvent(
                new CustomEvent("remote-created", {
                    detail: remote,
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

    private _onKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            void this._create();
        }
    }

    render() {
        return html`
            <ha-dialog
                open
                heading="Create Remote"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <div class="field">
                    <label>Name</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder="e.g. Living Room TV"
                        required
                        autofocus
                        @input=${(e: Event) =>
                            (this._name = (e.target as HTMLInputElement).value)}
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
                        ?disabled=${this._busy}
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
        input[type="text"] {
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
        input[type="text"]:focus {
            outline: none;
            border-color: #b87333;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
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
        "ir-create-remote-dialog": IrCreateRemoteDialog;
    }
}
