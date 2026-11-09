/**
 * The Sniffer's filter glyphs and its carrier column, as plain
 * functions (RF hear round 1), so the node tests run the rules the
 * panel runs.
 */
import { bandLabel } from "./rf-band.js";

/** The three filter glyphs at the right end of the receiver row (fix
 *  round 1, item 3): each an independent toggle. */
export interface SnifferShow {
    ir: boolean;
    rf: boolean;
    hidden: boolean;
}

/** Infrared on, radio on, hidden off. */
export const SNIFFER_SHOW_DEFAULT: SnifferShow = { ir: true, rf: true, hidden: false };

/** Whether a remote shows: its medium's glyph is lit, and it is not
 *  hidden unless the hidden glyph is lit too. A remote with no medium
 *  is infrared, as every row before radio was. */
export function snifferShows(
    show: SnifferShow,
    d: { dismissed: boolean; medium?: string },
): boolean {
    if (d.dismissed && !show.hidden) return false;
    return d.medium === "rf" ? show.rf : show.ir;
}

/** Whether every remote the server sent is shown, which is when the
 *  remote list can be reordered. */
export function snifferShowsEverything(show: SnifferShow): boolean {
    return show.ir && show.rf && !show.hidden;
}

/** What a row's carrier column says: a radio band in MHz ("433.92"),
 *  an infrared carrier in kHz, or nothing for a radio row heard with no
 *  carrier. */
export function carrierParts(row: {
    medium?: string;
    rf_frequency_hz?: number | null;
    frequency?: number;
}): { band: string } | { khz: number } | null {
    if (row.medium === "rf") {
        return row.rf_frequency_hz ? { band: bandLabel(row.rf_frequency_hz) } : null;
    }
    return typeof row.frequency === "number" ? { khz: Math.round(row.frequency / 1000) } : null;
}

/** A radio command's band ("433.92"), as the Sniffer row says it (N16),
 *  or null for infrared and for a radio command with no carrier. */
export function radioBandOf(row: { medium?: string; rf_frequency_hz?: number | null }): string | null {
    const parts = row.medium === "rf" ? carrierParts(row) : null;
    return parts && "band" in parts ? parts.band : null;
}
