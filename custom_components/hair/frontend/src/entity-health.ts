/**
 * Chip health: is this emitter or receiver online (ember, 2026-10-19).
 *
 * Every emitter and receiver chip shows two things at all times:
 * selection on the pill, health on the dot. This file answers the
 * health half, once, for every surface that draws one: the device
 * header's Emitters row, the Remote header's Receivers row, the emitter
 * and receiver pickers, the Sniffer's Listen chips and the Devices
 * tab's hardware cards. Each reads `hass.states` on every render, so a
 * device coming back turns green without a reload.
 *
 * The rule (owner, 2026-10-19):
 *   - `unavailable` is offline. HA sets it when it cannot reach the
 *     device, which is what the IR Mate on a switched-off TV's USB
 *     port looked like.
 *   - A missing state is offline. An entity HA has no state for is
 *     not answering either.
 *   - `unknown` is online. An emitter's state is its last-send
 *     timestamp, unknown until the first send, so a brand-new blaster
 *     is unproven, not down (GH #83).
 *
 * The colours are defined here and nowhere else in the health code.
 * Ember is HAIR's warning and danger colour; the online green is the
 * picker's old "on" dot. ir-header-chip-styles.ts turns them into the
 * `--hair-ember`, `--hair-ember-rgb` and `--hair-online` custom
 * properties on the panel host and uses these values only as the
 * fallback, so a chip mounted outside the panel keeps its colours.
 *
 * Pure and import-free, so tests/test_entity_health_js.py runs it under
 * node.
 */

export const EMBER = "#e65100";
export const EMBER_RGB = "230, 81, 0";
export const ONLINE_GREEN = "#6cbf78";

type States = Record<string, { state?: string } | undefined> | undefined;

/** True when HA can reach the entity: it has a state and that state
 *  is not `unavailable`. `unknown` counts as online. */
export function isEntityOnline(states: States, entityId: string): boolean {
    const st = states?.[entityId];
    if (!st) return false;
    return st.state !== "unavailable";
}

/** The class a health dot wears. */
export function healthDotClass(online: boolean): "online" | "offline" {
    return online ? "online" : "offline";
}

/** The class a selectable emitter or receiver chip wears:
 *    not selected       -> ""          (grey pill)
 *    selected, online   -> "on"        (tone pill, glow)
 *    selected, offline  -> "on down"   (ember edge and wash, no glow)
 *  The dot's own class comes from healthDotClass. */
export function healthChipClass(selected: boolean, online: boolean): string {
    if (!selected) return "";
    return online ? "on" : "on down";
}

/** What the tooltip and the accessible name say after the name:
 *  "online, selected", "offline, not selected" and so on. The word
 *  stays off the chip itself. `t` is localize.ts's, passed in so this
 *  file keeps no imports. */
export function healthPhrase(
    online: boolean,
    selected: boolean,
    t: (key: string) => string,
): string {
    return `${t(online ? "common.online" : "common.offline")}, ${t(
        selected ? "common.selected" : "common.not_selected",
    )}`;
}

/** The `hass.entities` shape this file reads. */
type Entities = Record<string, { device_id?: string | null } | undefined> | undefined;

/** The `infrared.*` entities the entity registry puts on a device. */
export function infraredEntitiesOf(entities: Entities, deviceId: string | null | undefined): string[] {
    if (!deviceId) return [];
    const out: string[] = [];
    for (const [entityId, entry] of Object.entries(entities ?? {})) {
        if (entityId.startsWith("infrared.") && entry?.device_id === deviceId) {
            out.push(entityId);
        }
    }
    return out;
}

/** A hardware card's health, as a whole. (Each badge on the card
 *  follows its own entity through isEntityOnline; this decides only
 *  the card's ember edge, ember glyph and "Offline" corner.)
 *    "none"    -> the device has no infrared entity: never offline.
 *                 The ESPHome event bridges (RX-BRIDGE) are this case.
 *    "online"  -> at least one of its infrared entities is online.
 *    "offline" -> it has infrared entities and every one is offline.
 *  `fallbackIds` covers a card whose entity has no device in the
 *  registry: the card's own entities stand in for the device's. */
export function cardHealth(
    hass: { states?: States; entities?: Entities } | undefined,
    deviceId: string | null | undefined,
    fallbackIds: string[] = [],
): "none" | "online" | "offline" {
    let ids = infraredEntitiesOf(hass?.entities, deviceId);
    if (ids.length === 0) ids = fallbackIds.filter((id) => id.startsWith("infrared."));
    if (ids.length === 0) return "none";
    return ids.some((id) => isEntityOnline(hass?.states, id)) ? "online" : "offline";
}

/** The health of the part of the hardware a card's icon follows (owner
 *  ruling, 2026-10-19): an Emitters card its emitter, a Receivers card
 *  its receiver, a Proxies card every part, offline if any one is down.
 *  "none" when the card has no such entity (an ESPHome event bridge),
 *  "online" when every one answers, "offline" otherwise. The card's
 *  ember border and OFFLINE corner do not use this: they stay with
 *  cardHealth, every infrared entity on the device. */
export function partsHealth(
    states: States,
    ids: (string | null | undefined)[],
): "none" | "online" | "offline" {
    const parts = ids.filter((id): id is string => typeof id === "string" && id !== "");
    if (parts.length === 0) return "none";
    return parts.every((id) => isEntityOnline(states, id)) ? "online" : "offline";
}

/** What a hardware card's glyph shows (owner bench, 2026-10-19): the
 *  glyph is the card's health signal.
 *    "plain"     -> no infrared entity (RX-BRIDGE): today's outline icon
 *                   in today's grey.
 *    "online"    -> the solid icon, in online green.
 *    "ready"     -> a capture device whose chip is ready: its gold.
 *    "listening" -> a capture device whose chip is listening: its green.
 *    "offline"   -> the icon's outline twin (card-icons.ts), in ember.
 *                   For the whole card being offline, and for a capture
 *                   device whose chip cannot listen (it follows its
 *                   chip).
 *  `health` is partsHealth for the part the icon follows; `capture` is
 *  null for a card that is not a capture device. */
export type CardGlyph = "plain" | "online" | "ready" | "listening" | "offline";

export function cardGlyph(
    health: "none" | "online" | "offline",
    capture: { online: boolean; listening: boolean } | null,
): CardGlyph {
    if (health === "none") return "plain";
    if (health === "offline") return "offline";
    if (capture) {
        if (!capture.online) return "offline";
        return capture.listening ? "listening" : "ready";
    }
    return "online";
}
