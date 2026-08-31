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
import "./ir-add-controlled-device-dialog.js";
import "./ir-add-trigger-remote-dialog.js";
import "./ir-signal-monitor.js";
import "./ir-clips.js";
import "./ir-pluck.js";
import "./ir-mirror.js";
import "./ir-wigs.js";
import type {
    DeviceSummary,
    IRDevice,
    PluckSource,
    TriggerRemoteInfo,
} from "./types.js";
import type { WigPickRow } from "./ir-wig-picker.js";

// Bump alongside manifest.json on every release. Surfaced as a quiet
// footer line at the bottom of the panel so users (and bug reporters)
// can identify the installed HAIR version without opening Settings.
const HAIR_VERSION = "0.14.0";

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
    @state() private _addRemoteDialogOpen = false;
    // Ghost tile drop wiring (signpost 3, Track 3 item 3): the wig a
    // successful drop resolved, riding along until the dialog it
    // opens reads it as .dropSource. Cleared on close/create same as
    // the open flags themselves.
    @state() private _addDialogDropSource: WigPickRow | null = null;
    @state() private _addRemoteDialogDropSource: WigPickRow | null = null;
    @state() private _triggerRemotes: TriggerRemoteInfo[] = [];
    @state() private _pluckSources: PluckSource[] = [];
    @state() private _pendingPluckEntity = "";

    private _api: HairApi | null = null;
    // Punch list item 7 (signpost 3 bench round, 2026-08-17): tracks
    // the last language we actually rendered the tab bar's own t()
    // calls with, so a language switch can force the one extra render
    // pass those calls need (see the requestUpdate() note below)
    // without doing it on every ordinary hass update.
    private _lastLanguage?: string;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.hass) {
            this._init();
        }
    }

    protected updated(changed: PropertyValues): void {
        if (changed.has("hass") && this.hass) {
            // Follow the USER's profile language (server language can
            // differ). Cheap no-op when unchanged.
            setPanelLanguage(this.hass.language);
            if (this.hass.language !== this._lastLanguage) {
                this._lastLanguage = this.hass.language;
                // This component's own render() (the tab bar's
                // t("panel.tab.devices") / t("panel.tab.wigs") labels)
                // just committed using the PREVIOUS language --
                // setPanelLanguage() above only takes effect on the
                // NEXT render. Ask for one, so the language switch
                // does not need a reload to reach the tab bar (the
                // child <ir-device-list>'s own body already re-renders
                // on its own hass property change and picks the new
                // language up without help).
                this.requestUpdate();
            }
            if (!this._api) {
                this._init();
            }
        }
    }

    private _init(): void {
        this._api = new HairApi(this.hass);
        void this._refreshDevices({ showSpinner: true });
        void this._refreshTriggerRemotes();
        void this._loadPluckSources();
    }

    /** The pluckable source roll, for the two add-dialogs.
     *
     *  This used to be `_checkPluckers()`, and it used to GATE the
     *  Plucker tab. It no longer does, and that is the whole point of
     *  this change: the tab renders always, like the other five, and
     *  says what it is when it is empty. Gating it hid the feature on
     *  exactly the hardware it was built for -- twice, once on the
     *  vendors-only rule and again on vendors-or-stores, because both
     *  asked "is there anything to pluck right now" of a surface whose
     *  job is to answer "could there ever be".
     *
     *  What survives is the ACTION PICKER rule, which is a different
     *  question and a legitimate one: see `anyPluckReadyNow`. The two
     *  dialogs read it off this list; nothing here decides for them. */
    private async _loadPluckSources(): Promise<void> {
        if (!this._api) return;
        try {
            this._pluckSources = (await this._api.listLearnedStores()).sources ?? [];
        } catch {
            this._pluckSources = [];
        }
    }

    private async _refreshDevices(
        opts: { showSpinner?: boolean } = {},
    ): Promise<void> {
        if (!this._api) return;
        // Add Popups signpost 3 bench fix (2026-08-15): only the very
        // first load should blank the list behind a spinner.
        // ir-device-list.ts's own render() returns just its ".loading"
        // div while `loading` is true, which tears down and rebuilds
        // its ENTIRE device grid -- including whatever expanded-detail
        // card is open and every custom element inside it. Every
        // background refresh (device-changed, device-created,
        // device-deleted) used to route through this same flag, so a
        // routine save -- e.g. toggling an emitter chip -- silently
        // destroyed and recreated <ir-device-detail> and its nested
        // <ir-header-chip-group>, resetting the chip group's own
        // `_expanded` state back to collapsed. That read to the owner
        // as "the page refreshes" and forced a re-click of "+" after
        // every single emitter toggle. The Remote/Receivers side never
        // had this bug: its refresh path (_onRemoteChanged ->
        // _refreshTriggerRemotes) never touches `_loading` at all --
        // that asymmetry was the tell. Spinner is opt-in per call now;
        // only _init()'s first call asks for one.
        if (opts.showSpinner) this._loading = true;
        try {
            this._devices = await this._api.listDevices();
            this._error = null;
        } catch (err) {
            this._error = t("panel.load_failed", { message: (err as Error).message });
        } finally {
            if (opts.showSpinner) this._loading = false;
        }
    }

    /**
     * Add Popups signpost 2, Track 4: named trigger remotes for the
     * Trigger Remotes section's card list. Parent-owned and passed
     * down as a property, same shape as _devices/_refreshDevices()
     * above -- the HAIR Triggers drawer itself stays self-loaded
     * inside ir-device-list.ts (getTriggerDrawer()/listTriggers()),
     * untouched by this.
     */
    private async _refreshTriggerRemotes(): Promise<void> {
        if (!this._api) return;
        try {
            this._triggerRemotes = await this._api.listTriggerRemotes();
        } catch {
            // Non-fatal; the section keeps showing its last-known list
            // until the next successful refresh.
        }
    }

    private _toggleDevice(deviceId: string): void {
        this._expandedDeviceId =
            this._expandedDeviceId === deviceId ? null : deviceId;
    }

    private _openAddDialog(
        e?: CustomEvent<{ dropSource?: WigPickRow }>,
    ): void {
        this._addDialogOpen = true;
        this._addDialogDropSource = e?.detail?.dropSource ?? null;
    }

    private _openAddRemoteDialog(
        e?: CustomEvent<{ dropSource?: WigPickRow }>,
    ): void {
        this._addRemoteDialogOpen = true;
        this._addRemoteDialogDropSource = e?.detail?.dropSource ?? null;
    }

    /** Ghost tile drop wiring (signpost 3, Track 3 item 3): the
     *  funnel's own refusal string, surfaced through the panel's
     *  existing error banner -- no new error copy, per the plan. */
    private _onDropUploadFailed(e: CustomEvent<string>): void {
        this._error = e.detail;
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
        this._addDialogDropSource = null;
    }

    private _closeAddRemoteDialog(): void {
        this._addRemoteDialogOpen = false;
        this._addRemoteDialogDropSource = null;
    }

    private async _onDeviceCreated(event: CustomEvent<IRDevice>): Promise<void> {
        this._addDialogOpen = false;
        this._addDialogDropSource = null;
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

    private async _onRemoteCreated(
        _event: CustomEvent<TriggerRemoteInfo>,
    ): Promise<void> {
        this._addRemoteDialogOpen = false;
        this._addRemoteDialogDropSource = null;
        await this._refreshTriggerRemotes();
    }

    private async _onRemoteDeleted(): Promise<void> {
        await this._refreshTriggerRemotes();
    }

    /** Add Popups signpost 2, Track 5: rename-in-place and duplicate
     *  both just need the same list refresh remote-deleted already
     *  triggers -- neither changes which remotes exist, only one
     *  remote's fields or the count. */
    private async _onRemoteChanged(): Promise<void> {
        await this._refreshTriggerRemotes();
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
                <button
                    class="tab ${this._activeTab === "plucker" ? "active" : ""}"
                    @click=${() => this._switchTab("plucker")}
                >
                    Plucker
                </button>
                <button
                    class="tab wigs-tab ${this._activeTab === "wigs" ? "active" : ""}"
                    @click=${() => this._switchTab("wigs")}
                >
                    ${t("panel.tab.wigs")}
                </button>
                <button
                    class="tab mirror-tab ${this._activeTab === "mirror" ? "active" : ""}"
                    @click=${() => this._switchTab("mirror")}
                >
                    Mirror
                </button>
                <!-- Signpost 3 follow-up (2026-08-15): the brand block
                     now lives inside the tab row itself instead of on
                     its own line above it -- shrunk to 46px (matches
                     a tab button's own rendered height) and bottom-
                     aligned via .tab-bar's align-items: flex-end, so
                     it reads as part of the same row rather than a
                     second header line. Pushed to the far right via
                     margin-left: auto on .brand-block.

                     Punch list item 5, owner ruling (2026-08-17): the
                     "HAIR" wordmark is dropped -- the sidebar already
                     names the integration and the character carries
                     the identity, so the text was spending horizontal
                     space the tab row needed more. Layout only, same
                     spirit as the 0.5.0 toolbar-title removal; not
                     documented as a feature. alt="HAIR" stays on the
                     image below -- it is non-visual (screen reader
                     only) and correctly describes the character. -->
                <div class="brand-block">
                    <img
                        src="/hair_panel/assets/hair-brand-mark-character.png"
                        alt="HAIR"
                        class="brand-mark"
                    />
                </div>
            </div>

            <div class="content">
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}
                ${this._activeTab === "devices"
                    ? html`
                          <ir-device-list
                              .devices=${this._devices}
                              .triggerRemotes=${this._triggerRemotes}
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
                              @add-trigger-remote=${this._openAddRemoteDialog}
                              @drop-upload-failed=${this._onDropUploadFailed}
                              @remote-deleted=${this._onRemoteDeleted}
                              @remote-renamed=${this._onRemoteChanged}
                              @remote-duplicated=${this._onRemoteChanged}
                              @remote-receivers-changed=${this._onRemoteChanged}
                              @remote-pins-changed=${this._onRemoteChanged}
                              @remote-trigger-toggled=${this._onRemoteChanged}
                              @remote-state-heard=${this._onRemoteChanged}
                              @remote-created=${this._onRemoteChanged}
                              @device-created=${this._onDeviceChanged}
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
                                      @navigate-device=${this._onNavigateDevice}
                                  ></ir-wigs>
                              `}
            </div>

            ${this._addDialogOpen
                ? html`
                      <ir-add-controlled-device-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          .pluckSources=${this._pluckSources}
                          .triggerRemotes=${this._triggerRemotes}
                          .dropSource=${this._addDialogDropSource}
                          @closed=${this._closeAddDialog}
                          @device-created=${this._onDeviceCreated}
                      ></ir-add-controlled-device-dialog>
                  `
                : ""}

            ${this._addRemoteDialogOpen
                ? html`
                      <ir-add-trigger-remote-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          .pluckSources=${this._pluckSources}
                          .dropSource=${this._addRemoteDialogDropSource}
                          @closed=${this._closeAddRemoteDialog}
                          @remote-created=${this._onRemoteCreated}
                      ></ir-add-trigger-remote-dialog>
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
        /* Signpost 3, third revision (2026-08-15): brand block lives in
           the tab row, text on the left, mascot hard right against the
           row's own right edge (margin-left: auto pushes the whole
           block there). The mascot carries its own 5px top/bottom
           margin so it reads as a deliberately framed image rather
           than a flush, floating one -- the tab-bar's flex-end
           alignment lets the row grow to fit that margin while the
           tab buttons stay pinned to the divider line beneath. */
        .brand-block {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-left: auto;
            padding-left: 12px;
        }
        .brand-mark {
            height: 46px;
            width: auto;
            display: block;
            margin: 5px 0;
        }
        /* Below 400px the mascot is what forces a third row of tab bar.
           Once .tab-bar wraps, the tabs pack two rows and .brand-block
           cannot fit beside the second one, so it takes a line of its
           own: measured 139px of bar at 320px against 98px at 390px.
           Dropping it below 400px puts every phone width on two rows at
           83px -- 56px back at 320px, and 15px even where the bar was
           already two rows.

           Owner ruling 2026-08-23: the banner carries page identity, so
           the mark is redundant on a phone and 83px beats 139px. Scoped
           to phones only; the mark is untouched from 400px up, where it
           costs nothing. */
        @media (max-width: 400px) {
            .brand-block {
                display: none;
            }
        }
        /* .brand-name removed with the wordmark, punch list item 5
           (2026-08-17) -- the character-only image is .brand-mark's
           sole child now. */
        /* flex-wrap is deliberately unconditional rather than parked in
           the 768px query below. Six tabs plus the brand block need
           625px; a phone gives the bar 379px at 390px viewport, so the
           last two tabs (Closet, Mirror) rendered entirely off-screen
           with no scroll affordance to hint they were there -- measured
           246px of overflow on a real 390px viewport.

           Wrap is a no-op at every width where the tabs already fit, so
           it costs the desktop layout nothing and needs no breakpoint of
           its own; it also keeps working if a seventh tab is ever added,
           which a hard-coded query would not. The alternative,
           overflow-x: auto, keeps one line but leaves those two tabs
           reachable only by a horizontal swipe that nothing advertises
           -- discoverability beat the 41px of extra bar height (57px ->
           98px at 390px, a 3+3 grid with the brand riding the second
           row). Switching to scrolling later is a one-line change. */
        .tab-bar {
            display: flex;
            flex-wrap: wrap;
            align-items: flex-end;
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
