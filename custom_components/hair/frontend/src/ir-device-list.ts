/**
 * Devices overview page with four sections:
 *   Devices  -- HAIR-managed IR devices (expandable inline detail)
 *   Emitters -- infrared.* TX entities
 *   Receivers -- RX-only capture providers
 *   Proxies  -- TX+RX capable hardware (both emitter and receiver)
 *
 * Emits ``device-selected`` and ``add-device`` events for HAIR devices.
 * Emitter/receiver/proxy cards link to their HA integration page.
 */
import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import {
    ICON_TRASH,
    TRASH_VIEWBOX,
    renderExitToEntityBtn,
    exitToEntityButtonStyles,
} from "./ir-icons.js";
import { BloomTracker, bloomStyles } from "./ir-bloom-styles.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";
import { keyed } from "lit/directives/keyed.js";
import { repeat } from "lit/directives/repeat.js";
import Sortable from "sortablejs";
import "./ir-device-detail.js";
import "./ir-trigger-dialog.js";
import "./ir-trigger-row.js";
import "./ir-confirm-dialog.js";
import "./ir-duplicate-device-dialog.js";
import type { HairApi } from "./api.js";
import type {
    CaptureProviderInfo,
    DeviceSummary,
    DeviceTypeId,
    IRDevice,
    IRTrigger,
    ReceiverInfo,
    TriggerDrawerInfo,
    TriggerFiredEvent,
} from "./types.js";

/**
 * Sentinel "device id" for the single HAIR Triggers drawer card, reusing
 * the parent panel's existing ``expandedDeviceId``/``device-selected``
 * expand-one-at-a-time machinery (ha-panel-ir-devices.ts's
 * ``_toggleDevice``) rather than inventing a second, parallel expansion
 * concept. Guaranteed not to collide with a real device id (those are
 * storage-assigned uuids).
 */
const TRIGGER_DRAWER_ID = "__hair_triggers_drawer__";

const DEVICE_TYPE_ICONS: Record<DeviceTypeId, string> = {
    media_player: "M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",
    ac: "M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",
    fan: "M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",
    light: "M12,2A7,7 0 0,0 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H15A1,1 0 0,0 16,17V14.74C17.81,13.47 19,11.38 19,9A7,7 0 0,0 12,2M9,21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9V21Z",
    switch: "M13,3H11V13H13V3M17.83,5.17L16.41,6.59C18,7.35 19,9.05 19,11A7,7 0 0,1 12,18A7,7 0 0,1 5,11C5,9.05 6,7.35 7.58,6.59L6.17,5.17C4.23,6.82 3,9.26 3,12A9,9 0 0,0 12,21A9,9 0 0,0 21,12C21,9.26 19.77,6.82 17.83,5.17Z",
    screen: "M20,19H4A2,2 0 0,1 2,17V7A2,2 0 0,1 4,5H20A2,2 0 0,1 22,7V17A2,2 0 0,1 20,19M4,7V17H20V7H4M12,10L16,14H13V17H11V14H8L12,10Z",
    other: "M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z",
};

// Dictionary keys, resolved through t() at render time. "other" maps
// to the card-specific label ("IR Device"), not the dialogs' "Other".
const DEVICE_TYPE_LABEL_KEYS: Record<DeviceTypeId, string> = {
    media_player: "device_type.media_player",
    ac: "device_type.ac",
    fan: "device_type.fan",
    light: "device_type.light",
    switch: "device_type.switch",
    screen: "device_type.screen",
    other: "device_type.other_card",
};

// Remote control (SVG Repo, scaled to a 24x24 box).
const ICON_DEVICES =
    "M17.655 0C17.391 0.034 17.201 0.276 17.235 0.54C17.269 0.804 17.511 0.994 17.775 0.96C17.775 0.96 18.154 0.941 18.81 1.155C19.466 1.369 20.353 1.804 21.255 2.73C22.162 3.66 22.611 4.551 22.83 5.205C23.049 5.859 23.04 6.24 23.04 6.24C23.038 6.412 23.128 6.574 23.278 6.662C23.428 6.748 23.612 6.748 23.762 6.662C23.912 6.574 24.002 6.412 24 6.24C24 6.24 23.991 5.679 23.73 4.905C23.469 4.131 22.957 3.109 21.945 2.07C20.927 1.027 19.894 0.495 19.11 0.24C18.326 -0.015 17.745 0 17.745 0C17.73 0 17.715 0 17.7 0C17.685 0 17.67 0 17.655 0 Z M 13.77 2.88C13.26 2.88 12.746 3.064 12.345 3.435C12.339 3.441 12.336 3.444 12.33 3.45L0.57 15.255C-0.195 16.02 -0.188 17.286 0.555 18.09C0.561 18.096 0.564 18.099 0.57 18.105L5.955 23.475C6.72 24.24 7.971 24.232 8.775 23.49C8.781 23.484 8.784 23.481 8.79 23.475L20.55 11.715C20.556 11.706 20.561 11.694 20.565 11.685C21.289 10.841 21.315 9.6 20.55 8.835L15.165 3.45C14.782 3.067 14.28 2.88 13.77 2.88 Z M 17.67 2.88C17.406 2.904 17.211 3.141 17.235 3.405C17.259 3.669 17.496 3.864 17.76 3.84C17.76 3.84 17.91 3.831 18.21 3.93C18.51 4.029 18.911 4.241 19.335 4.665C19.759 5.089 19.971 5.49 20.07 5.79C20.169 6.09 20.16 6.24 20.16 6.24C20.158 6.412 20.248 6.574 20.398 6.662C20.548 6.748 20.732 6.748 20.882 6.662C21.032 6.574 21.122 6.412 21.12 6.24C21.12 6.24 21.111 5.91 20.97 5.49C20.829 5.07 20.561 4.511 20.025 3.975C19.489 3.439 18.93 3.171 18.51 3.03C18.09 2.889 17.76 2.88 17.76 2.88C17.745 2.88 17.73 2.88 17.715 2.88C17.7 2.88 17.685 2.88 17.67 2.88 Z M 13.77 3.84C14.04 3.84 14.297 3.932 14.49 4.125L19.875 9.51C20.263 9.898 20.274 10.569 19.845 11.07L8.115 22.785C7.671 23.194 7.018 23.188 6.63 22.8L1.26 17.43C1.254 17.424 1.251 17.421 1.245 17.415C0.849 16.971 0.862 16.328 1.245 15.945L13.005 4.14C13.226 3.936 13.5 3.84 13.77 3.84 Z M 13.44 6.72C11.325 6.72 9.6 8.445 9.6 10.56C9.6 12.675 11.325 14.4 13.44 14.4C15.555 14.4 17.28 12.675 17.28 10.56C17.28 8.445 15.555 6.72 13.44 6.72 Z M 13.44 7.68C15.036 7.68 16.32 8.964 16.32 10.56C16.32 12.156 15.036 13.44 13.44 13.44C11.844 13.44 10.56 12.156 10.56 10.56C10.56 8.964 11.844 7.68 13.44 7.68 Z M 13.44 9.6C12.909 9.6 12.48 10.029 12.48 10.56C12.48 11.091 12.909 11.52 13.44 11.52C13.971 11.52 14.4 11.091 14.4 10.56C14.4 10.029 13.971 9.6 13.44 9.6 Z M 7.2 12.96C6.669 12.96 6.24 13.389 6.24 13.92C6.24 14.451 6.669 14.88 7.2 14.88C7.731 14.88 8.16 14.451 8.16 13.92C8.16 13.389 7.731 12.96 7.2 12.96 Z M 4.8 15.36C4.269 15.36 3.84 15.789 3.84 16.32C3.84 16.851 4.269 17.28 4.8 17.28C5.331 17.28 5.76 16.851 5.76 16.32C5.76 15.789 5.331 15.36 4.8 15.36 Z M 10.08 15.84C9.549 15.84 9.12 16.269 9.12 16.8C9.12 17.331 9.549 17.76 10.08 17.76C10.611 17.76 11.04 17.331 11.04 16.8C11.04 16.269 10.611 15.84 10.08 15.84 Z M 7.68 18.24C7.149 18.24 6.72 18.669 6.72 19.2C6.72 19.731 7.149 20.16 7.68 20.16C8.211 20.16 8.64 19.731 8.64 19.2C8.64 18.669 8.211 18.24 7.68 18.24Z";

// MDI: upload-outline for emitters (mirrors download-outline for receivers)
const ICON_EMITTER =
    "M9,10V16H15V10H19L12,3L5,10H9M12,5.8L14.2,8H13V14H11V8H9.8L12,5.8M19,18H5V20H19V18Z";

// MDI: download-outline for receivers
const ICON_RECEIVER =
    "M13,5V11H14.17L12,13.17L9.83,11H11V5H13M15,3H9V9H5L12,16L19,9H15V3M19,18H5V20H19V18Z";

// MDI: radio-tower for proxies
const ICON_PROXY =
    "M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.94 13.53,13.29L16.7,22H14.57L12,14.93L9.43,22H7.3L10.47,13.29C10.18,12.94 10,12.5 10,12A2,2 0 0,1 12,10M12,8A4,4 0 0,0 8,12C8,12.5 8.1,13 8.28,13.46L7.4,15.86C6.53,14.81 6,13.47 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12C18,13.47 17.47,14.81 16.6,15.86L15.72,13.46C15.9,13 16,12.5 16,12A4,4 0 0,0 12,8M12,4A8,8 0 0,0 4,12C4,14.36 5,16.5 6.64,17.94L5.92,19.94C3.54,18.11 2,15.23 2,12A10,10 0 0,1 12,2A10,10 0 0,1 22,12C22,15.23 20.46,18.11 18.08,19.94L17.36,17.94C19,16.5 20,14.36 20,12A8,8 0 0,0 12,4Z";

// MDI: flash (lightning bolt) for triggers
const ICON_TRIGGER =
    "M7,2V13H10V22L17,10H13L17,2H7Z";

// MDI: drag (six-dot grip), for the trigger row's slotted drag handle.
// Same glyph ir-device-detail.ts's own (unexported) ICON_GRIP uses for
// command rows -- kept as a local copy rather than a shared export,
// matching that file's own precedent of not centralizing this one icon.
const ICON_GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";

// MDI: content-copy (duplicate icon)
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";

// Tweezers (matches the Plucker tab icon).
const ICON_BLASTER =
    "M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z";

/** Debounce delay (ms) between a drop and the persist call. */
const REORDER_DEBOUNCE_MS = 500;

/**
 * Result of merging capture providers by HA device ID.
 *
 * A physical device with both a native ``InfraredReceiverEntity`` and a
 * legacy ESPHome event-bridge entry collapses into one of these.  Broadlink
 * (proprietary learn mode) is bucketed as bridge for display purposes.
 */
interface MergedHardwareEntry {
    device_id: string;            // HA device-registry ID (merge key)
    name: string;                 // display name
    nav_type: string;             // integration domain for navigation
    has_native: boolean;          // InfraredReceiverEntity present
    has_bridge: boolean;          // ESPHome bridge or Broadlink learn mode
    has_tx: boolean;              // also TX-capable (= shows as proxy)
    native_entity_id?: string;    // entity_id of the native receiver, if any
    tx_entity_ids: string[];      // infrared.* TX entity_ids on this device
}

@customElement("ir-device-list")
export class IrDeviceList extends LitElement {
    @property({ attribute: false }) public devices: DeviceSummary[] = [];
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api?: HairApi;
    @property({ type: Boolean }) public loading = false;
    @property({ attribute: false }) public expandedDeviceId: string | null = null;

    @state() private _emitters: { entity_id: string; name: string }[] = [];
    @state() private _captureProviders: CaptureProviderInfo[] = [];
    @state() private _pluckBlasters: {
        integration: string;
        entity_id: string;
        name: string;
        vendorName: string;
    }[] = [];
    @state() private _expandedDevice: IRDevice | null = null;
    @state() private _triggers: IRTrigger[] = [];
    @state() private _glowTriggerIds = new Set<string>();
    @state() private _editTrigger: IRTrigger | null = null;
    @state() private _confirmDeleteTrigger: IRTrigger | null = null;
    @state() private _duplicateTarget: DeviceSummary | null = null;
    @state() private _confirmDeleteDevice: DeviceSummary | null = null;

    // Receivers, for the trigger rows' scope-chip name resolution (v0.5.7
    // per-trigger scoping). Fetched alongside the capture-provider list in
    // ``_discoverHardware`` -- that method already calls ``listReceivers()``
    // for the emitter-exclusion set but was discarding the list itself.
    @state() private _receivers: ReceiverInfo[] = [];

    // HAIR Triggers drawer identity (name + optional HA device-registry
    // link, Track B item 9). Loaded once the trigger drawer card is
    // expanded, not eagerly -- same lazy-load discipline as
    // ``_expandedDevice``.
    @state() private _triggerDrawer: TriggerDrawerInfo | null = null;
    @state() private _editingDrawerName = false;
    @state() private _draftDrawerName = "";
    @state() private _drawerBusy = false;

    // Drag-to-reorder for trigger rows inside the expanded drawer (grip
    // handle, mirrors ir-device-detail.ts's command-reorder pattern).
    @state() private _triggerRowsVersion = 0;
    private _triggerSortable: Sortable | null = null;
    private _pendingTriggerReorderSave: number | null = null;

    // Sequence-numbered fire-glow tracker (ir-bloom-styles.ts). Replaces
    // the old bare ``setTimeout`` + ``Set`` pair, which let a fast repeat
    // fire's glow get cut short by the first fire's still-pending timeout
    // (v0.7.2 bug, see ir-bloom-styles.ts's module doc).
    private _bloomTracker = new BloomTracker();

    // Drag-to-reorder for the HAIR device cards (whole-card drag, no handle).
    // ``_localDevices`` holds the optimistic order between a drop and the
    // next parent refresh; it is reset to null whenever the parent pushes a
    // fresh ``devices`` property (which is then the source of truth).
    @state() private _devicesVersion = 0;
    @state() private _localDevices: DeviceSummary[] | null = null;
    private _devicesSortable: Sortable | null = null;
    private _pendingDevicesSave: number | null = null;

    private _unsubTriggerFired: (() => Promise<void>) | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        this._discoverHardware();
        void this._loadTriggers();
        void this._loadTriggerDrawer();
        void this._subscribeTriggerFired();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        void this._unsubscribeTriggerFired();
        this._devicesSortable?.destroy();
        this._devicesSortable = null;
        if (this._pendingDevicesSave !== null) clearTimeout(this._pendingDevicesSave);
        this._triggerSortable?.destroy();
        this._triggerSortable = null;
        if (this._pendingTriggerReorderSave !== null) {
            clearTimeout(this._pendingTriggerReorderSave);
        }
    }

    protected willUpdate(changed: PropertyValues): void {
        // When the parent hands us a fresh device list, adopt it as the
        // source of truth and drop any optimistic local ordering.
        if (changed.has("devices")) {
            this._localDevices = null;
        }
    }

    updated(changed: PropertyValues): void {
        if (changed.has("hass") || changed.has("api")) {
            this._discoverHardware();
        }
        if (changed.has("api") && this.api && !this._unsubTriggerFired) {
            void this._loadTriggers();
            void this._loadTriggerDrawer();
            void this._subscribeTriggerFired();
        }
        if (changed.has("expandedDeviceId")) {
            void this._loadExpandedDevice();
        }
        this._syncDevicesSortable();
        this._syncTriggerSortable();
    }

    /** Attach / detach the device-grid SortableJS instance. */
    private _syncDevicesSortable(): void {
        const grid = this.renderRoot.querySelector(".device-grid") as HTMLElement | null;
        if (grid && !this._devicesSortable) {
            this._attachDevicesSortable(grid);
        } else if (!grid && this._devicesSortable) {
            this._devicesSortable.destroy();
            this._devicesSortable = null;
        }
    }

    private _attachDevicesSortable(grid: HTMLElement): void {
        this._devicesSortable = Sortable.create(grid, {
            // Whole card drags (no grip). ``delay`` keeps a quick click as
            // expand/collapse and a press-and-hold as a drag. The corner
            // duplicate/delete buttons are excluded as drag origins.
            draggable: ".device-card",
            filter: ".card-action",
            preventOnFilter: false,
            delay: 150,
            delayOnTouchOnly: true,
            animation: 150,
            ghostClass: "sortable-ghost",
            onEnd: () => {
                // Read the new order straight from the DOM (robust against
                // the expanded-detail sibling that also lives in the grid).
                const ids = Array.from(
                    grid.querySelectorAll(".device-card"),
                )
                    .map((el) => (el as HTMLElement).dataset.id)
                    .filter((id): id is string => !!id);
                const base = this._localDevices ?? this.devices;
                const byId = new Map(base.map((d) => [d.id, d]));
                const reordered = ids
                    .map((id) => byId.get(id))
                    .filter((d): d is DeviceSummary => !!d);
                if (reordered.length !== base.length) return;
                this._localDevices = reordered;
                this._devicesSortable?.destroy();
                this._devicesSortable = null;
                for (const el of Array.from(
                    grid.querySelectorAll(".device-card, .expanded-detail"),
                )) {
                    el.remove();
                }
                this._devicesVersion++;
                this._scheduleDevicesSave(reordered.map((d) => d.id));
            },
        });
    }

    private _scheduleDevicesSave(deviceIds: string[]): void {
        if (this._pendingDevicesSave !== null) clearTimeout(this._pendingDevicesSave);
        this._pendingDevicesSave = window.setTimeout(async () => {
            this._pendingDevicesSave = null;
            if (!this.api) return;
            try {
                await this.api.reorderDevices(deviceIds);
            } catch {
                // Backend rejected (stale set). Force a parent refresh to
                // resync the canonical order.
                this.dispatchEvent(
                    new CustomEvent("device-changed", {
                        bubbles: true,
                        composed: true,
                    }),
                );
            }
        }, REORDER_DEBOUNCE_MS);
    }

    private async _loadExpandedDevice(): Promise<void> {
        // The trigger drawer's sentinel id shares the parent's expand-one
        // -at-a-time slot but isn't a real device -- ``getDevice`` would
        // 404 on it. ``_loadTriggerDrawer`` (called separately, see
        // ``updated()``) handles that case.
        if (
            !this.expandedDeviceId ||
            this.expandedDeviceId === TRIGGER_DRAWER_ID ||
            !this.api
        ) {
            this._expandedDevice = null;
            return;
        }
        try {
            this._expandedDevice = await this.api.getDevice(this.expandedDeviceId);
        } catch {
            this._expandedDevice = null;
        }
    }

    private async _onExpandedDeviceChanged(): Promise<void> {
        await this._loadExpandedDevice();
        this.dispatchEvent(
            new CustomEvent("device-changed", { bubbles: true, composed: true }),
        );
    }

    private _onExpandedDeviceDeleted(): void {
        this.dispatchEvent(
            new CustomEvent("device-deleted", { bubbles: true, composed: true }),
        );
    }

    /**
     * Apply a command-order change reported by the child detail view.
     *
     * Updates the cached ``_expandedDevice`` synchronously so the next
     * render passes the new order back down. Skips the full re-fetch
     * round-trip we do on ``device-changed`` because the child already
     * has authoritative local state for this mutation -- and because
     * the server save is debounced and asynchronous, a fetch here would
     * race with the user's in-flight reorder.
     */
    private _onCommandsReordered(ev: CustomEvent): void {
        if (!this._expandedDevice) return;
        const commands = ev.detail?.commands;
        if (!Array.isArray(commands)) return;
        this._expandedDevice = {
            ...this._expandedDevice,
            commands,
        };
    }

    private _onCollapse(): void {
        this.dispatchEvent(
            new CustomEvent("device-selected", {
                detail: this.expandedDeviceId,
                bubbles: true,
                composed: true,
            }),
        );
    }

    private async _discoverHardware(): Promise<void> {
        // Fetch native receiver entity IDs so we can exclude them from emitters.
        const receiverEntityIds = new Set<string>();
        if (this.api) {
            try {
                const receivers = await this.api.listReceivers();
                for (const r of receivers) {
                    receiverEntityIds.add(r.entity_id);
                }
                // Keep the full list too -- ir-trigger-row's scope chip
                // resolves receiver_entity_ids to friendly names from it.
                // (Previously this method only kept the id Set for the
                // emitter-exclusion check below and threw the names away.)
                this._receivers = receivers;
            } catch {
                // Pre-2026.6 or non-fatal error.
            }
        }

        // Emitters from hass.states (exclude receiver entities)
        const states = (this.hass?.states ?? {}) as Record<
            string,
            {
                entity_id: string;
                attributes: { friendly_name?: string; hair_observer?: boolean };
            }
        >;
        const emitters: { entity_id: string; name: string }[] = [];
        for (const [entityId, st] of Object.entries(states)) {
            if (
                entityId.startsWith("infrared.") &&
                !receiverEntityIds.has(entityId) &&
                !st.attributes.hair_observer
            ) {
                emitters.push({
                    entity_id: entityId,
                    name: st.attributes.friendly_name ?? entityId,
                });
            }
        }
        this._emitters = emitters;

        // Capture providers (RX hardware) from API
        if (this.api) {
            try {
                this._captureProviders = await this.api.listCaptureProviders();
            } catch {
                // Non-fatal
            }
        }

        // Pluckable blasters (vendor IR blasters HAIR can pull codes from).
        if (this.api) {
            try {
                const { vendors } = await this.api.listPluckVendors();
                const blasters: {
                    integration: string;
                    entity_id: string;
                    name: string;
                    vendorName: string;
                }[] = [];
                for (const v of vendors) {
                    for (const b of v.blasters) {
                        blasters.push({
                            integration: v.integration,
                            entity_id: b.entity_id,
                            name: b.name,
                            vendorName: v.name,
                        });
                    }
                }
                this._pluckBlasters = blasters;
            } catch {
                this._pluckBlasters = [];
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

    private _openInPlucker(entityId: string): void {
        this.dispatchEvent(
            new CustomEvent("navigate-plucker", {
                detail: { vendor_entity_id: entityId },
                bubbles: true,
                composed: true,
            }),
        );
    }

    // --- Device corner actions (duplicate + delete) ---

    private _openDuplicateDialog(device: DeviceSummary, e: Event): void {
        e.stopPropagation();
        this._duplicateTarget = device;
    }

    private _closeDuplicateDialog(): void {
        this._duplicateTarget = null;
    }

    private _onDeviceDuplicated(): void {
        // Tell the parent panel to refresh its device list. The duplicate
        // already lives in storage server-side; the parent owns the list.
        this._duplicateTarget = null;
        this.dispatchEvent(
            new CustomEvent("device-changed", { bubbles: true, composed: true }),
        );
    }

    private _requestDeleteDevice(device: DeviceSummary, e: Event): void {
        e.stopPropagation();
        this._confirmDeleteDevice = device;
    }

    private async _doDeleteDevice(): Promise<void> {
        if (!this._confirmDeleteDevice || !this.api) return;
        const device = this._confirmDeleteDevice;
        this._confirmDeleteDevice = null;
        try {
            await this.api.deleteDevice(device.id);
            this.dispatchEvent(
                new CustomEvent("device-deleted", { bubbles: true, composed: true }),
            );
        } catch {
            // Non-fatal; parent refresh will reconcile.
        }
    }

    private _navigateIntegration(domain: string) {
        const url = `/config/integrations/integration/${domain}`;
        window.history.pushState(null, "", url);
        window.dispatchEvent(new PopStateEvent("popstate"));
    }

    // --- Triggers ---

    /**
     * Number of trigger remotes (drawers). Always 1 today -- HAIR only
     * supports the single "HAIR Triggers" drawer for now -- but the
     * header counts remotes, not the triggers living inside them, so
     * this becomes meaningful the moment multi-drawer support ships
     * (owner ruling 2026-08-14: "each remote card has their own
     * numbered triggers on it").
     */
    private get _triggerDrawerCount(): number {
        return 1;
    }

    private async _loadTriggers(): Promise<void> {
        if (!this.api) return;
        try {
            this._triggers = await this.api.listTriggers();
        } catch {
            // Non-fatal.
        }
    }

    private async _subscribeTriggerFired(): Promise<void> {
        if (!this.api) return;
        try {
            this._unsubTriggerFired = await this.api.subscribeTriggerFired(
                (ev: TriggerFiredEvent) => {
                    // Glow the collapsed drawer card and the fired row alike
                    // (BloomTracker's sequence numbering is what fixes the
                    // v0.7.2 repeat-fire-cut-short bug -- see
                    // ir-bloom-styles.ts's module doc).
                    this._bloomTracker.trigger(
                        ev.trigger_id,
                        () => {
                            this._glowTriggerIds = new Set([
                                ...this._glowTriggerIds,
                                ev.trigger_id,
                            ]);
                        },
                        () => {
                            const next = new Set(this._glowTriggerIds);
                            next.delete(ev.trigger_id);
                            this._glowTriggerIds = next;
                        },
                    );
                    // Bump the trigger's own fire_count/last_fired_at
                    // optimistically so the row's aliveness phrase updates
                    // without waiting on a full _loadTriggers() round-trip.
                    this._triggers = this._triggers.map((t) =>
                        t.id === ev.trigger_id
                            ? {
                                  ...t,
                                  fire_count: t.fire_count + 1,
                                  last_fired_at: new Date().toISOString(),
                              }
                            : t,
                    );
                },
            );
        } catch {
            // Non-fatal.
        }
    }

    private async _unsubscribeTriggerFired(): Promise<void> {
        if (this._unsubTriggerFired) {
            await this._unsubTriggerFired();
            this._unsubTriggerFired = null;
        }
    }

    private _openEditTrigger(trigger: IRTrigger, e?: Event): void {
        e?.stopPropagation();
        this._editTrigger = trigger;
    }

    private _closeEditTrigger(): void {
        this._editTrigger = null;
    }

    private async _onTriggerUpdated(): Promise<void> {
        this._editTrigger = null;
        await this._loadTriggers();
    }

    private async _toggleTriggerEnabled(trigger: IRTrigger, e?: Event): Promise<void> {
        e?.stopPropagation();
        try {
            await this.api!.updateTrigger(trigger.id, {
                enabled: !trigger.enabled,
            });
            await this._loadTriggers();
        } catch {
            // Non-fatal.
        }
    }

    private _requestDeleteTrigger(trigger: IRTrigger, e?: Event): void {
        e?.stopPropagation();
        this._confirmDeleteTrigger = trigger;
    }

    private async _doDeleteTrigger(): Promise<void> {
        if (!this._confirmDeleteTrigger) return;
        const trigger = this._confirmDeleteTrigger;
        this._confirmDeleteTrigger = null;
        try {
            await this.api!.deleteTrigger(trigger.id);
            await this._loadTriggers();
        } catch {
            // Non-fatal.
        }
    }

    /** ``rename-trigger`` from an ``<ir-trigger-row>`` -- rides the same
     *  ``updateTrigger`` patch path the edit dialog uses (device_trigger.py's
     *  alias-history tolerance already covers a plain name patch). */
    private async _onRenameTrigger(
        ev: CustomEvent<{ trigger: IRTrigger; name: string }>,
    ): Promise<void> {
        const { trigger, name } = ev.detail;
        if (!this.api) return;
        try {
            await this.api.updateTrigger(trigger.id, { name });
            await this._loadTriggers();
        } catch {
            // Non-fatal; the row reverts to the server-confirmed name on
            // the next render since it reads straight off this._triggers.
        }
    }

    // --- HAIR Triggers drawer identity (name + go-to-HA link) ---

    private async _loadTriggerDrawer(): Promise<void> {
        if (!this.api) {
            this._triggerDrawer = null;
            return;
        }
        try {
            this._triggerDrawer = await this.api.getTriggerDrawer();
        } catch {
            this._triggerDrawer = null;
        }
    }

    private _startEditDrawerName(e: Event): void {
        e.stopPropagation();
        if (this._drawerBusy || !this._triggerDrawer) return;
        this._draftDrawerName = this._triggerDrawer.name;
        this._editingDrawerName = true;
        void this.updateComplete.then(() => {
            const input = this.renderRoot.querySelector<HTMLInputElement>(
                ".drawer-name-input",
            );
            input?.focus();
            input?.select();
        });
    }

    private async _saveDrawerName(): Promise<void> {
        if (!this._editingDrawerName) return;
        const name = this._draftDrawerName.trim();
        this._editingDrawerName = false;
        if (!name || !this.api || name === this._triggerDrawer?.name) return;
        this._drawerBusy = true;
        try {
            this._triggerDrawer = await this.api.renameTriggerDrawer(name);
        } catch {
            // Non-fatal; keeps the prior drawer name displayed.
        } finally {
            this._drawerBusy = false;
        }
    }

    private _onDrawerNameKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            e.preventDefault();
            void this._saveDrawerName();
        } else if (e.key === "Escape") {
            this._editingDrawerName = false;
        }
    }

    // --- Trigger row drag reorder (grip handle, mirrors
    //     ir-device-detail.ts's command-reorder pattern) ---

    private _syncTriggerSortable(): void {
        const list = this.renderRoot.querySelector(
            ".trigger-rows",
        ) as HTMLElement | null;
        if (list && !this._triggerSortable) {
            this._attachTriggerSortable(list);
        } else if (!list && this._triggerSortable) {
            this._triggerSortable.destroy();
            this._triggerSortable = null;
        }
    }

    private _attachTriggerSortable(list: HTMLElement): void {
        this._triggerSortable = Sortable.create(list, {
            handle: ".grip-handle",
            animation: 150,
            ghostClass: "sortable-ghost",
            onEnd: (e) => {
                const oldIndex = e.oldIndex;
                const newIndex = e.newIndex;
                if (
                    oldIndex === undefined ||
                    newIndex === undefined ||
                    oldIndex === newIndex
                ) {
                    return;
                }
                const triggers = [...this._triggers];
                const [moved] = triggers.splice(oldIndex, 1);
                triggers.splice(newIndex, 0, moved);
                this._triggers = triggers;

                // Tear down and let ``updated()`` re-attach against a
                // fresh ``.trigger-rows`` DOM tree, same discipline as
                // ir-device-detail.ts's command reorder -- avoids
                // SortableJS leaving the dragged row outside keyed()'s
                // managed range after the rebuild.
                this._triggerSortable?.destroy();
                this._triggerSortable = null;
                const container = this.renderRoot.querySelector(
                    ".trigger-rows",
                );
                if (container) {
                    for (const row of Array.from(
                        container.querySelectorAll("ir-trigger-row"),
                    )) {
                        row.remove();
                    }
                }
                this._triggerRowsVersion++;
                this._scheduleTriggerReorderSave(triggers.map((t) => t.id));
            },
        });
    }

    private _scheduleTriggerReorderSave(triggerIds: string[]): void {
        if (this._pendingTriggerReorderSave !== null) {
            clearTimeout(this._pendingTriggerReorderSave);
        }
        this._pendingTriggerReorderSave = window.setTimeout(async () => {
            this._pendingTriggerReorderSave = null;
            if (!this.api) return;
            try {
                await this.api.reorderTriggers(triggerIds);
            } catch {
                // Backend rejected (stale set) -- resync from server.
                await this._loadTriggers();
            }
        }, REORDER_DEBOUNCE_MS);
    }

    private _emitterIntegrationDomain(entityId: string): string {
        const entityReg = this.hass?.entities?.[entityId];
        if (entityReg?.platform) return entityReg.platform;
        return entityId.split(".")[0];
    }

    /** Device-registry IDs that have an emitter entity (TX capable). */
    private _getEmitterDeviceIds(): Set<string> {
        const ids = new Set<string>();
        for (const em of this._emitters) {
            const reg = this.hass?.entities?.[em.entity_id];
            if (reg?.device_id) ids.add(reg.device_id);
        }
        return ids;
    }

    /** Group emitter entity_ids by their HA device_id. */
    private _getEmitterEntityIdsByDevice(): Map<string, string[]> {
        const byDevice = new Map<string, string[]>();
        for (const em of this._emitters) {
            const reg = this.hass?.entities?.[em.entity_id];
            const deviceId = reg?.device_id;
            if (!deviceId) continue;
            const list = byDevice.get(deviceId) ?? [];
            list.push(em.entity_id);
            byDevice.set(deviceId, list);
        }
        return byDevice;
    }

    /** Detect HA versions older than 2026.6 (no native InfraredReceiverEntity). */
    private _isPre2026_6(): boolean {
        const v: string | undefined = this.hass?.config?.version;
        if (!v) return false;
        const m = v.match(/^(\d+)\.(\d+)/);
        if (!m) return false;
        const major = parseInt(m[1], 10);
        const minor = parseInt(m[2], 10);
        return major < 2026 || (major === 2026 && minor < 6);
    }

    /** Resolve integration domain for navigation. */
    private _resolveNavType(
        cp: CaptureProviderInfo,
        nativeEntityId: string | undefined,
    ): string {
        if (cp.type === "native" && nativeEntityId) {
            const platform = this.hass?.entities?.[nativeEntityId]?.platform;
            if (platform) return platform;
            // Fall back to esphome -- by far the most common source of
            // InfraredReceiverEntity in the wild.
            return "esphome";
        }
        return cp.type;
    }

    /**
     * Classify capture providers, merging native + bridge entries for the
     * same physical HA device into one entry with both flags set.
     *
     * Receivers = every capture-capable device.
     * Proxies   = subset that also has an emitter on the same HA device.
     * A TX+RX device shows in both sections by design (each section answers
     * a different question; same hardware legitimately answers both).
     */
    private _classifyHardware(): {
        receivers: MergedHardwareEntry[];
        proxies: MergedHardwareEntry[];
    } {
        const txByDevice = this._getEmitterEntityIdsByDevice();
        const txDeviceIds = new Set(txByDevice.keys());
        const byDeviceId = new Map<string, MergedHardwareEntry>();

        for (const cp of this._captureProviders) {
            // For native providers the backend stashes the entity_id in
            // ``cp.device_id``; the real HA device-registry ID has to be
            // looked up via ``hass.entities``.
            let haDeviceId: string | undefined;
            let nativeEntityId: string | undefined;
            if (cp.type === "native") {
                nativeEntityId = cp.receiver_entity_id ?? cp.device_id;
                haDeviceId = this.hass?.entities?.[nativeEntityId]?.device_id;
                // Fallback: use the entity_id as a synthetic merge key so
                // the card still shows even if the entity isn't registered.
                if (!haDeviceId) haDeviceId = nativeEntityId;
            } else {
                haDeviceId = cp.device_id;
            }
            if (!haDeviceId) continue;

            const existing = byDeviceId.get(haDeviceId);
            const entry: MergedHardwareEntry = existing ?? {
                device_id: haDeviceId,
                name: cp.name,
                nav_type: this._resolveNavType(cp, nativeEntityId),
                has_native: false,
                has_bridge: false,
                has_tx: txDeviceIds.has(haDeviceId),
                tx_entity_ids: txByDevice.get(haDeviceId) ?? [],
            };
            if (cp.type === "native") {
                entry.has_native = true;
                entry.native_entity_id = nativeEntityId;
            } else {
                // ESPHome event-bus bridge or Broadlink learn mode.
                entry.has_bridge = true;
                // Prefer the bridge's device-registry name (cleaner) and
                // its concrete integration domain over any native default.
                entry.name = cp.name;
                entry.nav_type = cp.type;
            }
            byDeviceId.set(haDeviceId, entry);
        }

        const merged = Array.from(byDeviceId.values());
        const proxies = merged.filter((e) => e.has_tx);
        return { receivers: merged, proxies };
    }

    /** Render TX/RX-NATIVE / RX-BRIDGE badges with a pre-2026.6 upgrade hint. */
    private _renderRxBadges(entry: MergedHardwareEntry) {
        const showGrayedNative =
            !entry.has_native && entry.has_bridge && this._isPre2026_6();
        return html`
            ${entry.has_native
                ? html`<span
                      class="badge rx-native"
                      title=${t("devlist.rx_native_title")}
                  >RX-NATIVE</span>`
                : nothing}
            ${entry.has_bridge
                ? html`<span
                      class="badge rx-bridge"
                      title=${entry.has_native
                          ? t("devlist.rx_bridge_active")
                          : t("devlist.rx_bridge_title")}
                  >RX-BRIDGE</span>`
                : nothing}
            ${showGrayedNative
                ? html`<span
                      class="badge rx-native-disabled"
                      title=${t("devlist.rx_upgrade_title")}
                  >RX-NATIVE</span>`
                : nothing}
        `;
    }

    render() {
        if (this.loading) {
            return html`<div class="loading">${t("devlist.loading")}</div>`;
        }

        const devices = this._localDevices ?? this.devices;
        const hasDevices = devices.length > 0;
        const hasEmitters = this._emitters.length > 0;
        const { receivers, proxies } = this._classifyHardware();
        const hasReceivers = receivers.length > 0;
        const hasProxies = proxies.length > 0;
        const hasNothing = !hasDevices && !hasEmitters && !hasReceivers && !hasProxies;

        if (hasNothing) {
            return html`
                <ha-card class="empty">
                    <h2>${t("devlist.empty_title")}</h2>
                    <p>${t("devlist.empty_sub")}</p>
                    <mwc-button raised @click=${this._add}>${t("devlist.add_device_plus")}</mwc-button>
                </ha-card>
            `;
        }

        return html`
            <!-- Devices -->
            <div class="toolbar">
                <span class="toolbar-title">
                    <ha-svg-icon .path=${ICON_DEVICES}></ha-svg-icon>
                    ${t("devlist.title")}
                    <span class="toolbar-count">(${this.devices.length})</span>
                </span>
                <button class="add-btn" @click=${this._add}>
                    ${t("devlist.add_device_plus")}
                </button>
            </div>
            ${hasDevices
                ? html`
                      <div class="grid device-grid">
                          ${keyed(
                              this._devicesVersion,
                              repeat(
                                  devices,
                                  (device) => device.id,
                                  (device) => html`
                                  <div
                                      class="card device-card ${device.id === this.expandedDeviceId ? "expanded" : ""}"
                                      data-id=${device.id}
                                      tabindex="0"
                                      @click=${() => this._select(device.id)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._select(device.id);
                                          }
                                      }}
                                  >
                                      <button
                                          class="card-action duplicate-action"
                                          title=${t("dup.heading")}
                                          @click=${(e: Event) =>
                                              this._openDuplicateDialog(device, e)}
                                      >
                                          <ha-svg-icon .path=${ICON_COPY}></ha-svg-icon>
                                      </button>
                                      <button
                                          class="card-action delete-action"
                                          title=${t("devlist.delete_device")}
                                          @click=${(e: Event) =>
                                              this._requestDeleteDevice(device, e)}
                                      >
                                          <ha-svg-icon
                                              .path=${ICON_TRASH}
                                              .viewBox=${TRASH_VIEWBOX}
                                          ></ha-svg-icon>
                                      </button>
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
                                              t(
                                                  DEVICE_TYPE_LABEL_KEYS[
                                                      device.device_type
                                                  ],
                                              ),
                                          ]
                                              .filter(Boolean)
                                              .join(" • ")}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge cmd-badge">
                                              ${t("devlist.cmd_badge", { count: device.command_count })}
                                          </span>
                                          ${device.emitter_entity_ids.length > 0
                                              ? html`<span class="badge tx-badge">${t("devlist.tx_badge", { count: device.emitter_entity_ids.length })}</span>`
                                              : html`<span class="badge no-tx-badge">${t("devlist.no_tx")}</span>`}
                                      </div>
                                  </div>
                                  ${device.id === this.expandedDeviceId && this._expandedDevice
                                      ? html`
                                            <div class="expanded-detail">
                                                <ir-device-detail
                                                    .api=${this.api}
                                                    .device=${this._expandedDevice}
                                                    .hass=${this.hass}
                                                    @device-changed=${this._onExpandedDeviceChanged}
                                                    @device-deleted=${this._onExpandedDeviceDeleted}
                                                    @commands-reordered=${this._onCommandsReordered}
                                                    @trigger-changed=${this._loadTriggers}
                                                    @collapse=${this._onCollapse}
                                                ></ir-device-detail>
                                            </div>
                                        `
                                      : nothing}
                              `,
                              ),
                          )}
                      </div>
                  `
                : html`
                      <div class="empty-devices">
                          No devices yet. Sniff some signals, then add your first device.
                      </div>
                  `}

            <!-- Trigger Remotes: one HAIR Triggers drawer card, same size as
                 a collapsed device card (owner bench ruling), expanding via
                 the same expandedDeviceId/device-selected slot a device
                 card uses (TRIGGER_DRAWER_ID sentinel). Renders even at
                 zero triggers -- the drawer itself is a permanent fixture,
                 not conditional on having any remotes captured yet; the
                 expanded view's own empty state (trow.empty_state) covers
                 that case instead of hiding the section. -->
            <div class="toolbar trigger-toolbar">
                <span class="toolbar-title trigger-toolbar-title">
                    <ha-svg-icon .path=${ICON_DEVICES}></ha-svg-icon>
                    ${t("devlist.trigger_remotes_title")}
                    <span class="toolbar-count">(${this._triggerDrawerCount})</span>
                </span>
            </div>
            <div class="grid">
                <div
                    class="card trigger-drawer-card ${this.expandedDeviceId === TRIGGER_DRAWER_ID ? "expanded" : ""} ${this._glowTriggerIds.size > 0 ? "bloom" : ""}"
                    tabindex="0"
                    @click=${() => this._select(TRIGGER_DRAWER_ID)}
                    @keydown=${(e: KeyboardEvent) => {
                        if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            this._select(TRIGGER_DRAWER_ID);
                        }
                    }}
                >
                    <div class="card-header">
                        <ha-svg-icon class="trigger-icon" .path=${ICON_TRIGGER}></ha-svg-icon>
                        <div class="card-name">
                            ${this._triggerDrawer?.name ?? t("devlist.trigger_drawer_default_name")}
                        </div>
                    </div>
                    <div class="card-meta">
                        ${tp("trow.header_count", this._triggers.length)}
                    </div>
                </div>
                ${this.expandedDeviceId === TRIGGER_DRAWER_ID
                    ? html`
                          <div class="expanded-detail trigger-drawer-detail">
                              <section class="header trh-header">
                                  <div class="header-left">
                                      <div class="name-row">
                                          ${this._editingDrawerName
                                              ? html`
                                                    <input
                                                        class="name-input drawer-name-input"
                                                        type="text"
                                                        .value=${this._draftDrawerName}
                                                        @input=${(e: Event) =>
                                                            (this._draftDrawerName = (
                                                                e.target as HTMLInputElement
                                                            ).value)}
                                                        @blur=${this._saveDrawerName}
                                                        @keydown=${this._onDrawerNameKeydown}
                                                        ?disabled=${this._drawerBusy}
                                                    />
                                                `
                                              : html`
                                                    <h1
                                                        class="editable-name"
                                                        @click=${this._startEditDrawerName}
                                                        title=${t("cmdrow.rename")}
                                                    >
                                                        ${this._triggerDrawer?.name ?? t("devlist.trigger_drawer_default_name")}
                                                        <span class="edit-icon">&#9998;</span>
                                                    </h1>
                                                `}
                                          ${this._triggerDrawer?.ha_device_id
                                              ? renderExitToEntityBtn(
                                                    `/config/devices/device/${this._triggerDrawer.ha_device_id}`,
                                                    t("devices.open_in_ha"),
                                                )
                                              : nothing}
                                      </div>
                                      <div class="trh-subtitle">
                                          ${tp("trow.header_count", this._triggers.length)}
                                      </div>
                                  </div>
                                  <button
                                      class="collapse-btn"
                                      @click=${() => this._select(TRIGGER_DRAWER_ID)}
                                      title=${t("common.close")}
                                  >&#x2715;</button>
                              </section>
                              ${this._triggers.length > 0
                                  ? html`
                                        <div class="trigger-rows">
                                            ${keyed(
                                                this._triggerRowsVersion,
                                                repeat(
                                                    this._triggers,
                                                    (trig) => trig.id,
                                                    (trig) => html`
                                                        <ir-trigger-row
                                                            .trigger=${trig}
                                                            .receivers=${this._receivers}
                                                            .bloom=${this._glowTriggerIds.has(trig.id)}
                                                            @rename-trigger=${this._onRenameTrigger}
                                                            @toggle-enabled=${(ev: CustomEvent) =>
                                                                this._toggleTriggerEnabled(ev.detail.trigger, ev)}
                                                            @edit-trigger=${(ev: CustomEvent) =>
                                                                this._openEditTrigger(ev.detail.trigger, ev)}
                                                            @delete-trigger=${(ev: CustomEvent) =>
                                                                this._requestDeleteTrigger(ev.detail.trigger, ev)}
                                                        >
                                                            <ha-svg-icon
                                                                slot="grip"
                                                                class="grip-handle"
                                                                .path=${ICON_GRIP}
                                                            ></ha-svg-icon>
                                                        </ir-trigger-row>
                                                    `,
                                                ),
                                            )}
                                        </div>
                                    `
                                  : html`<div class="trigger-drawer-empty">${t("trow.empty_state")}</div>`}
                          </div>
                      `
                    : nothing}
            </div>

            <!-- Blasters (Pluckable) -- vendor IR blasters HAIR can pull from -->
            ${this._pluckBlasters.length > 0
                ? html`
                      <div class="section-header">
                          <h2>${t("devlist.blasters")}</h2>
                          <span class="section-count"
                              >${this._pluckBlasters.length}</span
                          >
                      </div>
                      <div class="grid">
                          ${this._pluckBlasters.map(
                              (b) => html`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      title=${t("devlist.open_plucker_title")}
                                      @click=${() => this._openInPlucker(b.entity_id)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._openInPlucker(b.entity_id);
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${ICON_BLASTER}></ha-svg-icon>
                                          <div class="card-name">
                                              ${b.vendorName}: ${b.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">${b.entity_id}</div>
                                      <div class="card-footer">
                                          <span class="badge pluck-badge"
                                              >${t("devlist.open_plucker")}</span
                                          >
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            <!-- Emitters -->
            ${hasEmitters
                ? html`
                      <div class="section-header">
                          <h2>${t("devlist.emitters")}</h2>
                          <span class="section-count">${this._emitters.length}</span>
                      </div>
                      <div class="grid">
                          ${this._emitters.map(
                              (em) => html`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${() =>
                                          this._navigateIntegration(
                                              this._emitterIntegrationDomain(em.entity_id),
                                          )}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._navigateIntegration(
                                                  this._emitterIntegrationDomain(em.entity_id),
                                              );
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${ICON_EMITTER}></ha-svg-icon>
                                          <div class="card-name">${em.name}</div>
                                      </div>
                                      <div class="card-meta">${em.entity_id}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title=${t("devlist.tx_native_title")}
                                          >TX-NATIVE</span>
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            <!-- Receivers (capture-capable hardware; proxies appear here too by design) -->
            ${hasReceivers
                ? html`
                      <div class="section-header">
                          <h2>${t("devlist.receivers")}</h2>
                          <span class="section-count">${receivers.length}</span>
                      </div>
                      <div class="grid">
                          ${receivers.map(
                              (entry) => html`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${() => this._navigateIntegration(entry.nav_type)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._navigateIntegration(entry.nav_type);
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${ICON_RECEIVER}></ha-svg-icon>
                                          <div class="card-name">${entry.name}</div>
                                      </div>
                                      <div class="card-meta">${entry.native_entity_id ?? entry.nav_type}</div>
                                      <div class="card-footer">
                                          ${this._renderRxBadges(entry)}
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            <!-- Proxies (TX + RX hardware) -->
            ${hasProxies
                ? html`
                      <div class="section-header">
                          <h2>${t("devlist.proxies")}</h2>
                          <span class="section-count">${proxies.length}</span>
                      </div>
                      <div class="grid">
                          ${proxies.map(
                              (entry) => html`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${() => this._navigateIntegration(entry.nav_type)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._navigateIntegration(entry.nav_type);
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${ICON_PROXY}></ha-svg-icon>
                                          <div class="card-name">${entry.name}</div>
                                      </div>
                                      ${entry.tx_entity_ids[0]
                                          ? html`<div class="card-meta">${entry.tx_entity_ids[0]}</div>`
                                          : nothing}
                                      <div class="card-meta">${entry.native_entity_id ?? entry.nav_type}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title=${t("devlist.tx_native_title")}
                                          >TX-NATIVE</span>
                                          ${this._renderRxBadges(entry)}
                                      </div>
                                  </div>
                              `,
                          )}
                      </div>
                  `
                : nothing}

            ${this._editTrigger
                ? html`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._editTrigger}
                          @trigger-saved=${this._onTriggerUpdated}
                          @closed=${this._closeEditTrigger}
                      ></ir-trigger-dialog>
                  `
                : nothing}

            ${this._confirmDeleteTrigger
                ? html`
                      <ir-confirm-dialog
                          title=${t("mirror.del_trigger_title")}
                          message=${t("devlist.del_trigger_msg", { name: this._confirmDeleteTrigger.name })}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${() => (this._confirmDeleteTrigger = null)}
                      ></ir-confirm-dialog>
                  `
                : nothing}

            ${this._duplicateTarget && this.api
                ? html`
                      <ir-duplicate-device-dialog
                          .api=${this.api}
                          .sourceId=${this._duplicateTarget.id}
                          .sourceName=${this._duplicateTarget.name}
                          @device-duplicated=${this._onDeviceDuplicated}
                          @closed=${this._closeDuplicateDialog}
                      ></ir-duplicate-device-dialog>
                  `
                : nothing}

            ${this._confirmDeleteDevice
                ? html`
                      <ir-confirm-dialog
                          title=${t("devlist.del_device_title")}
                          message=${t("devlist.del_device_msg", { name: this._confirmDeleteDevice.name })}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._doDeleteDevice}
                          @closed=${() => (this._confirmDeleteDevice = null)}
                      ></ir-confirm-dialog>
                  `
                : nothing}
        `;
    }

    static styles = [
        exitToEntityButtonStyles,
        bloomStyles,
        css`
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

        .empty-devices {
            text-align: center;
            padding: 24px 16px;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
            margin-bottom: 16px;
        }

        /* --- Devices toolbar (matches sniffer) --- */
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .toolbar-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .toolbar-title ha-svg-icon {
            --mdc-icon-size: 24px;
            /* Devices wears the device green: the same #2e7d32 as the
               expanded-card stroke and the Assign chip (owner ruling,
               2026-07-20 -- green = device-ward, everywhere). */
            color: #2e7d32;
        }
        .add-btn {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: none;
            color: #2e7d32;
            border: 1px solid #2e7d32;
            border-radius: 4px;
            /* Chip metrics, matching the Clipper's Add Remote exactly
               (owner bench find: this one ran a size larger). */
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .add-btn ha-svg-icon {
            --mdc-icon-size: 18px;
        }
        .add-btn:hover {
            background: rgba(46, 125, 50, 0.08);
        }
        .toolbar-count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        /* Trigger Remotes' own toolbar -- same treatment as the devices
           toolbar above (icon + title + count), gold instead of device
           green, with the section boundary itself living here as a
           border-top (owner ruling 2026-08-14: the line caps off
           Controlled Devices, the header sits below it, not the other
           way around). */
        .trigger-toolbar {
            border-top: 2px solid var(--divider-color);
            padding-top: 20px;
            margin: 24px 0 16px;
        }
        .trigger-toolbar-title ha-svg-icon {
            color: #d4a017;
        }

        /* --- Section headers (neutral) --- */
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
            color: var(--secondary-text-color);
        }
        .section-count {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 4px;
            background: var(--secondary-background-color);
            color: var(--secondary-text-color);
        }

        /* --- Card grid (compact) --- */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 12px;
        }

        /* --- Shared card styles (neutral, sniffer palette) --- */
        .card {
            padding: 12px;
            cursor: pointer;
            border-radius: 8px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .card:hover,
        .card:focus-visible {
            background: var(--secondary-background-color);
            outline: none;
        }
        .card-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-header ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            /* Long card names (eg the Athom proxy transmitter title) can
               otherwise squeeze the flex item below its intrinsic size. */
            flex-shrink: 0;
        }
        .card-name {
            font-size: 0.95rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            /* Ellipsize ~2 characters earlier so a full-width name never
               runs under the corner glyph (owner catch, 2026-07-20: the
               duplicate glyph zone reaches 27px in from the card edge,
               the card's own padding only 12px). */
            padding-right: 16px;
        }
        .card-meta {
            margin-top: 6px;
            margin-left: 35px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-footer {
            margin-top: 8px;
            margin-left: 32px;
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .badge {
            border-radius: 4px;
            padding: 2px 4px;
            font-size: 0.72rem;
            font-weight: 500;
            line-height: 1;
        }

        /* Command count badge (green) */
        .cmd-badge {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }

        /* TX badge (amber text, dark bg) */
        .tx-badge {
            background: var(--secondary-background-color);
            color: #ff9800;
        }

        /* RX badge (blue text, dark bg) */
        .rx-badge {
            background: var(--secondary-background-color);
            color: var(--primary-color, #2196f3);
        }

        /* No TX warning (muted) */
        .no-tx-badge {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            font-style: italic;
        }

        /* Hardware section badges -- consistent <direction>-<source> pattern. */
        /* TX-NATIVE and RX-NATIVE share the green palette of .cmd-badge. */
        .tx-native,
        .rx-native {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }
        /* RX-BRIDGE uses HAIR's existing orange. */
        .rx-bridge {
            background: rgba(255, 152, 0, 0.15);
            color: #ff9800;
        }
        /* Pre-2026.6 upgrade hint: grayed RX-NATIVE alongside RX-BRIDGE. */
        .rx-native-disabled {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            opacity: 0.6;
            cursor: help;
        }

        /* --- Expanded detail row --- */
        .expanded-detail {
            grid-column: 1 / -1;
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            padding: 16px;
            animation: expand-in 200ms ease;
        }
        @keyframes expand-in {
            from { opacity: 0; transform: translateY(-8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* --- Device card expanded highlight --- */
        .device-card {
            position: relative;
        }
        .device-card.expanded {
            border-color: #2e7d32;
            box-shadow: 0 0 0 1px #2e7d32;
        }
        /* SortableJS marks the card being dragged. */
        .device-card.sortable-ghost {
            opacity: 0.4;
        }
        .device-card.sortable-chosen {
            cursor: grabbing;
        }

        /* --- Card corner actions (duplicate top-right, delete bottom-right) --- */
        .card-action {
            position: absolute;
            background: transparent;
            border: none;
            padding: 4px;
            border-radius: 4px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 120ms ease, color 120ms ease, opacity 120ms ease;
        }
        .card-action ha-svg-icon {
            /* Default card-action glyph size. The duplicate-action overrides
               this with a smaller value because the copy MDI glyph fills more
               of its viewbox than the trash glyph. */
            --mdc-icon-size: 16px;
        }
        .duplicate-action {
            top: 6px;
            right: 6px;
            color: var(--disabled-text-color, #999);
            opacity: 0;
        }
        /* Hidden until the card itself is hovered or has focus within
           (keyboard users tabbing onto the card or its children) --
           always-visible at rest read as busy (owner catch
           2026-08-14). */
        .device-card:hover .duplicate-action,
        .device-card:focus-within .duplicate-action,
        .device-card:hover .delete-action,
        .device-card:focus-within .delete-action {
            opacity: 0.55;
        }
        .duplicate-action ha-svg-icon {
            /* Copy MDI glyph fills more of its viewbox than the trash glyph,
               so render it smaller to land at the same visual size as the
               trash icon in the opposite corner. */
            --mdc-icon-size: 13px;
        }
        .duplicate-action:hover {
            color: var(--primary-text-color);
            opacity: 1;
        }
        .delete-action {
            bottom: 6px;
            right: 6px;
            color: var(--disabled-text-color, #999);
            opacity: 0;
        }
        /* EMBER, not material red (owner ruling 2026-08-03). Ember is
           already the panel's delete colour on every text chip, and the
           trash sweep put it on nine more cans; these two shipped in
           red and were suddenly the odd ones out. Two conventions for
           the same act is the exact failure the ruling avoids. */
        .delete-action:hover {
            background: rgba(230, 81, 0, 0.12);
            color: #e65100;
            opacity: 1;
        }

        /* --- Hardware cards inherit shared .card styles --- */
        .hw-card {
            /* Neutral -- no per-section color backgrounds */
        }
        /* "Open in Plucker" badge -- standard badge form, no stroke. */
        .pluck-badge {
            background: var(--secondary-background-color);
            color: #78909c;
            text-transform: uppercase;
        }

        /* --- Trigger Remotes: single HAIR Triggers drawer card --- */
        .trigger-drawer-card {
            transition: transform 120ms ease, box-shadow 300ms ease,
                        border-color 300ms ease, background 400ms ease;
            position: relative;
        }
        .trigger-drawer-card .trigger-icon {
            /* Gold, matching the drawer's own palette (bloomStyles'
               default hue) -- not the device green .toolbar-title uses,
               per the owner's green = device-ward ruling above. */
            color: #d4a017;
            transition: color 200ms ease, transform 200ms ease;
        }
        .trigger-drawer-card.expanded {
            border-color: #d4a017;
            box-shadow: 0 0 0 1px #d4a017;
        }
        /* Fire-glow now rides the shared .bloom class (ir-bloom-styles.ts)
           instead of this file's own trigger-card-flash/trigger-bolt-pulse
           keyframes -- same shape the Mirror's silver bloom uses, gold by
           this class's own default custom properties. */
        .trigger-drawer-card.bloom .trigger-icon {
            color: var(--bloom-peak);
        }

        /* --- Drawer header (rename-in-place + go-to-HA + close),
               parity with ir-device-detail.ts's own device header --- */
        .trh-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }
        .trh-header .header-left {
            flex: 1;
            min-width: 0;
        }
        .trh-header .name-row {
            display: flex;
            align-items: center;
            gap: 6px;
            min-width: 0;
        }
        .trh-header h1 {
            font-size: 1.3rem;
            margin: 0;
        }
        .trh-header .editable-name {
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .trh-header .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .trh-header .edit-icon {
            /* .editable-name's own flex gap (6px) already spaces this
               from the name -- an explicit margin here would double
               up with it (bench catch 2026-08-14: pushed the pencil
               out to 12px instead of 6). */
            font-size: 0.7rem;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .trh-header .editable-name:hover .edit-icon {
            opacity: 1;
        }
        .trh-header .name-input {
            font-size: 1.3rem;
            font-family: inherit;
            font-weight: bold;
            border: none;
            border-bottom: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-text-color);
            outline: none;
            flex: 1;
            min-width: 0;
            padding: 0 0 2px;
        }
        .trh-subtitle {
            margin-top: 2px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        .trh-header .collapse-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: none;
            border: none;
            padding: 4px;
            border-radius: 4px;
            font-size: 1rem;
            line-height: 1;
            color: var(--secondary-text-color);
            cursor: pointer;
            flex-shrink: 0;
            align-self: center;
            transition: background 150ms ease, color 150ms ease;
        }
        .trh-header .collapse-btn:hover {
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
        }

        /* --- Trigger row list (SortableJS grip-drag) --- */
        .trigger-rows {
            display: flex;
            flex-direction: column;
        }
        .trigger-rows ir-trigger-row.sortable-ghost {
            opacity: 0.4;
        }
        .grip-handle {
            --mdc-icon-size: 18px;
            color: var(--disabled-text-color, #999);
            cursor: grab;
        }
        .trigger-drawer-empty {
            padding: 20px 8px;
            text-align: center;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-list": IrDeviceList;
    }
}
