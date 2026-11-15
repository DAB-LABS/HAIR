/**
 * Which kind of hardware a picker offers (owner, 2026-11-14).
 *
 * Radio work offers radio receivers and transmitters only, and
 * infrared work infrared ones only. When the thing being made or
 * edited has codes of one kind, a picker shows that kind. When it has
 * both kinds, or nothing yet to tell by (a new device or Remote made by
 * hand, a wig whose codes the panel has not read), it shows both,
 * grouped under Infrared and Radio, so either kind can still be added.
 *
 * Make a Device from a Remote already worked this way (#269); this file
 * gives every other picker's caller the same rule. Selections of the
 * other kind are dropped when the dialog saves, the way the trigger
 * dialog already drops a receiver of the wrong kind (N18), so nothing
 * hidden is saved.
 *
 * Imports nothing at runtime, so tests run it under node.
 */
import type { Medium } from "./types.js";

/** The one kind in a media list, or null for both kinds or none. */
export function soleKind(media: readonly Medium[] | null | undefined): Medium | null {
    if (!media || media.length !== 1) return null;
    return media[0] === "rf" || media[0] === "ir" ? media[0] : null;
}

/** The one kind a device's or Remote's codes use, or null. A row with
 *  no medium is infrared, as everywhere else in the panel; a climate
 *  matrix only ever holds infrared codes, so it adds infrared to what
 *  the rows hold, as the server's `_media` does. */
export function rowsKind(
    rows: readonly { medium?: Medium | null }[] | null | undefined,
    matrix = false,
): Medium | null {
    const kinds = new Set<Medium>((rows ?? []).map((r) => (r.medium === "rf" ? "rf" : "ir")));
    if (matrix) kinds.add("ir");
    return kinds.size === 1 ? (kinds.values().next().value as Medium) : null;
}

/** A Sniffer, Clipper or Plucker remote's kind: radio says so, and one
 *  that says nothing is infrared. */
export function unknownKind(medium: Medium | null | undefined): Medium {
    return medium === "rf" ? "rf" : "ir";
}

/** The ids a picker of `kind` may save: all of them when the kind is
 *  open, otherwise only those of that kind. An id whose kind cannot be
 *  read is kept. */
export function keepKind(
    ids: readonly string[],
    kind: Medium | null,
    mediumOf: (id: string) => Medium | null,
): string[] {
    if (!kind) return [...ids];
    return ids.filter((id) => {
        const m = mediumOf(id);
        return m === null || m === kind;
    });
}

/** Whether a header chip row lists an entity: every one when the kind
 *  is open; otherwise those of the kind, those whose kind cannot be
 *  read, and any of the other kind that is still on, so it can be
 *  turned off. */
export function listsInKind(
    id: string,
    kind: Medium | null,
    mediumOf: (id: string) => Medium | null,
    on: boolean,
): boolean {
    if (!kind || on) return true;
    const m = mediumOf(id);
    return m === null || m === kind;
}

/** The picker's `media` property for a kind: that kind alone, or null
 *  for both. */
export function mediaFor(kind: Medium | null): Medium[] | null {
    return kind ? [kind] : null;
}
