/**
 * Which entities can be an emitter, and what to call them: `infrared.*`
 * emitters and, from the RF send round, `radio_frequency.*`
 * transmitters. A device may hold both kinds; each command goes only to
 * the emitters of its own medium (the send path's rule, rf_send.py).
 *
 * Moved out of ir-emitter-picker.ts so it imports nothing that needs a
 * browser and tests/test_entity_names_js.py can run it under node. The
 * filter is unchanged; what is new is that each option carries two
 * names. The picker
 * re-exports all of it, so existing imports still work. It builds the
 * one emitter list behind the picker (Add Device, Assign, Promote, Test
 * emitter) and the device header's Emitters chips, which is why the
 * doubled-name rule is applied here and nowhere downstream.
 */
import { entityDisplayName, entityFullName } from "./entity-names.js";
import { isEntityOnline } from "./entity-health.js";
import type { Medium } from "./types.js";

export interface EmitterInfo {
    entity_id: string;
    /** What the chip says: the friendly name with a doubled device
     *  name collapsed (entity-names.ts). */
    name: string;
    /** The friendly name as HA composes it, or the entity id. The
     *  tooltip keeps this one. */
    fullName: string;
    /** Online, by the one shared rule (entity-health.ts): HA can reach
     *  it. device_manager.py skips an unavailable emitter at send time,
     *  and every emitter chip shows this on its dot. `unknown` counts
     *  as online: an emitter's state is its last-send timestamp,
     *  unknown until the first send, so a brand-new blaster is
     *  unproven, not down (GH #83). */
    available: boolean;
    /** What it sends: infrared for `infrared.*`, radio for a
     *  `radio_frequency.*` transmitter. */
    medium: Medium;
}

/** The medium an entity sends, by domain, or null when it is neither. */
export function emitterMedium(entityId: string): Medium | null {
    if (entityId.startsWith("infrared.")) return "ir";
    if (entityId.startsWith("radio_frequency.")) return "rf";
    return null;
}

/** Every entity that can be assigned as an emitter, infrared emitters
 *  first, then radio transmitters. An `infrared.*` entity counts unless
 *  it is a known receiver or flagged `hair_observer`; a
 *  `radio_frequency.*` entity counts when its device class is
 *  `transmitter`. Nothing in `excludeIds` counts.
 *  `receiverIds` is the caller's job to supply (this function does no
 *  fetching of its own -- ir-emitter-picker.ts loads its own via
 *  `api.listReceivers()`; ir-device-detail.ts reuses ir-device-list.ts's
 *  already-loaded receivers list instead of a second fetch). */
export function getEmitterOptions(
    hass: any,
    receiverIds: Set<string>,
    excludeEntityIds: string[] = [],
): EmitterInfo[] {
    const states = (hass?.states ?? {}) as Record<
        string,
        {
            entity_id: string;
            state?: string;
            attributes: {
                friendly_name?: string;
                hair_observer?: boolean;
                device_class?: string;
            };
        }
    >;
    const excludeSet = new Set(excludeEntityIds);
    const infrared: EmitterInfo[] = [];
    const radio: EmitterInfo[] = [];
    for (const [entityId, st] of Object.entries(states)) {
        if (excludeSet.has(entityId)) continue;
        const attrs = st.attributes ?? {};
        const medium = emitterMedium(entityId);
        if (medium === "ir") {
            if (receiverIds.has(entityId) || attrs.hair_observer) continue;
        } else if (medium === "rf") {
            if (attrs.device_class !== "transmitter") continue;
        } else {
            continue;
        }
        (medium === "ir" ? infrared : radio).push({
            entity_id: entityId,
            name: entityDisplayName(hass, entityId),
            fullName: entityFullName(hass, entityId),
            available: isEntityOnline(states, entityId),
            medium,
        });
    }
    return [...infrared, ...radio];
}

/** The picker's groups: the options of each medium it shows, infrared
 *  first, a medium with no option left out. `media` null shows every
 *  medium (a new device may take either kind, or both). */
export function emitterGroups(
    options: EmitterInfo[],
    media: Medium[] | null,
): { medium: Medium; items: EmitterInfo[] }[] {
    const shown: Medium[] = (["ir", "rf"] as Medium[]).filter((m) => !media || media.includes(m));
    return shown
        .map((medium) => ({ medium, items: options.filter((o) => o.medium === medium) }))
        .filter((group) => group.items.length > 0);
}
