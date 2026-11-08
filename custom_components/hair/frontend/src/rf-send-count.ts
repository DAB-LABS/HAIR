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

/** The Assign dialog's starting count for a row. */
export function assignSendCount(
    signal: Pick<UnknownSignal, "medium" | "send_count" | "rf_repeats_observed"> | null | undefined,
): number {
    const stored = signal?.send_count ?? 1;
    if (signal?.medium !== "rf" || stored > 1) return stored;
    return seedSendCount(signal.rf_repeats_observed);
}
