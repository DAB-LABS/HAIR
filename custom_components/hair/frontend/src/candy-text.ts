/**
 * The Candy Drawer's text: one block per infrared or radio event, as it
 * is shown and as Copy all hands it over.
 *
 * Pure on purpose (no Lit, no DOM), so the layout runs under node in the
 * test suite. The block labels (RX, TX, Pronto, Raw, address, command,
 * frames, the echo and decode labels) are fixed English: the text exists
 * to be pasted into issues and pull requests. The window's own strings
 * (the opened marker, the dropped line) are passed in already localized.
 *
 * Numbers are separated by single plain spaces and never by anything
 * else, so the dialog's word wrap breaks lines between numbers and every
 * number stays whole.
 *
 * A radio block's .sub text comes from the radio editor's own writer
 * (``toSub``), fed the three values a row minted from the capture would
 * hold, so a block copied from here pastes into the Clipper and comes
 * back as the same code (schema: rf-2026-11-11-candy-schema.md).
 */
import { bandLabel } from "./rf-band.js";
import { toSub } from "./rf-code.js";

export type CandyMedium = "ir" | "rf";
export type CandyVerdict = "known" | "unknown" | "static";

/** One event from ``hair/candy/subscribe`` (candy_feed.py). An event
 *  from before radio carries no ``medium`` and reads as infrared. */
export interface CandyEvent {
    ts: number;
    dir: "rx" | "tx";
    protocol: string | null;
    address: string | null;
    command: string | null;
    fingerprint: string | null;
    covers: boolean | null;
    carrier_hz: number | null;
    frames: number;
    pronto: string | null;
    raw: number[] | null;
    // Every event since radio (the verdict: does HAIR hold this code)
    medium?: CandyMedium;
    verdict?: CandyVerdict;
    known_from?: "echo" | "device" | "trigger" | "sniffer" | null;
    known_name?: string | null;
    stage?: "press" | "frame" | "static" | null;
    // Radio
    frequency_hz?: number | null;
    frequency_source?: string | null;
    modulation?: string | null;
    short_mark_us?: number | null;
    gap_us?: number | null;
    gap_source?: string | null;
    votes?: number | null;
    frame_hash?: string | null;
    body_edges?: number | null;
    frame?: number[] | null;
    /** A static summary: captures since that receiver's last summary. */
    count?: number | null;
    since?: number | null;
    values?: number | null;
    /** A single static capture: why it is static. */
    reason?: "lone" | "no_body" | "short" | string | null;
    on_air_hz?: number | null;
    substituted?: boolean | null;
    skipped?: { entity_id: string; name: string; reason: string }[];
    // RX
    entity_id?: string | null;
    name?: string | null;
    ditto?: boolean;
    echo?: "send" | "guard" | "garbled" | "foreign" | null;
    echo_of?: number | null;
    echo_via?: string | null;
    // TX
    seq?: number;
    emitters?: { entity_id: string; name: string }[];
    label?: string;
    device?: string | null;
    command_name?: string | null;
    sends?: number;
    origin?: string | null;
}

/** Blocks kept in the open window, the queue of a pause included. */
export const CANDY_CAP = 2000;

/** Between the time and the direction, and between fields on a line. */
const GAP = "  ";
const WIDE = "   ";

/** Whole milliseconds, rounded once, so 0.818 s never prints as .817. */
function epochMs(ts: number): number {
    return Math.round(ts * 1000);
}

function zoneParts(ts: number, timeZone?: string): Intl.DateTimeFormatPart[] {
    return new Intl.DateTimeFormat("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hourCycle: "h23",
        timeZone,
        timeZoneName: "longOffset",
    }).formatToParts(new Date(epochMs(ts)));
}

/** "12:04:31.218" in the given zone (undefined: the browser's). */
export function clockTime(ts: number, timeZone?: string): string {
    const parts = zoneParts(ts, timeZone);
    const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "00";
    const ms = String(epochMs(ts) % 1000).padStart(3, "0");
    return `${get("hour")}:${get("minute")}:${get("second")}.${ms}`;
}

/** "UTC-7", "UTC+5:30", or "UTC", at the given moment in the zone. */
export function zoneOffset(ts: number, timeZone?: string): string {
    const name = zoneParts(ts, timeZone).find((p) => p.type === "timeZoneName")?.value ?? "";
    const m = /([+-])(\d{1,2})(?::?(\d{2}))?/.exec(name);
    if (!m) return "UTC";
    const hours = String(Number(m[2]));
    const minutes = m[3] && m[3] !== "00" ? `:${m[3]}` : "";
    if (hours === "0" && !minutes) return "UTC";
    return `UTC${m[1]}${hours}${minutes}`;
}

/** The opened marker, from its localized template ({time}, {zone}). */
export function openedLine(template: string, ts: number, timeZone?: string): string {
    const time = clockTime(ts, timeZone).slice(0, 8);
    return template.split("{time}").join(time).split("{zone}").join(zoneOffset(ts, timeZone));
}

function carrier(hz: number | null): string | null {
    if (!hz) return null;
    const khz = hz / 1000;
    return `${hz % 1000 === 0 ? khz.toFixed(0) : khz.toFixed(1)} kHz`;
}

function frames(count: number): string {
    return count === 1 ? "1 frame" : `${count} frames`;
}

function who(name: string | null | undefined, entityId: string | null | undefined): string {
    if (name && entityId && name !== entityId) return `${name} (${entityId})`;
    return name || entityId || "unknown receiver";
}

/** What the echo gate made of a received frame, or null. */
export function echoLabel(e: CandyEvent): string | null {
    switch (e.echo) {
        case "send":
        case "guard":
            return e.echo_of != null ? "echo of the TX above" : "echo of a HAIR send";
        case "garbled":
            return e.echo_of != null
                ? "echo of the TX above (garbled)"
                : "echo of a HAIR send (garbled)";
        case "foreign":
            return `echo of a send by another integration via ${e.echo_via || "an emitter"}`;
        default:
            return null;
    }
}

function decodeLine(e: CandyEvent): string {
    const fields: string[] = [];
    if (e.protocol) {
        fields.push(
            [e.protocol, `address=${e.address}`, `command=${e.command}`, e.fingerprint ?? ""]
                .filter(Boolean)
                .join(GAP),
        );
        if (e.covers === false) fields.push("decode covers part");
    } else {
        fields.push("no decode");
    }
    const khz = carrier(e.carrier_hz);
    if (khz) fields.push(khz);
    fields.push(frames(e.frames));
    return fields.join(WIDE);
}

/** The event's medium; one from before radio is infrared. */
export function mediumOf(e: Pick<CandyEvent, "medium">): CandyMedium {
    return e.medium === "rf" ? "rf" : "ir";
}

/** Whether the event is a static summary (a line, never a block). */
export function isStaticSummary(e: CandyEvent): boolean {
    return e.stage === "static" && typeof e.count === "number";
}

/** What the header says HAIR holds, after the echo words: "known: Bench
 *  Plug / On", "known: trigger Doorbell", "new", "frame, waiting", or
 *  nothing (an echo, an old event, a value this panel does not know). */
export function knownWords(e: CandyEvent): string | null {
    if (e.dir !== "rx" || !e.verdict) return null;
    const frame = e.stage === "frame";
    if (e.verdict === "unknown") {
        if (frame) return "frame, waiting";
        return e.ditto ? null : "new";
    }
    if (e.verdict === "static") return staticWords(e.reason);
    if (e.verdict !== "known") return null;
    let name: string | null = null;
    switch (e.known_from) {
        case "device":
        case "sniffer":
            name = e.known_name || null;
            break;
        case "trigger":
            name = e.known_name ? `trigger ${e.known_name}` : null;
            break;
        default:
            // An echo says so in its own words; anything else, nothing.
            return null;
    }
    if (!name) return null;
    return frame ? `known: ${name}, frame` : `known: ${name}`;
}

/** A single static capture's header word (owner, 2026-11-12): hiss
 *  for a capture with no code in it, or one too short to be a remote's
 *  (a short vote, or a lone piece under a remote's length); lone frame
 *  for frames whose burst never agreed; plain static for a reason this
 *  panel does not know. */
export function staticWords(reason: string | null | undefined): string {
    switch (reason) {
        case "no_body":
        case "short":
            return "static: hiss";
        case "lone":
            return "static: lone frame";
        default:
            return "static";
    }
}

function mhz(hz: number | null | undefined): string | null {
    return hz ? `${bandLabel(hz)} MHz` : null;
}

function ms(us: number): string {
    const value = us / 1000;
    return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)} ms`;
}

/** A radio block's second line: band and source, short mark, gap,
 *  frames and agreement, fingerprint. A family name, when decoders
 *  exist, goes right after "RF". */
function radioLine(e: CandyEvent): string {
    const head = e.protocol ? `RF${GAP}${e.protocol}` : "RF";
    const fields = [head];
    if (e.dir === "tx") {
        const band = mhz(e.frequency_hz);
        if (band) fields.push(band);
        const onAir = mhz(e.on_air_hz);
        if (onAir && (onAir !== band || e.substituted)) {
            fields.push(e.substituted ? `on air ${onAir} (its own carrier)` : `on air ${onAir}`);
        }
    } else {
        const band = mhz(e.frequency_hz);
        fields.push(band ? (e.frequency_source ? `${band} (${e.frequency_source})` : band) : "no band");
        if (e.short_mark_us) fields.push(`short mark ${Math.round(e.short_mark_us)} us`);
    }
    if (e.gap_us) fields.push(e.gap_source === "assumed" ? `gap ${ms(e.gap_us)} (assumed)` : `gap ${ms(e.gap_us)}`);
    if (e.dir === "rx") {
        fields.push(
            e.votes && e.frames > 1 ? `${frames(e.frames)}, ${e.votes} agree` : frames(e.frames || 1),
        );
    }
    if (e.frame_hash) fields.push(`fp ${e.frame_hash.slice(0, 8)}`);
    return fields.join(WIDE);
}

/** The .sub text the radio editor's copy writes for this code. */
function subLines(e: CandyEvent): string[] {
    if (!e.frame || !e.frame.length) return [];
    return ["Sub:", ...toSub(e.frame, e.frequency_hz ?? null, e.gap_us ?? null).trimEnd().split("\n")];
}

function rawLine(raw: number[] | null | undefined): string {
    return `Raw: ${raw && raw.length ? raw.join(" ") : "none"}`;
}

function skippedLine(e: CandyEvent): string | null {
    const skipped = e.skipped ?? [];
    if (!skipped.length) return null;
    return "skipped: " + skipped.map((s) => `${who(s.name, s.entity_id)} (${s.reason})`).join(", ");
}

function headerLine(e: CandyEvent, timeZone?: string): string {
    const time = clockTime(e.ts, timeZone);
    if (e.dir === "tx") {
        const via = (e.emitters ?? []).map((m) => who(m.name, m.entity_id)).join(", ");
        const parts = [`${time}${GAP}TX${GAP}${via || "no emitter"}`];
        if (e.label) parts.push(e.label);
        if ((e.sends ?? 1) > 1) parts.push(`x${e.sends} sends`);
        return parts.join(WIDE);
    }
    const parts = [`${time}${GAP}RX${GAP}${who(e.name, e.entity_id)}`];
    if (e.ditto) parts.push("repeat frame (ditto)");
    const echo = echoLabel(e);
    if (echo) parts.push(echo);
    const known = knownWords(e);
    if (known) parts.push(known);
    return parts.join(WIDE);
}

/** One event as its block of text, lines joined by "\n". */
export function formatBlock(e: CandyEvent, timeZone?: string): string {
    const lines = [headerLine(e, timeZone)];
    if (mediumOf(e) === "rf") {
        if (e.stage === "static") {
            // A single static capture (Static on): what came, nothing more.
            lines.push(rawLine(e.raw));
            return lines.join("\n");
        }
        lines.push(radioLine(e));
        const skipped = e.dir === "tx" ? skippedLine(e) : null;
        if (skipped) lines.push(skipped);
        lines.push(...subLines(e));
        lines.push(rawLine(e.raw));
        return lines.join("\n");
    }
    if (!e.ditto) {
        lines.push(decodeLine(e));
        lines.push(`Pronto: ${e.pronto || "none"}`);
    }
    lines.push(rawLine(e.raw));
    return lines.join("\n");
}

/** Where a block with this time goes so the list stays in time order.
 * Blocks almost always arrive in order, so this walks back from the end. */
export function insertIndex(times: number[], ts: number): number {
    let i = times.length;
    while (i > 0 && times[i - 1] > ts) i -= 1;
    return i;
}

/** How many of the oldest blocks must go to keep shown + queued at the cap. */
export function overflow(shown: number, queued: number, cap: number = CANDY_CAP): number {
    return Math.max(0, shown + queued - cap);
}

/** The chips: direction, medium, and whether HAIR holds the code. */
export interface CandyFilter {
    rx: boolean;
    tx: boolean;
    ir: boolean;
    rf: boolean;
    known: boolean;
    unknown: boolean;
    static: boolean;
}

/** Every chip on except Static, which starts off every time. */
export const DEFAULT_CANDY_FILTER: CandyFilter = {
    rx: true, tx: true, ir: true, rf: true, known: true, unknown: true, static: false,
};

/** What a block is, for the chips. */
export interface CandyKind {
    dir: "rx" | "tx";
    medium: CandyMedium;
    verdict: CandyVerdict;
}

/** A block's kind. TX is always Known; an event from before radio, with
 *  no verdict, shows under Known or Unknown alike. */
export function kindOf(e: CandyEvent): CandyKind {
    const medium = mediumOf(e);
    const verdict: CandyVerdict =
        e.dir === "tx" ? "known" : e.verdict === "static" || e.verdict === "unknown" ? e.verdict : "known";
    return { dir: e.dir, medium, verdict };
}

/** Whether the chips let this block show. Static is radio only, and
 *  shows only with RF on. An event with no verdict follows Known or
 *  Unknown, whichever is on. */
export function isVisible(kind: CandyKind, filter: CandyFilter, hasVerdict = true): boolean {
    if (!(kind.dir === "rx" ? filter.rx : filter.tx)) return false;
    if (!(kind.medium === "rf" ? filter.rf : filter.ir)) return false;
    if (kind.verdict === "static") return kind.medium === "rf" && filter.static;
    if (!hasVerdict) return filter.known || filter.unknown;
    return kind.verdict === "known" ? filter.known : filter.unknown;
}

/** Copy all: the opened marker, the dropped line and the static lines,
 *  then the visible blocks, one blank line between each. */
export function copyText(
    marker: string,
    dropped: string | null,
    blocks: { kind: CandyKind; hasVerdict?: boolean; text: string }[],
    filter: CandyFilter,
    staticLines: string[] = [],
): string {
    const parts = [marker];
    if (dropped) parts.push(dropped);
    parts.push(...staticLines);
    for (const b of blocks) if (isVisible(b.kind, filter, b.hasVerdict ?? true)) parts.push(b.text);
    return parts.join("\n\n") + "\n";
}

/** This browser's key for the chips. Static is never kept. */
export const CANDY_CHIPS_KEY = "hair.candy.chips";

/** The chips as kept in this browser, or the defaults for anything
 *  missing or unreadable. Static always starts off. */
export function parseChips(stored: string | null | undefined): CandyFilter {
    const filter = { ...DEFAULT_CANDY_FILTER };
    if (!stored) return filter;
    try {
        const data = JSON.parse(stored) as Record<string, unknown>;
        for (const key of ["rx", "tx", "ir", "rf", "known", "unknown"] as const) {
            if (typeof data[key] === "boolean") filter[key] = data[key] as boolean;
        }
    } catch {
        /* the defaults */
    }
    filter.static = false;
    return filter;
}

/** The chips to keep in this browser: everything but Static. */
export function serializeChips(filter: CandyFilter): string {
    const { rx, tx, ir, rf, known, unknown } = filter;
    return JSON.stringify({ rx, tx, ir, rf, known, unknown });
}

/** Static summaries added up per receiver: the panel keeps the total,
 *  the server sends the number since its last summary. */
export function addStatic(
    totals: Map<string, { name: string; count: number }>,
    e: CandyEvent,
): string {
    const key = e.entity_id || e.name || "unknown receiver";
    const seen = totals.get(key);
    const count = (seen?.count ?? 0) + Math.max(0, Math.trunc(e.count ?? 0));
    totals.set(key, { name: who(e.name, e.entity_id), count });
    return key;
}

/** One receiver's static line, from its localized template ({count},
 *  {name}). */
export function staticLine(template: string, name: string, count: number): string {
    return template.split("{count}").join(String(count)).split("{name}").join(name);
}
