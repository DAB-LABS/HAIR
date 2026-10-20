/**
 * The decisions behind the Sniffer's Listen row and its arrival marks
 * (BroadSniff Listen, 2026-10-17), as plain functions.
 *
 * They live apart from the components so a test can run them under
 * node: when a chip blooms, how much of a window its fill shows, and
 * which one row carries the "last heard" tint are exactly what a
 * source grep cannot see. Nothing here imports Lit or touches the DOM.
 */
import type { BroadSniffReceiverRow } from "./types.js";
import { isEntityOnline } from "./entity-health.js";

/** BroadSniff's own default window, for a remote whose window entity
 *  has no readable state. */
export const DEFAULT_WINDOW_S = 10;

/** A deadline further ahead than the window plus this is a browser
 *  clock that disagrees with the server's; the fill then starts full. */
export const CLOCK_SLACK_MS = 2000;

/** What one chip shows, read from Home Assistant's live states. */
export interface ListenLive {
    on: boolean;
    /** BroadSniff's deadline for the open window, or null when closed. */
    endsAt: string | null;
    /** BroadSniff's codes-captured count, or null when unreadable. */
    codes: number | null;
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

/** Whether the chip can listen at all (ember, 2026-10-19): online only
 *  when HA can reach both the receiver and BroadSniff's switch. Arming
 *  goes through the switch and hearing through the receiver, so either
 *  one unavailable or missing is offline (entity-health.ts's rule). */
export function listenOnline(states: States | undefined, row: BroadSniffReceiverRow): boolean {
    return (
        isEntityOnline(states, row.receiver_entity_id) &&
        isEntityOnline(states, row.switch_entity_id)
    );
}

export function listenLive(states: States | undefined, row: BroadSniffReceiverRow): ListenLive {
    const all = states ?? {};
    const sw = all[row.switch_entity_id];
    const on = sw?.state === "on";
    const endsAt: string | null = on ? (sw?.attributes?.window_ends_at ?? null) : null;
    const raw = row.codes_entity_id ? all[row.codes_entity_id]?.state : undefined;
    const codes =
        raw !== undefined && raw !== "" && !Number.isNaN(Number(raw)) ? Number(raw) : null;
    return { on, endsAt, codes };
}

/** The window length BroadSniff is set to, in ms. */
export function windowMs(states: States | undefined, row: BroadSniffReceiverRow): number {
    const raw = row.window_entity_id ? states?.[row.window_entity_id]?.state : undefined;
    const seconds = Number(raw);
    return (Number.isFinite(seconds) && seconds > 0 ? seconds : DEFAULT_WINDOW_S) * 1000;
}

/** The fill for a deadline seen for the first time: whatever is left
 *  of the window, as a share of the whole window. */
export function planFill(endsAt: string, totalMs: number, nowMs: number): FillPlan {
    let leftMs = Date.parse(endsAt) - nowMs;
    if (!Number.isFinite(leftMs) || leftMs > totalMs + CLOCK_SLACK_MS) {
        leftMs = totalMs;
    }
    leftMs = Math.max(0, Math.min(leftMs, totalMs));
    return { endsAt, start: totalMs > 0 ? leftMs / totalMs : 0, durationMs: leftMs };
}

/** Whether a chip blooms on this change: when it turns on, when its
 *  deadline restarts (``sliding`` mode, on every code), and when the
 *  code count goes up (every mode, which is what makes ``multiple``
 *  bloom while it keeps draining and ``single`` bloom on its one code
 *  as it goes back to gold). First sight is a page load, not an
 *  event, so ``before`` undefined never blooms. */
export function listenBlooms(before: ListenLive | undefined, now: ListenLive): boolean {
    if (before === undefined) return false;
    const opened = now.on && !before.on;
    const restarted =
        now.on && before.on && now.endsAt !== null && now.endsAt !== before.endsAt;
    const heard = now.codes !== null && before.codes !== null && now.codes > before.codes;
    return opened || restarted || heard;
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

/** What a Devices-page hardware card shows for a receiver that hears
 *  only while a capture window is open (round 2):
 *  - ``"chip"``: the Listen chip itself, in its compact form, because
 *    HAIR knows the switch that opens the window (a BroadSniff row);
 *  - ``"static"``: a plain RX-CAPTURE badge, for a windowed receiver
 *    whose switch HAIR does not know (a future one from another
 *    integration);
 *  - ``null``: an ordinary receiver, which keeps RX-NATIVE.
 * Windowed is read from the receiver's own ``capturing`` attribute
 * first (BroadSniff sets it on every receiver; any integration can),
 * and from the BroadSniff row second, which covers a receiver whose
 * state has not arrived yet. ``by`` says which of the two decided. */
export interface RxCaptureMatch {
    kind: "chip" | "static" | null;
    by: "attribute" | "row" | null;
}

export function rxCaptureMatch(
    receiverAttributes: Record<string, unknown> | undefined,
    hasListenRow: boolean,
): RxCaptureMatch {
    const byAttribute = typeof receiverAttributes?.capturing === "boolean";
    if (!byAttribute && !hasListenRow) return { kind: null, by: null };
    return {
        kind: hasListenRow ? "chip" : "static",
        by: byAttribute ? "attribute" : "row",
    };
}
