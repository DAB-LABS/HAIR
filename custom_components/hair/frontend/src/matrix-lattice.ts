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
import type { MatrixCellCoord, MatrixCells } from "./types.js";

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
