/**
 * Codes arriving at HAIR, per receiver (windowed receivers, round 3).
 *
 * A receiver's chip or pill blooms when HAIR takes a code from that
 * receiver: a row minted or bumped, or a trigger matched
 * (``hair_receiver_heard``, RF hear fix round 1). Never on a code HAIR
 * drops, so an always-on radio receiver hearing noise three times a
 * second does not flicker. This module shares one subscription among
 * every chip on the page, the Sniffer's row and the Devices cards alike,
 * however many there are.
 */
import type { HairApi } from "./api.js";

type Listener = () => void;

interface Hub {
    listeners: Map<string, Set<Listener>>;
    unsubscribe: Promise<() => Promise<void>> | null;
}

const hubs = new WeakMap<HairApi, Hub>();

function hubFor(api: HairApi): Hub {
    let hub = hubs.get(api);
    if (hub === undefined) {
        hub = { listeners: new Map(), unsubscribe: null };
        hubs.set(api, hub);
    }
    return hub;
}

function deliver(hub: Hub, event: { receiver_entity_id?: string | null }): void {
    const receiver = event.receiver_entity_id;
    if (!receiver) return;
    for (const listener of hub.listeners.get(receiver) ?? []) listener();
}

/** Call ``listener`` whenever a code from ``receiver`` reaches HAIR.
 *  Returns the function that stops it; the shared subscription closes
 *  when its last listener goes. */
export function onArrival(api: HairApi, receiver: string, listener: Listener): () => void {
    const hub = hubFor(api);
    let set = hub.listeners.get(receiver);
    if (set === undefined) {
        set = new Set();
        hub.listeners.set(receiver, set);
    }
    set.add(listener);
    if (hub.unsubscribe === null) {
        hub.unsubscribe = api.subscribeReceiverHeard((event) => deliver(hub, event));
        // A failed subscription leaves the chips without blooms, nothing
        // worse; the next listener tries again.
        hub.unsubscribe.catch(() => {
            hub.unsubscribe = null;
        });
    }
    return () => {
        set!.delete(listener);
        if (set!.size === 0) hub.listeners.delete(receiver);
        if (hub.listeners.size === 0 && hub.unsubscribe !== null) {
            const closing = hub.unsubscribe;
            hub.unsubscribe = null;
            void closing.then((stop) => stop()).catch(() => undefined);
        }
    };
}
