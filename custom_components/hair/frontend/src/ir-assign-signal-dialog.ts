/**
 * Dialog for assigning an unknown signal to a HAIR device.
 *
 * Two modes:
 *   1. Assign to existing device -- pick device, pick/type command name
 *   2. Create new device + assign -- inline device creation fields
 *
 * Fires `signal-assigned` on success (detail: AssignResult).
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type {
    AssignResult,
    CommandCategoryId,
    CommandTemplate,
    DeviceSummary,
    DeviceTypeId,
    UnknownSignal,
} from "./types.js";

type AssignMode = "existing" | "new";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "tv", label: "TV / Monitor" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "soundbar", label: "Soundbar / Audio" },
    { value: "projector", label: "Projector" },
    { value: "other", label: "Other" },
];

const CATEGORIES: { value: CommandCategoryId; label: string }[] = [
    { value: "power", label: "Power" },
    { value: "volume", label: "Volume" },
    { value: "channel", label: "Channel" },
    { value: "navigation", label: "Navigation" },
    { value: "mode", label: "Mode" },
    { value: "temperature", label: "Temperature" },
    { value: "fan_speed", label: "Fan Speed" },
    { value: "custom", label: "Custom" },
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
    @state() private _templates: CommandTemplate[] = [];
    @state() private _selectedDeviceId = "";
    @state() private _commandName = "";
    @state() private _commandCategory: CommandCategoryId = "custom";
    @state() private _useCustomName = false;

    // New-device fields
    @state() private _newName = "";
    @state() private _newType: DeviceTypeId = "tv";
    @state() private _newEmitterId = "";

    @state() private _busy = false;
    @state() private _testing = false;
    @state() private _testResult: string | null = null;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        this._mode = this.initialMode;
        if (this.suggestedDeviceName && !this._newName) {
            this._newName = this.suggestedDeviceName;
        }
        void this._loadDevices();
        if (this._mode === "new") {
            void this._loadTemplates(this._newType);
        }
    }

    private async _loadDevices(): Promise<void> {
        try {
            this._devices = await this.api.listDevices();
        } catch {
            // Non-fatal; user can still create new.
        }
    }

    private async _loadTemplates(deviceType: DeviceTypeId): Promise<void> {
        try {
            this._templates = await this.api.listTemplates(deviceType);
        } catch {
            this._templates = [];
        }
    }

    private async _onDeviceSelected(e: Event): Promise<void> {
        this._selectedDeviceId = (e.target as HTMLSelectElement).value;
        this._commandName = "";
        this._useCustomName = false;
        // Load templates for the selected device's type.
        const dev = this._devices.find((d) => d.id === this._selectedDeviceId);
        if (dev) {
            await this._loadTemplates(dev.device_type);
        }
    }

    private _onTemplateSelected(e: Event): void {
        const val = (e.target as HTMLSelectElement).value;
        if (val === "__custom__") {
            this._useCustomName = true;
            this._commandName = "";
            return;
        }
        this._useCustomName = false;
        this._commandName = val;
        // Set category from template.
        const tmpl = this._templates.find((t) => t.name === val);
        if (tmpl) {
            this._commandCategory = tmpl.category;
        }
    }

    private async _onNewTypeChanged(e: Event): Promise<void> {
        this._newType = (e.target as HTMLSelectElement).value as DeviceTypeId;
        await this._loadTemplates(this._newType);
        this._commandName = "";
        this._useCustomName = false;
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _testSignal(): Promise<void> {
        // Find the emitter to use for testing.
        let emitterEntityId: string | null = null;
        if (this._mode === "existing" && this._selectedDeviceId) {
            const dev = this._devices.find(
                (d) => d.id === this._selectedDeviceId,
            );
            emitterEntityId = dev?.emitter_entity_id ?? null;
        } else if (this._mode === "new" && this._newEmitterId) {
            emitterEntityId = this._newEmitterId;
        }

        if (!emitterEntityId) {
            this._testResult = "Select a device or emitter first.";
            return;
        }

        this._testing = true;
        this._testResult = null;
        try {
            const result = await this.api.testSignal(
                this.signal.fingerprint,
                emitterEntityId,
            );
            this._testResult = result.sent
                ? "Signal sent! Did the target device respond?"
                : "Send failed. Check emitter connection.";
        } catch (err) {
            this._testResult = `Error: ${(err as Error).message}`;
        } finally {
            this._testing = false;
        }
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
                    signal_fingerprint: this.signal.fingerprint,
                    hair_device_id: this._selectedDeviceId,
                    command_name: name,
                    command_category: this._commandCategory,
                });
            } else {
                if (!this._newName.trim()) {
                    this._error = "Device name is required.";
                    this._busy = false;
                    return;
                }
                if (!this._newEmitterId) {
                    this._error = "Select an IR emitter.";
                    this._busy = false;
                    return;
                }
                result = await this.api.assignToNewDevice({
                    device_id: this.unknownDeviceId,
                    signal_fingerprint: this.signal.fingerprint,
                    device_name: this._newName.trim(),
                    device_type: this._newType,
                    emitter_entity_id: this._newEmitterId,
                    command_name: name,
                    command_category: this._commandCategory,
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

    render() {
        const proto = this.signal.protocol ?? "RAW";
        const timings = this.signal.raw_timings?.length ?? 0;
        const freqKhz = this.signal.frequency
            ? `${Math.round(this.signal.frequency / 1000)}kHz`
            : "";
        const signalLabel = [proto, timings ? `${timings} timings` : "", freqKhz]
            .filter(Boolean)
            .join(" · ");

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

                <div class="signal-preview">
                    <span class="signal-info">${signalLabel}</span>
                    <button
                        class="action-btn test-btn"
                        @click=${this._testSignal}
                        ?disabled=${this._testing}
                    >
                        ${this._testing ? "Sending..." : "Test"}
                    </button>
                </div>

                ${this._testResult
                    ? html`<ha-alert
                          alert-type=${this._testResult.startsWith("Signal sent") ? "success" : "warning"}
                      >${this._testResult}</ha-alert>`
                    : ""}

                <!-- Mode tabs -->
                <div class="mode-tabs">
                    <button
                        class="mode-tab ${this._mode === "existing" ? "active" : ""}"
                        @click=${() => { this._mode = "existing"; }}
                    >
                        Existing Device
                    </button>
                    <button
                        class="mode-tab ${this._mode === "new" ? "active" : ""}"
                        @click=${() => { this._mode = "new"; void this._loadTemplates(this._newType); }}
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
        const emitters = this._getEmitters();

        return html`
            <ha-textfield
                label="Device name"
                .value=${this._newName}
                required
                @input=${(e: Event) =>
                    (this._newName = (e.target as HTMLInputElement).value)}
            ></ha-textfield>

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

            <div class="field">
                <label>IR emitter</label>
                ${emitters.length === 0
                    ? html`<ha-alert alert-type="warning">
                          No IR emitters found.
                      </ha-alert>`
                    : html`
                          <select
                              .value=${this._newEmitterId}
                              @change=${(e: Event) =>
                                  (this._newEmitterId = (
                                      e.target as HTMLSelectElement
                                  ).value)}
                          >
                              <option value="" disabled>Select emitter...</option>
                              ${emitters.map(
                                  (em) => html`
                                      <option
                                          value=${em.entity_id}
                                          ?selected=${this._newEmitterId === em.entity_id}
                                      >
                                          ${em.name}
                                      </option>
                                  `,
                              )}
                          </select>
                      `}
            </div>
        `;
    }

    private _renderCommandPicker() {
        return html`
            <div class="field">
                <label>Command name</label>
                ${this._templates.length > 0 && !this._useCustomName
                    ? html`
                          <select
                              .value=${this._commandName}
                              @change=${this._onTemplateSelected}
                          >
                              <option value="" disabled>
                                  Select command...
                              </option>
                              ${this._templates.map(
                                  (t) => html`
                                      <option
                                          value=${t.name}
                                          ?selected=${this._commandName === t.name}
                                      >
                                          ${t.name}${t.essential ? " *" : ""}
                                      </option>
                                  `,
                              )}
                              <option value="__custom__">Custom name...</option>
                          </select>
                      `
                    : html`
                          <ha-textfield
                              label="Command name"
                              .value=${this._commandName}
                              required
                              @input=${(e: Event) =>
                                  (this._commandName = (
                                      e.target as HTMLInputElement
                                  ).value)}
                          ></ha-textfield>
                          ${this._templates.length > 0
                              ? html`<mwc-button
                                    dense
                                    class="back-to-templates"
                                    @click=${() => {
                                        this._useCustomName = false;
                                        this._commandName = "";
                                    }}
                                >
                                    Back to templates
                                </mwc-button>`
                              : ""}
                      `}
            </div>

            <div class="field">
                <label>Category</label>
                <select
                    .value=${this._commandCategory}
                    @change=${(e: Event) =>
                        (this._commandCategory = (e.target as HTMLSelectElement)
                            .value as CommandCategoryId)}
                >
                    ${CATEGORIES.map(
                        (c) => html`
                            <option
                                value=${c.value}
                                ?selected=${this._commandCategory === c.value}
                            >
                                ${c.label}
                            </option>
                        `,
                    )}
                </select>
            </div>
        `;
    }

    private _getEmitters(): { entity_id: string; name: string }[] {
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
        return emitters;
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

        .signal-preview {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: var(--secondary-background-color);
            border-radius: 4px;
            margin-bottom: 12px;
        }
        .signal-info {
            flex: 1;
            font-size: 0.85rem;
            color: var(--primary-text-color);
            font-weight: 500;
        }
        .test-btn {
            background: transparent;
            color: var(--primary-color);
            border: 1px solid rgba(var(--rgb-primary-color, 33,150,243), 0.4) !important;
            padding: 4px 12px !important;
            font-size: 0.8rem !important;
        }
        .test-btn:hover:not(:disabled) {
            background: rgba(var(--rgb-primary-color, 33,150,243), 0.1);
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

        .back-to-templates {
            --mdc-typography-button-font-size: 0.75rem;
            margin-top: 4px;
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
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-assign-signal-dialog": IrAssignSignalDialog;
    }
}
