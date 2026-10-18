/**
 * The Sniffer's Listen row (BroadSniff Listen, 2026-10-17).
 *
 * A Broadlink hears IR only while BroadSniff (DAB-LABS/broadsniff) has a
 * capture window open on it, and the user is in the Sniffer when they
 * want it to listen. This row is a "Listen:" label and one
 * ``ir-listen-chip`` per BroadSniff remote; the chip carries all the
 * behaviour (the toggle, the fill, the bloom) and is the same element
 * the Devices page shows on the remote's hardware card.
 *
 * The look is the device pages' header chip group, from the shared
 * ir-header-chip-styles module, except for the label (round 2, owner):
 * the header chip group lines its labels up in a fixed right-aligned
 * column because several rows share it, and the Sniffer has nothing to
 * line up with, so here the label sits flush with the section title's
 * left edge and the chips follow it, wrapping when there are several.
 */
import { LitElement, html, css, nothing } from "lit";
import type { HairApi } from "./api.js";
import { headerChipStyles } from "./ir-header-chip-styles.js";
import "./ir-listen-chip.js";
import { customElement, property } from "./decorators.js";
import { t } from "./localize.js";
import type { BroadSniffReceiverRow } from "./types.js";

@customElement("ir-listen-row")
export class IrListenRow extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public rows: BroadSniffReceiverRow[] = [];

    render() {
        if (this.rows.length === 0) return nothing;
        return html`
            <div class="hdr-row" role="group" aria-label=${t("listen.label")}>
                <span class="hdr-row-label listen-label">${t("listen.label")}</span>
                <div class="hdr-row-pills">
                    ${this.rows.map(
                        (row) => html`<ir-listen-chip
                            .hass=${this.hass}
                            .api=${this.api}
                            .row=${row}
                        ></ir-listen-chip>`,
                    )}
                </div>
            </div>
        `;
    }

    static styles = [
        headerChipStyles,
        css`
            :host {
                display: block;
            }
            /* Flush left, sized to its word: no shared label column. */
            .listen-label {
                width: auto;
                text-align: left;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-listen-row": IrListenRow;
    }
}
