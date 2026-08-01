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
    /** Localization key for the send-count tooltip. */
    @property({ attribute: false }) public sendsKey = "cmdrow.sends_times";
    /** Localization key for the ditto tooltip. */
    @property({ attribute: false }) public dittoKey = "cmdrow.dittos";

    render() {
        const sends = this.sendCount ?? 1;
        const dittos = this.repeatCount ?? 0;
        const showSends = sends > 1;
        const showDittos = dittos > 1 && this.decoded && !this.bypassed;
        if (!showSends && !showDittos) return nothing;
        return html`
            ${showSends
                ? html`<span
                      class="knob repeat"
                      title=${t(this.sendsKey, { count: sends })}
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
