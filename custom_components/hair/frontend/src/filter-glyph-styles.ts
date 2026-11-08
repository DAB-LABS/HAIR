/**
 * The filter glyphs' look, one for every place they appear: the
 * Sniffer's receiver row (infrared, radio, hidden) and the homepage's
 * Devices and Remotes headers (infrared, radio; item 14). One filter
 * control looks the same everywhere.
 */
import { css } from "lit";

export const filterGlyphStyles = css`
    /* Lit when that kind is shown, grey when it is filtered out:
       both parts of a glyph, dot and lines. Lit is the remote cards'
       stroke blue, the theme blue at 30% (owner, 20:54 PT). */
    .show-glyph {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 24px;
        padding: 0;
        border: none;
        border-radius: 12px;
        background: none;
        /* Greyed by color, not opacity, so the hidden dot inside
           stays full blue on an unlit glyph. */
        color: color-mix(in srgb, var(--secondary-text-color) 60%, transparent);
        cursor: pointer;
        --hair-proto-source: currentColor;
        --hair-proto-signal: currentColor;
    }
    .show-glyph .hair-proto {
        --hair-proto-source: currentColor;
        --hair-proto-signal: currentColor;
    }
    .show-glyph ha-svg-icon {
        --mdc-icon-size: 18px;
    }
    .show-glyph.on {
        color: rgba(33, 150, 243, 0.3);
        color: color-mix(in srgb, var(--primary-color) 30%, transparent);
    }
    .show-glyph:hover {
        background: color-mix(in srgb, var(--primary-color) 10%, transparent);
    }
    .show-glyph:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 1px;
    }
`;
