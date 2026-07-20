/**
 * Dialog for promoting an unknown Sniffer device to a full HAIR device.
 *
 * Creates the device only -- signal assignment happens separately via
 * the assign-signal dialog.
 *
 * Fires `device-created` on success, `closed` on cancel / close.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-emitter-picker.js";
import type { HairApi } from "./api.js";
import type { DeviceTypeId } from "./types.js";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "media_player", label: "Media Player" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "light", label: "Light" },
    { value: "switch", label: "Switch" },
    { value: "screen", label: "Screen / Shade" },
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
            this._error = t("promote.device_name_required");
            return;
        }
        if (this._emitterIds.length === 0) {
            this._error = t("promote.emitter_required");
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
                heading=${t("promote.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <p class="description">${t("promote.description")}</p>

                <div class="field">
                    <label>${t("promote.device_name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${t("common.device_name_placeholder")}
                        required
                        autofocus
                        @input=${(e: Event) =>
                            (this._name = (e.target as HTMLInputElement)
                                .value)}
                        @keydown=${(e: KeyboardEvent) => {
                            if (e.key === "Enter") void this._create();
                        }}
                    />
                </div>

                <div class="field">
                    <label>${t("common.device_type")}</label>
                    <select
                        .value=${this._type}
                        @change=${(e: Event) =>
                            (this._type = (e.target as HTMLSelectElement)
                                .value as DeviceTypeId)}
                    >
                        ${DEVICE_TYPES.map(
                            (dt) => html`
                                <option
                                    value=${dt.value}
                                    ?selected=${this._type === dt.value}
                                >
                                    ${t(`device_type.${dt.value}`)}
                                </option>
                            `,
                        )}
                    </select>
                </div>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${(e: CustomEvent) =>
                        (this._emitterIds = e.detail.value)}
                ></ir-emitter-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn wide cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${t("common.cancel")}
                    </button>
                    <button
                        class="action-btn wide create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy ? t("common.creating") : t("promote.create_device")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
        /* NOTE: no ha-textfield here anymore. This dialog was the
           panel's last ha-textfield user; the element is lazy-loaded by
           the HA frontend and is not reliably defined inside a custom
           panel, so it rendered as an empty, unfocusable shell (shampoo
           bench). The name box is now the shared .field + plain input,
           the same proven pattern as every other dialog. */
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .description {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 0 0 8px;
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-promote-dialog": IrPromoteDialog;
    }
}
