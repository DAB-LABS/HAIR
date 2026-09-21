/**
 * Which lattice the dimension browser is reading.
 *
 * Split out of the card for the reason ``notice-state.ts`` was: the
 * answer is a rule rather than a render, and it is the rule this whole
 * change rests on. ``ir-matrix-card.ts`` imports ``lit`` and its
 * siblings, so the emitted module cannot stand alone under node; this
 * one imports nothing but types, which erase, so a test can RUN it
 * instead of reading it.
 */
import type { MatrixCellCoord, MatrixCells, SavePlanRow } from "./types.js";

/** What the dimension browser reads: cells plus the three vocabulary
 * lists that go with them. */
export interface LatticeView {
    cells: MatrixCellCoord[];
    modes: string[];
    fan_modes: string[];
    swing_modes: string[];
}

/** The lattice ``key`` names, or the main one when it is null.
 *
 * An extra is usually NARROWER than the main lattice -- one real
 * file's ``eco`` carries fan ``auto`` alone across four modes -- so a
 * browser reading its axes off the matrix would offer values that
 * lattice does not have, and every one of them would come back
 * ``not_found`` from the door.
 *
 * A key naming no lattice falls back to the main one, and that is the
 * only fallback anywhere in this change. It is a client-side selection
 * that can go stale only by the payload reloading under it, and the
 * alternative is a card with no branch to draw. The BACKEND never
 * falls back: there a miss is a stale client, and since every
 * coordinate the lattices share carries a different code, a fallback
 * would transmit the wrong frame and report success.
 */
export function latticeView(
    mc: MatrixCells,
    key: string | null,
): LatticeView {
    if (key !== null) {
        const found = (mc.lattices ?? []).find((l) => l.key === key);
        if (found) return found;
    }
    return mc;
}

/** Anything that may name a lattice: a card pick, a heard state, a
 * dialog row. Both fields optional and nullable, because each of those
 * spells "the main lattice" its own way -- absent, undefined or null. */
export interface LatticeRef {
    axis?: string | null;
    lattice?: string | null;
}

/** The lattice fields for a websocket message: both, or nothing.
 *
 * EVERY FORWARDER GOES THROUGH HERE. The card has always put ``axis``
 * and ``lattice`` on a pick, and the doors have always validated them,
 * but the code in between rebuilt each message from the coordinates
 * alone, so an extras cell reached the door as the MAIN lattice's cell
 * at the same coordinates. The door resolved it, the main code went
 * out, and the send reported success -- the failure the design named
 * as the worst available, because every coordinate the lattices share
 * carries a different code.
 *
 * BOTH OR NEITHER. The doors read one field without the other as a
 * client bug and refuse it, so this never emits a half pair: a ref
 * carrying only one field is treated as naming no lattice at all. And
 * for a main-lattice ref the result is an EMPTY object, so spreading
 * it adds no key whatever and the message is byte for byte what it was
 * before any of this existed -- not ``axis: null``, which would be a
 * different message even though the door happens to read it the same.
 *
 * Pure and type-only, like ``latticeView`` above, so it runs under
 * node, and written against ``LatticeRef`` rather than the card's pick
 * so the next consumer can take it as it stands.
 */
export function latticeFields(
    ref: LatticeRef | null | undefined,
): { axis: string; lattice: string } | Record<string, never> {
    const axis = ref?.axis;
    const lattice = ref?.lattice;
    if (typeof axis === "string" && typeof lattice === "string") {
        return { axis, lattice };
    }
    return {};
}

/** What TEST sends for one checklist row: a power code, or the row's
 * coordinates plus its lattice.
 *
 * The Save dialog's TEST routes a checklist row by coordinate, and the
 * same coordinates exist in the main lattice under a DIFFERENT code.
 * So the lattice goes on through ``latticeFields`` -- both or nothing,
 * and nothing at all for a main-lattice row, whose message is byte for
 * byte what it always was. Without it TEST on an extras row sends the
 * main code, the unit reacts, and the fitter ticks a row whose signed
 * code was never pressed (extras-fitting-plan.md 6).
 *
 * Pure and type-only, like the two helpers above, so a test can run it
 * on the rows the backend actually builds rather than read it. */
export function checklistSendState(row: SavePlanRow): {
    power?: "on" | "off";
    mode?: string;
    fan?: string | null;
    swing?: string | null;
    temp?: number | null;
    axis?: string;
    lattice?: string;
} {
    if (row.power) return { power: row.power as "on" | "off" };
    return {
        mode: row.mode ?? undefined,
        fan: row.fan ?? null,
        swing: row.swing ?? null,
        temp: row.temp ?? null,
        ...latticeFields(row),
    };
}

/** One lattice's run of checklist rows, headed by its word (null for
 * the main lattice). */
export interface PeerGroup {
    key: string | null;
    rows: SavePlanRow[];
}

/** The Save dialog's grouping, or null when there is nothing to group.
 *
 * NULL WHEN NO ROW NAMES A LATTICE, which is every plan for a wig
 * without extras: the dialog then draws its flat list exactly as it
 * always did, with no headings (extras-fitting-plan.md 6).
 *
 * Otherwise the rows split three ways, and NOTHING MOVES. ``before``
 * is everything ahead of the first sampled row (the ``on`` power row),
 * ``groups`` is each lattice's consecutive run of samples in checklist
 * order, and ``after`` is everything past the last sample: ``off``,
 * then the flat buttons riding along on the device. The checklist
 * already emits every extras sample after the main lattice's and
 * before ``off``, so concatenating the three reproduces the input.
 * Power stays outside every group because it belongs to the matrix,
 * never to a lattice, and ``off`` stays last so the session leaves the
 * unit off. */
export function peerGroups(rows: SavePlanRow[]): {
    before: SavePlanRow[];
    groups: PeerGroup[];
    after: SavePlanRow[];
} | null {
    if (!rows.some((r) => r.lattice != null)) return null;
    const isSample = (r: SavePlanRow): boolean =>
        !r.command_id && !r.power && !!r.mode;
    const first = rows.findIndex(isSample);
    let last = first;
    rows.forEach((r, i) => {
        if (isSample(r)) last = i;
    });
    const groups: PeerGroup[] = [];
    for (const row of rows.slice(first, last + 1)) {
        const key = row.lattice ?? null;
        const open = groups[groups.length - 1];
        if (open && open.key === key) open.rows.push(row);
        else groups.push({ key, rows: [row] });
    }
    return {
        before: rows.slice(0, first),
        groups,
        after: rows.slice(last + 1),
    };
}
