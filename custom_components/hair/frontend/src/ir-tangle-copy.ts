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
