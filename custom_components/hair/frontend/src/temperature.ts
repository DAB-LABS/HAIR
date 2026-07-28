/**
 * Matrix temperature display conversion (unit ruling 2026-07-29).
 *
 * The rule, restated: machine keys stay file-native forever, live
 * displays convert dynamically to the install's unit, names freeze at
 * mint time in the minter's unit. This module is the display side of
 * that rule -- every panel surface that shows a matrix temperature
 * (tiles, the Set-state line, summary ranges, fitting-row labels)
 * converts through here, and NOTHING that computes (absent-tile
 * walks, cell coordinates, row keys) ever does.
 *
 * displayTemp mirrors wig_climate.display_temp_str byte-for-byte: the
 * device page's current-tile glow compares a client-built name against
 * the backend-minted matrix_cell attribute, so the two converters must
 * never disagree on a single character.
 */

export type MatrixUnit = "C" | "F";

/** The install's unit letter, read dynamically per render off the HA
 * config's unit system (the degree-glyph "C"/"F" strings). Anything
 * that is not clearly Fahrenheit reads as "C" -- the corpus
 * convention and the format default -- matching the backend's
 * unit_letter exactly. */
export function installUnit(hass: any): MatrixUnit {
    const u = hass?.config?.unit_system?.temperature;
    return typeof u === "string" && u.endsWith("F") ? "F" : "C";
}

/** One temperature as display text, converted when the viewer's unit
 * differs from the matrix's native unit. Whole-degree matrices
 * convert to the nearest int (16C -> 61F, 17C -> 63F: the non-uniform
 * spacing is honest, those ARE the nearest degrees); a sub-degree
 * matrix (precision < 1) renders ONE decimal instead so distinct
 * 0.5-step cells never collide after rounding. Native renders keep
 * the file's own text. Math.round agrees with Python's round for
 * every reachable value here: 9/5 and 5/9 of the corpus grids never
 * land on exact .5. */
export function displayTemp(
    temp: number,
    unit: MatrixUnit,
    displayUnit: MatrixUnit,
    precision = 1,
): string {
    if (displayUnit === unit) return String(temp);
    const converted =
        unit === "C" ? (temp * 9) / 5 + 32 : ((temp - 32) * 5) / 9;
    if (precision < 1) return converted.toFixed(1);
    return String(Math.round(converted));
}
