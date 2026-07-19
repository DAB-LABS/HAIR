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
import { dialogStyles } from "./ir-dialog-styles.js";
import { t } from "./localize.js";

@customElement("ir-confirm-dialog")
export class IrConfirmDialog extends LitElement {
    // Empty-string defaults resolve through t() at render time, so
    // the fallbacks localize (class-body defaults would freeze English
    // before the panel language is known).
    @property() public title = "";
    @property() public message = "";
    @property() public confirmLabel = "";
    @property() public cancelLabel = "";
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
                    <h3 class="heading">${this.title || t("common.confirm")}</h3>
                    <p class="message">${this.message || t("common.are_you_sure")}</p>
                    <div class="actions">
                        <button class="btn cancel" @click=${this._close}>
                            ${this.cancelLabel || t("common.cancel")}
                        </button>
                        <button
                            class="btn confirm ${this.destructive ? "destructive" : ""}"
                            @click=${this._confirm}
                        >
                            ${this.confirmLabel || t("common.confirm")}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
        /* Tighter heading than the shared 16px; ships this way. */
        .heading {
            margin: 0 0 12px;
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
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-confirm-dialog": IrConfirmDialog;
    }
}
