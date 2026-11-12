/**
 * A radio row's send count when nobody chose one (send review F5): the
 * same rule as ``rf_send.seed_send_count``. A minted radio row stores 1,
 * which plays one frame where the remote sent several, so the Assign
 * dialog treats a radio 1 as unset and prefills what one press carried,
 * clamped to RF_MIN_SEND_COUNT..MAX_SEND_COUNT, or RF_DEFAULT_SEND_COUNT
 * when the press was not measured. Infrared rows keep their stored
 * count.
 */
import type { UnknownSignal } from "./types.js";

export const MAX_SEND_COUNT = 10;
export const RF_MIN_SEND_COUNT = 2;
export const RF_DEFAULT_SEND_COUNT = 4;

/** What one press carried, as a send count. */
export function seedSendCount(repeatsObserved: number | null | undefined): number {
    if (!repeatsObserved || !Number.isFinite(repeatsObserved)) return RF_DEFAULT_SEND_COUNT;
    return Math.max(RF_MIN_SEND_COUNT, Math.min(Math.trunc(repeatsObserved), MAX_SEND_COUNT));
}

/** The line under a radio code's send count (N20): why the count is
 *  what it is, as a locale key and its number, or null when there is
 *  nothing true to say. It speaks only while the field holds the seed
 *  (what one press carried, or the usual count), so it never describes
 *  a number the field does not show; a count the user chose, or a
 *  stored 1 the field still shows, gets no line. "As the remote sent
 *  it" only when the press was measured and the clamp left it alone.
 *  Null for an infrared row, which keeps its own sentence. */
export function sendTimesHint(
    medium: string | null | undefined,
    repeatsObserved: number | null | undefined,
    current: number,
): { key: string; count: number } | null {
    if (medium !== "rf") return null;
    const seed = seedSendCount(repeatsObserved);
    if (current !== seed) return null;
    const measured =
        !!repeatsObserved && Number.isFinite(repeatsObserved) && Math.trunc(repeatsObserved) === seed;
    return {
        key: measured ? "rfedit.send_times_measured" : "rfedit.send_times_usual",
        count: seed,
    };
}

/** The Assign dialog's starting count for a row. */
export function assignSendCount(
    signal: Pick<UnknownSignal, "medium" | "send_count" | "rf_repeats_observed"> | null | undefined,
): number {
    const stored = signal?.send_count ?? 1;
    if (signal?.medium !== "rf" || stored > 1) return stored;
    return seedSendCount(signal.rf_repeats_observed);
}
