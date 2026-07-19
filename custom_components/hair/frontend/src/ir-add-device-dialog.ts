/**
 * Simplified dialog for adding a new IR device.
 *
 * Collects name, device type, and emitter selection.
 * Brand, model, and capture provider can be edited in the
 * device detail view after creation.  Capture provider is
 * auto-selected (first available) behind the scenes.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-emitter-picker.js";
import type { HairApi } from "./api.js";
import type {
    CaptureProviderInfo,
    DeviceTypeId,
    IRDevice,
} from "./types.js";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "media_player", label: "Media Player" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "light", label: "Light" },
    { value: "switch", label: "Switch" },
    { value: "screen", label: "Screen / Shade" },
    { value: "other", label: "Other" },
];

@customElement("ir-add-device-dialog")
export class IrAddDeviceDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;

    @state() private _name = "";
    @state() private _deviceType: DeviceTypeId = "media_player";
    @state() private _emitterIds: string[] = [];
    @state() private _captureProviders: CaptureProviderInfo[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        void this._loadCaptureProviders();
    }

    private async _loadCaptureProviders() {
        try {
            this._captureProviders = await this.api.listCaptureProviders();
        } catch {
            // Non-fatal -- device can still be created without a capture provider.
        }
    }

    private _close() {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _create() {
        if (!this._name.trim()) {
            this._error = "Name is required.";
            return;
        }
        if (this._emitterIds.length === 0) {
            this._error = "Pick at least one IR emitter.";
            return;
        }

        this._busy = true;
        this._error = null;
        try {
            // Auto-select the first capture provider if available.
            const provider = this._captureProviders[0] ?? null;
            const created: IRDevice = await this.api.createDevice({
                name: this._name.trim(),
                device_type: this._deviceType,
                emitter_entity_ids: this._emitterIds,
                capture_device_id: provider?.device_id ?? null,
                capture_provider_type: provider?.type ?? "esphome",
            });
            this.dispatchEvent(
                new CustomEvent("device-created", {
                    detail: created,
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
                heading="Add Device"
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
                    />
                </div>

                <div class="field">
                    <label>Device type</label>
                    <select
                        .value=${this._deviceType}
                        @change=${(e: Event) =>
                            (this._deviceType = (e.target as HTMLSelectElement)
                                .value as DeviceTypeId)}
                    >
                        ${DEVICE_TYPES.map(
                            (t) => html`
                                <option
                                    value=${t.value}
                                    ?selected=${this._deviceType === t.value}
                                >
                                    ${t.label}
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

    static styles = [
        dialogStyles,
        css`
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-add-device-dialog": IrAddDeviceDialog;
    }
}
