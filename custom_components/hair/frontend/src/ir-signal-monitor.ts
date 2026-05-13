/**
 * Signal Monitor tab -- shows unknown IR devices detected by the
 * always-on SignalMonitor backend. Supports live WebSocket push so
 * new signals appear in real time without polling.
 */
import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { HairApi } from "./api.js";
import "./ir-assign-signal-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-promote-dialog.js";
import type {
    AssignResult,
    DeviceSummary,
    SignalRemovedEvent,
    UnknownDeviceSummary,
    UnknownDevice,
    UnknownSignal,
    UnknownSignalEvent,
} from "./types.js";

/** Format an ISO timestamp to a short locale string. */
function fmtTime(iso: string): string {
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

/** Relative time like "3 min ago". */
function relTime(iso: string): string {
    try {
        const diff = Date.now() - new Date(iso).getTime();
        if (diff < 60_000) return "just now";
        if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} min ago`;
        if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
        return `${Math.floor(diff / 86_400_000)}d ago`;
    } catch {
        return "";
    }
}

// MDI path: mdi:access-point
const ICON_SIGNAL =
    "M4.93,4.93C3.12,6.74 2,9.24 2,12C2,14.76 3.12,17.26 4.93,19.07L6.34,17.66C4.89,16.22 4,14.22 4,12C4,9.79 4.89,7.78 6.34,6.34L4.93,4.93M19.07,4.93L17.66,6.34C19.11,7.78 20,9.79 20,12C20,14.22 19.11,16.22 17.66,17.66L19.07,19.07C20.88,17.26 22,14.76 22,12C22,9.24 20.88,6.74 19.07,4.93M7.76,7.76C6.67,8.85 6,10.35 6,12C6,13.65 6.67,15.15 7.76,16.24L9.17,14.83C8.45,14.11 8,13.11 8,12C8,10.89 8.45,9.89 9.17,9.17L7.76,7.76M16.24,7.76L14.83,9.17C15.55,9.89 16,10.89 16,12C16,13.11 15.55,14.11 14.83,14.83L16.24,16.24C17.33,15.15 18,13.65 18,12C18,10.35 17.33,8.85 16.24,7.76M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10Z";

// MDI path: mdi:eye-off-outline
const ICON_DISMISS =
    "M2,5.27L3.28,4L20,20.72L18.73,22L15.65,18.92C14.5,19.3 13.28,19.5 12,19.5C7,19.5 2.73,16.39 1,12C1.69,10.24 2.79,8.69 4.19,7.46L2,5.27M12,9A3,3 0 0,1 15,12C15,12.35 14.94,12.69 14.83,13L11,9.17C11.31,9.06 11.65,9 12,9M12,4.5C17,4.5 21.27,7.61 23,12C22.18,14.08 20.79,15.88 19,17.19L17.58,15.76C18.94,14.82 20.06,13.54 20.82,12C19.17,8.64 15.76,6.5 12,6.5C10.91,6.5 9.84,6.68 8.84,7L7.3,5.47C8.74,4.85 10.33,4.5 12,4.5M3.18,12C4.83,15.36 8.24,17.5 12,17.5C12.69,17.5 13.37,17.43 14,17.29L11.72,15C10.29,14.85 9.15,13.71 9,12.28L5.6,8.87C4.61,9.72 3.78,10.78 3.18,12Z";

// MDI path: mdi:delete-outline
const ICON_CLEAR =
    "M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z";

// MDI path: mdi:eye-outline
const ICON_RESTORE =
    "M12,9A3,3 0 0,1 15,12A3,3 0 0,1 12,15A3,3 0 0,1 9,12A3,3 0 0,1 12,9M12,4.5C17,4.5 21.27,7.61 23,12C21.27,16.39 17,19.5 12,19.5C7,19.5 2.73,16.39 1,12C2.73,7.61 7,4.5 12,4.5M3.18,12C4.83,15.36 8.24,17.5 12,17.5C15.76,17.5 19.17,15.36 20.82,12C19.17,8.64 15.76,6.5 12,6.5C8.24,6.5 4.83,8.64 3.18,12Z";

// MDI path: mdi:pencil-outline
const ICON_PENCIL =
    "M14.06,9L15,9.94L5.92,19H5V18.08L14.06,9M17.66,3C17.41,3 17.15,3.1 16.96,3.29L15.13,5.12L18.88,8.87L20.71,7.04C21.1,6.65 21.1,6.02 20.71,5.63L18.37,3.29C18.17,3.09 17.92,3 17.66,3M14.06,6.19L3,17.25V21H6.75L17.81,9.94L14.06,6.19Z";

// MDI path: mdi:chevron-down
const ICON_EXPAND =
    "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";

// MDI path: mdi:chevron-up
const ICON_COLLAPSE =
    "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z";


@customElement("ir-signal-monitor")
export class IrSignalMonitor extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    @state() private _devices: UnknownDeviceSummary[] = [];
    @state() private _hairDevices: DeviceSummary[] = [];
    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _showDismissed = false;
    @state() private _expandedId: string | null = null;
    @state() private _expandedDevice: UnknownDevice | null = null;
    @state() private _flashIds = new Set<string>();
    @state() private _flashStats = new Set<string>();
    /** Last 2 signal fingerprints that received a hit (most recent first). */
    @state() private _recentFingerprints: string[] = [];
    /** Signal fingerprints currently in glow animation. */
    @state() private _glowFingerprints = new Set<string>();
    /** Signal fingerprints whose hit count is currently flashing. */
    @state() private _hitFlashFingerprints = new Set<string>();
    @state() private _confirmClearAll = false;

    // Inline rename state
    @state() private _editingDeviceId: string | null = null;
    @state() private _editLabel = "";

    // Dialog state
    @state() private _promoteTarget: UnknownDeviceSummary | null = null;
    @state() private _assignSignal: {
        deviceId: string;
        signal: UnknownSignal;
        label: string | null;
        initialMode: "existing" | "new";
    } | null = null;
    @state() private _deleteSignal: { deviceId: string; signal: UnknownSignal } | null = null;
    @state() private _testingFingerprint: string | null = null;
    @state() private _testResult: string | null = null;

    private _unsubLive: (() => Promise<void>) | null = null;
    private _unsubRemoved: (() => Promise<void>) | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
        void this._subscribeLive();
        void this._subscribeRemoved();
    }

    protected updated(changed: PropertyValues): void {
        super.updated(changed);
        // Auto-focus the rename input when it appears.
        if (changed.has("_editingDeviceId") && this._editingDeviceId) {
            const input = this.shadowRoot?.querySelector<HTMLInputElement>(".rename-input");
            if (input) {
                input.focus();
                input.select();
            }
        }
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        void this._unsubscribeLive();
        void this._unsubscribeRemoved();
    }

    private async _load(): Promise<void> {
        this._loading = true;
        try {
            const [unknowns, hairDevs] = await Promise.all([
                this.api.getUnknownDevices({
                    include_dismissed: this._showDismissed,
                }),
                this.api.listDevices(),
            ]);
            this._devices = unknowns;
            this._hairDevices = hairDevs;
            this._error = null;
        } catch (err) {
            this._error = `Failed to load: ${(err as Error).message}`;
        } finally {
            this._loading = false;
        }
    }

    /** Check if a label matches an existing HAIR device name (case-insensitive). */
    private _matchesHairDevice(label: string | null): boolean {
        if (!label) return false;
        const lower = label.toLowerCase();
        return this._hairDevices.some((d) => d.name.toLowerCase() === lower);
    }

    private async _subscribeLive(): Promise<void> {
        try {
            this._unsubLive = await this.api.subscribeUnknownSignals((ev) => {
                this._onLiveSignal(ev);
            });
        } catch {
            // Non-fatal: live updates just won't work.
        }
    }

    private async _unsubscribeLive(): Promise<void> {
        if (this._unsubLive) {
            await this._unsubLive();
            this._unsubLive = null;
        }
    }

    private async _subscribeRemoved(): Promise<void> {
        try {
            this._unsubRemoved = await this.api.subscribeSignalRemoved(
                (ev: SignalRemovedEvent) => {
                    // Refresh list when a signal is removed (assigned or deleted).
                    void this._load();
                    // If the expanded device was affected, refresh or collapse.
                    if (this._expandedId === ev.device_id) {
                        if (ev.device_removed) {
                            this._expandedId = null;
                            this._expandedDevice = null;
                        } else {
                            void this._toggleExpand(ev.device_id);
                            void this._toggleExpand(ev.device_id);
                        }
                    }
                },
            );
        } catch {
            // Non-fatal.
        }
    }

    private async _unsubscribeRemoved(): Promise<void> {
        if (this._unsubRemoved) {
            await this._unsubRemoved();
            this._unsubRemoved = null;
        }
    }

    // --- Inline rename ---

    private _startRename(d: UnknownDeviceSummary, e: Event): void {
        e.stopPropagation();
        this._editingDeviceId = d.id;
        this._editLabel = d.label ?? d.protocol ?? "";
    }

    private async _commitRename(deviceId: string): Promise<void> {
        const label = this._editLabel.trim();
        this._editingDeviceId = null;
        try {
            const result = await this.api.renameUnknown(deviceId, label);
            // Update local state
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

    private _cancelRename(): void {
        this._editingDeviceId = null;
    }

    private _onRenameKeydown(deviceId: string, e: KeyboardEvent): void {
        if (e.key === "Enter") {
            void this._commitRename(deviceId);
        } else if (e.key === "Escape") {
            this._cancelRename();
        }
    }

    /** Open promote dialog to create a HAIR device from this unknown device. */
    private _promoteDevice(d: UnknownDeviceSummary, e: Event): void {
        e.stopPropagation();
        this._promoteTarget = d;
    }

    private _closePromote(): void {
        this._promoteTarget = null;
    }

    private async _onDevicePromoted(): Promise<void> {
        this._promoteTarget = null;
        await this._load();
    }

    // --- Signal action handlers ---

    private _openAssign(
        deviceId: string,
        signal: UnknownSignal,
        label?: string | null,
        initialMode?: "existing" | "new",
    ): void {
        this._assignSignal = {
            deviceId,
            signal,
            label: label ?? null,
            initialMode: initialMode ?? "existing",
        };
    }

    private _closeAssign(): void {
        this._assignSignal = null;
    }

    private async _onSignalAssigned(_ev: CustomEvent<AssignResult>): Promise<void> {
        this._assignSignal = null;
        // The signal-removed subscription will auto-refresh the list.
        // But do a manual reload as a fallback.
        await this._load();
        if (this._expandedId) {
            try {
                this._expandedDevice = await this.api.getUnknownDevice(this._expandedId);
            } catch {
                this._expandedId = null;
                this._expandedDevice = null;
            }
        }
    }

    private _openDelete(deviceId: string, signal: UnknownSignal): void {
        this._deleteSignal = { deviceId, signal };
    }

    private _closeDelete(): void {
        this._deleteSignal = null;
    }

    private async _confirmDelete(): Promise<void> {
        if (!this._deleteSignal) return;
        const { deviceId, signal } = this._deleteSignal;
        this._deleteSignal = null;
        try {
            await this.api.deleteSignal(deviceId, signal.fingerprint);
            // Signal-removed event will refresh; manual fallback:
            await this._load();
        } catch (err) {
            this._error = `Delete failed: ${(err as Error).message}`;
        }
    }

    private async _testSignalInline(
        signal: UnknownSignal,
        _deviceId: string,
    ): Promise<void> {
        this._testingFingerprint = signal.fingerprint;
        this._testResult = null;
        try {
            // Let the backend pick the emitter from configured devices.
            const result = await this.api.testSignal(signal.fingerprint);
            this._testResult = result.sent ? "Sent!" : "Failed";
        } catch {
            this._testResult = "Error";
        }
        setTimeout(() => {
            this._testResult = null;
            this._testingFingerprint = null;
        }, 3000);
    }

    private _onLiveSignal(ev: UnknownSignalEvent): void {
        const now = new Date().toISOString();

        // Update the matching device in our local list, or add a new one.
        const idx = this._devices.findIndex((d) => d.id === ev.device_id);
        if (idx >= 0) {
            const updated = { ...this._devices[idx] };
            updated.hit_count = ev.device_hit_count ?? ev.hit_count;
            updated.last_seen = now;
            const copy = [...this._devices];
            copy[idx] = updated;
            this._devices = copy;
        } else {
            // New device appeared; reload the full list to get all fields.
            void this._load();
            return;
        }

        // Update per-signal hit count in expanded view.
        if (this._expandedDevice && this._expandedId === ev.device_id) {
            const sigIdx = this._expandedDevice.signals.findIndex(
                (s) => s.fingerprint === ev.signal_fingerprint,
            );
            if (sigIdx >= 0) {
                const updatedSig = { ...this._expandedDevice.signals[sigIdx] };
                updatedSig.hit_count = ev.hit_count;
                updatedSig.last_seen = now;
                const sigs = [...this._expandedDevice.signals];
                sigs[sigIdx] = updatedSig;
                this._expandedDevice = {
                    ...this._expandedDevice,
                    hit_count: ev.device_hit_count ?? ev.hit_count,
                    last_seen: now,
                    signals: sigs,
                };
            } else {
                // New signal on already-expanded device -- re-fetch to pick it up.
                void this.api.getUnknownDevice(ev.device_id).then((detail) => {
                    if (this._expandedId === ev.device_id) {
                        this._expandedDevice = detail;
                    }
                }).catch(() => {});
            }
        }

        // Flash the device card border briefly.
        this._flashIds = new Set([...this._flashIds, ev.device_id]);
        setTimeout(() => {
            const next = new Set(this._flashIds);
            next.delete(ev.device_id);
            this._flashIds = next;
        }, 800);

        // Flash collapsed stats (hit count / signal count) with accent color.
        this._flashStats = new Set([...this._flashStats, ev.device_id]);
        setTimeout(() => {
            const next = new Set(this._flashStats);
            next.delete(ev.device_id);
            this._flashStats = next;
        }, 1500);

        // Track last 2 active signal fingerprints for Assign button highlighting.
        if (ev.signal_fingerprint) {
            const recent = [ev.signal_fingerprint, ...this._recentFingerprints.filter(
                (fp) => fp !== ev.signal_fingerprint,
            )].slice(0, 2);
            this._recentFingerprints = recent;

            // Trigger glow animation on the Assign button.
            this._glowFingerprints = new Set([...this._glowFingerprints, ev.signal_fingerprint]);
            setTimeout(() => {
                const next = new Set(this._glowFingerprints);
                next.delete(ev.signal_fingerprint);
                this._glowFingerprints = next;
            }, 1200);

            // Trigger hit count flash animation.
            this._hitFlashFingerprints = new Set([...this._hitFlashFingerprints, ev.signal_fingerprint]);
            setTimeout(() => {
                const next = new Set(this._hitFlashFingerprints);
                next.delete(ev.signal_fingerprint);
                this._hitFlashFingerprints = next;
            }, 1200);
        }
    }

    private async _toggleExpand(deviceId: string): Promise<void> {
        if (this._expandedId === deviceId) {
            this._expandedId = null;
            this._expandedDevice = null;
            return;
        }
        this._expandedId = deviceId;
        try {
            this._expandedDevice = await this.api.getUnknownDevice(deviceId);
        } catch {
            this._expandedDevice = null;
        }
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
            await this.api.clearUnknowns();
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

    render() {
        return html`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${ICON_SIGNAL}></ha-svg-icon>
                    HAIR Sniffer
                    ${!this._loading
                        ? html`<span class="count">(${this._devices.length})</span>`
                        : ""}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn dismiss-btn"
                        @click=${this._toggleDismissed}
                    >${this._showDismissed ? "Hide Dismissed" : "Show Dismissed"}</button>
                    ${this._devices.length > 0
                        ? html`
                              <button
                                  class="action-btn delete-btn"
                                  @click=${() => (this._confirmClearAll = true)}
                              >Clear All</button>
                          `
                        : ""}
                </div>
            </div>

            ${this._error
                ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                : ""}

            ${this._loading
                ? html`<div class="loading">Scanning for signals...</div>`
                : this._devices.length === 0
                  ? html`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ICON_SIGNAL}></ha-svg-icon>
                            <h3>No unknown signals detected</h3>
                            <p>
                                When unrecognized IR signals are received by your
                                ESPHome devices, they will appear here automatically.
                            </p>
                            <p class="hint">
                                Try pressing a button on a remote that hasn't been
                                configured yet.
                            </p>
                        </ha-card>
                    `
                  : html`
                        <div class="device-list">
                            ${this._devices.map((d) => this._renderDevice(d))}
                        </div>
                    `}

            ${this._assignSignal
                ? html`
                      <ir-assign-signal-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .unknownDeviceId=${this._assignSignal.deviceId}
                          .signal=${this._assignSignal.signal}
                          .suggestedDeviceName=${this._assignSignal.label ?? ""}
                          .initialMode=${this._assignSignal.initialMode}
                          @signal-assigned=${this._onSignalAssigned}
                          @closed=${this._closeAssign}
                      ></ir-assign-signal-dialog>
                  `
                : ""}

            ${this._promoteTarget
                ? html`
                      <ir-promote-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .suggestedName=${this._promoteTarget.label ?? ""}
                          @device-created=${this._onDevicePromoted}
                          @closed=${this._closePromote}
                      ></ir-promote-dialog>
                  `
                : ""}

            ${this._deleteSignal
                ? html`
                      <ir-confirm-dialog
                          title="Delete Signal"
                          message="Remove this signal permanently? This cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._confirmDelete}
                          @closed=${this._closeDelete}
                      ></ir-confirm-dialog>
                  `
                : ""}

            ${this._confirmClearAll
                ? html`
                      <ir-confirm-dialog
                          title="Clear All Signals"
                          message="Remove all unknown signals and devices? This cannot be undone."
                          confirmLabel="Clear All"
                          .destructive=${true}
                          @confirmed=${this._doClearAll}
                          @closed=${() => (this._confirmClearAll = false)}
                      ></ir-confirm-dialog>
                  `
                : ""}
        `;
    }

    private _renderDevice(d: UnknownDeviceSummary) {
        const expanded = this._expandedId === d.id;
        const flashing = this._flashIds.has(d.id);
        const statsFlash = this._flashStats.has(d.id);

        return html`
            <ha-card class="device ${flashing ? "flash" : ""} ${d.dismissed ? "dismissed" : ""}">
                <div
                    class="device-row"
                    @click=${() => this._toggleExpand(d.id)}
                >
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId === d.id
                                ? html`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${(e: Event) => { this._editLabel = (e.target as HTMLInputElement).value; }}
                                      @keydown=${(e: KeyboardEvent) => this._onRenameKeydown(d.id, e)}
                                      @blur=${() => void this._commitRename(d.id)}
                                      @click=${(e: Event) => e.stopPropagation()}
                                  />`
                                : html`<span
                                      class="protocol"
                                      title="Click to rename"
                                      @click=${(e: Event) => this._startRename(d, e)}
                                  >${d.label ?? d.protocol ?? "RAW"}</span>
                                  <ha-svg-icon
                                      class="edit-icon"
                                      .path=${ICON_PENCIL}
                                      title="Rename"
                                      @click=${(e: Event) => this._startRename(d, e)}
                                  ></ha-svg-icon>`}
                            ${d.device_address
                                ? html`<span class="address">addr: ${d.device_address}</span>`
                                : ""}
                            ${d.dismissed
                                ? html`<span class="dismissed-badge">dismissed</span>`
                                : ""}
                        </div>
                        <div class="device-stats ${statsFlash ? "stats-flash" : ""}">
                            <span class="stat">
                                <strong>${d.hit_count}</strong> hits
                            </span>
                            <span class="stat">
                                <strong>${d.signal_count}</strong> signals
                            </span>
                            <span class="stat last-seen" title=${fmtTime(d.last_seen)}>
                                ${relTime(d.last_seen)}
                            </span>
                        </div>
                    </div>
                    ${d.label && this._matchesHairDevice(d.label)
                        ? html`<span
                              class="status-badge hair-device"
                              @click=${(e: Event) => e.stopPropagation()}
                          >HAIR Device</span>`
                        : d.label
                            ? html`<button
                                  class="action-btn promote-btn"
                                  @click=${(e: Event) => this._promoteDevice(d, e)}
                              >Promote to Device</button>`
                            : ""}
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${expanded ? ICON_COLLAPSE : ICON_EXPAND}
                    ></ha-svg-icon>
                </div>

                ${expanded && this._expandedDevice
                    ? this._renderExpanded(this._expandedDevice, d.dismissed)
                    : ""}
            </ha-card>
        `;
    }

    private _renderExpanded(device: UnknownDevice, dismissed: boolean) {
        return html`
            <div class="expanded">
                <div class="signal-header">
                    <span>Signals (${device.signals.length})</span>
                    <span class="first-seen">First seen: ${fmtTime(device.first_seen)}</span>
                </div>
                <div class="signal-list">
                    ${device.signals.map(
                        (sig) => {
                            const recentIdx = this._recentFingerprints.indexOf(sig.fingerprint);
                            const isLatest = recentIdx === 0;
                            const isPrevious = recentIdx === 1;
                            const isGlowing = this._glowFingerprints.has(sig.fingerprint);
                            const isHitFlash = this._hitFlashFingerprints.has(sig.fingerprint);
                            return html`
                            <div class="signal-row">
                                <div class="signal-info">
                                    ${sig.sl_pattern
                                        ? html`<span class="diamonds">${[...sig.sl_pattern].map((ch) =>
                                            ch === "L"
                                                ? html`<span class="diamond long">◆</span>`
                                                : html`<span class="diamond short">◇</span>`
                                          )}</span>`
                                        : html`<code class="signal-code">${sig.protocol ?? "RAW"}: ${sig.code ?? `${sig.raw_timings.length} timings`}</code>`}
                                </div>
                                <div class="signal-meta">
                                    <span class="${isHitFlash ? "hit-flash" : ""}">${sig.hit_count} hits</span>
                                    <span title=${fmtTime(sig.last_seen)}
                                        >${relTime(sig.last_seen)}</span
                                    >
                                </div>
                                <div class="signal-actions">
                                    <button
                                        class="action-btn assign-btn ${isLatest ? "recent-latest" : ""} ${isPrevious ? "recent-previous" : ""} ${isGlowing ? "glow" : ""}"
                                        @click=${(e: Event) => {
                                            e.stopPropagation();
                                            this._openAssign(device.id, sig, device.label);
                                        }}
                                    >Assign</button>
                                    <button
                                        class="action-btn test-btn"
                                        @click=${(e: Event) => {
                                            e.stopPropagation();
                                            void this._testSignalInline(sig, device.id);
                                        }}
                                        ?disabled=${this._testingFingerprint === sig.fingerprint}
                                    >${this._testingFingerprint === sig.fingerprint
                                        ? (this._testResult ?? "Sending...")
                                        : "Test"}</button>
                                    <button
                                        class="action-btn delete-btn"
                                        @click=${(e: Event) => {
                                            e.stopPropagation();
                                            this._openDelete(device.id, sig);
                                        }}
                                    >Delete</button>
                                    ${dismissed
                                        ? html`<button
                                              class="action-btn"
                                              @click=${(e: Event) => {
                                                  e.stopPropagation();
                                                  void this._undismiss(device.id);
                                              }}
                                          >Restore</button>`
                                        : html`<button
                                              class="action-btn dismiss-btn"
                                              @click=${(e: Event) => {
                                                  e.stopPropagation();
                                                  void this._dismiss(device.id);
                                              }}
                                          >Dismiss</button>`}
                                </div>
                            </div>
                        `},
                    )}
                </div>
            </div>
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
            color: var(--primary-color);
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .toolbar-actions {
            display: flex;
            gap: 8px;
        }

        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: var(--disabled-text-color);
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

        .device {
            transition: box-shadow 200ms ease;
        }
        .device.flash {
            box-shadow: 0 0 0 2px var(--primary-color), var(--ha-card-box-shadow, none);
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
        .protocol {
            font-weight: 600;
            font-size: 0.95rem;
            cursor: text;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .protocol:hover {
            border-bottom-color: var(--primary-color);
        }
        .edit-icon {
            --mdc-icon-size: 14px;
            color: var(--secondary-text-color);
            cursor: pointer;
            opacity: 0.4;
            transition: opacity 150ms ease;
        }
        .device-header:hover .edit-icon {
            opacity: 0.8;
        }
        .edit-icon:hover {
            opacity: 1 !important;
            color: var(--primary-color);
        }
        .status-badge.hair-device {
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            padding: 4px 10px;
            border-radius: 4px;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
        }
        .promote-btn {
            flex-shrink: 0;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid var(--primary-color);
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 140px;
        }
        .address {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-family: monospace;
        }
        .dismissed-badge {
            font-size: 0.7rem;
            background: var(--disabled-color, #999);
            color: white;
            padding: 1px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .device-stats {
            display: flex;
            gap: 16px;
            margin-top: 4px;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .stat strong {
            color: var(--primary-text-color);
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
        .signal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .first-seen {
            color: var(--secondary-text-color);
            font-weight: 400;
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
            background: var(--secondary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-code {
            font-size: 0.82rem;
            word-break: break-all;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
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
            transition: background 150ms ease, color 150ms ease,
                        border-color 150ms ease, box-shadow 300ms ease;
        }
        .action-btn:hover {
            background: var(--secondary-background-color);
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }

        /* Semantic button colors */
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
        .action-btn.delete-btn {
            color: #b71c1c;
            border-color: rgba(183, 28, 28, 0.2);
        }
        .action-btn.delete-btn:hover {
            background: rgba(183, 28, 28, 0.06);
        }
        .action-btn.dismiss-btn {
            color: var(--secondary-text-color);
            border-color: var(--divider-color);
        }

        /* Latest signal: bright green filled Assign button */
        .action-btn.assign-btn.recent-latest {
            color: #fff;
            background: #2e7d32;
            border-color: #2e7d32;
        }
        .action-btn.assign-btn.recent-latest:hover {
            background: #1b5e20;
        }

        /* Previous signal: muted green outline Assign button */
        .action-btn.assign-btn.recent-previous {
            color: rgba(46, 125, 50, 0.6);
            border-color: rgba(46, 125, 50, 0.25);
            background: rgba(46, 125, 50, 0.06);
        }
        .action-btn.assign-btn.recent-previous:hover {
            background: rgba(46, 125, 50, 0.12);
        }

        /* Glow pulse animation on hit */
        .action-btn.assign-btn.glow {
            animation: assign-glow 1.2s ease-out;
        }
        @keyframes assign-glow {
            0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.6); }
            50% { box-shadow: 0 0 8px 3px rgba(46, 125, 50, 0.3); }
            100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); }
        }

        /* Hit count flash animation */
        .signal-meta .hit-flash {
            animation: hit-count-glow 1.2s ease-out;
        }
        @keyframes hit-count-glow {
            0% { color: #2e7d32; text-shadow: 0 0 6px rgba(46, 125, 50, 0.8); }
            100% { color: inherit; text-shadow: none; }
        }

        /* Collapsed stats flash on hit */
        .device-stats.stats-flash strong {
            color: var(--primary-color);
            transition: color 300ms ease;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-signal-monitor": IrSignalMonitor;
    }
}
