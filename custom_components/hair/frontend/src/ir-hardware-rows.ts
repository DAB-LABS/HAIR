/**
 * The Devices tab's hardware cards, one row per capability (RF hear
 * round 1, frontend; design `homepage-hardware-cards.html`, owner
 * 2026-11-05).
 *
 * A card is one Home Assistant device. Under its header it lists every
 * infrared and radio entity HAIR can use on that device, one row each:
 * a badge that spells the medium and the direction (`IR-TX`, `IR-RX`,
 * `RF-TX`, `RF-RX`), the entity's name, and at the right the one fact
 * HAIR has about it: when HAIR last sent through a transmitter, when it
 * last took a code from a receiver, or that the entity is unavailable.
 * Infrared rows come first, then radio; transmitters before receivers
 * within each. Nothing on the card is a control: every receiver is
 * heard all the time, and a radio receiver's capture window is pressed
 * open on the Sniffer.
 *
 * This replaces the single receiver slot the old merge kept per device,
 * which an RM4 Pro's radio receiver, arriving last, took from its
 * infrared one (the defect the round started with). Here every receiver
 * is its own row.
 *
 * Plain functions over plain inputs, so the panel and the node tests
 * build the same cards.
 */
import type {
    CaptureReceiverRow,
    HardwareFacts,
    Medium,
    ReceiverHardwareInfo,
} from "./types.js";

export type Direction = "tx" | "rx";

/** The one fact a row shows at its right. ``none`` leaves it blank:
 *  HAIR has not used or heard the entity since it started, and cannot
 *  tell that from "never". */
export type RowFact =
    | { kind: "sent"; at: string }
    | { kind: "heard"; at: string }
    | { kind: "unavailable" }
    | { kind: "none" };

export interface CapabilityRow {
    direction: Direction;
    medium: Medium;
    entity_id: string;
    available: boolean;
    /** A radio or infrared receiver whose window is pressed open on the
     *  Sniffer (a capture device). Only the card icon reads it. */
    capture_device: boolean;
    fact: RowFact;
}

export interface HardwareCard {
    /** HA device id, or the first entity's id when it has no device. */
    device_id: string;
    rows: CapabilityRow[];
}

export interface HardwareSections {
    emitters: HardwareCard[];
    receivers: HardwareCard[];
    proxies: HardwareCard[];
}

type States = Record<string, { state?: string; attributes?: Record<string, unknown> } | undefined>;
type Entities = Record<string, { device_id?: string | null } | undefined>;

export interface HardwareInput {
    states: States | undefined;
    entities: Entities | undefined;
    /** ``hair/receivers/hardware``. */
    receivers: ReceiverHardwareInfo[];
    /** ``hair/receivers/capture``: remembered capture devices whose
     *  integration has not loaded still get their row. */
    captureRows: CaptureReceiverRow[];
    facts: HardwareFacts | null;
    /** Receivers HAIR knows but does not list (``hair/receivers``
     *  minus the hardware door: the GH #72 radio proxies on the
     *  infrared platform). Never drawn, and never taken for a
     *  transmitter. */
    hidden?: Set<string>;
}

/** The badge a row wears. */
export function badgeLabel(row: Pick<CapabilityRow, "direction" | "medium">): string {
    return `${row.medium === "rf" ? "RF" : "IR"}-${row.direction === "tx" ? "TX" : "RX"}`;
}

function isAvailable(states: States | undefined, entityId: string): boolean {
    const st = states?.[entityId];
    return st !== undefined && st.state !== "unavailable";
}

function rank(row: CapabilityRow): number {
    return (row.medium === "rf" ? 2 : 0) + (row.direction === "rx" ? 1 : 0);
}

/** The fact for one row. */
export function rowFact(
    direction: Direction,
    entityId: string,
    available: boolean,
    facts: HardwareFacts | null,
): RowFact {
    if (!available) return { kind: "unavailable" };
    const at = direction === "tx" ? facts?.sent?.[entityId] : facts?.heard?.[entityId];
    if (!at) return { kind: "none" };
    return direction === "tx" ? { kind: "sent", at } : { kind: "heard", at };
}

/** Every hardware card, by HA device, rows in order. */
export function buildHardwareCards(input: HardwareInput): HardwareCard[] {
    const { states, entities, facts } = input;
    const rows = new Map<string, { direction: Direction; medium: Medium; capture: boolean }>();
    const receiverIds = new Set<string>();

    for (const hw of input.receivers) {
        // Native receiver entities only: the legacy event bridge left
        // with the 2026.6 floor, and has nothing to draw.
        if (hw.type !== "native") continue;
        const id = hw.receiver_entity_id ?? hw.device_id;
        if (!id) continue;
        const medium: Medium = hw.medium === "rf" || id.startsWith("radio_frequency.") ? "rf" : "ir";
        receiverIds.add(id);
        rows.set(id, {
            direction: "rx",
            medium,
            capture: medium === "rf" ? hw.always_on === false : false,
        });
    }
    for (const row of input.captureRows) {
        if (!row.capture_device) continue;
        receiverIds.add(row.receiver_entity_id);
        rows.set(row.receiver_entity_id, {
            direction: "rx",
            medium: row.medium,
            capture: true,
        });
    }
    for (const [entityId, st] of Object.entries(states ?? {})) {
        if (receiverIds.has(entityId) || input.hidden?.has(entityId)) continue;
        if (entityId.startsWith("infrared.")) {
            if (st?.attributes?.hair_observer) continue;
            if (st?.attributes?.device_class === "receiver") continue;
            rows.set(entityId, { direction: "tx", medium: "ir", capture: false });
        } else if (
            entityId.startsWith("radio_frequency.") &&
            st?.attributes?.device_class === "transmitter"
        ) {
            rows.set(entityId, { direction: "tx", medium: "rf", capture: false });
        }
    }

    const cards = new Map<string, HardwareCard>();
    for (const [entityId, info] of rows) {
        const deviceId = entities?.[entityId]?.device_id ?? entityId;
        const available = isAvailable(states, entityId);
        const card = cards.get(deviceId) ?? { device_id: deviceId, rows: [] };
        card.rows.push({
            direction: info.direction,
            medium: info.medium,
            entity_id: entityId,
            available,
            capture_device: info.capture,
            fact: rowFact(info.direction, entityId, available, facts),
        });
        cards.set(deviceId, card);
    }
    for (const card of cards.values()) {
        card.rows.sort((a, b) => rank(a) - rank(b) || a.entity_id.localeCompare(b.entity_id));
    }
    return Array.from(cards.values());
}

/** The three sections, as today: a device with a transmitter is an
 *  emitter, one with a receiver is a receiver, one with both is also a
 *  proxy and shows in all three. */
export function hardwareSections(cards: HardwareCard[]): HardwareSections {
    const hasTx = (c: HardwareCard) => c.rows.some((r) => r.direction === "tx");
    const hasRx = (c: HardwareCard) => c.rows.some((r) => r.direction === "rx");
    return {
        emitters: cards.filter(hasTx),
        receivers: cards.filter(hasRx),
        proxies: cards.filter((c) => hasTx(c) && hasRx(c)),
    };
}

/** Where the infrared group ends and the radio group starts, for the
 *  dashed rule; -1 when the card has only one medium. */
export function mediumBreak(card: HardwareCard): number {
    const first = card.rows.findIndex((r) => r.medium === "rf");
    return first > 0 ? first : -1;
}

/** Whether every entity on the card is down: the corner OFFLINE word,
 *  the ember edge and the outline icon. */
export function cardOffline(card: HardwareCard): boolean {
    return card.rows.length > 0 && card.rows.every((r) => !r.available);
}

/** A time since, in whole units, for "sent 14 s ago": seconds under a
 *  minute, minutes under an hour, hours under a day, then days. */
export function agoParts(iso: string, nowMs: number): { n: number; unit: "s" | "m" | "h" | "d" } | null {
    const then = Date.parse(iso);
    if (!Number.isFinite(then)) return null;
    const s = Math.max(0, Math.floor((nowMs - then) / 1000));
    if (s < 60) return { n: s, unit: "s" };
    if (s < 3600) return { n: Math.floor(s / 60), unit: "m" };
    if (s < 86400) return { n: Math.floor(s / 3600), unit: "h" };
    return { n: Math.floor(s / 86400), unit: "d" };
}
