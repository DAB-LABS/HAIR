/**
 * HAIR's chip and dot colours, in one place (chip and dot audit,
 * owner 2026-11-14 19:15 PT: gertrude-2026-11-14-chip-audit.md).
 *
 * Every health dot, picked pill and capture state in the panel reads
 * its colour from here, through the custom properties hairTokens
 * (ir-header-chip-styles.ts) declares on the panel host. The values
 * are the ones the panel already showed; what this file adds is that
 * each meaning has one name and one value.
 *
 *   --hair-online      a health dot that is picked: reachable, in use
 *   --hair-dull-gray   what an unpicked dot is mixed toward
 *   --hair-ember       offline, danger
 *   --hair-grey        a dot with no health known, at rest
 *   --hair-picked      a picked pill's border and wash; a live window
 *   --hair-deep-green  counts and hardware badges
 *   --hair-gold        waiting to be pressed: a capture device ready
 *
 * The health values stay defined in entity-health.ts, where the
 * health rule lives; this file re-exports them so it is the whole
 * palette.
 *
 * THE DOT RULE (owner, 2026-11-14, as ruled for Kobe's dots and kept
 * in the audit): bright means picked. A picked chip's dot is its full
 * health colour, with a glow while online; an unpicked chip's, or a
 * row's with nothing to pick, is the same colour dulled toward gray.
 * Hollow always means offline, and offline is always ember, so the
 * two health states differ in shape as well as colour. dotClass below
 * is that rule, for surfaces that draw a dot outside a chip.
 *
 * Pure and import-free but for the health constants, so
 * tests/test_entity_health_js.py runs it under node.
 */
export { DULL_GRAY, EMBER, EMBER_RGB, ONLINE_GREEN } from "./entity-health.js";

/** A dot with no health to show (no Home Assistant object yet), or a
 *  chip at rest. */
export const REST_GREY = "#4d5359";
/** A picked pill's tone, and a capture window that is open: the
 *  header rows' green, now every picker's (owner, 2026-11-14). */
export const PICKED_GREEN = "#43a047";
/** Counts and hardware badges: CMD, IR-TX and the count dot. */
export const DEEP_GREEN = "#2e7d32";
/** Waiting to be pressed: a capture device that is ready, and HAIR's
 *  Remote and trigger origin. */
export const HAIR_GOLD = "#f5a623";

/** The S/L diamonds (owner, 2026-11-15 13:53 PT): long in HA's primary
 *  colour, short in its warning colour, as the infrared rows have always
 *  drawn them. Radio uses the same two for now; a radio variant later is
 *  a change here. */
export const DIAMOND_LONG = "var(--primary-color)";
export const DIAMOND_SHORT = "var(--warning-color, #ff9800)";

/** The class a health dot wears outside a picker chip:
 *    "online" / "offline"                 dull: unpicked, or no picking
 *    "online bright" / "offline bright"   full: the one in use
 *  A chip that is picked gets its brightness from the chip's own
 *  `.on` class instead (healthChipClass). */
export function dotClass(online: boolean, bright = false): string {
    const health = online ? "online" : "offline";
    return bright ? `${health} bright` : health;
}
