/**
 * Grouped commands (grouped-signals.md): the rules the panel shows.
 *
 * The bounds mirror ``const.py``'s GROUP_* constants, and a test checks
 * that the two agree. The server checks the same bounds on save, so
 * these only decide what the field says before the save is asked for.
 *
 * Pure, for the node tests: `t` is passed in where words are needed.
 */

export const GROUP_PROTOCOL = "GROUP";

/** The GROUP chip's colour, and the picker's "This device" badge, which
 *  follows it: avocado, clear of the colours already taken (blue
 *  protocol, orange Pronto and send count, gold capture and TRIGGER,
 *  green assign, copper Clipper), between the gold and the green. On a
 *  light theme it is a deeper avocado: the dark-theme one is 2.7:1 on
 *  white, this one 5.5:1. The device page
 *  picks between them (--hair-group-hue), as the Sniffer tones its
 *  last-heard wash. */
export const GROUP_HUE = "#86a83f";
export const GROUP_HUE_LIGHT = "#55722a";
/** The floor: counted from the END of the previous signal. */
export const GROUP_DELAY_MIN_MS = 300;
export const GROUP_DELAY_MAX_MS = 60_000;
export const GROUP_DELAY_DEFAULT_MS = 300;
export const GROUP_MAX_STEPS = 20;
export const GROUP_RUN_MAX_MS = 120_000;

/** Whether a command row is a grouped command. */
export function isGroup(command: { protocol?: string | null } | null | undefined): boolean {
    return command?.protocol === GROUP_PROTOCOL;
}

/** The delay stepper moves in steps of this. */
export const GROUP_DELAY_STEP_MS = 100;

/** A delay on the stepper's grid: rounded up to the next 100 ms, inside
 *  the floor and the most. A stored delay off the grid shows this way,
 *  and is saved this way the next time its step is changed. */
export function delayOnGrid(ms: number): number {
    const up = Math.ceil((Number(ms) || 0) / GROUP_DELAY_STEP_MS) * GROUP_DELAY_STEP_MS;
    return Math.min(GROUP_DELAY_MAX_MS, Math.max(GROUP_DELAY_MIN_MS, up));
}

/** One press of the stepper's - (-1) or + (1), from where it is now. */
export function stepDelay(ms: number, direction: 1 | -1): number {
    return delayOnGrid(delayOnGrid(ms) + direction * GROUP_DELAY_STEP_MS);
}

/** A delay as the stepper says it: "500 ms" under a second, then
 *  seconds, "1 s", "1.5 s", "12.3 s". */
export function delayText(ms: number): string {
    if (ms < 1000) return `${ms} ms`;
    const s = ms / 1000;
    return `${Number.isInteger(s) ? s : s.toFixed(1)} s`;
}

/** A run time as the row says it: "about 4.4 s", or "about 1 min 5 s". */
export function aboutSeconds(ms: number): string {
    const s = Math.max(0, ms) / 1000;
    if (s < 60) return `${s.toFixed(1)} s`;
    const whole = Math.round(s);
    return `${Math.floor(whole / 60)} min ${whole % 60} s`;
}

/** The steps the save door takes, from the steps the server showed. */
export function stepsForSave(
    steps: { device_id: string; command_id: string; delay_ms: number }[],
): { device_id: string; command_id: string; delay_ms: number }[] {
    return steps.map((s) => ({
        device_id: s.device_id,
        command_id: s.command_id,
        delay_ms: s.delay_ms,
    }));
}

/** Move one step from `from` to `to`, as the drag does. */
export function moveStep<T>(steps: readonly T[], from: number, to: number): T[] {
    const out = steps.slice();
    if (from < 0 || from >= out.length || to < 0 || to >= out.length) return out;
    const [item] = out.splice(from, 1);
    out.splice(to, 0, item);
    return out;
}

export interface PickerDevice {
    id: string;
    name: string;
    commands: { id: string; name: string }[];
}

/** The picker's view of its list for a search: which devices show, and
 *  which of their commands. With no search, every device shows with all
 *  its commands and its own open state; with one, only devices with a
 *  match show, open, with only the matching commands. */
export function pickerView<D extends PickerDevice>(
    devices: readonly D[],
    query: string,
    open: ReadonlySet<string>,
): { device: D; open: boolean; commands: D["commands"] }[] {
    const q = query.trim().toLowerCase();
    if (!q) {
        return devices.map((device) => ({
            device,
            open: open.has(device.id),
            commands: device.commands,
        }));
    }
    const out: { device: D; open: boolean; commands: D["commands"] }[] = [];
    for (const device of devices) {
        const byDevice = device.name.toLowerCase().includes(q);
        const commands = byDevice
            ? device.commands
            : device.commands.filter((c) => c.name.toLowerCase().includes(q));
        if (commands.length) out.push({ device, open: true, commands });
    }
    return out;
}

/** Why a whole device has nothing to add, or null when it has. Such a
 *  device is greyed at its row, with no chevron, rather than opening to
 *  nothing: no blaster; a climate matrix device with no saved states
 *  (its cells are not commands); no commands at all; or only commands
 *  that can't be steps. */
export function deviceBlocked(device: {
    blaster: boolean;
    matrix?: boolean;
    commands: readonly { reason?: string | null }[];
}): "no_blaster" | "matrix" | "empty" | "nothing" | null {
    if (!device.blaster) return "no_blaster";
    if (device.commands.some((c) => !c.reason)) return null;
    if (device.matrix) return "matrix";
    return device.commands.length ? "nothing" : "empty";
}

/** How many of a device's commands are in this group, each counted
 *  once however many steps send it: the green number of the picker's
 *  "3 / 12". `extra` adds "device/command" keys not yet saved. */
export function commandsInGroup(
    deviceId: string,
    steps: readonly { device_id: string; command_id: string }[],
    extra: Iterable<string> = [],
): number {
    const ids = new Set<string>();
    for (const s of steps) if (s.device_id === deviceId) ids.add(s.command_id);
    for (const key of extra) {
        if (key.startsWith(`${deviceId}/`)) ids.add(key.slice(deviceId.length + 1));
    }
    return ids.size;
}

type Translate = (key: string, subs?: Record<string, string>) => string;

/** What a delete confirm adds when grouped commands use what is being
 *  deleted: " It's a step in 2 grouped signals: Movie night (Living
 *  Room TV), Game time (Living Room TV). Those steps will show as
 *  missing." Empty when nothing uses it. */
export function groupsNote(
    t: Translate,
    groups: readonly { command_name: string; device_name: string }[],
): string {
    if (!groups.length) return "";
    const names = groups
        .map((g) => t("group.used_by_item", { name: g.command_name, device: g.device_name }))
        .join(", ");
    return (
        " " +
        t(groups.length === 1 ? "group.used_by_one" : "group.used_by_many", {
            count: String(groups.length),
            names,
        })
    );
}
