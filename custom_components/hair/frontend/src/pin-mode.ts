/**
 * What a pinned remote does with the presses it hears, per pinned
 * device (GH #294; GH #183 for leaving out Power). Pure, so the node
 * tests run the rules the Device Settings dialog runs.
 *
 * - "send": every press is sent to the device, for a device that can't
 *   hear the remote.
 * - "except_power": every press but the power toggle, for a device whose
 *   Power is one button and which hears that button itself. Offered
 *   only on such a device.
 * - "track": nothing is sent; the device's state follows every press,
 *   for a device that hears the remote itself.
 */

export type PinMode = "send" | "except_power" | "track";

/** A pin's stored mode, read from the remote's two lists. Track only
 *  wins, as the server reads it. */
export function pinModeOf(
    remote: { follow_only_device_ids?: string[]; track_only_device_ids?: string[] },
    deviceId: string,
): PinMode {
    if ((remote.track_only_device_ids ?? []).includes(deviceId)) return "track";
    if ((remote.follow_only_device_ids ?? []).includes(deviceId)) return "except_power";
    return "send";
}

/** The choices the menu offers: three on a device whose power goes
 *  round on one button, two on any other. */
export function pinModeChoices(toggles: boolean): PinMode[] {
    return toggles ? ["send", "except_power", "track"] : ["send", "track"];
}

/** The mode the menu shows: "except_power" reads as "send" on a device
 *  that doesn't toggle (unticked in this dialog, say), since leaving out
 *  a Power button it doesn't have changes nothing. */
export function pinModeShown(mode: PinMode, toggles: boolean): PinMode {
    return mode === "except_power" && !toggles ? "send" : mode;
}
