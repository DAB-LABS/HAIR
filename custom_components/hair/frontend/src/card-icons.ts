/**
 * The Devices tab hardware cards' icons, in solid and outline pairs
 * (ember, owner bench on VM999 with HA's real icons, 2026-10-19).
 *
 * The icon is the card's health signal. Online it is the solid icon,
 * in online green (a capture device in its chip's gold or green).
 * Offline it is the outline twin of the same icon (for the capture icon,
 * which has none, record-circle-outline), in ember, with no stroke added: a stroke on a line icon read heavy and blurry in HA's
 * ha-svg-icon. Filled online and hollow offline is the point: someone
 * who cannot tell green from ember still sees full against empty.
 *
 * Every path is @mdi/js 7.4.47, the package and version the panel's
 * other glyphs come from, copied byte for byte. Pairs:
 *   emitter   upload / upload-outline
 *   receiver  download / download-outline
 *   proxy     swap-vertical-circle / swap-vertical-circle-outline.
 *             radio-tower, the old proxy icon, has no outline twin.
 *             The up and down arrows say TX and RX in one box, in the
 *             same language as the emitter and receiver arrows, and
 *             the disc against the ring is the clearest full against
 *             empty of the candidates.
 *   capture   gesture-tap-button / record-circle-outline (owner ruling,
 *             2026-10-19). Online keeps the pointer finger on a button
 *             from BroadSniff round 2, gold when ready and green while
 *             listening. gesture-tap-button has no outline twin (nor do
 *             gesture-tap and gesture-tap-hold), so offline, or when the
 *             chip cannot listen, the icon becomes record-circle-outline
 *             in ember: the shape changes as well as the colour, and the
 *             ring reads as empty at 24px.
 *
 * Pure and import-free but for a type, so tests/test_entity_health_js.py
 * runs it under node.
 */
import type { CardGlyph } from "./entity-health.js";

export type CardIconKind = "emitter" | "receiver" | "proxy" | "capture";

export const CARD_ICONS: Record<CardIconKind, { solid: string; outline: string }> = {
    // mdi:upload / mdi:upload-outline
    emitter: {
        solid: "M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z",
        outline: "M9,10V16H15V10H19L12,3L5,10H9M12,5.8L14.2,8H13V14H11V8H9.8L12,5.8M19,18H5V20H19V18Z",
    },
    // mdi:download / mdi:download-outline
    receiver: {
        solid: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
        outline: "M13,5V11H14.17L12,13.17L9.83,11H11V5H13M15,3H9V9H5L12,16L19,9H15V3M19,18H5V20H19V18Z",
    },
    // mdi:swap-vertical-circle / mdi:swap-vertical-circle-outline
    proxy: {
        solid: "M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M6.5 9L10 5.5L13.5 9H11V13H9V9H6.5M17.5 15L14 18.5L10.5 15H13V11H15V15H17.5Z",
        outline: "M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M12 20C7.59 20 4 16.41 4 12S7.59 4 12 4 20 7.59 20 12 16.41 20 12 20M6.5 9L10 5.5L13.5 9H11V13H9V9H6.5M17.5 15L14 18.5L10.5 15H13V11H15V15H17.5Z",
    },
    // mdi:gesture-tap-button / mdi:record-circle-outline (owner ruling)
    capture: {
        solid: "M13 5C15.21 5 17 6.79 17 9C17 10.5 16.2 11.77 15 12.46V11.24C15.61 10.69 16 9.89 16 9C16 7.34 14.66 6 13 6S10 7.34 10 9C10 9.89 10.39 10.69 11 11.24V12.46C9.8 11.77 9 10.5 9 9C9 6.79 10.79 5 13 5M20 20.5C19.97 21.32 19.32 21.97 18.5 22H13C12.62 22 12.26 21.85 12 21.57L8 17.37L8.74 16.6C8.93 16.39 9.2 16.28 9.5 16.28H9.7L12 18V9C12 8.45 12.45 8 13 8S14 8.45 14 9V13.47L15.21 13.6L19.15 15.79C19.68 16.03 20 16.56 20 17.14V20.5M20 2H4C2.9 2 2 2.9 2 4V12C2 13.11 2.9 14 4 14H8V12L4 12L4 4H20L20 12H18V14H20V13.96L20.04 14C21.13 14 22 13.09 22 12V4C22 2.9 21.11 2 20 2Z",
        outline: "M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9Z",
    },
};

/** The path for a card: solid while it answers (online, ready,
 *  listening), the outline twin while it is offline. A card with no
 *  infrared entity ("plain", an ESPHome event bridge) keeps the outline
 *  it has always had, in its grey: it has no health to show. */
export function cardIconPath(kind: CardIconKind, glyph: CardGlyph): string {
    const pair = CARD_ICONS[kind];
    return glyph === "offline" || glyph === "plain" ? pair.outline : pair.solid;
}
