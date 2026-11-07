/**
 * The band a radio carrier reads as (fix round 1, item 8): the same
 * rule as ``rf_band.py``, pinned to the same cases
 * (``tests/fixtures/rf/band_cases.json``). A carrier within
 * RF_BAND_SNAP_HZ of a preset centre reads as that centre; any other is
 * rounded half up to RF_BAND_STEP_HZ. Integer arithmetic only.
 *
 * The panel's band labels come from here, so they never disagree with
 * a radio wig row's identity. An exact carrier (a picker option, a
 * "Sent at" toast) is not a band and keeps ``bandNumber``.
 */

/** The editor's preset bands (rf-in-hair-plan 5.1), in Hz. */
export const RF_BAND_CENTRES_HZ: readonly number[] = [
    303_875_000, 310_000_000, 315_000_000, 318_000_000, 350_000_000,
    390_000_000, 418_000_000, 433_420_000, 433_920_000, 868_350_000,
    915_000_000,
];
export const RF_BAND_SNAP_HZ = 150_000;
export const RF_BAND_STEP_HZ = 100_000;

/** The band a carrier reads as, in Hz. */
export function bandHz(frequencyHz: number): number {
    const hz = Math.trunc(frequencyHz);
    let best: number | null = null;
    for (const centre of RF_BAND_CENTRES_HZ) {
        const off = Math.abs(centre - hz);
        if (off <= RF_BAND_SNAP_HZ && (best === null || off < Math.abs(best - hz))) {
            best = centre;
        }
    }
    if (best !== null) return best;
    return Math.floor((hz + RF_BAND_STEP_HZ / 2) / RF_BAND_STEP_HZ) * RF_BAND_STEP_HZ;
}

/** The band as a wig row's identity writes it: MHz, one decimal. */
export function bandKey(frequencyHz: number): string {
    const tenths = Math.floor((bandHz(frequencyHz) + 50_000) / 100_000);
    return `${Math.floor(tenths / 10)}.${tenths % 10}`;
}

/** The band as the panel shows it: MHz with no trailing zeros
 *  ("433.92", "315", "303.875", "433.6"). */
export function bandLabel(frequencyHz: number): string {
    const hz = bandHz(frequencyHz);
    const whole = Math.floor(hz / 1_000_000);
    const digits = String(hz % 1_000_000).padStart(6, "0").replace(/0+$/, "");
    return digits ? `${whole}.${digits}` : String(whole);
}
