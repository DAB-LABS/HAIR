/**
 * The step picker for a grouped command (grouped-signals.md).
 *
 * Devices come up closed, each with the rows' chevron. Open one and its
 * commands drop down under it; tap one to add it; roll it back up.
 * Several devices can be open at once: opening one doesn't snap another
 * shut under the finger, and search already opens several, so it's one
 * rule for both. A closed device says how many of its commands are in
 * the group already. The group's own device is first (the server sends
 * it first). A device with no blaster and a command that can't be a step
 * stay in the list, greyed, with the reason. A device with nothing to
 * add (no blaster, no commands, only commands that can't be steps, or a
 * climate matrix device with no saved states) is greyed at its row from
 * the start, with no chevron, and says why. Each device row starts with
 * the Devices page's IR and RF glyphs, both on a device that has both.
 *
 * The IR and RF glyphs right of the title filter the device list, the
 * Sniffer's toggles and looks. They are not remembered: both are on
 * every time the picker opens, and one that is off shows dimmed. Search
 * runs inside what the filter leaves.
 *
 * Search (`pickerView`) opens every device with a match and shows only
 * the matching commands; clearing it puts the list back as it was left.
 *
 * Each command row starts with a green ADD chip, the panel's own action
 * chip, with the shared count dot on its corner once that command is in
 * the group (1, 2, ...): a command can be added more than once, and the
 * dot says how many times it is in. Clicking ADD adds it and the dot goes
 * up; nothing else happens. The right of a command row is empty; a
 * greyed row has no ADD, only its reason there.
 *
 * ADD STAGES; THE GREEN BUTTON ADDS. The dots and the green counts move
 * on each ADD, but nothing is saved until the filled green button at the
 * bottom, which says what it will do: "Add 1 signal", "Add 3 signals".
 * The X, Escape, or a click outside drop what is staged; a click outside
 * is ignored while something is staged, so a stray click never throws
 * picks away. With nothing staged the button is a plain "Close".
 *
 * THE TOP EDGE STAYS PUT. The dialog is centred once, when its list has
 * loaded, and from then on its top and width are fixed: opening a device
 * grows it downward, the list scrolls inside once it reaches the bottom
 * of the window, and closing one never moves the top. Re-centring on
 * every open made the list jump out from under the pointer.
 *
 * Emits `add` {picks: [{device_id, command_id}, ...]} in the order they
 * were staged, then `closed`; or `closed` alone. In `replace` mode (a
 * missing step's "Pick again") one ADD emits `pick` {device_id,
 * command_id} and closes, and the button is "Cancel".
 */
import { LitElement, html, css, nothing, unsafeCSS } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { GroupCandidateDevice } from "./types.js";
import { GROUP_HUE, GROUP_MAX_STEPS, commandsInGroup, deviceBlocked, pickerView } from "./group-steps.js";
import { radioBandOf } from "./sniffer-filter.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";
import { protoGlyphStyles, renderProtoGlyph } from "./ir-proto-glyph.js";
import { filterGlyphStyles } from "./filter-glyph-styles.js";
import { mediaShows, type MediaShow } from "./media-filter.js";
import type { Medium } from "./types.js";
import "./ir-count-dot.js";

/** A radio row's band, "433.92 MHz", as every radio row says it. */
export function bandText(row: { medium?: string; rf_frequency_hz?: number | null }): string {
    const band = radioBandOf(row);
    return band ? t("listen.band", { band }) : "";
}

const REASON_KEY: Record<string, string> = {
    rolling: "group.reason_rolling",
    lattice: "group.reason_lattice",
    no_blaster: "group.reason_no_blaster",
};

/** A greyed device row's reason (deviceBlocked). */
const BLOCKED_KEY: Record<string, string> = {
    no_blaster: "group.reason_no_blaster",
    matrix: "group.reason_matrix_empty",
    empty: "group.reason_empty",
    nothing: "group.reason_nothing",
};

@customElement("ir-group-picker")
export class IrGroupPicker extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    /** The device the group lives on. */
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public groupName = "";
    /** The group's steps now, for the counts and the ticks. */
    @property({ attribute: false }) public steps: { device_id: string; command_id: string }[] = [];
    /** One tap picks and closes (a missing step's "Pick again"). */
    @property({ type: Boolean }) public replace = false;

    @state() private _devices: GroupCandidateDevice[] | null = null;
    @state() private _open = new Set<string>();
    @state() private _query = "";
    /** What ADD has staged, in order; the green button adds them. */
    @state() private _picks: { device_id: string; command_id: string }[] = [];
    /** The same, counted by "device/command", for the dots and counts. */
    @state() private _staged = new Map<string, number>();
    /** The IR and RF filter. Not remembered: both on at every open. */
    @state() private _show: MediaShow = { ir: true, rf: true };
    /** The dialog's fixed top edge, set once the list has loaded. */
    @state() private _top: number | null = null;

    protected updated(): void {
        if (this._top !== null || this._devices === null) return;
        const dialog = this.renderRoot.querySelector<HTMLElement>(".dialog");
        if (!dialog) return;
        const height = dialog.getBoundingClientRect().height;
        this._top = Math.max(16, Math.round((window.innerHeight - height) / 2));
    }

    /** How many times a command is in the group, counting what is staged. */
    private _countOf(deviceId: string, commandId: string): number {
        const saved = this.steps.filter(
            (s) => s.device_id === deviceId && s.command_id === commandId,
        ).length;
        return saved + (this._staged.get(`${deviceId}/${commandId}`) ?? 0);
    }

    /** The group is full, counting what is staged. */
    private get _full(): boolean {
        return this.steps.length + this._picks.length >= GROUP_MAX_STEPS;
    }

    private _onKey = (e: KeyboardEvent): void => {
        if (e.key === "Escape") this._close();
    };

    connectedCallback(): void {
        super.connectedCallback();
        window.addEventListener("keydown", this._onKey);
        void this._load();
    }

    disconnectedCallback(): void {
        window.removeEventListener("keydown", this._onKey);
        super.disconnectedCallback();
    }

    private async _load(): Promise<void> {
        try {
            this._devices = (await this.api.groupCandidates(this.deviceId)).devices;
        } catch {
            this._devices = [];
        }
    }

    private _toggle(id: string): void {
        const next = new Set(this._open);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        this._open = next;
    }

    private _pick(deviceId: string, commandId: string): void {
        if (this.replace) {
            this.dispatchEvent(
                new CustomEvent("pick", { detail: { device_id: deviceId, command_id: commandId } }),
            );
            this._close();
            return;
        }
        if (this._full) return;
        const key = `${deviceId}/${commandId}`;
        const staged = new Map(this._staged);
        staged.set(key, (staged.get(key) ?? 0) + 1);
        this._staged = staged;
        this._picks = [...this._picks, { device_id: deviceId, command_id: commandId }];
    }

    /** The green button: add what is staged, then close. */
    private _commit(): void {
        this.dispatchEvent(new CustomEvent("add", { detail: { picks: this._picks } }));
        this._close();
    }

    /** A click outside closes only when nothing is staged. */
    private _outside(): void {
        if (!this._picks.length) this._close();
    }

    private _toggleShow(kind: keyof MediaShow): void {
        this._show = { ...this._show, [kind]: !this._show[kind] };
    }

    /** The IR and RF filter toggles right of the title. */
    private _renderShowGlyphs() {
        const glyphs: { kind: keyof MediaShow; label: string; medium: Medium }[] = [
            { kind: "ir", label: t("sniffer.filter.infrared"), medium: "ir" },
            { kind: "rf", label: t("sniffer.filter.radio"), medium: "rf" },
        ];
        return html`<div class="show-glyphs" role="group" aria-label=${t("sniffer.filter.label")}>
            ${glyphs.map(
                (g) => html`<button
                    class="show-glyph ${this._show[g.kind] ? "on" : ""}"
                    aria-pressed=${this._show[g.kind] ? "true" : "false"}
                    aria-label=${g.label}
                    title=${g.label}
                    @click=${() => this._toggleShow(g.kind)}
                >
                    ${renderProtoGlyph(g.medium, 18)}
                </button>`,
            )}
        </div>`;
    }

    /** A device's IR and RF glyphs, left of its name. */
    private _media(device: GroupCandidateDevice) {
        return html`<span class="media">${(device.media ?? []).map((m) => renderProtoGlyph(m, 16))}</span>`;
    }

    private _close(): void {
        this.dispatchEvent(new CustomEvent("closed"));
    }

    private _chevron(open: boolean) {
        return html`<svg class="chevron ${open ? "chevron-open" : ""}" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 9l6 6 6-6"></path>
        </svg>`;
    }

    private _renderDevice(row: ReturnType<typeof pickerView<GroupCandidateDevice>>[number]) {
        const { device, open, commands } = row;
        const inGroup = commandsInGroup(device.id, this.steps, this._staged.keys());
        const total = device.commands.length;
        const blocked = deviceBlocked(device);
        if (blocked) {
            return html`<div class="dev off">
                ${this._media(device)}
                <span class="dn">${device.name}</span>
                <span class="why">${t(BLOCKED_KEY[blocked])}</span>
            </div>`;
        }
        const searching = !!this._query.trim();
        return html`
            <button
                class="dev"
                aria-expanded=${open ? "true" : "false"}
                ?disabled=${searching}
                @click=${() => this._toggle(device.id)}
            >
                ${this._media(device)}
                <span class="dn">${device.name}</span>
                ${device.here ? html`<span class="here">${t("group.this_device")}</span>` : nothing}
                <span
                    class="counts"
                    title=${inGroup
                        ? t("group.count_title", { count: String(inGroup), total: String(total) })
                        : t(total === 1 ? "group.one_command" : "group.n_commands", { count: String(total) })}
                    >${inGroup
                        ? html`<span class="cnt">${inGroup}</span><span class="slash">/</span>`
                        : nothing}<span class="tot">${total}</span></span
                >
                ${this._chevron(open)}
            </button>
            ${open
                ? html`<div class="cmds">
                      ${commands.map((c) => {
                          const full = device.commands.find((x) => x.id === c.id)!;
                          const reason = full.reason && REASON_KEY[full.reason];
                          return reason
                              ? html`<div class="cmd off">
                                    <span class="add-slot"></span>
                                    <span class="n">${c.name}</span>
                                    <span class="why">${t(reason)}</span>
                                </div>`
                              : html`<div class="cmd">
                                    <span class="add-slot">
                                        <button
                                            class="action-btn assign-btn add-btn"
                                            ?disabled=${!this.replace && this._full}
                                            @click=${() => this._pick(device.id, c.id)}
                                        >
                                            ${t("group.add_chip")}<ir-count-dot
                                                color="green"
                                                .count=${this._countOf(device.id, c.id)}
                                            ></ir-count-dot>
                                        </button>
                                    </span>
                                    <span class="n">${c.name}</span>
                                </div>`;
                      })}
                  </div>`
                : nothing}
        `;
    }

    render() {
        // Search runs inside what the IR and RF filter leaves.
        const shown = (this._devices ?? []).filter((d) => mediaShows(this._show, d.media));
        const view = this._devices ? pickerView(shown, this._query, this._open) : [];
        return html`
            <div class="overlay ${this._top !== null ? "anchored" : ""}" @click=${this._outside}>
                <div
                    class="dialog picker"
                    style=${this._top !== null
                        ? `margin-top:${this._top}px;max-height:calc(100vh - ${this._top}px - 16px)`
                        : ""}
                    @click=${(e: Event) => e.stopPropagation()}
                >
                    <div class="title-row">
                        <h3 class="heading">
                            ${t(this.replace ? "group.pick_again_title" : "group.add_steps_title", {
                                name: this.groupName,
                            })}
                        </h3>
                        ${this._renderShowGlyphs()}
                        <button class="x" title=${t("common.close")} aria-label=${t("common.close")} @click=${this._close}>
                            ×
                        </button>
                    </div>
                    <input
                        class="search"
                        type="search"
                        placeholder=${t("group.search")}
                        .value=${this._query}
                        @input=${(e: Event) => (this._query = (e.target as HTMLInputElement).value)}
                    />
                    <div class="list">
                        ${this._devices === null
                            ? html`<div class="muted">${t("group.loading")}</div>`
                            : view.length
                              ? view.map((row) => this._renderDevice(row))
                              : html`<div class="muted">${t("group.no_match")}</div>`}
                    </div>
                    <div class="foot">
                        <span class="grow"></span>
                        ${!this.replace && this._picks.length
                            ? html`<button class="action-btn create-btn" @click=${this._commit}>
                                  ${this._picks.length === 1
                                      ? t("group.add_one_signal")
                                      : t("group.add_n_signals", { count: String(this._picks.length) })}
                              </button>`
                            : html`<button class="done" @click=${this._close}>
                                  ${t(this.replace ? "common.cancel" : "common.close")}
                              </button>`}
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        actionChipStyles,
        protoGlyphStyles,
        filterGlyphStyles,
        css`
            /* Once the top edge is set, the dialog hangs from it. */
            .overlay.anchored {
                align-items: flex-start;
            }
            /* Border-box, so the max-height holds the padding too and the
               bottom edge stays 16px above the window's. */
            .dialog.picker {
                box-sizing: border-box;
                /* 520, over the shared dialog's 400 cap: a device row
                   holds its glyphs, name, chip and counts on one line. */
                width: min(520px, calc(100vw - 24px));
                max-width: none;
                max-height: calc(100vh - 80px);
                display: flex;
                flex-direction: column;
            }
            /* The title, and the IR and RF filter hard right on its line. */
            .title-row {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 0 0 12px;
            }
            .heading {
                flex: 1 1 auto;
                min-width: 0;
                margin: 0;
            }
            .x {
                flex: none;
                background: none;
                border: none;
                color: var(--secondary-text-color);
                font-size: 1.2rem;
                width: 32px;
                height: 32px;
                border-radius: 4px;
                cursor: pointer;
            }
            .x:hover {
                background: var(--secondary-background-color);
                color: var(--primary-text-color);
            }
            .show-glyphs {
                flex: none;
                display: inline-flex;
                align-items: center;
                gap: 2px;
            }
            /* A device's glyphs: room for two, so every name starts at
               the same x whether it has one, two or none. */
            .media {
                flex: none;
                width: 36px;
                display: inline-flex;
                gap: 2px;
            }
            .search {
                width: 100%;
                box-sizing: border-box;
                padding: 8px 10px;
                border-radius: 6px;
                border: 1px solid var(--divider-color);
                background: var(--primary-background-color);
                color: var(--primary-text-color);
                font: inherit;
                margin-bottom: 8px;
            }
            .list {
                overflow: auto;
                flex: 1 1 auto;
                min-height: 80px;
            }
            .dev {
                box-sizing: border-box;
                display: flex;
                align-items: center;
                gap: 8px;
                width: 100%;
                padding: 9px 6px;
                border: none;
                border-top: 1px solid var(--divider-color);
                background: none;
                color: var(--primary-text-color);
                font: inherit;
                text-align: left;
                cursor: pointer;
                border-radius: 0;
            }
            .dev:hover:not(:disabled) {
                background: var(--secondary-background-color);
            }
            .dev:disabled {
                cursor: default;
            }
            .dev .dn {
                flex: 1 1 auto;
                min-width: 0;
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .dev.off {
                opacity: 0.5;
                cursor: default;
            }
            /* A greyed device's reason can be a sentence: it wraps on
               the right rather than pushing the name out. */
            .dev.off .why {
                flex: 0 0 auto;
                max-width: 55%;
                white-space: normal;
                text-align: right;
            }
            .here {
                font-size: 0.7rem;
                color: var(--hair-group-hue, ${unsafeCSS(GROUP_HUE)});
                border: 1px solid color-mix(in srgb, var(--hair-group-hue, ${unsafeCSS(GROUP_HUE)}) 50%, transparent);
                border-radius: 9px;
                padding: 1px 7px;
                white-space: nowrap;
            }
            /* "3 / 12" before the chevron: green in this group, grey the
               device's total, right-aligned in a fixed column so the
               figures line up down the list. */
            .counts {
                flex: none;
                min-width: 4.5em;
                text-align: right;
                font-size: 0.75rem;
                font-variant-numeric: tabular-nums;
                white-space: nowrap;
            }
            .cnt {
                color: #66bb6a;
            }
            .slash {
                color: var(--secondary-text-color);
                margin: 0 3px;
            }
            .tot,
            .why {
                font-size: 0.75rem;
                color: var(--secondary-text-color);
                white-space: nowrap;
            }
            .chevron {
                width: 20px;
                height: 20px;
                flex: none;
                fill: none;
                stroke: var(--secondary-text-color);
                stroke-width: 2;
                stroke-linecap: round;
                stroke-linejoin: round;
                transition: transform 150ms ease;
            }
            .chevron-open {
                transform: rotate(180deg);
            }
            .cmds {
                padding: 0 0 6px 18px;
            }
            .cmd {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 6px 6px;
                border-radius: 6px;
                color: var(--primary-text-color);
            }
            .cmd .n {
                flex: 1 1 auto;
                min-width: 0;
                overflow-wrap: anywhere;
            }
            /* The ADD column: the chip's width, held on a greyed row too,
               so every name starts at the same x. */
            .add-slot {
                flex: none;
                min-width: 52px;
                display: flex;
            }
            /* The Assign chip's green, filled a little so it reads as the
               thing to press on a long list. */
            .add-btn {
                padding: 3px 8px;
                font-size: 0.7rem;
                background: rgba(46, 125, 50, 0.12);
            }
            .add-btn:hover {
                background: rgba(46, 125, 50, 0.22);
            }
            .cmd.off {
                opacity: 0.5;
            }
            .muted {
                color: var(--secondary-text-color);
                padding: 12px 6px;
            }
            .foot {
                display: flex;
                align-items: center;
                gap: 10px;
                padding-top: 12px;
            }
            .grow {
                flex: 1;
            }
            /* The call to action: the panel's filled green, as on the
               Create and Accept buttons. */
            .create-btn {
                background: #2e7d32;
                color: #fff;
                border-color: #2e7d32;
                padding: 7px 14px;
            }
            .create-btn:hover {
                opacity: 0.9;
                background: #2e7d32;
            }
            /* Nothing staged: a plain Close. */
            .done {
                background: none;
                border: none;
                color: var(--primary-color);
                font: inherit;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                padding: 8px 10px;
                cursor: pointer;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-group-picker": IrGroupPicker;
    }
}
