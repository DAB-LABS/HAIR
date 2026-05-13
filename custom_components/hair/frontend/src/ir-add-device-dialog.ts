/**
 * Dialog for adding a new IR device.
 *
 * Auto-detects available emitters (entities in the `infrared` domain)
 * and capture providers (via `hair/capture/providers`) and lets the
 * user pick from the discovered hardware.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import "./ir-emitter-picker.js";
import type { HairApi } from "./api.js";
import type {
    CaptureProviderInfo,
    DeviceTypeId,
    IRDevice,
} from "./types.js";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "tv", label: "TV / Monitor" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "soundbar", label: "Soundbar / Audio" },
    { value: "projector", label: "Projector" },
    { value: "other", label: "Other" },
];

@customElement("ir-add-device-dialog")
export class IrAddDeviceDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;

    @state() private _name = "";
    @state() private _manufacturer = "";
    @state() private _model = "";
    @state() private _deviceType: DeviceTypeId = "tv";
    @state() private _emitterIds: string[] = [];
    @state() private _captureProviderId: string | null = null;
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
            if (this._captureProviders.length === 1) {
                this._captureProviderId = this._captureProviders[0].device_id;
            }
        } catch (err) {
            this._error = `Could not load capture providers: ${
                (err as Error).message
            }`;
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
            const provider = this._captureProviders.find(
                (p) => p.device_id === this._captureProviderId,
            );
            const created: IRDevice = await this.api.createDevice({
                name: this._name.trim(),
                device_type: this._deviceType,
                emitter_entity_ids: this._emitterIds,
                manufacturer: this._manufacturer.trim() || null,
                model: this._model.trim() || null,
                capture_device_id: this._captureProviderId,
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
                heading="Add IR Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

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

                <ha-textfield
                    label="Name"
                    .value=${this._name}
                    required
                    @input=${(e: Event) =>
                        (this._name = (e.target as HTMLInputElement).value)}
                ></ha-textfield>

                <ha-textfield
                    label="Brand (optional)"
                    .value=${this._manufacturer}
                    @input=${(e: Event) =>
                        (this._manufacturer = (e.target as HTMLInputElement).value)}
                ></ha-textfield>

                <ha-textfield
                    label="Model (optional)"
                    .value=${this._model}
                    @input=${(e: Event) =>
                        (this._model = (e.target as HTMLInputElement).value)}
                ></ha-textfield>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${(e: CustomEvent) =>
                        (this._emitterIds = e.detail.value)}
                ></ir-emitter-picker>

                <div class="field">
                    <label>IR receiver (learns commands)</label>
                    ${this._captureProviders.length === 0
                        ? html`<ha-alert alert-type="info">
                              No capture-capable devices detected. You can
                              still create the device and add commands by
                              importing them later.
                          </ha-alert>`
                        : html`
                              <select
                                  .value=${this._captureProviderId ?? ""}
                                  @change=${(e: Event) =>
                                      (this._captureProviderId =
                                          (e.target as HTMLSelectElement)
                                              .value || null)}
                              >
                                  <option value="">None (no learning)</option>
                                  ${this._captureProviders.map(
                                      (p) => html`
                                          <option
                                              value=${p.device_id}
                                              ?selected=${this
                                                  ._captureProviderId ===
                                              p.device_id}
                                          >
                                              ${p.name} (${p.type})
                                          </option>
                                      `,
                                  )}
                              </select>
                          `}
                </div>

                <mwc-button
                    slot="secondaryAction"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    Cancel
                </mwc-button>
                <mwc-button
                    slot="primaryAction"
                    raised
                    @click=${this._create}
                    ?disabled=${this._busy}
                >
                    Create
                </mwc-button>
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
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-add-device-dialog": IrAddDeviceDialog;
    }
}
