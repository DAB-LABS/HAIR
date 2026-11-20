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
/** The floor: counted from the END of the previous signal. */
export const GROUP_DELAY_MIN_MS = 300;
export const GROUP_DELAY_MAX_MS = 60_000;
export const GROUP_DELAY_DEFAULT_MS = 500;
export const GROUP_MAX_STEPS = 20;
export const GROUP_RUN_MAX_MS = 120_000;

/** Whether a command row is a grouped command. */
export function isGroup(command: { protocol?: string | null } | null | undefined): boolean {
    return command?.protocol === GROUP_PROTOCOL;
}

/** What is wrong with a typed delay, or null: "floor" under the
 *  floor, "ceiling" over the most, "number" not a whole number. */
export function delayProblem(value: string | number): "floor" | "ceiling" | "number" | null {
    const text = String(value).trim();
    if (!/^\d+$/.test(text)) return "number";
    const ms = Number(text);
    if (ms < GROUP_DELAY_MIN_MS) return "floor";
    if (ms > GROUP_DELAY_MAX_MS) return "ceiling";
    return null;
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

/** How many of a device's commands are steps of this group already. */
export function countInGroup(
    deviceId: string,
    steps: readonly { device_id: string }[],
): number {
    return steps.filter((s) => s.device_id === deviceId).length;
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
