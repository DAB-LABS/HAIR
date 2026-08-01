/**
 * The protocol chip (Highlights, GH #78) -- one pill, five homes.
 *
 * A signal either transmits as its decoded protocol rebuilt clean, or as
 * the bytes that were captured. The chip says which, and where it is
 * interactive it is also how you change it.
 *
 * Owner rulings baked in (2026-08-01):
 * - TWO states, not three. The protocol name, or BYPASS. A row that
 *   decoded nothing renders NO CHIP AT ALL, which is what it already did
 *   before this existed.
 * - ONE pill everywhere. Same geometry, same colours, in every location.
 *   Read-only surfaces differ only by `cursor: default` and no hover. An
 *   earlier draft used a second, greyer chip for static contexts to
 *   signal un-clickability; that was rejected, correctly, because it
 *   makes one fact look like two things depending on the screen.
 * - The protocol name never goes inside translated copy. It is a proper
 *   noun that can legitimately be absent, so interpolating it would
 *   leave a hole in the translation. The sentence stands alone and the
 *   name is appended after a middot.
 *
 * This settles the static-pill decision parked on 2026-06-21.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property } from "./decorators.js";
import { t } from "./localize.js";

@customElement("ir-protocol-chip")
export class IrProtocolChip extends LitElement {
    /** The decoded protocol name, or null when nothing decoded. */
    @property({ attribute: false }) public protocol: string | null = null;
    /** True when this row is pinned to raw replay. */
    @property({ type: Boolean }) public bypass = false;
    /** Read-only surfaces (fitting rows, Closet) pass false. */
    @property({ type: Boolean }) public interactive = false;
    @property({ type: Boolean }) public disabled = false;

    private _toggle(e: Event): void {
        e.stopPropagation();
        if (!this.interactive || this.disabled) return;
        this.dispatchEvent(
            new CustomEvent("toggle-bypass", {
                detail: { bypass: !this.bypass },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        // Nothing decoded means no chip. There is no protocol to name and
        // no re-encode to bypass, so the send path is already raw and a
        // pill would describe a choice that does not exist.
        if (!this.protocol) return nothing;
        const label = this.bypass ? t("chip.bypass") : this.protocol;
        const title = this.bypass
            ? `${t("chip.bypass_tip")} · ${this.protocol}`
            : t("chip.decoded_tip");
        return html`<button
            class="chip ${this.bypass ? "on" : ""} ${this.interactive
                ? "live"
                : ""}"
            ?disabled=${this.disabled || !this.interactive}
            title=${title}
            @click=${this._toggle}
        >
            ${label}
        </button>`;
    }

    static styles = css`
        :host {
            display: inline-flex;
        }
        /* Theme-safe: the two colours ride Home Assistant's semantic
           variables rather than fixed hexes, so a pale blue that reads on
           a dark card cannot go invisible on a light one. */
        .chip {
            font-family: inherit;
            font-size: 9.5px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            white-space: nowrap;
            padding: 2px 7px;
            border-radius: 9px;
            border: 1px solid;
            background: none;
            cursor: default;
            /* 1.05, not 1.5 (owner ruling 2026-08-01). At 9.5px the old
               value gave a 14.25px line box, and with the padding and the
               border that made a 20px pill against the 16px one the
               Mirror has always used. This lands at ~16px so the chip
               sits in a row rather than setting its height. */
            line-height: 1.05;
            color: var(--info-color, #64b5f6);
            border-color: var(--info-color, #64b5f6);
            opacity: 0.9;
        }
        /* BYPASS is a deliberate override of a decoder that exists, which
           is worth more attention than the ordinary decoded state. */
        .chip.on {
            color: var(--warning-color, #e6a23c);
            border-color: var(--warning-color, #e6a23c);
        }
        .chip.live {
            cursor: pointer;
        }
        .chip.live:hover {
            opacity: 1;
        }
        .chip[disabled] {
            cursor: default;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-protocol-chip": IrProtocolChip;
    }
}
