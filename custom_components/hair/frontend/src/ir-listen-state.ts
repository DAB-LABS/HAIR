/**
 * The decisions behind the Listen chips, the editor's Listen and the
 * Sniffer's arrival marks, as plain functions.
 *
 * They live apart from the components so a test can run them under
 * node: when a chip blooms, how its fill drains, which receiver the
 * editor listens on, what the switch picker offers and which one row
 * carries the "last heard" tint are exactly what a source grep cannot
 * see. Nothing here imports Lit or touches the DOM.
 *
 * A capture device is an infrared receiver whose state carries a
 * boolean ``capturing`` (windowed receivers, round 3;
 * docs/windowed-receivers.md). Everything below reads that contract
 * from the receiver entity itself and knows no integration by name.
 */
import type { CaptureReceiverRow, ReceiverInfo } from "./types.js";
import { isEntityOnline } from "./entity-health.js";

/** The longest drain the fill will plan. A deadline further ahead than
 *  this is a browser clock that disagrees with the server's, and the
 *  chip shows no fill rather than one that never moves. */
export const MAX_FILL_MS = 10 * 60 * 1000;

/** What one chip shows, read from Home Assistant's live states. */
export interface ListenLive {
    /** The receiver's ``capturing``: its window is open now. */
    on: boolean;
    /** The receiver's ``window_ends_at`` while open, or null. */
    endsAt: string | null;
}

/** The drain for one open window, fixed when its deadline first shows
 *  so later renders never retime a running animation. */
export interface FillPlan {
    endsAt: string;
    /** How full the chip starts, 0 to 1. */
    start: number;
    durationMs: number;
}

type States = Record<string, { state?: string; attributes?: Record<string, any> } | undefined>;

/** Whether the chip can listen at all (ember, 2026-10-19; any capture
 *  device since windowed receivers, round 3): online only when HA can
 *  reach the receiver and the entity that opens its window. Arming goes
 *  through that entity and hearing through the receiver, so either one
 *  unavailable or missing is offline (entity-health.ts's rule). With no
 *  entity chosen yet the chip waits for a choice instead (chipBlock),
 *  which is setup, not health. */
export function listenOnline(states: States | undefined, row: CaptureReceiverRow): boolean {
    return (
        isEntityOnline(states, row.receiver_entity_id) &&
        (row.switch_entity_id === null || isEntityOnline(states, row.switch_entity_id))
    );
}

export function listenLive(states: States | undefined, row: CaptureReceiverRow): ListenLive {
    const st = states?.[row.receiver_entity_id];
    const on = st?.attributes?.capturing === true;
    const ends = st?.attributes?.window_ends_at;
    return { on, endsAt: on && typeof ends === "string" && ends ? ends : null };
}

/** The fill for a deadline seen for the first time: full, draining to
 *  nothing at the deadline. A new deadline (a ``sliding`` window moved
 *  by a code) plans afresh, so the fill snaps back to full. Null when
 *  the deadline cannot be read or is not believable; the chip is then
 *  on without a fill. */
export function planFill(endsAt: string, nowMs: number): FillPlan | null {
    const leftMs = Date.parse(endsAt) - nowMs;
    if (!Number.isFinite(leftMs) || leftMs > MAX_FILL_MS) return null;
    return { endsAt, start: 1, durationMs: Math.max(0, leftMs) };
}

/** Whether a chip blooms on this change of state: when its window
 *  opens and when its deadline moves. A code arriving from the
 *  receiver blooms it too, through the arrivals feed rather than the
 *  receiver's state. First sight is a page load, not an event, so
 *  ``before`` undefined never blooms. */
export function listenBlooms(before: ListenLive | undefined, now: ListenLive): boolean {
    if (before === undefined) return false;
    const opened = now.on && !before.on;
    const restarted =
        now.on && before.on && now.endsAt !== null && now.endsAt !== before.endsAt;
    return opened || restarted;
}

/** Which receivers say they are capture devices right now: the
 *  ``infrared`` entities whose state carries a boolean ``capturing``.
 *  The panel re-reads its capture rows when this changes, which covers
 *  a receiver whose integration loads after HAIR, one that goes
 *  unavailable, and one that comes back, none of which touch the
 *  entity registry. Ordinary state changes (a window opening) do not
 *  change it. */
export function captureSignature(states: States | undefined): string {
    const ids: string[] = [];
    for (const [entityId, st] of Object.entries(states ?? {})) {
        if (entityId.startsWith("infrared.") && typeof st?.attributes?.capturing === "boolean") {
            ids.push(entityId);
        }
    }
    return ids.sort().join(",");
}

/** Why a chip cannot capture right now, or null when it can. Offline
 *  is health (listenOnline, drawn in ember, both parts disabled); no
 *  switch is setup. On the Devices card the chip is then grey and its
 *  main part opens the switch menu; the Sniffer's chip dims and waits. */
export type ChipBlock = "offline" | "no_switch" | null;

export function chipBlock(row: CaptureReceiverRow, online: boolean): ChipBlock {
    if (!online) return "offline";
    if (!row.switch_entity_id) return "no_switch";
    return null;
}

/** The item with the newest ``last_seen``, or null. Compared as times,
 *  not strings: the server and the live path can spell one instant
 *  differently. A tie keeps the first. */
export function newestSeen<T extends { last_seen: string }>(items: readonly T[]): T | null {
    let best: T | null = null;
    let bestAt = -Infinity;
    for (const item of items) {
        const at = Date.parse(item.last_seen);
        if (Number.isFinite(at) && at > bestAt) {
            best = item;
            bestAt = at;
        }
    }
    return best;
}

/** Where the Sniffer's one "last heard" tint goes. The remote heard
 *  most recently carries it on its header row; when that remote is the open
 *  one, the tint moves to its signal heard most recently instead.
 *  Derived from stored ``last_seen`` alone, so it survives a reload
 *  and moves the moment the next signal lands anywhere. At most one of
 *  the two ids is set. */
export function lastHeardTarget(
    devices: readonly { id: string; last_seen: string }[],
    expandedId: string | null,
    expanded: { id: string; signals: readonly { id: string; last_seen: string }[] } | null,
): { deviceId: string | null; signalId: string | null } {
    const device = newestSeen(devices);
    if (device === null) return { deviceId: null, signalId: null };
    const open = expandedId === device.id && expanded?.id === device.id ? expanded : null;
    if (open === null) return { deviceId: device.id, signalId: null };
    const signal = newestSeen(open.signals);
    return signal === null
        ? { deviceId: device.id, signalId: null }
        : { deviceId: null, signalId: signal.id };
}

/** The bloom key for an arriving signal: the signal's own row when its
 *  remote is open, the remote's header row when it is collapsed. */
export function arrivalBloomKey(
    deviceId: string,
    signalId: string | null | undefined,
    remoteOpen: boolean,
): string {
    return remoteOpen && signalId ? `sig:${signalId}` : `dev:${deviceId}`;
}

/** What a Devices-page hardware card shows for a capture device:
 *  - ``"chip"``: the Listen chip in its compact form, because the
 *    server has a row for it (``hair/receivers/capture``);
 *  - ``"static"``: a plain RX-CAPTURE badge, for a receiver whose state
 *    says ``capturing`` before its row has arrived;
 *  - ``null``: an ordinary receiver, which keeps RX-NATIVE.
 * The row decides first, because it also covers a capture device that
 * is unavailable and so carries no attributes at all. ``by`` says which
 * of the two decided. */
export interface RxCaptureMatch {
    kind: "chip" | "static" | null;
    by: "attribute" | "row" | null;
}

export function rxCaptureMatch(
    receiverAttributes: Record<string, unknown> | undefined,
    hasCaptureRow: boolean,
): RxCaptureMatch {
    const byAttribute = typeof receiverAttributes?.capturing === "boolean";
    if (!byAttribute && !hasCaptureRow) return { kind: null, by: null };
    return {
        kind: hasCaptureRow ? "chip" : "static",
        by: byAttribute ? "attribute" : "row",
    };
}

// ---------------------------------------------------------------------------
// The editor's Listen: which receiver
// ---------------------------------------------------------------------------

/** Where the editor remembers the receiver last listened on, per browser. */
export const LAST_RECEIVER_KEY = "hair.listen.receiver";

/** One receiver the editor's Listen menu offers. */
export interface ListenChoice {
    entityId: string;
    name: string;
    /** A capture device: listening opens its window. */
    capture: boolean;
}

/** The receivers to offer: every native receiver HAIR hears, with the
 *  capture devices marked. An offline one is still listed, with its
 *  health on its dot (the menu draws it from hass.states), so the menu
 *  says what is down rather than hiding it. */
export function listenChoices(
    receivers: readonly ReceiverInfo[],
    captureRows: readonly CaptureReceiverRow[],
): ListenChoice[] {
    const capture = new Set(captureRows.map((row) => row.receiver_entity_id));
    return receivers.map((r) => ({
        entityId: r.entity_id,
        name: r.name,
        capture: capture.has(r.entity_id),
    }));
}

/** The receiver Listen uses: the last one used when it is still offered
 *  and online, otherwise the first online one, otherwise the last one
 *  used or the first offered (so an all-offline house still names one),
 *  or null when none is offered (a house with only ESPHome bridge
 *  receivers keeps the listen that hears everything). */
export function pickReceiver(
    choices: readonly ListenChoice[],
    lastUsed: string | null,
    online: (entityId: string) => boolean = () => true,
): ListenChoice | null {
    const last = choices.find((c) => c.entityId === lastUsed);
    if (last && online(last.entityId)) return last;
    return choices.find((c) => online(c.entityId)) ?? last ?? choices[0] ?? null;
}

// ---------------------------------------------------------------------------
// The capture switch picker
// ---------------------------------------------------------------------------

/** The domains a hand-made choice may come from, as the server allows. */
export const CHOOSABLE_DOMAINS = ["switch", "input_boolean"] as const;

export interface PickerEntity {
    entityId: string;
    name: string;
}

/** The "Choose another..." list: every ``switch`` and ``input_boolean``
 *  in ``hass.states``, matching the query on the friendly name or the
 *  entity id, ignoring case, sorted by name. */
export function pickerEntities(states: States | undefined, query: string): PickerEntity[] {
    const q = query.trim().toLocaleLowerCase();
    const out: PickerEntity[] = [];
    for (const [entityId, st] of Object.entries(states ?? {})) {
        const domain = entityId.split(".", 1)[0];
        if (!(CHOOSABLE_DOMAINS as readonly string[]).includes(domain)) continue;
        const name = String(st?.attributes?.friendly_name ?? entityId);
        if (q && !name.toLocaleLowerCase().includes(q) && !entityId.toLocaleLowerCase().includes(q)) {
            continue;
        }
        out.push({ entityId, name });
    }
    return out.sort((a, b) => a.name.localeCompare(b.name) || a.entityId.localeCompare(b.entityId));
}

/** The switch menu behind the RX-CAPTURE chip's caret (owner ruling,
 *  2026-10-20): every capture device has it, even with one option.
 *  - Declared (``source: "declared"``): that switch alone, checked.
 *    Nothing else on the device is offered, so an RM4 Pro's RF capture
 *    never appears, and there is no "Choose another...".
 *  - Otherwise: the switches on the receiver's device, the current one
 *    checked (the only switch is already picked; with several, none is
 *    until the user picks), then "Choose another...". A current choice
 *    from elsewhere (a helper, a switch on another device) is listed
 *    first so the menu always shows what is in use.
 *  Nothing else: no Remove, no Always listening. */
export interface PickerMenuItem {
    kind: "switch" | "other";
    entityId?: string;
    name?: string;
    current?: boolean;
}

export function pickerMenu(row: CaptureReceiverRow, currentName?: string): PickerMenuItem[] {
    const items: PickerMenuItem[] = [];
    const current = row.switch_entity_id;
    if (current && row.source === "declared") {
        const own = row.device_switches.find((s) => s.entity_id === current);
        return [{ kind: "switch", entityId: current, name: own?.name ?? currentName ?? current, current: true }];
    }
    if (current && !row.device_switches.some((s) => s.entity_id === current)) {
        items.push({ kind: "switch", entityId: current, name: currentName ?? current, current: true });
    }
    for (const s of row.device_switches) {
        items.push({ kind: "switch", entityId: s.entity_id, name: s.name, current: s.entity_id === current });
    }
    items.push({ kind: "other" });
    return items;
}
