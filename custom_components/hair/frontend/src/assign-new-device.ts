/**
 * The Assign dialog's New Device tab, the rules that do not need a
 * browser (bench, 2026-11-10).
 *
 * A radio row's New Device tab lists radio transmitters only, so its
 * refusal for an empty choice names a radio transmitter; an infrared
 * row's names an IR emitter, as before. The bench read "Select at
 * least one IR emitter" on a radio row whose transmitter chips were
 * online but not chosen.
 *
 * Imports nothing at runtime, so tests run it under node.
 */
import type { Medium } from "./types.js";

/** The locale key that asks for an emitter of the row's medium. */
export function emitterRequiredKey(medium: Medium | null | undefined): string {
    return medium === "rf" ? "assign.transmitter_required" : "promote.emitter_required";
}

/** Why the New Device tab cannot create yet, as a locale key, or null
 *  when it can. Checked in this order, as the tab lays them out. */
export function newDeviceRefusalKey(
    medium: Medium | null | undefined,
    name: string,
    emitterIds: readonly string[],
): string | null {
    if (!name.trim()) return "promote.device_name_required";
    if (emitterIds.length === 0) return emitterRequiredKey(medium);
    return null;
}
