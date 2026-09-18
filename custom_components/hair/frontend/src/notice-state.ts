/**
 * How long a panel notice lives.
 *
 * Split out of the panel because the answer is a rule rather than a
 * render, and because the rule was wrong once in a way no rendering
 * test would have caught: a drop that filed several wigs dispatched
 * the notice and a `device-changed` in the same breath, the refetch
 * that `device-changed` triggers cleared the notice on success, and
 * the banner the fix exists to show survived one websocket round trip.
 *
 * So the refresh is a signal like any other here, and its answer is
 * "keep what is there". A notice ends where a new user action begins:
 * the next drop, or the dismiss button.
 */
export type NoticeSignal =
    | { kind: "landed"; text: string }
    | { kind: "drop-failed" }
    | { kind: "dismissed" }
    | { kind: "refreshed" };

export function nextNotice(
    current: string | null,
    signal: NoticeSignal,
): string | null {
    switch (signal.kind) {
        case "landed":
            return signal.text;
        case "drop-failed":
        case "dismissed":
            return null;
        case "refreshed":
            // NOT null. This is the refetch the notice's own drop asked
            // for, and it must not erase the sentence that sent it.
            return current;
    }
}
