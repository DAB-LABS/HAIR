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
import { actionChipStyles } from "./ir-action-chip-styles";
import { customElement, property, state } from "./decorators.js";
import { keyed } from "lit/directives/keyed.js";
import { repeat } from "lit/directives/repeat.js";
import Sortable from "sortablejs";
import { HairApi } from "./api.js";
import "./ir-assign-signal-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-create-remote-dialog.js";
import "./ir-promote-dialog.js";
import "./ir-signal-alias.js";
import "./ir-signal-editor.js";
import "./ir-test-emitter-dialog.js";
import "./ir-trigger-dialog.js";
import "./ir-count-dot.js";
import "./ir-trigger-popover.js";
import "./ir-assigned-popover.js";
import { triggerMatchesSignal } from "./types.js";
import type {
    AssignResult,
    DeviceSummary,
    IRTrigger,
    ReceiverInfo,
    SignalAssignment,
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

// Hair clippers (SVG Repo, two paths merged + scaled to a 24x24 box).
const ICON_CLIPPER =
    "M12.462,10.448c-0.639-0.639-1.678-0.639-2.317,0c-0.639,0.639-0.639,1.678,0,2.317l1.09,1.09c0.319,0.319,0.739,0.479,1.159,0.479c0.42,0,0.839-0.16,1.159-0.479c0-0,0-0,0-0c0.639-0.639,0.639-1.678,0-2.317L12.462,10.448z M12.763,13.066c-0.204,0.204-0.535,0.204-0.739,0l-1.09-1.09c-0.204-0.204-0.204-0.535,0-0.739c0.102-0.102,0.236-0.153,0.369-0.153c0.134,0,0.267,0.051,0.369,0.153l1.09,1.09C12.966,12.531,12.966,12.863,12.763,13.066z M23.998,6.609l-0.104-1.419c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.068-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.069-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.069-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-1.419-0.103c-0.162-0.012-0.321,0.047-0.435,0.162l-1.993,1.993c-0,0.001-0.001,0.001-0.001,0.001c-0.097,0.097-0.191,0.197-0.282,0.298c-1.933,2.042-12.871,13.598-13.716,14.551c-0.722,0.814-0.712,1.983,0.023,2.717l0.341,0.341L0.539,20.852c-0.719,0.719-0.719,1.889,0,2.609c0.36,0.36,0.832,0.539,1.304,0.539c0.472,0,0.945-0.18,1.304-0.539l0.787-0.787l0.341,0.341c0.735,0.735,1.903,0.745,2.717,0.023c0.953-0.845,12.509-11.783,14.551-13.716c0.102-0.091,0.201-0.186,0.299-0.283c0.001-0.001,0.001-0.001,0.001-0.002l1.992-1.992C23.951,6.93,24.01,6.771,23.998,6.609z M20.61,4.179l0.684,0.05l0.05,0.684l-1.418,1.418l-0.733-0.734L20.61,4.179z M19.087,2.656l0.684,0.05l0.05,0.684L18.403,4.807L17.67,4.074L19.087,2.656z M17.564,1.133l0.684,0.05l0.05,0.684l-1.418,1.418l-0.733-0.733L17.564,1.133z M2.359,22.671c-0.284,0.284-0.746,0.284-1.03,0c-0.284-0.284-0.284-0.746,0-1.03l0.787-0.787l1.03,1.03L2.359,22.671z M6.253,22.202c-0.366,0.324-0.877,0.334-1.188,0.023l-0.735-0.735l-2.555-2.555c-0.311-0.311-0.301-0.822,0.023-1.188c0.633-0.715,7.3-7.769,11.189-11.88c-0.014,0.084-0.026,0.169-0.036,0.253c-0.179,1.482,0.239,2.815,1.176,3.752c0.937,0.937,2.27,1.355,3.752,1.176c0.084-0.01,0.169-0.022,0.253-0.036C14.022,14.901,6.968,21.568,6.253,22.202z M14.917,9.083c-0.69-0.69-0.994-1.694-0.857-2.829c0.123-1.019,0.585-2.03,1.315-2.897l0.717,0.717l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.734,0.734l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.734,0.734l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.717,0.717C18.756,10.213,16.277,10.443,14.917,9.083z M21.449,7.853l-0.734-0.734l1.418-1.418l0.684,0.05l0.05,0.684L21.449,7.853z";
// mdi:chevron-down / up
const ICON_EXPAND = "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";
const ICON_COLLAPSE = "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z";
// mdi:content-copy
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";
// MDI: drag (six-dot grip) -- same handle used by the command reorder.
const ICON_GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";

/** Debounce delay (ms) between a drop and the persist call. */
const REORDER_DEBOUNCE_MS = 500;

@customElement("ir-clips")
export class IrClips extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    @state() private _devices: UnknownDeviceSummary[] = [];
    @state() private _hairDevices: DeviceSummary[] = [];
    @state() private _triggers: IRTrigger[] = [];
    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _expandedId: string | null = null;
    @state() private _expandedDevice: UnknownDevice | null = null;
    @state() private _confirmClearAll = false;
    @state() private _deleteRemoteId: string | null = null;
    @state() private _deleteRemoteLabel = "";
    @state() private _deleteRemoteCount = 0;

    // Inline device rename
    @state() private _editingDeviceId: string | null = null;
    @state() private _editLabel = "";

    // Dialog state
    @state() private _createRemoteOpen = false;
    @state() private _createSignalDeviceId: string | null = null;
    @state() private _editSignal: {
        deviceId: string;
        signal: UnknownSignal;
    } | null = null;
    @state() private _promoteTarget: UnknownDeviceSummary | null = null;
    @state() private _assignSignal: {
        deviceId: string;
        signal: UnknownSignal;
        label: string | null;
    } | null = null;
    @state() private _deleteSignal: { deviceId: string; signal: UnknownSignal } | null = null;
    @state() private _triggerDialog: { signal: UnknownSignal; deviceId: string } | null = null;
    @state() private _triggerEditDialog: IRTrigger | null = null;
    @state() private _triggerPopover: {
        deviceId: string;
        signal: UnknownSignal;
        top: number;
        left: number;
    } | null = null;
    // Assigned-commands popover (v0.6.6); mirrors the trigger popover flow.
    @state() private _assignedPopover: {
        deviceId: string;
        signal: UnknownSignal;
        label: string | null;
        top: number;
        left: number;
    } | null = null;
    @state() private _receivers: ReceiverInfo[] = [];
    private _unsubUpdated: (() => Promise<void>) | null = null;
    @state() private _confirmDeleteTriggerId: string | null = null;
    @state() private _testDialog: { signal: UnknownSignal } | null = null;
    @state() private _testEmitters: string[] = [];
    @state() private _testingSignalId: string | null = null;
    @state() private _testResult: string | null = null;

    // Drag-to-reorder (remotes + signals-within-a-remote).
    @state() private _remotesVersion = 0;
    @state() private _signalsVersion = 0;
    private _remotesSortable: Sortable | null = null;
    private _signalsSortable: Sortable | null = null;
    private _signalsSortableContainer: HTMLElement | null = null;
    private _pendingRemotesSave: number | null = null;
    private _pendingSignalsSave: number | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
        void this._subscribeUpdated();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        void this._unsubscribeUpdated();
        this._removePopoverDismiss();
        this._remotesSortable?.destroy();
        this._remotesSortable = null;
        this._signalsSortable?.destroy();
        this._signalsSortable = null;
        this._signalsSortableContainer = null;
        if (this._pendingRemotesSave !== null) clearTimeout(this._pendingRemotesSave);
        if (this._pendingSignalsSave !== null) clearTimeout(this._pendingSignalsSave);
    }

    protected updated(changed: PropertyValues): void {
        super.updated(changed);
        if (changed.has("_editingDeviceId") && this._editingDeviceId) {
            const input = this.shadowRoot?.querySelector<HTMLInputElement>(".rename-input");
            input?.focus();
            input?.select();
        }
        this._syncSortables();
    }

    /** Attach / detach SortableJS for the remote list and the open
     *  remote's signal list, tracking container swaps so a re-render or
     *  an expand change rebinds cleanly. */
    private _syncSortables(): void {
        const remotes = this.renderRoot.querySelector(".device-list") as HTMLElement | null;
        if (remotes && !this._remotesSortable) {
            this._attachRemotesSortable(remotes);
        } else if (!remotes && this._remotesSortable) {
            this._remotesSortable.destroy();
            this._remotesSortable = null;
        }

        const sig = this.renderRoot.querySelector(".signal-list") as HTMLElement | null;
        const canDrag = !!this._expandedDevice && !this._expandedDevice.dismissed;
        if (sig && canDrag && (!this._signalsSortable || this._signalsSortableContainer !== sig)) {
            this._signalsSortable?.destroy();
            this._attachSignalsSortable(sig);
        } else if ((!sig || !canDrag) && this._signalsSortable) {
            this._signalsSortable.destroy();
            this._signalsSortable = null;
            this._signalsSortableContainer = null;
        }
    }

    private _attachRemotesSortable(container: HTMLElement): void {
        this._remotesSortable = Sortable.create(container, {
            handle: ".remote-grip",
            animation: 150,
            ghostClass: "sortable-ghost",
            onEnd: (e) => {
                const { oldIndex, newIndex } = e;
                if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex) {
                    return;
                }
                const devices = [...this._devices];
                const [moved] = devices.splice(oldIndex, 1);
                devices.splice(newIndex, 0, moved);
                this._devices = devices;
                this._remotesSortable?.destroy();
                this._remotesSortable = null;
                this._purgeChildren(container, "ha-card");
                this._remotesVersion++;
                this._scheduleRemotesSave(devices.map((d) => d.id));
            },
        });
    }

    private _attachSignalsSortable(container: HTMLElement): void {
        if (!this._expandedDevice) return;
        this._signalsSortableContainer = container;
        this._signalsSortable = Sortable.create(container, {
            handle: ".signal-grip",
            animation: 150,
            ghostClass: "sortable-ghost",
            onEnd: (e) => {
                const { oldIndex, newIndex } = e;
                if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex) {
                    return;
                }
                // Read id + signals from the CURRENT expanded device so the
                // device id always matches the signals being sent, even if
                // the user switched remotes after this handler was bound
                // (Lit reuses the .signal-list element across remotes).
                const dev = this._expandedDevice;
                if (!dev) return;
                const signals = [...dev.signals];
                const [moved] = signals.splice(oldIndex, 1);
                signals.splice(newIndex, 0, moved);
                this._expandedDevice = { ...dev, signals };
                this._signalsSortable?.destroy();
                this._signalsSortable = null;
                this._signalsSortableContainer = null;
                this._purgeChildren(container, ".signal-row");
                this._signalsVersion++;
                this._scheduleSignalsSave(dev.id, signals.map((s) => s.id));
            },
        });
    }

    /** Remove leftover children SortableJS may have left outside keyed()'s
     *  managed range, so the rebuild starts from a clean container. */
    private _purgeChildren(container: HTMLElement, selector: string): void {
        for (const el of Array.from(container.querySelectorAll(selector))) {
            el.remove();
        }
    }

    private _scheduleRemotesSave(deviceIds: string[]): void {
        if (this._pendingRemotesSave !== null) clearTimeout(this._pendingRemotesSave);
        this._pendingRemotesSave = window.setTimeout(async () => {
            this._pendingRemotesSave = null;
            try {
                await this.api.reorderUnknownDevices("manual", deviceIds);
            } catch (err) {
                this._error = `Reorder failed: ${(err as Error).message}`;
                await this._load();
            }
        }, REORDER_DEBOUNCE_MS);
    }

    private _scheduleSignalsSave(deviceId: string, signalIds: string[]): void {
        if (this._pendingSignalsSave !== null) clearTimeout(this._pendingSignalsSave);
        this._pendingSignalsSave = window.setTimeout(async () => {
            this._pendingSignalsSave = null;
            try {
                await this.api.reorderUnknownSignals(deviceId, signalIds);
            } catch (err) {
                this._error = `Reorder failed: ${(err as Error).message}`;
                await this._refreshExpanded();
            }
        }, REORDER_DEBOUNCE_MS);
    }

    private async _load(): Promise<void> {
        this._loading = true;
        try {
            const [unknowns, hairDevs, triggers] = await Promise.all([
                this.api.getUnknownDevices({
                    include_dismissed: true,
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
            this.api
                .listReceivers()
                .then((r) => {
                    this._receivers = r;
                })
                .catch(() => {
                    this._receivers = [];
                });
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

    /** Public so the panel's tab-bar "+ Create" button can open it. */
    openCreateRemote(): void {
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

    private _openEditSignal(
        deviceId: string,
        sig: UnknownSignal,
        e: Event,
    ): void {
        e.stopPropagation();
        this._editSignal = { deviceId, signal: sig };
    }

    private async _onSignalEdited(): Promise<void> {
        this._editSignal = null;
        await this._refreshExpanded();
        await this._load();
    }

    private _openDeleteRemote(device: UnknownDevice): void {
        this._deleteRemoteId = device.id;
        this._deleteRemoteLabel = device.label || "this remote";
        this._deleteRemoteCount = device.signals.length;
    }

    private async _confirmDeleteRemote(): Promise<void> {
        const id = this._deleteRemoteId;
        this._deleteRemoteId = null;
        if (!id) return;
        try {
            await this.api.deleteRemote(id);
            if (this._expandedId === id) {
                this._expandedId = null;
                this._expandedDevice = null;
            }
            await this._load();
        } catch (err) {
            this._error = `Delete failed: ${(err as Error).message}`;
        }
    }

    // --- Signal alias (delegated to ir-signal-alias) ---

    private _onAliasChanged(
        e: CustomEvent<{ id: string; alias: string }>,
    ): void {
        const { id, alias } = e.detail;
        if (!this._expandedDevice) return;
        this._expandedDevice = {
            ...this._expandedDevice,
            signals: this._expandedDevice.signals.map((s) =>
                s.id === id ? { ...s, alias } : s,
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

    /** Assign-button click router (v0.6.6, mirrors the Trigger flow):
     * zero assignments opens the Assign dialog directly; 1+ shows the
     * assigned popover with "+ new assignment" and click-through rows. */
    private _onAssignClick(
        deviceId: string,
        signal: UnknownSignal,
        label: string | null | undefined,
        ev?: Event,
    ): void {
        if (!signal.assigned_to?.length) {
            this._openAssign(deviceId, signal, label);
            return;
        }
        const btn = ev?.currentTarget as HTMLElement | undefined;
        const rect = btn?.getBoundingClientRect();
        this._assignedPopover = {
            deviceId,
            signal,
            label: label ?? null,
            top: rect ? rect.bottom + 4 : 120,
            left: rect ? Math.max(8, rect.right - 220) : 120,
        };
        this._installPopoverDismiss();
    }

    private _closeAssignedPopover(): void {
        this._assignedPopover = null;
        this._removePopoverDismiss();
    }

    private _onAssignedPopoverCreateNew(): void {
        const p = this._assignedPopover;
        this._closeAssignedPopover();
        if (p) this._openAssign(p.deviceId, p.signal, p.label);
    }

    private _onAssignedPopoverOpen(ev: CustomEvent): void {
        const a = ev.detail as SignalAssignment | undefined;
        this._closeAssignedPopover();
        if (!a) return;
        this.dispatchEvent(
            new CustomEvent("navigate-device", {
                detail: a.device_id,
                bubbles: true,
                composed: true,
            }),
        );
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
            await this.api.deleteSignal(deviceId, signal.id);
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
        this._testingSignalId = signal.id;
        this._testResult = null;
        this._testDialog = null;
        try {
            const results = await Promise.allSettled(
                emitters.map((eid) => this.api.testSignal(signal.id, eid)),
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
            this._testingSignalId = null;
        }, 3000);
    }

    /** Identity-aware trigger matching (v0.5.8): fingerprint + byte_hash. */
    private _hasTrigger(signal: UnknownSignal): boolean {
        return this._triggers.some((t) => triggerMatchesSignal(t, signal));
    }

    private _triggerCountFor(signal: UnknownSignal): number {
        return this._triggers.filter((t) => triggerMatchesSignal(t, signal))
            .length;
    }

    private _openTriggerDialog(
        deviceId: string,
        signal: UnknownSignal,
        ev?: Event,
    ): void {
        const matches = this._triggers.filter((t) =>
            triggerMatchesSignal(t, signal),
        );
        if (matches.length === 0) {
            this._triggerDialog = { signal, deviceId };
            return;
        }
        const btn = ev?.currentTarget as HTMLElement | undefined;
        const rect = btn?.getBoundingClientRect();
        this._triggerPopover = {
            deviceId,
            signal,
            top: rect ? rect.bottom + 4 : 120,
            left: rect ? Math.max(8, rect.right - 220) : 120,
        };
        this._installPopoverDismiss();
    }

    private _closeTriggerPopover(): void {
        this._triggerPopover = null;
        this._removePopoverDismiss();
    }

    private _onPopoverCreateNew(): void {
        const p = this._triggerPopover;
        this._closeTriggerPopover();
        if (p) this._triggerDialog = { signal: p.signal, deviceId: p.deviceId };
    }

    private _onPopoverEditTrigger(ev: CustomEvent): void {
        const t = ev.detail as IRTrigger | undefined;
        this._closeTriggerPopover();
        if (t) this._triggerEditDialog = t;
    }

    private _onDocClickForPopover = (ev: Event): void => {
        const path = ev.composedPath();
        const trig = this.shadowRoot?.querySelector("ir-trigger-popover");
        const asgn = this.shadowRoot?.querySelector("ir-assigned-popover");
        if ((trig && path.includes(trig)) || (asgn && path.includes(asgn))) {
            return;
        }
        this._closeTriggerPopover();
        this._closeAssignedPopover();
    };

    private _onScrollForPopover = (): void => {
        this._closeTriggerPopover();
        this._closeAssignedPopover();
    };

    private _installPopoverDismiss(): void {
        setTimeout(() => {
            document.addEventListener("click", this._onDocClickForPopover, true);
            window.addEventListener("scroll", this._onScrollForPopover, true);
        }, 0);
    }

    private _removePopoverDismiss(): void {
        document.removeEventListener("click", this._onDocClickForPopover, true);
        window.removeEventListener("scroll", this._onScrollForPopover, true);
    }

    private async _subscribeUpdated(): Promise<void> {
        try {
            this._unsubUpdated = await this.api.subscribeSignalUpdated(() => {
                void this._refreshAfterSignalUpdate();
            });
        } catch {
            // Non-fatal.
        }
    }

    private async _unsubscribeUpdated(): Promise<void> {
        if (this._unsubUpdated) {
            await this._unsubUpdated();
            this._unsubUpdated = null;
        }
    }

    private async _refreshAfterSignalUpdate(): Promise<void> {
        try {
            this._triggers = await this.api.listTriggers();
        } catch {
            // Non-fatal.
        }
        if (this._expandedId) {
            try {
                this._expandedDevice = await this.api.getUnknownDevice(
                    this._expandedId,
                );
            } catch {
                // Non-fatal.
            }
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


    // --- Render ---

    render() {
        const count = this._devices.length;
        return html`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${ICON_CLIPPER}></ha-svg-icon>
                    HAIR Clipper
                    ${!this._loading
                        ? html`<span class="count"
                              >(${count} ${count === 1 ? "remote" : "remotes"})</span
                          >`
                        : ""}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn create-btn"
                        @click=${() => (this._createRemoteOpen = true)}
                    >
                        + Add Remote
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
                            <ha-svg-icon class="empty-icon" .path=${ICON_CLIPPER}></ha-svg-icon>
                            <h3>No virtual remotes yet</h3>
                            <p>
                                Clipper lets you build remotes by pasting Pronto codes.
                                Create a remote, then add a signal for each button.
                            </p>
                            <p class="hint">
                                Click "+ Add Remote" above to start a clipped remote.
                            </p>
                        </ha-card>
                    `
                  : html`
                        <div class="device-list">
                            ${keyed(
                                this._remotesVersion,
                                repeat(
                                    this._devices,
                                    (d) => d.id,
                                    (d) => this._renderDevice(d),
                                ),
                            )}
                        </div>
                    `}

            ${count > 0
                ? html`
                      <div class="clear-all-row">
                          <button
                              class="action-btn delete-btn"
                              title="Delete all clipped remotes and their signals. Sniffed signals are untouched."
                              @click=${() => (this._confirmClearAll = true)}
                          >
                              Clear All
                          </button>
                      </div>
                  `
                : ""}

            ${this._renderDialogs()}
        `;
    }

    private _renderDevice(d: UnknownDeviceSummary) {
        const expanded = this._expandedId === d.id;
        return html`
            <ha-card class="device clip-device">
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
                                : html`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${ICON_GRIP}
                                          title="Drag to reorder"
                                          @click=${(e: Event) => e.stopPropagation()}
                                      ></ha-svg-icon>
                                      <span
                                          class="protocol"
                                          title="Click to rename"
                                          @click=${(e: Event) => this._startRename(d, e)}
                                          >${d.label ?? "Remote"}</span
                                      >`}
                            <span class="stat"
                                ><strong>${d.signal_count}</strong>
                                ${d.signal_count === 1 ? "signal" : "signals"}</span
                            >
                            ${d.label && this._matchesHairDevice(d.label)
                                ? html`<span
                                      class="status-badge hair-device"
                                      @click=${(e: Event) => e.stopPropagation()}
                                  >HAIR Device</span>`
                                : d.label
                                    ? html`<span
                                          class="status-badge promote-badge"
                                          @click=${(e: Event) => this._promoteDevice(d, e)}
                                      >Promote</span>`
                                    : ""}
                        </div>
                    </div>
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
                        class="create-signal-btn"
                        title="Add a signal to this remote"
                        @click=${(e: Event) => this._openCreateSignal(device.id, e)}
                    >
                        + Add Signal
                    </button>
                </div>
                ${device.signals.length === 0
                    ? html`<div class="no-signals-row">
                          <span class="no-signals"
                              >No signals yet. Click "+ Add Signal" to paste a
                              Pronto code.</span
                          >
                      </div>`
                    : html`
                          <div class="signal-list">
                              ${keyed(
                                  this._signalsVersion,
                                  repeat(
                                      device.signals,
                                      (sig) => sig.id,
                                      (sig) =>
                                          this._renderSignal(
                                              device.id,
                                              sig,
                                              device.label,
                                          ),
                                  ),
                              )}
                          </div>
                      `}
                <div class="remote-footer">
                    <button
                        class="action-btn delete-btn"
                        title="Delete this remote and all its signals"
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openDeleteRemote(device);
                        }}
                    >Delete remote</button>
                </div>
            </div>
        `;
    }

    private _renderSignal(
        deviceId: string,
        sig: UnknownSignal,
        label: string | null,
    ) {
        const isTesting = this._testingSignalId === sig.id;
        return html`
            <div class="signal-row">
                <ha-svg-icon
                    class="signal-grip"
                    .path=${ICON_GRIP}
                    title="Drag to reorder"
                ></ha-svg-icon>
                <div class="signal-info">
                    <ir-signal-alias
                        .api=${this.api}
                        .deviceId=${deviceId}
                        .signal=${sig}
                        @alias-changed=${this._onAliasChanged}
                        @alias-error=${(e: CustomEvent) => (this._error = e.detail)}
                    ></ir-signal-alias>
                </div>
                <div class="signal-meta">
                    ${isTesting && this._testResult
                        ? html`<span class="test-result">${this._testResult}</span>`
                        : html`<span>${Math.round(sig.frequency / 1000)} kHz</span>`}
                </div>
                ${sig.code
                    ? html`<button
                          title="View or edit code"
                          @click=${(e: Event) =>
                              this._openEditSignal(deviceId, sig, e)}
                          style="background:none;border:none;cursor:pointer;color:var(--secondary-text-color);padding:2px;display:inline-flex;align-items:center"
                      >
                          <ha-svg-icon
                              .path=${ICON_COPY}
                              style="--mdc-icon-size:10px"
                          ></ha-svg-icon>
                      </button>`
                    : ""}
                <div class="signal-actions">
                    <button
                        class="action-btn assign-btn"
                        title=${sig.assignment_count && sig.assigned_to?.length
                            ? (sig.assignment_count === 1
                                ? `Assigned to ${sig.assigned_to[0].device_name} / ${sig.assigned_to[0].command_name}`
                                : `Assigned to ${sig.assignment_count} commands:\n- ${sig.assigned_to.map((a) => `${a.device_name} / ${a.command_name}`).join("\n- ")}`)
                            : "Assign this signal to a HAIR device"}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._onAssignClick(deviceId, sig, label, e);
                        }}
                    >Assign<ir-count-dot
                            color="green"
                            .count=${sig.assignment_count ?? 0}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${isTesting}
                        title="Send this signal through an emitter"
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openTestDialog(sig);
                        }}
                    >${isTesting ? "Sending..." : "Test"}</button>
                    <button
                        class="action-btn trigger-btn"
                        title=${this._hasTrigger(sig)
                            ? "Edit trigger(s) for this signal"
                            : "Create an HA event entity that fires on this signal"}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openTriggerDialog(deviceId, sig, e);
                        }}
                    >Trigger<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(sig)}
                        ></ir-count-dot></button>
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
                ? html`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._createSignalDeviceId}
                      @signal-created=${this._onSignalCreated}
                      @closed=${() => (this._createSignalDeviceId = null)}
                  ></ir-signal-editor>`
                : ""}

            ${this._editSignal
                ? html`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._editSignal.deviceId}
                      .signalId=${this._editSignal.signal.id}
                      .initialPronto=${this._editSignal.signal.code ?? ""}
                      .initialAlias=${this._editSignal.signal.alias ?? ""}
                      .initialSendCount=${this._editSignal.signal.send_count ?? 1}
                      .initialDitto=${this._editSignal.signal.repeat_count ?? 1}
                      .initialObservedRepeatCount=${this._editSignal.signal
                          .observed_repeat_count ?? 0}
                      .hasTrigger=${this._hasTrigger(this._editSignal.signal)}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${() => (this._editSignal = null)}
                  ></ir-signal-editor>`
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

            ${this._deleteRemoteId
                ? html`<ir-confirm-dialog
                      title="Delete Remote"
                      message=${this._deleteRemoteCount > 0
                          ? `Remove "${this._deleteRemoteLabel}" and its ${this._deleteRemoteCount} ${this._deleteRemoteCount === 1 ? "signal" : "signals"}? This cannot be undone.`
                          : `Remove "${this._deleteRemoteLabel}"? This cannot be undone.`}
                      confirmLabel="Delete"
                      .destructive=${true}
                      @confirmed=${this._confirmDeleteRemote}
                      @closed=${() => (this._deleteRemoteId = null)}
                  ></ir-confirm-dialog>`
                : ""}

            ${this._triggerPopover
                ? html`<ir-trigger-popover
                      .triggers=${this._triggers.filter((t) =>
                          triggerMatchesSignal(t, this._triggerPopover!.signal),
                      )}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`
                : ""}

            ${this._assignedPopover
                ? html`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to ?? []}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`
                : ""}

            ${this._triggerDialog
                ? html`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                      .byteHash=${this._triggerDialog.signal.byte_hash ?? null}
                      .decodedFingerprint=${this._triggerDialog.signal.decoded_fingerprint ?? null}
                      .protocol=${this._triggerDialog.signal.protocol}
                      .code=${this._triggerDialog.signal.code}
                      .slPattern=${this._triggerDialog.signal.sl_pattern ?? null}
                      .alias=${this._triggerDialog.signal.alias || null}
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

    static styles = [actionChipStyles, css`
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
        /* Toolbar "+ Add Remote": shared chip anatomy, copper accent. */
        .action-btn.create-btn {
            color: #b87333;
            border-color: #b87333;
        }
        .action-btn.create-btn:hover:not(:disabled) {
            background: rgba(184, 115, 51, 0.08);
        }
        /* Card-internal "+ Add Signal": borderless copper text action
           (no chip, no stroke -- owner ruling), one pixel up from its
           old size, font color matching the Add Remote accent. */
        .create-signal-btn {
            border: none;
            background: none;
            padding: 0;
            font-size: 11px;
            font-weight: 500;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #b87333;
            cursor: pointer;
            position: relative;
            top: 1px;
        }
        .create-signal-btn:hover:not(:disabled) {
            background: none;
            text-decoration: underline;
        }

        .clear-all-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 16px;
        }
        /* Show Dismissed stacked above Clear All, both right-aligned. */
        .bottom-bar {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
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
            border: 1px solid rgba(184, 115, 51, 0.3);
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
        /* Remote drag handle (replaces the paperclip): copper, matches tab. */
        .remote-grip {
            --mdc-icon-size: 18px;
            color: #b87333;
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.85;
            transition: opacity 120ms ease;
        }
        .remote-grip:hover {
            opacity: 1;
        }
        .remote-grip:active {
            cursor: grabbing;
        }
        /* Signal drag handle: gray, same as the hits / time / frequency meta. */
        .signal-grip {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.6;
            transition: opacity 120ms ease;
        }
        .signal-grip:hover {
            opacity: 1;
        }
        .signal-grip:active {
            cursor: grabbing;
        }
        /* SortableJS marks the element being dragged. */
        ha-card.sortable-ghost,
        .signal-row.sortable-ghost {
            opacity: 0.4;
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
        .no-signals-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            padding: 6px 8px;
        }
        .no-signals {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        /* Persistent "Delete remote" footer: a row below the signal list,
           right-justified so its button lines up with the per-signal Delete
           buttons (which sit 8px in from the row edge). Same button size as
           every other action button. */
        .remote-footer {
            display: flex;
            justify-content: flex-end;
            margin-top: 10px;
            padding-right: 8px;
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
    `];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-clips": IrClips;
    }
}
