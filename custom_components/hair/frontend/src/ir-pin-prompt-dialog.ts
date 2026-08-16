/**
 * "Pin these together?" prompt (signpost 3, Track 3.5, owner-directed
 * 2026-08-15 -- s11 mockup section 4 "The pin prompt").
 *
 * Owner-ruled: no auto-pin, ever. Every mirror-door mint
 * (ws_device_make_remote / ws_trigger_remote_make_device) and every
 * USE-fork mint whose source already carried an opposite-kind link
 * ends with this prompt instead of a silent link -- see
 * ir-device-list.ts's _onRemoteMinted/_onDeviceMinted for the
 * mirror-door trigger.
 *
 * Gated behind PINNING_UI_ENABLED (ir-pin-flag.ts): the header Pin:
 * chip group this dialog's "Pin" button ultimately feeds is still a
 * readonly preview until signpost 4 (no retransmit/derivation
 * behavior lives yet), but the prompt itself calls the real,
 * already-landed Track 2.5 storage command
 * (hair/trigger-remote/pin) -- the pin takes effect in storage
 * immediately, TriggerRemote.pinned_device_ids just has no visible
 * behavior riding on it yet.
 *
 * Plain overlay dialog, not <ha-dialog> -- modeled on
 * ir-confirm-dialog.ts, the closest existing precedent: a small
 * transient two-button prompt has no form state to protect from
 * ha-dialog's real showModal()/close() transition bug the create
 * dialogs work around (see ir-device-settings-dialog.ts's header for
 * that bug's own writeup).
 *
 * Colors are hardcoded literals, not imports from ir-origin-colors.ts
 * -- same convention ir-promote-remote-dialog.ts's own create-btn
 * already uses (its `#f5a623` is hardcoded too, not imported), since
 * lit's `css` tagged template needs `unsafeCSS()` to interpolate an
 * external JS constant and no sibling dialog bothers with that for a
 * one-off color. `#f5a623` is ORIGIN_COLORS.remote (gold, the s11
 * mockup's --gold-peak) and `#43a047` is GREEN_PEAK -- see
 * ir-origin-colors.ts if either token ever needs to move in lockstep
 * with the rest of the app.
 *
 * Fires `pinned` on success, `closed` on "Not now" / backdrop click.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";

@customElement("ir-pin-prompt-dialog")
export class IrPinPromptDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public remoteId = "";
    @property() public remoteName = "";
    @property() public deviceId = "";
    @property() public deviceName = "";

    @state() private _busy = false;
    @state() private _error: string | null = null;

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _pin(): Promise<void> {
        this._busy = true;
        this._error = null;
        try {
            await this.api.pinTriggerRemoteDevice(this.remoteId, this.deviceId);
            this.dispatchEvent(
                new CustomEvent("pinned", { bubbles: true, composed: true }),
            );
        } catch (err) {
            this._error = (err as Error).message;
            this._busy = false;
        }
    }

    render() {
        return html`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${(e: Event) => e.stopPropagation()}>
                    <h3 class="heading">${t("pinprompt.heading")}</h3>
                    ${this._error
                        ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                        : ""}
                    <p class="body">
                        ${t("pinprompt.body", {
                            remote: this.remoteName,
                            device: this.deviceName,
                        })}
                    </p>
                    <div class="visual">
                        <span class="k-remote">${this.remoteName}</span>
                        <span class="arrow">&#8594;</span>
                        <span class="k-device">${this.deviceName}</span>
                    </div>
                    <div class="actions">
                        <button
                            class="btn not-now"
                            @click=${this._close}
                            ?disabled=${this._busy}
                        >
                            ${t("pinprompt.not_now")}
                        </button>
                        <button
                            class="btn pin"
                            @click=${this._pin}
                            ?disabled=${this._busy}
                        >
                            ${this._busy ? t("common.saving") : t("pinprompt.pin")}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            .overlay {
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            }
            .dialog {
                width: 400px;
                max-width: calc(100vw - 32px);
                background: var(--card-background-color, #fff);
                border: 1px solid rgba(245, 166, 35, 0.4);
                border-radius: 10px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
                padding: 14px 16px;
            }
            .heading {
                margin: 0 0 4px;
                font-size: 1rem;
                font-weight: 600;
            }
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            .body {
                margin: 4px 0 0;
                font-size: 0.82rem;
                color: var(--secondary-text-color);
                line-height: 1.5;
            }
            .visual {
                margin: 10px 0 0;
                padding: 10px;
                border-radius: 8px;
                background: var(--secondary-background-color);
                border: 1px solid var(--divider-color);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                font-size: 0.85rem;
                text-align: center;
            }
            .k-remote {
                font-weight: 700;
            }
            .k-device {
                font-weight: 700;
                color: #43a047;
            }
            .arrow {
                color: #f5a623;
                font-weight: 700;
            }
            .actions {
                display: flex;
                justify-content: flex-end;
                gap: 8px;
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid var(--divider-color);
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
            .btn:disabled {
                opacity: 0.6;
                cursor: default;
            }
            .not-now {
                color: var(--secondary-text-color);
            }
            .not-now:hover:not(:disabled) {
                background: var(--secondary-background-color);
            }
            .pin {
                background: #f5a623;
                border-color: #f5a623;
                color: #241c00;
            }
            .pin:hover:not(:disabled) {
                opacity: 0.9;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-pin-prompt-dialog": IrPinPromptDialog;
    }
}
