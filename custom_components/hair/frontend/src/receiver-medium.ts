/**
 * Which medium a receiver hears, and the receivers a trigger may be
 * scoped to (N18, owner's bench on VM998, 2026-11-09).
 *
 * A radio trigger scoped to an infrared receiver never fires: the code
 * arrives on the radio receiver. An Athom's two receivers share one
 * device name, so the picker shows each receiver's medium, and the
 * trigger dialog offers only the trigger's own medium. Imports nothing
 * at runtime, so the rules run under node in the tests.
 */
import type { Medium, ReceiverInfo } from "./types.js";

/** The radio trigger protocol (const.py RF_PROTOCOL). */
export const RF_TRIGGER_PROTOCOL = "RF_RAW";

/** The medium a receiver hears: what the server says, else its domain. */
export function receiverMedium(r: Pick<ReceiverInfo, "entity_id" | "medium">): Medium {
    if (r.medium === "ir" || r.medium === "rf") return r.medium;
    return r.entity_id.startsWith("radio_frequency.") ? "rf" : "ir";
}

/** The medium of a receiver known only by its entity id, or null when
 *  its domain says neither. */
export function receiverIdMedium(entityId: string): Medium | null {
    if (entityId.startsWith("infrared.")) return "ir";
    if (entityId.startsWith("radio_frequency.")) return "rf";
    return null;
}

/** The receivers a picker lists: all of them, or one medium's. */
export function receiversOf<T extends Pick<ReceiverInfo, "entity_id" | "medium">>(
    receivers: readonly T[],
    medium: Medium | null,
): T[] {
    return medium ? receivers.filter((r) => receiverMedium(r) === medium) : [...receivers];
}

/** A trigger's medium: the stored one when editing, else what its
 *  protocol says; null when a create door has no protocol yet (the
 *  server works it out, and refuses a mismatch). */
export function triggerMedium(
    trigger: { medium?: Medium | null; protocol?: string | null } | null,
    protocol: string | null,
): Medium | null {
    if (trigger) {
        if (trigger.medium === "rf" || trigger.protocol === RF_TRIGGER_PROTOCOL) return "rf";
        return "ir";
    }
    if (!protocol) return null;
    return protocol === RF_TRIGGER_PROTOCOL ? "rf" : "ir";
}

/** A stored receiver scope with the other medium's receivers dropped,
 *  so saving it repairs it. A receiver whose domain says neither is
 *  kept. */
export function keepMedium(ids: readonly string[], medium: Medium | null): string[] {
    if (!medium) return [...ids];
    return ids.filter((id) => {
        const m = receiverIdMedium(id);
        return m === null || m === medium;
    });
}
