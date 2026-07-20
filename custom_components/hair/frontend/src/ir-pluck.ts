/**
 * Plucker tab -- pull IR codes off existing vendor blasters into HAIR.
 *
 * Mirrors the Clipper (ir-clips) card + dialog structure. Each card is a
 * plucked blaster (one vendor entity + one appliance), holding plucked
 * signals. "+ Pluck Signal" fires the vendor send service at the HAIR
 * Tweezer and captures the code. Reuses the shared Assign / Trigger / Test /
 * Confirm dialogs and the inline alias editor. Slate accent (#455a64).
 *
 * Plucked blasters are never dismissed or evicted; the refresh model is
 * delete-and-recreate, so there is no Show Dismissed / Promote machinery.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { actionChipStyles } from "./ir-action-chip-styles";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { keyed } from "lit/directives/keyed.js";
import { repeat } from "lit/directives/repeat.js";
import Sortable from "sortablejs";
import { HairApi } from "./api.js";
import "./ir-assign-signal-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-save-wig-dialog.js";
import "./ir-pluck-add-remote-dialog.js";
import "./ir-pluck-signal-dialog.js";
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
    PluckVendor,
    ReceiverInfo,
    SignalAssignment,
    UnknownDevice,
    UnknownDeviceSummary,
    UnknownSignal,
} from "./types.js";

// Tweezers (SVG Repo, scaled to a 24x24 box), the Plucker / HAIR Tweezer motif.
const ICON_PLUCK =
    "M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z";
const ICON_EXPAND = "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";
const ICON_COLLAPSE = "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z";
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";
const ICON_GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";

const REORDER_DEBOUNCE_MS = 500;

@customElement("ir-pluck")
export class IrPluck extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;
    @property() public pendingEntity = "";

    @state() private _devices: UnknownDeviceSummary[] = [];
    @state() private _hairDevices: DeviceSummary[] = [];
    @state() private _triggers: IRTrigger[] = [];
    @state() private _loading = true;
    @state() private _saveWigDevice: UnknownDevice | null = null;
    @state() private _error: string | null = null;
    @state() private _expandedId: string | null = null;
    @state() private _expandedDevice: UnknownDevice | null = null;
    @state() private _confirmClearAll = false;
    @state() private _deleteRemoteId: string | null = null;
    @state() private _deleteRemoteLabel = "";
    @state() private _deleteRemoteCount = 0;

    // entity_id -> integration domain, from the discovery list.
    private _vendorIntegration: Record<string, string> = {};

    // Inline rename
    @state() private _editingDeviceId: string | null = null;
    @state() private _editLabel = "";

    // Dialog state
    @state() private _createRemoteOpen = false;
    @state() private _promoteTarget: UnknownDeviceSummary | null = null;
    @state() private _linkedPopoverId: string | null = null;
    private _linkedPopoverPos = { top: 0, left: 0 };
    @state() private _pluckDialog: { device: UnknownDevice; integration: string } | null =
        null;
    @state() private _editSignal: { deviceId: string; signal: UnknownSignal } | null =
        null;
    @state() private _assignSignal: {
        deviceId: string;
        signal: UnknownSignal;
        label: string | null;
    } | null = null;
    @state() private _deleteSignal: { deviceId: string; signal: UnknownSignal } | null =
        null;
    @state() private _triggerDialog: { signal: UnknownSignal; deviceId: string } | null =
        null;
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

    // Drag-to-reorder
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

    private _syncSortables(): void {
        const remotes = this.renderRoot.querySelector(".device-list") as HTMLElement | null;
        if (remotes && !this._remotesSortable) {
            this._attachRemotesSortable(remotes);
        } else if (!remotes && this._remotesSortable) {
            this._remotesSortable.destroy();
            this._remotesSortable = null;
        }

        const sig = this.renderRoot.querySelector(".signal-list") as HTMLElement | null;
        const canDrag = !!this._expandedDevice;
        if (
            sig &&
            canDrag &&
            (!this._signalsSortable || this._signalsSortableContainer !== sig)
        ) {
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
                if (
                    oldIndex === undefined ||
                    newIndex === undefined ||
                    oldIndex === newIndex
                ) {
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
                if (
                    oldIndex === undefined ||
                    newIndex === undefined ||
                    oldIndex === newIndex
                ) {
                    return;
                }
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
                this._scheduleSignalsSave(
                    dev.id,
                    signals.map((s) => s.id),
                );
            },
        });
    }

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
                await this.api.reorderUnknownDevices("plucked", deviceIds);
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
            const [unknowns, hairDevs, triggers, vendors] = await Promise.all([
                this.api.getUnknownDevices({
                    include_dismissed: false,
                    min_hits: 0,
                    source: "plucked",
                }),
                this.api.listDevices(),
                this.api.listTriggers(),
                this.api.listPluckVendors().catch(() => ({ vendors: [] })),
            ]);
            this._devices = unknowns;
            this._hairDevices = hairDevs;
            this._triggers = triggers;
            this._vendorIntegration = this._mapIntegrations(vendors.vendors);
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

    private _mapIntegrations(vendors: PluckVendor[]): Record<string, string> {
        const map: Record<string, string> = {};
        for (const v of vendors) {
            for (const b of v.blasters) {
                map[b.entity_id] = v.integration;
            }
        }
        return map;
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

    // --- Add Remote / Pluck Signal ---

    /** Public so the panel's tab-bar "+ Add Remote" button can open it. */
    openCreateRemote(): void {
        this._createRemoteOpen = true;
    }

    private async _onBlasterCreated(e: CustomEvent<UnknownDevice>): Promise<void> {
        this._createRemoteOpen = false;
        this.pendingEntity = "";
        await this._load();
        this._expandedId = e.detail.id;
        await this._refreshExpanded();
    }

    private _openPluckSignal(device: UnknownDevice, e: Event): void {
        e.stopPropagation();
        const integration = device.vendor_entity_id
            ? (this._vendorIntegration[device.vendor_entity_id] ?? "")
            : "";
        if (!integration) {
            this._error =
                t("pluck.vendor_unavailable");
            return;
        }
        this._pluckDialog = { device, integration };
    }

    private async _onSignalsCreated(): Promise<void> {
        this._pluckDialog = null;
        await this._refreshExpanded();
        await this._load();
    }

    private _openEditSignal(deviceId: string, sig: UnknownSignal, e: Event): void {
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
        this._deleteRemoteLabel = device.label || "this blaster";
        this._deleteRemoteCount = device.signals.length;
    }

    private async _confirmDeleteRemote(): Promise<void> {
        const id = this._deleteRemoteId;
        this._deleteRemoteId = null;
        if (!id) return;
        try {
            await this.api.deletePluckedBlaster(id);
            if (this._expandedId === id) {
                this._expandedId = null;
                this._expandedDevice = null;
            }
            await this._load();
        } catch (err) {
            this._error = `Delete failed: ${(err as Error).message}`;
        }
    }

    private async _doClearAll(): Promise<void> {
        this._confirmClearAll = false;
        try {
            await this.api.clearUnknowns("plucked");
            this._devices = [];
            this._expandedId = null;
            this._expandedDevice = null;
        } catch (err) {
            this._error = `Clear failed: ${(err as Error).message}`;
        }
    }

    // --- Alias / rename ---

    private _onAliasChanged(e: CustomEvent<{ id: string; alias: string }>): void {
        const { id, alias } = e.detail;
        if (!this._expandedDevice) return;
        this._expandedDevice = {
            ...this._expandedDevice,
            signals: this._expandedDevice.signals.map((s) =>
                s.id === id ? { ...s, alias } : s,
            ),
        };
    }

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

    // --- Assign / Delete / Test / Trigger (reuse shared dialogs) ---

    private _openAssign(
        deviceId: string,
        signal: UnknownSignal,
        label?: string | null,
    ): void {
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

    /**
     * Linked-devices chip (v0.7.0), identical to the Sniffer's and
     * Clipper's: count form, dropdown always, fixed-position popover.
     */
    private _renderLinkedChip(d: UnknownDeviceSummary) {
        const linked = d.linked_devices ?? [];
        if (linked.length === 0) return "";
        return html`<span
            class="status-badge hair-device"
            @click=${(e: Event) => this._toggleLinkedPopover(d.id, e)}
        >${tp("sniffer.linked", linked.length)}</span>`;
    }

    private _toggleLinkedPopover(deviceId: string, e: Event): void {
        e.stopPropagation();
        if (this._linkedPopoverId === deviceId) {
            this._linkedPopoverId = null;
            return;
        }
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        this._linkedPopoverPos = {
            top: rect.bottom + 6,
            left: rect.left,
        };
        this._linkedPopoverId = deviceId;
    }

    private _renderLinkedPopover() {
        if (!this._linkedPopoverId) return "";
        const d = this._devices.find(
            (dev) => dev.id === this._linkedPopoverId,
        );
        const linked = d?.linked_devices ?? [];
        if (!d || linked.length === 0) return "";
        return html`<div
                class="linked-scrim"
                @click=${() => (this._linkedPopoverId = null)}
            ></div>
            <div
                class="linked-popover"
                style="top: ${this._linkedPopoverPos.top}px; left: ${this
                    ._linkedPopoverPos.left}px;"
            >
                ${linked.map(
                    (entry) => html`<button
                        class="linked-entry"
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._linkedPopoverId = null;
                            this._navigateToDevice(entry.device_id);
                        }}
                    >${entry.device_name}</button>`,
                )}
            </div>`;
    }

    private _navigateToDevice(deviceId: string): void {
        this.dispatchEvent(
            new CustomEvent("navigate-device", {
                detail: deviceId,
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _promoteDevice(d: UnknownDeviceSummary, e: Event): void {
        e.stopPropagation();
        this._promoteTarget = d;
    }

    private async _onDevicePromoted(): Promise<void> {
        this._promoteTarget = null;
        await this._load();
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
                this._testResult = total === 1 ? t("mirror.sent") : t("mirror.sent_all_n", { sent, total });
            } else if (sent === 0) {
                this._testResult = t("mirror.failed");
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

    private async _toggleExpand(deviceId: string): Promise<void> {
        if (this._expandedId === deviceId) {
            this._expandedId = null;
            this._expandedDevice = null;
            return;
        }
        this._expandedId = deviceId;
        await this._refreshExpanded();
    }

    // --- Render ---

    render() {
        const count = this._devices.length;
        return html`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${ICON_PLUCK}></ha-svg-icon>
                    ${t("pluck.title")}
                    ${!this._loading
                        ? html`<span class="count"
                              >(${count} ${count === 1 ? "blaster" : "blasters"})</span
                          >`
                        : ""}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn create-btn"
                        @click=${() => (this._createRemoteOpen = true)}
                    >
                        ${t("pluck.add_blaster")}
                    </button>
                </div>
            </div>

            ${this._error
                ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                : ""}

            ${this._loading
                ? html`<div class="loading">${t("common.loading_plain")}</div>`
                : count === 0
                  ? html`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ICON_PLUCK}></ha-svg-icon>
                            <h3>${t("pluck.empty_title")}</h3>
                            <p>${t("pluck.empty_body")}</p>
                            <p class="hint">${t("pluck.empty_hint")}</p>
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
                              title=${t("pluck.clear_all_title")}
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
            <ha-card class="device pluck-device">
                <div class="device-row" @click=${() => this._toggleExpand(d.id)}>
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId === d.id
                                ? html`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${(e: Event) => {
                                          this._editLabel = (
                                              e.target as HTMLInputElement
                                          ).value;
                                      }}
                                      @keydown=${(e: KeyboardEvent) =>
                                          this._onRenameKeydown(d.id, e)}
                                      @blur=${() => void this._commitRename(d.id)}
                                      @click=${(e: Event) => e.stopPropagation()}
                                  />`
                                : html`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${ICON_GRIP}
                                          title=${t("devdetail.drag")}
                                          @click=${(e: Event) => e.stopPropagation()}
                                      ></ha-svg-icon>
                                      <span
                                          class="protocol"
                                          title=${t("cmdrow.rename")}
                                          @click=${(e: Event) => this._startRename(d, e)}
                                          >${d.label ?? t("pluck.blaster_fallback")}</span
                                      >`}
                            ${d.appliance
                                ? html`<span
                                      class="appliance-badge"
                                      @click=${(e: Event) => e.stopPropagation()}
                                      >${d.appliance}</span
                                  >`
                                : ""}
                            <span class="stat"
                                ><strong>${d.signal_count}</strong>
                                ${d.signal_count === 1 ? "signal" : "signals"}</span
                            >
                            ${d.label
                                ? html`<span
                                      class="status-badge promote-badge"
                                      title=${t("pluck.promote_title")}
                                      @click=${(e: Event) => this._promoteDevice(d, e)}
                                      >${t("sniffer.promote")}</span
                                  >`
                                : ""}
                            ${this._renderLinkedChip(d)}
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
                    <span>${t("sniffer.signals_head", { count: device.signals.length })}</span>
                    <button
                        class="create-signal-btn"
                        title=${t("pluck.pluck_signal_title")}
                        @click=${(e: Event) => this._openPluckSignal(device, e)}
                    >
                        ${t("pluck.pluck_signal")}
                    </button>
                </div>
                ${device.signals.length === 0
                    ? html`<div class="no-signals-row">
                          <span class="no-signals"
                              >${t("pluck.no_signals")}</span
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
                                          this._renderSignal(device.id, sig, device.label),
                                  ),
                              )}
                          </div>
                      `}
                <div class="remote-footer">
                    <button
                        class="action-btn save-wig-btn"
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._saveWigDevice = device;
                        }}
                    >${t("wigs.save_as_wig")}</button>
                    <button
                        class="action-btn delete-btn"
                        title=${t("pluck.delete_blaster_title")}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openDeleteRemote(device);
                        }}
                    >
                        ${t("pluck.delete_blaster")}
                    </button>
                </div>
            </div>
        `;
    }

    private _renderSignal(deviceId: string, sig: UnknownSignal, label: string | null) {
        const isTesting = this._testingSignalId === sig.id;
        return html`
            <div class="signal-row">
                <ha-svg-icon
                    class="signal-grip"
                    .path=${ICON_GRIP}
                    title=${t("devdetail.drag")}
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
                          title=${t("cmdrow.edit_code")}
                          @click=${(e: Event) => this._openEditSignal(deviceId, sig, e)}
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
                            : t("mirror.assign_title")}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._onAssignClick(deviceId, sig, label, e);
                        }}
                    >
                        ${t("assign.assign")}<ir-count-dot
                            color="green"
                            .count=${sig.assignment_count ?? 0}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${isTesting}
                        title=${t("clips.test_title")}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openTestDialog(sig);
                        }}
                    >
                        ${isTesting ? (this._testResult ?? t("mirror.sending")) : t("mirror.test")}
                    </button>
                    <button
                        class="action-btn trigger-btn"
                        title=${this._hasTrigger(sig)
                            ? t("mirror.trigger_edit")
                            : t("sniffer.trigger_create")}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openTriggerDialog(deviceId, sig, e);
                        }}
                    >
                        ${t("cmdrow.trigger")}<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(sig)}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn delete-btn"
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openDelete(deviceId, sig);
                        }}
                    >
                        ${t("common.delete")}
                    </button>
                </div>
            </div>
        `;
    }

    private _renderDialogs() {
        return html`
            ${this._createRemoteOpen
                ? html`<ir-pluck-add-remote-dialog
                      .api=${this.api}
                      .pendingEntity=${this.pendingEntity}
                      @blaster-created=${this._onBlasterCreated}
                      @closed=${() => {
                          this._createRemoteOpen = false;
                          this.pendingEntity = "";
                      }}
                  ></ir-pluck-add-remote-dialog>`
                : ""}

            ${this._promoteTarget
                ? html`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._promoteTarget.label ?? ""}
                      .sourceUnknownId=${this._promoteTarget.id}
                      @device-created=${this._onDevicePromoted}
                      @closed=${() => (this._promoteTarget = null)}
                  ></ir-promote-dialog>`
                : ""}

            ${this._pluckDialog
                ? html`<ir-pluck-signal-dialog
                      .api=${this.api}
                      .blaster=${this._pluckDialog.device}
                      .integration=${this._pluckDialog.integration}
                      @signals-created=${this._onSignalsCreated}
                      @closed=${() => (this._pluckDialog = null)}
                  ></ir-pluck-signal-dialog>`
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

            ${this._deleteSignal
                ? html`<ir-confirm-dialog
                      title=${t("sniffer.del_signal_title")}
                      message=${t("sniffer.del_signal_msg")}
                      confirmLabel="Delete"
                      .destructive=${true}
                      @confirmed=${this._confirmDelete}
                      @closed=${() => (this._deleteSignal = null)}
                  ></ir-confirm-dialog>`
                : ""}

            ${this._confirmClearAll
                ? html`<ir-confirm-dialog
                      title=${t("pluck.clear_all_confirm_title")}
                      message=${t("pluck.clear_all_confirm_msg")}
                      confirmLabel="Clear All"
                      .destructive=${true}
                      @confirmed=${this._doClearAll}
                      @closed=${() => (this._confirmClearAll = false)}
                  ></ir-confirm-dialog>`
                : ""}

            ${this._deleteRemoteId
                ? html`<ir-confirm-dialog
                      title=${t("pluck.del_blaster_confirm_title")}
                      message=${this._deleteRemoteCount > 0
                          ? tp("clips.del_remote_msg_n", this._deleteRemoteCount, { name: this._deleteRemoteLabel ?? "" })
                          : t("clips.del_remote_msg", { name: this._deleteRemoteLabel ?? "" })}
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
                      title=${t("mirror.del_trigger_title")}
                      message=${t("devdetail.del_trigger_msg")}
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
            ${this._renderLinkedPopover()}
            ${this._saveWigDevice
                ? html`<ir-save-wig-dialog
                      .api=${this.api}
                      source="catalog"
                      sourceId=${this._saveWigDevice.id}
                      sourceName=${this._saveWigDevice.label ?? ""}
                      @closed=${() => (this._saveWigDevice = null)}
                  ></ir-save-wig-dialog>`
                : ""}
        `;
    }

    static styles = [actionChipStyles, css`
        .linked-scrim {
            position: fixed;
            inset: 0;
            z-index: 39;
        }
        .linked-popover {
            position: fixed;
            z-index: 40;
            min-width: 160px;
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
            padding: 4px;
            display: flex;
            flex-direction: column;
        }
        .linked-entry {
            background: none;
            border: none;
            text-align: left;
            padding: 7px 10px;
            font-size: 12.5px;
            color: var(--primary-text-color);
            cursor: pointer;
            border-radius: 6px;
        }
        .linked-entry:hover {
            background: rgba(255, 255, 255, 0.06);
        }

        .save-wig-btn {
            color: #8e3b3b;
            border-color: #8e3b3b;
            margin-right: auto;
            margin-left: 8px;
        }
        .save-wig-btn:hover:not(:disabled) {
            background: rgba(142, 59, 59, 0.12);
        }

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
        .toolbar-actions {
            display: flex;
            align-items: center;
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
            color: #455a64;
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        /* Toolbar "+ Add Blaster": shared chip anatomy, slate accent. */
        .action-btn.create-btn {
            color: #78909c;
            border-color: #78909c;
        }
        .action-btn.create-btn:hover:not(:disabled) {
            background: rgba(120, 144, 156, 0.12);
        }
        /* Card-internal "+ Pluck Signal": borderless slate text action
           (no chip, no stroke -- owner ruling), one pixel up from its
           old size, font color matching the Add Blaster accent. */
        .create-signal-btn {
            border: none;
            background: none;
            padding: 0;
            font-size: 10px;
            font-weight: 500;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #78909c;
            cursor: pointer;
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
        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: #455a64;
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
        .device.pluck-device {
            border: 1px solid rgba(69, 90, 100, 0.3);
            overflow: hidden;
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
        .remote-grip {
            --mdc-icon-size: 18px;
            color: #455a64;
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
        .protocol:hover {
            border-bottom-color: #455a64;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid #455a64;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 160px;
        }
        .appliance-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            letter-spacing: 0.02em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(69, 90, 100, 0.15);
            color: #455a64;
            border: 1px solid rgba(69, 90, 100, 0.35);
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
        .stat {
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
        "ir-pluck": IrPluck;
    }
}
