/**
 * The detangle surface (internal name "Tangles", PR #129 backend).
 * Design brief v6 (docs/internal/plans/tangles-frontend-design-brief.md)
 * is THE spec; section 6's copy table is verbatim law. Mockups
 * tangle-mockup-t4.html through t8.html are the approved look and the
 * click-annotated flows this file builds from.
 *
 * Mounted under Commands in ir-device-detail.ts, rendered only when
 * there is something to show. One calm header line, then up to three
 * cards -- "Fixes ready" [FIX], "Requires your remote" [LISTEN],
 * "Requires your answer" [DECIDE] -- each a plain sentence, a count,
 * one button opening its flow. No imposed order. One card open at a
 * time; opening a second closes the first (the brief's flows are each
 * "open it" full-width work, not simultaneous).
 *
 * BUCKETING (tangles-backend.md P6, verified against the merged
 * websocket_api.py/tangles.py source, corrected 2026-08-27): a
 * TangleListing has no bucket field of its own, and a cluster's own
 * `mechanic` is the STRONGEST road any of its members can take
 * (_best_mechanic in tangles.py), not a per-row fact -- a "donor"
 * cluster can hold a member with no donor of its own. Bucketing keys
 * on each ROW's own `has_donor` instead, which is what guarantees
 * `row.donor.pronto` (the candidate FIX actually sends/writes) exists:
 *   - FIX:    rows with `has_donor: true` (a donor candidate already
 *             exists -- nothing to capture).
 *   - LISTEN: rows with `has_donor: false`. Within LISTEN, the row's
 *             CLUSTER mechanic ("witness" vs "recapture") still picks
 *             which mismatch logic applies, per ir-tangle-listen.ts.
 *             A witness capture there can seed `tangle/plan` for its
 *             cluster; the result arrives here as a `tangle-batch-
 *             planned` event and is held in `_witnessPlans` until its
 *             cluster's members either get written (ACCEPT, in FIX) or
 *             the listing moves on without them.
 *   - DECIDE: any 2-member "identical-bytes" cluster (the duplicate-
 *             name shape P6 already clusters). The brief's other
 *             DECIDE item type ("keep or fix, this code looks
 *             unusual") has no backend data source in the merged PR
 *             #129 payload: `listing.advisories` are explicitly
 *             informational-only (tangles.py's own docstring: "not
 *             suspects", "never become rows or cards"), and every row
 *             already resolves to has_donor or one of the two LISTEN
 *             mechanics, with no ambiguous fourth case. Owner-ruled
 *             2026-08-27: omit it entirely rather than ship a dormant
 *             item type; it lands with the alias-collision ticket that
 *             designs DECIDE's full population.
 *
 * The wig write-through result each mutating command returns under
 * `wig` is tracked here (the most recent one); "Your wig has been
 * updated." (brief section 5) renders only once the whole section is
 * about to retire AND that last write reported `written: true`.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { TangleListing, TangleRow, TangleCluster, TangleBatchPlan } from "./types.js";
import { t, tp } from "./localize.js";
import type { MatrixUnit } from "./temperature.js";
import { ICON_COMB, COMB_VIEWBOX } from "./ir-icons.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-tangle-fix.js";
import "./ir-tangle-listen.js";
import "./ir-tangle-decide.js";

interface HassLike {
    language?: string;
    [key: string]: unknown;
}

type CardKey = "fix" | "listen" | "decide";

/** Which cluster (if any) a row belongs to -- built once per listing
 * fetch since clusters carry members by row id, not the reverse. */
function clusterByRowId(listing: TangleListing): Map<string, TangleCluster> {
    const map = new Map<string, TangleCluster>();
    for (const cluster of listing.clusters) {
        for (const memberId of cluster.members) {
            map.set(memberId, cluster);
        }
    }
    return map;
}

export function bucketFixRows(listing: TangleListing): TangleRow[] {
    const byId = clusterByRowId(listing);
    return listing.rows.filter((row) => {
        const cluster = byId.get(row.id);
        if (cluster?.rule === "identical-bytes") return false;
        return row.has_donor === true;
    });
}

/** LISTEN's rows: everything with no donor of its own, MINUS anything
 * a held witness plan has already built a candidate for.
 *
 * That subtraction is the whole of issue 7. One good witness capture
 * settles the row it was aimed at and stages its cluster siblings as
 * FIX rows immediately, but they kept counting here too, so after a
 * sixteen-row capture the section read "15 more fixes ready" AND "15
 * presses from your remote will finish these" -- the second claim no
 * longer true. A row belongs to one card at a time; the press is what
 * moves it. */
export function bucketListenRows(
    listing: TangleListing,
    plannedIds: ReadonlySet<string> = new Set(),
): TangleRow[] {
    const byId = clusterByRowId(listing);
    return listing.rows.filter((row) => {
        const cluster = byId.get(row.id);
        if (cluster?.rule === "identical-bytes") return false;
        if (plannedIds.has(row.id)) return false;
        return row.has_donor !== true;
    });
}

export interface DecidePair {
    cluster: TangleCluster;
    rows: TangleRow[];
}

/**
 * DECIDE, as this build can actually populate it (2026-08-27 finding,
 * owner-ruled: ship the duplicate pairing only, the keep-or-fix item
 * type has no data source today and lands with the alias-collision
 * ticket). See this file's header doc comment for the full reasoning.
 */
export function bucketDecide(listing: TangleListing): {
    pairs: DecidePair[];
} {
    const byId = new Map(listing.rows.map((r) => [r.id, r]));
    const pairs: DecidePair[] = [];
    for (const cluster of listing.clusters) {
        if (cluster.rule === "identical-bytes" && cluster.members.length === 2) {
            const rows = cluster.members
                .map((id) => byId.get(id))
                .filter((r): r is TangleRow => !!r);
            if (rows.length === 2) pairs.push({ cluster, rows });
        }
    }
    return { pairs };
}

/** One witness capture's pure plan for its cluster, held client-side
 * until ACCEPT writes it (tangle/apply-batch) or it stops applying.
 * `pendingMembers` is the deduped display list: every candidate the
 * plan found, minus the witness target itself (LISTEN already applied
 * that one directly) and minus anything already showing as an
 * ordinary donor FIX row (real has_donor, no need to say it twice). */
export interface WitnessBatchEntry {
    clusterId: string;
    witness: string;
    witnessTarget: string;
    plan: TangleBatchPlan;
    pendingMembers: string[];
}

@customElement("ir-tangle-section")
export class IrTangleSection extends LitElement {
    @property({ attribute: false }) public hass!: HassLike;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    /** The device matrix's native temperature unit, handed down so
     * row names convert like every other display surface. */
    @property({ attribute: false }) public matrixUnit: MatrixUnit = "C";

    @state() private _listing: TangleListing | null = null;
    @state() private _loading = false;
    /** Why the listing could not be read, when it could not. A silent
     * failure here used to mean the previous device's rows stayed on
     * screen looking authoritative (issue 22). */
    @state() private _error: string | null = null;
    @state() private _open: CardKey | null = null;
    @state() private _lastWigWrite: boolean | null = null;
    @state() private _justRetired = false;
    @state() private _witnessPlans = new Map<
        string,
        { witness: string; witnessTarget: string; plan: TangleBatchPlan }
    >();

    connectedCallback(): void {
        super.connectedCallback();
        void this._refresh();
    }

    updated(changed: Map<string, unknown>): void {
        if (changed.has("deviceId") && changed.get("deviceId") !== undefined) {
            this._forget();
            void this._refresh();
        }
    }

    /** EVERYTHING that belongs to the device we are leaving (issue
     * 22). The listing was the one that mattered and the one that was
     * missed: it stayed put across the switch, so the new device's
     * page rendered the old device's rows -- eleven findings on a
     * Marantz whose own listing is provably empty -- and every one of
     * them opened a flow that would have written to the wrong place.
     *
     * The rest are the same class. A held witness plan belongs to one
     * lattice. "Your wig has been updated." belongs to the device that
     * was just repaired. A stale error line belongs to the fetch that
     * failed. None of them survive a device change. */
    private _forget(): void {
        this._listing = null;
        this._open = null;
        this._witnessPlans = new Map();
        this._justRetired = false;
        this._lastWigWrite = null;
        this._error = null;
    }

    private async _refresh(): Promise<void> {
        if (!this.deviceId) return;
        // Which device this answer is for. Two quick switches can land
        // the first device's response after the second has already
        // asked, and a listing is not "the newest answer", it is one
        // device's answer.
        const asked = this.deviceId;
        this._loading = true;
        try {
            const listing = await this.api.tangles(asked);
            if (this.deviceId !== asked) return;
            this._listing = listing;
            this._error = null;
        } catch (err) {
            if (this.deviceId !== asked) return;
            // Say so. Keeping the last good listing would be the
            // stale-data bug again, arrived at from the other side.
            this._listing = null;
            this._error = (err as Error).message || String(err);
        } finally {
            if (this.deviceId === asked) this._loading = false;
        }
    }

    /** Called by a child flow after any mutating command. Records the
     * write-through outcome, re-fetches, and -- if the section is now
     * empty and the write succeeded -- shows the closing line once. */
    private _handleMutated = async (
        ev: CustomEvent<{ wigWritten: boolean | null; batchClusterApplied?: string }>,
    ): Promise<void> => {
        if (ev.detail.wigWritten !== null) this._lastWigWrite = ev.detail.wigWritten;
        if (ev.detail.batchClusterApplied) {
            const next = new Map(this._witnessPlans);
            next.delete(ev.detail.batchClusterApplied);
            this._witnessPlans = next;
        }
        const before = this._listing;
        await this._refresh();
        // Advisories are informational only (never suspects, never
        // actionable -- see bucketDecide's own doc comment) and are
        // deliberately excluded here: a device that still has
        // advisories but zero open rows is a fully retired section.
        const nowEmpty =
            this._listing &&
            this._listing.rows.length === 0 &&
            this._witnessPlans.size === 0;
        const wasNonEmpty = before && before.rows.length > 0;
        if (nowEmpty && wasNonEmpty && this._lastWigWrite) {
            this._justRetired = true;
        }
        if (nowEmpty) this._open = null;
    };

    /** A witness capture in LISTEN produced a pure plan for its
     * cluster (ir-tangle-listen.ts's tangle-batch-planned event). Held
     * here, not written -- ACCEPT in FIX is still what commits it. */
    private _handleBatchPlanned = (
        ev: CustomEvent<{
            clusterId: string;
            witness: string;
            witnessTarget: string;
            plan: TangleBatchPlan;
        }>,
    ): void => {
        const { clusterId, witness, witnessTarget, plan } = ev.detail;
        if (plan.refused || Object.keys(plan.candidates).length === 0) return;
        const next = new Map(this._witnessPlans);
        next.set(clusterId, { witness, witnessTarget, plan });
        this._witnessPlans = next;
    };

    private _toggle(card: CardKey): void {
        this._open = this._open === card ? null : card;
    }

    protected render() {
        if (this._justRetired) {
            return html`<div class="retired-line">${t("tangles.updated")}</div>`;
        }
        if (this._error) {
            return html`<div class="tangle-section">
                <div class="load-failed">${t("tangles.load_failed")}</div>
            </div>`;
        }
        if (!this._listing) return nothing;

        const fixRows = bucketFixRows(this._listing);
        const decide = bucketDecide(this._listing);
        const decideCount = decide.pairs.length * 2;

        const fixRowIds = new Set(fixRows.map((r) => r.id));
        const batchEntries: WitnessBatchEntry[] = Array.from(
            this._witnessPlans.entries(),
        )
            .map(([clusterId, held]) => {
                const pendingMembers = Object.keys(held.plan.candidates).filter(
                    (m) => m !== held.witnessTarget && !fixRowIds.has(m),
                );
                return { clusterId, ...held, pendingMembers };
            })
            .filter((entry) => entry.pendingMembers.length > 0);
        const batchCount = batchEntries.reduce(
            (sum, entry) => sum + entry.pendingMembers.length,
            0,
        );
        const fixCount = fixRows.length + batchCount;
        // The rows those plans now speak for are FIX's, not LISTEN's
        // (issue 7): counted once, in the card that can act on them.
        const plannedIds = new Set(
            batchEntries.flatMap((entry) => entry.pendingMembers),
        );
        const listenRows = bucketListenRows(this._listing, plannedIds);

        if (fixCount === 0 && listenRows.length === 0 && decideCount === 0) {
            return nothing;
        }

        // THE OPEN BUCKET BELONGS TO ITS OWN CARD (issue 13, owner
        // ruled 2026-08-30). The three panels used to render after the
        // whole card stack, so clicking LISTEN opened its rows
        // underneath the DECIDE card and the rows read as DECIDE's.
        // Each card now carries its own bucket directly beneath it and
        // the other cards keep their order around the opened block.
        const bucket = (card: CardKey) => {
            if (this._open !== card) return nothing;
            if (card === "fix") {
                return html`<ir-tangle-fix
                    .hass=${this.hass}
                    .api=${this.api}
                    .deviceId=${this.deviceId}
                    .matrixUnit=${this.matrixUnit}
                    .rows=${fixRows}
                    .listing=${this._listing}
                    .batchPlans=${batchEntries}
                ></ir-tangle-fix>`;
            }
            if (card === "listen") {
                return html`<ir-tangle-listen
                    .hass=${this.hass}
                    .api=${this.api}
                    .deviceId=${this.deviceId}
                    .matrixUnit=${this.matrixUnit}
                    .rows=${listenRows}
                    .listing=${this._listing}
                ></ir-tangle-listen>`;
            }
            return html`<ir-tangle-decide
                .hass=${this.hass}
                .api=${this.api}
                .deviceId=${this.deviceId}
                .matrixUnit=${this.matrixUnit}
                .pairs=${decide.pairs}
            ></ir-tangle-decide>`;
        };

        // The card order is the order they are built in, and it does
        // not move when one opens (owner ruling): the others stay
        // above or below the opened block exactly where they were.
        const cards: { card: CardKey; sentence: string }[] = [];
        if (fixCount > 0) {
            cards.push({
                card: "fix",
                sentence: tp("tangles.card_fix", fixCount),
            });
        }
        if (listenRows.length > 0) {
            cards.push({
                card: "listen",
                sentence: tp("tangles.card_listen", listenRows.length),
            });
        }
        if (decideCount > 0) {
            cards.push({
                card: "decide",
                sentence: t("tangles.card_decide", { count: decideCount }),
            });
        }

        return html`
            <div
                class="tangle-section"
                @tangle-mutated=${this._handleMutated}
                @tangle-batch-planned=${this._handleBatchPlanned}
            >
                <div class="tangle-header">${t("tangles.section_header")}</div>
                <!-- At most three detangle rows, at the top (ruling
                     2026-08-29). There are only ever three cards, so
                     this is the shape rather than a limit that bites,
                     but it is stated here rather than left implicit. -->
                <div class="tangle-cards">
                    ${cards.map(
                        (entry) => html`
                            <div
                                class="tcard-block ${this._open === entry.card
                                    ? "open"
                                    : ""}"
                            >
                                ${this._renderCard(entry.card, entry.sentence)}
                                ${bucket(entry.card)}
                            </div>
                        `,
                    )}
                </div>
            </div>
        `;
    }

    /** One detangle row, in the command row's own anatomy (owner
     * ruling batch, 2026-08-29): status column, name line, actions,
     * same paddings and background, no colored left edge. The comb
     * takes the slot the drag grip holds on a command row and carries
     * the card's own color -- blue FIX, amber LISTEN, copper DECIDE,
     * the colors the chrome already used, no new palette. */
    private _renderCard(card: CardKey, sentence: string) {
        const isOpen = this._open === card;
        // THE WHOLE CELL OPENS IT (owner ruled 2026-08-30). The button
        // stays as the visual call to action and remains the keyboard
        // control -- it is a real button, it focuses, and Enter on it
        // fires a click that lands here by bubbling, so there is one
        // handler rather than two racing each other.
        return html`
            <div
                class="trow ${this._loading ? "" : "clickable"}"
                @click=${() => {
                    if (!this._loading) this._toggle(card);
                }}
            >
                <div class="top-line">
                    <div class="status" aria-hidden="true">
                        <span class="comb-glyph ${card}">
                            <svg viewBox=${COMB_VIEWBOX}>
                                <path d=${ICON_COMB}></path>
                            </svg>
                        </span>
                    </div>
                    <div class="name-line">${sentence}</div>
                    <div class="actions">
                        <button
                            class="tcard-btn ${card}"
                            ?disabled=${this._loading}
                        >
                            ${isOpen ? t("tangles.close") : t(`tangles.open_${card}`)}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            :host {
                display: block;
            }
            .tangle-section {
                margin: 12px 0;
                border-top: 1px solid var(--divider-color);
                padding-top: 9px;
            }
            .load-failed {
                font-size: 0.8rem;
                color: var(--secondary-text-color);
            }
            .tangle-header {
                font-size: 0.85rem;
                font-weight: 500;
                margin-bottom: 8px;
                color: var(--primary-text-color);
            }
            .tangle-cards {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            /* A card and its open bucket are one block, so the gap
               between cards never lands between a card and the rows it
               just opened. */
            .tcard-block {
                display: flex;
                flex-direction: column;
            }
            /* ONE SURFACE (issue 19). Open, the block paints the box
               that the card used to paint alone: same background, one
               set of rounded corners around card and rows together, no
               seam and no second panel floating below. */
            .tcard-block.open {
                background: var(--primary-background-color);
                border-radius: 4px;
            }
            .tcard-block.open .trow {
                background: none;
                border-radius: 4px 4px 0 0;
            }
            /* The command row's anatomy, deliberately duplicated
               rather than imported: ir-command-row owns its styles
               inside its own shadow root, and the ruling is that these
               cells LOOK like command cells, not that they become
               them. Same paddings, same background, same three-part
               top line (32px status | flexible name | auto actions),
               same wrap behaviour at narrow widths. */
            .trow {
                display: flex;
                flex-direction: column;
                gap: 4px;
                padding: 8px 10px;
                background: var(--primary-background-color);
                border-radius: 4px;
            }
            .trow.clickable {
                cursor: pointer;
            }
            .top-line {
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 12px;
            }
            .status {
                display: flex;
                align-items: center;
                justify-content: center;
                flex: 0 0 32px;
            }
            .name-line {
                flex: 1 1 auto;
                min-width: 0;
                font-size: 0.85rem;
                color: var(--primary-text-color);
            }
            .actions {
                display: flex;
                align-items: center;
                gap: 6px;
                flex: 0 0 auto;
            }
            /* The comb sits where the drag grip sits on a command row
               and wears the card's own color. */
            .comb-glyph {
                display: inline-flex;
                align-items: center;
            }
            .comb-glyph svg {
                width: 14px;
                height: 14px;
            }
            .comb-glyph.fix svg {
                fill: var(--tangle-blue, #2196f3);
            }
            .comb-glyph.listen svg {
                fill: var(--tangle-amber, #b89930);
            }
            .comb-glyph.decide svg {
                fill: var(--tangle-copper, #b5651d);
            }
            .tcard-btn {
                background: none;
                border: 1px solid var(--divider-color);
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 0.75rem;
                font-weight: 500;
                font-family: inherit;
                cursor: pointer;
                text-transform: uppercase;
                letter-spacing: 0.03em;
                transition: background 150ms ease;
                flex: 0 0 auto;
            }
            .tcard-btn:hover {
                background: var(--secondary-background-color);
            }
            .tcard-btn.fix {
                color: var(--tangle-blue, #2196f3);
                border-color: rgba(33, 150, 243, 0.3);
            }
            .tcard-btn.listen {
                color: var(--tangle-amber, #b89930);
                border-color: rgba(184, 153, 48, 0.3);
            }
            .tcard-btn.decide {
                color: var(--tangle-copper, #b5651d);
                border-color: rgba(181, 101, 29, 0.3);
            }
            .retired-line {
                margin: 12px 0;
                padding: 10px 12px;
                font-size: 0.85rem;
                color: var(--secondary-text-color);
                text-align: center;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tangle-section": IrTangleSection;
    }
}
