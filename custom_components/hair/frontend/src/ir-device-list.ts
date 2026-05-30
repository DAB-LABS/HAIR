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
import { customElement, property, state } from "lit/decorators.js";
import "./ir-device-detail.js";
import "./ir-trigger-dialog.js";
import "./ir-confirm-dialog.js";
import type { HairApi } from "./api.js";
import type {
    CaptureProviderInfo,
    DeviceSummary,
    DeviceTypeId,
    IRDevice,
    IRTrigger,
    TriggerFiredEvent,
} from "./types.js";

const DEVICE_TYPE_ICONS: Record<DeviceTypeId, string> = {
    media_player: "M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",
    ac: "M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",
    fan: "M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",
    light: "M12,2A7,7 0 0,0 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H15A1,1 0 0,0 16,17V14.74C17.81,13.47 19,11.38 19,9A7,7 0 0,0 12,2M9,21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9V21Z",
    switch: "M13,3H11V13H13V3M17.83,5.17L16.41,6.59C18,7.35 19,9.05 19,11A7,7 0 0,1 12,18A7,7 0 0,1 5,11C5,9.05 6,7.35 7.58,6.59L6.17,5.17C4.23,6.82 3,9.26 3,12A9,9 0 0,0 12,21A9,9 0 0,0 21,12C21,9.26 19.77,6.82 17.83,5.17Z",
    screen: "M20,19H4A2,2 0 0,1 2,17V7A2,2 0 0,1 4,5H20A2,2 0 0,1 22,7V17A2,2 0 0,1 20,19M4,7V17H20V7H4M12,10L16,14H13V17H11V14H8L12,10Z",
    other: "M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z",
};

const DEVICE_TYPE_LABELS: Record<DeviceTypeId, string> = {
    media_player: "Media Player",
    ac: "Air Conditioner",
    fan: "Fan",
    light: "Light",
    switch: "Switch",
    screen: "Screen / Shade",
    other: "IR Device",
};

// MDI: remote (devices header icon)
const ICON_DEVICES =
    "M12,0C8.96,0 6.21,1.23 4.22,3.22L5.63,4.63C7.26,3 9.5,2 12,2C14.5,2 16.74,3 18.36,4.64L19.78,3.22C17.79,1.23 15.04,0 12,0M7.05,6.05L8.46,7.46C9.37,6.56 10.62,6 12,6C13.38,6 14.63,6.56 15.54,7.46L16.95,6.05C15.68,4.78 13.93,4 12,4C10.07,4 8.32,4.78 7.05,6.05M12,15A2,2 0 0,1 10,13A2,2 0 0,1 12,11A2,2 0 0,1 14,13A2,2 0 0,1 12,15M15,9H9A1,1 0 0,0 8,10V22A1,1 0 0,0 9,23H15A1,1 0 0,0 16,22V10A1,1 0 0,0 15,9Z";

// MDI: access-point (antenna icon) for emitters
const ICON_EMITTER =
    "M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.95 13.53,13.29L16.7,16.46C17.5,15.26 18,13.71 18,12A6,6 0 0,0 12,6A6,6 0 0,0 6,12C6,13.71 6.5,15.26 7.3,16.46L10.47,13.29C10.18,12.95 10,12.5 10,12A2,2 0 0,1 12,10M12,2A10,10 0 0,0 2,12C2,15.07 3.18,17.85 5.09,19.91L7.5,17.5C6.19,15.89 5.5,14 5.5,12A6.5,6.5 0 0,1 12,5.5A6.5,6.5 0 0,1 18.5,12C18.5,14 17.81,15.89 16.5,17.5L18.91,19.91C20.82,17.85 22,15.07 22,12A10,10 0 0,0 12,2Z";

// MDI: download-outline for receivers
const ICON_RECEIVER =
    "M13,5V11H14.17L12,13.17L9.83,11H11V5H13M15,3H9V9H5L12,16L19,9H15V3M19,18H5V20H19V18Z";

// MDI: radio-tower for proxies
const ICON_PROXY =
    "M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.94 13.53,13.29L16.7,22H14.57L12,14.93L9.43,22H7.3L10.47,13.29C10.18,12.94 10,12.5 10,12A2,2 0 0,1 12,10M12,8A4,4 0 0,0 8,12C8,12.5 8.1,13 8.28,13.46L7.4,15.86C6.53,14.81 6,13.47 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12C18,13.47 17.47,14.81 16.6,15.86L15.72,13.46C15.9,13 16,12.5 16,12A4,4 0 0,0 12,8M12,4A8,8 0 0,0 4,12C4,14.36 5,16.5 6.64,17.94L5.92,19.94C3.54,18.11 2,15.23 2,12A10,10 0 0,1 12,2A10,10 0 0,1 22,12C22,15.23 20.46,18.11 18.08,19.94L17.36,17.94C19,16.5 20,14.36 20,12A8,8 0 0,0 12,4Z";

// MDI: flash (lightning bolt) for triggers
const ICON_TRIGGER =
    "M7,2V13H10V22L17,10H13L17,2H7Z";

// MDI: delete-outline (trash icon)
const ICON_TRASH =
    "M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z";

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
    @state() private _expandedDevice: IRDevice | null = null;
    @state() private _triggers: IRTrigger[] = [];
    @state() private _glowTriggerIds = new Set<string>();
    @state() private _editTrigger: IRTrigger | null = null;
    @state() private _confirmDeleteTrigger: IRTrigger | null = null;

    private _unsubTriggerFired: (() => Promise<void>) | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        this._discoverHardware();
        void this._loadTriggers();
        void this._subscribeTriggerFired();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        void this._unsubscribeTriggerFired();
    }

    updated(changed: PropertyValues): void {
        if (changed.has("hass") || changed.has("api")) {
            this._discoverHardware();
        }
        if (changed.has("api") && this.api && !this._unsubTriggerFired) {
            void this._loadTriggers();
            void this._subscribeTriggerFired();
        }
        if (changed.has("expandedDeviceId")) {
            void this._loadExpandedDevice();
        }
    }

    private async _loadExpandedDevice(): Promise<void> {
        if (!this.expandedDeviceId || !this.api) {
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
            } catch {
                // Pre-2026.6 or non-fatal error.
            }
        }

        // Emitters from hass.states (exclude receiver entities)
        const states = (this.hass?.states ?? {}) as Record<
            string,
            { entity_id: string; attributes: { friendly_name?: string } }
        >;
        const emitters: { entity_id: string; name: string }[] = [];
        for (const [entityId, st] of Object.entries(states)) {
            if (entityId.startsWith("infrared.") && !receiverEntityIds.has(entityId)) {
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

    // --- Triggers ---

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
                    // Glow the card and flash the bolt.
                    this._glowTriggerIds = new Set([
                        ...this._glowTriggerIds,
                        ev.trigger_id,
                    ]);
                    setTimeout(() => {
                        const next = new Set(this._glowTriggerIds);
                        next.delete(ev.trigger_id);
                        this._glowTriggerIds = next;
                    }, 2500);
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

    private _openEditTrigger(trigger: IRTrigger, e: Event): void {
        e.stopPropagation();
        this._editTrigger = trigger;
    }

    private _closeEditTrigger(): void {
        this._editTrigger = null;
    }

    private async _onTriggerUpdated(): Promise<void> {
        this._editTrigger = null;
        await this._loadTriggers();
    }

    private async _toggleTriggerEnabled(trigger: IRTrigger, e: Event): Promise<void> {
        e.stopPropagation();
        try {
            await this.api!.updateTrigger(trigger.id, {
                enabled: !trigger.enabled,
            });
            await this._loadTriggers();
        } catch {
            // Non-fatal.
        }
    }

    private _requestDeleteTrigger(trigger: IRTrigger, e: Event): void {
        e.stopPropagation();
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
        const txDeviceIds = this._getEmitterDeviceIds();
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
                      title="Receives via HA's native infrared platform"
                  >RX-NATIVE</span>`
                : nothing}
            ${entry.has_bridge
                ? html`<span
                      class="badge rx-bridge"
                      title="Receives via legacy capture bridge"
                  >RX-BRIDGE</span>`
                : nothing}
            ${showGrayedNative
                ? html`<span
                      class="badge rx-native-disabled"
                      title="Upgrade to HA 2026.6+ for native receiver support"
                  >RX-NATIVE</span>`
                : nothing}
        `;
    }

    render() {
        if (this.loading) {
            return html`<div class="loading">Loading IR devices...</div>`;
        }

        const hasDevices = this.devices.length > 0;
        const hasEmitters = this._emitters.length > 0;
        const { receivers, proxies } = this._classifyHardware();
        const hasReceivers = receivers.length > 0;
        const hasProxies = proxies.length > 0;
        const hasTriggers = this._triggers.length > 0;
        const hasNothing = !hasDevices && !hasEmitters && !hasReceivers && !hasProxies;

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
            <!-- Devices -->
            <div class="toolbar">
                <span class="toolbar-title">
                    <ha-svg-icon .path=${ICON_DEVICES}></ha-svg-icon>
                    HAIR Devices
                    <span class="toolbar-count">(${this.devices.length})</span>
                </span>
            </div>
            ${hasDevices
                ? html`
                      <div class="grid">
                          ${this.devices.map(
                              (device) => html`
                                  <div
                                      class="card device-card ${device.id === this.expandedDeviceId ? "expanded" : ""}"
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
                                          <span class="badge cmd-badge">
                                              CMD: ${device.command_count}
                                          </span>
                                          ${device.emitter_entity_ids.length > 0
                                              ? html`<span class="badge tx-badge">TX: ${device.emitter_entity_ids.length}</span>`
                                              : html`<span class="badge no-tx-badge">No TX</span>`}
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
                                                    @collapse=${this._onCollapse}
                                                ></ir-device-detail>
                                            </div>
                                        `
                                      : nothing}
                              `,
                          )}
                      </div>
                  `
                : html`
                      <div class="empty-devices">
                          No devices yet. Sniff some signals, then add your first device.
                      </div>
                  `}

            <!-- Triggers -->
            ${hasTriggers
                ? html`
                      <div class="section-header">
                          <h2>Triggers</h2>
                          <span class="section-count">${this._triggers.length}</span>
                      </div>
                      <div class="grid">
                          ${this._triggers.map(
                              (t) => html`
                                  <div
                                      class="card trigger-card ${this._glowTriggerIds.has(t.id) ? "trigger-glow" : ""} ${!t.enabled ? "trigger-disabled" : ""}"
                                      tabindex="0"
                                      @click=${(e: Event) => this._openEditTrigger(t, e)}
                                      @keydown=${(e: KeyboardEvent) => {
                                          if (e.key === "Enter" || e.key === " ") {
                                              e.preventDefault();
                                              this._openEditTrigger(t, e);
                                          }
                                      }}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon class="trigger-icon" .path=${ICON_TRIGGER}></ha-svg-icon>
                                          <div class="card-name">${t.name}</div>
                                      </div>
                                      <div class="card-meta">Trigger Event</div>
                                      <div class="card-footer">
                                          ${t.min_hits > 1
                                              ? html`<span class="badge trigger-hits-badge">
                                                    ${t.min_hits}x hits
                                                </span>`
                                              : nothing}
                                          <span
                                              class="badge trigger-toggle ${t.enabled ? "trigger-enabled" : "trigger-off"}"
                                              @click=${(e: Event) => this._toggleTriggerEnabled(t, e)}
                                          >${t.enabled ? "ON" : "OFF"}</span>
                                          <ha-svg-icon
                                              class="trigger-trash"
                                              .path=${ICON_TRASH}
                                              title="Delete trigger"
                                              @click=${(e: Event) => this._requestDeleteTrigger(t, e)}
                                          ></ha-svg-icon>
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
                          <h2>Emitters</h2>
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
                                              title="Sends via HA's native infrared platform"
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
                          <h2>Receivers</h2>
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
                                      <div class="card-meta">${entry.nav_type}</div>
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
                          <h2>Proxies</h2>
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
                                      <div class="card-meta">${entry.nav_type}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title="Sends via HA's native infrared platform"
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
                          title="Delete Trigger"
                          message="Remove &quot;${this._confirmDeleteTrigger.name}&quot;? The associated HA event entity will also be removed."
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${() => (this._confirmDeleteTrigger = null)}
                      ></ir-confirm-dialog>
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
            color: var(--primary-color);
        }
        .toolbar-count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
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
        }
        .card-name {
            font-size: 0.95rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-meta {
            margin-top: 6px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-footer {
            margin-top: 8px;
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .badge {
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 0.72rem;
            font-weight: 500;
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
        .device-card.expanded {
            border-color: #2e7d32;
            box-shadow: 0 0 0 1px #2e7d32;
        }

        /* --- Hardware cards inherit shared .card styles --- */
        .hw-card {
            /* Neutral -- no per-section color backgrounds */
        }

        /* --- Trigger section --- */
        .trigger-card {
            transition: transform 120ms ease, box-shadow 300ms ease,
                        border-color 300ms ease, background 400ms ease;
        }
        .trigger-card .trigger-icon {
            transition: color 200ms ease, transform 200ms ease;
        }
        .trigger-card.trigger-disabled {
            opacity: 0.5;
        }

        /* --- Trigger fire animation (card + bolt) --- */
        .trigger-card.trigger-glow {
            border-color: #d4a017;
            background: rgba(212, 160, 23, 0.08);
            animation: trigger-card-flash 2.4s ease-out;
        }
        .trigger-card.trigger-glow .trigger-icon {
            color: #f5a623;
            animation: trigger-bolt-pulse 2.4s ease-out;
        }
        @keyframes trigger-card-flash {
            0% {
                background: rgba(212, 160, 23, 0.18);
                border-color: #f5a623;
                box-shadow: 0 0 16px 4px rgba(245, 166, 35, 0.4);
            }
            30% {
                background: rgba(212, 160, 23, 0.1);
                border-color: #d4a017;
                box-shadow: 0 0 8px 2px rgba(245, 166, 35, 0.2);
            }
            60% {
                background: rgba(212, 160, 23, 0.06);
                box-shadow: 0 0 4px 1px rgba(245, 166, 35, 0.1);
            }
            100% {
                background: transparent;
                border-color: var(--divider-color);
                box-shadow: none;
            }
        }
        @keyframes trigger-bolt-pulse {
            0% { color: #ffb300; transform: scale(1.4); }
            15% { color: #f5a623; transform: scale(1.0); }
            30% { color: #ffb300; transform: scale(1.35); }
            50% { color: #d4a017; transform: scale(1.0); }
            100% { color: var(--secondary-text-color); transform: scale(1.0); }
        }
        .trigger-hits-badge {
            background: rgba(184, 153, 48, 0.15);
            color: #b89930;
        }
        .trigger-toggle {
            cursor: pointer;
            transition: background 150ms ease;
        }
        .trigger-toggle.trigger-enabled {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }
        .trigger-toggle.trigger-enabled:hover {
            background: rgba(46, 125, 50, 0.25);
        }
        .trigger-toggle.trigger-off {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
        }
        .trigger-toggle.trigger-off:hover {
            background: rgba(0, 0, 0, 0.1);
        }
        .trigger-trash {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: pointer;
            margin-left: auto;
            opacity: 0.6;
            transition: color 150ms ease, opacity 150ms ease;
        }
        .trigger-trash:hover {
            color: #e65100;
            opacity: 1;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-list": IrDeviceList;
    }
}
