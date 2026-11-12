/**
 * The Candy Drawer's chip glyphs, as plain data.
 *
 * The console is plain DOM that also renders in a pop-out (a second
 * document), so its glyphs cannot be Lit templates: each is a viewBox
 * and a few SVG parts, built by the console with the target document's
 * own createElementNS.
 *
 * IR and RF are the panel's own filter glyphs (ir-proto-glyph.ts: the
 * source dot and its signal lines); a test pins the geometry to that
 * file. Known, Unknown and Static are the owner's pick (2026-11-12),
 * one constant each.
 */

export interface CandyGlyphPart {
    tag: "path" | "circle";
    attrs: Record<string, string>;
    /** Filled (the source dot) rather than stroked. */
    fill?: boolean;
}

export interface CandyGlyph {
    viewBox: string;
    parts: CandyGlyphPart[];
}

const SOURCE: CandyGlyphPart = { tag: "circle", attrs: { cx: "5", cy: "12", r: "2.5" }, fill: true };

/** Infrared: the source dot and three straight lines. */
export const CANDY_GLYPH_IR: CandyGlyph = {
    viewBox: "0 0 24 24",
    parts: [SOURCE, { tag: "path", attrs: { d: "M9.5 8h8.5M9.5 12h11.5M9.5 16h8.5" } }],
};

/** Radio: the source dot and three arcs. */
export const CANDY_GLYPH_RF: CandyGlyph = {
    viewBox: "0 0 24 24",
    parts: [
        SOURCE,
        {
            tag: "path",
            attrs: { d: "M9 9A4.24 4.24 0 0 1 9 15M12 6A8.49 8.49 0 0 1 12 18M15 3A12.73 12.73 0 0 1 15 21" },
        },
    ],
};

/** Known: a tag. */
export const CANDY_GLYPH_KNOWN: CandyGlyph = {
    viewBox: "0 0 24 24",
    parts: [
        { tag: "path", attrs: { d: "M3.5 3.5h8l9 9-8 8-9-9z" } },
        { tag: "circle", attrs: { cx: "8", cy: "8", r: "1.5" }, fill: true },
    ],
};

/** Unknown: a question mark in a circle. */
export const CANDY_GLYPH_UNKNOWN: CandyGlyph = {
    viewBox: "0 0 24 24",
    parts: [
        { tag: "circle", attrs: { cx: "12", cy: "12", r: "9" } },
        { tag: "path", attrs: { d: "M9.6 9.4a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.8" } },
        { tag: "circle", attrs: { cx: "12", cy: "17", r: "1" }, fill: true },
    ],
};

/** Static: a waveform. */
export const CANDY_GLYPH_STATIC: CandyGlyph = {
    viewBox: "0 0 24 24",
    parts: [{ tag: "path", attrs: { d: "M2 12h3l2.5-6 3 12 3-9 2.5 6 2-3H22" } }],
};
