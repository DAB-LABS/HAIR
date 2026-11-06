/**
 * One Listen pill on the Sniffer (BroadSniff Listen, 2026-10-17; any
 * capture device since windowed receivers, round 3; the pill since RF
 * hear round 1, design sniffer-listen-pills.html, owner 2026-11-06).
 *
 * Every receiver is heard all the time. A pill is where a capture
 * window is pressed open: one per capture device (infrared or radio, a
 * receiver that hears only while its window is open, docs/windowed-
 * receivers.md), and one per always-on radio receiver, whose window is
 * HAIR's own (a software window: known codes fire all the time, a new
 * radio remote is minted only while it is open). Always-on infrared
 * receivers have no pill: they mint freely.
 *
 * THE PILL, at the shipped header-chip metrics: a solid badge (IR-RX or
 * RF-RX, white on the tone), the receiver's device name, a word when
 * there is one, the pickers, then the exit glyph at the right end
 * (2026-11-06: it moved from after the name), which opens the device
 * page. The whole pill is the press except the pickers and the glyph.
 *
 * ITS LOOKS (ir-listen-state.ts pillLook): gold while a capture device
 * waits; steady green with "hearing" for an always-on radio receiver;
 * green with the drain while a window is open; green with no fill and
 * "hold the button" while a sweep looks for the carrier; ember, pickers
 * greyed and no press while the receiver is down; dimmed while a
 * capture device has no switch to open its window with yet.
 *
 * THE WINDOW is read live: a capture device's from its receiver's own
 * state in ``hass`` (``capturing``, ``window_ends_at``, and for radio
 * ``capture_phase`` and ``frequency_hz``), so a window opened anywhere
 * shows here; a software window's from the radio subscription's latest
 * item, never from ``hass`` (the window is HAIR's, not the receiver's).
 *
 * THE FILL drains across the pill over the window, drawn from the
 * window's deadline, never a timer started on tap; a moved deadline
 * (a sliding window extended by a code) plans it afresh, so it snaps
 * back to full. THE BLOOM fires when the window opens, when its end
 * moves, and when a code from this receiver reaches HAIR.
 *
 * THE PICKERS (ir-pill-picker.ts): frequency (a radio capture device
 * that declares a frequency select and two or more options in its
 * ``frequency_options`` map), length and type. A software window's are
 * kept on the receiver's record (``hair/receivers/window_prefs``); a
 * capture device's set its own declared entities, and a setting it
 * does not declare shows no picker. All of them are inactive while the
 * window is open: a change applies to the next one.
 *
 * A capture device that declares no ``capture_switch`` keeps its switch
 * menu (ir-capture-switch-menu.ts), as a small settings caret on this
 * pill only.
 *
 * Every click and keydown that is the pill's stops at the pill.
 */
import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import { keyed } from "lit/directives/keyed.js";
import type { HairApi } from "./api.js";
import { BloomTracker, bloomStyles } from "./ir-bloom-styles.js";
import { EMBER_VAR, headerChipStyles } from "./ir-header-chip-styles.js";
import { exitToEntityButtonStyles, renderExitToEntityBtn } from "./ir-icons.js";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { onArrival } from "./ir-arrivals.js";
import "./ir-capture-switch-menu.js";
import "./ir-pill-picker.js";
import type { PickerChoice } from "./ir-pill-picker.js";
import {
    bandNumber,
    currentFrequency,
    currentLength,
    currentMode,
    frequencyChoices,
    lengthChoices,
    listenBlooms,
    modeChoices,
    pickersActive,
    pillBadge,
    pillLive,
    pillLook,
    pillOnline,
    planFill,
    type FillPlan,
    type PillLive,
    type PillLook,
} from "./ir-listen-state.js";
import type { CaptureReceiverRow, RfReceiverItem, WindowMode } from "./types.js";

/** Waiting: HAIR's gold (ORIGIN_COLORS.remote). */
export const LISTEN_GOLD = "#f5a623";
/** Hearing, or a window open. */
export const LISTEN_GREEN = "#43a047";
/** No switch yet: the card icons' own grey. */
const WAITING_TONE = "var(--secondary-text-color)";

/** A length as the picker writes it: "30 s", "2 min". */
export function lengthLabel(seconds: number): string {
    return seconds % 60 === 0 && seconds >= 60
        ? t("listen.len_min", { count: seconds / 60 })
        : t("listen.len_s", { count: seconds });
}

@customElement("ir-listen-chip")
export class IrListenChip extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public row!: CaptureReceiverRow;
    /** A software window's latest item from the radio subscription. */
    @property({ attribute: false }) public item: RfReceiverItem | null = null;

    @state() private _bloomed = false;
    @state() private _busy = false;
    @state() private _failed = false;
    /** A software window's choice, as just picked, until the row is
     *  read again. */
    @state() private _prefs: { seconds: number; mode: WindowMode } | null = null;

    private _bloom = new BloomTracker();
    private _seen: PillLive | undefined = undefined;
    private _fill: FillPlan | undefined = undefined;
    private _arrivals: { key: string; stop: () => void } | null = null;

    /** The row, with a software window's just-picked choice on it. */
    private _row(): CaptureReceiverRow {
        if (!this._prefs || !this.row.software_window) return this.row;
        return { ...this.row, window_seconds: this._prefs.seconds, window_mode: this._prefs.mode };
    }

    private _live(): PillLive {
        return pillLive(this.hass?.states, this.row, this.item);
    }

    connectedCallback(): void {
        super.connectedCallback();
        this._listenForArrivals();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._arrivals?.stop();
        this._arrivals = null;
    }

    private _listenForArrivals(): void {
        const receiver = this.row?.receiver_entity_id;
        const key = receiver && this.api ? receiver : "";
        if (this._arrivals?.key === key) return;
        this._arrivals?.stop();
        this._arrivals = null;
        if (!key || !this.isConnected) return;
        this._arrivals = { key, stop: onArrival(this.api, key, () => this._bloomPill()) };
    }

    protected willUpdate(changed: PropertyValues): void {
        if (changed.has("row") || changed.has("api")) this._listenForArrivals();
        if (!this.row) return;
        if (changed.has("row")) {
            const previous = changed.get("row") as CaptureReceiverRow | undefined;
            if (previous && previous.receiver_entity_id !== this.row.receiver_entity_id) {
                this._seen = undefined;
                this._fill = undefined;
                this._prefs = null;
            } else if (
                this._prefs &&
                this.row.window_seconds === this._prefs.seconds &&
                this.row.window_mode === this._prefs.mode
            ) {
                this._prefs = null;
            }
        }
        if (!changed.has("hass") && !changed.has("row") && !changed.has("item")) return;
        const now = this._live();
        const before = this._seen;
        this._seen = now;
        // A sweep has no fill until the carrier locks.
        const ends = now.phase === "sweeping" ? null : now.endsAt;
        if (ends === null) {
            this._fill = undefined;
        } else if (this._fill?.endsAt !== ends) {
            this._fill = planFill(ends, Date.now()) ?? undefined;
        }
        if (listenBlooms(before, now)) this._bloomPill();
        if (now.on && this._failed) this._failed = false;
    }

    private _bloomPill(): void {
        this._bloom.trigger(
            "pill",
            () => {
                this._bloomed = true;
            },
            () => {
                this._bloomed = false;
            },
        );
    }

    private async _press(look: PillLook, on: boolean): Promise<void> {
        if (this._busy || look === "offline" || look === "waiting") return;
        this._busy = true;
        this._failed = false;
        try {
            await this.api.receiverListen(this.row.receiver_entity_id, !on);
        } catch {
            this._failed = true;
        } finally {
            this._busy = false;
        }
    }

    /** A software window's choice goes to the server; a capture
     *  device's to its own declared entity. */
    private async _save(kind: "frequency" | "length" | "mode", value: string): Promise<void> {
        const row = this._row();
        try {
            if (row.software_window) {
                const seconds = kind === "length" ? Number(value) : (row.window_seconds ?? 30);
                const mode = (kind === "mode" ? value : (row.window_mode ?? "sliding")) as WindowMode;
                this._prefs = { seconds, mode };
                const saved = await this.api.setWindowPrefs(row.receiver_entity_id, seconds, mode);
                this._prefs = { seconds: saved.window_seconds, mode: saved.window_mode };
                return;
            }
            if (kind === "length" && row.window_length) {
                await this.hass.callService("number", "set_value", {
                    entity_id: row.window_length,
                    value: Number(value),
                });
            } else if (kind === "mode" && row.capture_mode_select) {
                await this.hass.callService("select", "select_option", {
                    entity_id: row.capture_mode_select,
                    option: value,
                });
            } else if (kind === "frequency" && row.frequency_select) {
                await this.hass.callService("select", "select_option", {
                    entity_id: row.frequency_select,
                    option: value,
                });
            }
        } catch {
            this._prefs = null;
            this._failed = true;
        }
    }

    private _stop = (e: Event) => e.stopPropagation();

    private _renderPickers(row: CaptureReceiverRow, live: PillLive, look: PillLook) {
        const states = this.hass?.states;
        const active = pickersActive(look) && !this._busy;
        const locked = look === "open" || look === "sweep";
        const out = [];

        const freqs = frequencyChoices(row);
        const freq = currentFrequency(states, row, live);
        if (freqs.length > 0 && freq) {
            const label = freq.sweep
                ? t("listen.sweep")
                : freq.hz
                  ? bandNumber(freq.hz)
                  : t("listen.band_unknown");
            const choices: PickerChoice[] = freqs.map((o) => ({
                value: o.option,
                label: o.hz === null ? t("listen.sweep") : t("listen.band", { band: bandNumber(o.hz) }),
            }));
            const current = states?.[row.frequency_select ?? ""]?.state ?? null;
            out.push(html`<ir-pill-picker
                class="pick-frequency"
                .label=${label}
                .name=${t("listen.pick_frequency", { value: label })}
                .choices=${choices}
                .value=${current}
                ?inactive=${!active}
                ?locked=${locked}
                @pick=${(e: CustomEvent) => void this._save("frequency", e.detail.value)}
            ></ir-pill-picker>`);
        }

        const lengths = lengthChoices(states, row);
        const length = currentLength(states, row);
        if (lengths.length > 0) {
            const label = length !== null ? lengthLabel(length) : "";
            out.push(html`<ir-pill-picker
                class="pick-length"
                .label=${label}
                .name=${t("listen.pick_length", { value: label })}
                .choices=${lengths.map((s) => ({ value: String(s), label: lengthLabel(s) }))}
                .value=${length !== null ? String(length) : null}
                ?inactive=${!active}
                ?locked=${locked}
                @pick=${(e: CustomEvent) => void this._save("length", e.detail.value)}
            ></ir-pill-picker>`);
        }

        const modes = modeChoices(states, row);
        const mode = currentMode(states, row);
        if (modes.length > 0) {
            const len = lengthLabel(length ?? 30);
            const label = mode ? t(`listen.mode.${mode}`) : "";
            out.push(html`<ir-pill-picker
                class="pick-mode"
                .label=${label}
                .name=${t("listen.pick_mode", { value: label })}
                .choices=${modes.map((m) => ({
                    value: m,
                    label: t(`listen.mode.${m}`),
                    note: t(`listen.mode_note.${m}`, { length: len }),
                }))}
                .value=${mode}
                ?inactive=${!active}
                ?locked=${locked}
                @pick=${(e: CustomEvent) => void this._save("mode", e.detail.value)}
            ></ir-pill-picker>`);
        }

        // A capture device that declares no switch keeps its menu, as a
        // small settings caret on this pill only.
        if (!row.software_window && row.source !== "declared") {
            out.push(html`<ir-capture-switch-menu
                .hass=${this.hass}
                .api=${this.api}
                .row=${row}
                ?disabled=${look === "offline"}
            ></ir-capture-switch-menu>`);
        }
        return out;
    }

    private _title(row: CaptureReceiverRow, look: PillLook, on: boolean): string {
        const name = row.name;
        if (look === "offline") return t("listen.offline_title", { name });
        if (look === "waiting") return t("listen.no_switch_title");
        if (this._failed) return t("listen.failed", { name });
        if (look === "sweep") return t("listen.sweep_title", { name });
        if (on) return t("listen.on_title", { name });
        if (look === "hearing") return t("listen.hearing_title", { name });
        return t("listen.off_title", { name });
    }

    render() {
        if (!this.row) return nothing;
        const row = this._row();
        const online = pillOnline(this.hass?.states, row);
        const live = online ? this._live() : { on: false, endsAt: null, phase: null, frequencyHz: null };
        const look = pillLook(row, online, live);
        const fill = look === "open" ? this._fill : undefined;
        const tone =
            look === "offline"
                ? EMBER_VAR.cssText
                : look === "waiting"
                  ? WAITING_TONE
                  : look === "idle"
                    ? LISTEN_GOLD
                    : LISTEN_GREEN;
        const title = this._title(row, look, live.on);
        const word =
            look === "hearing" ? t("listen.hearing") : look === "sweep" ? t("listen.hold_button") : "";
        const pressable = look !== "offline" && look !== "waiting" && !this._busy;
        return html`
            <span
                class="pill look-${look} ${this._failed && online ? "failed" : ""} ${this._bloomed && online ? "bloom" : ""}"
                style="--tone:${tone}"
                @click=${(e: Event) => {
                    e.stopPropagation();
                    if (pressable) void this._press(look, live.on);
                }}
                @keydown=${this._stop}
            >
                ${fill
                    ? keyed(
                          fill.endsAt,
                          html`<span
                              class="fill"
                              style="--fill-start:${fill.start};animation-duration:${fill.durationMs}ms"
                          ></span>`,
                      )
                    : nothing}
                <button
                    class="press"
                    role="switch"
                    aria-checked=${live.on ? "true" : "false"}
                    aria-label=${title}
                    title=${title}
                    ?disabled=${!pressable}
                >
                    <span class="rx-badge">${pillBadge(row)}</span>
                    <span class="pill-name">${row.name}</span>
                    ${word ? html`<span class="word">${word}</span>` : nothing}
                </button>
                <span class="pickers" @click=${this._stop}>${this._renderPickers(row, live, look)}</span>
                ${row.ha_device_id
                    ? html`<span class="exit" @click=${this._stop}
                          >${renderExitToEntityBtn(
                              `/config/devices/device/${row.ha_device_id}`,
                              t("listen.open_title", { name: row.name }),
                          )}</span
                      >`
                    : nothing}
            </span>
        `;
    }

    static styles = [
        headerChipStyles,
        bloomStyles,
        exitToEntityButtonStyles,
        css`
            :host {
                display: inline-flex;
                max-width: 100%;
            }
            /* The shipped header-chip metrics: 11.5px text, 14px radius,
               a 1px border in the tone. */
            .pill {
                position: relative;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                max-width: 100%;
                box-sizing: border-box;
                padding: 2px 6px 2px 3px;
                border: 1px solid var(--tone);
                border-radius: 14px;
                font-size: 11.5px;
                color: var(--primary-text-color);
                overflow: hidden;
                isolation: isolate;
                cursor: pointer;
            }
            .pill.look-idle {
                background: color-mix(in srgb, var(--tone) 10%, transparent);
            }
            .pill.look-hearing,
            .pill.look-sweep {
                background: color-mix(in srgb, var(--tone) 8%, transparent);
            }
            .pill.look-offline {
                background: color-mix(in srgb, var(--tone) 8%, transparent);
                color: var(--secondary-text-color);
                cursor: not-allowed;
            }
            .pill.look-waiting {
                opacity: 0.55;
                cursor: default;
            }
            .pill.failed {
                border-style: dashed;
            }
            .press {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                min-width: 0;
                padding: 0;
                border: none;
                background: none;
                font: inherit;
                color: inherit;
                cursor: inherit;
            }
            .press:focus-visible {
                outline: 2px solid var(--tone);
                outline-offset: 2px;
                border-radius: 10px;
            }
            .press:disabled {
                cursor: inherit;
            }
            /* The solid badge: white text on the tone. */
            .rx-badge {
                flex: none;
                padding: 2px 6px;
                border-radius: 10px;
                background: var(--tone);
                color: #fff;
                font-weight: 600;
                font-size: 10.5px;
                line-height: 1.2;
                letter-spacing: 0.02em;
            }
            .pill-name {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                min-width: 0;
            }
            .word {
                color: var(--tone);
                white-space: nowrap;
            }
            .pickers {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                cursor: default;
                --split-fg: var(--tone);
                --split-bg: transparent;
            }
            .exit {
                display: inline-flex;
            }
            .pill .exit-to-entity-btn {
                position: relative;
                padding: 0 2px;
                color: var(--secondary-text-color);
            }
            .pill .exit-to-entity-btn:hover {
                background: none;
                color: var(--primary-text-color);
            }
            .pill .exit-to-entity-btn ha-svg-icon {
                --mdc-icon-size: 11px;
            }
            .fill {
                position: absolute;
                inset: 0;
                z-index: -1;
                transform-origin: left center;
                transform: scaleX(var(--fill-start, 1));
                background: color-mix(in srgb, var(--tone) 24%, transparent);
                animation-name: listen-drain;
                animation-timing-function: linear;
                animation-fill-mode: forwards;
            }
            @keyframes listen-drain {
                from {
                    transform: scaleX(var(--fill-start, 1));
                }
                to {
                    transform: scaleX(0);
                }
            }
            @media (prefers-reduced-motion: reduce) {
                .fill {
                    animation: none;
                }
            }
            .pill.bloom {
                --bloom-rgb: 67, 160, 71;
                --bloom-peak: #43a047;
                --bloom-edge: #66bb6a;
            }
            /* Phone: the pill takes the full row; badge, name and glyph
               on the first line, the pickers on a second line inside. */
            @media (max-width: 600px) {
                :host {
                    display: flex;
                    width: 100%;
                }
                .pill {
                    display: grid;
                    grid-template-columns: minmax(0, 1fr) auto;
                    grid-template-areas:
                        "press exit"
                        "pickers pickers";
                    row-gap: 4px;
                    width: 100%;
                    border-radius: 10px;
                    padding: 4px 6px 5px 4px;
                }
                .press {
                    grid-area: press;
                }
                .exit {
                    grid-area: exit;
                    justify-self: end;
                }
                .pickers {
                    grid-area: pickers;
                    flex-wrap: wrap;
                }
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-listen-chip": IrListenChip;
    }
}
