/**
 * Signal Monitor tab -- shows unknown IR devices detected by the
 * always-on SignalMonitor backend. Supports live WebSocket push so
 * new signals appear in real time without polling.
 */
import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import { actionChipStyles } from "./ir-action-chip-styles";
import { customElement, property, state } from "./decorators.js";
import { formatLanguage, t, tp } from "./localize.js";
import { keyed } from "lit/directives/keyed.js";
import { repeat } from "lit/directives/repeat.js";
import Sortable from "sortablejs";
import { HairApi } from "./api.js";
import "./ir-assign-signal-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-save-wig-dialog.js";
import "./ir-promote-dialog.js";
import "./ir-signal-alias.js";
import "./ir-signal-editor.js";
import "./ir-test-emitter-dialog.js";
import "./ir-trigger-dialog.js";
import "./ir-count-dot.js";
import "./ir-trigger-popover.js";
import "./ir-assigned-popover.js";
import { MIRROR_DEVICE_FP, triggerMatchesSignal } from "./types.js";
import type {
    AssignResult,
    DeviceSummary,
    IRTrigger,
    ReceiverInfo,
    SignalAssignment,
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
        return d.toLocaleString(formatLanguage(), {
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
        if (diff < 60_000) return t("rel.just_now");
        if (diff < 3_600_000) return t("rel.min_ago", { count: Math.floor(diff / 60_000) });
        if (diff < 86_400_000) return t("rel.h_ago", { count: Math.floor(diff / 3_600_000) });
        return t("rel.d_ago", { count: Math.floor(diff / 86_400_000) });
    } catch {
        return "";
    }
}

// Signal-stream (SVG Repo, scaled to a 24x24 box).
const ICON_SIGNAL =
    "M12 9.188c-1.553 0-2.812 1.259-2.812 2.812s1.259 2.812 2.812 2.812c1.553 0 2.812-1.259 2.812-2.812v0c-0.002-1.552-1.26-2.81-2.812-2.812h-0zM12 13.688c-0.932 0-1.688-0.755-1.688-1.688s0.755-1.688 1.688-1.688c0.932 0 1.688 0.755 1.688 1.688v0c-0.002 0.931-0.756 1.686-1.688 1.688h-0zM2.062 12c0.16-2.665 1.25-5.049 2.948-6.856l-0.005 0.006c0.098-0.101 0.159-0.239 0.159-0.392 0-0.31-0.252-0.562-0.562-0.562-0.153 0-0.291 0.061-0.393 0.16l0-0c-1.906 1.998-3.125 4.667-3.27 7.618l-0.001 0.028c0.146 2.979 1.365 5.647 3.275 7.652l-0.005-0.005c0.101 0.098 0.239 0.159 0.392 0.159 0.31 0 0.562-0.252 0.562-0.562 0-0.152-0.061-0.291-0.16-0.392l0 0c-1.694-1.8-2.785-4.185-2.94-6.821l-0.002-0.03zM6.647 12c0.113-1.859 0.874-3.523 2.058-4.784l-0.004 0.004c0.098-0.101 0.159-0.239 0.159-0.392 0-0.31-0.252-0.562-0.562-0.562-0.153 0-0.291 0.061-0.392 0.16l0-0c-1.39 1.457-2.278 3.403-2.383 5.554l-0.001 0.02c0.105 2.171 0.994 4.117 2.386 5.577l-0.003-0.004c0.102 0.104 0.244 0.167 0.4 0.167 0.31 0 0.562-0.251 0.562-0.562 0-0.156-0.064-0.297-0.167-0.399l-0-0c-1.183-1.256-1.944-2.92-2.053-4.759l-0.001-0.021zM19.793 4.355c-0.102-0.101-0.241-0.164-0.396-0.164-0.31 0-0.562 0.252-0.562 0.562 0 0.154 0.062 0.294 0.162 0.395l-0-0c1.691 1.802 2.782 4.185 2.94 6.82l0.002 0.03c-0.16 2.665-1.249 5.05-2.947 6.857l0.005-0.006c-0.105 0.102-0.17 0.244-0.17 0.403 0 0.31 0.252 0.562 0.562 0.562 0.158 0 0.301-0.065 0.404-0.171l0-0c1.906-1.999 3.125-4.667 3.268-7.618l0.001-0.028c-0.146-2.978-1.364-5.647-3.274-7.65l0.005 0.005zM15.299 6.425c-0.102 0.102-0.165 0.242-0.165 0.398 0 0.154 0.062 0.295 0.164 0.397l-0-0c1.181 1.257 1.942 2.92 2.054 4.758l0.001 0.022c-0.114 1.86-0.875 3.523-2.059 4.784l0.004-0.004c-0.101 0.102-0.164 0.241-0.164 0.396 0 0.311 0.252 0.563 0.563 0.563 0.155 0 0.295-0.062 0.397-0.164l-0 0c1.389-1.458 2.277-3.404 2.383-5.555l0.001-0.02c-0.105-2.172-0.994-4.118-2.388-5.578l0.003 0.003c-0.101-0.102-0.242-0.165-0.397-0.165s-0.295 0.063-0.397 0.165l-0 0z";

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

// MDI: drag (six-dot grip) -- same handle used by the command reorder.
const ICON_GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";
// mdi:content-copy
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";

/** Debounce delay (ms) between a drop and the persist call. */
const REORDER_DEBOUNCE_MS = 500;


@customElement("ir-signal-monitor")
export class IrSignalMonitor extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    @state() private _devices: UnknownDeviceSummary[] = [];
    @state() private _hairDevices: DeviceSummary[] = [];
    @state() private _loading = true;
    @state() private _saveWigDevice: UnknownDevice | null = null;
    @state() private _deleteRemote: UnknownDevice | null = null;
    @state() private _error: string | null = null;
    // False when no receiver is configured (no native receiver, no bridge
    // events this session). Distinguishes "no receiver" from "no signals
    // yet" in the empty state. Optimistic default so the page does not
    // flash the no-receiver message before the status query returns.
    @state() private _hasReceivers = true;
    @state() private _showDismissed = false;
    @state() private _expandedId: string | null = null;
    @state() private _expandedDevice: UnknownDevice | null = null;
    @state() private _flashIds = new Set<string>();
    @state() private _flashStats = new Set<string>();
    /** Last 2 signal ids that received a hit (most recent first). */
    @state() private _recentSignalIds: string[] = [];
    /** Signal ids currently in glow animation. */
    @state() private _glowSignalIds = new Set<string>();
    /** Signal ids whose hit count is currently flashing. */
    @state() private _hitFlashSignalIds = new Set<string>();
    @state() private _confirmClearAll = false;

    // Trigger state
    @state() private _triggers: IRTrigger[] = [];
    @state() private _triggerDialog: {
        signal: UnknownSignal;
        deviceId: string;
    } | null = null;
    @state() private _triggerEditDialog: IRTrigger | null = null;
    @state() private _confirmDeleteTriggerId: string | null = null;
    // Trigger picker popover (v0.5.7): shown when 1+ triggers already bind a
    // signal's fingerprint; zero-trigger click opens the Create dialog directly.
    @state() private _triggerPopover: {
        deviceId: string;
        signal: UnknownSignal;
        top: number;
        left: number;
    } | null = null;
    // Assigned-commands popover (v0.6.6): shown when 1+ HAIR commands
    // already carry a signal's identity; zero-assignment click opens the
    // Assign dialog directly. Mirrors the trigger popover's flow.
    @state() private _assignedPopover: {
        deviceId: string;
        signal: UnknownSignal;
        label: string | null;
        top: number;
        left: number;
    } | null = null;
    // Receiver list for the popover's scope subtitles (best-effort load).
    @state() private _receivers: ReceiverInfo[] = [];
    private _unsubUpdated: (() => Promise<void>) | null = null;

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
    @state() private _editSignal: { deviceId: string; signal: UnknownSignal } | null = null;
    @state() private _testingSignalId: string | null = null;
    @state() private _testResult: string | null = null;
    // Dialog state for the Test emitter picker. ``_testEmitters`` persists
    // across opens (session-level memory) so users testing five signals
    // in a row don't have to re-pick the same emitter each time.
    @state() private _testDialog: { signal: UnknownSignal } | null = null;
    @state() private _testEmitters: string[] = [];

    // Dismiss-activity surface (Show Dismissed button).
    // ``_dismissGlowActive`` drives the transient blue glow class on the
    // button -- it flips true on every dismiss-activity bus event and
    // clears after a hold timer (slightly longer than the hit-flash so
    // it stays discoverable).
    // ``_dismissDotVisible`` is the persistent dot indicator -- it sticks
    // from the first dismiss-activity event after panel mount until the
    // user clicks Show Dismissed (which is the click-through that owns
    // restoring those remotes).
    @state() private _dismissGlowActive = false;
    @state() private _dismissDotVisible = false;

    private _unsubLive: (() => Promise<void>) | null = null;
    private _unsubRemoved: (() => Promise<void>) | null = null;
    private _unsubDismiss: (() => Promise<void>) | null = null;
    private _dismissGlowTimer: ReturnType<typeof setTimeout> | null = null;
    /**
     * Glow hold duration in ms. Hit-flash is ~2500ms; the dismiss-activity
     * glow holds ~3800ms so it sits 1-1.5 seconds longer than a hit-flash,
     * per the v0.2.0 plan decision: discoverable, not loud.
     */
    private static readonly DISMISS_GLOW_HOLD_MS = 3800;

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
        void this._subscribeLive();
        void this._subscribeRemoved();
        void this._subscribeDismissActivity();
        void this._subscribeUpdated();
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
        this._syncSortables();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        void this._unsubscribeLive();
        void this._unsubscribeRemoved();
        void this._unsubscribeDismissActivity();
        void this._unsubscribeUpdated();
        this._removePopoverDismiss();
        if (this._dismissGlowTimer !== null) {
            clearTimeout(this._dismissGlowTimer);
            this._dismissGlowTimer = null;
        }
        this._remotesSortable?.destroy();
        this._remotesSortable = null;
        this._signalsSortable?.destroy();
        this._signalsSortable = null;
        this._signalsSortableContainer = null;
        if (this._pendingRemotesSave !== null) clearTimeout(this._pendingRemotesSave);
        if (this._pendingSignalsSave !== null) clearTimeout(this._pendingSignalsSave);
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
                await this.api.reorderUnknownDevices("sniffed", deviceIds);
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
            }
        }, REORDER_DEBOUNCE_MS);
    }

    private async _load(): Promise<void> {
        this._loading = true;
        try {
            const [unknowns, hairDevs, triggers, status] = await Promise.all([
                this.api.getUnknownDevices({
                    include_dismissed: this._showDismissed,
                    source: "sniffed",
                }),
                this.api.listDevices(),
                this.api.listTriggers(),
                this.api.getSnifferStatus(),
            ]);
            this._devices = unknowns;
            this._hairDevices = hairDevs;
            this._triggers = triggers;
            this._hasReceivers = status.has_receivers;
            this._error = null;
            // Best-effort: receiver names for the trigger popover scope labels.
            // Never let a pre-2026.6 HA (no receiver API) break the main load.
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

    // --- Dismiss-activity surface (Show Dismissed glow + dot) ---

    /**
     * Subscribe to the dismiss-activity bus event. Each event represents
     * a signal that arrived from a remote in the persisted dismiss set
     * and got dropped from the live feed -- but the user should still
     * know it is firing so they can decide whether to restore it.
     *
     * The signal itself is not delivered through this channel; only the
     * device_fingerprint is needed to (a) trigger the button glow and
     * (b) flip the persistent dot. Multiple events from the same
     * fingerprint just re-trigger the glow timer.
     */
    private async _subscribeDismissActivity(): Promise<void> {
        try {
            this._unsubDismiss = await this.api.subscribeDismissActivity(
                () => this._onDismissActivity(),
            );
        } catch {
            // Non-fatal -- the glow + dot just won't surface.
        }
    }

    private async _unsubscribeDismissActivity(): Promise<void> {
        if (this._unsubDismiss) {
            await this._unsubDismiss();
            this._unsubDismiss = null;
        }
    }

    /**
     * Handle one dismiss-activity event. Restarts the glow hold timer
     * (so a held-down button keeps the button lit instead of flickering)
     * and sets the persistent dot until the user clicks through.
     */
    private _onDismissActivity(): void {
        this._dismissDotVisible = true;
        this._dismissGlowActive = true;
        if (this._dismissGlowTimer !== null) {
            clearTimeout(this._dismissGlowTimer);
        }
        this._dismissGlowTimer = setTimeout(() => {
            this._dismissGlowActive = false;
            this._dismissGlowTimer = null;
        }, IrSignalMonitor.DISMISS_GLOW_HOLD_MS);
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
        // Bubble up to the panel: switch to the Devices tab and expand
        // the assignment's device card.
        this.dispatchEvent(
            new CustomEvent("navigate-device", {
                detail: a.device_id,
                bubbles: true,
                composed: true,
            }),
        );
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

    private _openEditSignal(
        deviceId: string,
        signal: UnknownSignal,
        e: Event,
    ): void {
        e.stopPropagation();
        this._editSignal = { deviceId, signal };
    }

    private async _onSignalEdited(): Promise<void> {
        this._editSignal = null;
        await this._load();
        // The open signal list is rendered from _expandedDevice, not the
        // _devices summaries, so re-fetch it to surface the edited code/alias
        // without needing a re-expand.
        if (this._expandedId) {
            try {
                this._expandedDevice = await this.api.getUnknownDevice(this._expandedId);
            } catch {
                this._expandedId = null;
                this._expandedDevice = null;
            }
        }
    }

    private async _confirmDelete(): Promise<void> {
        if (!this._deleteSignal) return;
        const { deviceId, signal } = this._deleteSignal;
        this._deleteSignal = null;
        try {
            await this.api.deleteSignal(deviceId, signal.id);
            // Signal-removed event will refresh; manual fallback:
            await this._load();
        } catch (err) {
            this._error = `Delete failed: ${(err as Error).message}`;
        }
    }

    private _openTestDialog(signal: UnknownSignal): void {
        this._testDialog = { signal };
    }

    private _closeTestDialog(): void {
        this._testDialog = null;
    }

    private async _sendTest(e: CustomEvent): Promise<void> {
        if (!this._testDialog) return;
        const { signal } = this._testDialog;
        const emitters = e.detail.emitters as string[];
        if (emitters.length === 0) return;

        this._testingSignalId = signal.id;
        this._testResult = null;
        // Close the dialog immediately so the row's "Sending..." toast is
        // visible against the live feed background, not the dialog scrim.
        this._testDialog = null;

        try {
            const results = await Promise.allSettled(
                emitters.map((eid) =>
                    this.api.testSignal(signal.id, eid),
                ),
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

    // --- Trigger helpers ---

    /** Check if a signal already has a trigger (identity-aware, v0.5.8). */
    private _hasTrigger(signal: UnknownSignal): boolean {
        return this._triggers.some((t) => triggerMatchesSignal(t, signal));
    }

    /** Count triggers bound to a signal (yellow dot count). */
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
        // Zero triggers: open the Create dialog directly (no popover).
        if (matches.length === 0) {
            this._triggerDialog = { signal, deviceId };
            return;
        }
        // 1+ triggers: show the picker popover near the Trigger button.
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

    // Dismiss the popovers on an outside click or any scroll (bound refs so
    // add/removeEventListener pair up). One handler pair covers both the
    // trigger and assigned popovers; only one is ever open at a time.
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
        // Defer so the click that opened the popover doesn't immediately close it.
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

    /** A signal's assignment set changed: refresh triggers + the expanded
     * device so the green Assign and yellow trigger dots reflect it live. */
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
        // Reload triggers list.
        try {
            this._triggers = await this.api.listTriggers();
        } catch {
            // Non-fatal.
        }
    }

    private _onLiveSignal(ev: UnknownSignalEvent): void {
        // Mirror pushes (v0.6.6) are the house's own sends; the Mirror tab
        // renders them. Without this guard every HAIR send would look like
        // an unknown device and trigger a full list reload.
        if (ev.device_fingerprint === MIRROR_DEVICE_FP) return;
        const now = new Date().toISOString();

        // Update the matching device in our local list, or add a new one.
        const idx = this._devices.findIndex((d) => d.id === ev.device_id);
        if (idx >= 0) {
            const updated = { ...this._devices[idx] };
            updated.hit_count = ev.device_hit_count ?? ev.hit_count;
            updated.last_seen = now;
            // hit_count === 1 means a brand-new signal was created.
            if (ev.hit_count === 1) {
                updated.signal_count = (updated.signal_count ?? 0) + 1;
            }
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
                (s) => s.id === ev.signal_id,
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
                        // Sync collapsed row signal_count from fetched detail.
                        const dIdx = this._devices.findIndex((d) => d.id === ev.device_id);
                        if (dIdx >= 0) {
                            const synced = { ...this._devices[dIdx], signal_count: detail.signals.length };
                            const dCopy = [...this._devices];
                            dCopy[dIdx] = synced;
                            this._devices = dCopy;
                        }
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

        // Track the last 2 active signal ids for Assign button highlighting.
        // Keyed by signal id, not fingerprint: two signals on a remote can
        // share a fingerprint, so a fingerprint key would highlight both.
        if (ev.signal_id) {
            const recent = [ev.signal_id, ...this._recentSignalIds.filter(
                (sid) => sid !== ev.signal_id,
            )].slice(0, 2);
            this._recentSignalIds = recent;

            // Trigger glow animation on the Assign button.
            this._glowSignalIds = new Set([...this._glowSignalIds, ev.signal_id]);
            setTimeout(() => {
                const next = new Set(this._glowSignalIds);
                next.delete(ev.signal_id);
                this._glowSignalIds = next;
            }, 1200);

            // Trigger hit count flash animation.
            this._hitFlashSignalIds = new Set([...this._hitFlashSignalIds, ev.signal_id]);
            setTimeout(() => {
                const next = new Set(this._hitFlashSignalIds);
                next.delete(ev.signal_id);
                this._hitFlashSignalIds = next;
            }, 1200);
        }
    }

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


    private async _confirmDeleteRemote(): Promise<void> {
        const device = this._deleteRemote;
        this._deleteRemote = null;
        if (!device) return;
        try {
            await this.api.deleteSniffedRemote(device.id);
            this._expandedId = null;
        } catch (err) {
            this._error = (err as Error).message;
        }
        await this._load();
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
        // Click-through clears the persistent dot. The user has now
        // acknowledged the dismissed-activity surface; further events
        // can re-light it. Glow runs out on its own timer.
        this._dismissDotVisible = false;
        void this._load();
    }

    render() {
        return html`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${ICON_SIGNAL}></ha-svg-icon>
                    ${t("sniffer.title")}
                    ${!this._loading
                        ? html`<span class="count"
                              >(${tp("sniffer.remotes", this._devices.length)})</span
                          >`
                        : ""}
                </span>
            </div>

            ${this._error
                ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                : ""}

            ${this._loading
                ? html`<div class="loading">${t("sniffer.scanning")}</div>`
                : this._devices.length === 0
                  ? this._hasReceivers
                    ? html`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ICON_SIGNAL}></ha-svg-icon>
                            <h3>${t("sniffer.empty_title")}</h3>
                            <p>${t("sniffer.empty_body")}</p>
                            <p class="hint">${t("sniffer.empty_hint")}</p>
                        </ha-card>
                    `
                    : html`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ICON_SIGNAL}></ha-svg-icon>
                            <h3>${t("sniffer.norx_title")}</h3>
                            <p>${t("sniffer.norx_body")}</p>
                            <p class="hint">${t("sniffer.norx_hint")}</p>
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

            <div class="bottom-bar">
                <button
                    class="action-btn dismiss-btn ${this._dismissGlowActive ? "dismiss-glow" : ""}"
                    title=${t("sniffer.show_dismissed_title")}
                    @click=${this._toggleDismissed}
                >
                    ${this._showDismissed ? t("sniffer.hide_dismissed") : t("sniffer.show_dismissed")}
                    ${this._dismissDotVisible
                        ? html`<span class="dismiss-dot" aria-hidden="true"></span>`
                        : ""}
                </button>
                ${this._devices.length > 0 || this._showDismissed
                    ? html`<button
                          class="action-btn delete-btn"
                          title=${t("sniffer.clear_all_title")}
                          @click=${() => (this._confirmClearAll = true)}
                      >
                          ${t("sniffer.clear_all")}
                      </button>`
                    : ""}
            </div>

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
            ${this._deleteRemote
                ? html`<ir-confirm-dialog
                      title=${t("clips.del_remote_confirm_title")}
                      message=${t("sniffer.del_remote_msg", {
                          name: this._deleteRemote.label ?? "this remote",
                      })}
                      confirmLabel=${t("common.delete")}
                      .destructive=${true}
                      @confirmed=${this._confirmDeleteRemote}
                      @closed=${() => (this._deleteRemote = null)}
                  ></ir-confirm-dialog>`
                : ""}
            ${this._saveWigDevice
                ? html`<ir-save-wig-dialog
                      .api=${this.api}
                      source="catalog"
                      sourceId=${this._saveWigDevice.id}
                      sourceName=${this._saveWigDevice.label ?? ""}
                      @closed=${() => (this._saveWigDevice = null)}
                  ></ir-save-wig-dialog>`
                : ""}

            ${this._deleteSignal
                ? html`
                      <ir-confirm-dialog
                          title=${t("sniffer.del_signal_title")}
                          message=${t("sniffer.del_signal_msg")}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._confirmDelete}
                          @closed=${this._closeDelete}
                      ></ir-confirm-dialog>
                  `
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
                      .allowSnap=${true}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${() => (this._editSignal = null)}
                  ></ir-signal-editor>`
                : ""}

            ${this._confirmClearAll
                ? html`
                      <ir-confirm-dialog
                          title=${t("sniffer.clear_all_confirm_title")}
                          message=${t("sniffer.clear_all_confirm_msg")}
                          confirmLabel="Clear All"
                          .destructive=${true}
                          @confirmed=${this._doClearAll}
                          @closed=${() => (this._confirmClearAll = false)}
                      ></ir-confirm-dialog>
                  `
                : ""}

            ${this._triggerPopover
                ? html`
                      <ir-trigger-popover
                          .triggers=${this._triggers.filter((t) =>
                              triggerMatchesSignal(
                                  t,
                                  this._triggerPopover!.signal,
                              ),
                          )}
                          .receivers=${this._receivers}
                          .top=${this._triggerPopover.top}
                          .left=${this._triggerPopover.left}
                          @create-new=${this._onPopoverCreateNew}
                          @edit-trigger=${this._onPopoverEditTrigger}
                      ></ir-trigger-popover>
                  `
                : ""}
            ${this._assignedPopover
                ? html`
                      <ir-assigned-popover
                          .assignments=${this._assignedPopover.signal.assigned_to ?? []}
                          .top=${this._assignedPopover.top}
                          .left=${this._assignedPopover.left}
                          @create-new=${this._onAssignedPopoverCreateNew}
                          @open-assignment=${this._onAssignedPopoverOpen}
                      ></ir-assigned-popover>
                  `
                : ""}
            ${this._triggerDialog
                ? html`
                      <ir-trigger-dialog
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
                      ></ir-trigger-dialog>
                  `
                : ""}
            ${this._testDialog
                ? html`
                      <ir-test-emitter-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .value=${this._testEmitters}
                          @emitters-changed=${(e: CustomEvent) =>
                              (this._testEmitters = e.detail.value)}
                          @send=${this._sendTest}
                          @closed=${this._closeTestDialog}
                      ></ir-test-emitter-dialog>
                  `
                : ""}
            ${this._triggerEditDialog
                ? html`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEditDialog}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${(e: CustomEvent) =>
                              this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `
                : ""}
            ${this._confirmDeleteTriggerId
                ? html`
                      <ir-confirm-dialog
                          title=${t("mirror.del_trigger_title")}
                          message=${t("devdetail.del_trigger_msg")}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${() => (this._confirmDeleteTriggerId = null)}
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
            <ha-card class="device ${d.dismissed ? "dismissed" : ""}">
                <div
                    class="device-row ${flashing ? "flash-row" : ""}"
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
                                : html`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${ICON_GRIP}
                                          title=${t("devdetail.drag")}
                                          @click=${(e: Event) => e.stopPropagation()}
                                      ></ha-svg-icon>
                                      ${d.dismissed
                                          ? html`<span class="protocol locked"
                                                >${d.label ?? d.protocol ?? t("common.raw")}</span
                                            >`
                                          : html`<span
                                                class="protocol"
                                                title=${t("cmdrow.rename")}
                                                @click=${(e: Event) => this._startRename(d, e)}
                                            >${d.label ?? d.protocol ?? t("common.raw")}</span>`}`}
                            <span class="device-stats ${statsFlash ? "stats-flash" : ""}">
                                <span class="stat"
                                    ><strong>${d.hit_count}</strong>
                                    ${tp("sniffer.hit_word", d.hit_count)}</span
                                >
                                <span class="stat"
                                    ><strong>${d.signal_count}</strong>
                                    ${tp("sniffer.signal_word", d.signal_count)}</span
                                >
                                <span class="stat last-seen" title=${fmtTime(d.last_seen)}>${relTime(d.last_seen)}</span>
                            </span>
                            ${d.label && this._matchesHairDevice(d.label)
                                ? html`<span
                                      class="status-badge hair-device"
                                      @click=${(e: Event) => e.stopPropagation()}
                                  >${t("sniffer.hair_device")}</span>`
                                : d.label && !d.dismissed
                                    ? html`<span
                                          class="status-badge promote-badge"
                                          @click=${(e: Event) => this._promoteDevice(d, e)}
                                      >${t("sniffer.promote")}</span>`
                                    : ""}
                            ${d.device_address
                                ? html`<span class="address">${t("sniffer.addr", { address: d.device_address })}</span>`
                                : ""}
                            ${d.dismissed
                                ? html`<span class="dismissed-badge">${t("sniffer.dismissed")}</span>`
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
                          >${t("sniffer.restore")}</button>`
                        : html`<button
                              class="action-btn device-dismiss-btn"
                              @click=${(e: Event) => {
                                  e.stopPropagation();
                                  void this._dismiss(d.id);
                              }}
                          >${t("sniffer.dismiss")}</button>`}
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
                    <span class="first-seen">${t("sniffer.first_seen", { time: fmtTime(device.first_seen) })}</span>
                </div>
                <div class="signal-list">
                    ${keyed(
                        this._signalsVersion,
                        repeat(
                            device.signals,
                            (sig) => sig.id,
                            (sig) => {
                            const recentIdx = this._recentSignalIds.indexOf(sig.id);
                            const isLatest = recentIdx === 0;
                            const isPrevious = recentIdx === 1;
                            const isGlowing = this._glowSignalIds.has(sig.id);
                            const isHitFlash = this._hitFlashSignalIds.has(sig.id);
                            return html`
                            <div class="signal-row">
                                ${device.dismissed
                                    ? ""
                                    : html`<ha-svg-icon
                                          class="signal-grip"
                                          .path=${ICON_GRIP}
                                          title=${t("devdetail.drag")}
                                      ></ha-svg-icon>`}
                                <div class="signal-info">
                                    <ir-signal-alias
                                        .api=${this.api}
                                        .deviceId=${device.id}
                                        .signal=${sig}
                                        ?disabled=${device.dismissed}
                                        @alias-changed=${this._onAliasChanged}
                                    ></ir-signal-alias>
                                </div>
                                <div class="signal-meta">
                                    <span class="${isHitFlash ? "hit-flash" : ""}"
                                        >${sig.hit_count}
                                        ${tp("sniffer.hit_word", sig.hit_count)}</span
                                    >
                                    <span title=${fmtTime(sig.last_seen)}
                                        >${relTime(sig.last_seen)}</span
                                    >
                                    <span>${Math.round(sig.frequency / 1000)} kHz</span>
                                </div>
                                ${sig.code
                                    ? html`<button
                                          ?disabled=${device.dismissed}
                                          title=${t("cmdrow.edit_code")}
                                          @click=${(e: Event) =>
                                              this._openEditSignal(device.id, sig, e)}
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
                                        class="action-btn assign-btn ${isLatest ? "recent-latest" : ""} ${isPrevious ? "recent-previous" : ""} ${isGlowing ? "glow" : ""}"
                                        @click=${(e: Event) => {
                                            e.stopPropagation();
                                            this._onAssignClick(device.id, sig, device.label, e);
                                        }}
                                        ?disabled=${device.dismissed}
                                        title=${sig.assignment_count && sig.assigned_to?.length
                                            ? (sig.assignment_count === 1
                                                ? t("mirror.assigned_one", {
                                                      device: sig.assigned_to[0].device_name,
                                                      command: sig.assigned_to[0].command_name,
                                                  })
                                                : t("mirror.assigned_n", { count: sig.assignment_count }) + `\n- ${sig.assigned_to.map((a) => `${a.device_name} / ${a.command_name}`).join("\n- ")}`)
                                            : (device.dismissed
                                                ? t("sniffer.restore_first")
                                                : t("mirror.assign_title"))}
                                    >${t("assign.assign")}<ir-count-dot
                                            color="green"
                                            .count=${sig.assignment_count ?? 0}
                                        ></ir-count-dot></button>
                                    <button
                                        class="action-btn test-btn"
                                        @click=${(e: Event) => {
                                            e.stopPropagation();
                                            this._openTestDialog(sig);
                                        }}
                                        ?disabled=${device.dismissed || this._testingSignalId === sig.id}
                                        title=${device.dismissed
                                            ? t("sniffer.restore_first")
                                            : t("mirror.test_title")}
                                    >${this._testingSignalId === sig.id
                                        ? (this._testResult ?? t("mirror.sending"))
                                        : t("mirror.test")}</button>
                                    <button
                                        class="action-btn trigger-btn"
                                        @click=${(e: Event) => {
                                            e.stopPropagation();
                                            this._openTriggerDialog(device.id, sig, e);
                                        }}
                                        ?disabled=${device.dismissed}
                                        title=${this._hasTrigger(sig)
                                            ? t("mirror.trigger_edit")
                                            : (device.dismissed
                                                ? t("sniffer.restore_first")
                                                : t("sniffer.trigger_create"))}
                                    >${t("cmdrow.trigger")}<ir-count-dot
                                            color="yellow"
                                            .count=${this._triggerCountFor(sig)}
                                        ></ir-count-dot></button>
                                    <button
                                        class="action-btn delete-btn"
                                        @click=${(e: Event) => {
                                            e.stopPropagation();
                                            this._openDelete(device.id, sig);
                                        }}
                                    >${t("common.delete")}</button>
                                </div>
                            </div>
                        `;
                            },
                        ),
                    )}
                </div>
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
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._deleteRemote = device;
                        }}
                    >${t("clips.delete_remote")}</button>
                </div>
            </div>
        `;
    }

    static styles = [actionChipStyles, css`
        .remote-footer {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
            margin-top: 10px;
            padding-right: 8px;
        }
        .save-wig-btn {
            color: #8e3b3b;
            border-color: #8e3b3b;
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

        /* Clear All anchor below the unknown-devices list.
           Moved out of the top toolbar in v0.2.1 to pair visually with
           the new "Clear All also wipes the dismiss list" semantic, and
           to force the user to scroll past what they are about to delete
           before pressing the destructive button. */
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
            /* Clip the row's rectangular hover highlight to the card's
               rounded corners so it does not poke past the border stroke. */
            overflow: hidden;
            /* Subtle stroke in the Sniffer's accent blue (the radio-icon
               colour) at the same 0.3 as the Clips copper stroke. The
               rgba line is a fallback for webviews without color-mix. */
            border: 1px solid rgba(33, 150, 243, 0.3);
            border-color: color-mix(in srgb, var(--primary-color) 30%, transparent);
        }
        /* Hit flash: pulse the device-row background. When the card is
           collapsed the row fills the whole card (the card's overflow:hidden
           clips the pulse to the rounded corners), so the entire card appears
           to flash; when expanded only the top row flashes, leaving the signal
           list below calm. */
        .device-row.flash-row {
            animation: row-flash 900ms ease-out;
        }
        @keyframes row-flash {
            0% { background: transparent; }
            18% {
                background: rgba(33, 150, 243, 0.32);
                background: color-mix(in srgb, var(--primary-color) 32%, transparent);
            }
            100% { background: transparent; }
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
        .device-icon {
            --mdc-icon-size: 16px;
            color: var(--primary-color);
            flex-shrink: 0;
        }
        /* Remote drag handle (replaces the radio icon): blue, matches tab. */
        .remote-grip {
            --mdc-icon-size: 18px;
            color: var(--primary-color);
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
        .protocol:not(.locked):hover {
            border-bottom-color: var(--primary-color);
        }
        .protocol.locked {
            cursor: default;
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
        /* Identical box to .promote-badge (now also uppercase, so no
           line-height hack needed) -- only the colour differs. */
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
            margin-left: 4px;
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
            margin-left: 4px;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 151, 167, 0.25);
        }
        .device-dismiss-btn {
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
            display: inline-flex;
            align-items: center;
            gap: 12px;
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
            /* Match the page background so the Sniffer signal rows blend
               with the panel backdrop instead of reading as highlighted
               peach strips, mirroring the device-detail command row
               treatment. Device-row hover (above) and action-btn hover
               (below) still use --secondary-background-color so hover
               feedback stays distinguishable. */
            background: var(--primary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        /* Mobile layout fix.
           On narrow viewports the diamond pattern inside .signal-info
           wraps internally into a tall column, and flex/align-center
           floats the action buttons (Assign / Test / Trigger / Delete)
           into the vertical middle of the row with huge whitespace
           above and below. Switching to a 2-row grid keeps the
           diamonds + meta on the first row and stacks the action
           buttons below in their own band. Mirrors the bounded row
           height that the device-detail command rows already get via
           their fixed-column grid on every viewport. */
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
        .signal-code {
            font-size: 0.82rem;
            word-break: break-all;
        }
        .signal-short-label {
            font-size: 0.82rem;
            color: var(--secondary-text-color);
            font-style: italic;
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

        /* Transient blue pulse on the Show Dismissed button when a
           signal arrives from a remote in the dismiss set. Reuses the
           same --primary-color blue users associate with "a signal just
           arrived", held ~3.8s so it sits about 1.3s longer than the
           hit-flash and stays discoverable. */
        .action-btn.dismiss-btn.dismiss-glow {
            animation: dismiss-pulse 3.8s ease-out;
            border-color: var(--primary-color);
        }
        @keyframes dismiss-pulse {
            0% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.0); }
            12% { box-shadow: 0 0 10px 3px rgba(33, 150, 243, 0.55); }
            70% { box-shadow: 0 0 6px 2px rgba(33, 150, 243, 0.3); }
            100% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.0); }
        }

        /* Persistent dot indicator anchored to the top-right of the
           Show Dismissed button. Stays visible from the first
           dismiss-activity event after panel mount until the user
           clicks the button (the natural click-through that owns
           restoring dismissed remotes). */
        .dismiss-dot {
            position: absolute;
            top: -3px;
            right: -3px;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--primary-color);
            box-shadow: 0 0 4px rgba(33, 150, 243, 0.55);
            pointer-events: none;
        }

        /* Latest signal: deep green fill (AA contrast with the white
           label) with a mint rim that previews the hit ring. Locked
           design: sniffer-hit-glow.md -- the earlier same-green halo
           read as a blob against the fill. */
        .action-btn.assign-btn.recent-latest {
            color: #fff;
            background: #2e7d32;
            border-color: #69f0ae;
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

        /* Hit pulse: the mint rim blooms into a ring, brighter than
           the fill so the halo separates instead of blobbing. */
        .action-btn.assign-btn.glow {
            animation: assign-glow 1.4s ease-out;
        }
        @keyframes assign-glow {
            0% { box-shadow: 0 0 0 0 rgba(105, 240, 174, 0.9); }
            35% { box-shadow: 0 0 0 2px #69f0ae, 0 0 12px 5px rgba(105, 240, 174, 0.55); }
            100% { box-shadow: 0 0 0 0 rgba(105, 240, 174, 0); }
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
    `];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-signal-monitor": IrSignalMonitor;
    }
}
