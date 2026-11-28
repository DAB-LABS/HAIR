/**
 * The Plucker's ghosts: what could be plucked and isn't yet.
 *
 * The Plucker tab shows its plucked remotes first and, under them,
 * a ghost for everything it could still pluck. There is no Add Blaster
 * step any more. This
 * module turns the two lists the server already sends into that ghost
 * list, in the order below, and nothing else. It is pure and imports
 * only types, so a test can run it under node without a browser.
 *
 * THREE KINDS:
 *   - store: one sub-device of a learned-code store that has no
 *     plucked remote yet. Clicking it plucks that sub-device.
 *   - tweezer: one per blaster that replays codes by name
 *     (hair/pluck/list-vendors lists only those). It never goes away:
 *     opened, it takes an appliance and a command, and its first code
 *     makes a remote, after which a fresh tweezer ghost is there for
 *     the next appliance.
 *   - disabled: what could never pluck to anything, with its reason. A
 *     store that won't parse is ONE disabled ghost (its sub-devices
 *     can't be read); an empty or radio-only sub-device is one each.
 *
 * ORDER: store ghosts first, by source, then the
 * tweezer ghosts, then the disabled ones. Within a source the server's
 * order is kept (file order), so nothing jumps around between loads.
 *
 * A sub-device that has a plucked remote has no ghost. The server
 * finds that remote by its (integration, store, sub-device) key, never
 * by label, so a renamed remote is still matched, and deleting the
 * remote brings its ghost back on the next load.
 */
import type {
    LearnedStore,
    LearnedStoreImport,
    PluckSource,
    PluckVendor,
} from "./types.js";

export type GhostReason = "unreadable" | "empty" | "radio_only";

export interface PluckGhost {
    /** Stable across loads; the render key and the busy/error key. */
    key: string;
    kind: "store" | "tweezer" | "disabled";
    /** What the remote will be called (stores: the server's label). */
    name: string;
    /** The source's brand name, shown small; never translated. */
    source: string;
    integration: string;
    /** store: the command count to show. */
    codes?: number;
    /** store and disabled-store ghosts. */
    storeId?: string;
    /** store: the sub-device to pluck. Absent on a server that does not
     *  list sub-devices yet, in which case the whole store is plucked. */
    subdevice?: string;
    /** tweezer: the blaster that replays. */
    entityId?: string;
    blasterName?: string;
    /** The vendor's own wording for the appliance field, from its
     *  registry entry; shown as the field's tooltip. */
    applianceLabel?: string;
    applianceHelp?: string;
    /** disabled: why. */
    reason?: GhostReason;
}

/** Source order for the store ghosts; anything unknown sorts after. */
const SOURCE_ORDER = ["broadlink", "tuya_local", "openirblaster"];

function sourceRank(integration: string): number {
    const i = SOURCE_ORDER.indexOf(integration);
    return i === -1 ? SOURCE_ORDER.length : i;
}

function byRank<T extends { integration: string }>(list: T[]): T[] {
    // Array.prototype.sort is stable, so the server's order holds
    // inside each source.
    return [...list].sort(
        (a, b) => sourceRank(a.integration) - sourceRank(b.integration),
    );
}

/** The ghosts, in the ruled order. */
export function buildGhosts(
    stores: LearnedStore[],
    vendors: PluckVendor[],
    sources: PluckSource[] = [],
): PluckGhost[] {
    const names: Record<string, string> = {};
    for (const s of sources) names[s.integration] = s.name;
    for (const v of vendors) names[v.integration] ??= v.name;
    const brand = (integration: string): string =>
        names[integration] ?? integration;

    const live: PluckGhost[] = [];
    const dead: PluckGhost[] = [];

    for (const store of byRank(stores)) {
        const source = brand(store.integration);
        const base = { integration: store.integration, source, storeId: store.store_id };
        if (store.error) {
            dead.push({
                ...base,
                key: `broken:${store.store_id}`,
                kind: "disabled",
                name: store.friendly_name,
                reason: "unreadable",
            });
            continue;
        }
        const remotes = store.remotes;
        if (remotes === undefined) {
            // An older server: no sub-device list, so the store is one
            // ghost and a click plucks it whole, as the dialog did.
            if (store.codes > 0) {
                live.push({
                    ...base,
                    key: `store:${store.store_id}`,
                    kind: "store",
                    name: store.friendly_name,
                    codes: store.codes,
                });
            } else {
                dead.push({
                    ...base,
                    key: `empty:${store.store_id}`,
                    kind: "disabled",
                    name: store.friendly_name,
                    reason: "empty",
                });
            }
            continue;
        }
        if (remotes.length === 0) {
            dead.push({
                ...base,
                key: `empty:${store.store_id}`,
                kind: "disabled",
                name: store.friendly_name,
                reason: "empty",
            });
            continue;
        }
        for (const r of remotes) {
            if (r.device_id) continue; // plucked: it's in the list above
            const key = `${store.store_id}:${r.subdevice}`;
            if (r.pluckable) {
                live.push({
                    ...base,
                    key: `store:${key}`,
                    kind: "store",
                    name: r.label,
                    codes: r.codes,
                    subdevice: r.subdevice,
                });
            } else {
                dead.push({
                    ...base,
                    key: `off:${key}`,
                    kind: "disabled",
                    name: r.label,
                    subdevice: r.subdevice,
                    reason: r.reason === "radio_only" ? "radio_only" : "empty",
                });
            }
        }
    }

    const tweezers: PluckGhost[] = [];
    for (const v of byRank(vendors)) {
        for (const b of v.blasters) {
            tweezers.push({
                key: `tweezer:${b.entity_id}`,
                kind: "tweezer",
                name: b.name,
                source: brand(v.integration),
                integration: v.integration,
                entityId: b.entity_id,
                blasterName: b.name,
                applianceLabel: v.appliance_label ?? "",
                applianceHelp: v.appliance_help ?? "",
            });
        }
    }

    return [...live, ...tweezers, ...dead];
}

/** The name a tweezer pluck gives its new remote, the one the old
 *  replay form suggested: "<blaster>: <appliance>". */
export function tweezerRemoteName(blasterName: string, appliance: string): string {
    const a = appliance.trim();
    return (a ? `${blasterName}: ${a}` : blasterName).trim();
}

/** The plucked order with these ids moved to the top, in the order
 *  given, and everything else after them as it was. New remotes land
 *  at the top. */
export function idsToTop(current: string[], fresh: string[]): string[] {
    const top = fresh.filter((id, i) => fresh.indexOf(id) === i);
    const set = new Set(top);
    return [...top, ...current.filter((id) => !set.has(id))];
}

type T = (key: string, subs?: Record<string, string | number>) => string;
type TP = (key: string, count: number, subs?: Record<string, string | number>) => string;

/**
 * The landing sentence after a store pluck (moved here from the
 * retired Add Blaster dialog, unchanged). Every zero-count clause is
 * omitted, and when every signal was already in the catalog the
 * sentence says only that, since repeating the wash numbers for an
 * import that changed nothing would read as though something happened.
 */
export function landingSentence(s: LearnedStoreImport, t: T, tp: TP): string {
    const head = t("pluckstore.landing.head", {
        remotes: tp("pluckstore.n_remotes", s.remotes),
        signals: tp("pluckstore.n_signals", s.signals),
    });
    const parts = [head];
    if (s.signals > 0 && s.already_present === s.signals) {
        parts.push(tp("pluckstore.landing.already", s.already_present));
        return parts.join(" ");
    }
    // Radio first after the head: "2 of them radio." reads against the
    // signal count, which includes them.
    const rfIn = s.rf_imported ?? 0;
    const rfRolling = s.rf_rolling ?? 0;
    if (rfIn > 0) parts.push(tp("pluckstore.landing.rf_imported", rfIn));
    if (rfRolling > 0) parts.push(tp("pluckstore.landing.rf_rolling", rfRolling));
    if (s.washed > 0) parts.push(tp("pluckstore.landing.washed", s.washed));
    if (s.kept_raw > 0) parts.push(tp("pluckstore.landing.kept_raw", s.kept_raw));
    if (s.toggle_pairs > 0) {
        parts.push(tp("pluckstore.landing.toggle_pairs", s.toggle_pairs));
    }
    if (s.no_timings > 0) parts.push(tp("pluckstore.landing.no_timings", s.no_timings));
    // Radio that didn't read (it used to be every radio code).
    if (s.rf_receipted > 0) parts.push(tp("pluckstore.landing.rf", s.rf_receipted));
    if (s.already_present > 0) {
        parts.push(tp("pluckstore.landing.already", s.already_present));
    }
    return parts.join(" ");
}
