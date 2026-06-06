/**
 * Clips tab -- build "clipped" remotes by pasting Pronto codes.
 *
 * Mirrors the Sniffer (ir-signal-monitor) card + dialog structure but
 * without the live-capture, flash, and dismiss-glow machinery, since
 * manual remotes never receive live signals. Queries only manual-source
 * devices and reuses the same Assign / Promote / Trigger / Test / Confirm
 * dialogs the Sniffer uses. Adds two create dialogs and an inline alias
 * editor that replaces the S/L diamonds on a signal once named.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { HairApi } from "./api.js";
import "./ir-assign-signal-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-create-remote-dialog.js";
import "./ir-create-signal-dialog.js";
import "./ir-promote-dialog.js";
import "./ir-signal-alias.js";
import "./ir-test-emitter-dialog.js";
import "./ir-trigger-dialog.js";
import type {
    AssignResult,
    DeviceSummary,
    IRTrigger,
    UnknownDevice,
    UnknownDeviceSummary,
    UnknownSignal,
} from "./types.js";

function fmtTime(iso: string): string {
    try {
        return new Date(iso).toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    } catch {
        return iso;
    }
}

// mdi:paperclip
const ICON_PAPERCLIP =
    "M16.5,6V17.5A4,4 0 0,1 12.5,21.5A4,4 0 0,1 8.5,17.5V5A2.5,2.5 0 0,1 11,2.5A2.5,2.5 0 0,1 13.5,5V15.5A1,1 0 0,1 12.5,16.5A1,1 0 0,1 11.5,15.5V6H10V15.5A2.5,2.5 0 0,0 12.5,18A2.5,2.5 0 0,0 15,15.5V5A4,4 0 0,0 11,1A4,4 0 0,0 7,5V17.5A5.5,5.5 0 0,0 12.5,23A5.5,5.5 0 0,0 18,17.5V6H16.5Z";
// mdi:chevron-down / up
const ICON_EXPAND = "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";
const ICON_COLLAPSE = "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z";

@customElement("ir-clips")
export class IrClips extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    @state() private _devices: UnknownDeviceSummary[] = [];
    @state() private _hairDevices: DeviceSummary[] = [];
    @state() private _triggers: IRTrigger[] = [];
    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _showDismissed = false;
    @state() private _expandedId: string | null = null;
    @state() private _expandedDevice: UnknownDevice | null = null;
    @state() private _confirmClearAll = false;

    // Inline device rename
    @state() private _editingDeviceId: string | null = null;
    @state() private _editLabel = "";

    // Dialog state
    @state() private _createRemoteOpen = false;
    @state() private _createSignalDeviceId: string | null = null;
    @state() private _promoteTarget: UnknownDeviceSummary | null = null;
    @state() private _assignSignal: {
        deviceId: string;
        signal: UnknownSignal;
        label: string | null;
    } | null = null;
    @state() private _deleteSignal: { deviceId: string; signal: UnknownSignal } | null = null;
    @state() private _triggerDialog: { signal: UnknownSignal; deviceId: string } | null = null;
    @state() private _triggerEditDialog: IRTrigger | null = null;
    @state() private _confirmDeleteTriggerId: string | null = null;
    @state() private _testDialog: { signal: UnknownSignal } | null = null;
    @state() private _testEmitters: string[] = [];
    @state() private _testingFingerprint: string | null = null;
    @state() private _testResult: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
    }

    protected updated(changed: PropertyValues): void {
        super.updated(changed);
        if (changed.has("_editingDeviceId") && this._editingDeviceId) {
            const input = this.shadowRoot?.querySelector<HTMLInputElement>(".rename-input");
            input?.focus();
            input?.select();
        }
    }

    private async _load(): Promise<void> {
        this._loading = true;
        try {
            const [unknowns, hairDevs, triggers] = await Promise.all([
                this.api.getUnknownDevices({
                    include_dismissed: this._showDismissed,
                    min_hits: 0,
                    source: "manual",
                }),
                this.api.listDevices(),
                this.api.listTriggers(),
            ]);
            this._devices = unknowns;
            this._hairDevices = hairDevs;
            this._triggers = triggers;
            this._error = null;
        } catch (err) {
            this._error = `Failed to load: ${(err as Error).message}`;
        } finally {
            this._loading = false;
        }
    }

    private _matchesHairDevice(label: string | null): boolean {
        if (!label) return false;
        const lower = label.toLowerCase();
        return this._hairDevices.some((d) => d.name.toLowerCase() === lower);
    }

    private async _refreshExpanded(): Promise<void> {
        if (!this._expandedId) return;
        try {
            this._expandedDevice = await this.api.getUnknownDevice(this._expandedId);
        } catch {
            this._expandedId = null;
            this._expandedDevice = null;
        }
    }

    // --- Create remote / signal ---

    private _openCreateRemote(): void {
        this._createRemoteOpen = true;
    }

    private async _onRemoteCreated(e: CustomEvent<UnknownDevice>): Promise<void> {
        this._createRemoteOpen = false;
        await this._load();
        // Auto-expand the new remote so the user can add a signal at once.
        this._expandedId = e.detail.id;
        await this._refreshExpanded();
    }

    private _openCreateSignal(deviceId: string, e: Event): void {
        e.stopPropagation();
        this._createSignalDeviceId = deviceId;
    }

    private async _onSignalCreated(): Promise<void> {
        this._createSignalDeviceId = null;
        await this._refreshExpanded();
        await this._load();
    }

    // --- Signal alias (delegated to ir-signal-alias) ---

    private _onAliasChanged(
        e: CustomEvent<{ fingerprint: string; alias: string }>,
    ): void {
        const { fingerprint, alias } = e.detail;
        if (!this._expandedDevice) return;
        this._expandedDevice = {
            ...this._expandedDevice,
            signals: this._expandedDevice.signals.map((s) =>
                s.fingerprint === fingerprint ? { ...s, alias } : s,
            ),
        };
    }

    // --- Inline device rename ---

    private _startRename(d: UnknownDeviceSummary, e: Event): void {
        e.stopPropagation();
        this._editingDeviceId = d.id;
        this._editLabel = d.label ?? "";
    }

    private async _commitRename(deviceId: string): Promise<void> {
        const label = this._editLabel.trim();
        this._editingDeviceId = null;
        try {
            const result = await this.api.renameUnknown(deviceId, label);
            const idx = this._devices.findIndex((d) => d.id === deviceId);
            if (idx >= 0) {
                const copy = [...this._devices];
                copy[idx] = { ...copy[idx], label: result.label };
                this._devices = copy;
            }
        } catch (err) {
            this._error = `Rename failed: ${(err as Error).message}`;
        }
    }

    private _onRenameKeydown(deviceId: string, e: KeyboardEvent): void {
        if (e.key === "Enter") {
            void this._commitRename(deviceId);
        } else if (e.key === "Escape") {
            this._editingDeviceId = null;
        }
    }

    // --- Promote / Assign / Delete / Test / Trigger (reuse Sniffer dialogs) ---

    private _promoteDevice(d: UnknownDeviceSummary, e: Event): void {
        e.stopPropagation();
        this._promoteTarget = d;
    }

    private async _onDevicePromoted(): Promise<void> {
        this._promoteTarget = null;
        await this._load();
    }

    private _openAssign(deviceId: string, signal: UnknownSignal, label?: string | null): void {
        this._assignSignal = { deviceId, signal, label: label ?? null };
    }

    private async _onSignalAssigned(_ev: CustomEvent<AssignResult>): Promise<void> {
        this._assignSignal = null;
        await this._load();
        await this._refreshExpanded();
    }

    private _openDelete(deviceId: string, signal: UnknownSignal): void {
        this._deleteSignal = { deviceId, signal };
    }

    private async _confirmDelete(): Promise<void> {
        if (!this._deleteSignal) return;
        const { deviceId, signal } = this._deleteSignal;
        this._deleteSignal = null;
        try {
            await this.api.deleteSignal(deviceId, signal.fingerprint);
            await this._load();
            await this._refreshExpanded();
        } catch (err) {
            this._error = `Delete failed: ${(err as Error).message}`;
        }
    }

    private _openTestDialog(signal: UnknownSignal): void {
        this._testDialog = { signal };
    }

    private async _sendTest(e: CustomEvent): Promise<void> {
        if (!this._testDialog) return;
        const { signal } = this._testDialog;
        const emitters = e.detail.emitters as string[];
        if (emitters.length === 0) return;
        this._testingFingerprint = signal.fingerprint;
        this._testResult = null;
        this._testDialog = null;
        try {
            const results = await Promise.allSettled(
                emitters.map((eid) => this.api.testSignal(signal.fingerprint, eid)),
            );
            const sent = results.filter(
                (r) => r.status === "fulfilled" && r.value.sent,
            ).length;
            const total = emitters.length;
            if (sent === total) {
                this._testResult = total === 1 ? "Sent!" : `Sent! (${sent}/${total})`;
            } else if (sent === 0) {
                this._testResult = "Failed";
            } else {
                this._testResult = `Sent (${sent}/${total})`;
            }
        } catch {
            this._testResult = "Error";
        }
        setTimeout(() => {
            this._testResult = null;
            this._testingFingerprint = null;
        }, 3000);
    }

    private _hasTrigger(fingerprint: string): boolean {
        return this._triggers.some((t) => t.signal_fingerprint === fingerprint);
    }

    private _openTriggerDialog(deviceId: string, signal: UnknownSignal): void {
        const existing = this._triggers.find(
            (t) => t.signal_fingerprint === signal.fingerprint,
        );
        if (existing) {
            this._triggerEditDialog = existing;
        } else {
            this._triggerDialog = { signal, deviceId };
        }
    }

    private _closeTriggerDialog(): void {
        this._triggerDialog = null;
        this._triggerEditDialog = null;
    }

    private _requestDeleteTrigger(triggerId: string): void {
        this._confirmDeleteTriggerId = triggerId;
    }

    private async _doDeleteTrigger(): Promise<void> {
        if (!this._confirmDeleteTriggerId) return;
        const id = this._confirmDeleteTriggerId;
        this._confirmDeleteTriggerId = null;
        this._triggerEditDialog = null;
        try {
            await this.api.deleteTrigger(id);
            this._triggers = await this.api.listTriggers();
        } catch {
            // Non-fatal.
        }
    }

    private async _onTriggerSaved(): Promise<void> {
        this._triggerDialog = null;
        this._triggerEditDialog = null;
        try {
            this._triggers = await this.api.listTriggers();
        } catch {
            // Non-fatal.
        }
    }

    // --- Device list actions ---

    private async _toggleExpand(deviceId: string): Promise<void> {
        if (this._expandedId === deviceId) {
            this._expandedId = null;
            this._expandedDevice = null;
            return;
        }
        this._expandedId = deviceId;
        await this._refreshExpanded();
    }

    private async _dismiss(deviceId: string): Promise<void> {
        try {
            await this.api.dismissUnknown(deviceId);
            await this._load();
            if (this._expandedId === deviceId) {
                this._expandedId = null;
                this._expandedDevice = null;
            }
        } catch (err) {
            this._error = `Dismiss failed: ${(err as Error).message}`;
        }
    }

    private async _undismiss(deviceId: string): Promise<void> {
        try {
            await this.api.undismissUnknown(deviceId);
            await this._load();
        } catch (err) {
            this._error = `Restore failed: ${(err as Error).message}`;
        }
    }

    private async _doClearAll(): Promise<void> {
        this._confirmClearAll = false;
        try {
            await this.api.clearUnknowns("manual");
            this._devices = [];
            this._expandedId = null;
            this._expandedDevice = null;
        } catch (err) {
            this._error = `Clear failed: ${(err as Error).message}`;
        }
    }

    private _toggleDismissed(): void {
        this._showDismissed = !this._showDismissed;
        void this._load();
    }

    // --- Render ---

    render() {
        const count = this._devices.length;
        return html`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${ICON_PAPERCLIP}></ha-svg-icon>
                    HAIR Clips
                    ${!this._loading
                        ? html`<span class="count"
                              >(${count} ${count === 1 ? "remote" : "remotes"})</span
                          >`
                        : ""}
                </span>
                <div class="toolbar-actions">
                    <button class="create-btn" @click=${this._openCreateRemote}>
                        + Create
                    </button>
                    <button class="action-btn dismiss-btn" @click=${this._toggleDismissed}>
                        ${this._showDismissed ? "Hide Dismissed" : "Show Dismissed"}
                    </button>
                </div>
            </div>

            ${this._error
                ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                : ""}

            ${this._loading
                ? html`<div class="loading">Loading...</div>`
                : count === 0
                  ? html`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ICON_PAPERCLIP}></ha-svg-icon>
                            <h3>No virtual remotes yet</h3>
                            <p>
                                Clips lets you build remotes by pasting Pronto codes.
                                Create a remote, then add a signal for each button.
                            </p>
                            <p class="hint">
                                Click "+ Create" above to start a clipped remote.
                            </p>
                        </ha-card>
                    `
                  : html`
                        <div class="device-list">
                            ${this._devices.map((d) => this._renderDevice(d))}
                        </div>
                    `}

            ${count > 0 || this._showDismissed
                ? html`
                      <div class="clear-all-row">
                          <button
                              class="action-btn delete-btn"
                              title="Wipe all clipped remotes and their dismiss entries. Sniffed signals are untouched."
                              @click=${() => (this._confirmClearAll = true)}
                          >Clear All</button>
                      </div>
                  `
                : ""}

            ${this._renderDialogs()}
        `;
    }

    private _renderDevice(d: UnknownDeviceSummary) {
        const expanded = this._expandedId === d.id;
        return html`
            <ha-card class="device clip-device ${d.dismissed ? "dismissed" : ""}">
                <div class="device-row" @click=${() => this._toggleExpand(d.id)}>
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId === d.id
                                ? html`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${(e: Event) => {
                                          this._editLabel = (e.target as HTMLInputElement).value;
                                      }}
                                      @keydown=${(e: KeyboardEvent) => this._onRenameKeydown(d.id, e)}
                                      @blur=${() => void this._commitRename(d.id)}
                                      @click=${(e: Event) => e.stopPropagation()}
                                  />`
                                : html`<ha-svg-icon class="clip-icon" .path=${ICON_PAPERCLIP}></ha-svg-icon>
                                      ${d.dismissed
                                          ? html`<span class="protocol locked"
                                                >${d.label ?? "Remote"}</span
                                            >`
                                          : html`<span
                                                class="protocol"
                                                title="Click to rename"
                                                @click=${(e: Event) => this._startRename(d, e)}
                                            >${d.label ?? "Remote"}</span>`}`}
                            <span class="stat"><strong>${d.signal_count}</strong> signals</span>
                            ${d.label && this._matchesHairDevice(d.label)
                                ? html`<span
                                      class="status-badge hair-device"
                                      @click=${(e: Event) => e.stopPropagation()}
                                  >HAIR Device</span>`
                                : d.label && !d.dismissed
                                    ? html`<span
                                          class="status-badge promote-badge"
                                          @click=${(e: Event) => this._promoteDevice(d, e)}
                                      >Promote</span>`
                                    : ""}
                            ${d.dismissed
                                ? html`<span class="dismissed-badge">dismissed</span>`
                                : ""}
                        </div>
                    </div>
                    ${d.dismissed
                        ? html`<button
                              class="action-btn device-dismiss-btn"
                              @click=${(e: Event) => {
                                  e.stopPropagation();
                                  void this._undismiss(d.id);
                              }}
                          >Restore</button>`
                        : html`<button
                              class="action-btn device-dismiss-btn"
                              @click=${(e: Event) => {
                                  e.stopPropagation();
                                  void this._dismiss(d.id);
                              }}
                          >Dismiss</button>`}
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${expanded ? ICON_COLLAPSE : ICON_EXPAND}
                    ></ha-svg-icon>
                </div>

                ${expanded && this._expandedDevice
                    ? this._renderExpanded(this._expandedDevice)
                    : ""}
            </ha-card>
        `;
    }

    private _renderExpanded(device: UnknownDevice) {
        return html`
            <div class="expanded">
                <div class="signal-header">
                    <span>Signals (${device.signals.length})</span>
                    <button
                        class="create-btn create-signal-btn"
                        ?disabled=${device.dismissed}
                        title=${device.dismissed
                            ? "Restore this remote first"
                            : "Add a signal to this remote"}
                        @click=${(e: Event) => this._openCreateSignal(device.id, e)}
                    >
                        + Create
                    </button>
                </div>
                ${device.signals.length === 0
                    ? html`<div class="no-signals">
                          No signals yet. Click "+ Create" to paste a Pronto code.
                      </div>`
                    : html`
                          <div class="signal-list">
                              ${device.signals.map((sig) =>
                                  this._renderSignal(device.id, sig, device.dismissed),
                              )}
                          </div>
                      `}
            </div>
        `;
    }

    private _renderSignal(deviceId: string, sig: UnknownSignal, dismissed: boolean) {
        const isTesting = this._testingFingerprint === sig.fingerprint;
        return html`
            <div class="signal-row">
                <div class="signal-info">
                    <ir-signal-alias
                        .api=${this.api}
                        .deviceId=${deviceId}
                        .signal=${sig}
                        ?disabled=${dismissed}
                        @alias-changed=${this._onAliasChanged}
                        @alias-error=${(e: CustomEvent) => (this._error = e.detail)}
                    ></ir-signal-alias>
                </div>
                <div class="signal-meta">
                    ${isTesting && this._testResult
                        ? html`<span class="test-result">${this._testResult}</span>`
                        : html`<span>${Math.round(sig.frequency / 1000)} kHz</span>`}
                </div>
                <div class="signal-actions">
                    <button
                        class="action-btn assign-btn"
                        ?disabled=${dismissed}
                        title=${dismissed
                            ? "Restore this remote first"
                            : "Assign this signal to a HAIR device"}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openAssign(deviceId, sig);
                        }}
                    >Assign</button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${dismissed || isTesting}
                        title=${dismissed
                            ? "Restore this remote first"
                            : "Send this signal through an emitter"}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openTestDialog(sig);
                        }}
                    >${isTesting ? "Sending..." : "Test"}</button>
                    <button
                        class="action-btn trigger-btn ${this._hasTrigger(sig.fingerprint) ? "trigger-on" : ""}"
                        ?disabled=${dismissed}
                        title=${dismissed
                            ? "Restore this remote first"
                            : "Create an HA event entity that fires on this signal"}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openTriggerDialog(deviceId, sig);
                        }}
                    >Trigger</button>
                    <button
                        class="action-btn delete-btn"
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openDelete(deviceId, sig);
                        }}
                    >Delete</button>
                </div>
            </div>
        `;
    }

    private _renderDialogs() {
        return html`
            ${this._createRemoteOpen
                ? html`<ir-create-remote-dialog
                      .api=${this.api}
                      @remote-created=${this._onRemoteCreated}
                      @closed=${() => (this._createRemoteOpen = false)}
                  ></ir-create-remote-dialog>`
                : ""}

            ${this._createSignalDeviceId
                ? html`<ir-create-signal-dialog
                      .api=${this.api}
                      .deviceId=${this._createSignalDeviceId}
                      @signal-created=${this._onSignalCreated}
                      @closed=${() => (this._createSignalDeviceId = null)}
                  ></ir-create-signal-dialog>`
                : ""}

            ${this._assignSignal
                ? html`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._assignSignal.deviceId}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${this._assignSignal.label ?? ""}
                      .initialMode=${"existing"}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${() => (this._assignSignal = null)}
                  ></ir-assign-signal-dialog>`
                : ""}

            ${this._promoteTarget
                ? html`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._promoteTarget.label ?? ""}
                      @device-created=${this._onDevicePromoted}
                      @closed=${() => (this._promoteTarget = null)}
                  ></ir-promote-dialog>`
                : ""}

            ${this._deleteSignal
                ? html`<ir-confirm-dialog
                      title="Delete Signal"
                      message="Remove this signal permanently? This cannot be undone."
                      confirmLabel="Delete"
                      .destructive=${true}
                      @confirmed=${this._confirmDelete}
                      @closed=${() => (this._deleteSignal = null)}
                  ></ir-confirm-dialog>`
                : ""}

            ${this._confirmClearAll
                ? html`<ir-confirm-dialog
                      title="Clear All Clips"
                      message="Remove all clipped remotes and their signals? This cannot be undone. Sniffed signals are not affected."
                      confirmLabel="Clear All"
                      .destructive=${true}
                      @confirmed=${this._doClearAll}
                      @closed=${() => (this._confirmClearAll = false)}
                  ></ir-confirm-dialog>`
                : ""}

            ${this._triggerDialog
                ? html`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                      .protocol=${this._triggerDialog.signal.protocol}
                      .code=${this._triggerDialog.signal.code}
                      .slPattern=${this._triggerDialog.signal.sl_pattern ?? null}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                  ></ir-trigger-dialog>`
                : ""}

            ${this._triggerEditDialog
                ? html`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${(e: CustomEvent) =>
                          this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`
                : ""}

            ${this._confirmDeleteTriggerId
                ? html`<ir-confirm-dialog
                      title="Delete Trigger"
                      message="Remove this trigger? The associated HA event entity will also be removed."
                      confirmLabel="Delete"
                      .destructive=${true}
                      @confirmed=${this._doDeleteTrigger}
                      @closed=${() => (this._confirmDeleteTriggerId = null)}
                  ></ir-confirm-dialog>`
                : ""}

            ${this._testDialog
                ? html`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${(e: CustomEvent) =>
                          (this._testEmitters = e.detail.value)}
                      @send=${this._sendTest}
                      @closed=${() => (this._testDialog = null)}
                  ></ir-test-emitter-dialog>`
                : ""}
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: #b87333;
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .toolbar-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        /* Header "+ Create" -- sized to match the Hide Dismissed (action-btn)
           button beside it: same padding/font, copper colors. */
        .create-btn {
            background: none;
            color: #b87333;
            border: 1px solid #b87333;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .create-btn:hover:not(:disabled) {
            background: rgba(184, 115, 51, 0.08);
        }
        .create-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        /* Card-internal "+ Create" -- smaller and pill-shaped, so it reads
           as distinct from the rectangular Assign/Test/Trigger/Delete row. */
        .create-signal-btn {
            padding: 1px 8px;
            font-size: 0.61rem;
            border-radius: 999px;
            position: relative;
            top: 1px;
        }

        .clear-all-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 16px;
        }
        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: #b87333;
            opacity: 0.5;
            margin-bottom: 16px;
        }
        .empty h3 {
            color: var(--primary-text-color);
            margin: 8px 0;
        }
        .hint {
            font-size: 0.85rem;
            font-style: italic;
        }

        .device-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .device.clip-device {
            border: 1px solid rgba(184, 115, 51, 0.4);
            /* Clip the row's rectangular hover highlight to the card's
               rounded corners so its square corners do not poke out over
               the border stroke. */
            overflow: hidden;
        }
        .device.dismissed {
            opacity: 0.6;
        }
        .device-row {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            gap: 12px;
        }
        .device-row:hover {
            background: var(--secondary-background-color);
        }
        .device-info {
            flex: 1;
            min-width: 0;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .clip-icon {
            --mdc-icon-size: 14px;
            color: #b87333;
        }
        .protocol {
            font-weight: 600;
            font-size: 0.95rem;
            cursor: text;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .protocol:not(.locked):hover {
            border-bottom-color: #b87333;
        }
        .protocol.locked {
            cursor: default;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid #b87333;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 160px;
        }
        .dismissed-badge {
            font-size: 0.7rem;
            background: var(--disabled-color, #999);
            color: white;
            padding: 1px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .stat {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .stat strong {
            color: var(--primary-text-color);
        }
        .status-badge.hair-device {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
        }
        .status-badge.promote-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: rgba(0, 151, 167, 0.15);
            color: #0097a7;
            border: 1px solid rgba(0, 151, 167, 0.35);
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 151, 167, 0.25);
        }
        .device-dismiss-btn {
            flex-shrink: 0;
        }
        .expand-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            flex-shrink: 0;
        }

        .expanded {
            border-top: 1px solid var(--divider-color);
            padding: 12px 16px 16px;
        }
        /* "+ Create" sits immediately right of the "Signals (N)" label,
           left-aligned, rather than pushed to the far right. */
        .signal-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .no-signals {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 4px 0;
        }
        .signal-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .signal-row {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            background: var(--primary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        @media (max-width: 768px) {
            .signal-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: start;
                gap: 6px 8px;
            }
            .signal-actions {
                grid-column: 1 / -1;
                justify-content: flex-start;
                flex-wrap: wrap;
            }
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        .test-result {
            color: #2e7d32;
            font-weight: 500;
        }
        .signal-actions {
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }
        .action-btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            color: var(--primary-color);
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease, color 150ms ease, border-color 150ms ease;
        }
        .action-btn:hover {
            background: var(--secondary-background-color);
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .action-btn.assign-btn {
            color: #2e7d32;
            border-color: rgba(46, 125, 50, 0.3);
        }
        .action-btn.assign-btn:hover {
            background: rgba(46, 125, 50, 0.08);
        }
        .action-btn.test-btn {
            color: var(--primary-color);
        }
        .action-btn.trigger-btn {
            color: #b89930;
            border-color: rgba(184, 153, 48, 0.3);
        }
        .action-btn.trigger-btn:hover {
            background: rgba(184, 153, 48, 0.08);
        }
        .action-btn.trigger-btn.trigger-on {
            color: #fff;
            background: #b89930;
            border-color: #b89930;
        }
        .action-btn.delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.25);
        }
        .action-btn.delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
        .action-btn.dismiss-btn {
            color: var(--secondary-text-color);
            border-color: var(--divider-color);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-clips": IrClips;
    }
}
