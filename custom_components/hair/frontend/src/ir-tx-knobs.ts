/**
 * The TX-knob glyphs: whole-frame send count and NEC ditto count.
 *
 * One component, four homes (owner ruling, 2026-08-01). These glyphs
 * had been hand-copied into the device command rows and the Mirror
 * rows, and were simply absent from the Sniffer and Clipper signal
 * rows -- so a user could set a send count on a catalog signal, save
 * it, and see no trace of it anywhere on the row they had just edited.
 * Reported from the bench as "maybe that's an oversight we have
 * systemically", which it was.
 *
 * Both glyphs are conditional in the same way they always were:
 * - the repeat glyph appears only above 1, because "sends once" is the
 *   default and drawing it would put a badge on every row in the list
 * - the ditto glyph additionally requires a decoded identity, since
 *   dittos are an NEC-family frame construct and mean nothing on a row
 *   that only ever replays captured timings
 * - and it is suppressed entirely on a bypassed row. Raw replay sends
 *   the captured bytes verbatim, so the dittos never reach the wire and
 *   a glyph claiming otherwise would misdescribe the transmission. That
 *   rule already existed on the device command rows; folding it in here
 *   is what extends it to the three surfaces that lacked it.
 *
 * A row that carries a tuned SPACING says so in the same tooltip
 * (GH #151): the glyph itself stays one orange number, because a
 * second badge on a list row would cost more attention than the fact
 * is worth, but hovering it tells you the cadence the row was proved
 * at rather than just how many times it fires.
 *
 * The tooltip keys are properties rather than constants because the
 * hosts word the same fact differently and correctly: a command "sends
 * this command N times", a catalog signal "sends this signal N times".
 * Passing the key in keeps both sentences, and their ten translations,
 * exactly as they are.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property } from "./decorators.js";
import { t } from "./localize.js";

// mdi:repeat -- whole-frame send-count indicator (orange).
const ICON_REPEAT =
    "M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z";
// mdi:dots-horizontal -- NEC ditto-count indicator (blue), paired with
// the decoded-protocol blue diamond.
const ICON_DITTO =
    "M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z";

/**
 * The protocol whose repeat frame a ditto actually is.
 *
 * Measured against infrared-protocols rather than assumed, by counting
 * the timings each protocol emits as repeat_count goes 0, 1, 3.
 * Re-measured 2026-09-12 against 5.8.1, which corrects the last two
 * rows: the original note (2026-08-02) recorded Sharp and Sony as
 * ignoring repeat_count, and they do not.
 *
 *   NEC         67 -> 71 -> 79    a 4-entry ditto frame. The real thing.
 *   Samsung32   67 -> 135 -> 271  duplicates the entire frame
 *   RC-5        21 -> 43 -> 87    duplicates the entire frame
 *   Sharp       64 -> 128 -> 256  duplicates the entire frame
 *   Sony        26 -> 52 -> 104   duplicates the entire frame
 *
 * Only the first is a ditto. The other four are doing what send_count
 * already does, except from inside the content hash, where a delivery
 * detail has no business being. So the knob stays NEC-only everywhere
 * it appears, for the same reason it always was; only the reason
 * given for two of the four has changed.
 *
 * The correction matters beyond this comment: a whole-frame duplicate
 * lives INSIDE the block an encoder returns, so it is counted by the
 * send-spacing air-time cap and by the spacing estimate, both of which
 * measure the built command rather than the frame (GH #151).
 */
export const DITTO_PROTOCOL = "NEC";

/** Whether a row may carry dittos: NEC, and not pinned to raw replay. */
export function isDittoable(
    protocol: string | null | undefined,
    bypassed: boolean | null | undefined,
): boolean {
    if (bypassed) return false;
    return (protocol ?? "").toUpperCase() === DITTO_PROTOCOL;
}

@customElement("ir-tx-knobs")
export class IrTxKnobs extends LitElement {
    /** Whole-frame send count. Absent on the wire means 1. */
    @property({ attribute: false }) public sendCount?: number | null;
    /** NEC ditto count. Absent on the wire means none. */
    @property({ attribute: false }) public repeatCount?: number | null;
    /** True when the row carries a decoded identity. */
    @property({ type: Boolean }) public decoded = false;
    /** True when the row is pinned to raw replay. Hides the ditto glyph. */
    @property({ type: Boolean }) public bypassed = false;
    /** Start-to-start spacing between those sends, in milliseconds
     *  (GH #151). Null on an old row, which is most rows: only a row
     *  somebody tuned carries one. Never an estimate -- a list surface
     *  reports what a row STORES, and showing a computed number here
     *  would put a figure on every row that nobody chose. */
    @property({ attribute: false }) public spacingMs?: number | null;
    /** True when at least one of the row's emitters cannot hold the
     *  spacing and will send at its own pace. Off by default: emitter
     *  capability is a per-emitter server fact and list rendering does
     *  not fetch it, so today only a host that already knows can pass
     *  it. The editor's status line carries the same warning where the
     *  answer is available. */
    @property({ type: Boolean }) public approxEmitter = false;
    /** Localization key for the send-count tooltip. */
    @property({ attribute: false }) public sendsKey = "cmdrow.sends_times";
    /** Localization key for the ditto tooltip. */
    @property({ attribute: false }) public dittoKey = "cmdrow.dittos";

    /** The send glyph's tooltip.
     *
     * A tuned row's sentence is about CADENCE and says nothing about
     * what the row is, so unlike the plain sentence it is one string
     * for every host rather than one per surface.
     */
    private _sendsTitle(sends: number): string {
        const spacing = this.spacingMs ?? null;
        const base =
            spacing === null
                ? t(this.sendsKey, { count: sends })
                : t("cmdrow.sends_spaced", { count: sends, ms: spacing });
        return this.approxEmitter
            ? `${base} ${t("cmdrow.sends_approx")}`
            : base;
    }

    render() {
        const sends = this.sendCount ?? 1;
        const dittos = this.repeatCount ?? 0;
        const showSends = sends > 1;
        // Deliberately NOT gated to NEC, unlike the surfaces that let
        // you SET a ditto. This glyph reports what a row already
        // stores, and a value hidden is a value nobody can find and
        // correct. If a wig from an older build carries a ditto on
        // something other than NEC, the reader should see it.
        const showDittos = dittos > 1 && this.decoded && !this.bypassed;
        if (!showSends && !showDittos) return nothing;
        return html`
            ${showSends
                ? html`<span
                      class="knob repeat"
                      title=${this._sendsTitle(sends)}
                      ><ha-svg-icon .path=${ICON_REPEAT}></ha-svg-icon
                      >${sends}</span
                  >`
                : nothing}
            ${showDittos
                ? html`<span
                      class="knob ditto"
                      title=${t(this.dittoKey, { count: dittos })}
                      ><ha-svg-icon .path=${ICON_DITTO}></ha-svg-icon
                      >${dittos}</span
                  >`
                : nothing}
        `;
    }

    static styles = css`
        :host {
            display: inline-flex;
            gap: 6px;
            align-items: center;
        }
        .knob {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            font-size: 9px;
            font-weight: 600;
            opacity: 0.85;
            white-space: nowrap;
        }
        .repeat {
            color: var(--warning-color, #ff9800);
        }
        .ditto {
            color: var(--primary-color);
        }
        .knob ha-svg-icon {
            --mdc-icon-size: 10px;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tx-knobs": IrTxKnobs;
    }
}
