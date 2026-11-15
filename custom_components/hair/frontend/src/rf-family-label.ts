/**
 * A radio family in the protocol pill (decoder round 2, owner rulings of
 * 2026-11-14 19:06 PT on Kobe's mock).
 *
 * The server reads a radio frame's family (rf_family.py) and sends it as
 * `rf_family` on each radio row: Sniffer and Clipper rows, a device's
 * commands, the trigger list and the wig save plan. This file turns that
 * object into what the pill shows:
 *
 *   - the pill's text, which must fit the 88px protocol column. Every
 *     label fits as sent except "PT2262 or EV1527", which reads
 *     "PT2262/1527" (fit A). A label this table has not seen is
 *     shortened by the same rule, and the pill's own width cap and
 *     ellipsis catch anything still too long, so a new label never
 *     pushes a row out of line;
 *   - the tooltip, the label and the fields only (ruling 2): "EV1527 ·
 *     address 950E4 · data 9". No sentence, so nothing to translate:
 *     the labels and field names are fixed English, like the Candy
 *     Drawer's line;
 *   - the editor's line after the pill, the fields as plain text.
 *
 * The clone names (`aliases`) stay out of all three (ruling 2).
 *
 * Pure and import-free, so tests/test_rf_family_pill_js.py runs it
 * under node.
 */

/** One decoded field, in the server's display order. */
export interface RfFamilyField {
    name: string;
    value: string;
}

/** A radio row's family, as rf_family.py sends it; null when no shown
 *  family fits the frame. */
export interface RfFamily {
    /** The full words: "EV1527", "PT2262 or EV1527", "KeeLoq". */
    label: string;
    /** The shown families' keys joined by "_": "pt2262_ev1527". */
    family: string;
    certainty: "decoded" | "ambiguous";
    unit_us?: number;
    fields: RfFamilyField[];
    /** Clone names. Never shown in the pill (ruling 2). */
    aliases?: string[];
}

/** Pill text for a label too wide for the column, by family key. Every
 *  label a shown family can give today is pinned by the tests. */
export const FAMILY_SHORT: Readonly<Record<string, string>> = {
    pt2262_ev1527: "PT2262/1527",
};

/** What the pill says, or null for no pill. */
export function familyShort(family: RfFamily | null | undefined): string | null {
    if (!family || !family.label) return null;
    const known = FAMILY_SHORT[family.family];
    if (known) return known;
    // A label not in the table: "A or B" reads "A/B". The pill's width
    // cap handles whatever is still too long.
    return family.label.split(" or ").join("/");
}

/** The fields as the editor and the drawer write them:
 *  "address 950E4 data 9". */
export function familyFieldsText(family: RfFamily | null | undefined): string {
    if (!family) return "";
    return (family.fields ?? []).map((f) => `${f.name} ${f.value}`).join(" ");
}

/** The editor's line after the pill: the fields, with the full label
 *  first wherever the pill shortened it, as the mock draws it:
 *  "PT2262 or EV1527 · tri-state 0F10FF001001 code 1C50C3". */
export function familyEditorText(family: RfFamily | null | undefined): string {
    if (!family) return "";
    const fields = familyFieldsText(family);
    if (familyShort(family) === family.label) return fields;
    return fields ? `${family.label} · ${fields}` : family.label;
}

/** The pill's tooltip and accessible name: the label, then each field,
 *  joined by " · ". */
export function familyTitle(family: RfFamily | null | undefined): string {
    if (!family) return "";
    return [family.label, ...(family.fields ?? []).map((f) => `${f.name} ${f.value}`)].join(" · ");
}
