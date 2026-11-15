/**
 * Send and edit refusals, in the user's language.
 *
 * The server refuses with a code on the Test, send, edit and device
 * doors (`agent-exchange/rf-hear/rf-send-doors.md` section 2), and the
 * panel shows a sentence for each instead of the raw message.
 *
 * RF hear round 1 had two: HAIR did not send radio yet
 * (`rf_send_unsupported`), and a radio row had no Pronto to edit
 * (`rf_edit_unsupported`). The send round retires both, and its own
 * refusals are about which emitter can send what. The two old codes
 * keep their sentences until the server stops sending them.
 */
import { t } from "./localize.js";

export const RF_SEND_UNSUPPORTED = "rf_send_unsupported";
export const RF_EDIT_UNSUPPORTED = "rf_edit_unsupported";
export const NO_EMITTER_FOR_MEDIUM = "no_emitter_for_medium";
export const RF_NO_FREQUENCY = "rf_no_frequency";
/** A radio command with no frame to send (radio trigger fix): one made
 *  from a radio Remote before the fix, or one waiting for its button to
 *  be heard once. The server refuses it before anything else. */
export const RF_NO_FRAME = "rf_no_frame";
export const RF_FREQUENCY_UNSUPPORTED = "rf_frequency_unsupported";
export const RF_PLATFORM_NOT_LOADED = "rf_platform_not_loaded";
export const EMITTER_WRONG_MEDIUM = "emitter_wrong_medium";
export const INVALID_EMITTER = "invalid_emitter";
/** An infrared code sent to the radio editor, or the reverse (send
 *  review N10): only a stale panel or a crafted request reaches it. */
export const WRONG_MEDIUM_CODE = "wrong_medium_code";

const SENTENCES: Record<string, string> = {
    [RF_SEND_UNSUPPORTED]: "errors.rf_send_unsupported",
    [RF_EDIT_UNSUPPORTED]: "errors.rf_edit_unsupported",
    [NO_EMITTER_FOR_MEDIUM]: "errors.no_emitter_for_medium",
    [RF_NO_FREQUENCY]: "errors.rf_no_frequency",
    [RF_NO_FRAME]: "errors.rf_no_frame",
    [RF_FREQUENCY_UNSUPPORTED]: "errors.rf_frequency_unsupported",
    [RF_PLATFORM_NOT_LOADED]: "errors.rf_platform_not_loaded",
    [EMITTER_WRONG_MEDIUM]: "errors.emitter_wrong_medium",
    [INVALID_EMITTER]: "errors.invalid_emitter",
    [WRONG_MEDIUM_CODE]: "errors.wrong_medium_code",
};

/** The locale key for a refusal code, or null for any other error.
 *  Pure, so the node tests can check the map without localize. */
export function refusalKey(err: unknown): string | null {
    const code = (err as { code?: unknown } | null)?.code;
    return typeof code === "string" ? (SENTENCES[code] ?? null) : null;
}

/** The sentence for a refusal, or null for any other error. */
export function sendRefusal(err: unknown): string | null {
    const key = refusalKey(err);
    return key ? t(key) : null;
}

/** A Test from the Sniffer or the Clipper refused (send review N14):
 *  the locale key and its values. A frequency the picked transmitter
 *  cannot send names that transmitter and the band, since a Sniffer or
 *  Clipper row has no device; anything else is the send refusal's own
 *  sentence. Null for an error that is not a refusal. Pure, for the
 *  node tests. */
export function testRefusalKey(
    err: unknown,
    transmitterName: string,
    band: string | null,
): { key: string; params?: Record<string, string> } | null {
    const code = (err as { code?: unknown } | null)?.code;
    if (code === RF_FREQUENCY_UNSUPPORTED && band) {
        return { key: "errors.test_rf_frequency_unsupported", params: { name: transmitterName, band } };
    }
    const key = refusalKey(err);
    return key ? { key } : null;
}

/** The sentence for a refused Test, or null. */
export function testRefusal(err: unknown, transmitterName: string, band: string | null): string | null {
    const found = testRefusalKey(err, transmitterName, band);
    return found ? t(found.key, found.params) : null;
}

/** The first radio send in a Test fan-out that went out at the
 *  transmitter's own frequency, as Hz, or null. */
export function substitutedHz(
    results: PromiseSettledResult<{ substituted?: boolean; frequency_hz?: number }>[],
): number | null {
    for (const r of results) {
        if (r.status === "fulfilled" && r.value.substituted && r.value.frequency_hz) {
            return r.value.frequency_hz;
        }
    }
    return null;
}

/** Words in the server's rf_frequency_unsupported message (rf_send.py)
 *  that mean "no transmitter can send this band" would not be true. */
export const BAND_SENTENCE_UNTRUE = ["unavailable", "declares no frequency"] as const;

/** A device command's send refused (N19): the locale key and its
 *  values, naming the code, the medium and the device. A radio code
 *  with no radio transmitter, an infrared code with no infrared
 *  emitter, and radio transmitters that cannot send the band each get
 *  their own sentence; anything else is the refusal's general sentence,
 *  as is a refusal with no names to hand. Null for an error that is
 *  not a refusal. Pure, for the node tests. */
export function deviceRefusalKey(
    err: unknown,
    ctx: { device?: string | null; command?: string | null; medium?: string | null; band?: string | null },
): { key: string; params?: Record<string, string> } | null {
    const code = (err as { code?: unknown } | null)?.code;
    const device = ctx.device || "";
    const command = ctx.command || "";
    if (code === NO_EMITTER_FOR_MEDIUM && device && command) {
        return {
            key: ctx.medium === "rf" ? "errors.no_radio_transmitter" : "errors.no_infrared_emitter",
            params: { command, device },
        };
    }
    if (code === RF_FREQUENCY_UNSUPPORTED && device && ctx.band) {
        // The band sentence says no transmitter can send it. When one is
        // down, or every transmitter declares no frequency (a YAML fix),
        // that is not the reason: the server's own message says which,
        // so the caller shows it.
        const message = String((err as { message?: unknown }).message ?? "");
        if (BAND_SENTENCE_UNTRUE.some((m) => message.includes(m))) return null;
        return { key: "errors.no_transmitter_for_band", params: { device, band: ctx.band } };
    }
    const key = refusalKey(err);
    return key ? { key } : null;
}

/** The sentence for a device command's refused send, or null. */
export function deviceRefusal(
    err: unknown,
    ctx: { device?: string | null; command?: string | null; medium?: string | null; band?: string | null },
): string | null {
    const found = deviceRefusalKey(err, ctx);
    return found ? t(found.key, found.params) : null;
}

/** The round 1 name, kept for its callers. */
export const rfRefusal = sendRefusal;
