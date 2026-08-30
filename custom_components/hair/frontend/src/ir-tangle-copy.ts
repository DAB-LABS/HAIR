/**
 * Shared copy helpers for the three Tangles flow components
 * (ir-tangle-fix / -listen / -decide). Kept out of the locale system
 * deliberately: these are open-ended values read live off a device's
 * matrix or its own command names, not fixed UI strings -- the same
 * class of live data a command's own name already is (localize.ts's
 * own `tv()` doc-comment: "unknown labels pass through unchanged").
 */
import type { TangleTarget } from "./types.js";
import { displayTemp, type MatrixUnit } from "./temperature.js";

/** Which cell coordinate answers which map field.
 *
 * THE MIRROR of wig_comb.py's FIELD_COORDINATE, and the reason issue
 * 18 existed. A verdict's `reads_as` is keyed by MAP FIELD NAME
 * ("temperature"), because that is what the field map calls it; a
 * target's `coordinates` are keyed by CELL AXIS ("temp"), because that
 * is what the lattice calls it. The witness comparison read one with
 * the other's key, so `asked` came back undefined for every
 * temperature cluster and a perfect capture went to the ladder.
 *
 * One constant, read through one helper, so a fifth field cannot be
 * added on one side only. Kept in step with wig_comb.py by hand, which
 * is what the backend's own aliasing comment says it does for
 * tangles.py.
 */
export const FIELD_COORDINATE: Record<string, string> = {
    temperature: "temp",
    mode: "mode",
    fan_speed: "fan",
    swing: "swing",
};

/** Power is not an axis: it rides as its own coordinate and a cell
 * that does not mention it is on. Same rule tangles.py's pre_read
 * applies. */
export const POWER_FIELD = "power";

/** What this target claims for one map field, or undefined when the
 * field does not reach these coordinates at all. */
export function claimedFor(
    field: string | null | undefined,
    coordinates: Record<string, unknown> | null | undefined,
): unknown {
    if (!field || !coordinates) return undefined;
    if (field === POWER_FIELD) return coordinates[POWER_FIELD] ?? "on";
    const axis = FIELD_COORDINATE[field];
    return axis === undefined ? undefined : coordinates[axis];
}

/** Does a reading say the same thing as a claim?
 *
 * String-normalized on purpose (issue 18): a lattice writes 26 and a
 * reading comes back 26.0, and those are the same temperature. Numbers
 * compare as numbers when both sides are numbers; everything else
 * compares as trimmed text, never case-folded, because mode and fan
 * vocabularies ride verbatim and two labels differing only in case are
 * two labels. */
export function sameReading(reading: unknown, claim: unknown): boolean {
    if (reading === undefined || reading === null) return false;
    if (claim === undefined || claim === null) return false;
    if (reading === claim) return true;
    const a = Number(reading);
    const b = Number(claim);
    if (Number.isFinite(a) && Number.isFinite(b)) return a === b;
    return String(reading).trim() === String(claim).trim();
}

/** One field's value as the ladder should say it.
 *
 * Temperature converts to the panel's unit like every other display
 * surface, so "Heard 79" sits beside a row named 79 instead of the
 * lattice's native "Heard 26" (round three, T5). Every other field is
 * a vocabulary label and rides unchanged. The bare number, no degree
 * glyph: the ladder's sentence supplies the context the row name's
 * "79 degrees F" spells out.
 */
export function fieldWords(
    field: string | null | undefined,
    value: unknown,
    nativeUnit: MatrixUnit = "C",
    displayUnit: MatrixUnit = nativeUnit,
): string | null {
    if (value === undefined || value === null || value === "") return null;
    if (field !== "temperature") return String(value);
    const native = Number(value);
    return Number.isFinite(native)
        ? displayTemp(native, nativeUnit, displayUnit)
        : String(value);
}

function titleCase(raw: string): string {
    return raw
        .split("_")
        .filter(Boolean)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
}

/** A target's own setting in the wig's own words -- "Heat, Fan High,
 * 22" for a matrix cell (design brief v6 section 2's own example), or
 * the signal's own alias for a command target.
 *
 * The alias comes FIRST (round one, issue 2). The backend fills `key`
 * with the human alias and `command_id` with the device command's
 * uuid, and this helper used to prefer the uuid -- so a LISTEN row
 * introduced itself as "a16d8c11-ce67-47fd-a18c-632f6733daf5". The
 * uuid is still the fallback, because it is a real identifier and a
 * row with no alias has to say something.
 *
 * Temperatures render in the panel's unit (round one, F9). The matrix
 * keeps its native numbers forever and every display surface converts
 * per render (unit ruling 2026-07-29); this one converts through the
 * same displayTemp the state-matrix header uses, so a row and the
 * header can never disagree on a degree. Precision is the format
 * default: the tangle listing carries the matrix summary, which has
 * no precision field of its own. */
export function targetWords(
    target: TangleTarget,
    nativeUnit: MatrixUnit = "C",
    displayUnit: MatrixUnit = nativeUnit,
): string {
    if (target.kind === "command") {
        return target.key || target.command_id || target.key;
    }
    const coords = target.coordinates;
    if (!coords) return target.key;
    if ("power" in coords) {
        return coords.power === "on" ? "On" : "Off";
    }
    const parts: string[] = [];
    if (coords.mode) parts.push(titleCase(coords.mode));
    if (coords.fan) parts.push(`Fan ${titleCase(coords.fan)}`);
    if (coords.swing && coords.swing !== "off") {
        parts.push(`Swing ${titleCase(coords.swing)}`);
    }
    if (coords.temp !== undefined && coords.temp !== null && coords.temp !== "") {
        const native = Number(coords.temp);
        const shown = Number.isFinite(native)
            ? displayTemp(native, nativeUnit, displayUnit)
            : String(coords.temp);
        parts.push(`${shown}°${displayUnit}`);
    }
    return parts.length > 0 ? parts.join(", ") : target.key;
}
