/**
 * Dialog for assigning an unknown signal to a HAIR device.
 *
 * Two modes:
 *   1. Assign to existing device -- pick device, pick/type command name
 *   2. Create new device + assign -- inline device creation fields
 *
 * Fires `signal-assigned` on success (detail: AssignResult).
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import "./ir-emitter-picker.js";
import type { HairApi } from "./api.js";
import type {
    AssignResult,
    CommandTemplate,
    DeviceSummary,
    DeviceTypeId,
    UnknownSignal,
} from "./types.js";

type AssignMode = "existing" | "new";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "media_player", label: "Media Player" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "light", label: "Light" },
    { value: "switch", label: "Switch" },
    { value: "screen", label: "Screen / Shade" },
    { value: "other", label: "Other" },
];


@customElement("ir-assign-signal-dialog")
export class IrAssignSignalDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    /** The unknown device ID that owns this signal. */
    @property() public unknownDeviceId!: string;

    /** The signal to assign. */
    @property({ attribute: false }) public signal!: UnknownSignal;

    /** Optional suggested device name from the unknown device label. */
    @property() public suggestedDeviceName = "";

    /** Which tab to start on ("existing" or "new"). */
    @property() public initialMode: AssignMode = "existing";

    // --- state ---
    @state() private _mode: AssignMode = "existing";
    @state() private _devices: DeviceSummary[] = [];
    @state() private _selectedDeviceId = "";
    @state() private _commandName = "";

    // New-device fields
    @state() private _newName = "";
    @state() private _newType: DeviceTypeId = "media_player";
    @state() private _newEmitterIds: string[] = [];

    // Command name templates
    @state() private _templates: CommandTemplate[] = [];
    @state() private _customCommand = false;

    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        this._mode = this.initialMode;
        if (this.suggestedDeviceName && !this._newName) {
            this._newName = this.suggestedDeviceName;
        }
        void this._loadDevices();
        // Templates loaded after _loadDevices resolves (for existing mode)
        // or immediately for new mode.
        if (this._mode === "new") {
            void this._loadTemplates(this._newType);
        }
    }

    private async _loadDevices(): Promise<void> {
        try {
            this._devices = await this.api.listDevices();
            // Auto-select target device if the suggested name matches.
            if (this.suggestedDeviceName && !this._selectedDeviceId) {
                const lower = this.suggestedDeviceName.toLowerCase();
                const match = this._devices.find(
                    (d) => d.name.toLowerCase() === lower,
                );
                if (match) {
                    this._selectedDeviceId = match.id;
                    // Load templates for the matched device's type.
                    void this._loadTemplates(match.device_type as DeviceTypeId);
                    return;
                }
            }
            // If in existing mode and we have devices but no auto-match,
            // load templates for the first device or fallback to "other".
            if (this._mode === "existing" && this._devices.length > 0) {
                const first = this._devices[0];
                void this._loadTemplates(first.device_type as DeviceTypeId);
            } else if (this._mode === "existing") {
                void this._loadTemplates("other");
            }
        } catch {
            // Non-fatal; user can still create new.
            if (this._mode === "existing") {
                void this._loadTemplates("other");
            }
        }
    }

    private async _loadTemplates(deviceType: DeviceTypeId): Promise<void> {
        try {
            this._templates = await this.api.listTemplates(deviceType);
        } catch {
            this._templates = [];
        }
        // Reset command name when templates change, unless user typed custom.
        if (!this._customCommand) {
            this._commandName = "";
        }
    }

    /** Get the device type for the currently-selected target. */
    private _activeDeviceType(): DeviceTypeId {
        if (this._mode === "new") return this._newType;
        const dev = this._devices.find((d) => d.id === this._selectedDeviceId);
        return (dev?.device_type as DeviceTypeId) ?? "other";
    }

    private _onDeviceSelected(e: Event): void {
        this._selectedDeviceId = (e.target as HTMLSelectElement).value;
        // Reload templates for the selected device's type.
        const dev = this._devices.find((d) => d.id === this._selectedDeviceId);
        if (dev) {
            void this._loadTemplates(dev.device_type as DeviceTypeId);
        }
    }

    private _onNewTypeChanged(e: Event): void {
        this._newType = (e.target as HTMLSelectElement).value as DeviceTypeId;
        void this._loadTemplates(this._newType);
    }

    private _switchMode(mode: AssignMode): void {
        if (mode === this._mode) return;
        this._mode = mode;
        this._customCommand = false;
        this._commandName = "";
        // Reload templates for the active device type in the new mode.
        void this._loadTemplates(this._activeDeviceType());
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _assign(): Promise<void> {
        const name = this._commandName.trim();
        if (!name) {
            this._error = "Command name is required.";
            return;
        }

        this._busy = true;
        this._error = null;

        try {
            let result: AssignResult;

            if (this._mode === "existing") {
                if (!this._selectedDeviceId) {
                    this._error = "Select a target device.";
                    this._busy = false;
                    return;
                }
                result = await this.api.assignSignal({
                    device_id: this.unknownDeviceId,
                    signal_id: this.signal.id,
                    hair_device_id: this._selectedDeviceId,
                    command_name: name,
                });
            } else {
                if (!this._newName.trim()) {
                    this._error = "Device name is required.";
                    this._busy = false;
                    return;
                }
                if (this._newEmitterIds.length === 0) {
                    this._error = "Select at least one IR emitter.";
                    this._busy = false;
                    return;
                }
                result = await this.api.assignToNewDevice({
                    device_id: this.unknownDeviceId,
                    signal_id: this.signal.id,
                    device_name: this._newName.trim(),
                    device_type: this._newType,
                    emitter_entity_ids: this._newEmitterIds,
                    command_name: name,
                });
            }

            if (result.assigned) {
                this.dispatchEvent(
                    new CustomEvent("signal-assigned", {
                        detail: result,
                        bubbles: true,
                        composed: true,
                    }),
                );
            } else {
                this._error = "Assignment failed. The signal may have a duplicate code on the target device.";
            }
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private _fmtTime(iso: string): string {
        try {
            const d = new Date(iso);
            return d.toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
            });
        } catch {
            return iso;
        }
    }

    render() {
        const proto = this.signal.protocol ?? "RAW";
        const freqKhz = this.signal.frequency
            ? `${Math.round(this.signal.frequency / 1000)}kHz`
            : "";

        return html`
            <ha-dialog
                open
                heading="Assign Signal"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <div class="signal-header">
                    ${this.suggestedDeviceName
                        ? html`<div class="device-name">${this.suggestedDeviceName}</div>`
                        : ""}
                    <div class="signal-detail">
                        ${this.signal.sl_pattern
                            ? html`<span class="diamonds">${[...this.signal.sl_pattern].map((ch) =>
                                ch === "L"
                                    ? html`<span class="diamond long">&#9670;</span>`
                                    : html`<span class="diamond short">&#9671;</span>`
                              )}</span>`
                            : html`<span class="proto-label">${proto}</span>`}
                    </div>
                    <div class="signal-stats">
                        <span>${this.signal.hit_count} hits</span>
                        ${freqKhz ? html`<span>${freqKhz}</span>` : ""}
                        <span>${this._fmtTime(this.signal.last_seen)}</span>
                    </div>
                </div>

                <!-- Mode tabs -->
                <div class="mode-tabs">
                    <button
                        class="mode-tab ${this._mode === "existing" ? "active" : ""}"
                        @click=${() => { this._switchMode("existing"); }}
                    >
                        Existing Device
                    </button>
                    <button
                        class="mode-tab ${this._mode === "new" ? "active" : ""}"
                        @click=${() => { this._switchMode("new"); }}
                    >
                        New Device
                    </button>
                </div>

                ${this._mode === "existing"
                    ? this._renderExistingMode()
                    : this._renderNewMode()}

                <!-- Command name (shared by both modes) -->
                ${this._renderCommandPicker()}

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        Cancel
                    </button>
                    <button
                        class="action-btn assign-btn"
                        @click=${this._assign}
                        ?disabled=${this._busy}
                    >
                        ${this._busy ? "Assigning..." : this._mode === "new" ? "Create & Assign" : "Assign"}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    private _renderExistingMode() {
        return html`
            <div class="field">
                <label>Target device</label>
                ${this._devices.length === 0
                    ? html`<ha-alert alert-type="info">
                          No devices yet. Switch to "New Device" to create one.
                      </ha-alert>`
                    : html`
                          <select
                              .value=${this._selectedDeviceId}
                              @change=${this._onDeviceSelected}
                          >
                              <option value="" disabled>Select device...</option>
                              ${this._devices.map(
                                  (d) => html`
                                      <option
                                          value=${d.id}
                                          ?selected=${this._selectedDeviceId === d.id}
                                      >
                                          ${d.name} (${d.device_type})
                                      </option>
                                  `,
                              )}
                          </select>
                      `}
            </div>
        `;
    }

    private _renderNewMode() {
        return html`
            <div class="field">
                <label>Device name</label>
                <input
                    type="text"
                    .value=${this._newName}
                    placeholder="e.g. Living Room TV"
                    required
                    autofocus
                    @input=${(e: Event) =>
                        (this._newName = (e.target as HTMLInputElement).value)}
                />
            </div>

            <div class="field">
                <label>Device type</label>
                <select
                    .value=${this._newType}
                    @change=${this._onNewTypeChanged}
                >
                    ${DEVICE_TYPES.map(
                        (t) => html`
                            <option
                                value=${t.value}
                                ?selected=${this._newType === t.value}
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
                .value=${this._newEmitterIds}
                ?disabled=${this._busy}
                @emitters-changed=${(e: CustomEvent) =>
                    (this._newEmitterIds = e.detail.value)}
            ></ir-emitter-picker>
        `;
    }

    private _onCommandSelect(e: Event) {
        const val = (e.target as HTMLSelectElement).value;
        if (val === "__custom__") {
            this._customCommand = true;
            this._commandName = "";
            this.updateComplete.then(() => {
                const input = this.shadowRoot?.querySelector<HTMLInputElement>(".custom-cmd-input");
                input?.focus();
            });
        } else {
            this._customCommand = false;
            this._commandName = val;
        }
    }

    private _renderCommandPicker() {
        if (this._customCommand) {
            return html`
                <div class="field">
                    <label>Command name</label>
                    <div class="custom-cmd-row">
                        <input
                            class="custom-cmd-input"
                            type="text"
                            placeholder="Enter command name"
                            .value=${this._commandName}
                            @input=${(e: Event) =>
                                (this._commandName = (e.target as HTMLInputElement).value)}
                        />
                        <button
                            class="back-link"
                            @click=${() => { this._customCommand = false; this._commandName = ""; }}
                        >Templates</button>
                    </div>
                </div>
            `;
        }
        return html`
            <div class="field">
                <label>Command name</label>
                <select
                    .value=${this._commandName}
                    @change=${this._onCommandSelect}
                >
                    <option value="" disabled ?selected=${!this._commandName}>
                        Select command...
                    </option>
                    ${this._templates.map(
                        (t) => html`
                            <option
                                value=${t.name}
                                ?selected=${this._commandName === t.name}
                            >
                                ${t.name}
                            </option>
                        `,
                    )}
                    <option value="__custom__">Custom...</option>
                </select>
            </div>
        `;
    }

    static styles = css`
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
        input[type="text"],
        select {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        input[type="text"]:focus,
        select:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }

        .signal-header {
            padding: 10px 12px;
            background: var(--secondary-background-color);
            border-radius: 4px;
            margin-bottom: 12px;
        }
        .device-name {
            font-weight: 600;
            font-size: 0.95rem;
            margin-bottom: 6px;
        }
        .signal-detail {
            margin-bottom: 4px;
        }
        .diamonds {
            font-size: 0.7rem;
            letter-spacing: 0px;
            line-height: 1;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .proto-label {
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--secondary-text-color);
        }
        .signal-stats {
            display: flex;
            gap: 12px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }

        .mode-tabs {
            display: flex;
            border-bottom: 1px solid var(--divider-color);
            margin: 12px 0;
        }
        .mode-tab {
            flex: 1;
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--secondary-text-color);
            cursor: pointer;
            font-family: inherit;
            transition: color 150ms ease, border-color 150ms ease;
        }
        .mode-tab:hover {
            color: var(--primary-text-color);
        }
        .mode-tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
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
        .assign-btn {
            background: var(--primary-color);
            color: var(--text-primary-color, #fff);
        }
        .assign-btn:hover:not(:disabled) {
            opacity: 0.9;
        }

        /* --- Custom command input --- */
        .custom-cmd-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .custom-cmd-input {
            flex: 1;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.9rem;
        }
        .custom-cmd-input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .back-link {
            background: none;
            border: none;
            color: var(--primary-color);
            font-size: 0.8rem;
            font-family: inherit;
            cursor: pointer;
            padding: 4px 8px;
            white-space: nowrap;
        }
        .back-link:hover {
            text-decoration: underline;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-assign-signal-dialog": IrAssignSignalDialog;
    }
}
