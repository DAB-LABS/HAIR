/**
 * The USE fork's pin-prompt trigger (signpost 3, Track 3 item 5,
 * owner-directed 2026-08-15): "same rule, two triggers, no
 * heuristics." The mirror-door trigger's counterpart is trivial (the
 * mint's own source IS the counterpart, by construction); this one
 * reads the Track 2.4 combined linked-count data instead, since a
 * catalog row's USE-fork mint has no such guarantee.
 *
 * The rule: if the source already carries EXACTLY ONE linked object
 * of the opposite kind, that link is the pin prompt's target. Zero
 * links: nothing to pin against, no prompt. Two or more: ambiguous --
 * no prompt, same as every other trigger in this app never guessing
 * which of several candidates is "the" match. This is the one place
 * that ambiguity rule lives, so all four catalog surfaces (Sniffer,
 * Clipper, Plucker, Closet) stay in lockstep by construction instead
 * of by four separately-maintained copies of the same filter.
 */
import type { LinkedEntry } from "./types.js";

export function singleOppositeLink(
    linked: LinkedEntry[] | undefined,
    oppositeKind: "device" | "remote",
): LinkedEntry | null {
    const matches = (linked ?? []).filter((e) => e.kind === oppositeKind);
    return matches.length === 1 ? matches[0] : null;
}
