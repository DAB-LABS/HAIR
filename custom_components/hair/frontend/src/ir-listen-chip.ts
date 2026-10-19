/**
 * One Listen chip for a capture device (BroadSniff Listen, 2026-10-17;
 * its own element since round 2, so the Sniffer and the Devices page
 * share it; any integration's capture device since round 3).
 *
 * A capture device is an infrared receiver that hears only while a
 * capture window is open, and says so with a boolean ``capturing``
 * attribute (docs/windowed-receivers.md): a Broadlink through BroadSniff
 * (DAB-LABS/broadsniff), or any other integration that follows the
 * contract. The chip is gold while the window is closed and green while
 * it is open; one click opens a window, another closes it, through
 * ``hair/receivers/listen``, which takes the receiver and resolves what
 * to toggle on the server.
 *
 * The chip follows the receiver's own ``capturing``, read live from
 * ``hass``, so a window opened anywhere else (the integration's device
 * page, a listen in the code editor, the same chip in the other place)
 * shows green here too, and the chip goes back to gold by itself when
 * the window ends.
 *
 * THE FILL drains across the chip over the window. It is drawn from the
 * receiver's ``window_ends_at``, never from a timer started on tap: it
 * starts full when a deadline first shows and drains to nothing at it,
 * and a new deadline (a ``sliding`` window moved by a code) plans it
 * afresh, so the fill snaps back to full. That snap is the user's proof
 * the receiver heard the press. A receiver that publishes no deadline
 * gets on and off with no fill.
 *
 * THE BLOOM (the shared ir-bloom-styles animation, in the chip's green)
 * fires when the window opens, when the deadline moves, and when a code
 * from this receiver reaches HAIR (ir-arrivals.ts). The last is HAIR's
 * own arrival, so the glow means HAIR heard it, in every capture mode.
 * Repeat frames can bloom it several times a second; BloomTracker
 * restarts the glow cleanly each time.
 *
 * WAITING while no entity is chosen to open the window. That is setup,
 * not health, so it is not drawn in ember. In the Sniffer the chip dims,
 * is disabled, and its title says to choose a switch first. On the
 * Devices card (compact) it is grey, like the card's icon, and a click
 * anywhere on it opens the switch menu (owner ruling, 2026-10-20).
 *
 * TWO FORMS, one element (round 2, owner: "one component, two places;
 * do not fork the chip"):
 * - the Sniffer's Listen row shows the full pill: the receiver's name,
 *   then the exit-to-entity glyph, which opens the receiver's device
 *   page in Home Assistant;
 * - ``compact`` is the Devices page's hardware-card badge, made to
 *   look like the TX-NATIVE and RX-NATIVE badges beside it: the
 *   ``RX-CAPTURE`` label in badge geometry, with no dot (owner
 *   addendum, 2026-10-17: the dot belongs to the header-style chips)
 *   and no glyph (the card around it is already a link). The tone,
 *   the fill and the bloom are the same. Since the owner's ruling of
 *   2026-10-20 it is a SPLIT chip, like the editor's Listen: the main
 *   part starts and stops a capture, and a caret behind a thin divider
 *   opens the switch menu (ir-capture-switch-menu.ts). Gold once a
 *   switch is resolved, grey until then, ember and disabled offline,
 *   caret included. Its tooltip names the switch ("Capture with ...")
 *   and where it came from. The separate switch pill is gone.
 * OFFLINE (ember, 2026-10-19): when HA cannot reach the receiver or
 * the entity that opens its window (ir-listen-state.ts listenOnline),
 * the chip is disabled, keeps its gold outline dimmed, wears the shared
 * ember ring for a dot, and its tooltip and accessible name say
 * offline. A capture device HAIR remembers but whose integration has
 * not loaded is offline the same way. Gold and green still mean ready
 * and listening: that is the capture window, not health. The compact
 * RX-CAPTURE badge has no dot; it goes ember instead, like the hardware
 * card's other badges (owner bench, 2026-10-19), is not clickable, and
 * says its health first.
 *
 * Every click and keydown stops at the chip. The hardware card around
 * the compact form navigates on click, and its keydown handler cancels
 * Enter and Space, which would otherwise swallow the chip button's own
 * keyboard activation.
 */
import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import { ifDefined } from "lit/directives/if-defined.js";
import { keyed } from "lit/directives/keyed.js";
import type { HairApi } from "./api.js";
import { BloomTracker, bloomStyles } from "./ir-bloom-styles.js";
import { EMBER_VAR, headerChipStyles } from "./ir-header-chip-styles.js";
import { exitToEntityButtonStyles, renderExitToEntityBtn } from "./ir-icons.js";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { onArrival } from "./ir-arrivals.js";
import { entityFullName } from "./entity-names.js";
import "./ir-capture-switch-menu.js";
import type { IrCaptureSwitchMenu } from "./ir-capture-switch-menu.js";
import {
    chipBlock,
    listenBlooms,
    listenLive,
    listenOnline,
    planFill,
    type FillPlan,
    type ListenLive,
} from "./ir-listen-state.js";
import type { CaptureReceiverRow, CaptureSwitchSource } from "./types.js";

/** Not listening: HAIR's gold (ORIGIN_COLORS.remote). */
export const LISTEN_GOLD = "#f5a623";
/** Listening. */
export const LISTEN_GREEN = "#43a047";

/** The compact form's label: a hardware badge, like RX-NATIVE, so it
 *  is not translated. */
export const RX_CAPTURE_LABEL = "RX-CAPTURE";

/** Where the switch came from, for the compact chip's tooltip. */
const SOURCE_KEYS: Record<CaptureSwitchSource, string> = {
    declared: "capswitch.source_declared",
    user: "capswitch.source_user",
    device: "capswitch.source_device",
};

/** Grey, the card icons' own, while no switch is resolved. */
const WAITING_TONE = "var(--secondary-text-color)";

@customElement("ir-listen-chip")
export class IrListenChip extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public row!: CaptureReceiverRow;
    /** The Devices page's badge form. */
    @property({ type: Boolean, reflect: true }) public compact = false;

    @state() private _bloomed = false;
    @state() private _busy = false;
    @state() private _failed = false;

    private _bloom = new BloomTracker();
    /** What the chip showed last, to tell an open, a restart or a new
     *  code from an ordinary state refresh. */
    private _seen: ListenLive | undefined = undefined;
    /** The fill for the open window, fixed when its deadline arrives so
     *  later renders never retime a running animation. */
    private _fill: FillPlan | undefined = undefined;
    /** The arrivals feed for the receiver this chip shows. */
    private _arrivals: { key: string; stop: () => void } | null = null;

    private _live(): ListenLive {
        return listenLive(this.hass?.states, this.row);
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

    /** One arrivals subscription per receiver shown, moved when the row
     *  or the api changes. */
    private _listenForArrivals(): void {
        const receiver = this.row?.receiver_entity_id;
        const key = receiver && this.api ? receiver : "";
        if (this._arrivals?.key === key) return;
        this._arrivals?.stop();
        this._arrivals = null;
        if (!key || !this.isConnected) return;
        this._arrivals = { key, stop: onArrival(this.api, key, () => this._bloomChip()) };
    }

    protected willUpdate(changed: PropertyValues): void {
        if (changed.has("row") || changed.has("api")) this._listenForArrivals();
        if (!this.row || (!changed.has("hass") && !changed.has("row"))) return;
        // A different receiver in the same element starts from scratch.
        const previous = changed.get("row") as CaptureReceiverRow | undefined;
        if (previous && previous.receiver_entity_id !== this.row.receiver_entity_id) {
            this._seen = undefined;
            this._fill = undefined;
        }
        const now = this._live();
        const before = this._seen;
        this._seen = now;
        if (now.endsAt === null) {
            this._fill = undefined;
        } else if (this._fill?.endsAt !== now.endsAt) {
            this._fill = planFill(now.endsAt, Date.now()) ?? undefined;
        }
        if (listenBlooms(before, now)) this._bloomChip();
        // A window that opened after all (from the integration's own
        // page, or a listen in the editor) answers an earlier failed
        // click.
        if (now.on && this._failed) this._failed = false;
    }

    private _bloomChip(): void {
        this._bloom.trigger(
            "chip",
            () => {
                this._bloomed = true;
            },
            () => {
                this._bloomed = false;
            },
        );
    }

    private async _toggle(on: boolean): Promise<void> {
        if (this._busy) return;
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

    /** The compact chip's main part: with nothing picked there is
     *  nothing to capture with, so it opens the switch menu under the
     *  whole chip instead. */
    private _onMain(on: boolean, waiting: boolean): void {
        if (waiting) {
            const menu = this.renderRoot.querySelector<IrCaptureSwitchMenu>("ir-capture-switch-menu");
            menu?.open(this.renderRoot.querySelector<HTMLElement>(".split") ?? undefined);
            return;
        }
        void this._toggle(on);
    }

    /** The full name of the switch, for the tooltip. */
    private _switchName(entityId: string): string {
        if (this.hass?.states?.[entityId]) return entityFullName(this.hass, entityId);
        return this.row.device_switches.find((s) => s.entity_id === entityId)?.name ?? entityId;
    }

    /** The chip lives inside things that act on click and keys (the
     *  Devices page's hardware card); nothing it handles goes further. */
    private _stop = (e: Event) => e.stopPropagation();

    render() {
        if (!this.row) return nothing;
        const row = this.row;
        // Offline (ember, 2026-10-19): the capture window cannot open,
        // so the chip shows no window state at all. It stays gold,
        // dimmed rather than grey so it still reads as a capture device
        // that is down, its dot becomes the ember ring, and it cannot be
        // pressed until HA reaches the receiver again. Without a chosen
        // switch it waits (dimmed, not ember: setup, not health).
        const online = listenOnline(this.hass?.states, row);
        const block = chipBlock(row, online);
        const live = online ? this._live() : { on: false, endsAt: null };
        const fill = live.on ? this._fill : undefined;
        // On the Devices card nothing picked is grey and opens the menu;
        // in the Sniffer it dims and waits, as before.
        const waiting = this.compact && block === "no_switch";
        const said =
            block === "offline"
                ? t("listen.offline_title", { name: row.name })
                : block === "no_switch"
                  ? this.compact
                      ? t("capswitch.choose_title", { name: row.name })
                      : t("listen.no_switch_title")
                  : this._failed
                    ? t("listen.failed", { name: row.name })
                    : live.on
                      ? t("listen.on_title", { name: row.name })
                      : t("listen.off_title", { name: row.name });
        // The compact form is a hardware badge, and every badge on the
        // card says its health first: "RX-CAPTURE, online: ...", then
        // the switch it captures with and where that came from.
        const current = row.switch_entity_id;
        const word = this.compact
            ? [
                  `${RX_CAPTURE_LABEL}, ${t(online ? "common.online" : "common.offline")}: ${said}`,
                  current ? t("listen.capture_with", { name: this._switchName(current) }) : "",
                  current && row.source ? t(SOURCE_KEYS[row.source]) : "",
              ]
                  .filter(Boolean)
                  .join("\n")
            : said;
        const tone = waiting ? WAITING_TONE : live.on ? LISTEN_GREEN : LISTEN_GOLD;
        const disabled = this._busy || (this.compact ? block === "offline" : block !== null);
        const chip = html`
            <span
                class="chip listen ${live.on ? "on" : "idle"} ${online ? "" : "offline"} ${block === "no_switch" && !this.compact ? "blocked" : ""} ${waiting ? "waiting" : ""} ${this._failed && online ? "failed" : ""} ${this._bloomed && online ? "bloom" : ""}"
                style="--tone:${tone}"
                @click=${this._stop}
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
                    class="listen-toggle"
                    role=${waiting ? "button" : "switch"}
                    aria-checked=${ifDefined(waiting ? undefined : live.on ? "true" : "false")}
                    aria-haspopup=${ifDefined(waiting ? "menu" : undefined)}
                    aria-label=${word.replace(/\n/g, ". ")}
                    title=${word}
                    ?disabled=${disabled}
                    @click=${() => this._onMain(live.on, waiting)}
                >
                    ${this.compact
                        ? nothing
                        : html`<span class="dot ${online ? "" : "offline"}"></span>`}
                    <span class="chip-name">${this.compact ? RX_CAPTURE_LABEL : row.name}</span>
                </button>
                ${this.compact || !row.ha_device_id
                    ? nothing
                    : renderExitToEntityBtn(
                          `/config/devices/device/${row.ha_device_id}`,
                          t("listen.open_title", { name: row.name }),
                      )}
            </span>
        `;
        if (!this.compact) return chip;
        // The split: the menu sits beside the chip, not inside it, so its
        // fixed menu is not trapped in the chip's isolated stacking
        // context; the two share colours through --split-fg/--split-bg.
        return html`
            <span
                class="split ${live.on ? "on" : ""} ${online ? "" : "offline"} ${waiting ? "waiting" : ""}"
                style="--tone:${tone}"
                @click=${this._stop}
                @keydown=${this._stop}
            >
                ${chip}
                <ir-capture-switch-menu
                    .hass=${this.hass}
                    .api=${this.api}
                    .row=${row}
                    ?disabled=${!online}
                ></ir-capture-switch-menu>
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
            }
            /* The chip is a frame around two controls (the toggle and
               the exit glyph), so it stops being a button itself and
               hands the toggle the padding the shared chip had. */
            .chip.listen {
                position: relative;
                overflow: hidden;
                padding: 0 4px 0 0;
                gap: 0;
                border-color: var(--tone);
                color: var(--primary-text-color);
                isolation: isolate;
            }
            .chip.listen .dot {
                background: var(--tone);
            }
            .chip.listen.on .dot {
                box-shadow: 0 0 5px color-mix(in srgb, var(--tone) 65%, transparent);
            }
            /* The shared .chip.on wash would sit under the fill and
               keep the chip looking full; the fill is the wash here. */
            .chip.listen.on {
                background: none;
            }
            .chip.listen.failed {
                border-style: dashed;
            }
            /* Offline (ember, 2026-10-19): the gold outline dimmed, no
               wash, quiet text, and the shared ember ring in place of
               the gold dot (healthDotStyles draws the ring; this only
               keeps the gold background off it). */
            .chip.listen.offline {
                border-color: color-mix(in srgb, var(--tone) 45%, transparent);
                background: none;
                color: var(--secondary-text-color);
            }
            .chip.listen .dot.offline {
                background: transparent;
                box-shadow: none;
            }
            .chip.listen.offline .listen-toggle:disabled {
                cursor: not-allowed;
            }
            /* The compact RX-CAPTURE badge offline (owner bench,
               2026-10-19): ember like the hardware card's other badges,
               on a 13 percent ember ground, and not clickable. */
            :host([compact]) .chip.listen.offline {
                background: color-mix(in srgb, ${EMBER_VAR} 13%, transparent);
            }
            :host([compact]) .chip.listen.offline .listen-toggle {
                color: ${EMBER_VAR};
            }
            .listen-toggle {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 3px 4px 3px 8px;
                border: none;
                background: none;
                font: inherit;
                color: inherit;
                cursor: pointer;
            }
            .listen-toggle:disabled {
                cursor: progress;
            }
            /* No switch chosen yet: dimmed, and the click does
               nothing (the Sniffer; the card's chip is grey and opens
               the switch menu instead). */
            .chip.listen.blocked {
                opacity: 0.45;
            }
            .chip.listen.blocked .listen-toggle {
                cursor: default;
            }
            .listen-toggle:focus-visible {
                outline: 2px solid var(--tone);
                outline-offset: -2px;
                border-radius: 14px;
            }
            /* Round 2: the glyph sits inside the pill at the chip's own
               text size, quiet until hovered. */
            .chip.listen .exit-to-entity-btn {
                position: relative;
                padding: 0 2px;
                color: var(--secondary-text-color);
            }
            .chip.listen .exit-to-entity-btn:hover {
                background: none;
                color: var(--primary-text-color);
            }
            .chip.listen .exit-to-entity-btn ha-svg-icon {
                --mdc-icon-size: 11px;
            }
            .fill {
                position: absolute;
                inset: 0;
                z-index: -1;
                transform-origin: left center;
                transform: scaleX(var(--fill-start, 1));
                background: color-mix(in srgb, var(--tone) 22%, transparent);
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
            /* The shared bloom, in the chip's green whatever the chip's
               state: in single mode the code arrives just as the window
               closes, and the glow is the proof it was heard. */
            .chip.listen.bloom {
                --bloom-rgb: 67, 160, 71;
                --bloom-peak: #43a047;
                --bloom-edge: #66bb6a;
            }

            /* COMPACT: the hardware card's badge row, in the other
               badges' own form (ir-device-list .badge: 4px radius,
               2px 4px padding, 0.72rem, weight 500, line-height 1),
               plain text in the tone on a 15 percent ground of the tone
               when idle; when listening the fill is the ground. */
            :host([compact]) .chip.listen {
                border: none;
                border-radius: 4px;
                padding: 0;
                font-size: 0.72rem;
                font-weight: 500;
                line-height: 1;
                white-space: nowrap;
                background: color-mix(in srgb, var(--tone) 15%, transparent);
            }
            :host([compact]) .chip.listen.on {
                background: color-mix(in srgb, var(--tone) 10%, transparent);
            }
            :host([compact]) .fill {
                background: color-mix(in srgb, var(--tone) 28%, transparent);
            }
            :host([compact]) .listen-toggle {
                gap: 0;
                padding: 2px 4px;
                color: var(--tone);
                font-weight: inherit;
                line-height: inherit;
            }
            :host([compact]) .listen-toggle:focus-visible {
                border-radius: 4px;
            }
            :host([compact]) .chip-name {
                max-width: none;
            }
            /* THE SPLIT (owner ruling, 2026-10-20): the chip's main part,
               then the caret, one chip on one row. The caret reads the
               chip's colours from --split-fg and --split-bg. */
            .split {
                display: inline-flex;
                align-items: stretch;
                white-space: nowrap;
                border-radius: 4px;
                font-size: 0.72rem;
                font-weight: 500;
                line-height: 1;
                --split-fg: var(--tone);
                --split-bg: color-mix(in srgb, var(--tone) 15%, transparent);
            }
            .split.on {
                --split-bg: color-mix(in srgb, var(--tone) 10%, transparent);
            }
            .split.offline {
                --split-fg: ${EMBER_VAR};
                --split-bg: color-mix(in srgb, ${EMBER_VAR} 13%, transparent);
            }
            :host([compact]) .split .chip.listen {
                border-radius: 4px 0 0 4px;
            }
            /* Nothing picked: grey, and the main part opens the menu. */
            :host([compact]) .chip.listen.waiting .listen-toggle {
                cursor: pointer;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-listen-chip": IrListenChip;
    }
}
