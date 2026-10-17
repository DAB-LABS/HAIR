/**
 * One BroadSniff Listen chip (BroadSniff Listen, 2026-10-17; its own
 * element since round 2, so the Sniffer and the Devices page share it).
 *
 * A Broadlink hears IR only while BroadSniff (DAB-LABS/broadsniff) has a
 * capture window open on it. The chip is gold while the remote is not
 * listening and green while it is; one click opens a window, another
 * closes it, through ``hair/broadsniff/listen``.
 *
 * The chip follows BroadSniff's own switch, read live from ``hass``, so
 * a window opened from BroadSniff's device page, by a HAIR capture
 * session or by the same chip in the other place shows green here too,
 * and the chip goes back to gold by itself when the window ends.
 *
 * THE FILL drains across the chip over the window. It is drawn from
 * BroadSniff's own deadline (the switch's ``window_ends_at``), never
 * from a timer started on tap, and is re-read whenever the deadline
 * changes: in BroadSniff's ``sliding`` mode each code moves the
 * deadline, and the fill snaps back to full. That snap is the user's
 * proof the Broadlink heard the press.
 *
 * THE BLOOM (the shared ir-bloom-styles animation, in the chip's green)
 * fires when the chip turns on, when the deadline restarts, and when
 * BroadSniff's code count goes up. The last covers the modes whose
 * deadline never moves: in ``multiple`` the chip blooms on every code
 * while the fill keeps draining to its fixed end, and in ``single`` it
 * blooms on the one code just as the window closes and the chip goes
 * back to gold (owner, 2026-10-17). Repeat frames can bloom it several
 * times a second; BloomTracker restarts the glow cleanly each time.
 *
 * TWO FORMS, one element (round 2, owner: "one component, two places;
 * do not fork the chip"):
 * - the Sniffer's Listen row shows the full pill: the remote's name,
 *   then the exit-to-entity glyph, which opens the remote's BroadSniff
 *   device page, where the window length and mode live;
 * - ``compact`` is the Devices page's hardware-card badge, made to
 *   look like the TX-NATIVE and RX-NATIVE badges beside it: the
 *   ``RX-CAPTURE`` label alone in badge geometry, with no dot (owner
 *   addendum, 2026-10-17: the dot belongs to the header-style chips)
 *   and no glyph (the card around it is already a link). The tone,
 *   the fill and the bloom are the same.
 * Every click and keydown stops at the chip. The hardware card around
 * the compact form navigates on click, and its keydown handler cancels
 * Enter and Space, which would otherwise swallow the chip button's own
 * keyboard activation.
 */
import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import { keyed } from "lit/directives/keyed.js";
import type { HairApi } from "./api.js";
import { BloomTracker, bloomStyles } from "./ir-bloom-styles.js";
import { headerChipStyles } from "./ir-header-chip-styles.js";
import { exitToEntityButtonStyles, renderExitToEntityBtn } from "./ir-icons.js";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import {
    listenBlooms,
    listenLive,
    planFill,
    windowMs,
    type FillPlan,
    type ListenLive,
} from "./ir-listen-state.js";
import type { BroadSniffReceiverRow } from "./types.js";

/** Not listening: HAIR's gold (ORIGIN_COLORS.remote). */
export const LISTEN_GOLD = "#f5a623";
/** Listening. */
export const LISTEN_GREEN = "#43a047";

/** The compact form's label: a hardware badge, like RX-NATIVE, so it
 *  is not translated. */
export const RX_CAPTURE_LABEL = "RX-CAPTURE";

@customElement("ir-listen-chip")
export class IrListenChip extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public row!: BroadSniffReceiverRow;
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

    private _live(): ListenLive {
        return listenLive(this.hass?.states, this.row);
    }

    protected willUpdate(changed: PropertyValues): void {
        if (!this.row || (!changed.has("hass") && !changed.has("row"))) return;
        // A different remote in the same element starts from scratch.
        const previous = changed.get("row") as BroadSniffReceiverRow | undefined;
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
            this._fill = planFill(now.endsAt, windowMs(this.hass?.states, this.row), Date.now());
        }
        if (listenBlooms(before, now)) this._bloomChip();
        // A window that opened after all (from BroadSniff's own page,
        // or a capture session) answers an earlier failed click.
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
            await this.api.broadsniffListen(this.row.receiver_entity_id, !on);
        } catch {
            this._failed = true;
        } finally {
            this._busy = false;
        }
    }

    /** The chip lives inside things that act on click and keys (the
     *  Devices page's hardware card); nothing it handles goes further. */
    private _stop = (e: Event) => e.stopPropagation();

    render() {
        if (!this.row) return nothing;
        const row = this.row;
        const live = this._live();
        const fill = live.on ? this._fill : undefined;
        const word = this._failed
            ? t("listen.failed", { name: row.name })
            : live.on
              ? t("listen.on_title", { name: row.name })
              : t("listen.off_title", { name: row.name });
        return html`
            <span
                class="chip listen ${live.on ? "on" : "idle"} ${this._failed ? "failed" : ""} ${this._bloomed ? "bloom" : ""}"
                style="--tone:${live.on ? LISTEN_GREEN : LISTEN_GOLD}"
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
                    role="switch"
                    aria-checked=${live.on ? "true" : "false"}
                    aria-label=${word}
                    title=${word}
                    ?disabled=${this._busy}
                    @click=${() => void this._toggle(live.on)}
                >
                    ${this.compact ? nothing : html`<span class="dot"></span>`}
                    <span class="chip-name">${this.compact ? RX_CAPTURE_LABEL : row.name}</span>
                </button>
                ${this.compact
                    ? nothing
                    : renderExitToEntityBtn(
                          `/config/devices/device/${row.ha_device_id}`,
                          t("listen.open_title", { name: row.name }),
                      )}
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
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-listen-chip": IrListenChip;
    }
}
