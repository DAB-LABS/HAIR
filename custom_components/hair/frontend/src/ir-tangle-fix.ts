/**
 * FIX -- "Fixes ready" (design brief v6 section 2, signed). A donor
 * candidate already exists for every row here; the flow is SEND
 * (optional, no question follows it) and ACCEPT (settles the row in
 * place), plus one ACCEPT ALL that cascades every remaining row and
 * collapses the card to its receipt.
 *
 * SEND is the panel's real, already-shipped `ir-test-button` --
 * unforked, per the kickoff's own rule -- with its idle label pointed
 * at the "tangles.send" locale key instead of the component's own
 * default (TEST). `hair/device/tangle/test-send`'s corrected contract
 * (owner-ruled 2026-08-27, matching sendCommand/matrixSend) reports
 * `heard`, so a receiver catch renders SENT . HEARD exactly like every
 * other send button in the panel.
 *
 * Every ordinary row's candidate is `row.donor.pronto` -- `row.pronto`
 * is what the cell CURRENTLY transmits (list_tangles sets it from the
 * cell/command's own bytes), the very thing this row is wrong about.
 * Sending or accepting `row.pronto` would just re-prove and re-write
 * the broken code back onto itself.
 *
 * Row order is snapshotted on open and held stable -- "no reordering
 * while the workspace is open" (brief section 7). Accepted rows render
 * as a done line IN PLACE rather than disappearing, until the parent
 * re-fetches and this component is torn down/rebuilt on next open.
 *
 * BATCH CARDS (owner ruling 2026-08-27, LISTEN's witness-plan finding):
 * a witness capture in LISTEN seeds `tangle/plan` for its cluster, and
 * the section hands the result down here as `batchPlans` -- candidates
 * for that cluster's OTHER members, still unwritten, appearing as
 * ordinary FIX work per the brief's LISTEN closing line. A batch has
 * no single donor pronto to send/accept per row; it is one cluster,
 * one representative sample to prove (`plan.sample`, minus whatever
 * the witness press itself already proved), and one atomic
 * `tangle/apply-batch` write for every member once that sample is in.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { TangleListing, TangleRow, TangleTarget } from "./types.js";
import { t, tp } from "./localize.js";
import { targetWords } from "./ir-tangle-copy.js";
import { installUnit, type MatrixUnit } from "./temperature.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";
import "./ir-test-button.js";
import type { WitnessBatchEntry } from "./ir-tangle-section.js";

interface HassLike {
    [key: string]: unknown;
}

@customElement("ir-tangle-fix")
export class IrTangleFix extends LitElement {
    @property({ attribute: false }) public hass!: HassLike;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public rows: TangleRow[] = [];
    @property({ attribute: false }) public listing!: TangleListing;
    @property({ attribute: false }) public batchPlans: WitnessBatchEntry[] = [];
    /** The matrix's own native unit; display converts off it. */
    @property({ attribute: false }) public matrixUnit: MatrixUnit = "C";

    @state() private _snapshot: TangleRow[] = [];
    @state() private _accepted = new Set<string>();
    @state() private _accepting = new Set<string>();
    @state() private _acceptAllBusy = false;
    @state() private _receipt: { count: number; targets: string[] } | null = null;
    @state() private _undoing = false;

    // Every SEND this card actually put on the air, keyed by target.
    // A call answered sent: true is the only thing that counts: this
    // is evidence, it feeds the tier, and it is strict where the
    // corner dot is not. Unheard still counts -- a send nothing hears
    // is still a send (owner ruling 2026-08-28, brief s8).
    @state() private _sends = new Map<string, number>();

    // Per cluster: which sample members have been proved this session
    // (seeded with the witness target itself -- LISTEN already proved
    // that one on air before this card ever existed).
    private _batchTested = new Map<string, Set<string>>();
    @state() private _batchBusy = new Set<string>();
    @state() private _batchError = new Map<string, string>();
    @state() private _batchDone = new Set<string>();

    connectedCallback(): void {
        super.connectedCallback();
        this._snapshot = this.rows;
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

    private _emitBatchApplied(clusterId: string, wigWritten: boolean | null): void {
        this.dispatchEvent(
            new CustomEvent("tangle-mutated", {
                detail: { wigWritten, batchClusterApplied: clusterId },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _sendsFor(target: string): number {
        return this._sends.get(target) ?? 0;
    }

    private _countSend(target: string): void {
        this._sends = new Map(this._sends).set(
            target,
            this._sendsFor(target) + 1,
        );
    }

    /** This cluster's tallies, keyed by target. Only the members this
     * card knows of: apply-batch re-plans server-side, so the client
     * has no authority over the member list, and a key it omits reads
     * as zero. */
    private _sendsForBatch(entry: WitnessBatchEntry): Record<string, number> {
        const counts: Record<string, number> = {};
        for (const target of [entry.witnessTarget, ...entry.pendingMembers]) {
            counts[target] = this._sendsFor(target);
        }
        return counts;
    }

    /** Wired straight to <ir-test-button>.send: resolves to whether a
     * receiver heard the echo, so the button itself decides SENT vs.
     * SENT . HEARD. No question ever follows a send (brief section 2)
     * -- this never touches _accepted. */
    private async _send(row: TangleRow): Promise<boolean> {
        const pronto = row.donor?.pronto ?? row.pronto;
        const result = await this.api.tangleTestSend(this.deviceId, pronto);
        if (result.sent) this._countSend(row.id);
        return result.heard;
    }

    private async _accept(row: TangleRow): Promise<void> {
        this._accepting = new Set(this._accepting).add(row.id);
        try {
            const result = await this.api.tangleApply({
                deviceId: this.deviceId,
                target: row.id,
                pronto: row.donor?.pronto ?? row.pronto,
                tested: true,
                sendsFired: this._sendsFor(row.id),
                source: "donor",
            });
            this._accepted = new Set(this._accepted).add(row.id);
            this._emitMutated(result.wig.written);
        } finally {
            const next = new Set(this._accepting);
            next.delete(row.id);
            this._accepting = next;
        }
    }

    private async _acceptAll(): Promise<void> {
        this._acceptAllBusy = true;
        const targets: string[] = [];
        let lastWigWritten: boolean | null = null;
        try {
            for (const row of this._snapshot) {
                if (this._accepted.has(row.id)) continue;
                try {
                    // eslint-disable-next-line no-await-in-loop -- a
                    // visible top-to-bottom cascade is the point
                    // (brief section 2): each row settles before the
                    // next fires, so the user can watch it happen.
                    const result = await this.api.tangleApply({
                        deviceId: this.deviceId,
                        target: row.id,
                        pronto: row.donor?.pronto ?? row.pronto,
                        tested: true,
                        sendsFired: this._sendsFor(row.id),
                        source: "donor",
                    });
                    this._accepted = new Set(this._accepted).add(row.id);
                    targets.push(row.id);
                    lastWigWritten = result.wig.written;
                } catch {
                    // A row that did not convince stays un-accepted and
                    // remains a finding (brief section 2) -- no halt,
                    // the cascade continues past a single failure.
                }
            }
            this._receipt = { count: targets.length, targets };
            this._emitMutated(lastWigWritten);
        } finally {
            this._acceptAllBusy = false;
        }
    }

    private async _undo(): Promise<void> {
        if (!this._receipt) return;
        this._undoing = true;
        let lastWigWritten: boolean | null = null;
        try {
            for (const target of this._receipt.targets) {
                // eslint-disable-next-line no-await-in-loop
                const result = await this.api.tangleRevert(this.deviceId, target);
                lastWigWritten = result.wig.written;
            }
            this._receipt = null;
            this._accepted = new Set();
            this._emitMutated(lastWigWritten);
        } finally {
            this._undoing = false;
        }
    }

    private _testedFor(entry: WitnessBatchEntry): Set<string> {
        let set = this._batchTested.get(entry.clusterId);
        if (!set) {
            set = new Set([entry.witnessTarget]);
            this._batchTested.set(entry.clusterId, set);
        }
        return set;
    }

    private async _sendBatchMember(entry: WitnessBatchEntry, member: string): Promise<boolean> {
        const candidate = entry.plan.candidates[member];
        const pronto = (candidate?.pronto as string | undefined) ?? "";
        const result = pronto
            ? await this.api.tangleTestSend(this.deviceId, pronto)
            : { sent: false, heard: false, receiver: null, emitters: [] };
        // Only a real transmission is tallied. The empty-candidate
        // branch above sends nothing, and a call answered sent: false
        // put nothing on the air either.
        if (result.sent) this._countSend(member);
        // A member joins the sample only when a transmission really
        // fired for it. The backend takes tested_targets on faith and
        // cannot check this from its side, so marking an untransmitted
        // member here would manufacture the very evidence the receipt
        // ruling exists to stop. Recorded, never verified still holds
        // for what a send PROVED: unheard counts, because sent is the
        // predicate, not heard.
        if (result.sent) this._testedFor(entry).add(member);
        this.requestUpdate();
        return result.heard;
    }

    private async _acceptBatch(entry: WitnessBatchEntry): Promise<void> {
        this._batchBusy = new Set(this._batchBusy).add(entry.clusterId);
        this._batchError = new Map(this._batchError);
        this._batchError.delete(entry.clusterId);
        try {
            const testedTargets = Array.from(this._testedFor(entry));
            const result = await this.api.tangleApplyBatch({
                deviceId: this.deviceId,
                cluster: entry.clusterId,
                tested: true,
                testedTargets,
                sendsFired: this._sendsForBatch(entry),
                witness: entry.witness,
                witnessTarget: entry.witnessTarget,
            });
            this._batchDone = new Set(this._batchDone).add(entry.clusterId);
            this._emitBatchApplied(entry.clusterId, result.wig.written);
        } catch (err) {
            this._batchError = new Map(this._batchError).set(
                entry.clusterId,
                err instanceof Error ? err.message : String(err),
            );
        } finally {
            const next = new Set(this._batchBusy);
            next.delete(entry.clusterId);
            this._batchBusy = next;
        }
    }


    /** This row's words, in the panel's unit (F9). */
    private _words(target: TangleTarget): string {
        return targetWords(target, this.matrixUnit, installUnit(this.hass));
    }

    protected render() {
        if (this._receipt) {
            return html`
                <div class="work">
                    <div class="receipt">
                        ${tp("tangles.fix_receipt", this._receipt.count)}
                        <button
                            class="action-btn"
                            ?disabled=${this._undoing}
                            @click=${() => this._undo()}
                        >
                            ${t("tangles.undo")}
                        </button>
                    </div>
                </div>
            `;
        }

        const remaining = this._snapshot.filter((r) => !this._accepted.has(r.id));
        const batchesLive = this.batchPlans.filter(
            (entry) => !this._batchDone.has(entry.clusterId),
        );
        const totalCount =
            this._snapshot.length +
            batchesLive.reduce((sum, entry) => sum + entry.pendingMembers.length, 0);

        return html`
            <div class="work">
                <div class="case">${tp("tangles.fix_case", totalCount)}</div>
                <div class="rows">
                    ${this._snapshot.map((row) => this._renderRow(row))}
                    ${batchesLive.map((entry) => this._renderBatch(entry))}
                </div>
                ${remaining.length > 0
                    ? html`
                          <button
                              class="accept-all-btn"
                              ?disabled=${this._acceptAllBusy}
                              @click=${() => this._acceptAll()}
                          >
                              ${tp("tangles.accept_all", remaining.length)}
                          </button>
                      `
                    : nothing}
            </div>
        `;
    }

    private _renderRow(row: TangleRow) {
        const done = this._accepted.has(row.id);
        const accepting = this._accepting.has(row.id);
        if (done) {
            return html`
                <div class="rrow done">
                    <span class="rname">${this._words(row.target)}</span>
                    <span class="done-mark">${t("tangles.row_done")}</span>
                </div>
            `;
        }
        return html`
            <div class="rrow">
                <span class="rname">${this._words(row.target)}</span>
                <span class="ractions">
                    <ir-test-button
                        .send=${() => this._send(row)}
                        .idleLabelKey=${"tangles.send"}
                        ?disabled=${accepting}
                    ></ir-test-button>
                    <button
                        class="action-btn accept-btn"
                        ?disabled=${accepting}
                        @click=${() => this._accept(row)}
                    >
                        ${t("tangles.accept")}
                    </button>
                </span>
            </div>
        `;
    }

    private _renderBatch(entry: WitnessBatchEntry) {
        const tested = this._testedFor(entry);
        const sampleRemaining = entry.plan.sample.filter((m) => !tested.has(m));
        const canAccept = sampleRemaining.length === 0;
        const busy = this._batchBusy.has(entry.clusterId);
        const error = this._batchError.get(entry.clusterId);
        const byId = new Map(this.listing.rows.map((r) => [r.id, r]));

        return html`
            <div class="brow">
                <div class="bintro">
                    ${tp("tangles.batch_intro", entry.pendingMembers.length)}
                </div>
                ${sampleRemaining.map((member) => {
                    const target = byId.get(member)?.target;
                    const candidate = entry.plan.candidates[member];
                    const pronto = (candidate?.pronto as string | undefined) ?? "";
                    return html`
                        <div class="rrow">
                            <span class="rname"
                                >${target ? this._words(target) : member}</span
                            >
                            <span class="ractions">
                                <ir-test-button
                                    .send=${() => this._sendBatchMember(entry, member)}
                                    .idleLabelKey=${"tangles.send"}
                                    ?disabled=${!pronto || busy}
                                ></ir-test-button>
                            </span>
                        </div>
                    `;
                })}
                ${error ? html`<div class="berror">${error}</div>` : nothing}
                <button
                    class="action-btn accept-btn"
                    ?disabled=${!canAccept || busy}
                    @click=${() => this._acceptBatch(entry)}
                >
                    ${tp("tangles.accept_all", entry.pendingMembers.length)}
                </button>
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
            .case {
                font-size: 0.85rem;
                color: var(--primary-text-color);
                margin-bottom: 10px;
                max-width: 640px;
            }
            .rows {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .rrow {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
                padding: 6px 8px;
                border-radius: 4px;
            }
            .rrow.done {
                opacity: 0.65;
            }
            .rname {
                flex: 1 1 auto;
                font-size: 0.8rem;
                font-family: var(--code-font-family, monospace);
                color: var(--primary-text-color);
                min-width: 0;
            }
            .ractions {
                display: flex;
                gap: 6px;
                flex: 0 0 auto;
                align-items: center;
            }
            .accept-btn {
                color: #2e7d32;
                border-color: rgba(46, 125, 50, 0.3);
            }
            .done-mark {
                font-size: 0.75rem;
                color: #2e7d32;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }
            .accept-all-btn {
                margin-top: 10px;
                padding: 9px 20px;
                font-size: 0.85rem;
                font-weight: 500;
                font-family: inherit;
                text-transform: uppercase;
                letter-spacing: 0.03em;
                color: #fff;
                background: var(--tangle-blue, #2196f3);
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .accept-all-btn:disabled {
                opacity: 0.5;
                cursor: default;
            }
            .receipt {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 0.85rem;
                color: #2e7d32;
            }
            .brow {
                display: flex;
                flex-direction: column;
                gap: 4px;
                padding: 6px 8px;
                border-radius: 4px;
                border-left: 3px solid var(--tangle-amber, #b89930);
            }
            .bintro {
                font-size: 0.78rem;
                color: var(--secondary-text-color);
            }
            .berror {
                font-size: 0.75rem;
                color: #e65100;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tangle-fix": IrTangleFix;
    }
}
