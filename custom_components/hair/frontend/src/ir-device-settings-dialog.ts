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

                <p class="section-explainer">
                    ${t("devsettings.power_intro")}
                </p>

                <div class="field">
                    <label>${t("devsettings.sensor_label")}</label>
                    <div class="select-wrap">
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
                        <span class="select-chevron" aria-hidden="true"></span>
                    </div>
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

    /** The dot signals "this number is live," full stop (design brief:
     * "stays green in both sections... independent of the
     * oxblood/cold-blue theming" -- and, same principle, independent
     * of the on/off verdict too). An earlier pass colored it by
     * classify_power_reading()'s on/off/hold verdict instead, which
     * read as "sensor might be broken" on a perfectly healthy reading
     * that just happened to sit in the off band -- corrected here. */
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
             * -- owner ruling, bench pass. Scoped to this section so
             * it doesn't reach into the shared dialogStyles .field
             * label rule other dialogs use. */
            .section-power label {
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
             * markup was valid. The fill is hardcoded to POWER's
             * --section-accent-bright (#b05050) rather than reading
             * the CSS var, since a data-URI background-image can't
             * reference one -- CLIMATE (next pass) will need its own
             * .section-climate chevron rule with a cold-blue fill
             * rather than inheriting this one. */
            .select-wrap {
                position: relative;
            }
            .section-power select {
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
