/**
 * Reusable confirmation dialog using HA-native ha-dialog wrapper.
 *
 * Usage:
 *   <ir-confirm-dialog
 *       .title=${"Delete signal?"}
 *       .message=${"This action cannot be undone."}
 *       .confirmLabel=${"Delete"}
 *       .destructive=${true}
 *       @confirmed=${this._onConfirmed}
 *       @closed=${this._onClosed}
 *   ></ir-confirm-dialog>
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";

@customElement("ir-confirm-dialog")
export class IrConfirmDialog extends LitElement {
    @property() public title = "Confirm";
    @property() public message = "Are you sure?";
    @property() public confirmLabel = "Confirm";
    @property() public cancelLabel = "Cancel";
    @property({ type: Boolean }) public destructive = false;
    @state() private _busy = false;

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _confirm(): void {
        this.dispatchEvent(
            new CustomEvent("confirmed", { bubbles: true, composed: true }),
        );
    }

    render() {
        return html`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${(e: Event) => e.stopPropagation()}>
                    <h3 class="heading">${this.title}</h3>
                    <p class="message">${this.message}</p>
                    <div class="actions">
                        <button class="btn cancel" @click=${this._close}>
                            ${this.cancelLabel}
                        </button>
                        <button
                            class="btn confirm ${this.destructive ? "destructive" : ""}"
                            @click=${this._confirm}
                        >
                            ${this.confirmLabel}
                        </button>
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
            margin: 0 0 12px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .message {
            margin: 0 0 20px;
            color: var(--secondary-text-color);
            line-height: 1.5;
            font-size: 0.95rem;
        }
        .actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
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
        .cancel {
            color: var(--secondary-text-color);
        }
        .confirm {
            color: #fff;
            background: var(--primary-color);
            border-color: var(--primary-color);
        }
        .confirm:hover {
            opacity: 0.9;
        }
        .confirm.destructive {
            background: #e65100;
            border-color: #e65100;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-confirm-dialog": IrConfirmDialog;
    }
}
