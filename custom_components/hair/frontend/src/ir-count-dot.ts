/**
 * Shared count-aware corner dot for action buttons.
 *
 * Renders nothing for count < 1 and a numbered 10px badge for count >= 1
 * (stretching to a pill for double digits). Every count shows its number,
 * including 1 -- a bare dot next to numbered siblings read as a different,
 * lesser indicator (owner ruling, v0.6.3 bench). Colour is the only
 * difference between the green Assign dot and the yellow Trigger dot.
 *
 * The calling button is responsible for positioning: it sets
 * ``position: relative`` and places the dot in its top-right corner via its
 * own CSS. Keeping the offset out of this component lets it ride on buttons
 * of any width.
 *
 * Usage:
 *   <ir-count-dot color="green" .count=${sig.assignment_count ?? 0}></ir-count-dot>
 *   <ir-count-dot color="yellow" .count=${triggerCount}></ir-count-dot>
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "./decorators.js";

type DotColor = "green" | "yellow";

@customElement("ir-count-dot")
export class IrCountDot extends LitElement {
    @property({ type: String }) color: DotColor = "green";
    @property({ type: Number }) count = 0;

    render() {
        if (this.count < 1) return html``;
        const isMulti = this.count >= 10;
        return html`<span
            class="dot badge ${this.color} ${isMulti ? "multi-digit" : ""}"
            ><span class="digit">${this.count}</span></span
        >`;
    }

    static styles = css`
        /* The host generates no box; each dot is absolutely positioned against
           the calling button (which sets position: relative). This keeps the
           dot out of inline flow, so a numbered badge cannot pick up a
           line-box strut and drift downward the way an inline-flex child does. */
        :host {
            display: contents;
        }
        .dot {
            position: absolute;
            pointer-events: none;
            box-shadow: 0 0 0 1.5px var(--card-background-color);
        }
        /* Numbered 10px badge for count 1..9. Anchored at -5 so the box
           centres on the button's top-right corner point. (A bare unnumbered
           dot for count 1 existed through v0.6.1; retired on the v0.6.3
           bench -- every count shows its number now.) */
        .dot.badge {
            top: -5px;
            right: -5px;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            color: #ffffff;
            /* 8px (not 7px) rasterises crisply at this size and reads as
               centred; 7px snapped to the pixel grid and looked off. */
            font-size: 8px;
            font-weight: 500;
            line-height: 1;
            /* The action buttons set letter-spacing, which inherits here and
               adds phantom space to the RIGHT of the single digit -- the flex
               box then centres [digit + that space], shoving the digit left.
               Reset it so the digit centres on its own advance. */
            letter-spacing: normal;
        }
        /* A digit glyph has no descender, so flex-centring the line box leaves
           the number riding ~0.5px above the badge's true centre. Nudge just
           the digit down half a pixel so it sits dead-centre in the circle. */
        .dot.badge .digit {
            display: block;
            transform: translateY(0.5px);
        }
        /* Double-digit stretch for count >= 10 (wider pill, pulled out a touch
           further so it clears the corner). */
        .dot.badge.multi-digit {
            right: -6px;
            min-width: 10px;
            padding: 0 3px;
            border-radius: 5px;
        }
        /* Colour variants */
        .dot.green {
            background: #2e7d32;
        }
        .dot.yellow {
            background: #b89930;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-count-dot": IrCountDot;
    }
}
