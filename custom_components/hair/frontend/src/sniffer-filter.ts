/**
 * The Sniffer's SHOW chips and its carrier column, as plain functions
 * (RF hear round 1), so the node tests run the rules the panel runs.
 */
import { bandNumber } from "./ir-listen-state.js";

/** All, Infrared, Radio, Hidden. */
export type SnifferFilter = "all" | "ir" | "rf" | "hidden";

/** Whether a remote shows under a chip. Hidden shows the hidden
 *  remotes only; the others show what is not hidden, by medium. A
 *  remote with no medium is infrared, as every row before radio was. */
export function snifferShows(
    filter: SnifferFilter,
    d: { dismissed: boolean; medium?: string },
): boolean {
    if (filter === "hidden") return d.dismissed;
    if (d.dismissed) return false;
    if (filter === "ir") return d.medium !== "rf";
    if (filter === "rf") return d.medium === "rf";
    return true;
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
        return row.rf_frequency_hz ? { band: bandNumber(row.rf_frequency_hz) } : null;
    }
    return typeof row.frequency === "number" ? { khz: Math.round(row.frequency / 1000) } : null;
}
