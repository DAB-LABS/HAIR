/**
 * Dialog for promoting an unknown Sniffer device to a full HAIR device.
 *
 * Creates the device only -- signal assignment happens separately via
 * the assign-signal dialog.
 *
 * Fires `device-created` on success, `closed` on cancel / close.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import "./ir-emitter-picker.js";
import type { HairApi } from "./api.js";
import type { DeviceTypeId } from "./types.js";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "tv", label: "TV / Monitor" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "soundbar", label: "Soundbar / Audio" },
    { value: "projector", label: "Projector" },
    { value: "other", label: "Other" },
];

@customElement("ir-promote-dialog")
export class IrPromoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    /** Pre-filled device name from the unknown device label. */
    @property() public suggestedName = "";

    @state() private _name = "";
    @state() private _type: DeviceTypeId = "other";
    @state() private _emitterIds: string[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.suggestedName && !this._name) {
            this._name = this.suggestedName;
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _create(): Promise<void> {
        const name = this._name.trim();
        if (!name) {
            this._error = "Device name is required.";
            return;
        }
        if (this._emitterIds.length === 0) {
            this._error = "Select at least one IR emitter.";
            return;
        }

        this._busy = true;
        this._error = null;

        try {
            await this.api.createDevice({
                name,
                device_type: this._type,
                emitter_entity_ids: this._emitterIds,
            });
            this.dispatchEvent(
                new CustomEvent("device-created", {
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

    render() {
        return html`
            <ha-dialog
                open
                heading="Promote to Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <p class="description">
                    Create a new HAIR device. You can then assign captured
                    signals to it as commands.
                </p>

                <ha-textfield
                    label="Device name"
                    .value=${this._name}
                    required
                    @input=${(e: Event) =>
                        (this._name = (e.target as HTMLInputElement).value)}
                ></ha-textfield>

                <div class="field">
                    <label>Device type</label>
                    <select
                        .value=${this._type}
                        @change=${(e: Event) =>
                            (this._type = (e.target as HTMLSelectElement)
                                .value as DeviceTypeId)}
                    >
                        ${DEVICE_TYPES.map(
                            (t) => html`
                                <option
                                    value=${t.value}
                                    ?selected=${this._type === t.value}
                                >
                                    ${t.label}
                                </option>
                            `,
                        )}
                    </select>
                </div>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${(e: CustomEvent) =>
                        (this._emitterIds = e.detail.value)}
                ></ir-emitter-picker>

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
                        ${this._busy ? "Creating..." : "Create Device"}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = css`
        ha-textfield,
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
        select {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .description {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 0 0 8px;
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
            padding: 8px 20px;
            border-radius: 4px;
            font-size: 0.9rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            border: none;
            transition: background 150ms ease, opacity 150ms ease;
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .cancel-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .cancel-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-promote-dialog": IrPromoteDialog;
    }
}
