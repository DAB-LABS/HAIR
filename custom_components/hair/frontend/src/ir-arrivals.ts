/**
 * Codes arriving at HAIR, per receiver (windowed receivers, round 3).
 *
 * A capture device's chip blooms when a code from that receiver reaches
 * HAIR: HAIR's own arrival, not the receiver's code count, so the glow
 * means HAIR heard it. The Sniffer's live feed (``hair_signal_detected``)
 * names the receiver on every press, and this module shares one
 * subscription to it among every chip on the page, the Sniffer's row and
 * the Devices cards alike, however many there are.
 */
import type { HairApi } from "./api.js";
import type { UnknownSignalEvent } from "./types.js";

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

function deliver(hub: Hub, event: UnknownSignalEvent): void {
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
        hub.unsubscribe = api.subscribeUnknownSignals((event) => deliver(hub, event));
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
