/**
 * Fan speed cycle settings (GH Discussion #201), the pure half.
 *
 * A fan whose one Speed Cycle button steps 1, 2, 3, back to 1 needs
 * the number of speeds before HAIR can set one. These are the rules
 * the device editor's speed-cycle section runs on, kept free of lit so
 * the test harness can run them under node. The backend enforces the
 * same range (models.py FAN_SPEED_STEPS_MIN / FAN_SPEED_STEPS_MAX).
 */
import type { IRDevice } from "./types.js";

export const MIN_SPEED_STEPS = 2;
export const MAX_SPEED_STEPS = 10;

/** A fan with a Speed Cycle command mapped gets the section. */
export function hasSpeedCycle(
    device: Pick<IRDevice, "device_type"> &
        Partial<Pick<IRDevice, "entity_config">>,
): boolean {
    return (
        device.device_type === "fan" &&
        !!device.entity_config?.command_mapping?.speed_cycle
    );
}

/** The number of speeds the field saves as: null for an empty field
 * (no speed control), the integer when it is one in range, and NaN
 * for anything else, which the editor refuses to save. */
export function speedStepsForSave(raw: string): number | null {
    const text = raw.trim();
    if (text === "") return null;
    const value = Number(text);
    if (
        !Number.isInteger(value) ||
        value < MIN_SPEED_STEPS ||
        value > MAX_SPEED_STEPS
    ) {
        return NaN;
    }
    return value;
}
