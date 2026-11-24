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
 * Each section is a card that opens (settings-section-styles.ts holds
 * the rule and the one accent): its name over a one-line summary of
 * what is set. The first card a device gets opens with the dialog,
 * and so does one holding a validation problem, whose summary then
 * says the problem. Make a Remote is a card with its button on it.
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
 * THE POWER SECTION'S FIELDS (the state source picker, the readout,
 * the thresholds and the settle time) are ir-power-source-section.ts,
 * which the Remote settings dialog uses too; this dialog adds the
 * matrix Power button tick above them. The climate pickers are plain
 * <select>s, filtering on device_class "temperature" or "humidity"
 * (see _candidatesByDeviceClass); a stored sensor the filter no longer
 * matches is still offered, so it is never lost.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import { pinModeChoices, pinModeOf, pinModeShown, type PinMode } from "./pin-mode.js";
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
import {
    sectionAccentHost,
    settingsSectionStyles,
} from "./settings-section-styles.js";
import {
    type IrPowerSourceSection,
    renderLiveReadout,
} from "./ir-power-source-section.js";

export type SettingsSectionId = "power" | "climate" | "speed_cycle";

/** The cards that open, in the order they are drawn
 * (settings-section-styles.ts): where the state comes from, how the
 * device is driven, then other remotes. Make a Remote, an action,
 * follows them and does not open. */
type CardKey = SettingsSectionId | "relay";
const CARD_ORDER: readonly CardKey[] = ["power", "climate", "speed_cycle", "relay"];

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

@customElement("ir-device-settings-dialog")
export class IrDeviceSettingsDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public device!: IRDevice;
    /** Every Remote, for the pins section (GH #183): the ones whose
     * pinned_device_ids hold this device are listed there. */
    @property({ attribute: false }) public triggerRemotes: TriggerRemoteInfo[] =
        [];

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
    // Toggle power (GH #183): the matrix setting. Per pinning Remote,
    // what the pin does with its presses (GH #294, ``pin-mode.ts``).
    @state() private _powerToggles = false;
    // GH #323: a matrix with its own "on" code sends it before a state
    // from off. Absent in the stored config reads as ticked.
    @state() private _wakeWithOn = true;
    @state() private _modes: Record<string, PinMode> = {};
    @state() private _busy = false;
    @state() private _error: string | null = null;
    /** The cards that are open. Any number can be; Save saves every
     * section, open or not. */
    @state() private _open: ReadonlySet<CardKey> = new Set();

    updated(): void {
        this.toggleAttribute("dark", Boolean(this.hass?.themes?.darkMode));
    }

    firstUpdated(): void {
        this._powerToggles = this.device.power_toggles === true;
        this._wakeWithOn = this.device.entity_config?.wake_with_on !== false;
        this._modes = Object.fromEntries(
            this._pinningRemotes().map((r) => [r.id, pinModeOf(r, this.device.id)]),
        );
        this._temperatureChoice = this.device.temperature_sensor_entity_id ?? "";
        this._humidityChoice = this.device.humidity_sensor_entity_id ?? "";
        const config = this.device.entity_config;
        this._speedSteps = config?.fan_speed_steps?.toString() ?? "";
        this._cycleIncludesOff = config?.speed_cycle_includes_off === true;
        this._cycleTurnOn =
            config?.speed_cycle_turn_on === "speed_1" ? "speed_1" : "resume";
        // The first card opens, and so does one holding a problem.
        const first = CARD_ORDER.find((key) => this._cardShows(key));
        const problem = this._problemCard();
        this._open = new Set(
            [first, problem].filter((key): key is CardKey => !!key),
        );
    }

    /** Whether a card is drawn for this device at all. */
    private _cardShows(key: CardKey): boolean {
        if (key === "relay") return this._showsRelay();
        return settingsSections(this.device).includes(key);
    }

    /** The card whose fields hold the validation problem, if any. */
    private _problemCard(): CardKey | null {
        if (!this._validationError) return null;
        return settingsSections(this.device).includes("speed_cycle") &&
            Number.isNaN(speedStepsForSave(this._speedSteps))
            ? "speed_cycle"
            : "power";
    }

    private _toggleCard(key: CardKey): void {
        const open = new Set(this._open);
        if (open.has(key)) open.delete(key);
        else open.add(key);
        this._open = open;
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
        if (!settingsSections(this.device).includes("power")) return null;
        return this._power?.validationError ?? null;
    }

    /** The Power card's fields (ir-power-source-section.ts). */
    private get _power(): IrPowerSourceSection | null {
        return this.renderRoot?.querySelector("ir-power-source-section") ?? null;
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

    /** Whether the device's power goes round on one button: the matrix
     * setting as ticked now, or a flat device's toggle mapping. Decides
     * whether a pin can leave out Power. */
    private _toggles(): boolean {
        return this.device.matrix
            ? this._powerToggles
            : this.device.power_is_toggle === true;
    }

    /** Whether the pins section shows: some Remote pins this device
     * (GH #294; it showed only on toggle-power devices before). Outside
     * the settingsSections() list on purpose: it reads Remotes, and the
     * gear no longer depends on sections. */
    private _showsRelay(): boolean {
        return this._pinningRemotes().length > 0;
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
        const patch: Parameters<HairApi["updateDevice"]>[1] = {};
        if (sections.includes("power") && this._power) {
            Object.assign(patch, this._power.patch());
        }
        if (this.device.matrix) {
            patch.power_toggles = this._powerToggles;
        }
        if (this.device.matrix?.has_on) {
            patch.wake_with_on = this._wakeWithOn;
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
            const relayChanged = await this._savePinModes();
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

    /** Write each pin whose mode changed; true when any did. Runs after
     * the device's own save, so a power toggle ticked here is stored
     * before a pin asks to leave out Power. */
    private async _savePinModes(): Promise<boolean> {
        let changed = false;
        const toggles = this._toggles();
        for (const remote of this._pinningRemotes()) {
            const chosen = this._modes[remote.id];
            if (chosen === undefined) continue;
            const mode = pinModeShown(chosen, toggles);
            const before = pinModeOf(remote, this.device.id);
            if (mode === before) continue;
            await this.api.setPinMode(remote.id, this.device.id, mode);
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
        return html`
            <div ?hidden=${!this._error}>
                <ha-alert alert-type="error">${this._error}</ha-alert>
            </div>
            ${this._renderCard(
                "power",
                t("devsettings.power_title"),
                this._powerSummary(),
                this._renderPowerCard(),
            )}
            ${this._renderCard(
                "climate",
                t("devsettings.climate_section_label"),
                this._climateSummary(),
                this._renderClimateSection(),
            )}
            ${this._renderCard(
                "speed_cycle",
                t("devsettings.speed_cycle_section_label"),
                this._speedCycleSummary(),
                this._renderSpeedCycleSection(),
            )}
            ${this._renderCard(
                "relay",
                t("devsettings.relay_section_label"),
                this._pinningRemotes()
                    .map((remote) => remote.name)
                    .join(", "),
                this._renderRelaySection(),
            )}
            ${this._renderConvertSection()}
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
            <div class="card card-action section-convert">
                <div class="card-row">
                    <div class="card-text">
                        <h3 class="card-heading card-title">
                            ${t("devsettings.make_remote_title")}
                        </h3>
                        <span class="card-sum">
                            ${t("devsettings.make_remote_desc")}
                        </span>
                    </div>
                    <button
                        class="action-btn convert-btn card-action-btn"
                        @click=${this._requestMakeRemote}
                    >
                        ${t("devsettings.make_remote_btn")}
                    </button>
                </div>
            </div>
        `;
    }

    /** Whether the "wake with On" tick shows (GH #323): a matrix with its
     * own "on" code, and not while the one-Power-button tick is on,
     * whose path already sends its power code first. */
    private _showsWakeWithOn(): boolean {
        return this.device.matrix?.has_on === true && !this._powerToggles;
    }

    /** The Power card's body, in two groups. "How the unit turns on":
     * a matrix Device's Power button tick and, when its file has an
     * "on" code, the wake tick. "Power state": the source and what is
     * read from it, which every settings dialog with a Power section
     * shares (ir-power-source-section.ts). A device with nothing in the
     * first group (no matrix) shows the source alone, as before, with
     * no group headings. */
    private _renderPowerCard() {
        const turnsOn = Boolean(this.device.matrix);
        return html`
            ${turnsOn
                ? html`
                      <section class="settings-section section-power power-group">
                          <h4 class="power-group-head">
                              ${t("devsettings.power_group_turns_on")}
                          </h4>
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
                          ${this._showsWakeWithOn()
                              ? html`
                                    <label class="check-row">
                                        <input
                                            type="checkbox"
                                            class="wake-with-on"
                                            .checked=${this._wakeWithOn}
                                            @change=${(e: Event) =>
                                                (this._wakeWithOn = (
                                                    e.target as HTMLInputElement
                                                ).checked)}
                                            ?disabled=${this._busy}
                                        />
                                        <span>${t("devsettings.wake_with_on_label")}</span>
                                    </label>
                                    <p class="section-explainer">
                                        ${t("devsettings.wake_with_on_help")}
                                    </p>
                                `
                              : ""}
                      </section>
                      <h4 class="power-group-head power-group-divided">
                          ${t("devsettings.power_group_state")}
                      </h4>
                  `
                : ""}
            <ir-power-source-section
                .hass=${this.hass}
                .source=${this.device}
                .busy=${this._busy}
                @power-source-change=${() => this.requestUpdate()}
            ></ir-power-source-section>
        `;
    }

    /**
     * One card (settings-section-styles.ts): a heading button with the
     * section's name over its summary, and the section's fields under
     * it while open. A card this device does not get stays in the DOM,
     * hidden, like every other part of this dialog; so do a closed
     * card's fields, so the state source picker keeps its elements.
     */
    private _renderCard(
        key: CardKey,
        title: string,
        summary: string,
        body: unknown,
    ) {
        const open = this._open.has(key);
        return html`
            <div
                class="card card-${key} ${open ? "open" : ""}"
                ?hidden=${!this._cardShows(key)}
            >
                <h3 class="card-heading">
                    <button
                        type="button"
                        class="card-head"
                        aria-expanded=${open ? "true" : "false"}
                        aria-controls="card-body-${key}"
                        @click=${() => this._toggleCard(key)}
                    >
                        <span class="card-text">
                            <span class="card-title">${title}</span>
                            <span class="card-sum">${summary}</span>
                        </span>
                        <span class="card-fold" aria-hidden="true"></span>
                    </button>
                </h3>
                <div class="card-body" id="card-body-${key}" ?hidden=${!open}>
                    ${body}
                </div>
            </div>
        `;
    }

    /** What a closed card says. A card holding the validation problem
     * says the problem instead. */
    private _powerSummary(): string {
        if (this._problemCard() === "power") return this._validationError ?? "";
        return this._power?.summary ?? "";
    }

    private _climateSummary(): string {
        const readings = [this._temperatureChoice, this._humidityChoice]
            .filter((id) => !!id)
            .map((id) => {
                const state = this.hass?.states?.[id];
                const unit = state?.attributes?.unit_of_measurement ?? "";
                const raw = parseFloat(state?.state ?? "");
                if (Number.isNaN(raw)) {
                    return state?.attributes?.friendly_name ?? id;
                }
                return unit ? `${raw} ${unit}` : `${raw}`;
            });
        return readings.length
            ? readings.join(" · ")
            : t("devsettings.sum_climate_none");
    }

    private _speedCycleSummary(): string {
        if (this._problemCard() === "speed_cycle") {
            return this._validationError ?? "";
        }
        if (!this._speedSteps) return t("devsettings.sum_speed_unset");
        return [
            t("devsettings.sum_speed_count", { count: this._speedSteps }),
            this._cycleIncludesOff
                ? t("devsettings.sum_speed_off")
                : t(
                      this._cycleTurnOn === "speed_1"
                          ? "devsettings.speed_cycle_turn_on_speed_1"
                          : "devsettings.speed_cycle_turn_on_resume",
                  ),
        ].join(" · ");
    }

    /** Pinned remotes (GH #294, GH #183): per Remote pinning this
     * device, one menu: send every press, send every press but Power (a
     * toggle-power device only), or track only and send nothing. The
     * line under it says what the choice does. */
    private _renderRelaySection() {
        const toggles = this._toggles();
        const choices = pinModeChoices(toggles);
        return html`
            <section class="settings-section section-relay">
                ${this._pinningRemotes().map((remote) => {
                    const mode = pinModeShown(this._modes[remote.id] ?? "send", toggles);
                    return html`
                        <div class="field pin-row">
                            <label for=${`pin-${remote.id}`}
                                >${t("devsettings.pin_remote_label")}
                                <span class="pin-remote-name">${remote.name}</span></label
                            >
                            <div class="select-wrap">
                                <select
                                    id=${`pin-${remote.id}`}
                                    .value=${mode}
                                    @change=${(e: Event) =>
                                        (this._modes = {
                                            ...this._modes,
                                            [remote.id]: (e.target as HTMLSelectElement)
                                                .value as PinMode,
                                        })}
                                    ?disabled=${this._busy}
                                >
                                    ${choices.map(
                                        (choice) => html`<option
                                            value=${choice}
                                            ?selected=${mode === choice}
                                        >
                                            ${t(`devsettings.pin_mode_${choice}`)}
                                        </option>`,
                                    )}
                                </select>
                                <span class="select-chevron" aria-hidden="true"></span>
                            </div>
                            <p class="section-explainer pin-desc">
                                ${t(`devsettings.pin_mode_${mode}_desc`)}
                            </p>
                        </div>
                    `;
                })}
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
                              ${renderLiveReadout(tempState)}
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
                              ${renderLiveReadout(humidityState)}
                          </div>
                      `
                    : ""}
            </section>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            /* Destructive alone on the left, constructive pair on the
             * right, with a growing spacer between (punch list item
             * 20). The grey Close is gone: the dialog's own X already
             * closes it, and two close doors on one popup read as
             * clutter -- Escape and the X both still work. The
             * grouping lives in the markup rather than in a
             * justify-content mode, so the footer says its own shape:
             * Delete, gap, Duplicate, Save. */
            /* Duplicate: outlined GREEN_PEAK (#43a047 -- see
             * ir-origin-colors.ts's GREEN_PEAK comment; same token
             * ir-header-chip-group.ts's Emitters:/Receivers: groups
             * use, confirmed against s10's own .btn-outline-green, not
             * invented for this button). The footer keeps its own
             * colours; the sections take theirs from
             * settings-section-styles.ts. */
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

            /* Pinned remotes: "Pinned remote:" muted, the remote's name
             * in full text colour, the menu under it, and the line that
             * says what the choice does. Scoped so it wins over the
             * shared bold field label (settings-section-styles.ts). */
            .settings-section .field.pin-row > label {
                font-weight: 400;
                color: var(--secondary-text-color);
            }
            .pin-remote-name {
                color: var(--primary-text-color);
                font-weight: 500;
                margin-left: 4px;
            }
            .pin-desc {
                margin: 6px 0 0;
            }
            /* The Power card's two groups (GH #323): a quiet small-caps
             * heading in the text colours the cards already use, and a
             * thin divider above the second. No new colour values. */
            .power-group-head {
                margin: 0 0 8px;
                font-size: 0.7rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--secondary-text-color);
            }
            .power-group-divided {
                margin-top: 4px;
                padding-top: 12px;
                border-top: 1px solid var(--divider-color);
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
        sectionAccentHost,
        settingsSectionStyles,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-settings-dialog": IrDeviceSettingsDialog;
    }
}
