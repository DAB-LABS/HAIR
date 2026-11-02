/**
 * A Device's state source: the rules the settings dialog follows.
 *
 * A source is either a power sensor in watts, classified against two
 * thresholds, or an on/off entity read by its state (models.py
 * ON_OFF_DOMAINS: on and home are on, off and not_home are off). This
 * module decides which entities the picker offers, in which group, what
 * a search leaves, how the closed field and its floating list respond
 * to clicks and keys, where the list goes, how long the settle time may
 * be, and what a save sends; the dialog only renders it. It is plain
 * functions over plain shapes so a node test can run it.
 */

/** Mirrors models.py ON_OFF_DOMAINS; a test checks the two match. */
export const ON_OFF_DOMAINS: readonly string[] = [
    "binary_sensor",
    "switch",
    "input_boolean",
    "device_tracker",
];

/** Mirror models.py MAX_POWER_SETTLE_S and MAX_ON_OFF_SETTLE_S; a test
 * checks they match. The backend is the one that enforces them. */
export const MAX_POWER_SETTLE_S = 120;
export const MAX_ON_OFF_SETTLE_S = 600;

/** What the settle field is set to when a device tracker is picked: a
 * presence or network tracker typically takes minutes to notice a
 * device switched off. The field stays editable. */
export const TRACKER_SETTLE_PRESET_S = 300;

export interface SourceStateShape {
    state?: string;
    attributes: {
        friendly_name?: string;
        device_class?: string;
        unit_of_measurement?: string;
    };
}

export interface SourceCandidate {
    entityId: string;
    name: string;
}

export interface SourceGroups {
    power: SourceCandidate[];
    onOff: SourceCandidate[];
}

export function isOnOffEntity(entityId: string | null | undefined): boolean {
    if (!entityId) return false;
    const dot = entityId.indexOf(".");
    if (dot <= 0) return false;
    return ON_OFF_DOMAINS.includes(entityId.slice(0, dot));
}

/** The longest settle time a Device with this source accepts. */
export function settleCapFor(sensorId: string | null | undefined): number {
    return isOnOffEntity(sensorId) ? MAX_ON_OFF_SETTLE_S : MAX_POWER_SETTLE_S;
}

/**
 * The settle field after a new source is picked, from what it holds.
 * A device tracker presets TRACKER_SETTLE_PRESET_S. Any other source
 * keeps the field, brought down to that source's cap if it is over it,
 * so the field never shows a value the save would not send.
 */
export function settleOnPick(sensorId: string, current: string): string {
    if (sensorId.startsWith("device_tracker.")) {
        return String(TRACKER_SETTLE_PRESET_S);
    }
    const value = parseFloat(current);
    const cap = settleCapFor(sensorId);
    if (!Number.isNaN(value) && value > cap) return String(cap);
    return current;
}

function looksLikePower(entityId: string, st: SourceStateShape): boolean {
    if (!entityId.startsWith("sensor.")) return false;
    const unit = st.attributes.unit_of_measurement;
    return (
        st.attributes.device_class === "power" || unit === "W" || unit === "kW"
    );
}

/**
 * The picker's two groups, each sorted by name.
 *
 * Power sensors are the `sensor.` entities that look like power
 * (device_class power, or a W/kW unit). On/off entities are every entity
 * in the four domains, except HAIR's own (registry platform "hair"):
 * their state is what HAIR assumed, so as a source they would only
 * confirm themselves. The saved source always stays selectable, in the
 * group its domain belongs to, so reopening the dialog never drops it.
 */
export function stateSourceCandidates(
    states: Record<string, SourceStateShape>,
    entities: Record<string, { platform?: string } | undefined>,
    current: string | null,
): SourceGroups {
    const power: SourceCandidate[] = [];
    const onOff: SourceCandidate[] = [];
    for (const [entityId, st] of Object.entries(states)) {
        const name = st.attributes.friendly_name ?? entityId;
        if (looksLikePower(entityId, st)) {
            power.push({ entityId, name });
        } else if (
            isOnOffEntity(entityId) &&
            entities[entityId]?.platform !== "hair"
        ) {
            onOff.push({ entityId, name });
        }
    }
    if (
        current &&
        !power.some((c) => c.entityId === current) &&
        !onOff.some((c) => c.entityId === current)
    ) {
        const entry = {
            entityId: current,
            name: states[current]?.attributes.friendly_name ?? current,
        };
        (isOnOffEntity(current) ? onOff : power).push(entry);
    }
    const byName = (a: SourceCandidate, b: SourceCandidate) =>
        a.name.localeCompare(b.name) || a.entityId.localeCompare(b.entityId);
    power.sort(byName);
    onOff.sort(byName);
    return { power, onOff };
}

/**
 * The picker's groups narrowed to a search, matching the query on the
 * name or the entity id, ignoring case: the same rule as the RX-CAPTURE
 * switch search (ir-listen-state.ts pickerEntities). An empty query
 * leaves both groups whole. The current source stays in its group
 * whatever the query, so a search never hides what is in use; order is
 * kept.
 */
export function filterSourceGroups(
    groups: SourceGroups,
    query: string,
    current: string | null,
): SourceGroups {
    const q = query.trim().toLocaleLowerCase();
    if (!q) return groups;
    const keep = (c: SourceCandidate) =>
        c.entityId === current ||
        c.name.toLocaleLowerCase().includes(q) ||
        c.entityId.toLocaleLowerCase().includes(q);
    return { power: groups.power.filter(keep), onOff: groups.onOff.filter(keep) };
}

/** The four power fields a save sends for the chosen source. */
export function stateSourcePatch(
    sensorId: string | null,
    offBelow: string,
    onAbove: string,
    settle: number | null,
): {
    power_sensor_entity_id: string | null;
    power_off_below_w: number | null;
    power_on_above_w: number | null;
    power_settle_s: number | null;
} {
    if (!sensorId) {
        return {
            power_sensor_entity_id: null,
            power_off_below_w: null,
            power_on_above_w: null,
            power_settle_s: null,
        };
    }
    const onOff = isOnOffEntity(sensorId);
    return {
        power_sensor_entity_id: sensorId,
        power_off_below_w: onOff ? null : parseFloat(offBelow),
        power_on_above_w: onOff ? null : parseFloat(onAbove),
        power_settle_s: settle,
    };
}

// ---------------------------------------------------------------------------
// The picker's open and closed states
// ---------------------------------------------------------------------------

/**
 * The closed field and its floating list, as a state machine the dialog
 * drives: the dialog turns DOM events into PickerEvents, renders the
 * PickerState, and carries out what a PickerStep asks (apply a pick,
 * put focus back on the field, cancel the key's default). A node test
 * runs it without a DOM.
 *
 * `active` is the option the arrow keys are on, an entity id or "" for
 * None. Headings are not options, so they are never active.
 */
export interface PickerState {
    open: boolean;
    query: string;
    active: string | null;
}

export const PICKER_CLOSED: PickerState = { open: false, query: "", active: null };

export type PickerEvent =
    | { kind: "field-click" }
    | { kind: "field-key"; key: string }
    | { kind: "panel-key"; key: string }
    | { kind: "outside" }
    | { kind: "query"; value: string }
    | { kind: "row"; entityId: string };

export interface PickerStep {
    state: PickerState;
    /** The source to apply ("" is None), when the step is a pick. */
    pick?: string;
    /** Put focus back on the closed field. */
    focusField?: boolean;
    /** Move focus into the open panel's search. */
    focusSearch?: boolean;
    /** The key did something here: cancel its default and stop it, so
     * Escape closes the list and not the dialog around it. */
    handled?: boolean;
}

/** The options in the list, in order: None, the power sensors, then the
 * on/off entities. */
export function pickerOptions(shown: SourceGroups): string[] {
    return [
        "",
        ...shown.power.map((c) => c.entityId),
        ...shown.onOff.map((c) => c.entityId),
    ];
}

/** The keys that open the closed field. */
export const OPEN_KEYS: readonly string[] = ["Enter", " ", "ArrowDown"];

/**
 * One step of the picker. `chosen` is the current source ("" for None).
 * `optionsFor(query)` is the options the list shows for a query, None
 * and the chosen source included; `optionsFor(query, false)` leaves
 * the chosen source out unless it matches, so it holds only what the
 * query found.
 *
 * Typing moves the active option to the first entity the query found,
 * so Enter picks it; an empty query puts it back on the chosen source.
 */
export function pickerStep(
    state: PickerState,
    event: PickerEvent,
    chosen: string,
    optionsFor: (query: string, keepChosen?: boolean) => string[],
): PickerStep {
    const close = (extra: Partial<PickerStep> = {}): PickerStep => ({
        state: PICKER_CLOSED,
        focusField: true,
        ...extra,
    });
    if (!state.open) {
        const opens =
            event.kind === "field-click" ||
            (event.kind === "field-key" && OPEN_KEYS.includes(event.key));
        if (!opens) return { state };
        // The search clears each time the list opens.
        return {
            state: { open: true, query: "", active: chosen },
            focusSearch: true,
            handled: event.kind === "field-key",
        };
    }
    switch (event.kind) {
        case "field-click":
            return close();
        case "outside":
            return close();
        case "row":
            return close({ pick: event.entityId });
        case "query": {
            const found = event.value.trim()
                ? optionsFor(event.value, false).filter((id) => id !== "")
                : [];
            const active = found[0] ?? chosen;
            return { state: { ...state, query: event.value, active } };
        }
        case "field-key":
        case "panel-key": {
            const key = event.key;
            if (key === "Escape" || key === "Tab") {
                return close({ handled: true });
            }
            if (key === "Enter") {
                if (state.active === null) return { state, handled: true };
                return close({ pick: state.active, handled: true });
            }
            const options = optionsFor(state.query);
            const at = state.active === null ? -1 : options.indexOf(state.active);
            let next: number;
            if (key === "ArrowDown") next = Math.min(at + 1, options.length - 1);
            else if (key === "ArrowUp") next = Math.max(at - 1, 0);
            else if (key === "Home") next = 0;
            else if (key === "End") next = options.length - 1;
            else return { state };
            return {
                state: { ...state, active: options[next] ?? null },
                handled: true,
            };
        }
    }
    return { state };
}

/** Where the floating list goes, from the field's box and the window. */
export interface PanelPlacement {
    left: number;
    width: number;
    /** Opens upward: placed by `bottom`, its distance from the window's
     * bottom edge; otherwise by `top`. */
    up: boolean;
    top: number;
    bottom: number;
    maxHeight: number;
}

/** The list's ceiling, search box included. */
export const PANEL_MAX_HEIGHT = 320;
/** The gap between the field and the list, and the list and the window
 * edge. */
export const PANEL_GAP = 4;
export const PANEL_EDGE = 8;

/**
 * Under the field, or over it when there is not room for the whole list
 * below and there is more room above. Never wider than the window, never
 * past its edges.
 */
export function placePanel(
    field: { top: number; bottom: number; left: number; width: number },
    viewport: { width: number; height: number },
): PanelPlacement {
    const below = viewport.height - field.bottom - PANEL_GAP - PANEL_EDGE;
    const above = field.top - PANEL_GAP - PANEL_EDGE;
    const up = below < PANEL_MAX_HEIGHT && above > below;
    const width = Math.min(field.width, viewport.width - 2 * PANEL_EDGE);
    const left = Math.max(
        PANEL_EDGE,
        Math.min(field.left, viewport.width - PANEL_EDGE - width),
    );
    return {
        left,
        width,
        up,
        top: field.bottom + PANEL_GAP,
        bottom: viewport.height - field.top + PANEL_GAP,
        maxHeight: Math.max(0, Math.min(PANEL_MAX_HEIGHT, up ? above : below)),
    };
}
