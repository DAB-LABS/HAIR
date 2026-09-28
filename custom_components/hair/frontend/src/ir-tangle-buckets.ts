/**
 * Which Needs attention card each open row belongs to, as pure
 * functions over a TangleListing. Lifted out of ir-tangle-section.ts
 * so the rules can be run under node without a DOM (GH #177), and
 * re-exported from there so every existing import keeps working.
 *
 * FOUR CARDS, ONE CARD PER ROW. The order a row is tested in is the
 * order of precedence:
 *   - DECIDE:  a member of a 2-member "identical-bytes" cluster.
 *   - UNUSUAL: the server marked it `unusual` (tangles.is_unusual:
 *              every class is in UNUSUAL_CLASSES and HAIR has no
 *              candidate for it). The predicate and the class list
 *              live on the server only; this file reads the flag and
 *              never keeps a copy of either.
 *   - FIX:     `has_donor: true` (a candidate already exists).
 *   - LISTEN:  everything else, minus rows a held witness plan has
 *              already built a candidate for.
 */
import type { TangleCluster, TangleListing, TangleRow } from "./types.js";

/** Which cluster (if any) a row belongs to -- built once per listing
 * fetch since clusters carry members by row id, not the reverse. */
export function clusterByRowId(listing: TangleListing): Map<string, TangleCluster> {
    const map = new Map<string, TangleCluster>();
    for (const cluster of listing.clusters) {
        for (const memberId of cluster.members) {
            map.set(memberId, cluster);
        }
    }
    return map;
}

/** The server's word on whether this row is merely unusual. Absent
 * (an older backend) reads as false, so the row keeps the bucket it
 * had before this card existed. */
export function isUnusualRow(row: TangleRow): boolean {
    return row.unusual === true;
}

export function bucketFixRows(listing: TangleListing): TangleRow[] {
    const byId = clusterByRowId(listing);
    return listing.rows.filter((row) => {
        const cluster = byId.get(row.id);
        if (cluster?.rule === "identical-bytes") return false;
        if (isUnusualRow(row)) return false;
        return row.has_donor === true;
    });
}

/** LISTEN's rows: everything with no donor of its own, MINUS anything
 * a held witness plan has already built a candidate for, and minus the
 * Unusual rows.
 *
 * The planned-id subtraction is the whole of issue 7. One good witness
 * capture settles the row it was aimed at and stages its cluster
 * siblings as FIX rows immediately, but they kept counting here too,
 * so after a sixteen-row capture the section read "15 more fixes
 * ready" AND "15 presses from your remote will finish these" -- the
 * second claim no longer true. A row belongs to one card at a time;
 * the press is what moves it.
 *
 * The Unusual subtraction is GH #177. A frame-shape row on a flat
 * remote has no donor, so it used to land here and ask for a press;
 * the button really does send that shape, so every press came back
 * the same shape and the row could never clear. */
export function bucketListenRows(
    listing: TangleListing,
    plannedIds: ReadonlySet<string> = new Set(),
): TangleRow[] {
    const byId = clusterByRowId(listing);
    return listing.rows.filter((row) => {
        const cluster = byId.get(row.id);
        if (cluster?.rule === "identical-bytes") return false;
        if (plannedIds.has(row.id)) return false;
        if (isUnusualRow(row)) return false;
        return row.has_donor !== true;
    });
}

/** UNUSUAL's rows (GH #177, owner ruled 2026-09-27). Findings that
 * mean "this looks unusual" rather than "this is wrong": the person
 * sends the code, and if the device answers, keeps it. */
export function bucketUnusualRows(listing: TangleListing): TangleRow[] {
    const byId = clusterByRowId(listing);
    return listing.rows.filter((row) => {
        const cluster = byId.get(row.id);
        if (cluster?.rule === "identical-bytes") return false;
        return isUnusualRow(row);
    });
}

export interface DecidePair {
    cluster: TangleCluster;
    rows: TangleRow[];
}

/**
 * DECIDE: the duplicate pairing. The brief's other DECIDE item type
 * ("keep or fix, this code looks unusual") was left out on 2026-08-27
 * because nothing could populate it; that ruling is superseded by the
 * Unusual card (owner ruled 2026-09-27, GH #177), which carries a
 * single-row keep of its own. DECIDE stays the pairing only.
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

/** How many open rows hold up a Perfect Fit: every open row except the
 * Unusual ones. The server gate counts the same thing through
 * tangles.blocking_rows. */
export function blockingCount(listing: TangleListing): number {
    return listing.rows.filter((row) => !isUnusualRow(row)).length;
}

/** The key a send is remembered under. The row AND the bytes: a send
 * proves these bytes, so if the row's code changes underneath it the
 * old send stops counting and the keep button closes again. */
export function sentKey(row: TangleRow): string {
    return `${row.id}|${row.digest}`;
}

/** "It Works, Keep It" is offered only once this row's current code
 * was sent from this window in this session. The server takes the
 * `tested` flag on faith, so this is the only place the rule can
 * actually hold. */
export function keepEnabled(row: TangleRow, sent: ReadonlySet<string>): boolean {
    return sent.has(sentKey(row));
}
