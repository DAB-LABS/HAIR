/**
 * Main panel entry point for HAIR.
 *
 * Renders in the HA sidebar as "HAIR" and routes between the device
 * list, device detail, and sniffer views. Holds the
 * WebSocket API client and the in-memory device cache.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { customElement, property, state } from "./decorators.js";
import { HairApi } from "./api.js";
import { setPanelLanguage, t } from "./localize.js";
import "./ir-device-list.js";
import "./ir-add-device-dialog.js";
import "./ir-signal-monitor.js";
import "./ir-clips.js";
import "./ir-pluck.js";
import "./ir-mirror.js";
import "./ir-wigs.js";
import type { DeviceSummary, IRDevice } from "./types.js";

// Bump alongside manifest.json on every release. Surfaced as a quiet
// footer line at the bottom of the panel so users (and bug reporters)
// can identify the installed HAIR version without opening Settings.
const HAIR_VERSION = "0.6.9";

type PanelTab = "devices" | "sniffer" | "clips" | "plucker" | "mirror" | "wigs";

@customElement("ha-panel-ir-devices")
export class HaPanelIrDevices extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public narrow = false;
    @property({ attribute: false }) public route?: { prefix: string; path: string };
    @property({ attribute: false }) public panel?: { config?: { entry_id?: string } };

    @state() private _activeTab: PanelTab = "devices";
    @state() private _devices: DeviceSummary[] = [];
    @state() private _expandedDeviceId: string | null = null;
    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _addDialogOpen = false;
    @state() private _pluckersAvailable = false;
    @state() private _pendingPluckEntity = "";

    private _api: HairApi | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.hass) {
            this._init();
        }
    }

    protected updated(changed: PropertyValues): void {
        if (changed.has("hass") && this.hass) {
            // Follow the USER's profile language (server language can
            // differ). Cheap no-op when unchanged; a language change
            // takes effect on reload per the i18n plan.
            setPanelLanguage(this.hass.language);
            if (!this._api) {
                this._init();
            }
        }
    }

    private _init(): void {
        this._api = new HairApi(this.hass);
        void this._refreshDevices();
        void this._checkPluckers();
    }

    /** Gate the Plucker tab on at least one compatible blaster being
     *  configured. Default false + render-only-when-true means no flash. */
    private async _checkPluckers(): Promise<void> {
        if (!this._api) return;
        try {
            const { vendors } = await this._api.listPluckVendors();
            this._pluckersAvailable = vendors.length > 0;
        } catch {
            this._pluckersAvailable = false;
        }
        if (this._activeTab === "plucker" && !this._pluckersAvailable) {
            this._switchTab("devices");
        }
    }

    private _tagline(): string {
        return t(`panel.tagline.${this._activeTab}`);
    }

    private async _refreshDevices(): Promise<void> {
        if (!this._api) return;
        this._loading = true;
        try {
            this._devices = await this._api.listDevices();
            this._error = null;
        } catch (err) {
            this._error = t("panel.load_failed", { message: (err as Error).message });
        } finally {
            this._loading = false;
        }
    }

    private _toggleDevice(deviceId: string): void {
        this._expandedDeviceId =
            this._expandedDeviceId === deviceId ? null : deviceId;
    }

    private _openAddDialog(): void {
        this._addDialogOpen = true;
    }

    private _onNavigatePlucker(
        e: CustomEvent<{ vendor_entity_id?: string }>,
    ): void {
        this._pendingPluckEntity = e.detail?.vendor_entity_id ?? "";
        this._switchTab("plucker");
    }

    /** Assigned-popover click-through (v0.6.6): switch to Devices and
     * expand the assignment's device card. Set the expansion AFTER the
     * tab switch, which clears it. */
    private _onNavigateDevice(e: CustomEvent<string>): void {
        this._switchTab("devices");
        this._expandedDeviceId = e.detail;
    }

    private _closeAddDialog(): void {
        this._addDialogOpen = false;
    }

    private async _onDeviceCreated(event: CustomEvent<IRDevice>): Promise<void> {
        this._addDialogOpen = false;
        await this._refreshDevices();
        this._expandedDeviceId = event.detail.id;
    }

    private async _onDeviceChanged(): Promise<void> {
        await this._refreshDevices();
    }

    private async _onDeviceDeleted(): Promise<void> {
        this._expandedDeviceId = null;
        await this._refreshDevices();
    }

    private _switchTab(tab: PanelTab): void {
        this._expandedDeviceId = null;
        this._activeTab = tab;
        if (tab === "devices") {
            void this._refreshDevices();
        }
    }

    /**
     * Dispatch HA's ``hass-toggle-menu`` event so the sidebar overlay
     * opens. Custom panels in the HA Companion app frequently hide the
     * system header on mobile, leaving phone users no obvious way back
     * to the rest of HA. This is an HA-blessed escape-hatch pattern;
     * the event must bubble and cross the shadow-DOM boundary to reach
     * the host shell that listens for it.
     *
     * Known caveat: certain late-2025 Android Companion builds report
     * that ``hass-toggle-menu`` does not consistently open the sidebar.
     * Users on those builds can still use the left-edge swipe gesture
     * (which is HA's primary navigation pattern on mobile). The button
     * being present and inert is no worse than the button being absent.
     */
    private _openHaSidebar(): void {
        this.dispatchEvent(
            new Event("hass-toggle-menu", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        if (!this._api) {
            return html`<div class="loading">${t("panel.loading")}</div>`;
        }

        return html`
            <ha-top-app-bar-fixed>
                <ha-menu-button
                    slot="navigationIcon"
                    .hass=${this.hass}
                ></ha-menu-button>

            <div class="mobile-nav-row">
                <button
                    class="mobile-nav-button"
                    title=${t("panel.open_menu")}
                    aria-label=${t("panel.open_menu")}
                    @click=${this._openHaSidebar}
                >
                    <ha-svg-icon
                        .path=${"M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}
                    ></ha-svg-icon>
                </button>
            </div>

            <div class="header-banner">
                <img
                    src="/hair_panel/assets/hair-header.png"
                    alt="HAIR"
                    class="header-img"
                />
            </div>

            <div class="tab-bar">
                <button
                    class="tab devices-tab ${this._activeTab === "devices" ? "active" : ""}"
                    @click=${() => this._switchTab("devices")}
                >
                    ${t("panel.tab.devices")}
                </button>
                <button
                    class="tab ${this._activeTab === "sniffer" ? "active" : ""}"
                    @click=${() => this._switchTab("sniffer")}
                >
                    Sniffer
                </button>
                <button
                    class="tab clipper-tab ${this._activeTab === "clips" ? "active" : ""}"
                    @click=${() => this._switchTab("clips")}
                >
                    Clipper
                </button>
                ${this._pluckersAvailable
                    ? html`<button
                          class="tab ${this._activeTab === "plucker" ? "active" : ""}"
                          @click=${() => this._switchTab("plucker")}
                      >
                          Plucker
                      </button>`
                    : ""}
                <button
                    class="tab mirror-tab ${this._activeTab === "mirror" ? "active" : ""}"
                    @click=${() => this._switchTab("mirror")}
                >
                    Mirror
                </button>
                <button
                    class="tab wigs-tab ${this._activeTab === "wigs" ? "active" : ""}"
                    @click=${() => this._switchTab("wigs")}
                >
                    ${t("panel.tab.wigs")}
                </button>
            </div>

            <div class="tab-tagline">${this._tagline()}</div>

            <div class="content">
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}
                ${this._activeTab === "devices"
                    ? html`
                          <ir-device-list
                              .devices=${this._devices}
                              .hass=${this.hass}
                              .api=${this._api}
                              .loading=${this._loading}
                              .expandedDeviceId=${this._expandedDeviceId}
                              @device-selected=${(e: CustomEvent<string>) =>
                                  this._toggleDevice(e.detail)}
                              @device-changed=${this._onDeviceChanged}
                              @device-deleted=${this._onDeviceDeleted}
                              @navigate-sniffer=${() => this._switchTab("sniffer")}
                              @navigate-clips=${() => this._switchTab("clips")}
                              @navigate-mirror=${() => this._switchTab("mirror")}
                              @navigate-plucker=${this._onNavigatePlucker}
                              @add-device=${this._openAddDialog}
                          ></ir-device-list>

                      `
                    : this._activeTab === "sniffer"
                      ? html`
                            <ir-signal-monitor
                                .api=${this._api}
                                .hass=${this.hass}
                                @navigate-device=${this._onNavigateDevice}
                            ></ir-signal-monitor>
                        `
                      : this._activeTab === "clips"
                        ? html`
                              <ir-clips
                                  .api=${this._api}
                                  .hass=${this.hass}
                                  @navigate-device=${this._onNavigateDevice}
                              ></ir-clips>
                          `
                        : this._activeTab === "plucker"
                          ? html`
                                <ir-pluck
                                    .api=${this._api}
                                    .hass=${this.hass}
                                    .pendingEntity=${this._pendingPluckEntity}
                                    @navigate-device=${this._onNavigateDevice}
                                ></ir-pluck>
                            `
                          : this._activeTab === "mirror"
                            ? html`
                                  <ir-mirror
                                      .api=${this._api}
                                      .hass=${this.hass}
                                      @navigate-device=${this._onNavigateDevice}
                                  ></ir-mirror>
                              `
                            : html`
                                  <ir-wigs
                                      .api=${this._api}
                                      .hass=${this.hass}
                                      @wig-tried-on=${() => this._switchTab("clips")}
                                  ></ir-wigs>
                              `}
            </div>

            ${this._addDialogOpen
                ? html`
                      <ir-add-device-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          @closed=${this._closeAddDialog}
                          @device-created=${this._onDeviceCreated}
                      ></ir-add-device-dialog>
                  `
                : ""}

            <div class="version-footer">v${HAIR_VERSION}</div>
            </ha-top-app-bar-fixed>
        `;
    }

    static styles = css`
        :host {
            display: block;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            min-height: 100vh;
        }
        .version-footer {
            text-align: center;
            color: var(--secondary-text-color);
            opacity: 0.5;
            font-size: 12px;
            padding: 24px 0 16px;
        }
        .header-banner {
            max-width: 1100px;
            margin: 0 auto;
            padding: 12px 16px 0;
            text-align: center;
        }
        .header-img {
            max-width: 100%;
            height: auto;
            max-height: 120px;
            object-fit: contain;
            border-radius: 6px;
        }
        .tab-tagline {
            max-width: 1100px;
            margin: 0 auto;
            padding: 8px 16px 0;
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            text-align: center;
            color: var(--secondary-text-color);
            margin-top: 14px;
        }
        .tab-bar {
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--divider-color);
            padding: 0 16px;
            max-width: 1100px;
            margin: 0 auto;
        }
        .tab-spacer {
            flex: 1;
        }
        .add-device-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            background: none;
            color: var(--primary-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            cursor: pointer;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .add-device-btn:hover {
            background: var(--secondary-background-color);
        }
        /* Clipper's tab-bar create button: identical to Add Device (gray
           stroke, neutral hover), just with copper text + icon. */
        .clipper-create-btn {
            color: #b87333;
        }
        .add-device-btn ha-svg-icon {
            --mdc-icon-size: 14px;
        }
        .tab {
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 12px 20px;
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--secondary-text-color);
            cursor: pointer;
            transition: color 150ms ease, border-color 150ms ease;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .tab:hover {
            color: var(--primary-text-color);
        }
        .tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
        }
        /* Devices wears the device green (#2e7d32 -- the expanded-card
           stroke and the Assign chip; owner ruling 2026-07-20). */
        .tab.devices-tab.active {
            color: #2e7d32;
            border-bottom-color: #2e7d32;
        }
        /* The Clipper wears its copper in the tab bar too (owner bench
           find, 2026-07-20: the active tab was default-blue while the
           whole tab's content is copper). */
        .tab.clipper-tab.active {
            color: #b87333;
            border-bottom-color: #b87333;
        }
        /* The Mirror wears silver (v0.6.6), matching its tab accent. */
        .tab.mirror-tab.active {
            color: #607d8b;
            border-bottom-color: #607d8b;
        }
        /* The closet wears oxblood leather (v0.7.0, owner ruling). */
        .tab.wigs-tab.active {
            color: #8e3b3b;
            border-bottom-color: #8e3b3b;
        }
        .content {
            padding: 16px;
            max-width: 1100px;
            margin: 0 auto;
        }
        .loading {
            padding: 48px;
            text-align: center;
            color: var(--secondary-text-color);
        }

        /* Mobile-only navigation row.
           Custom HA panels can have their system header hidden by the
           parent shell on the HA Companion app, especially on iOS where
           swipe-to-go-back does not exist as a platform gesture. Adding
           a hamburger inside the panel content guarantees mobile users
           always have a visible nav target. Hidden on desktop because
           the ha-top-app-bar-fixed above already exposes the same menu
           button there, and a second control would be redundant. */
        .mobile-nav-row {
            display: none;
        }
        @media (max-width: 768px) {
            .mobile-nav-row {
                display: flex;
                align-items: center;
                padding: 8px 12px 0;
                max-width: 1100px;
                margin: 0 auto;
            }
        }
        .mobile-nav-button {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            color: var(--secondary-text-color);
            padding: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 150ms ease, color 150ms ease;
        }
        .mobile-nav-button:hover {
            background: var(--secondary-background-color);
            color: var(--primary-text-color);
        }
        .mobile-nav-button ha-svg-icon {
            --mdc-icon-size: 22px;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ha-panel-ir-devices": HaPanelIrDevices;
    }
}
