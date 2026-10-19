/**
 * An entity named once: the panel's twin of entity_names.py.
 *
 * HA composes an entity's friendly name as device name plus entity
 * name. HAIR's ESPHome configs name the transmitter
 * `${friendly_name} TX`, so on a device called "KinCony AGv3 1" the
 * emitter's friendly name comes out "KinCony AGv3 1 KinCony AGv3 1 TX".
 * The Mirror's labels are built server-side and go through
 * entity_names.py. Everything the panel names from `hass.states`
 * (the device header's Emitters chips, the emitter picker in Add
 * Device, Assign and Promote, the Devices tab's Emitters cards) goes
 * through this file instead, with the same rule word for word.
 *
 * Pure and import-free, so tests/test_entity_names_js.py can run it
 * under node.
 */

/** Drop a leading device name only when the entity's own name repeats
 *  it exactly: "D D TX" -> "D TX", "D D" -> "D". "D TX", "Bora Bora
 *  Lamp" and "Den Denon TX" are left alone. Anything missing or not a
 *  string returns the friendly name as given. */
export function collapseDoubledDeviceName(
    friendlyName: unknown,
    deviceName: unknown,
): unknown {
    if (typeof friendlyName !== "string" || typeof deviceName !== "string") {
        return friendlyName;
    }
    if (!friendlyName || !deviceName) return friendlyName;
    const device = deviceName.trim();
    if (!device) return friendlyName;
    const doubled = `${device} ${device}`;
    if (friendlyName === doubled || friendlyName.startsWith(`${doubled} `)) {
        return friendlyName.slice(device.length + 1);
    }
    return friendlyName;
}

/** The friendly name HA shows for an entity, or its id. This is the
 *  full name, the one a tooltip keeps. */
export function entityFullName(hass: any, entityId: string): string {
    const name = hass?.states?.[entityId]?.attributes?.friendly_name;
    return typeof name === "string" && name ? name : entityId;
}

/** The name to show for an entity, with a doubled device name
 *  collapsed. Reads the entity registry for its device and the device
 *  registry for that device's names: `name_by_user` first, then
 *  `name`, the first that collapses wins, as
 *  entity_names.entity_display_name does. Falls back to the full name
 *  whenever the entity, its device or a name is missing. */
export function entityDisplayName(hass: any, entityId: string): string {
    const full = entityFullName(hass, entityId);
    const deviceId = hass?.entities?.[entityId]?.device_id;
    if (!deviceId) return full;
    const device = hass?.devices?.[deviceId];
    if (!device) return full;
    for (const deviceName of [device.name_by_user, device.name]) {
        const collapsed = collapseDoubledDeviceName(full, deviceName);
        if (collapsed !== full) return collapsed as string;
    }
    return full;
}
