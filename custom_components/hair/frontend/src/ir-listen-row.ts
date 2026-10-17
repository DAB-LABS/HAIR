/**
 * The Sniffer's Listen row (BroadSniff Listen, 2026-10-17).
 *
 * A Broadlink hears IR only while BroadSniff (DAB-LABS/broadsniff) has a
 * capture window open on it, and the user is in the Sniffer when they
 * want it to listen. This row gives each BroadSniff remote one chip:
 * gold while the remote is not listening, green while it is. One tap
 * opens a window, another closes it.
 *
 * The chip follows BroadSniff's own switch, read live from ``hass``, so
 * a window opened from BroadSniff's device page or by a HAIR capture
 * session shows green here too, and the chip goes back to gold by
 * itself when the window ends.
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
 * Settings (window length, mode) are BroadSniff's and stay there: the
 * exit-to-entity glyph after the name opens the remote's BroadSniff
 * device page in Home Assistant.
 *
 * The look is the device pages' header chip group, from the shared
 * ir-header-chip-styles module; the behaviour differs (one tap toggles,
 * every chip always shows), which is why this is its own component.
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

@customElement("ir-listen-row")
export class IrListenRow extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public rows: BroadSniffReceiverRow[] = [];
    /** Width of the label column, in px, as on the device headers. */
    @property({ type: Number }) public labelWidth = 64;

    @state() private _bloomed = new Set<string>();
    @state() private _busy = new Set<string>();
    @state() private _failed = new Set<string>();

    private _bloom = new BloomTracker();
    /** What each chip showed last, to tell an open, a restart or a new
     *  code from an ordinary state refresh. */
    private _seen = new Map<string, ListenLive>();
    /** The fill for each open window, fixed when its deadline arrives
     *  so later renders never retime a running animation. */
    private _fills = new Map<string, FillPlan>();

    private _live(row: BroadSniffReceiverRow): ListenLive {
        return listenLive(this.hass?.states, row);
    }

    protected willUpdate(changed: PropertyValues): void {
        if (!changed.has("hass") && !changed.has("rows")) return;
        for (const row of this.rows) {
            const id = row.receiver_entity_id;
            const now = this._live(row);
            const before = this._seen.get(id);
            this._seen.set(id, now);
            if (now.endsAt === null) {
                this._fills.delete(id);
            } else if (this._fills.get(id)?.endsAt !== now.endsAt) {
                this._fills.set(
                    id,
                    planFill(now.endsAt, windowMs(this.hass?.states, row), Date.now()),
                );
            }
            if (listenBlooms(before, now)) this._bloomChip(id);
            // A window that opened after all (from BroadSniff's own page,
            // or a capture session) answers an earlier failed tap.
            if (now.on && this._failed.has(id)) {
                const cleared = new Set(this._failed);
                cleared.delete(id);
                this._failed = cleared;
            }
        }
    }

    private _bloomChip(id: string): void {
        this._bloom.trigger(
            id,
            () => {
                this._bloomed = new Set([...this._bloomed, id]);
            },
            () => {
                if (!this._bloomed.has(id)) return;
                const next = new Set(this._bloomed);
                next.delete(id);
                this._bloomed = next;
            },
        );
    }

    private async _toggle(row: BroadSniffReceiverRow, on: boolean): Promise<void> {
        const id = row.receiver_entity_id;
        if (this._busy.has(id)) return;
        this._busy = new Set([...this._busy, id]);
        if (this._failed.has(id)) {
            const cleared = new Set(this._failed);
            cleared.delete(id);
            this._failed = cleared;
        }
        try {
            await this.api.broadsniffListen(id, !on);
        } catch {
            this._failed = new Set([...this._failed, id]);
        } finally {
            const next = new Set(this._busy);
            next.delete(id);
            this._busy = next;
        }
    }

    render() {
        if (this.rows.length === 0) return nothing;
        return html`
            <div class="hdr-row" role="group" aria-label=${t("listen.label")}>
                <span class="hdr-row-label" style="width:${this.labelWidth}px"
                    >${t("listen.label")}</span
                >
                <div class="hdr-row-pills">
                    ${this.rows.map((row) => this._renderChip(row))}
                </div>
            </div>
        `;
    }

    private _renderChip(row: BroadSniffReceiverRow) {
        const id = row.receiver_entity_id;
        const live = this._live(row);
        const fill = live.on ? this._fills.get(id) : undefined;
        const failed = this._failed.has(id);
        const word = failed
            ? t("listen.failed", { name: row.name })
            : live.on
              ? t("listen.on_title", { name: row.name })
              : t("listen.off_title", { name: row.name });
        return html`
            <span
                class="chip listen ${live.on ? "on" : "idle"} ${failed ? "failed" : ""} ${this._bloomed.has(id) ? "bloom" : ""}"
                style="--tone:${live.on ? LISTEN_GREEN : LISTEN_GOLD}"
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
                    ?disabled=${this._busy.has(id)}
                    @click=${() => void this._toggle(row, live.on)}
                >
                    <span class="dot"></span>
                    <span class="chip-name">${row.name}</span>
                </button>
                ${renderExitToEntityBtn(
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
                display: block;
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
            .chip.listen .exit-to-entity-btn {
                position: relative;
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
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-listen-row": IrListenRow;
    }
}
