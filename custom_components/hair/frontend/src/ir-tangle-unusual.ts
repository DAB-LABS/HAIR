/**
 * UNUSUAL -- the fourth Needs attention card (owner ruled 2026-09-27,
 * GH Discussion #177). Findings that mean "this looks unusual" rather
 * than "this is wrong": a frame count that differs from the rest of
 * the remote, a stray burst on the end. The row the server marks
 * `unusual` (tangles.is_unusual) lands here: every class on it is in
 * UNUSUAL_CLASSES and HAIR has no candidate of its own for it.
 *
 * WHY A CARD OF ITS OWN. These rows used to land in LISTEN, which asks
 * for a fresh press. A button that really sends an odd shape sends it
 * every time, so the press came back the same shape, the row returned
 * on the next comb, and there was no way to say "it works".
 *
 * THREE BUTTONS PER ROW, laid out as the other cards lay theirs:
 *   - Send: the real ir-test-button over tangle/test-send, sending the
 *     row's OWN bytes. Those are the bytes a keep would vouch for.
 *   - Fix: the row's existing mechanic. An Unusual row never has a
 *     candidate (a row HAIR can repair stays under Fixes ready), so
 *     this is always the same popup LISTEN opens: the reason, the
 *     current bytes, paste, and the press.
 *   - It Works, Keep It: the existing keep door (tangle/keep) with
 *     tested: true. Disabled, with a tooltip, until this row's current
 *     code was sent from this window in this session. The server takes
 *     `tested` on faith, so this is the only place that rule can hold.
 *
 * The record of what was sent belongs to the section (it survives
 * closing this card and is keyed to the row's bytes). This card
 * reports a send with a `tangle-unusual-sent` event and reads the
 * record back through `sent`.
 *
 * Scope is the button (owner ruling): no Kept chip, no Kept list, no
 * undo in this round. A kept row leaves the list on the refetch.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { TangleListing, TangleRow, TangleTarget } from "./types.js";
import { t } from "./localize.js";
import { targetWords } from "./ir-tangle-copy.js";
import { reasonLine } from "./ir-tangle-reason.js";
import { keepEnabled } from "./ir-tangle-buckets.js";
import "./ir-signal-editor.js";
import "./ir-test-button.js";
import { installUnit, type MatrixUnit } from "./temperature.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";

interface HassLike {
    [key: string]: unknown;
}

@customElement("ir-tangle-unusual")
export class IrTangleUnusual extends LitElement {
    @property({ attribute: false }) public hass!: HassLike;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public rows: TangleRow[] = [];
    @property({ attribute: false }) public listing!: TangleListing;
    /** The matrix's own native unit; display converts off it. */
    @property({ attribute: false }) public matrixUnit: MatrixUnit = "C";
    /** Sends made from this window, keyed by ir-tangle-buckets sentKey.
     * Owned by the section; read here. */
    @property({ attribute: false }) public sent: ReadonlySet<string> = new Set();

    /** The row whose Fix popup is open, if any. */
    @state() private _fixing: TangleRow | null = null;
    @state() private _busy = new Set<string>();
    @state() private _error: string | null = null;

    private _clusterFor(row: TangleRow) {
        return this.listing.clusters.find((c) => c.members.includes(row.id)) ?? null;
    }

    private _words(target: TangleTarget): string {
        return targetWords(target, this.matrixUnit, installUnit(this.hass));
    }

    private _reasonText(row: TangleRow): string | null {
        return reasonLine(row, this.matrixUnit, installUnit(this.hass));
    }

    /** The reason on a middle dot after the name, as LISTEN shows it. */
    private _reason(row: TangleRow) {
        const line = this._reasonText(row);
        return line ? html`<span class="reason"> · ${line}</span>` : nothing;
    }

    /** Wired to <ir-test-button>.send. The row's OWN bytes go out,
     * because those are what a keep would vouch for. A call answered
     * sent: true counts, heard or not. */
    private async _send(row: TangleRow): Promise<boolean> {
        const result = await this.api.tangleTestSend(this.deviceId, row.pronto);
        if (result.sent) {
            this.dispatchEvent(
                new CustomEvent("tangle-unusual-sent", {
                    detail: { row },
                    bubbles: true,
                    composed: true,
                }),
            );
        }
        return result.heard;
    }

    private async _keep(row: TangleRow): Promise<void> {
        if (!keepEnabled(row, this.sent)) return;
        this._busy = new Set(this._busy).add(row.id);
        this._error = null;
        try {
            const result = await this.api.tangleKeep(this.deviceId, row.id, true);
            this.dispatchEvent(
                new CustomEvent("tangle-mutated", {
                    detail: { wigWritten: result.wig.written },
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = (err as Error).message || String(err);
        } finally {
            const next = new Set(this._busy);
            next.delete(row.id);
            this._busy = next;
        }
    }

    protected render() {
        return html`
            <div class="work">
                <div class="rows">${this.rows.map((row) => this._renderRow(row))}</div>
                ${this._error
                    ? html`<div class="unusual-error">${this._error}</div>`
                    : nothing}
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
                          .tangleMapped=${this.listing.field_tier === "read"}
                          .matrixUnit=${this.matrixUnit}
                          allowSnap
                          @closed=${() => (this._fixing = null)}
                          @tangle-mutated=${() => (this._fixing = null)}
                      ></ir-signal-editor>`
                    : nothing}
            </div>
        `;
    }

    private _renderRow(row: TangleRow) {
        const busy = this._busy.has(row.id);
        const canKeep = keepEnabled(row, this.sent);
        // The tooltip rides a wrapper: a disabled button does not raise
        // hover events in every browser, so a title on the button
        // itself can go unseen exactly when it is needed.
        const hint = canKeep ? "" : t("tangles.unusual_keep_hint");
        return html`
            <div class="urow">
                <span class="uname"
                    >${this._words(row.target)}${this._reason(row)}</span
                >
                <span class="uactions">
                    <ir-test-button
                        .send=${() => this._send(row)}
                        .idleLabelKey=${"tangles.send"}
                        ?disabled=${busy}
                    ></ir-test-button>
                    <button
                        class="action-btn fix-btn"
                        ?disabled=${busy}
                        @click=${() => (this._fixing = row)}
                    >
                        ${t("tangles.open_listen")}
                    </button>
                    <span class="keep-wrap" title=${hint}>
                        <button
                            class="action-btn keep-btn"
                            ?disabled=${!canKeep || busy}
                            aria-describedby=${canKeep ? nothing : `hint-${row.id}`}
                            @click=${() => this._keep(row)}
                        >
                            ${t("tangles.unusual_keep")}
                        </button>
                        ${canKeep
                            ? nothing
                            : html`<span class="sr-only" id="hint-${row.id}"
                                  >${hint}</span
                              >`}
                    </span>
                </span>
            </div>
        `;
    }

    static styles = [
        actionChipStyles,
        css`
            :host {
                display: block;
            }
            /* The block in ir-tangle-section owns the surface and the
               corners (issue 19); this is only the padding. */
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
            .urow {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
                padding: 6px 8px;
                border-radius: 4px;
            }
            .uname {
                flex: 1 1 auto;
                font-size: 0.8rem;
                color: var(--primary-text-color);
                min-width: 0;
            }
            .reason {
                color: var(--secondary-text-color);
                font-weight: 400;
            }
            .uactions {
                display: flex;
                gap: 6px;
                flex: 0 0 auto;
                align-items: center;
            }
            .keep-wrap {
                display: inline-flex;
            }
            .keep-btn {
                color: #2e7d32;
                border-color: rgba(46, 125, 50, 0.3);
            }
            .keep-btn:disabled {
                pointer-events: none;
            }
            .unusual-error {
                margin-top: 6px;
                font-size: 0.75rem;
                color: #e65100;
            }
            .sr-only {
                position: absolute;
                width: 1px;
                height: 1px;
                overflow: hidden;
                clip: rect(0 0 0 0);
                white-space: nowrap;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tangle-unusual": IrTangleUnusual;
    }
}
