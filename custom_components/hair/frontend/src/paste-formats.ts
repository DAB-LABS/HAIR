/**
 * What the Clipper's add window reads, per medium, and which editor a
 * paste belongs in.
 *
 * ONE TABLE. `PASTE_FORMATS` names the formats the code box reads, per
 * medium, in the order the empty box's hint lists them. The server's
 * `paste_medium.PASTE_FORMATS` holds the same ids, and a test checks
 * that the two agree, so adding or removing a format is one entry in
 * each and the hint follows. Format names, "raw timings" among them,
 * are names and are not translated.
 *
 * Pure, for the node tests: `t` is passed in.
 */

export type Medium = "ir" | "rf";

export const PASTE_FORMATS: Record<Medium, readonly string[]> = {
    ir: ["pronto", "broadlink", "tuya", "globalcache", "tasmota"],
    rf: ["sub", "broadlink", "timings"],
};

const FORMAT_NAMES: Record<string, string> = {
    pronto: "Pronto",
    broadlink: "Broadlink",
    tuya: "Tuya",
    globalcache: "Global Cache",
    tasmota: "Tasmota",
    sub: "Flipper .sub",
    timings: "raw timings",
};

type Translate = (key: string, subs?: Record<string, string>) => string;

/** A format's name; an id with no name shows as itself. */
export function formatName(id: string): string {
    return FORMAT_NAMES[id] ?? id;
}

/** One line per medium, naming what it reads: the add window's hint
 *  and the empty clipped remote both show these, so a new format is
 *  added once. */
export function formatLines(t: Translate): string[] {
    const line = (medium: Medium) =>
        t("addcode.hint_line", {
            medium: t(`addcode.medium_${medium}`),
            formats: PASTE_FORMATS[medium].map(formatName).join(", "),
        });
    return [line("ir"), line("rf")];
}

/** The empty box's hint: a lead-in, then the format lines. */
export function hintLines(t: Translate): string[] {
    return [t("addcode.hint_lead"), ...formatLines(t)];
}

/** The editor a paste belongs in, from the medium the server named for
 *  it (`paste_medium`). A list of timings is radio until the window can
 *  ask; text that is no code stays where it is. */
export function editorFor(
    current: Medium,
    medium: string | null | undefined,
): Medium {
    if (medium === "ir") return "ir";
    if (medium === "rf" || medium === "either") return "rf";
    return current;
}
