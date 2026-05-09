/**
 * Grid of IR device cards. Emits ``device-selected`` and ``add-device``
 * events; the parent panel handles routing and dialog management.
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { DeviceSummary, DeviceTypeId } from "./types.js";

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

@customElement("ir-device-list")
export class IrDeviceList extends LitElement {
    @property({ attribute: false }) public devices: DeviceSummary[] = [];
    @property({ type: Boolean }) public loading = false;

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

    render() {
        if (this.loading) {
            return html`<div class="loading">Loading IR devices…</div>`;
        }
        if (this.devices.length === 0) {
            return html`
                <ha-card class="empty">
                    <h2>No IR devices yet</h2>
                    <p>Add your first device to get started.</p>
                    <mwc-button raised @click=${this._add}>+ Add Device</mwc-button>
                </ha-card>
            `;
        }

        return html`
            <div class="grid">
                ${this.devices.map(
                    (device) => html`
                        <ha-card
                            class="device"
                            tabindex="0"
                            @click=${() => this._select(device.id)}
                            @keydown=${(e: KeyboardEvent) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    this._select(device.id);
                                }
                            }}
                        >
                            <div class="device-header">
                                <ha-svg-icon
                                    .path=${DEVICE_TYPE_ICONS[device.device_type] ??
                                    DEVICE_TYPE_ICONS.other}
                                ></ha-svg-icon>
                                <div class="device-name">${device.name}</div>
                            </div>
                            <div class="device-meta">
                                ${[
                                    device.manufacturer,
                                    DEVICE_TYPE_LABELS[device.device_type],
                                    device.emitter_entity_id,
                                ]
                                    .filter(Boolean)
                                    .join(" • ")}
                            </div>
                            <div class="device-footer">
                                <span class="badge"
                                    >${device.command_count} commands</span
                                >
                            </div>
                        </ha-card>
                    `,
                )}
            </div>
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
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 16px;
        }
        .device {
            padding: 16px;
            cursor: pointer;
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .device:hover,
        .device:focus-visible {
            transform: translateY(-1px);
            box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.18));
            outline: 2px solid transparent;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .device-header ha-svg-icon {
            --mdc-icon-size: 28px;
            color: var(--primary-color);
        }
        .device-name {
            font-size: 1.1rem;
            font-weight: 500;
        }
        .device-meta {
            margin-top: 8px;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .device-footer {
            margin-top: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .badge {
            background: var(--secondary-background-color);
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.85rem;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-list": IrDeviceList;
    }
}
