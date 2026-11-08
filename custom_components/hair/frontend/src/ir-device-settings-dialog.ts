/**
 * Device settings dialog (Device Settings, 0.9.8, coding plan commit
 * 5 of 6). Opens from the settings button (mustache gear, RULED
 * 2026-08-09 -- see ir-icons.ts) in the device detail meta row
 * (ir-device-detail.ts) and holds whatever per-device settings don't
 * belong on the main card: power monitoring, and climate temperature/
 * humidity sensors (climate-sensors-coding-plan.md).
 *
 * `settingsSections(device)` is the single source of truth for which
 * power/climate sections a device gets INSIDE this dialog. It once
 * also gated the settings button's own visibility in
 * ir-device-detail.ts, but coding plan item 0.2 (Track 1 item 6, s10)
 * made the gear universal across every device type -- the button
 * always shows now, and this dialog's convert/Duplicate/Delete rows
 * are unconditional too, so an empty-sections device (a plain media
 * player, say) still opens a real, useful dialog rather than a
 * near-blank one (bench-verified at the Track 3.4 checkpoint).
 * It returns `'power'` for the device types that can plausibly draw
 * current (ac, media_player, fan, light, switch), `'climate'` for any
 * device carrying a loaded matrix (climate-sensors.md), and `[]` for
 * everything else (screen, other) -- a matrix AC device gets both.
 *
 * STRINGS: commit 5 shipped every user-facing string here as a plain
 * English literal rather than routing through t()/en.json, since
 * touching en.json without the matching nine-locale sync would have
 * broken the parity tests (tests/test_locales.py). Commit 6 wired
 * everything through the "devsettings.*" locale namespace (plus the
 * existing common.close/common.save/common.saving keys for the
 * action bar) and added the nine-language translations alongside it,
 * landing both halves together so the tree stayed green throughout.
 * Climate sensors (commit 3 of climate-sensors-coding-plan.md) added
 * four more devsettings.* keys the same way, ten-language sync
 * included in the same commit rather than queued for later.
 *
 * Bench fix pattern reused from ir-save-new-dialog.ts: one persistent
 * <ha-dialog> for the component's whole life, its direct children
 * never changing identity or count -- HA 2026.7's real showModal()/
 * close() transition throws an uncaught InvalidStateError if the
 * dialog's content is swapped wholesale mid-transition instead of
 * toggled with `?hidden`.
 *
 * ENTITY PICKER: the coding plan calls for <ha-entity-picker>, but
 * that component is used nowhere else in this codebase and internally
 * leans on <ha-combo-box>/<ha-textfield> -- the same lazy-load family
 * that made <ha-textfield> render as an empty, unfocusable shell in
 * ir-promote-dialog.ts (see that file's header comment, "shampoo
 * bench" bug) when used directly inside a custom panel. Rather than
 * risk the identical failure mode on the one field this dialog cannot
 * work without, the state source picker below is house-built: a
 * closed field showing what is chosen, which opens a floating list (a
 * combobox; ir-capture-switch-menu.ts is the nearest precedent, a
 * closed control and a floating menu). The list is a plain search
 * <input> over the rows of the RX-CAPTURE switch search, and scans
 * this.hass.states (state-source.ts): None, then the "sensor" entities
 * that look like power sensors (device_class "power", or a W/kW unit),
 * then the on/off entities a state can be read from, each group under
 * its heading and sorted by name -- the same direct-hass.states-scan
 * convention ir-emitter-picker.ts already uses for emitters. The search
 * matches a name or an entity id and never hides the chosen row; how
 * the field and the list answer clicks and keys is pickerStep's. No
 * manual entity-ID fallback (owner ruling 2026-08-09, post-launch
 * bench pass): the design brief specs a picker only, so a device whose
 * currently-configured sensor doesn't match the power-ish filter still
 * gets it injected into the candidate list (see stateSourceCandidates)
 * rather than losing it. The climate pickers (climate-sensors.md) are
 * plain <select>s, filtering on device_class "temperature"/"humidity"
 * (see _candidatesByDeviceClass) -- same safety net, same no-custom-ID
 * ruling, picker only.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type {
    DeviceTypeId,
    IRDevice,
    SpeedCycleTurnOn,
    TriggerRemoteInfo,
} from "./types.js";
import {
    MAX_SPEED_STEPS,
    MIN_SPEED_STEPS,
    hasSpeedCycle,
    speedStepsForSave,
} from "./speed-cycle-settings.js";
import { healthDotClass, isEntityOnline } from "./entity-health.js";
import { healthDotStyles } from "./ir-header-chip-styles.js";
import { popoverStyles } from "./ir-popover-styles.js";
import {
    PANEL_GAP,
    PICKER_CLOSED,
    filterSourceGroups,
    isOnOffEntity,
    pickerOptions,
    pickerStep,
    placePanel,
    settleCapFor,
    settleOnPick,
    stateSourceCandidates,
    stateSourcePatch,
    type PanelPlacement,
    type PickerEvent,
    type PickerState,
    type SourceGroups,
} from "./state-source.js";

export type SettingsSectionId = "power" | "climate" | "speed_cycle";

const POWER_ELIGIBLE_TYPES: ReadonlySet<DeviceTypeId> = new Set([
    "ac",
    "media_player",
    "fan",
    "light",
    "switch",
]);

/** Single source of truth for which sections a device gets. See the
 * file header comment -- this must stay in lockstep between the
 * settings button (ir-device-detail.ts) and this dialog. CLIMATE
 * (climate-sensors.md) is matrix-gated, not device-type-gated: a
 * device's full payload carries `matrix` exactly when it has a loaded
 * climate lattice, so that field alone decides it. SPEED CYCLE (GH
 * Discussion #201) is for a fan with a Speed Cycle command mapped. */
export function settingsSections(
    device: Pick<IRDevice, "device_type" | "matrix"> &
        Partial<Pick<IRDevice, "entity_config">>,
): SettingsSectionId[] {
    const sections: SettingsSectionId[] = [];
    if (POWER_ELIGIBLE_TYPES.has(device.device_type)) {
        sections.push("power");
    }
    if (hasSpeedCycle(device)) {
        sections.push("speed_cycle");
    }
    if (device.matrix) {
        sections.push("climate");
    }
    return sections;
}

interface SensorCandidate {
    entityId: string;
    name: string;
}

/** Sensor "attributes" shape read by _candidatesByDeviceClass
 * (climate); the state source's picker reads the same shape through
 * state-source.ts. */
interface SensorStateShape {
    state?: string;
    attributes: {
        friendly_name?: string;
        device_class?: string;
        unit_of_measurement?: string;
    };
}

const DEFAULT_OFF_BELOW_W = 5;
const DEFAULT_ON_ABOVE_W = 10;
// The settle window (0.17.2). Mirrors models.py DEFAULT_POWER_SETTLE_S;
// the ceilings depend on the source (state-source.ts settleCapFor).
const DEFAULT_SETTLE_S = 20;

/** Is focus, through any shadow roots, on something a user types into
 * or presses? */
function focusIsOnAControl(): boolean {
    let el: Element | null = document.activeElement;
    while (el?.shadowRoot?.activeElement) el = el.shadowRoot.activeElement;
    if (!el || el === document.body) return false;
    return el.matches(
        "input, textarea, select, button, a[href], [contenteditable=''], [contenteditable='true'], [tabindex]:not([tabindex='-1'])",
    );
}

@customElement("ir-device-settings-dialog")
export class IrDeviceSettingsDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public device!: IRDevice;
    /** Every Remote, for the pins section (GH #183): the ones whose
     * pinned_device_ids hold this device are listed there. */
    @property({ attribute: false }) public triggerRemotes: TriggerRemoteInfo[] =
        [];

    /** "" = no source, otherwise a power sensor or an on/off entity id
     *  from the picker. */
    @state() private _sensorChoice = "";
    @state() private _offBelow = "";
    @state() private _onAbove = "";
    @state() private _settle = "";
    /** The state source picker: closed, or open with its search and
     * the option the arrow keys are on (state-source.ts pickerStep). */
    @state() private _picker: PickerState = PICKER_CLOSED;
    /** Where the open list floats, and the correction for a containing
     * block that is not the window (see _placePanel). */
    @state() private _panel: PanelPlacement | null = null;
    @state() private _panelShift = { dx: 0, dy: 0 };
    private _trackFrame = 0;
    private _trackedBox = "";
    // Climate room sensors (climate-sensors.md, riding 0.9.8). Same ""
    // = none convention as the power picker above, but independent of
    // it and of each other -- either can be picked, changed, or
    // cleared without touching the other.
    @state() private _temperatureChoice = "";
    @state() private _humidityChoice = "";
    // Fan speed cycle. "" = no number of speeds set.
    @state() private _speedSteps = "";
    @state() private _cycleIncludesOff = false;
    @state() private _cycleTurnOn: SpeedCycleTurnOn = "resume";
    // Toggle power (GH #183): the matrix setting, and per pinning Remote
    // whether the pin relays the power toggle (true) or follows it.
    @state() private _powerToggles = false;
    @state() private _relay: Record<string, boolean> = {};
    @state() private _busy = false;
    @state() private _error: string | null = null;

    firstUpdated(): void {
        this._powerToggles = this.device.power_toggles === true;
        this._relay = Object.fromEntries(
            this._pinningRemotes().map((r) => [
                r.id,
                !(r.follow_only_device_ids ?? []).includes(this.device.id),
            ]),
        );
        this._sensorChoice = this.device.power_sensor_entity_id ?? "";
        this._offBelow =
            this.device.power_off_below_w?.toString() ??
            String(DEFAULT_OFF_BELOW_W);
        this._onAbove =
            this.device.power_on_above_w?.toString() ??
            String(DEFAULT_ON_ABOVE_W);
        // ?? and not ||: a stored 0 is the opt-out and must show as 0.
        this._settle =
            this.device.power_settle_s?.toString() ??
            String(DEFAULT_SETTLE_S);
        this._temperatureChoice = this.device.temperature_sensor_entity_id ?? "";
        this._humidityChoice = this.device.humidity_sensor_entity_id ?? "";
        const config = this.device.entity_config;
        this._speedSteps = config?.fan_speed_steps?.toString() ?? "";
        this._cycleIncludesOff = config?.speed_cycle_includes_off === true;
        this._cycleTurnOn =
            config?.speed_cycle_turn_on === "speed_1" ? "speed_1" : "resume";
    }

    /** Climate's picker filter (climate-sensors.md): device_class
     * only, no unit-based fallback -- temperature/humidity sensors
     * reliably declare device_class, unlike the power-ish sensors the
     * method above has to guess at from W/kW when it's missing. Same
     * "keep the currently-configured one selectable" safety net. */
    private _candidatesByDeviceClass(
        deviceClass: string,
        current: string | null,
    ): SensorCandidate[] {
        const states = (this.hass?.states ?? {}) as Record<
            string,
            SensorStateShape
        >;
        const out: SensorCandidate[] = [];
        for (const [entityId, st] of Object.entries(states)) {
            if (!entityId.startsWith("sensor.")) continue;
            if (st.attributes.device_class !== deviceClass) continue;
            out.push({
                entityId,
                name: st.attributes.friendly_name ?? entityId,
            });
        }
        if (current && !out.some((c) => c.entityId === current)) {
            out.push({
                entityId: current,
                name: states[current]?.attributes.friendly_name ?? current,
            });
        }
        out.sort((a, b) => a.name.localeCompare(b.name));
        return out;
    }

    private get _validationError(): string | null {
        if (
            settingsSections(this.device).includes("speed_cycle") &&
            Number.isNaN(speedStepsForSave(this._speedSteps))
        ) {
            return t("devsettings.validation_speed_steps");
        }
        if (!this._sensorChoice) return null;
        // An on/off entity is read by its state: no thresholds to check.
        if (isOnOffEntity(this._sensorChoice)) return null;
        const off = parseFloat(this._offBelow);
        const on = parseFloat(this._onAbove);
        if (Number.isNaN(off) || Number.isNaN(on)) {
            return t("devsettings.validation_incomplete");
        }
        if (on < off) {
            return t("devsettings.validation_order");
        }
        return null;
    }

    /** Bench fix (see file header): plain dispatch, one persistent
     * dialog, no target to check. */
    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    /** Dual-entry with ir-device-list.ts's card-corner Duplicate icon
     *  (Track 1 item 6, s10): this dialog does not implement
     *  duplication itself, it just asks for it and gets out of the
     *  way. Composed so it bubbles straight through ir-device-detail.ts
     *  (its host) to ir-device-list.ts's <ir-device-detail>
     *  instantiation, which reuses its existing
     *  _openDuplicateDialog/ir-duplicate-device-dialog flow verbatim. */
    private _requestDuplicate(): void {
        this.dispatchEvent(
            new CustomEvent("request-duplicate", { bubbles: true, composed: true }),
        );
        this._close();
    }

    /** Dual-entry with the card's hover-trash icon, same one flow
     *  (Track 1 item 6, s10 callout: "one delete flow, two entry
     *  points"). See ir-device-detail.ts's own _requestDelete for the
     *  footer button's identical treatment and why this consolidates
     *  what used to be a third, separate implementation. */
    private _requestDelete(): void {
        this.dispatchEvent(
            new CustomEvent("request-delete", { bubbles: true, composed: true }),
        );
        this._close();
    }

    /** "Make a Remote" mirror-door mint (signpost 3, Track 3.5,
     *  owner-directed 2026-08-15). Same ask-and-get-out-of-the-way
     *  shape as _requestDuplicate/_requestDelete above -- this dialog
     *  does not mint anything itself, ir-device-list.ts's
     *  <ir-promote-remote-dialog> (sourceDeviceId mode) does, reached
     *  by composed bubbling through this dialog's host exactly like
     *  those two requests already are. */
    private _requestMakeRemote(): void {
        this.dispatchEvent(
            new CustomEvent("request-make-remote", { bubbles: true, composed: true }),
        );
        this._close();
    }

    /** A row of the state source picker was chosen ("" is None). */
    private _pickSource(entityId: string): void {
        if (this._busy || entityId === this._sensorChoice) return;
        this._sensorChoice = entityId;
        if (entityId) {
            this._settle = settleOnPick(entityId, this._settle);
        }
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._stopPanelTracking();
    }

    private _sourceGroups(): SourceGroups {
        return stateSourceCandidates(
            this.hass?.states ?? {},
            this.hass?.entities ?? {},
            this.device.power_sensor_entity_id,
        );
    }

    /**
     * Every click and key on the picker goes through pickerStep; this
     * carries out what the step asks. A handled key is cancelled and
     * stopped here, so Escape closes the list and never reaches the
     * dialog around it.
     */
    private _pickerEvent(event: PickerEvent, dom?: Event): void {
        if (this._busy && !this._picker.open) return;
        const groups = this._sourceGroups();
        const chosen = this._sensorChoice;
        const step = pickerStep(this._picker, event, chosen, (query, keep = true) =>
            pickerOptions(
                filterSourceGroups(groups, query, keep ? chosen || null : null),
            ),
        );
        if (step.handled && dom) {
            dom.preventDefault();
            dom.stopPropagation();
        }
        const wasOpen = this._picker.open;
        this._picker = step.state;
        if (step.pick !== undefined) this._pickSource(step.pick);
        if (!wasOpen && step.state.open) {
            // Placed before the first render: a list that is not yet
            // visible cannot take focus.
            const field = this.renderRoot.querySelector<HTMLElement>(".source-field");
            if (field) {
                this._panel = placePanel(field.getBoundingClientRect(), {
                    width: window.innerWidth,
                    height: window.innerHeight,
                });
            }
            this._startPanelTracking();
        }
        if (wasOpen && !step.state.open) this._stopPanelTracking();
        void this.updateComplete.then(() => {
            const root = this.renderRoot;
            if (step.focusSearch) {
                root.querySelector<HTMLInputElement>(".source-search")?.focus();
            }
            if (step.focusField && event.kind !== "outside") {
                root.querySelector<HTMLElement>(".source-field")?.focus();
            }
            root.querySelector<HTMLElement>(".source-row.active")?.scrollIntoView({
                block: "nearest",
            });
        });
    }

    /**
     * A press anywhere but the field or the list closes it. Focus goes
     * back to the field once the press is over, unless the press put it
     * on another control, which is where the user meant it to go.
     */
    private _onOutsidePointer = (e: Event): void => {
        const path = e.composedPath();
        const field = this.renderRoot.querySelector<HTMLElement>(".source-field");
        const panel = this.renderRoot.querySelector(".source-panel");
        if ((field && path.includes(field)) || (panel && path.includes(panel))) {
            return;
        }
        this._pickerEvent({ kind: "outside" });
        window.addEventListener(
            "pointerup",
            () =>
                setTimeout(() => {
                    if (!focusIsOnAControl()) field?.focus();
                }),
            { once: true, capture: true },
        );
    };

    /**
     * While the list is open it follows the field. Any of the scroll
     * areas between here and the window can move it, and a scroll event
     * from inside another shadow root never reaches a listener out
     * here, so the field's box is checked once a frame instead, and the
     * list placed again when it or the window changes.
     */
    private _startPanelTracking(): void {
        document.addEventListener("pointerdown", this._onOutsidePointer, true);
        this._trackedBox = "";
        const tick = () => {
            const field = this.renderRoot.querySelector<HTMLElement>(".source-field");
            if (field) {
                const r = field.getBoundingClientRect();
                const box = `${r.top},${r.left},${r.width},${r.height},${window.innerWidth},${window.innerHeight}`;
                if (box !== this._trackedBox) {
                    this._trackedBox = box;
                    void this._placePanel(field);
                }
            }
            this._trackFrame = requestAnimationFrame(tick);
        };
        this._trackFrame = requestAnimationFrame(tick);
    }

    private _stopPanelTracking(): void {
        document.removeEventListener("pointerdown", this._onOutsidePointer, true);
        cancelAnimationFrame(this._trackFrame);
        this._trackFrame = 0;
        this._panel = null;
    }

    /**
     * Fixed, from the field's box (placePanel), so no scroll area in the
     * dialog clips it and it floats over what follows. Fixed means the
     * window only when no ancestor makes itself the containing block (a
     * transform does); the list is measured once placed, and any
     * difference from where it was meant to be is kept as a shift.
     */
    private async _placePanel(field: HTMLElement): Promise<void> {
        const r = field.getBoundingClientRect();
        const place = placePanel(r, {
            width: window.innerWidth,
            height: window.innerHeight,
        });
        this._panel = place;
        await this.updateComplete;
        const panel = this.renderRoot.querySelector<HTMLElement>(".source-panel");
        if (!panel || !this._picker.open) return;
        const got = panel.getBoundingClientRect();
        const dx = place.left - got.left;
        const dy = place.up
            ? r.top - PANEL_GAP - got.bottom
            : r.bottom + PANEL_GAP - got.top;
        if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
            this._panelShift = {
                dx: this._panelShift.dx + dx,
                dy: this._panelShift.dy + dy,
            };
        }
    }

    private _onTemperatureChoiceChanged(e: Event): void {
        this._temperatureChoice = (e.target as HTMLSelectElement).value;
    }

    private _onHumidityChoiceChanged(e: Event): void {
        this._humidityChoice = (e.target as HTMLSelectElement).value;
    }

    /** The Remotes this device is pinned to (GH #183). */
    private _pinningRemotes(): TriggerRemoteInfo[] {
        return this.triggerRemotes.filter((r) =>
            (r.pinned_device_ids ?? []).includes(this.device.id),
        );
    }

    /** Whether the pins section shows: the device's power goes round on
     * one button (the matrix setting as ticked now, or a flat device's
     * toggle mapping) and some Remote pins it. Outside the
     * settingsSections() list on purpose: it reads Remotes, and the
     * gear no longer depends on sections. */
    private _showsRelay(): boolean {
        const toggles = this.device.matrix
            ? this._powerToggles
            : this.device.power_is_toggle === true;
        return toggles && this._pinningRemotes().length > 0;
    }

    /** What the settle field saves as. A device still on the default
     * that nobody changed stays on the default (null), so it keeps
     * following it; an empty field also means the default. Anything
     * else is clamped into the range the backend accepts for the
     * chosen source. */
    private _settleForSave(): number | null {
        const value = parseFloat(this._settle);
        if (Number.isNaN(value)) return null;
        if (
            this.device.power_settle_s == null &&
            value === DEFAULT_SETTLE_S
        ) {
            return null;
        }
        return Math.min(
            settleCapFor(this._sensorChoice),
            Math.max(0, value),
        );
    }

    private async _save(): Promise<void> {
        if (this._busy) return;
        const validation = this._validationError;
        if (validation) {
            this._error = validation;
            return;
        }
        this._busy = true;
        this._error = null;
        const sections = settingsSections(this.device);
        const sensorId = this._sensorChoice || null;
        const patch: Parameters<HairApi["updateDevice"]>[1] = {};
        if (sections.includes("power")) {
            Object.assign(
                patch,
                stateSourcePatch(
                    sensorId,
                    this._offBelow,
                    this._onAbove,
                    sensorId ? this._settleForSave() : null,
                ),
            );
        }
        if (this.device.matrix) {
            patch.power_toggles = this._powerToggles;
        }
        if (sections.includes("climate")) {
            patch.temperature_sensor_entity_id = this._temperatureChoice || null;
            patch.humidity_sensor_entity_id = this._humidityChoice || null;
        }
        if (sections.includes("speed_cycle")) {
            patch.fan_speed_steps = speedStepsForSave(this._speedSteps);
            patch.speed_cycle_includes_off = this._cycleIncludesOff;
            patch.speed_cycle_turn_on = this._cycleTurnOn;
        }
        try {
            await this.api.updateDevice(this.device.id, patch);
            const relayChanged = await this._saveRelays();
            if (relayChanged) {
                this.dispatchEvent(
                    new CustomEvent("remote-pins-changed", {
                        bubbles: true,
                        composed: true,
                    }),
                );
            }
            // Bare event, no detail -- matches the house convention
            // (ir-device-list.ts _onExpandedDeviceChanged): the
            // ancestor always does a full refetch on device-changed
            // rather than trusting an event payload, so there is
            // nothing this dialog needs to carry.
            this.dispatchEvent(
                new CustomEvent("device-changed", {
                    bubbles: true,
                    composed: true,
                }),
            );
            this._close();
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    /** Write each pin whose relay choice changed; true when any did. */
    private async _saveRelays(): Promise<boolean> {
        let changed = false;
        for (const remote of this._pinningRemotes()) {
            const relay = this._relay[remote.id];
            if (relay === undefined) continue;
            const before = !(remote.follow_only_device_ids ?? []).includes(
                this.device.id,
            );
            if (relay === before) continue;
            await this.api.setPinRelay(remote.id, this.device.id, relay);
            changed = true;
        }
        return changed;
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${t("devsettings.title")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._renderBody()}
            </ha-dialog>
        `;
    }

    private _renderBody() {
        const sections = settingsSections(this.device);
        return html`
            <div ?hidden=${!this._error}>
                <ha-alert alert-type="error">${this._error}</ha-alert>
            </div>
            <div class="section-slot" ?hidden=${!sections.includes("power")}>
                ${this._renderPowerSection()}
            </div>
            <div
                class="section-slot"
                ?hidden=${!sections.includes("speed_cycle")}
            >
                ${this._renderSpeedCycleSection()}
            </div>
            <div class="section-slot" ?hidden=${!sections.includes("climate")}>
                ${this._renderClimateSection()}
            </div>
            <div class="section-slot" ?hidden=${!this._showsRelay()}>
                ${this._renderRelaySection()}
            </div>
            <div class="section-slot">
                ${this._renderConvertSection()}
            </div>
            <div class="dialog-actions">
                <button
                    class="action-btn delete-btn"
                    @click=${this._requestDelete}
                    ?disabled=${this._busy}
                >
                    ${t("devsettings.delete")}
                </button>
                <span class="actions-spacer"></span>
                <button
                    class="action-btn duplicate-btn"
                    @click=${this._requestDuplicate}
                    ?disabled=${this._busy}
                >
                    ${t("devsettings.duplicate")}
                </button>
                <button
                    class="action-btn save-btn"
                    @click=${this._save}
                    ?disabled=${this._busy || !!this._validationError}
                >
                    ${this._busy ? t("common.saving") : t("common.save")}
                </button>
            </div>
        `;
    }

    /** "Make a Remote" mirror-door row (s10, s10's .sd-section.convert):
     *  wired since signpost 3 Track 3.5 (owner-directed 2026-08-15) to
     *  hair/device/make-remote via ir-device-list.ts's
     *  <ir-promote-remote-dialog> (sourceDeviceId mode) -- the gap
     *  flagged at the Track 3.4 checkpoint (Track 2.2 covered
     *  Sniffer/Clipper/Plucker/Closet-wig sources but never a live
     *  Device's own commands) is now closed. This dialog only asks
     *  for the mint (_requestMakeRemote) and gets out of the way, same
     *  dual-entry shape as Duplicate/Delete above. */
    private _renderConvertSection() {
        return html`
            <section class="settings-section section-convert">
                <div class="convert-row">
                    <div class="convert-text">
                        <h3 class="section-label convert-label">
                            ${t("devsettings.make_remote_title")}
                        </h3>
                        <p class="section-explainer convert-desc">
                            ${t("devsettings.make_remote_desc")}
                        </p>
                    </div>
                    <div class="convert-btn-cell">
                        <button
                            class="action-btn convert-btn"
                            @click=${this._requestMakeRemote}
                        >
                            ${t("devsettings.make_remote_btn")}
                        </button>
                    </div>
                </div>
            </section>
        `;
    }

    private _renderPowerSection() {
        const groups = this._sourceGroups();
        const sensorPicked = !!this._sensorChoice;
        const onOff = isOnOffEntity(this._sensorChoice);
        const liveState = sensorPicked
            ? this.hass?.states?.[this._sensorChoice]
            : undefined;
        const shown = filterSourceGroups(
            groups,
            this._picker.query,
            this._sensorChoice || null,
        );
        return html`
            <section class="settings-section section-power">
                <h3 class="section-label">
                    ${t("devsettings.power_section_label")}
                </h3>

                <p class="section-explainer">
                    ${t("devsettings.power_intro")}
                </p>

                ${this.device.matrix
                    ? html`
                          <label class="check-row">
                              <input
                                  type="checkbox"
                                  .checked=${this._powerToggles}
                                  @change=${(e: Event) =>
                                      (this._powerToggles = (
                                          e.target as HTMLInputElement
                                      ).checked)}
                                  ?disabled=${this._busy}
                              />
                              <span>${t("devsettings.power_toggles_label")}</span>
                          </label>
                          <p class="section-explainer">
                              ${t("devsettings.power_toggles_help")}
                          </p>
                      `
                    : ""}

                <div class="field">
                    <label id="source-label"
                        >${t("devsettings.sensor_label")}</label
                    >
                    ${this._renderSourceField(groups)}
                    ${this._picker.open ? this._renderSourcePanel(shown) : ""}
                    <p class="section-explainer">
                        ${t(
                            onOff
                                ? "devsettings.onoff_explainer"
                                : "devsettings.power_explainer",
                        )}
                    </p>
                </div>

                ${sensorPicked
                    ? html`
                          <div class="live-readout">
                              ${this._renderLiveReadout(liveState, onOff)}
                          </div>
                      `
                    : ""}
                ${sensorPicked && !onOff
                    ? html`
                          <div class="pair-grid field">
                              <div>
                                  <label
                                      >${t("devsettings.off_below_label")}</label
                                  >
                                  <input
                                      type="number"
                                      .value=${this._offBelow}
                                      @input=${(e: Event) =>
                                          (this._offBelow = (
                                              e.target as HTMLInputElement
                                          ).value)}
                                      ?disabled=${this._busy}
                                  />
                              </div>
                              <div>
                                  <label
                                      >${t("devsettings.on_above_label")}</label
                                  >
                                  <input
                                      type="number"
                                      .value=${this._onAbove}
                                      @input=${(e: Event) =>
                                          (this._onAbove = (
                                              e.target as HTMLInputElement
                                          ).value)}
                                      ?disabled=${this._busy}
                                  />
                              </div>
                          </div>
                      `
                    : ""}
                ${sensorPicked
                    ? html`
                          <div class="field">
                              <label>${t("devsettings.settle_label")}</label>
                              <input
                                  type="number"
                                  min="0"
                                  max=${settleCapFor(this._sensorChoice)}
                                  step="1"
                                  .value=${this._settle}
                                  @input=${(e: Event) =>
                                      (this._settle = (
                                          e.target as HTMLInputElement
                                      ).value)}
                                  ?disabled=${this._busy}
                              />
                              <p class="section-explainer">
                                  ${t(
                                      onOff
                                          ? "devsettings.settle_help_onoff"
                                          : "devsettings.settle_help",
                                  )}
                              </p>
                          </div>
                      `
                    : ""}
            </section>
        `;
    }

    /** Pins and the power toggle (GH #183): per Remote pinning this
     * device, whether a heard power press is sent on (relay) or only
     * followed. Following is right when the device hears its own
     * handset; relaying is for a device out of the handset's sight. */
    private _renderRelaySection() {
        return html`
            <section class="settings-section section-relay">
                <h3 class="section-label">
                    ${t("devsettings.relay_section_label")}
                </h3>

                <p class="section-explainer">
                    ${t("devsettings.relay_intro")}
                </p>

                ${this._pinningRemotes().map(
                    (remote) => html`
                        <label class="check-row">
                            <input
                                type="checkbox"
                                .checked=${this._relay[remote.id] ?? true}
                                @change=${(e: Event) =>
                                    (this._relay = {
                                        ...this._relay,
                                        [remote.id]: (
                                            e.target as HTMLInputElement
                                        ).checked,
                                    })}
                                ?disabled=${this._busy}
                            />
                            <span
                                >${t("devsettings.relay_label", {
                                    remote: remote.name,
                                })}</span
                            >
                        </label>
                    `,
                )}
            </section>
        `;
    }

    /** Fan speed cycle (GH Discussion #201): the number of speeds the
     * one button steps through, whether off is one of them, and where
     * turning the fan on lands when it is not. The last line is the
     * honest part: HAIR counts presses, it does not read the speed. */
    private _renderSpeedCycleSection() {
        return html`
            <section class="settings-section section-speed-cycle">
                <h3 class="section-label">
                    ${t("devsettings.speed_cycle_section_label")}
                </h3>

                <p class="section-explainer">
                    ${t("devsettings.speed_cycle_intro")}
                </p>

                <div class="field">
                    <label>${t("devsettings.speed_steps_label")}</label>
                    <input
                        type="number"
                        min=${MIN_SPEED_STEPS}
                        max=${MAX_SPEED_STEPS}
                        step="1"
                        .value=${this._speedSteps}
                        @input=${(e: Event) =>
                            (this._speedSteps = (
                                e.target as HTMLInputElement
                            ).value)}
                        ?disabled=${this._busy}
                    />
                </div>

                <label class="check-row">
                    <input
                        type="checkbox"
                        .checked=${this._cycleIncludesOff}
                        @change=${(e: Event) =>
                            (this._cycleIncludesOff = (
                                e.target as HTMLInputElement
                            ).checked)}
                        ?disabled=${this._busy}
                    />
                    <span>${t("devsettings.speed_cycle_off_label")}</span>
                </label>

                ${this._cycleIncludesOff
                    ? ""
                    : html`
                      <div class="field">
                          <label>${t("devsettings.speed_cycle_turn_on_label")}</label>
                          <div class="select-wrap">
                              <select
                                  .value=${this._cycleTurnOn}
                                  @change=${(e: Event) =>
                                      (this._cycleTurnOn = (
                                          e.target as HTMLSelectElement
                                      ).value as SpeedCycleTurnOn)}
                                  ?disabled=${this._busy}
                              >
                                  <option
                                      value="resume"
                                      ?selected=${this._cycleTurnOn === "resume"}
                                  >
                                      ${t("devsettings.speed_cycle_turn_on_resume")}
                                  </option>
                                  <option
                                      value="speed_1"
                                      ?selected=${this._cycleTurnOn === "speed_1"}
                                  >
                                      ${t("devsettings.speed_cycle_turn_on_speed_1")}
                                  </option>
                              </select>
                              <span class="select-chevron" aria-hidden="true"></span>
                          </div>
                      </div>
                      `}

                <p class="section-explainer">
                    ${t("devsettings.speed_cycle_drift")}
                </p>
            </section>
        `;
    }

    /** No per-field explainer here (design ruling 2026-08-09, matches
     * the power section's own post-launch trim) -- field labels carry
     * the whole story. Two independent pickers: either can be picked,
     * changed, or cleared without touching the other, so there is no
     * shared "sensorPicked" gate the way power's threshold pair has
     * one. */
    private _renderClimateSection() {
        const tempCandidates = this._candidatesByDeviceClass(
            "temperature",
            this.device.temperature_sensor_entity_id,
        );
        const humidityCandidates = this._candidatesByDeviceClass(
            "humidity",
            this.device.humidity_sensor_entity_id,
        );
        const tempPicked = !!this._temperatureChoice;
        const humidityPicked = !!this._humidityChoice;
        const tempState = tempPicked
            ? this.hass?.states?.[this._temperatureChoice]
            : undefined;
        const humidityState = humidityPicked
            ? this.hass?.states?.[this._humidityChoice]
            : undefined;
        return html`
            <section class="settings-section section-climate">
                <h3 class="section-label">
                    ${t("devsettings.climate_section_label")}
                </h3>

                <p class="section-explainer">
                    ${t("devsettings.climate_intro")}
                </p>

                <div class="field">
                    <label>${t("devsettings.temp_sensor_label")}</label>
                    <div class="select-wrap">
                        <select
                            .value=${this._temperatureChoice}
                            @change=${this._onTemperatureChoiceChanged}
                            ?disabled=${this._busy}
                        >
                            <option value="">${t("devsettings.sensor_none")}</option>
                            ${tempCandidates.map(
                                (c) => html`
                                    <option
                                        value=${c.entityId}
                                        ?selected=${this._temperatureChoice === c.entityId}
                                    >
                                        ${c.name}
                                    </option>
                                `,
                            )}
                        </select>
                        <span class="select-chevron" aria-hidden="true"></span>
                    </div>
                </div>
                ${tempPicked
                    ? html`
                          <div class="live-readout">
                              ${this._renderLiveReadout(tempState)}
                          </div>
                      `
                    : ""}

                <div class="field">
                    <label>${t("devsettings.humidity_sensor_label")}</label>
                    <div class="select-wrap">
                        <select
                            .value=${this._humidityChoice}
                            @change=${this._onHumidityChoiceChanged}
                            ?disabled=${this._busy}
                        >
                            <option value="">${t("devsettings.sensor_none")}</option>
                            ${humidityCandidates.map(
                                (c) => html`
                                    <option
                                        value=${c.entityId}
                                        ?selected=${this._humidityChoice === c.entityId}
                                    >
                                        ${c.name}
                                    </option>
                                `,
                            )}
                        </select>
                        <span class="select-chevron" aria-hidden="true"></span>
                    </div>
                </div>
                ${humidityPicked
                    ? html`
                          <div class="live-readout">
                              ${this._renderLiveReadout(humidityState)}
                          </div>
                      `
                    : ""}
            </section>
        `;
    }

    /**
     * The closed field: what is chosen, in the shape of a list row (the
     * health dot, the name over the entity id), or None, with the caret
     * on the right. A combobox: click, Enter, Space or Arrow Down opens
     * the list.
     */
    private _renderSourceField(groups: SourceGroups) {
        const id = this._sensorChoice;
        const known = [...groups.power, ...groups.onOff].find(
            (c) => c.entityId === id,
        );
        const name = id
            ? (known?.name ??
              this.hass?.states?.[id]?.attributes?.friendly_name ??
              id)
            : t("devsettings.sensor_none");
        const open = this._picker.open;
        return html`<div
            class="source-field ${open ? "open" : ""}"
            role="combobox"
            tabindex=${this._busy ? "-1" : "0"}
            aria-labelledby="source-label"
            aria-haspopup="listbox"
            aria-expanded=${open ? "true" : "false"}
            aria-controls="source-listbox"
            aria-disabled=${this._busy ? "true" : "false"}
            title=${id ? `${name} · ${id}` : name}
            @click=${(e: Event) => this._pickerEvent({ kind: "field-click" }, e)}
            @keydown=${(e: KeyboardEvent) =>
                this._pickerEvent({ kind: "field-key", key: e.key }, e)}
        >
            ${this._renderSourceDot(id)}
            <span class="txt">
                <span class="iname">${name}</span>
                ${id ? html`<span class="iid">${id}</span>` : ""}
            </span>
            <span class="select-chevron" aria-hidden="true"></span>
        </div>`;
    }

    /**
     * The open list, floating over the dialog (ir-popover-styles): the
     * search, which takes focus, then None and the two groups. The
     * arrow keys move the active option from the search
     * (aria-activedescendant); headings are not options.
     */
    private _renderSourcePanel(shown: SourceGroups) {
        const place = this._panel;
        const options = pickerOptions(shown);
        const optionId = (entityId: string) =>
            `source-opt-${options.indexOf(entityId)}`;
        const active = this._picker.active;
        const style = place
            ? [
                  `left:${place.left + this._panelShift.dx}px`,
                  `width:${place.width}px`,
                  `max-height:${place.maxHeight}px`,
                  place.up
                      ? `bottom:${place.bottom - this._panelShift.dy}px`
                      : `top:${place.top + this._panelShift.dy}px`,
              ].join(";")
            : "visibility:hidden";
        const row = (entityId: string, name: string) =>
            this._renderSourceRow(entityId, name, optionId(entityId), active);
        return html`<div
            class="action-popover source-panel ${place?.up ? "up" : ""}"
            style=${style}
            @keydown=${(e: KeyboardEvent) =>
                this._pickerEvent({ kind: "panel-key", key: e.key }, e)}
        >
            <input
                class="source-search"
                type="text"
                .value=${this._picker.query}
                placeholder=${t("devsettings.source_search")}
                aria-label=${t("devsettings.source_search")}
                aria-controls="source-listbox"
                aria-activedescendant=${active !== null && options.includes(active)
                    ? optionId(active)
                    : ""}
                @input=${(e: Event) =>
                    this._pickerEvent({
                        kind: "query",
                        value: (e.target as HTMLInputElement).value,
                    })}
            />
            <div
                class="source-list"
                id="source-listbox"
                role="listbox"
                aria-labelledby="source-label"
            >
                ${row("", t("devsettings.sensor_none"))}
                ${shown.power.length
                    ? html`<div role="group" aria-label=${t("devsettings.power_group_label")}>
                          <div class="source-group" aria-hidden="true">
                              ${t("devsettings.power_group_label")}
                          </div>
                          ${shown.power.map((c) => row(c.entityId, c.name))}
                      </div>`
                    : ""}
                ${shown.onOff.length
                    ? html`<div role="group" aria-label=${t("devsettings.onoff_group_label")}>
                          <div class="source-group" aria-hidden="true">
                              ${t("devsettings.onoff_group_label")}
                              <span class="source-group-hint"
                                  >${t("devsettings.onoff_group_hint")}</span
                              >
                          </div>
                          ${shown.onOff.map((c) => row(c.entityId, c.name))}
                      </div>`
                    : ""}
                ${shown.power.length + shown.onOff.length === 0
                    ? html`<div class="source-none">
                          ${t("devsettings.source_no_match")}
                      </div>`
                    : ""}
            </div>
        </div>`;
    }

    private _renderSourceDot(entityId: string) {
        return entityId
            ? html`<span
                  class="dot ${healthDotClass(
                      isEntityOnline(this.hass?.states, entityId),
                  )}"
              ></span>`
            : html`<span class="dot-gap"></span>`;
    }

    /** One option of the open list, the shape of the RX-CAPTURE switch
     * search (ir-capture-switch-menu.ts): the health dot, the name over
     * the entity id, the chosen row tinted, the active one outlined.
     * None has no dot and no id. Not a button: the search keeps focus,
     * so a press here must not take it. */
    private _renderSourceRow(
        entityId: string,
        name: string,
        id: string,
        active: string | null,
    ) {
        const chosen = this._sensorChoice === entityId;
        return html`<div
            id=${id}
            class="source-row ${chosen ? "cur" : ""} ${active === entityId ? "active" : ""}"
            role="option"
            aria-selected=${chosen ? "true" : "false"}
            title=${entityId ? `${name} · ${entityId}` : name}
            @pointerdown=${(e: Event) => e.preventDefault()}
            @click=${() => this._pickerEvent({ kind: "row", entityId })}
        >
            ${this._renderSourceDot(entityId)}
            <span class="txt">
                <span class="iname">${name}</span>
                ${entityId ? html`<span class="iid">${entityId}</span>` : ""}
            </span>
        </div>`;
    }

    /** The dot signals "this number is live," full stop (design brief:
     * "stays green in both sections... independent of the
     * oxblood/cold-blue theming" -- and, same principle, independent
     * of the on/off verdict too). An earlier pass colored it by
     * classify_power_reading()'s on/off/hold verdict instead, which
     * read as "sensor might be broken" on a perfectly healthy reading
     * that just happened to sit in the off band -- corrected here.
     * An on/off source shows its state as it is ("Now: home"), live
     * when it is one of the four states that mean on or off. */
    private _renderLiveReadout(state: {
        state?: string;
        attributes?: { unit_of_measurement?: string };
    } | undefined, onOff = false) {
        if (!state || state.state === undefined) {
            return html`<span class="readout-dot readout-unknown"></span>
                ${t("devsettings.readout_unavailable")}`;
        }
        if (onOff) {
            const known = ["on", "off", "home", "not_home"].includes(
                state.state,
            );
            return html`<span
                    class="readout-dot ${known ? "readout-live" : "readout-unknown"}"
                ></span>
                ${t("devsettings.readout_now", { value: state.state })}`;
        }
        const raw = parseFloat(state.state);
        const unit = state.attributes?.unit_of_measurement ?? "";
        if (Number.isNaN(raw)) {
            const value = unit ? `${state.state} ${unit}` : state.state;
            return html`<span class="readout-dot readout-unknown"></span>
                ${t("devsettings.readout_now", { value })}`;
        }
        const value = unit ? `${raw} ${unit}` : `${raw}`;
        return html`<span class="readout-dot readout-live"></span>
            ${t("devsettings.readout_now", { value })}`;
    }

    static styles = [
        dialogStyles,
        css`
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            .check-row {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 4px 0 12px;
                font-size: 14px;
                color: var(--primary-text-color);
                cursor: pointer;
            }
            .pair-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                column-gap: 10px;
            }
            /* Destructive alone on the left, constructive pair on the
             * right, with a growing spacer between (punch list item
             * 20). The grey Close is gone: the dialog's own X already
             * closes it, and two close doors on one popup read as
             * clutter -- Escape and the X both still work. The
             * grouping lives in the markup rather than in a
             * justify-content mode, so the footer says its own shape:
             * Delete, gap, Duplicate, Save. */
            /* Mirror-door row (s10 .convert-grid/.convert-text/
             * .convert-btn-cell): description on the left, a
             * fixed-width button cell on the right so the button reads
             * as a standalone action rather than a right-aligned
             * label. section-label/section-explainer are the same
             * classes power/climate already use -- convert-label just
             * overrides the accent color (s10: HA's own --primary-color
             * blue, not a kind color -- this row isn't "device green"
             * or "remote gold," it's a neutral cross-kind action). */
            .convert-row {
                display: flex;
                align-items: center;
                gap: 14px;
            }
            .convert-text {
                flex: 1;
            }
            .convert-label {
                color: var(--primary-color);
            }
            .convert-btn-cell {
                flex: 0 0 116px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .convert-btn {
                width: 100%;
            }
            /* Duplicate: outlined GREEN_PEAK (#43a047 -- see
             * ir-origin-colors.ts's GREEN_PEAK comment; same token
             * ir-header-chip-group.ts's Emitters:/Receivers: groups
             * use, confirmed against s10's own .btn-outline-green, not
             * invented for this button). Hardcoded rather than
             * imported/unsafeCSS'd, matching this file's own existing
             * convention of hardcoded hex literals per accent (see
             * .settings-section.section-power/.section-climate above). */
            .duplicate-btn {
                background: none;
                border-color: #43a047;
                color: #43a047;
            }
            .duplicate-btn:hover:not(:disabled) {
                background: rgba(67, 160, 71, 0.14);
            }
            /* Delete: outlined ember -- the same #e65100
             * ir-icons.ts's .trash-btn convention already uses on
             * hover, colored at rest here per s10. */
            .delete-btn {
                background: none;
                border-color: #e65100;
                color: #e65100;
            }
            .delete-btn:hover:not(:disabled) {
                background: rgba(230, 81, 0, 0.14);
            }

            /* Section-accent styling (owner ruling 2026-08-09, design
             * brief "Section color treatment"): a light color WASH on
             * specific elements -- the section label, the entity
             * picker's border/chevron, the live-readout's background
             * -- explicitly NOT a sidebar rule. A left border was here
             * in an earlier build pass and got corrected out (bench
             * pass, post-launch): the design brief calls a left rule
             * out by name as the thing this treatment is NOT. CLIMATE
             * (climate-sensors.md) reuses this same anatomy in cold
             * blue via --section-accent / --section-accent-bright --
             * the brief specs a single cold-blue value for both,
             * unlike power's separate border/bright shades, so the
             * .section-climate modifier below repeats the one hex
             * twice on purpose rather than inventing a second shade. */
            .settings-section {
                margin: 16px 0;
            }
            /* Divider between settings sections (owner ruling
             * 2026-08-09): a plain gray rule, the standard seam for
             * however many sections this dialog ends up with over
             * time -- not power/climate-specific. Scoped to the
             * section-slot wrapper divs (_renderBody) rather than
             * .settings-section itself, since two sections' <section>
             * elements are never direct DOM siblings (each sits in
             * its own ?hidden wrapper) while the wrapper divs always
             * are. :not([hidden]) on both sides of the combinator
             * means a device missing a section (the wrapper stays in
             * the DOM but hidden) never leaves a dangling line with
             * nothing visible above it -- the rule only fires between
             * two sections that are both actually showing.
             *
             * GENERAL sibling, not adjacent (punch list item 20). With
             * "+" the pair had to be DOM-adjacent, so a flat device --
             * whose hidden climate wrapper sits between power and the
             * mirror door -- matched nothing and drew no divider at
             * all, while a matrix device drew two. Same dialog, two
             * looks, entirely because of which optional sections
             * happened to be present. "~" says what the rule always
             * meant: every visible section after the first gets a
             * seam above it, whatever is hidden in between.
             */
            .section-slot:not([hidden]) ~ .section-slot:not([hidden]) {
                border-top: 1px solid var(--divider-color);
                padding-top: 8px;
            }
            .settings-section.section-power {
                --section-accent: #8e3b3b;
                --section-accent-bright: #b05050;
                --section-wash: rgba(142, 59, 59, 0.12);
            }
            .settings-section.section-climate {
                --section-accent: #58a6d8;
                --section-accent-bright: #58a6d8;
                --section-wash: rgba(88, 166, 216, 0.12);
            }
            .section-label {
                margin: 0 0 4px;
                font-size: 0.95rem;
                font-weight: 500;
                color: var(--section-accent-bright, var(--primary-text-color));
            }
            /* Indented to line up with the entity picker's own text
             * (owner correction, bench pass -- the earlier 26px lined
             * up with the live-readout instead, which read as too
             * much for a caption). input[type="text"]/select get
             * padding: 8px from dialogStyles, so 8px here lands this
             * paragraph's text under the "F" of whatever's selected
             * in the dropdown. Shared by both the section intro
             * (before the picker) and the per-field explainer (under
             * it) -- same look, same alignment, two spots. */
            .section-explainer {
                margin: 0 0 12px;
                padding-left: 8px;
                font-size: 0.8rem;
                color: var(--secondary-text-color);
            }
            /* The per-field explainer ("The sensor must report
             * watts.") sits directly under the select with no gap by
             * default -- owner correction, bench pass: a little
             * standoff from the box above it reads better than
             * touching. Scoped to the .field instance only, so the
             * section-intro paragraph (which sits under the heading,
             * not a box) keeps its original spacing. */
            .field > .section-explainer {
                margin-top: 6px;
            }
            /* Labels bold, descriptive text (.section-explainer) not
             * -- owner ruling, bench pass. Scoped to these two
             * sections so it doesn't reach into the shared
             * dialogStyles .field label rule other dialogs use. */
            .section-power label,
            .section-climate label,
            .section-speed-cycle .field > label {
                font-weight: 600;
            }
            /* dialogStyles only styles input[type="text"]/select --
             * number inputs need the same anatomy spelled out here. */
            input[type="number"] {
                width: 100%;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                color: var(--primary-text-color);
                font-size: 0.95rem;
                font-family: inherit;
                box-sizing: border-box;
            }
            input[type="number"]:focus {
                outline: none;
                border-color: var(--primary-color);
            }
            .settings-section select,
            .settings-section input[type="text"],
            .settings-section input[type="number"] {
                border-color: var(--section-accent, var(--divider-color));
            }
            /* The dropdown chevron, in the section accent too (design
             * brief: "the entity picker's border and dropdown
             * chevron"). BENCH FIX: this never painted in the
             * previous two passes. Root cause, found by loading the
             * data-URI directly as an Image() in the console: the
             * inline SVG had a stray closing path tag after the
             * path's own self-close (self-close, then an extra
             * closing tag right after it) -- invalid XML, so
             * Chrome's SVG image decoder silently rejected the whole
             * thing and painted nothing, with no console error and no
             * hint in getComputedStyle (it just echoes the specified
             * value back, decoded or not). Fixed by dropping the
             * stray closing tag. Moved off the select element itself
             * onto this sibling span, layered on top via
             * position:absolute, while chasing the bug -- kept that
             * shape since it's a plainer element to reason about than
             * a native form control's background layer, even though
             * the select itself would have worked fine once the
             * markup was valid. The fill is hardcoded per section
             * rather than reading the CSS var, since a data-URI
             * background-image can't reference one -- POWER's copy
             * uses its --section-accent-bright (#b05050), CLIMATE's
             * copy below uses its single cold-blue value (#58a6d8)
             * the same way. */
            .select-wrap {
                position: relative;
            }
            .section-power select,
            .section-climate select,
            .section-speed-cycle select {
                appearance: none;
                -webkit-appearance: none;
                padding-right: 32px;
            }
            .section-power .select-chevron {
                position: absolute;
                top: 50%;
                right: 10px;
                width: 18px;
                height: 18px;
                transform: translateY(-50%);
                pointer-events: none;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23b05050' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-position: center;
                background-size: 18px;
            }
            .section-climate .select-chevron {
                position: absolute;
                top: 50%;
                right: 10px;
                width: 18px;
                height: 18px;
                transform: translateY(-50%);
                pointer-events: none;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%2358a6d8' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-position: center;
                background-size: 18px;
            }
            /* Speed cycle (GH Discussion #201) has no accent of its
             * own yet: neutral borders, and the chevron in the
             * secondary text grey. */
            .section-speed-cycle .select-chevron {
                position: absolute;
                top: 50%;
                right: 10px;
                width: 18px;
                height: 18px;
                transform: translateY(-50%);
                pointer-events: none;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23888888' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-position: center;
                background-size: 18px;
            }
            .settings-section select option {
                color: var(--primary-text-color);
                background: var(--card-background-color);
            }

            .live-readout {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 4px 0 0;
                padding: 8px 10px;
                border-radius: 6px;
                background: var(--section-wash, var(--secondary-background-color));
                font-size: 0.85rem;
                color: var(--primary-text-color);
            }
            .readout-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                flex: 0 0 auto;
            }
            /* Green whenever the readout has a genuine live number,
             * full stop -- design brief: "signals 'this number is
             * moving right now,' not which section it belongs to."
             * Not tied to the on/off verdict; a reading sitting in
             * the hysteresis band is just as live as one past a
             * threshold. */
            .readout-live {
                background: #66bb6a;
            }
            .readout-unknown {
                background: var(--disabled-text-color, #999);
                opacity: 0.5;
            }

            /* The state source picker: a closed field the height of the
               other inputs, and a floating list (ir-popover-styles) with
               the RX-CAPTURE switch search's rows
               (ir-capture-switch-menu.ts). */
            .source-field {
                position: relative;
                display: flex;
                align-items: center;
                gap: 10px;
                box-sizing: border-box;
                width: 100%;
                min-height: 38px;
                padding: 3px 34px 3px 10px;
                border: 1px solid var(--divider-color);
                border-radius: 4px;
                background: var(--card-background-color);
                color: var(--primary-text-color);
                font-size: 0.9rem;
                cursor: pointer;
            }
            .source-field:focus,
            .source-field.open {
                outline: none;
                border-color: var(--primary-color);
            }
            .source-field[aria-disabled="true"] {
                cursor: default;
                opacity: 0.6;
            }
            .action-popover.source-panel {
                display: flex;
                flex-direction: column;
                max-width: none;
                min-width: 0;
                box-sizing: border-box;
                padding: 6px;
                overflow: hidden;
            }
            .source-panel .source-search {
                flex: none;
                margin-bottom: 6px;
            }
            .source-list {
                flex: 1 1 auto;
                min-height: 0;
                overflow-y: auto;
                border-top: 1px solid var(--divider-color);
            }
            .source-group {
                display: flex;
                flex-direction: column;
                gap: 2px;
                padding: 9px 10px 5px;
                border-bottom: 1px solid var(--divider-color);
                background: var(--secondary-background-color);
                font-size: 0.7rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--secondary-text-color);
            }
            .source-group-hint {
                font-size: 0.75rem;
                text-transform: none;
                letter-spacing: normal;
                line-height: 1.35;
            }
            .source-row {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 7px 10px;
                border-bottom: 1px solid var(--divider-color);
                font-size: 0.9rem;
                color: var(--primary-text-color);
                cursor: pointer;
            }
            .source-row:hover {
                background: var(--secondary-background-color);
            }
            .source-row.cur {
                background: color-mix(in srgb, var(--primary-color) 10%, transparent);
            }
            .source-row.active {
                box-shadow: inset 0 0 0 1px var(--primary-color);
            }
            .source-field .dot,
            .source-field .dot-gap,
            .source-row .dot,
            .source-row .dot-gap {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                flex: none;
            }
            .source-field .txt,
            .source-row .txt {
                display: flex;
                flex-direction: column;
                min-width: 0;
            }
            .source-field .iname,
            .source-field .iid,
            .source-row .iname,
            .source-row .iid {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .source-field .iid,
            .source-row .iid {
                font-size: 0.7rem;
                color: var(--secondary-text-color);
                margin-top: 1px;
            }
            .source-none {
                padding: 14px 10px;
                color: var(--secondary-text-color);
                font-style: italic;
            }

            .save-btn {
                background: #3f8a4b;
                color: #fff;
                border-color: #3f8a4b;
            }
            .save-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
        `,
        popoverStyles,
        healthDotStyles,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-settings-dialog": IrDeviceSettingsDialog;
    }
}
