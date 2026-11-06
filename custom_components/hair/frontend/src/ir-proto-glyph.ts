/**
 * The protocol glyphs (docs/internal/plans/HAIR IR RF Protocol Glyphs
 * Spec.md, owner 2026-11-04; placement for RF hear round 1 by the
 * owner's ruling of 2026-11-06): a grey source dot with blue signal
 * lines, straight rays for infrared and arcs for radio.
 *
 * This round they go on the Devices tab's HAIR Device and Remote cards
 * (right of the pill row, 16px, both when a device holds both media,
 * infrared first) and in the Sniffer's remote rows (the drag-handle
 * slot, swapping to the grip on hover or focus). Not on hardware cards
 * and not on Listen pills, which spell the medium in their badges.
 *
 * Fixed colours, HAIR's palette, not the theme's primary (ruling Q10):
 * two custom properties, so one change restyles every glyph. A medium
 * HAIR does not know draws the grey dot alone, "Protocol unknown": a
 * defensive fallback, since every row HAIR writes has a medium.
 */
import { css, html, svg, unsafeCSS } from "lit";
import { t } from "./localize.js";
import type { Medium } from "./types.js";

export const PROTO_SOURCE = "#8b8f96";
export const PROTO_SIGNAL = "#03a9f4";

const SOURCE = svg`<circle class="src" cx="5" cy="12" r="2.5"/>`;
const IR_SIGNAL = svg`<path class="sig" d="M9.5 8h8.5M9.5 12h11.5M9.5 16h8.5"/>`;
const RF_SIGNAL = svg`<path class="sig" d="M9 9A4.24 4.24 0 0 1 9 15M12 6A8.49 8.49 0 0 1 12 18M15 3A12.73 12.73 0 0 1 15 21"/>`;

/** The label a glyph carries: "IR", "RF", "RF 433.92 MHz", or
 *  "Protocol unknown". */
export function protoLabel(medium: Medium | null | undefined, band?: string | null): string {
    if (medium === "ir") return t("proto.ir");
    if (medium === "rf") return band ? t("proto.rf_band", { band }) : t("proto.rf");
    return t("proto.unknown");
}

/** One glyph, as an image with its label as the accessible name and
 *  the hover tooltip. */
export function renderProtoGlyph(
    medium: Medium | null | undefined,
    size = 16,
    band?: string | null,
) {
    const label = protoLabel(medium, band);
    return html`<svg
        class="hair-proto"
        viewBox="0 0 24 24"
        width=${size}
        height=${size}
        role="img"
        aria-label=${label}
    >
        <title>${label}</title>
        ${SOURCE}${medium === "ir" ? IR_SIGNAL : medium === "rf" ? RF_SIGNAL : ""}
    </svg>`;
}

export const protoGlyphStyles = css`
    .hair-proto {
        --hair-proto-source: ${unsafeCSS(PROTO_SOURCE)};
        --hair-proto-signal: ${unsafeCSS(PROTO_SIGNAL)};
        flex: none;
        fill: none;
        stroke-width: 1.75;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .hair-proto .src {
        fill: var(--hair-proto-source);
    }
    .hair-proto .sig {
        stroke: var(--hair-proto-signal);
    }
`;
