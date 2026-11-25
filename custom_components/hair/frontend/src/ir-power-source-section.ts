/**
 * The Power section's fields: a state source and what is read from it.
 *
 * One element for every settings dialog that has a Power section, a
 * Device's and a typed Remote's, so the two can never drift apart:
 * the source picker, the live readout, the two thresholds and the
 * settle time, with their explainers. The dialog around it owns the
 * card, the Save and anything else in the section (a matrix Device's
 * Power button tick goes above it).
 *
 * THE PICKER is house-built rather than <ha-entity-picker>: that
 * component leans on the lazy-loaded <ha-combo-box>/<ha-textfield>
 * family, which renders as an empty, unfocusable shell inside a custom
 * panel. A closed field shows what is chosen and opens a floating list
 * (a combobox; ir-capture-switch-menu.ts is the nearest precedent): a
 * search over None, then the "sensor" entities that look like power
 * sensors (device_class "power", or a W/kW unit), then the on/off
 * entities a state can be read from, each group under its heading and
 * sorted by name (state-source.ts). The search matches a name or an
 * entity id and never hides the chosen row; how the field and the list
 * answer clicks and keys is pickerStep's. A stored source the filter no
 * longer matches is still offered, so it is never lost.
 *
 * The dialog reads the result through ``validationError`` and
 * ``patch()``, and hears every edit as a ``power-source-change`` event,
 * so its card summary (``summary``) and its Save keep up.
 */
import { LitElement, html, css, type TemplateResult } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import { isEntityOnline } from "./entity-health.js";
import { dotClass } from "./hair-colors.js";
import { healthDotStyles } from "./ir-header-chip-styles.js";
import { popoverStyles } from "./ir-popover-styles.js";
import { settingsSectionStyles } from "./settings-section-styles.js";
import {
    PANEL_GAP,
    PICKER_CLOSED,
    filterSourceGroups,
    isOnOffEntity,
    pickerOptions,
    pickerStep,
    placePanel,
    settleCapFor,
    settleDefaultFor,
    settleOnPick,
    stateSourceCandidates,
    stateSourcePatch,
    type PanelPlacement,
    type PickerEvent,
    type PickerState,
    type SourceGroups,
} from "./state-source.js";

/** The four stored fields a Device and a typed Remote share. */
export interface PowerSource {
    power_sensor_entity_id: string | null;
    power_off_below_w: number | null;
    power_on_above_w: number | null;
    power_settle_s: number | null;
}

const DEFAULT_OFF_BELOW_W = 5;
const DEFAULT_ON_ABOVE_W = 10;

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

/** A live reading, for the Power section and a dialog's other sensor
 * fields (the climate sensors) alike. */
export interface ReadoutState {
    state?: string;
    attributes?: { unit_of_measurement?: string };
}

@customElement("ir-power-source-section")
export class IrPowerSourceSection extends LitElement {
    @property({ attribute: false }) public hass: any;
    /** What is stored now; the fields start from it. */
    @property({ attribute: false }) public source: PowerSource | null = null;
    @property({ type: Boolean }) public busy = false;
    /** A typed Remote's section: its window opens on a heard Power
     * press rather than a send, and the words say so. */
    @property({ type: Boolean }) public forRemote = false;

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
    private _loaded = false;

    // The dialog's own busy flag, under the name the moved code reads.
    private get _busy(): boolean {
        return this.busy;
    }

    willUpdate(): void {
        if (this._loaded || this.source === null) return;
        this._loaded = true;
        const source = this.source;
        this._sensorChoice = source.power_sensor_entity_id ?? "";
        this._offBelow =
            source.power_off_below_w?.toString() ?? String(DEFAULT_OFF_BELOW_W);
        this._onAbove =
            source.power_on_above_w?.toString() ?? String(DEFAULT_ON_ABOVE_W);
        // ?? and not ||: a stored 0 is the opt-out and must show as 0.
        this._settle =
            source.power_settle_s?.toString() ??
            String(settleDefaultFor(source.power_sensor_entity_id));
    }

    updated(changed: Map<string, unknown>): void {
        const fields = ["_sensorChoice", "_offBelow", "_onAbove", "_settle"];
        if (fields.some((name) => changed.has(name))) {
            this.dispatchEvent(new CustomEvent("power-source-change"));
        }
    }

    /** What is wrong with the fields, or null. An on/off entity is read
     * by its state: no thresholds to check. */
    get validationError(): string | null {
        if (!this._sensorChoice) return null;
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

    /** The four fields to save, as the update doors take them. */
    patch(): PowerSource {
        const sensorId = this._sensorChoice || null;
        return stateSourcePatch(
            sensorId,
            this._offBelow,
            this._onAbove,
            sensorId ? this._settleForSave() : null,
        );
    }

    /** The card's one line: the source and where it reads on, or that
     * there is none. */
    get summary(): string {
        const id = this._sensorChoice;
        if (!id) {
            return t(
                this.forRemote
                    ? "devsettings.sum_power_none_remote"
                    : "devsettings.sum_power_none",
            );
        }
        const name = this.hass?.states?.[id]?.attributes?.friendly_name ?? id;
        if (isOnOffEntity(id)) return name;
        return t("devsettings.sum_power_watts", { name, watts: this._onAbove });
    }

    render() {
        return this._renderPowerSection();
    }

    /** A row of the state source picker was chosen ("" is None). */
    private _pickSource(entityId: string): void {
        if (this._busy || entityId === this._sensorChoice) return;
        const previous = this._sensorChoice;
        this._sensorChoice = entityId;
        if (entityId) {
            this._settle = settleOnPick(entityId, this._settle, previous);
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
            this.source?.power_sensor_entity_id ?? null,
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

    /** What the settle field saves as. A device still on its source's
     * default that nobody changed stays on the default (null), so it
     * keeps following it; an empty field also means the default.
     * Anything else is clamped into the range the backend accepts for
     * the chosen source. */
    private _settleForSave(): number | null {
        const value = parseFloat(this._settle);
        if (Number.isNaN(value)) return null;
        if (
            this.source?.power_settle_s == null &&
            value === settleDefaultFor(this._sensorChoice)
        ) {
            return null;
        }
        return Math.min(
            settleCapFor(this._sensorChoice),
            Math.max(0, value),
        );
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
                <p class="section-explainer">
                    ${t(
                        this.forRemote
                            ? "devsettings.power_intro_remote"
                            : "devsettings.power_intro",
                    )}
                </p>

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
                                      this.forRemote
                                          ? onOff
                                              ? "devsettings.settle_help_onoff_remote"
                                              : "devsettings.settle_help_remote"
                                          : onOff
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
            ${this._renderSourceDot(id, true)}
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

    /** The source's health dot: bright on the closed field, which names
     *  the source in use, dull in the list, where nothing is picked yet,
     *  as every picker's dots are. */
    private _renderSourceDot(entityId: string, bright = false) {
        return entityId
            ? html`<span
                  class="dot ${dotClass(isEntityOnline(this.hass?.states, entityId), bright)}"
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

    private _renderLiveReadout(state: ReadoutState | undefined, onOff = false) {
        return renderLiveReadout(state, onOff);
    }

    static styles = [
        dialogStyles,
        settingsSectionStyles,
        css`
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

        `,
        popoverStyles,
        healthDotStyles,
    ];
}

/** A live reading: "Now: 742 W" with a dot that says only that the
 * number is live, whatever section it is in and whatever on/off verdict
 * it gives (a reading in the hysteresis band is as live as any). An
 * on/off source shows its state as it is ("Now: home"), live when it is
 * one of the four states that mean on or off. */
export function renderLiveReadout(
    state: ReadoutState | undefined,
    onOff = false,
): TemplateResult {
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

declare global {
    interface HTMLElementTagNameMap {
        "ir-power-source-section": IrPowerSourceSection;
    }
}
