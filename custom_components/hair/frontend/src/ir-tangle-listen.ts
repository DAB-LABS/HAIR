/**
 * LISTEN -- "Requires your remote" (design brief v6 section 3, signed).
 * No opening statement, just the list, all asks visible at once.
 *
 * ONE BUTTON PER ROW (owner ruled 2026-09-03). This card used to carry
 * the repair itself: an inline Listen that armed a capture in place, a
 * Skip for now beside it, and -- from 0.14.1 -- a third button that
 * opened the paste popup. Three entries to one job, two of which could
 * only do half of it. A row now offers Fix and nothing else, and the
 * popup does the whole repair: the reason, the current bytes, a paste,
 * and the press.
 *
 * THE PRESS FLOW MOVED, IT DID NOT CHANGE. Arming, teardown, the
 * read-back against this row, the plain-words mismatch ladder, the
 * three-miss Use It Anyway and the timeout line all live in
 * ir-signal-editor's tangle context now, behaviour intact, including
 * the witness-class match logic that keys on the witnessed field
 * rather than on bare `verdict.matches`. What is left here is the
 * list, the reason line, and the cluster and unit this row needs
 * handed to the popup so a press is judged exactly as it was.
 *
 * SKIP IS GONE. Closing the popup is the skip: nothing is recorded and
 * the row stays where it was. Rows are independent now, so nothing
 * waits for every row to settle before anything can be said -- the
 * receipts ride the apply, on the section, which is where the person
 * is looking once the popup closes.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { TangleListing, TangleRow, TangleTarget } from "./types.js";
import { t } from "./localize.js";
import { targetWords } from "./ir-tangle-copy.js";
import { reasonLine } from "./ir-tangle-reason.js";
import "./ir-signal-editor.js";
import { installUnit, type MatrixUnit } from "./temperature.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";

interface HassLike {
    [key: string]: unknown;
}

@customElement("ir-tangle-listen")
export class IrTangleListen extends LitElement {
    @property({ attribute: false }) public hass!: HassLike;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public rows: TangleRow[] = [];
    @property({ attribute: false }) public listing!: TangleListing;
    /** The matrix's own native unit; display converts off it. */
    @property({ attribute: false }) public matrixUnit: MatrixUnit = "C";

    /** The row whose Fix popup is open, if any.
     *
     * The popup is the ordinary command editor in its tangle mode:
     * the reason line, the code box holding this row's current bytes,
     * paste with live validation and the carrier snap, and the press
     * flow. It is the whole repair, and closing it without applying
     * is what used to be Skip.
     */
    @state() private _fixing: TangleRow | null = null;

    /** The cluster this row belongs to, handed to the popup so the
     * read-back can tell a witness press from a recapture one. */
    private _clusterFor(row: TangleRow) {
        return this.listing.clusters.find((c) => c.members.includes(row.id)) ?? null;
    }

    /** This row's words, in the panel's unit (F9). */
    private _words(target: TangleTarget): string {
        return targetWords(target, this.matrixUnit, installUnit(this.hass));
    }

    /** The reason as plain text, for the popup that has no room for
     * markup. Same sentence the row shows, same source. */
    private _reasonText(row: TangleRow): string | null {
        return reasonLine(row, this.matrixUnit, installUnit(this.hass));
    }

    /** This row's reason, on a middle dot after its name (P5).
     *
     * Never a dash. A dash between a name and a sentence reads as an
     * aside, and the copy rule for every rendered string in this build
     * is that there are none. */
    private _reason(row: TangleRow) {
        const line = reasonLine(row, this.matrixUnit, installUnit(this.hass));
        return line ? html`<span class="reason"> · ${line}</span>` : nothing;
    }

    protected render() {
        return html`
            <div class="work">
                <!-- ONE LIST, ONE SNAPSHOT (owner walkthrough,
                     2026-09-03). This renders the rows the section
                     just counted, so a repaired row leaves on the same
                     update that drops the header count. Copying them
                     into local state was what let the two disagree. -->
                <div class="rows">${this.rows.map((row) => this._renderRow(row))}</div>
                ${this._fixing
                    ? html`<ir-signal-editor
                          .hass=${this.hass}
                          .api=${this.api}
                          .deviceId=${this.deviceId}
                          .initialPronto=${this._fixing.pronto}
                          .tangleTarget=${this._fixing.id}
                          .tangleReason=${this._reasonText(this._fixing)}
                          .tangleRow=${this._fixing}
                          .tangleCluster=${this._clusterFor(this._fixing)}
                          .matrixUnit=${this.matrixUnit}
                          allowSnap
                          @closed=${() => (this._fixing = null)}
                          @tangle-mutated=${() => (this._fixing = null)}
                      ></ir-signal-editor>`
                    : nothing}
            </div>
        `;
    }

    /** ONE ROW, ONE BUTTON. The same renderer serves a flat row and a
     * matrix cell: they differ in what their name says, not in how
     * they are repaired. */
    private _renderRow(row: TangleRow) {
        return html`
            <div class="lrow">
                <div class="ltop">
                    <span class="lname"
                        >${this._words(row.target)}${this._reason(row)}</span
                    >
                    <span class="lactions">
                        <button
                            class="action-btn fix-btn"
                            @click=${() => (this._fixing = row)}
                        >
                            ${t("tangles.open_listen")}
                        </button>
                    </span>
                </div>
            </div>
        `;
    }

    static styles = [
        actionChipStyles,
        css`
            :host {
                display: block;
            }
            /* THE CARD PAINTS THE BOX (issue 19). This used to be a
               separate rounded panel with its own background and an
               8px gap above it, so an opened bucket read as a second
               thing that had appeared near the card rather than as
               the card opening. The block in ir-tangle-section owns
               the surface and the corners now; what is left here is
               the padding the rows sit in. */
            .work {
                margin: 0;
                padding: 10px 12px;
                background: none;
                border-radius: 0;
            }
            .rows {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .lrow {
                padding: 6px 8px;
                border-radius: 4px;
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .ltop {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }
            .lname {
                flex: 1 1 auto;
                font-size: 0.8rem;
                color: var(--primary-text-color);
                min-width: 0;
            }
            .reason {
                color: var(--secondary-text-color);
                font-family: var(--paper-font-body1_-_font-family, inherit);
                font-weight: 400;
            }
            .lactions {
                display: flex;
                gap: 6px;
                flex: 0 0 auto;
            }
            /* The card's own amber, so the one button on the row reads
               as belonging to the card that opened it. */
            .fix-btn {
                color: var(--tangle-amber, #b89930);
                border-color: rgba(184, 153, 48, 0.3);
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tangle-listen": IrTangleListen;
    }
}
