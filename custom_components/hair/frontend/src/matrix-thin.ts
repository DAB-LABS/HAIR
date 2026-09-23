/**
 * The thinning editor's draft, as rules rather than renders
 * (thinning-plan.md 7, thinning-design-brief.md 4 to 6).
 *
 * Split out of the card for the reason ``matrix-lattice.ts`` was: the
 * card imports ``lit`` and cannot load under node, and what the editor
 * does with a click -- which toggles are allowed, what the counts say,
 * what shape goes to the door -- is exactly the part a test should RUN
 * rather than read. This module imports nothing but types.
 *
 * THE DRAFT IS THE WHOLE SHAPE. Per lattice, per mode, the values kept
 * on each axis the mode carries, plus mode-on and lattice-on flags and
 * the On code's keep flag. The door takes the whole desired shape too,
 * never a diff, so ``thinPayload`` is a straight read of the draft.
 *
 * COUNTS ARE CELLS, NOT PRODUCTS. A mode's surviving count is the
 * number of its cells whose every value is kept, by the same rule the
 * door applies (``matrix_thin._cell_survives``): a sparse branch never
 * reports cells it does not have.
 */
import type { MatrixCellCoord, MatrixCells } from "./types.js";

export type ThinAxis = "fans" | "swings" | "temps";
const AXES: ThinAxis[] = ["fans", "swings", "temps"];

/** One mode inside one lattice. */
export interface DraftMode {
    mode: string;
    /** What the mode carries now, per axis, in display order; null for
     * an axis the mode does not have. */
    carried: {
        fans: string[] | null;
        swings: string[] | null;
        temps: number[] | null;
    };
    /** What the person is keeping, per axis the mode carries. */
    kept: {
        fans: Set<string> | null;
        swings: Set<string> | null;
        temps: Set<number> | null;
    };
    on: boolean;
    cells: MatrixCellCoord[];
}

/** One lattice: the main one (axis and key null) or an extra. */
export interface DraftLattice {
    axis: string | null;
    key: string | null;
    on: boolean;
    modes: DraftMode[];
}

export interface ThinDraft {
    lattices: DraftLattice[];
    hasOn: boolean;
    keepOn: boolean;
}

/** What the door takes (``hair/devices/matrix-thin``), less the id. */
export interface ThinShape {
    keep_on: boolean;
    lattices: Array<{
        axis: string | null;
        key: string | null;
        modes: Array<{
            mode: string;
            fans: string[] | null;
            swings: string[] | null;
            temps: number[] | null;
        }>;
    }>;
}

function modesOf(
    cells: MatrixCellCoord[],
    declared: string[],
): string[] {
    const seen: string[] = [];
    for (const c of cells) if (!seen.includes(c.m)) seen.push(c.m);
    const out = declared.filter((m) => seen.includes(m));
    for (const m of seen) if (!out.includes(m)) out.push(m);
    return out;
}

function ordered(declared: string[], observed: Set<string>): string[] {
    const out = declared.filter((v) => observed.has(v));
    for (const v of observed) if (!out.includes(v)) out.push(v);
    return out;
}

function draftMode(
    mode: string,
    cells: MatrixCellCoord[],
    fanOrder: string[],
    swingOrder: string[],
): DraftMode {
    const mine = cells.filter((c) => c.m === mode);
    const fans = new Set<string>();
    const swings = new Set<string>();
    const temps = new Set<number>();
    for (const c of mine) {
        if (c.f !== undefined) fans.add(c.f);
        if (c.s !== undefined) swings.add(c.s);
        if (c.t !== undefined) temps.add(c.t);
    }
    const carried = {
        fans: fans.size ? ordered(fanOrder, fans) : null,
        swings: swings.size ? ordered(swingOrder, swings) : null,
        temps: temps.size ? [...temps].sort((a, b) => a - b) : null,
    };
    return {
        mode,
        carried,
        kept: {
            fans: carried.fans ? new Set(carried.fans) : null,
            swings: carried.swings ? new Set(carried.swings) : null,
            temps: carried.temps ? new Set(carried.temps) : null,
        },
        on: true,
        cells: mine,
    };
}

/** A fresh draft: everything kept, which is what pressing the pencil
 * shows ("Everything green is in the wig now"). */
export function startDraft(mc: MatrixCells): ThinDraft {
    const lattice = (
        axis: string | null,
        key: string | null,
        cells: MatrixCellCoord[],
        modes: string[],
        fanOrder: string[],
        swingOrder: string[],
    ): DraftLattice => ({
        axis,
        key,
        on: true,
        modes: modesOf(cells, modes).map((m) =>
            draftMode(m, cells, fanOrder, swingOrder),
        ),
    });
    return {
        lattices: [
            lattice(null, null, mc.cells, mc.modes, mc.fan_modes,
                mc.swing_modes),
            ...(mc.lattices ?? []).map((l) =>
                lattice(l.axis, l.key, l.cells, l.modes, l.fan_modes,
                    l.swing_modes),
            ),
        ],
        hasOn: mc.has_on,
        keepOn: mc.has_on,
    };
}

/** How many axes a mode has: the depth tag ("3 axes", "single code"). */
export function depthOf(m: DraftMode): number {
    return AXES.filter((a) => m.carried[a] !== null).length;
}

function survives(c: MatrixCellCoord, m: DraftMode): boolean {
    // A cell with no value on an axis the mode otherwise carries is not
    // addressable by that axis, so that axis passes it: the door's rule.
    if (m.kept.fans && c.f !== undefined && !m.kept.fans.has(c.f)) {
        return false;
    }
    if (m.kept.swings && c.s !== undefined && !m.kept.swings.has(c.s)) {
        return false;
    }
    if (m.kept.temps && c.t !== undefined && !m.kept.temps.has(c.t)) {
        return false;
    }
    return true;
}

/** Cells this mode keeps under the draft (zero when it or its lattice
 * is off). */
export function modeKept(l: DraftLattice, m: DraftMode): number {
    if (!l.on || !m.on) return 0;
    return m.cells.filter((c) => survives(c, m)).length;
}

export function latticeTotal(l: DraftLattice): number {
    return l.modes.reduce((n, m) => n + m.cells.length, 0);
}

export function latticeKept(l: DraftLattice): number {
    return l.modes.reduce((n, m) => n + modeKept(l, m), 0);
}

export interface ThinTotals {
    total: number;
    kept: number;
    removed: number;
    /** Modes touched inside lattices that stay, named for the count
     * line: a bare mode for the main lattice, "(key) mode" for an
     * extra, the card's own naming ruling. */
    modes: string[];
    /** Extras removed whole, by their own word. */
    lattices: string[];
    onRemoved: boolean;
}

export function totals(d: ThinDraft): ThinTotals {
    let total = 0;
    let kept = 0;
    const modes: string[] = [];
    const lattices: string[] = [];
    for (const l of d.lattices) {
        total += latticeTotal(l);
        kept += latticeKept(l);
        if (!l.on) {
            lattices.push(`(${l.key})`);
            continue;
        }
        for (const m of l.modes) {
            if (modeKept(l, m) < m.cells.length) {
                modes.push(l.key === null ? m.mode : `(${l.key}) ${m.mode}`);
            }
        }
    }
    return {
        total,
        kept,
        removed: total - kept,
        modes,
        lattices,
        onRemoved: d.hasOn && !d.keepOn,
    };
}

/** Does the draft remove anything at all? The save button's gate; the
 * door refuses the same case as "nothing to remove". */
export function removesAnything(d: ThinDraft): boolean {
    const t = totals(d);
    return t.removed > 0 || t.onRemoved;
}

/** Flip one value. The last value on an axis cannot go: at least one
 * value survives on any axis of a mode being kept (brief 5). Returns
 * whether anything changed. */
export function toggleValue(
    d: ThinDraft,
    li: number,
    mode: string,
    axis: ThinAxis,
    value: string | number,
): boolean {
    const m = d.lattices[li]?.modes.find((x) => x.mode === mode);
    const set = m?.kept[axis] as Set<string | number> | null | undefined;
    if (!m || !set) return false;
    if (set.has(value)) {
        if (set.size <= 1) return false;
        set.delete(value);
    } else {
        const carried = m.carried[axis] as Array<string | number> | null;
        if (!carried || !carried.includes(value)) return false;
        set.add(value);
    }
    return true;
}

/** Flip one mode. The last mode kept in a lattice cannot go: the main
 * lattice must keep one (a matrix with no main lattice is not a
 * matrix), and an extra with none is removed with its own chip. */
export function toggleMode(d: ThinDraft, li: number, mode: string): boolean {
    const l = d.lattices[li];
    const m = l?.modes.find((x) => x.mode === mode);
    if (!l || !m) return false;
    if (m.on && l.modes.filter((x) => x.on).length <= 1) return false;
    m.on = !m.on;
    return true;
}

/** Flip a whole extras lattice. The main lattice has no chip and
 * cannot go. */
export function toggleLattice(d: ThinDraft, li: number): boolean {
    if (li === 0 || !d.lattices[li]) return false;
    d.lattices[li].on = !d.lattices[li].on;
    return true;
}

/** Flip the On code's keep flag; a matrix without one has nothing to
 * flip. Off has no toggle anywhere in this module, on purpose. */
export function toggleOn(d: ThinDraft): boolean {
    if (!d.hasOn) return false;
    d.keepOn = !d.keepOn;
    return true;
}

/** The whole desired shape, for the door. Lattices and modes that are
 * off are simply absent, which is how the door reads "removed". */
export function thinPayload(d: ThinDraft): ThinShape {
    return {
        keep_on: d.hasOn ? d.keepOn : true,
        lattices: d.lattices
            .filter((l) => l.on)
            .map((l) => ({
                axis: l.axis,
                key: l.key,
                modes: l.modes
                    .filter((m) => m.on)
                    .map((m) => ({
                        mode: m.mode,
                        fans: m.carried.fans
                            ? m.carried.fans.filter((v) => m.kept.fans!.has(v))
                            : null,
                        swings: m.carried.swings
                            ? m.carried.swings.filter((v) =>
                                  m.kept.swings!.has(v),
                              )
                            : null,
                        temps: m.carried.temps
                            ? m.carried.temps.filter((v) =>
                                  m.kept.temps!.has(v),
                              )
                            : null,
                    })),
            })),
    };
}

/** Which lines are open. Keys: ``"g:<li>"`` for a lattice group and
 * ``"m:<li>:<mode>"`` for a mode line. */
export type OpenState = Record<string, boolean>;

/** The default on pencil (RULED): Main controls open, every mode inside
 * it closed, every extras lattice closed. */
export function defaultOpen(d: ThinDraft): OpenState {
    const open: OpenState = {};
    d.lattices.forEach((l, li) => {
        open[`g:${li}`] = li === 0;
        for (const m of l.modes) open[`m:${li}:${m.mode}`] = false;
    });
    return open;
}

/** The receipt a save leaves on the device page (owner bench
 * 2026-09-22, item 2).
 *
 * ONE LINE, TWO SENTENCES: what the trim cost, then the existing
 * write-through sentence. Composed here rather than in the card so a
 * test can run it against the shipped strings, and so the page that
 * flashes it does not have to know the grammar.
 *
 * ``trimmed`` comes from the device payload the door answers with,
 * which is the same pair the card's summary line reads, so the receipt
 * and the line can never disagree. Absent (an old payload, a door that
 * answered without one) the receipt is the write-through sentence
 * alone rather than a half-built one.
 */
export function thinReceipt(
    trimmed: { from: number; to: number } | null | undefined,
    wig: { written?: boolean; reason?: string } | null | undefined,
    t: (key: string, subs?: Record<string, string>) => string,
): string {
    const parts: string[] = [];
    if (trimmed) {
        parts.push(t("devices.thin_receipt", {
            from: String(trimmed.from),
            to: String(trimmed.to),
        }));
    }
    if (wig?.written) {
        parts.push(t("tangles.updated"));
    } else {
        const reason = wig?.reason ?? "";
        parts.push(
            reason === "not-adopted"
                ? t("devices.thin_wig_not_adopted")
                : reason === "source_missing"
                  ? t("devices.thin_wig_source_missing")
                  : t("devices.thin_wig_not_written"),
        );
    }
    return parts.join(" ");
}
