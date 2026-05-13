/**
 * Devices overview page: HAIR device cards, IR emitter cards, and
 * ESPHome proxy cards -- three segregated sections with distinct colors.
 *
 * Emits ``device-selected`` and ``add-device`` events for HAIR devices.
 * Emitter/proxy cards link to their HA integration page on click.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type {
    CaptureProviderInfo,
    DeviceSummary,
    DeviceTypeId,
} from "./types.js";

const DEVICE_TYPE_ICONS: Record<DeviceTypeId, string> = {
    tv: "M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",
    ac: "M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",
    fan: "M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",
    soundbar: "M16,4V8H8V4H16M3,9V14H21V9H3M2,16C2,17.1 2.9,18 4,18H20C21.1,18 22,17.1 22,16V8C22,6.89 21.1,6 20,6H4C2.89,6 2,6.89 2,8V16Z",
    projector: "M4,5A2,2 0 0,0 2,7V17A2,2 0 0,0 4,19H10V21H14V19H20A2,2 0 0,0 22,17V7A2,2 0 0,0 20,5H4M14,8A4,4 0 0,1 18,12A4,4 0 0,1 14,16A4,4 0 0,1 10,12A4,4 0 0,1 14,8M5,9A1,1 0 0,1 6,10A1,1 0 0,1 5,11A1,1 0 0,1 4,10A1,1 0 0,1 5,9M14,10A2,2 0 0,0 12,12A2,2 0 0,0 14,14A2,2 0 0,0 16,12A2,2 0 0,0 14,10Z",
    other: "M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z",
};

const DEVICE_TYPE_LABELS: Record<DeviceTypeId, string> = {
    tv: "TV",
    ac: "Air Conditioner",
    fan: "Fan",
    soundbar: "Soundbar",
    projector: "Projector",
    other: "IR Device",
};

// MDI: access-point (antenna icon) for emitters
const ICON_EMITTER =
    "M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.95 13.53,13.29L16.7,16.46C17.5,15.26 18,13.71 18,12A6,6 0 0,0 12,6A6,6 0 0,0 6,12C6,13.71 6.5,15.26 7.3,16.46L10.47,13.29C10.18,12.95 10,12.5 10,12A2,2 0 0,1 12,10M12,2A10,10 0 0,0 2,12C2,15.07 3.18,17.85 5.09,19.91L7.5,17.5C6.19,15.89 5.5,14 5.5,12A6.5,6.5 0 0,1 12,5.5A6.5,6.5 0 0,1 18.5,12C18.5,14 17.81,15.89 16.5,17.5L18.91,19.91C20.82,17.85 22,15.07 22,12A10,10 0 0,0 12,2Z";

// MDI: router-wireless for proxies
const ICON_PROXY =
    "M20,13A8,8 0 0,0 12,5A8,8 0 0,0 4,13H2A10,10 0 0,1 12,3A10,10 0 0,1 22,13H20M16,13A4,4 0 0,0 12,9A4,4 0 0,0 8,13H6A6,6 0 0,1 12,7A6,6 0 0,1 18,13H16M13,18H11V14H13V18M13,21H11V19H13V21Z";

@customElement("ir-device-list")
export class IrDeviceList extends LitElement {
    @property({ attribute: false }) public devices: DeviceSummary[] = [];
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api?: HairApi;
    @property({ type: Boolean }) public loading = false;

    @state() private _emitters: { entity_id: string; name: string }[] = [];
    @state() private _proxies: CaptureProviderInfo[] = [];

    connectedCallback(): void {
        super.connectedCallback();
        this._discoverHardware();
    }

    updated(changed: Map<string, unknown>): void {
        if (changed.has("hass") || changed.has("api")) {
            this._discoverHardware();
        }
    }

    private async _discoverHardware(): Promise<void> {
        // Emitters from hass.states
        const states = (this.hass?.states ?? {}) as Record<
            string,
            { entity_id: string; attributes: { friendly_name?: string } }
        >;
        const emitters: { entity_id: string; name: string }[] = [];
        for (const [entityId, st] of Object.entries(states)) {
            if (entityId.startsWith("infrared.")) {
                emitters.push({
                    entity_id: entityId,
                    name: st.attributes.friendly_name ?? entityId,
                });
            }
        }
        this._emitters = emitters;

        // Proxies from API
        if (this.api) {
            try {
                this._proxies = await this.api.listCaptureProviders();
            } catch {
                // Non-fatal
            }
        }
    }

    private _select(deviceId: string) {
        this.dispatchEvent(
            new CustomEvent("device-selected", {
                detail: deviceId,
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _add() {
        this.dispatchEvent(
            new CustomEvent("add-device", { bubbles: true, composed: true }),
        );
    }

    private _navigateIntegration(domain: string) {
        const url = `/config/integrations/integration/${domain}`;
        window.history.pushState(null, "", url);
        window.dispatchEvent(new PopStateEvent("popstate"));
    }

    private _emitterIntegrationDomain(entityId: string): string {
        const entityReg = this.hass?.entities?.[entityId];
        if (entityReg?.platform) return entityReg.platform;
        return entityId.split(".")[0];
    }

    render() {
        if (this.loading) {
            return html`<div class="loading">Loading IR devices...</div>`;
        }

        const hasDevices = this.devices.length > 0;
        const hasEmitters = this._emitters.length > 0;
        const hasProxies = this._proxies.length > 0;
        const hasNothing = !hasDevices && !hasEmitters && !hasProxies;

        if (hasNothing) {
            return html`
                <ha-card class="empty">
                    <h2>No IR devices yet</h2>
                    <p>Add your first device to get started.</p>
                    <mwc-button raised @click=${this._add}>+ Add Device</mwc-button>
                </ha-card>
            `;
        }

        return html`
            <!-- HAIR Devices -->
            ${hasDevices
                ? html`
                      <div class="section-header device-section-header">
                          <h2>Devices</h2>
                          <span class="section-count">${this.devices.length}</span>
                      </div>
                      <div class="grid">
                          ${this.devices.map(
                              (device) => html`
                                  <ha-card
                                      class="card device-card"
                                      tabindex="0"
                                      @click=${() => this._select(device.id)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._select(device.id);
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${DEVICE_TYPE_ICONS[
                                                  device.device_type
                                              ] ?? DEVICE_TYPE_ICONS.other}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${device.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${[
                                              device.manufacturer,
                                              DEVICE_TYPE_LABELS[
                                                  device.device_type
                                              ],
                                          ]
                                              .filter(Boolean)
                                              .join(" • ")}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge device-badge">
                                              ${device.command_count} commands
                                          </span>
                                      </div>
                                  </ha-card>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            <!-- Emitters (TX) -->
            ${hasEmitters
                ? html`
                      <div class="section-header emitter-section-header">
                          <h2>Emitters</h2>
                          <span class="section-count">${this._emitters.length}</span>
                      </div>
                      <div class="grid">
                          ${this._emitters.map(
                              (em) => html`
                                  <div
                                      class="card hw-card emitter-card"
                                      tabindex="0"
                                      @click=${() =>
                                          this._navigateIntegration(
                                              this._emitterIntegrationDomain(
                                                  em.entity_id,
                                              ),
                                          )}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (
                                              e.key === "Enter" ||
                                              e.key === " "
                                          ) {
                                              e.preventDefault();
                                              this._navigateIntegration(
                                                  this._emitterIntegrationDomain(
                                                      em.entity_id,
                                                  ),
                                              );
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${ICON_EMITTER}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${em.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${em.entity_id}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge emitter-badge">TX</span>
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            <!-- Proxies (RX) -->
            ${hasProxies
                ? html`
                      <div class="section-header proxy-section-header">
                          <h2>Proxies</h2>
                          <span class="section-count">${this._proxies.length}</span>
                      </div>
                      <div class="grid">
                          ${this._proxies.map(
                              (p) => html`
                                  <div
                                      class="card hw-card proxy-card"
                                      tabindex="0"
                                      @click=${() =>
                                          this._navigateIntegration(p.type)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (
                                              e.key === "Enter" ||
                                              e.key === " "
                                          ) {
                                              e.preventDefault();
                                              this._navigateIntegration(
                                                  p.type,
                                              );
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${ICON_PROXY}
                                          ></ha-svg-icon>
                                          <div class="card-name">${p.name}</div>
                                      </div>
                                      <div class="card-meta">${p.type}</div>
                                      <div class="card-footer">
                                          <span class="badge proxy-badge">RX</span>
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        .loading,
        .empty {
            padding: 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty h2 {
            margin-top: 8px;
            color: var(--primary-text-color);
        }

        /* --- Section headers --- */
        .section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 24px 0 10px;
            padding-bottom: 6px;
            border-bottom: 2px solid var(--divider-color);
        }
        .section-header:first-child {
            margin-top: 0;
        }
        .section-header h2 {
            margin: 0;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        .section-count {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 999px;
            background: var(--secondary-background-color);
            color: var(--secondary-text-color);
        }

        /* Section header accent colors */
        .device-section-header {
            border-bottom-color: var(--primary-color);
        }
        .device-section-header h2 {
            color: var(--primary-color);
        }
        .emitter-section-header {
            border-bottom-color: #1e88e5;
        }
        .emitter-section-header h2 {
            color: #1565c0;
        }
        .proxy-section-header {
            border-bottom-color: #43a047;
        }
        .proxy-section-header h2 {
            color: #2e7d32;
        }

        /* --- Card grid --- */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 12px;
        }

        /* --- Shared card styles --- */
        .card {
            padding: 16px;
            cursor: pointer;
            border-radius: 8px;
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .card:hover,
        .card:focus-visible {
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
            outline: none;
        }
        .card-header {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .card-header ha-svg-icon {
            --mdc-icon-size: 28px;
        }
        .card-name {
            font-size: 1.05rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-meta {
            margin-top: 8px;
            font-size: 0.82rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-footer {
            margin-top: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .badge {
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.78rem;
            font-weight: 500;
        }

        /* --- Device cards (HA default / primary accent) --- */
        .device-card {
            /* ha-card provides its own background */
        }
        .device-card .card-header ha-svg-icon {
            color: var(--primary-color);
        }
        .device-badge {
            background: var(--secondary-background-color);
            color: var(--primary-text-color);
        }

        /* --- Hardware cards (non-ha-card) --- */
        .hw-card {
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
        }

        /* Emitter cards (blue / TX) */
        .emitter-card {
            border-color: rgba(30, 136, 229, 0.25);
            background: rgba(30, 136, 229, 0.04);
        }
        .emitter-card:hover {
            background: rgba(30, 136, 229, 0.09);
        }
        .emitter-card .card-header ha-svg-icon {
            color: #1e88e5;
        }
        .emitter-badge {
            background: rgba(30, 136, 229, 0.15);
            color: #1565c0;
        }

        /* Proxy cards (green / RX) */
        .proxy-card {
            border-color: rgba(56, 142, 60, 0.25);
            background: rgba(56, 142, 60, 0.04);
        }
        .proxy-card:hover {
            background: rgba(56, 142, 60, 0.09);
        }
        .proxy-card .card-header ha-svg-icon {
            color: #43a047;
        }
        .proxy-badge {
            background: rgba(56, 142, 60, 0.15);
            color: #2e7d32;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-list": IrDeviceList;
    }
}
