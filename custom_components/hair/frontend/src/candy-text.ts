/**
 * The Candy Drawer's text: one block per infrared event, as it is shown
 * and as Copy all hands it over.
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
 */

/** One event from ``hair/candy/subscribe`` (candy_feed.py). */
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
    raw: number[];
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
    return parts.join(WIDE);
}

/** One event as its block of text, lines joined by "\n". */
export function formatBlock(e: CandyEvent, timeZone?: string): string {
    const lines = [headerLine(e, timeZone)];
    if (!e.ditto) {
        lines.push(decodeLine(e));
        lines.push(`Pronto: ${e.pronto || "none"}`);
    }
    lines.push(`Raw: ${e.raw.length ? e.raw.join(" ") : "none"}`);
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

/** Whether the RX / TX filter chips let this block show. */
export function isVisible(dir: "rx" | "tx", filter: { rx: boolean; tx: boolean }): boolean {
    return dir === "rx" ? filter.rx : filter.tx;
}

/** Copy all: the visible blocks, one blank line between them. */
export function copyText(
    marker: string,
    dropped: string | null,
    blocks: { dir: "rx" | "tx"; text: string }[],
    filter: { rx: boolean; tx: boolean },
): string {
    const parts = [marker];
    if (dropped) parts.push(dropped);
    for (const b of blocks) if (isVisible(b.dir, filter)) parts.push(b.text);
    return parts.join("\n\n") + "\n";
}
