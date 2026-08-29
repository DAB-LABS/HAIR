/**
 * Shared copy helpers for the three Tangles flow components
 * (ir-tangle-fix / -listen / -decide). Kept out of the locale system
 * deliberately: these are open-ended values read live off a device's
 * matrix or its own command names, not fixed UI strings -- the same
 * class of live data a command's own name already is (localize.ts's
 * own `tv()` doc-comment: "unknown labels pass through unchanged").
 */
import type { TangleTarget } from "./types.js";

function titleCase(raw: string): string {
    return raw
        .split("_")
        .filter(Boolean)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
}

/** A target's own setting in the wig's own words -- "Heat, Fan High,
 * 22" for a matrix cell (design brief v6 section 2's own example), or
 * a flat command's id for a command target (no IRCommand lookup is
 * wired into the Tangles section today, so a flat-command row shows
 * its command id/key rather than the friendly template name -- flagged
 * for a follow-up, not silently wrong: it is the target's own real
 * identifier, just not the prettiest one). */
export function targetWords(target: TangleTarget, unit: "C" | "F" = "C"): string {
    if (target.kind === "command") {
        return target.command_id ?? target.key;
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
        parts.push(`${coords.temp}°${unit}`);
    }
    return parts.length > 0 ? parts.join(", ") : target.key;
}
