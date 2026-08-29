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
 * actually aimed at (origin "capture") and stops there -- that part
 * never changed. What DID change (owner ruling 2026-08-27, superseding
 * this file's earlier documented choice to leave the rest passive):
 * for a WITNESS-mechanic row, a good capture also asks `tangle/plan`
 * (pure, nothing written) for its cluster with this capture as the
 * witness reading. Never auto-applied -- the plan's candidates are
 * handed up to the section as pending work, so they can appear as
 * ordinary FIX rows and move the "Fixes ready" count live, exactly per
 * the brief's LISTEN closing line ("your presses built N more fixes,
 * waiting under Fixes ready"). Writing them is still ACCEPT's job, in
 * FIX, same as any other candidate. A RECAPTURE-mechanic row never
 * plans -- "nothing can be derived" is the whole meaning of that
 * mechanic, so there is nothing a plan could find beyond the row just
 * captured.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type {
    TangleListing,
    TangleRow,
    TangleListenEvent,
    TangleCaptureEvent,
    TangleBatchPlan,
    TangleTarget,
} from "./types.js";
import { t, tp } from "./localize.js";
import { targetWords } from "./ir-tangle-copy.js";
import { installUnit, type MatrixUnit } from "./temperature.js";
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
    /** The matrix's own native unit; display converts off it. */
    @property({ attribute: false }) public matrixUnit: MatrixUnit = "C";

    @state() private _snapshot: TangleRow[] = [];
    @state() private _states = new Map<string, RowState>();
    @state() private _missCounts = new Map<string, number>();
    @state() private _lastMessage = new Map<string, string>();
    // The most recent decoded capture per row, good or mismatched --
    // USE IT ANYWAY has to apply THIS, never the row's own current
    // (still-wrong) bytes.
    @state() private _lastPronto = new Map<string, string>();
    @state() private _ladder = new Set<string>();
    @state() private _listeningRow: string | null = null;
    @state() private _closing: { count: number; fixesGained: number } | null = null;
    private _fixesGained = 0;

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

    /** Hands a witness cluster's pure plan up to the section, which
     * merges its candidates into what FIX shows -- nothing here writes
     * anything. */
    private _emitBatchPlanned(
        clusterId: string,
        witness: string,
        witnessTarget: string,
        plan: TangleBatchPlan,
    ): void {
        this.dispatchEvent(
            new CustomEvent("tangle-batch-planned", {
                detail: { clusterId, witness, witnessTarget, plan },
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

    /** Common tail of a settled capture (a clean match, or a ladder
     * override): write the row, then -- witness rows only -- ask what
     * else this reading could seed and hand it up. */
    private async _finishCapture(
        row: TangleRow,
        pronto: string,
        readingDisagreed: boolean,
    ): Promise<void> {
        await this._unsubscribe?.();
        this._unsubscribe = null;
        this._listeningRow = null;
        const cluster = this._clusterFor(row);
        const result = await this.api.tangleApply({
            deviceId: this.deviceId,
            target: row.id,
            pronto,
            tested: true,
            // LISTEN has no SEND. A captured press is evidence of a
            // press, not of a transmission, so zero is the true tally
            // and the receipt reads accepted, never air-tested.
            sendsFired: 0,
            source: "capture",
            ...(readingDisagreed ? { readingDisagreed: true } : {}),
        });
        this._states = new Map(this._states).set(row.id, "captured");
        this._emitMutated(result.wig.written);

        if (cluster?.mechanic === "witness" && cluster.field) {
            try {
                const plan = await this.api.tanglePlan({
                    deviceId: this.deviceId,
                    cluster: cluster.id,
                    witness: pronto,
                    witnessTarget: row.id,
                });
                if (!plan.refused) {
                    const gained = Object.keys(plan.candidates).filter(
                        (member) => member !== row.id,
                    ).length;
                    this._fixesGained += gained;
                    this._emitBatchPlanned(cluster.id, pronto, row.id, plan);
                }
            } catch {
                // Best-effort. The row this LISTEN session was actually
                // working is already applied and settled above; a plan
                // that fails to resolve just means no sibling rows show
                // up early -- they are still reachable the ordinary way
                // once this cell counts as a donor.
            }
        }

        this._maybeClose();
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
        this._lastPronto.set(row.id, capture.pronto);
        this._lastPronto = new Map(this._lastPronto);

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
            await this._finishCapture(row, capture.pronto, false);
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

    private async _useAnyway(row: TangleRow): Promise<void> {
        const pronto = this._lastPronto.get(row.id);
        if (!pronto) return;
        await this._finishCapture(row, pronto, true);
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
        this._closing = { count: capturedCount, fixesGained: this._fixesGained };
    }


    /** This row's words, in the panel's unit (F9). */
    private _words(target: TangleTarget): string {
        return targetWords(target, this.matrixUnit, installUnit(this.hass));
    }

    protected render() {
        if (this._closing) {
            return html`
                <div class="work">
                    <div class="closing">
                        ${tp("tangles.listen_closing", this._closing.count, {
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
                    <span class="lname">${this._words(row.target)}</span>
                    <span class="done-mark">${t("tangles.listen_captured")}</span>
                </div>
            `;
        }
        if (state === "skipped") {
            return html`
                <div class="lrow skipped">
                    <span class="lname">${this._words(row.target)}</span>
                    <span class="skip-mark">${t("tangles.skip_for_now")}</span>
                </div>
            `;
        }

        const listening = state === "listening";
        return html`
            <div class="lrow">
                <div class="ltop">
                    <span class="lname">${this._words(row.target)}</span>
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
                              <button class="action-btn" @click=${() => this._useAnyway(row)}>
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
