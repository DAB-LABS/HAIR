/**
 * A drag under a filter: the cards that are showing move among the
 * slots they hold, and the ones a filter hides stay where they are.
 *
 * The same rule as the Sniffer's store (signal_store.reorder_devices):
 * walk the whole order, and each slot a shown card held takes the next
 * card of the new order, while a hidden card keeps its slot. With no
 * filter every card is shown and this is a plain reorder. The panel then
 * sends the whole order, so a door that wants exactly the current set
 * still gets it. Kept free of lit so the node tests run it.
 */

/** The whole order after a drag, or null when ``shown`` is not a set of
 * distinct cards out of ``all`` (a stale grid; the drop is ignored).
 * ``shown`` is the new order of the cards that are showing, read from
 * the grid after the drop. */
export function reorderInSlots<T>(
    all: readonly T[],
    shown: readonly T[],
    key: (item: T) => string,
): T[] | null {
    const allKeys = new Set(all.map(key));
    const shownKeys = new Set(shown.map(key));
    if (shownKeys.size !== shown.length) return null;
    for (const k of shownKeys) {
        if (!allKeys.has(k)) return null;
    }
    let next = 0;
    return all.map((item) => (shownKeys.has(key(item)) ? shown[next++] : item));
}

/** The new order of the shown cards after SortableJS moved one from
 * ``oldIndex`` to ``newIndex`` among them, or null for no move. */
export function movedWithin<T>(
    shown: readonly T[],
    oldIndex: number | undefined,
    newIndex: number | undefined,
): T[] | null {
    if (
        oldIndex === undefined ||
        newIndex === undefined ||
        oldIndex === newIndex ||
        oldIndex < 0 ||
        oldIndex >= shown.length ||
        newIndex < 0 ||
        newIndex >= shown.length
    ) {
        return null;
    }
    const out = [...shown];
    const [moved] = out.splice(oldIndex, 1);
    out.splice(newIndex, 0, moved);
    return out;
}
