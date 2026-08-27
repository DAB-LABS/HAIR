/**
 * LISTEN -- "Requires your remote" (design brief v6 section 3, signed).
 * No opening statement, just the list, all asks visible at once. Each
 * row's own LISTEN button arms a capture; a good press flips it to
 * CAPTURED and settles the row in place. ONE ROW LISTENS AT A TIME --
 * arming a second row's LISTEN moves the listening state there and
 * reverts the first.
 *
 * WITNESS-CLASS MATCH LOGIC (kickoff ruling, tangles-frontend-coding-
 * plan.md 2026-08-27 addendum, bench finding 1): a legitimate witness
 * capture can honestly read `verdict.matches: false`, because the
 * capture demonstrates a value from a DIFFERENT cell's coordinates on
 * an axis this row's own label doesn't cover. So the mismatch ladder
 * for a witness-class row keys on the witnessed field's own value
 * (against what this row/cluster needs for that field), never on bare
 * `verdict.matches`. A plain recapture row (mechanic "recapture" --
 * re-proving one already-correct code) has no such axis problem and
 * uses `verdict.matches` directly.
 *
 * ON CAPTURE, this applies the captured bytes to the row that was
 * actually aimed at (origin "capture") and stops there. It
 * deliberately does NOT also run the cluster-wide witness-synthesis +
 * batch-apply machinery (tangle/plan + tangle/apply-batch, backend
 * P7/P8) -- the design brief's LISTEN flow never mentions a batch step
 * or a representative-sample confirmation, and auto-writing an entire
 * cluster's sibling cells from one capture with no user-visible
 * confirmation step felt like a design decision this file shouldn't
 * make unilaterally. Flagged for the owner: see the build report.
 * Today, any FIX-side gain from a capture comes the ordinary way --
 * the freshly-corrected cell becoming a valid DONOR for a sibling on
 * the next listing fetch, ordinary P2 donor search, nothing special
 * wired here.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type {
    TangleListing,
    TangleRow,
    TangleListenEvent,
    TangleCaptureEvent,
} from "./types.js";
import { t } from "./localize.js";
import { targetWords } from "./ir-tangle-copy.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";

interface HassLike {
    [key: string]: unknown;
}

type RowState = "idle" | "listening" | "captured" | "skipped";

@customElement("ir-tangle-listen")
export class IrTangleListen extends LitElement {
    @property({ attribute: false }) public hass!: HassLike;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public rows: TangleRow[] = [];
    @property({ attribute: false }) public listing!: TangleListing;

    @state() private _snapshot: TangleRow[] = [];
    @state() private _states = new Map<string, RowState>();
    @state() private _missCounts = new Map<string, number>();
    @state() private _lastMessage = new Map<string, string>();
    @state() private _ladder = new Set<string>();
    @state() private _listeningRow: string | null = null;
    @state() private _closing: { count: number; fixesGained: number } | null = null;

    private _unsubscribe: (() => Promise<void>) | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        this._snapshot = this.rows;
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        void this._unsubscribe?.();
    }

    private _emitMutated(wigWritten: boolean | null): void {
        this.dispatchEvent(
            new CustomEvent("tangle-mutated", {
                detail: { wigWritten },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _clusterFor(row: TangleRow) {
        return this.listing.clusters.find((c) => c.members.includes(row.id));
    }

    private async _arm(row: TangleRow): Promise<void> {
        await this._unsubscribe?.();
        this._listeningRow = row.id;
        this._states = new Map(this._states).set(row.id, "listening");
        this._unsubscribe = await this.api.tangleListen(
            this.deviceId,
            (event) => this._onEvent(row, event),
            row.id,
        );
    }

    private async _onEvent(row: TangleRow, event: TangleListenEvent): Promise<void> {
        if (event.type === "tangle_listen_timeout") {
            // Stays listening -- a timeout just means try again; the
            // row does not revert or escalate on a timeout alone.
            return;
        }
        const capture = event as TangleCaptureEvent;
        if (!capture.decoded) {
            this._lastMessage.set(row.id, t("tangles.listen_garbled"));
            this._lastMessage = new Map(this._lastMessage);
            return;
        }

        const cluster = this._clusterFor(row);
        const isWitness = cluster?.mechanic === "witness";
        let good: boolean;
        if (isWitness && cluster?.field) {
            const readsAs = capture.verdict.reads_as as Record<string, unknown> | null;
            const witnessed = readsAs?.[cluster.field];
            const coords = row.target.coordinates as Record<string, unknown> | undefined;
            const asked = coords?.[cluster.field];
            good = witnessed !== undefined && witnessed === asked;
        } else {
            good = capture.verdict.matches === true;
        }

        if (good) {
            await this._unsubscribe?.();
            this._unsubscribe = null;
            this._listeningRow = null;
            const result = await this.api.tangleApply({
                deviceId: this.deviceId,
                target: row.id,
                pronto: capture.pronto,
                tested: true,
                source: "capture",
            });
            this._states = new Map(this._states).set(row.id, "captured");
            this._emitMutated(result.wig.written);
            this._maybeClose();
            return;
        }

        const misses = (this._missCounts.get(row.id) ?? 0) + 1;
        this._missCounts = new Map(this._missCounts).set(row.id, misses);
        const heardWord =
            (capture.verdict.reads_as as Record<string, unknown> | null)?.[
                cluster?.field ?? ""
            ] ?? "?";
        if (misses >= 3) {
            this._ladder = new Set(this._ladder).add(row.id);
            this._lastMessage.set(
                row.id,
                t("tangles.listen_mismatch_3", { heard: String(heardWord) }),
            );
        } else if (misses === 1) {
            this._lastMessage.set(
                row.id,
                t("tangles.listen_mismatch_1", { heard: String(heardWord) }),
            );
        } else {
            this._lastMessage.set(
                row.id,
                t("tangles.listen_mismatch_2", { heard: String(heardWord) }),
            );
        }
        this._lastMessage = new Map(this._lastMessage);
        // Row stays listening -- a miss never reverts the arm.
    }

    private async _useAnyway(row: TangleRow, capturedPronto: string): Promise<void> {
        await this._unsubscribe?.();
        this._unsubscribe = null;
        this._listeningRow = null;
        const result = await this.api.tangleApply({
            deviceId: this.deviceId,
            target: row.id,
            pronto: capturedPronto,
            tested: true,
            source: "capture",
            readingDisagreed: true,
        });
        this._states = new Map(this._states).set(row.id, "captured");
        this._emitMutated(result.wig.written);
        this._maybeClose();
    }

    private _skip(row: TangleRow): void {
        this._states = new Map(this._states).set(row.id, "skipped");
        if (this._listeningRow === row.id) {
            void this._unsubscribe?.();
            this._unsubscribe = null;
            this._listeningRow = null;
        }
    }

    private _maybeClose(): void {
        const allSettled = this._snapshot.every((r) => {
            const s = this._states.get(r.id) ?? "idle";
            return s === "captured" || s === "skipped";
        });
        if (!allSettled) return;
        const capturedCount = this._snapshot.filter(
            (r) => this._states.get(r.id) === "captured",
        ).length;
        if (capturedCount === 0) return;
        // Fixes gained: not independently knowable from here without a
        // fresh listing diff, which the parent owns. Report 0 and let
        // the parent's own count (already live via tangle-mutated)
        // speak for itself; the closing line's own fixes-gained clause
        // is a nice-to-have this build leaves at 0 pending a diff hook.
        this._closing = { count: capturedCount, fixesGained: 0 };
    }

    protected render() {
        if (this._closing) {
            return html`
                <div class="work">
                    <div class="closing">
                        ${t("tangles.listen_closing", {
                            count: this._closing.count,
                            gained: this._closing.fixesGained,
                        })}
                    </div>
                </div>
            `;
        }
        return html`
            <div class="work">
                <div class="rows">${this._snapshot.map((row) => this._renderRow(row))}</div>
            </div>
        `;
    }

    private _renderRow(row: TangleRow) {
        const state = this._states.get(row.id) ?? "idle";
        const message = this._lastMessage.get(row.id);
        const onLadder = this._ladder.has(row.id);

        if (state === "captured") {
            return html`
                <div class="lrow captured">
                    <span class="lname">${targetWords(row.target)}</span>
                    <span class="done-mark">${t("tangles.listen_captured")}</span>
                </div>
            `;
        }
        if (state === "skipped") {
            return html`
                <div class="lrow skipped">
                    <span class="lname">${targetWords(row.target)}</span>
                    <span class="skip-mark">${t("tangles.skip_for_now")}</span>
                </div>
            `;
        }

        const listening = state === "listening";
        return html`
            <div class="lrow">
                <div class="ltop">
                    <span class="lname">${targetWords(row.target)}</span>
                    <span class="lactions">
                        <button
                            class="action-btn listen-btn ${listening ? "pulsing" : ""}"
                            @click=${() => this._arm(row)}
                        >
                            ${listening
                                ? html`<span class="pulse"
                                      ><span class="dot"></span
                                      ><span class="dot"></span
                                      ><span class="dot"></span
                                  ></span>`
                                : t("tangles.listen")}
                        </button>
                        <button class="action-btn skip-btn" @click=${() => this._skip(row)}>
                            ${t("tangles.skip_for_now")}
                        </button>
                    </span>
                </div>
                ${message ? html`<div class="lmsg">${message}</div>` : nothing}
                ${onLadder
                    ? html`
                          <div class="ladder">
                              <button
                                  class="action-btn"
                                  @click=${() =>
                                      this._useAnyway(row, row.pronto)}
                              >
                                  ${t("tangles.use_anyway")}
                              </button>
                              <button class="action-btn" @click=${() => this._skip(row)}>
                                  ${t("tangles.skip_for_now")}
                              </button>
                          </div>
                      `
                    : nothing}
            </div>
        `;
    }

    static styles = [
        actionChipStyles,
        css`
            :host {
                display: block;
            }
            .work {
                margin: 8px 0 0 0;
                padding: 10px 12px;
                background: var(--card-background-color, var(--primary-background-color));
                border-radius: 4px;
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
            .lrow.captured {
                opacity: 0.65;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
            }
            .lrow.skipped {
                opacity: 0.5;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
            }
            .lname {
                flex: 1 1 auto;
                font-size: 0.8rem;
                color: var(--primary-text-color);
                min-width: 0;
            }
            .lactions {
                display: flex;
                gap: 6px;
                flex: 0 0 auto;
            }
            .listen-btn {
                color: var(--tangle-amber, #b89930);
                border-color: rgba(184, 153, 48, 0.3);
                min-width: 64px;
            }
            .pulse {
                display: inline-flex;
                gap: 3px;
                align-items: center;
                justify-content: center;
            }
            .pulse .dot {
                width: 4px;
                height: 4px;
                border-radius: 50%;
                background: var(--tangle-amber, #b89930);
                animation: tangle-pulse 1s ease-in-out infinite;
            }
            .pulse .dot:nth-child(2) {
                animation-delay: 0.15s;
            }
            .pulse .dot:nth-child(3) {
                animation-delay: 0.3s;
            }
            @keyframes tangle-pulse {
                0%,
                80%,
                100% {
                    opacity: 0.3;
                }
                40% {
                    opacity: 1;
                }
            }
            .lmsg {
                font-size: 0.75rem;
                color: var(--secondary-text-color);
                padding-left: 2px;
            }
            .ladder {
                display: flex;
                gap: 6px;
                padding-left: 2px;
            }
            .done-mark {
                font-size: 0.75rem;
                color: #2e7d32;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }
            .skip-mark {
                font-size: 0.75rem;
                color: var(--secondary-text-color);
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }
            .closing {
                font-size: 0.85rem;
                color: #2e7d32;
                text-align: center;
                padding: 6px 0;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tangle-listen": IrTangleListen;
    }
}
