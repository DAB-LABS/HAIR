/**
 * Which `infrared.*` entities can be an emitter, and what to call them.
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
}

/** Every `infrared.*` entity that can be assigned as an emitter: not a
 *  known receiver, not flagged `hair_observer`, not in `excludeIds`.
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
            attributes: { friendly_name?: string; hair_observer?: boolean };
        }
    >;
    const excludeSet = new Set(excludeEntityIds);
    const emitters: EmitterInfo[] = [];
    for (const [entityId, st] of Object.entries(states)) {
        if (
            entityId.startsWith("infrared.") &&
            !excludeSet.has(entityId) &&
            !receiverIds.has(entityId) &&
            !st.attributes.hair_observer
        ) {
            emitters.push({
                entity_id: entityId,
                name: entityDisplayName(hass, entityId),
                fullName: entityFullName(hass, entityId),
                available: isEntityOnline(states, entityId),
            });
        }
    }
    return emitters;
}
