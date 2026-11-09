/**
 * A radio code as the editor shows it (RF send round, T3).
 *
 * Plain functions, no browser and no localize, so the node tests run
 * them: the `.sub` text a stored frame is shown and copied as (the same
 * text the server's `rf_paste.to_sub` writes), the frequency field's
 * presets and parsing, and which sentence each refusal and each
 * frequency source maps to.
 */

/** The bands offered as one click; any other Hz is typed. */
export const RF_PRESETS_HZ = [433_920_000, 315_000_000] as const;

/** The frequency field's range, the doors' own (rf/validate,
 *  command/update): 1 MHz to 10 GHz. */
export const RF_MIN_HZ = 1_000_000;
export const RF_MAX_HZ = 10_000_000_000;

const SUB_HEADER = "Filetype: Flipper SubGhz RAW File";
const SUB_PRESET = "FuriHalSubGhzPresetOok650Async";
const SUB_LINE_VALUES = 512;

/** One frame as a Flipper SubGhz RAW file: the frame once, ending on
 *  its gap, `Frequency: 0` when there is none yet. */
export function toSub(frame: number[], frequencyHz: number | null, gapUs: number | null): string {
    const values = frame.filter((v) => v !== 0).map((v) => Math.round(v));
    if (values.length && values[values.length - 1] > 0 && gapUs) values.push(-Math.round(gapUs));
    const lines = [
        SUB_HEADER,
        "Version: 1",
        `Frequency: ${Math.round(frequencyHz ?? 0)}`,
        `Preset: ${SUB_PRESET}`,
        "Protocol: RAW",
    ];
    for (let start = 0; start < values.length; start += SUB_LINE_VALUES) {
        lines.push("RAW_Data: " + values.slice(start, start + SUB_LINE_VALUES).join(" "));
    }
    return lines.join("\n") + "\n";
}

/** A .sub's text with its Frequency line set to ``frequencyHz``, so the
 *  Code box says the band the buttons say (N15). Text with no Frequency
 *  line (timings, a Broadlink code) comes back unchanged. */
export function withSubFrequency(text: string, frequencyHz: number): string {
    return text.replace(/^([ \t]*Frequency:[ \t]*)\d+/m, `$1${Math.round(frequencyHz)}`);
}

/** "433.92" or "433.92 MHz" to Hz, or null when it is not a frequency
 *  the doors take. */
export function mhzToHz(text: string): number | null {
    const cleaned = text.trim().replace(/\s*mhz$/i, "").replace(",", ".");
    if (!/^\d+(\.\d+)?$/.test(cleaned)) return null;
    const hz = Math.round(parseFloat(cleaned) * 1_000_000);
    return hz >= RF_MIN_HZ && hz <= RF_MAX_HZ ? hz : null;
}

/** Hz as the field shows it: MHz, up to three decimals, no trailing
 *  zeros ("433.92", "315", "303.875"). */
export function hzToMhz(hz: number): string {
    return String(Math.round(hz / 1000) / 1000);
}

/** Which preset a frequency is, or null for a typed one. */
export function presetOf(hz: number | null): number | null {
    return hz !== null && (RF_PRESETS_HZ as readonly number[]).includes(hz) ? hz : null;
}

/** The locale key for where a frequency came from. */
export function sourceKey(source: string | null | undefined): string | null {
    switch (source) {
        case "signal":
            return "rfedit.source_signal";
        case "receiver":
        case "window":
            return "rfedit.source_receiver";
        case "user":
            return "rfedit.source_user";
        case "assumed":
            return "rfedit.source_assumed";
        default:
            return null;
    }
}

/** The locale key for a paste refusal from rf/validate. */
export function pasteRefusalKey(code: string | null | undefined): string | null {
    switch (code) {
        case "rf_paste_empty":
        case "rf_paste_unreadable":
        case "rf_paste_no_frame":
        case "rf_paste_frames_disagree":
            return `rfedit.${code.replace("rf_", "")}`;
        default:
            return null;
    }
}

/** A wig's radio rows (hair-wig/5) as `.sub` files, one per row, for
 *  the Closet's download (T5). `wigText` is the wig file as the server
 *  serves it; `baseName` is its download name. Rows named alike get a
 *  number, so no file overwrites another. Infrared wigs give none. */
export function wigSubFiles(
    wigText: string, baseName: string,
): { filename: string; text: string }[] {
    let wig: { signals?: unknown };
    try {
        wig = JSON.parse(wigText);
    } catch {
        return [];
    }
    const signals = Array.isArray(wig?.signals) ? wig.signals : [];
    const base = baseName.replace(/\.wig\.json$/i, "").replace(/\.json$/i, "");
    const taken = new Set<string>();
    const out: { filename: string; text: string }[] = [];
    for (const raw of signals) {
        const sig = raw as {
            alias?: unknown;
            rf?: { frequency_hz?: unknown; frame?: unknown; frame_gap_us?: unknown };
        };
        const rf = sig?.rf;
        if (!rf || !Array.isArray(rf.frame)) continue;
        const slug = String(sig.alias ?? "")
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "") || "code";
        let name = `${base}-${slug}`;
        for (let n = 2; taken.has(name); n += 1) name = `${base}-${slug}-${n}`;
        taken.add(name);
        out.push({
            filename: `${name}.sub`,
            text: toSub(
                rf.frame as number[],
                typeof rf.frequency_hz === "number" ? rf.frequency_hz : null,
                typeof rf.frame_gap_us === "number" ? rf.frame_gap_us : null,
            ),
        });
    }
    return out;
}
