/**
 * A Device's state source: the rules the settings dialog follows.
 *
 * A source is either a power sensor in watts, classified against two
 * thresholds, or an on/off entity read by its state (power_monitor.py
 * ON_OFF_DOMAINS: on and home are on, off and not_home are off). This
 * module decides which entities the picker offers, in which group, how
 * long the settle time may be, and what a save sends; the dialog only
 * renders it. It is plain functions
 * over the hass shapes so a node test can run it.
 */

/** Mirrors models.py ON_OFF_DOMAINS; a test checks the two match. */
export const ON_OFF_DOMAINS: readonly string[] = [
    "binary_sensor",
    "switch",
    "input_boolean",
    "device_tracker",
];

/** Mirror models.py MAX_POWER_SETTLE_S and MAX_ON_OFF_SETTLE_S; a test
 * checks they match. The backend is the one that enforces them. */
export const MAX_POWER_SETTLE_S = 120;
export const MAX_ON_OFF_SETTLE_S = 600;

/** What the settle field is set to when a device tracker is picked: a
 * presence or network tracker typically takes minutes to notice a
 * device switched off. The field stays editable. */
export const TRACKER_SETTLE_PRESET_S = 300;

export interface SourceStateShape {
    state?: string;
    attributes: {
        friendly_name?: string;
        device_class?: string;
        unit_of_measurement?: string;
    };
}

export interface SourceCandidate {
    entityId: string;
    name: string;
}

export interface SourceGroups {
    power: SourceCandidate[];
    onOff: SourceCandidate[];
}

export function isOnOffEntity(entityId: string | null | undefined): boolean {
    if (!entityId) return false;
    const dot = entityId.indexOf(".");
    if (dot <= 0) return false;
    return ON_OFF_DOMAINS.includes(entityId.slice(0, dot));
}

/** The longest settle time a Device with this source accepts. */
export function settleCapFor(sensorId: string | null | undefined): number {
    return isOnOffEntity(sensorId) ? MAX_ON_OFF_SETTLE_S : MAX_POWER_SETTLE_S;
}

/**
 * The settle field after a new source is picked, from what it holds.
 * A device tracker presets TRACKER_SETTLE_PRESET_S. Any other source
 * keeps the field, brought down to that source's cap if it is over it,
 * so the field never shows a value the save would not send.
 */
export function settleOnPick(sensorId: string, current: string): string {
    if (sensorId.startsWith("device_tracker.")) {
        return String(TRACKER_SETTLE_PRESET_S);
    }
    const value = parseFloat(current);
    const cap = settleCapFor(sensorId);
    if (!Number.isNaN(value) && value > cap) return String(cap);
    return current;
}

function looksLikePower(entityId: string, st: SourceStateShape): boolean {
    if (!entityId.startsWith("sensor.")) return false;
    const unit = st.attributes.unit_of_measurement;
    return (
        st.attributes.device_class === "power" || unit === "W" || unit === "kW"
    );
}

/**
 * The picker's two groups, each sorted by name.
 *
 * Power sensors are the `sensor.` entities that look like power
 * (device_class power, or a W/kW unit). On/off entities are every entity
 * in the four domains, except HAIR's own (registry platform "hair"):
 * their state is what HAIR assumed, so as a source they would only
 * confirm themselves. The saved source always stays selectable, in the
 * group its domain belongs to, so reopening the dialog never drops it.
 */
export function stateSourceCandidates(
    states: Record<string, SourceStateShape>,
    entities: Record<string, { platform?: string } | undefined>,
    current: string | null,
): SourceGroups {
    const power: SourceCandidate[] = [];
    const onOff: SourceCandidate[] = [];
    for (const [entityId, st] of Object.entries(states)) {
        const name = st.attributes.friendly_name ?? entityId;
        if (looksLikePower(entityId, st)) {
            power.push({ entityId, name });
        } else if (
            isOnOffEntity(entityId) &&
            entities[entityId]?.platform !== "hair"
        ) {
            onOff.push({ entityId, name });
        }
    }
    if (
        current &&
        !power.some((c) => c.entityId === current) &&
        !onOff.some((c) => c.entityId === current)
    ) {
        const entry = {
            entityId: current,
            name: states[current]?.attributes.friendly_name ?? current,
        };
        (isOnOffEntity(current) ? onOff : power).push(entry);
    }
    const byName = (a: SourceCandidate, b: SourceCandidate) =>
        a.name.localeCompare(b.name);
    power.sort(byName);
    onOff.sort(byName);
    return { power, onOff };
}

/** The four power fields a save sends for the chosen source. */
export function stateSourcePatch(
    sensorId: string | null,
    offBelow: string,
    onAbove: string,
    settle: number | null,
): {
    power_sensor_entity_id: string | null;
    power_off_below_w: number | null;
    power_on_above_w: number | null;
    power_settle_s: number | null;
} {
    if (!sensorId) {
        return {
            power_sensor_entity_id: null,
            power_off_below_w: null,
            power_on_above_w: null,
            power_settle_s: null,
        };
    }
    const onOff = isOnOffEntity(sensorId);
    return {
        power_sensor_entity_id: sensorId,
        power_off_below_w: onOff ? null : parseFloat(offBelow),
        power_on_above_w: onOff ? null : parseFloat(onAbove),
        power_settle_s: settle,
    };
}
