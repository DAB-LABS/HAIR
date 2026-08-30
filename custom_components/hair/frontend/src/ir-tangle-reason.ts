/**
 * Why this row is on the list, in one sentence (P5).
 *
 * A row used to introduce itself by name alone -- "Heat, Fan High,
 * 25" -- and left the person to guess what was wrong with it. The comb
 * already knows: every row carries the check classes that flagged it,
 * worst first. This turns the leading one into a sentence.
 *
 * It lives in its own module rather than in ir-tangle-copy because
 * that module is deliberately outside the locale system (its own
 * header says so: it formats live values read off a device, not fixed
 * UI strings). This is fixed UI copy, and it draws the value
 * formatting it needs from over there. Section imports the flows, so
 * the flows cannot import section, which is the other reason this is
 * not a method on the section element.
 *
 * SEPARATOR. The caller joins it to the row name on a middle dot, and
 * never on a dash: a dash between a name and a sentence reads as an
 * em-dash aside, and half the locales here do not punctuate that way
 * at all.
 */
import { t } from "./localize.js";
import { fieldWords } from "./ir-tangle-copy.js";
import type { MatrixUnit } from "./temperature.js";
import type { TangleRow } from "./types.js";

const FIELD_MISMATCH = "field-mismatch";

/** The thirteen check classes the comb can raise, and the only keys
 * this will ask the dictionary for.
 *
 * Explicit rather than derived, because `t()` answers an unknown key
 * with the key itself: a class this build has no sentence for has to
 * produce NO reason line, not the literal text
 * "tangles.reason.something-new" in front of a user. A fourteenth
 * class added to wig_comb.py lands here at the same time as its
 * sentence, or it says nothing at all. */
const KNOWN: ReadonlySet<string> = new Set([
    "malformed",
    "frame-disagreement",
    FIELD_MISMATCH,
    "frame-integrity",
    "stray-burst",
    "frame-shape",
    "duplicated-neighbour",
    "missing-cell",
    "stray-cell",
    "coordinate-collision",
    "duplicate-labels",
    "bypass-with-dittos",
    "ramp-dittos",
]);

/** The map field a field-mismatch finding is about. The comb writes it
 * as a locale key so the diagnosis renders in the reader's language;
 * the field name is the tail of it, exactly as _mismatched_fields
 * reads it on the backend. */
function fieldOf(params: Record<string, unknown>): string {
    const raw = String(params.field ?? "");
    return raw.slice(raw.lastIndexOf(".") + 1);
}

/**
 * One sentence for this row's leading finding, or null when there is
 * nothing this build can say.
 *
 * FIELD-MISMATCH IS THE ONE THAT INTERPOLATES, and it says both
 * values: what the state claims and what the bytes actually send. The
 * listing hands those over as LABELS -- the map named them on the way
 * out rather than leaving every surface to invert an encoding -- so
 * the only work left here is the panel's unit, through the same
 * displayTemp the row name and the matrix header already agree on. A
 * wig whose protocol no field map covers reaches the fallback
 * sentence instead of a half-filled one.
 */
export function reasonLine(
    row: TangleRow,
    nativeUnit: MatrixUnit = "C",
    displayUnit: MatrixUnit = nativeUnit,
): string | null {
    const check = row.classes[0];
    if (!check || !KNOWN.has(check)) return null;
    if (check !== FIELD_MISMATCH) return t(`tangles.reason.${check}`);

    const finding = row.findings.find((f) => f.check === FIELD_MISMATCH);
    const params = (finding?.params ?? {}) as Record<string, unknown>;
    const field = fieldOf(params);
    const claimed = fieldWords(
        field, params.claimed, nativeUnit, displayUnit);
    const read = fieldWords(
        field, params.reads_as, nativeUnit, displayUnit);
    if (claimed === null || read === null) {
        return t("tangles.reason.field-mismatch_plain");
    }
    return t("tangles.reason.field-mismatch", { claimed, read });
}
