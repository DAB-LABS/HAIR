/**
 * The LAST HEARD row (signpost 4, Track M, mockup m1).
 *
 * One row, between the STATE MATRIX card and TRIGGERS on a matrix
 * Remote, holding the most recent state that remote heard. It is a
 * READOUT, not a trigger: no toggle, no edit, no delete, no HA glyph.
 * It has exactly one door -- + Trigger -- which opens the trigger
 * dialog pre-filled and mints a real row in TRIGGERS below, leaving
 * this row untouched.
 *
 * It borrows the trigger-row anatomy (ir-trigger-row-styles.ts) so the
 * two read as the same family, with two deliberate differences the
 * handoff calls out:
 *
 * - The grip column is present but EMPTY. The row is not reorderable,
 *   and the 24px keeps line one's name and line two's diamonds on the
 *   same left edge a trigger row has.
 * - The when/where text takes NO fixed-width reservation. A real
 *   trigger row reserves 144px so a LIST of rows aligns; this row is
 *   always alone, with nothing to align against.
 *
 * Empty state is a row, not an absence: "Nothing heard yet" in muted
 * italic with + Trigger present and disabled (the brief asks for
 * "action disabled", not "no action").
 */
import { LitElement, html, css, nothing } from "lit";
import { actionChipStyles } from "./ir-action-chip-styles";
import { customElement, property } from "./decorators.js";
import { t } from "./localize.js";
import { relTime, triggerRowStyles } from "./ir-trigger-row-styles.js";
import type { LastHeard, ReceiverInfo } from "./types.js";

@customElement("ir-last-heard-row")
export class IrLastHeardRow extends LitElement {
    @property({ attribute: false }) heard: LastHeard | null = null;
    /** For naming the receiver the frame came in on. */
    @property({ attribute: false }) receivers: ReceiverInfo[] = [];

    private _where(): string {
        const h = this.heard;
        if (!h) return "";
        // The area is the friendlier fact when the backend resolved
        // one (the v0.5.7 location trio), the receiver's own name
        // otherwise.
        if (h.receiver_area_name) return h.receiver_area_name;
        if (!h.receiver_entity_id) return "";
        const match = this.receivers.find(
            (r) => r.entity_id === h.receiver_entity_id,
        );
        return match?.name ?? h.receiver_entity_id;
    }

    /** The diamonds, straight from the stored S/L pattern.
     *
     * A trigger row decodes its own Pronto to get here; this row is
     * handed the pattern at stamp time instead, so the panel never
     * needs the matrix file to draw line two. */
    private _renderDiamonds() {
        const pattern = this.heard?.sl_pattern;
        if (!pattern) return nothing;
        return html`<span class="diamonds"
            >${[...pattern].map((ch) =>
                ch === "L"
                    ? html`<span class="diamond long">&#9670;</span>`
                    : html`<span class="diamond short">&#9671;</span>`,
            )}</span
        >`;
    }

    private _addTrigger(): void {
        if (!this.heard) return;
        this.dispatchEvent(
            new CustomEvent("last-heard-trigger", {
                detail: this.heard,
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const h = this.heard;
        const where = this._where();
        const when = h ? relTime(h.at) : "";
        return html`
            <div class="trow">
                <div class="trow-top">
                    <div class="trow-grip"></div>
                    <div class="trow-namewrap">
                        ${h
                            ? html`<span class="trow-name">${h.cell_name}</span>`
                            : html`<span class="trow-name empty"
                                  >${t("lastheard.nothing")}</span
                              >`}
                    </div>
                    ${h
                        ? html`<span class="lh-when"
                              >${where
                                  ? html`${where} &middot; ${when}`
                                  : when}</span
                          >`
                        : nothing}
                    <button
                        class="action-btn trigger-btn"
                        ?disabled=${!h}
                        @click=${this._addTrigger}
                    >
                        ${t("trow.add_trigger")}
                    </button>
                </div>
                <div class="trow-diamonds">${this._renderDiamonds()}</div>
            </div>
        `;
    }

    static styles = [
        actionChipStyles,
        triggerRowStyles,
        css`
            /* Nothing heard yet: muted and italic, so an empty row
               reads as a state rather than as a name. */
            .trow-name.empty {
                font-style: italic;
                font-weight: 400;
                color: var(--secondary-text-color);
            }
            /* Location before time, and NO width reservation -- see the
               module comment for why this row does not take the
               trigger row's 144px. */
            .lh-when {
                font-size: 0.74rem;
                color: var(--secondary-text-color);
                white-space: nowrap;
                margin-left: auto;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-last-heard-row": IrLastHeardRow;
    }
}
