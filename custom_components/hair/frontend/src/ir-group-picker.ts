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
 * stay in the list, greyed, with the reason.
 *
 * Search (`pickerView`) opens every device with a match and shows only
 * the matching commands; clearing it puts the list back as it was left.
 *
 * Emits `pick` {device_id, command_id} for each tap, and `closed`. In
 * `replace` mode (a missing step's "Pick again") one tap picks and closes.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { GroupCandidateDevice } from "./types.js";
import { countInGroup, pickerView } from "./group-steps.js";
import { radioBandOf } from "./sniffer-filter.js";
import "./ir-protocol-chip.js";

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
    /** Steps added while the picker has been open. */
    @state() private _added = 0;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
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
        this._added += 1;
        this.dispatchEvent(
            new CustomEvent("pick", { detail: { device_id: deviceId, command_id: commandId } }),
        );
        if (this.replace) this._close();
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
        const inGroup = countInGroup(device.id, this.steps);
        if (!device.blaster) {
            return html`<div class="dev off">
                <span class="dn">${device.name}</span>
                <span class="why">${t("group.reason_no_blaster")}</span>
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
                <span class="dn">${device.name}</span>
                ${device.here ? html`<span class="here">${t("group.this_device")}</span>` : nothing}
                ${inGroup
                    ? html`<span class="cnt">${t("group.in_this_group", { count: String(inGroup) })}</span>`
                    : nothing}
                <span class="tot">${t(device.commands.length === 1 ? "group.one_command" : "group.n_commands", {
                    count: String(device.commands.length),
                })}</span>
                ${this._chevron(open)}
            </button>
            ${open
                ? html`<div class="cmds">
                      ${commands.map((c) => {
                          const full = device.commands.find((x) => x.id === c.id)!;
                          const reason = full.reason && REASON_KEY[full.reason];
                          const added = this.steps.some(
                              (s) => s.device_id === device.id && s.command_id === c.id,
                          );
                          return reason
                              ? html`<div class="cmd off">
                                    <span class="plus"></span>
                                    <span class="n">${c.name}</span>
                                    <span class="why">${t(reason)}</span>
                                </div>`
                              : html`<button class="cmd ${added ? "added" : ""}" @click=${() => this._pick(device.id, c.id)}>
                                    <span class="plus">${added ? "✓" : "+"}</span>
                                    <span class="n">${c.name}</span>
                                    ${full.medium === "rf"
                                        ? html`<span class="band">${bandText(full)}</span>`
                                        : full.protocol
                                          ? html`<ir-protocol-chip .protocol=${full.protocol}></ir-protocol-chip>`
                                          : nothing}
                                </button>`;
                      })}
                  </div>`
                : nothing}
        `;
    }

    render() {
        const view = this._devices ? pickerView(this._devices, this._query, this._open) : [];
        return html`
            <div class="overlay" @click=${this._close}>
                <div class="dialog picker" @click=${(e: Event) => e.stopPropagation()}>
                    <h3 class="heading">
                        ${t(this.replace ? "group.pick_again_title" : "group.add_steps_title", {
                            name: this.groupName,
                        })}
                    </h3>
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
                        ${this.replace
                            ? nothing
                            : html`<span class="count">${t("group.added", { count: String(this._added) })}</span>`}
                        <span class="grow"></span>
                        <button class="done" @click=${this._close}>
                            ${t(this.replace ? "common.cancel" : "group.done")}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            .dialog.picker {
                width: min(520px, calc(100vw - 24px));
                max-height: calc(100vh - 80px);
                display: flex;
                flex-direction: column;
            }
            .heading {
                margin: 0 0 12px;
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
            .here {
                font-size: 0.7rem;
                color: #c9a3e6;
                border: 1px solid rgba(201, 163, 230, 0.5);
                border-radius: 9px;
                padding: 1px 7px;
                white-space: nowrap;
            }
            .cnt {
                font-size: 0.75rem;
                color: #66bb6a;
                white-space: nowrap;
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
                width: 100%;
                padding: 7px 6px;
                border: none;
                border-radius: 6px;
                background: none;
                color: var(--primary-text-color);
                font: inherit;
                text-align: left;
                cursor: pointer;
            }
            .cmd:hover:not(.off) {
                background: var(--secondary-background-color);
            }
            .cmd .n {
                flex: 1 1 auto;
                min-width: 0;
            }
            .cmd .plus {
                width: 20px;
                text-align: center;
                color: var(--primary-color);
                font-size: 1.1rem;
            }
            .cmd.added .plus {
                color: #66bb6a;
            }
            .cmd.off {
                opacity: 0.5;
                cursor: default;
            }
            .band {
                font-size: 0.75rem;
                color: var(--secondary-text-color);
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
            .count {
                color: var(--secondary-text-color);
                font-size: 0.85rem;
            }
            .grow {
                flex: 1;
            }
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
            @media (max-width: 450px) {
                .tot {
                    display: none;
                }
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-group-picker": IrGroupPicker;
    }
}
