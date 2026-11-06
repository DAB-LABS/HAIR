/**
 * The two radio refusals, in the user's language (RF hear round 1).
 *
 * HAIR hears radio but does not send it yet, and a radio row has no
 * Pronto to edit. The server refuses both with a code
 * (``rf_send_unsupported``, ``rf_edit_unsupported``) on the Test, send
 * and edit doors; the panel shows a sentence for each instead of the
 * raw message.
 */
import { t } from "./localize.js";

export const RF_SEND_UNSUPPORTED = "rf_send_unsupported";
export const RF_EDIT_UNSUPPORTED = "rf_edit_unsupported";

/** The sentence for a radio refusal, or null for any other error. */
export function rfRefusal(err: unknown): string | null {
    const code = (err as { code?: unknown } | null)?.code;
    if (code === RF_SEND_UNSUPPORTED) return t("errors.rf_send_unsupported");
    if (code === RF_EDIT_UNSUPPORTED) return t("errors.rf_edit_unsupported");
    return null;
}
