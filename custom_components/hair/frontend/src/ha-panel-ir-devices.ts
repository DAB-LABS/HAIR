/**
 * Main panel entry point for HAIR.
 *
 * Renders in the HA sidebar as "HAIR" and routes between the device
 * list, device detail, and sniffer views. Holds the
 * WebSocket API client and the in-memory device cache.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { HairApi } from "./api.js";
import "./ir-device-list.js";
import "./ir-add-device-dialog.js";
import "./ir-signal-monitor.js";
import type { DeviceSummary, IRDevice } from "./types.js";

type PanelTab = "devices" | "sniffer";

@customElement("ha-panel-ir-devices")
export class HaPanelIrDevices extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public narrow = false;
    @property({ attribute: false }) public route?: { prefix: string; path: string };
    @property({ attribute: false }) public panel?: { config?: { entry_id?: string } };

    @state() private _activeTab: PanelTab = "devices";
    @state() private _devices: DeviceSummary[] = [];
    @state() private _expandedDeviceId: string | null = null;
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

    private _toggleDevice(deviceId: string): void {
        this._expandedDeviceId =
            this._expandedDeviceId === deviceId ? null : deviceId;
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
        this._expandedDeviceId = event.detail.id;
    }

    private async _onDeviceChanged(): Promise<void> {
        await this._refreshDevices();
    }

    private async _onDeviceDeleted(): Promise<void> {
        this._expandedDeviceId = null;
        await this._refreshDevices();
    }

    private _switchTab(tab: PanelTab): void {
        this._expandedDeviceId = null;
        this._activeTab = tab;
        if (tab === "devices") {
            void this._refreshDevices();
        }
    }

    render() {
        if (!this._api) {
            return html`<div class="loading">Loading…</div>`;
        }

        return html`
            <ha-top-app-bar-fixed>
                <ha-icon-button
                    slot="navigationIcon"
                    .path=${"M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}
                ></ha-icon-button>
                <span slot="title">HAIR</span>
            </ha-top-app-bar-fixed>

            <div class="header-banner">
                <img
                    src="/hair_panel/assets/hair-header.png"
                    alt="HAIR"
                    class="header-img"
                />
            </div>

            <div class="tab-bar">
                <button
                    class="tab ${this._activeTab === "devices" ? "active" : ""}"
                    @click=${() => this._switchTab("devices")}
                >
                    Devices
                </button>
                <button
                    class="tab ${this._activeTab === "sniffer" ? "active" : ""}"
                    @click=${() => this._switchTab("sniffer")}
                >
                    Sniffer
                </button>
            </div>

            <div class="content">
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}
                ${this._activeTab === "devices"
                    ? html`
                          <ir-device-list
                              .devices=${this._devices}
                              .hass=${this.hass}
                              .api=${this._api}
                              .loading=${this._loading}
                              .expandedDeviceId=${this._expandedDeviceId}
                              @device-selected=${(e: CustomEvent<string>) =>
                                  this._toggleDevice(e.detail)}
                              @device-changed=${this._onDeviceChanged}
                              @device-deleted=${this._onDeviceDeleted}
                              @navigate-sniffer=${() => this._switchTab("sniffer")}
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
                      `
                    : html`
                          <ir-signal-monitor
                              .api=${this._api}
                              .hass=${this.hass}
                          ></ir-signal-monitor>
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
        .header-banner {
            max-width: 1100px;
            margin: 0 auto;
            padding: 12px 16px 0;
            text-align: center;
        }
        .header-img {
            max-width: 100%;
            height: auto;
            max-height: 120px;
            object-fit: contain;
            border-radius: 6px;
        }
        .tab-bar {
            display: flex;
            border-bottom: 1px solid var(--divider-color);
            padding: 0 16px;
            max-width: 1100px;
            margin: 0 auto;
        }
        .tab {
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 12px 20px;
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--secondary-text-color);
            cursor: pointer;
            transition: color 150ms ease, border-color 150ms ease;
            font-family: inherit;
        }
        .tab:hover {
            color: var(--primary-text-color);
        }
        .tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
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
