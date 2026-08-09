/**
 * Device settings dialog (Device Settings, v0.9.9, coding plan commit
 * 5 of 6). Opens from the wrench/screwdriver button in the device
 * detail meta row (ir-device-detail.ts) and holds whatever per-device
 * settings don't belong on the main card -- power monitoring today,
 * climate temperature/humidity sensors in a later pass.
 *
 * `settingsSections(device)` is the single source of truth for which
 * sections a device gets. It gates BOTH the settings button's
 * visibility (ir-device-detail.ts) and this dialog's rendered content,
 * so they can never disagree -- there is no placeholder dialog, ever.
 * For this pass it returns `['power']` for the device types that can
 * plausibly draw current (ac, media_player, fan, light, switch) and
 * `[]` for everything else (screen, other); CLIMATE is deliberately
 * held back (design brief: "mocked for layout only, ships later") even
 * though the section-accent styling below already anticipates it.
 *
 * STRINGS: commit 5 shipped every user-facing string here as a plain
 * English literal rather than routing through t()/en.json, since
 * touching en.json without the matching nine-locale sync would have
 * broken the parity tests (tests/test_locales.py). Commit 6 wires
 * everything through the "devsettings.*" locale namespace (plus the
 * existing common.close/common.save/common.saving keys for the
 * action bar) and adds the nine-language translations alongside it,
 * landing both halves together so the tree stays green throughout.
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
 * work without, the sensor picker below is a plain <select> populated
 * by scanning this.hass.states for domain "sensor" entities that look
 * like power sensors (device_class "power", or a W/kW unit) -- the
 * same direct-hass.states-scan convention ir-emitter-picker.ts already
 * uses for emitters. No manual entity-ID fallback (owner ruling
 * 2026-08-09, post-launch bench pass): the design brief specs a
 * picker only, so a device whose currently-configured sensor doesn't
 * match the power-ish filter still gets it injected into the
 * candidate list (see _candidateSensors) rather than losing it.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { DeviceTypeId, IRDevice } from "./types.js";

export type SettingsSectionId = "power";

const POWER_ELIGIBLE_TYPES: ReadonlySet<DeviceTypeId> = new Set([
    "ac",
    "media_player",
    "fan",
    "light",
    "switch",
]);

/** Single source of truth for which sections a device gets. See the
 * file header comment -- this must stay in lockstep between the
 * settings button (ir-device-detail.ts) and this dialog. */
export function settingsSections(
    device: Pick<IRDevice, "device_type">,
): SettingsSectionId[] {
    const sections: SettingsSectionId[] = [];
    if (POWER_ELIGIBLE_TYPES.has(device.device_type)) {
        sections.push("power");
    }
    return sections;
}

interface PowerSensorCandidate {
    entityId: string;
    name: string;
}

const DEFAULT_OFF_BELOW_W = 5;
const DEFAULT_ON_ABOVE_W = 10;

/** Mirrors power_monitor.classify_power_reading() (backend, commit 2)
 * so the live readout's status dot agrees with what will actually
 * fire a correction -- a kW reading is converted to watts first, same
 * as the backend, so both sides compare in watts. */
function classifyPowerReading(
    valueW: number | null,
    offBelowW: number | null,
    onAboveW: number | null,
): "on" | "off" | null {
    if (valueW === null || offBelowW === null || onAboveW === null) {
        return null;
    }
    if (valueW <= offBelowW) return "off";
    if (valueW >= onAboveW) return "on";
    return null;
}

@customElement("ir-device-settings-dialog")
export class IrDeviceSettingsDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public device!: IRDevice;

    /** "" = no sensor, otherwise a sensor.* entity id from the picker. */
    @state() private _sensorChoice = "";
    @state() private _offBelow = "";
    @state() private _onAbove = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;

    firstUpdated(): void {
        this._sensorChoice = this.device.power_sensor_entity_id ?? "";
        this._offBelow =
            this.device.power_off_below_w?.toString() ??
            String(DEFAULT_OFF_BELOW_W);
        this._onAbove =
            this.device.power_on_above_w?.toString() ??
            String(DEFAULT_ON_ABOVE_W);
    }

    private _candidateSensors(): PowerSensorCandidate[] {
        const states = (this.hass?.states ?? {}) as Record<
            string,
            {
                state?: string;
                attributes: {
                    friendly_name?: string;
                    device_class?: string;
                    unit_of_measurement?: string;
                };
            }
        >;
        const out: PowerSensorCandidate[] = [];
        for (const [entityId, st] of Object.entries(states)) {
            if (!entityId.startsWith("sensor.")) continue;
            const unit = st.attributes.unit_of_measurement;
            const isPower =
                st.attributes.device_class === "power" ||
                unit === "W" ||
                unit === "kW";
            if (!isPower) continue;
            out.push({
                entityId,
                name: st.attributes.friendly_name ?? entityId,
            });
        }
        // The device's currently-configured sensor always stays
        // selectable, even if it no longer matches the power-ish
        // filter above (a template sensor whose device_class/unit
        // changed, for instance) -- reopening this dialog must never
        // silently drop what's already saved.
        const current = this.device.power_sensor_entity_id;
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
        if (!this._sensorChoice) return null;
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

    private _onSensorChoiceChanged(e: Event): void {
        this._sensorChoice = (e.target as HTMLSelectElement).value;
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
        const sensorId = this._sensorChoice || null;
        try {
            await this.api.updateDevice(this.device.id, {
                power_sensor_entity_id: sensorId,
                power_off_below_w: sensorId ? parseFloat(this._offBelow) : null,
                power_on_above_w: sensorId ? parseFloat(this._onAbove) : null,
            });
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
            <div ?hidden=${sections.length > 0}>
                <p class="empty-state">${t("devsettings.no_sections")}</p>
            </div>
            <div ?hidden=${!sections.includes("power")}>
                ${this._renderPowerSection()}
            </div>
            <div class="dialog-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    ${t("common.close")}
                </button>
                <span class="spacer"></span>
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

    private _renderPowerSection() {
        const candidates = this._candidateSensors();
        const sensorPicked = !!this._sensorChoice;
        const liveState = sensorPicked
            ? this.hass?.states?.[this._sensorChoice]
            : undefined;
        return html`
            <section class="settings-section section-power">
                <h3 class="section-label">
                    ${t("devsettings.power_section_label")}
                </h3>

                <div class="field">
                    <label>${t("devsettings.sensor_label")}</label>
                    <select
                        .value=${this._sensorChoice}
                        @change=${this._onSensorChoiceChanged}
                        ?disabled=${this._busy}
                    >
                        <option value="">${t("devsettings.sensor_none")}</option>
                        ${candidates.map(
                            (c) => html`
                                <option
                                    value=${c.entityId}
                                    ?selected=${this._sensorChoice === c.entityId}
                                >
                                    ${c.name}
                                </option>
                            `,
                        )}
                    </select>
                    <p class="section-explainer">
                        ${t("devsettings.power_explainer")}
                    </p>
                </div>

                ${sensorPicked
                    ? html`
                          <div class="live-readout">
                              ${this._renderLiveReadout(liveState)}
                          </div>

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
            </section>
        `;
    }

    private _renderLiveReadout(state: {
        state?: string;
        attributes?: { unit_of_measurement?: string };
    } | undefined) {
        if (!state || state.state === undefined) {
            return html`<span class="readout-dot readout-unknown"></span>
                ${t("devsettings.readout_unavailable")}`;
        }
        const raw = parseFloat(state.state);
        const unit = state.attributes?.unit_of_measurement ?? "";
        if (Number.isNaN(raw)) {
            const value = unit ? `${state.state} ${unit}` : state.state;
            return html`<span class="readout-dot readout-unknown"></span>
                ${t("devsettings.readout_now", { value })}`;
        }
        const valueW = unit === "kW" ? raw * 1000 : raw;
        const offBelow = parseFloat(this._offBelow);
        const onAbove = parseFloat(this._onAbove);
        const verdict = classifyPowerReading(
            valueW,
            Number.isNaN(offBelow) ? null : offBelow,
            Number.isNaN(onAbove) ? null : onAbove,
        );
        const dotClass =
            verdict === "on"
                ? "readout-on"
                : verdict === "off"
                  ? "readout-off"
                  : "readout-hold";
        const value = unit ? `${raw} ${unit}` : `${raw}`;
        return html`<span class="readout-dot ${dotClass}"></span>
            ${t("devsettings.readout_now", { value })}`;
    }

    static styles = [
        dialogStyles,
        css`
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            .empty-state {
                color: var(--secondary-text-color);
                font-size: 0.9rem;
                margin: 8px 0 4px;
            }
            .pair-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                column-gap: 10px;
            }
            /* CLOSE-left/SAVE-right idiom (ir-claims-ledger.ts,
             * ir-comb-report.ts, ir-save-perfect-dialog.ts): dialogStyles'
             * .dialog-actions is flex-end by default, so this spacer is
             * what actually pushes Close to the left. */
            .spacer {
                flex: 1;
            }

            /* Section-accent styling (owner ruling 2026-08-09, design
             * brief "Section color treatment"): a light color WASH on
             * specific elements -- the section label, the entity
             * picker's border/chevron, the live-readout's background
             * -- explicitly NOT a sidebar rule. A left border was here
             * in an earlier build pass and got corrected out (bench
             * pass, post-launch): the design brief calls a left rule
             * out by name as the thing this treatment is NOT. The
             * CLIMATE section (next pass) reuses this same anatomy in
             * cold blue via --section-accent / --section-accent-bright
             * -- only the .section-power modifier below is wired up
             * today. */
            .settings-section {
                margin: 16px 0;
            }
            .settings-section.section-power {
                --section-accent: #8e3b3b;
                --section-accent-bright: #b05050;
                --section-wash: rgba(142, 59, 59, 0.12);
            }
            .section-label {
                margin: 0 0 4px;
                font-size: 0.95rem;
                font-weight: 500;
                color: var(--section-accent-bright, var(--primary-text-color));
            }
            .section-explainer {
                margin: 0 0 12px;
                font-size: 0.8rem;
                color: var(--secondary-text-color);
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
             * chevron"). Native <select> arrows aren't stylable via a
             * CSS color property, so this replaces the UA arrow with
             * an inline SVG. The fill is hardcoded to POWER's
             * --section-accent-bright (#b05050) rather than reading
             * the CSS var, since a data-URI background-image can't
             * reference one -- CLIMATE (next pass) will need its own
             * .section-climate select rule with a cold-blue chevron
             * rather than inheriting this one. */
            .section-power select {
                appearance: none;
                -webkit-appearance: none;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23b05050' d='M7 10l5 5 5-5z'/%3E%3C/path%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-position: right 10px center;
                background-size: 18px;
                padding-right: 32px;
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
            .readout-on {
                background: #66bb6a;
            }
            .readout-off {
                background: #999;
            }
            .readout-hold {
                background: #d9a441;
            }
            .readout-unknown {
                background: var(--disabled-text-color, #999);
                opacity: 0.5;
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
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-settings-dialog": IrDeviceSettingsDialog;
    }
}
