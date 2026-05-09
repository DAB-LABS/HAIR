/**
 * Main panel entry point for HAIR.
 *
 * Renders in the HA Settings sidebar as "IR Devices" and routes between
 * the device list and device detail views. Holds the WebSocket API
 * client and the in-memory device cache.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { HairApi } from "./api.js";
import "./ir-device-list.js";
import "./ir-device-detail.js";
import "./ir-add-device-dialog.js";
import type { DeviceSummary, IRDevice } from "./types.js";

@customElement("ha-panel-ir-devices")
export class HaPanelIrDevices extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public narrow = false;
    @property({ attribute: false }) public route?: { prefix: string; path: string };
    @property({ attribute: false }) public panel?: { config?: { entry_id?: string } };

    @state() private _devices: DeviceSummary[] = [];
    @state() private _selectedDevice: IRDevice | null = null;
    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _addDialogOpen = false;

    private _api: HairApi | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.hass) {
            this._init();
        }
    }

    protected updated(changed: PropertyValues): void {
        if (changed.has("hass") && this.hass && !this._api) {
            this._init();
        }
    }

    private _init(): void {
        this._api = new HairApi(this.hass);
        void this._refreshDevices();
    }

    private async _refreshDevices(): Promise<void> {
        if (!this._api) return;
        this._loading = true;
        try {
            this._devices = await this._api.listDevices();
            this._error = null;
        } catch (err) {
            this._error = `Failed to load devices: ${(err as Error).message}`;
        } finally {
            this._loading = false;
        }
    }

    private async _openDevice(deviceId: string): Promise<void> {
        if (!this._api) return;
        try {
            this._selectedDevice = await this._api.getDevice(deviceId);
            const url = `${this.route?.prefix ?? "/ir-devices"}/${deviceId}`;
            history.pushState({ deviceId }, "", url);
        } catch (err) {
            this._error = `Failed to open device: ${(err as Error).message}`;
        }
    }

    private _backToList(): void {
        this._selectedDevice = null;
        history.pushState({}, "", this.route?.prefix ?? "/ir-devices");
    }

    private _openAddDialog(): void {
        this._addDialogOpen = true;
    }

    private _closeAddDialog(): void {
        this._addDialogOpen = false;
    }

    private async _onDeviceCreated(event: CustomEvent<IRDevice>): Promise<void> {
        this._addDialogOpen = false;
        await this._refreshDevices();
        this._selectedDevice = event.detail;
    }

    private async _onDeviceChanged(): Promise<void> {
        await this._refreshDevices();
        if (this._selectedDevice && this._api) {
            this._selectedDevice = await this._api.getDevice(
                this._selectedDevice.id,
            );
        }
    }

    private async _onDeviceDeleted(): Promise<void> {
        this._selectedDevice = null;
        await this._refreshDevices();
    }

    render() {
        if (!this._api) {
            return html`<div class="loading">Loading…</div>`;
        }

        return html`
            <ha-top-app-bar-fixed>
                <ha-icon-button
                    slot="navigationIcon"
                    .path=${this._selectedDevice
                        ? "M19,11H7.83L12.83,6L11.41,4.59L4,12L11.41,19.41L12.83,18L7.83,13H19V11Z"
                        : "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}
                    @click=${this._selectedDevice ? this._backToList : undefined}
                ></ha-icon-button>
                <span slot="title">
                    ${this._selectedDevice
                        ? this._selectedDevice.name
                        : "IR Devices"}
                </span>
            </ha-top-app-bar-fixed>

            <div class="content">
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}
                ${this._selectedDevice
                    ? html`
                          <ir-device-detail
                              .api=${this._api}
                              .device=${this._selectedDevice}
                              .hass=${this.hass}
                              @device-changed=${this._onDeviceChanged}
                              @device-deleted=${this._onDeviceDeleted}
                          ></ir-device-detail>
                      `
                    : html`
                          <ir-device-list
                              .devices=${this._devices}
                              .loading=${this._loading}
                              @device-selected=${(e: CustomEvent<string>) =>
                                  this._openDevice(e.detail)}
                              @add-device=${this._openAddDialog}
                          ></ir-device-list>

                          ${!this._loading && this._devices.length > 0
                              ? html`
                                    <ha-fab
                                        class="fab"
                                        label="Add Device"
                                        extended
                                        @click=${this._openAddDialog}
                                    >
                                        <ha-svg-icon
                                            slot="icon"
                                            .path=${"M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"}
                                        ></ha-svg-icon>
                                    </ha-fab>
                                `
                              : ""}
                      `}
            </div>

            ${this._addDialogOpen
                ? html`
                      <ir-add-device-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          @closed=${this._closeAddDialog}
                          @device-created=${this._onDeviceCreated}
                      ></ir-add-device-dialog>
                  `
                : ""}
        `;
    }

    static styles = css`
        :host {
            display: block;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            min-height: 100vh;
        }
        .content {
            padding: 16px;
            max-width: 1100px;
            margin: 0 auto;
        }
        .loading {
            padding: 48px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .fab {
            position: fixed;
            right: 24px;
            bottom: 24px;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ha-panel-ir-devices": HaPanelIrDevices;
    }
}
