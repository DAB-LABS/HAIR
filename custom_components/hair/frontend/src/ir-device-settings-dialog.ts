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
 * STRINGS: every user-facing string in this file is a plain English
 * literal, not routed through t()/en.json. Commit 6 of this plan
 * (docs/internal/plans/device-settings-power-sensor-coding-plan.md)
 * owns wiring these through the locale system and syncing the other
 * nine languages -- doing that here, one commit early, would touch
 * en.json without the matching nine-locale updates the parity tests
 * (tests/test_locales.py) require, breaking the tree for this commit's
 * own sake.
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
 * uses for emitters. A "Custom entity ID" fallback option covers
 * template-sensor power meters that don't carry device_class "power"
 * (documented in device-settings-power-sensor.md's sensor-class
 * guidance).
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
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

    /** "" = no sensor, "__custom__" = the manual-entry fallback is
     * showing, otherwise a sensor.* entity id from the dropdown. */
    @state() private _sensorChoice = "";
    @state() private _customSensorId = "";
    @state() private _offBelow = "";
    @state() private _onAbove = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;

    firstUpdated(): void {
        const sensorId = this.device.power_sensor_entity_id ?? "";
        if (sensorId && !this._candidateSensors().some((c) => c.entityId === sensorId)) {
            this._sensorChoice = "__custom__";
            this._customSensorId = sensorId;
        } else {
            this._sensorChoice = sensorId;
        }
        this._offBelow =
            this.device.power_off_below_w?.toString() ??
            String(DEFAULT_OFF_BELOW_W);
        this._onAbove =
            this.device.power_on_above_w?.toString() ??
            String(DEFAULT_ON_ABOVE_W);
    }

    /** The sensor id actually in effect, whichever control set it. */
    private get _effectiveSensorId(): string {
        return this._sensorChoice === "__custom__"
            ? this._customSensorId.trim()
            : this._sensorChoice;
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
        out.sort((a, b) => a.name.localeCompare(b.name));
        return out;
    }

    private get _validationError(): string | null {
        if (!this._effectiveSensorId) return null;
        const off = parseFloat(this._offBelow);
        const on = parseFloat(this._onAbove);
        if (Number.isNaN(off) || Number.isNaN(on)) {
            return "Enter both thresholds in watts.";
        }
        if (on < off) {
            return "On above must be at or above off below.";
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
        const sensorId = this._effectiveSensorId || null;
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
                heading="Device settings"
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
                <p class="empty-state">
                    No device-specific settings for this device type yet.
                </p>
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
                    Close
                </button>
                <span class="spacer"></span>
                <button
                    class="action-btn save-btn"
                    @click=${this._save}
                    ?disabled=${this._busy || !!this._validationError}
                >
                    ${this._busy ? "Saving..." : "Save"}
                </button>
            </div>
        `;
    }

    private _renderPowerSection() {
        const candidates = this._candidateSensors();
        const sensorPicked = !!this._effectiveSensorId;
        const liveState = sensorPicked
            ? this.hass?.states?.[this._effectiveSensorId]
            : undefined;
        return html`
            <section class="settings-section section-power">
                <h3 class="section-label">Power monitoring</h3>
                <p class="section-explainer">The sensor must report watts.</p>

                <div class="field">
                    <label>Power sensor</label>
                    <select
                        .value=${this._sensorChoice}
                        @change=${this._onSensorChoiceChanged}
                        ?disabled=${this._busy}
                    >
                        <option value="">None</option>
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
                        <option
                            value="__custom__"
                            ?selected=${this._sensorChoice === "__custom__"}
                        >
                            Custom entity ID...
                        </option>
                    </select>
                </div>

                <div ?hidden=${this._sensorChoice !== "__custom__"} class="field">
                    <label>Sensor entity ID</label>
                    <input
                        type="text"
                        placeholder="sensor.living_room_tv_power"
                        .value=${this._customSensorId}
                        @input=${(e: Event) =>
                            (this._customSensorId = (
                                e.target as HTMLInputElement
                            ).value)}
                        ?disabled=${this._busy}
                    />
                </div>

                <div ?hidden=${!sensorPicked} class="pair-grid field">
                    <div>
                        <label>Off below (W)</label>
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
                        <label>On above (W)</label>
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

                <div ?hidden=${!sensorPicked} class="live-readout">
                    ${this._renderLiveReadout(liveState)}
                </div>

                <p ?hidden=${!sensorPicked} class="section-override-note">
                    Readings override the device's assumed on/off state.
                </p>
            </section>
        `;
    }

    private _renderLiveReadout(state: {
        state?: string;
        attributes?: { unit_of_measurement?: string };
    } | undefined) {
        if (!state || state.state === undefined) {
            return html`<span class="readout-dot readout-unknown"></span>
                Not available yet.`;
        }
        const raw = parseFloat(state.state);
        const unit = state.attributes?.unit_of_measurement ?? "";
        if (Number.isNaN(raw)) {
            return html`<span class="readout-dot readout-unknown"></span>
                Now: ${state.state}${unit ? ` ${unit}` : nothing}`;
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
        return html`<span class="readout-dot ${dotClass}"></span>
            Now: ${raw}${unit ? ` ${unit}` : nothing}`;
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

            /* Section-accent styling (owner ruling 2026-08-09): oxblood
             * for power monitoring, reused from ir-device-detail.ts's
             * SAVE TO CLOSET hover state. The CLIMATE section (next
             * pass) reuses this same anatomy in cold blue via
             * --section-accent / --section-accent-bright -- only the
             * .section-power modifier below is wired up today. */
            .settings-section {
                border-left: 3px solid var(--section-accent, transparent);
                padding-left: 12px;
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
            .section-override-note {
                font-size: 0.75rem;
                color: var(--secondary-text-color);
                margin: 8px 0 0;
                font-style: italic;
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
