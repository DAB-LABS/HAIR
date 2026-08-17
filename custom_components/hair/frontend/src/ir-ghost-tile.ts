/**
 * The ghost tile (add-popups, signpost 3, Track 1 item 2).
 *
 * Replaces both section "+ Add" buttons in ir-device-list.ts. Renders
 * as the last cell of a section's grid: a dashed, plus-sign card that
 * opens that section's Add dialog on click, exactly as the retired
 * button did, and is also a drop target for code-set files (funnel
 * callability confirmed at Track 0 -- `api.wigsUpload()` is a plain,
 * standalone WS call, not entangled in ir-wigs.ts's own state, so drop
 * wiring builds this signpost as planned; see the commit message for
 * the full finding).
 *
 * Three layouts, chosen by the consumer (this component has no
 * Devices/Remotes knowledge of its own):
 *   - `empty=false` (default): compact -- just the plus, card-sized.
 *     The populated-grid case for both sections.
 *   - `empty=true, spanFull=false`: "fuller" -- plus, title, and a
 *     shorter hint, still card-sized. This is the Remotes case: the
 *     HAIR Triggers drawer always occupies a card, so Remotes' grid is
 *     never truly empty even when no named remote exists yet, and the
 *     tile sits card-sized next to the drawer rather than spanning.
 *   - `empty=true, spanFull=true`: "full" -- larger plus, title, and
 *     the fuller hint, `grid-column: 1 / -1`. The Devices-section-has-
 *     zero-devices case; the tile IS the section body.
 *
 * COPY: the COMPACT HINT is redlined and localized; the rest is
 * still held.
 *
 * add-popups-signpost-2-coding-plan.md's carry-forward note (section
 * 0.5, restated for signpost 3) ruled the ghost tile's structure and
 * format list FINAL but held the phrasing out of `t()` pending the
 * owner's bench redline, so that a stale translation could not ship
 * ahead of the English it was translated from. The redline arrived for
 * the compact hint alone (ghost-tile-redesign-handoff.md, owner-
 * approved 2026-08-16, punch list item 14), which is why exactly one
 * string moved: `hintCompact` now reads through `t()` in ten
 * dictionaries. The title, the two longer hints, and the aria label
 * are still awaiting their own redline and stay hardcoded English on
 * purpose -- promote them when they are ruled, not before.
 *
 * The compact hint's WORDING then went back (punch list item 22): the
 * owner saw the shortened "code-set file" phrasing live and took the
 * flip-back the handoff had named, restoring the full sentence with
 * every format in it. Two lines are allowed here now -- the one-line
 * fit that motivated the shorter string was never a requirement, only
 * a margin, and the tile still takes its height from its row. The
 * keys did not move, only their values.
 *
 * Usage:
 *   <ir-ghost-tile
 *       kind="device"
 *       .empty=${devices.length === 0}
 *       .spanFull=${devices.length === 0}
 *       @add-click=${this._add}
 *       @files-dropped=${this._onGhostTileDrop}
 *   ></ir-ghost-tile>
 *
 * Fires `add-click` (no detail) and `files-dropped` with detail
 * `{ files: File[] }` -- Track 2/3 wire the actual funnel call and the
 * drop-mode Add dialog; this component only knows tile presentation
 * and drag/drop capture.
 */
import { LitElement, html, css, unsafeCSS } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { ORIGIN_COLORS } from "./ir-origin-colors.js";

type GhostKind = "device" | "remote";

// Held-back copy -- see file header. English only, on purpose.
const COPY: Record<
    GhostKind,
    {
        title: string;
        hintFull: string;
        hintFuller: string;
        hintCompactKey: string;
        aria: string;
    }
> = {
    device: {
        title: "Add a Device",
        hintFull: "Drag a Wig, SmartIR, Flipper, LIRC, or Girr file here, or click to add",
        hintFuller: "Drag a code-set file or click",
        hintCompactKey: "ghost.hint_compact_device",
        aria: "Add Device -- or drop a Wig, SmartIR, Flipper, LIRC, or Girr file",
    },
    remote: {
        title: "Add a Remote",
        hintFull: "Drag a Wig, SmartIR, Flipper, LIRC, or Girr file here, or click to add",
        hintFuller: "Drag a code-set file or click",
        hintCompactKey: "ghost.hint_compact_remote",
        aria: "Add Remote -- or drop a Wig, SmartIR, Flipper, LIRC, or Girr file",
    },
};

@customElement("ir-ghost-tile")
export class IrGhostTile extends LitElement {
    /** Drives color (device green / remote gold) and which copy set
     * this tile shows when `empty` is true. */
    @property() public kind: GhostKind = "device";

    /** Show the title + hint copy instead of a bare plus. */
    @property({ type: Boolean }) public empty = false;

    /** Span the full grid width with the larger plus (Devices' true
     * empty-section case). Meaningless when `empty` is false. */
    @property({ type: Boolean }) public spanFull = false;

    /** Tile-only dragover lighting (owner-ruled 2026-08-15: no
     * section-wide lighting -- see the coding plan's open item 0.3). */
    @state() private _dragOver = false;

    private _onClick(): void {
        this.dispatchEvent(
            new CustomEvent("add-click", { bubbles: true, composed: true }),
        );
    }

    private _onKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            this._onClick();
        }
    }

    private _onDragOver(e: DragEvent): void {
        e.preventDefault();
        if (!this._dragOver) this._dragOver = true;
    }

    private _onDragLeave(): void {
        this._dragOver = false;
    }

    private _onDrop(e: DragEvent): void {
        e.preventDefault();
        this._dragOver = false;
        const files = Array.from(e.dataTransfer?.files ?? []);
        if (files.length === 0) return;
        this.dispatchEvent(
            new CustomEvent("files-dropped", {
                detail: { files },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const copy = COPY[this.kind];
        const classes = [
            "gt-tile",
            this.kind,
            this.empty
                ? this.spanFull
                    ? "gt-tile-full"
                    : "gt-tile-fuller"
                : "gt-tile-compact",
            this._dragOver ? "gt-dragover" : "",
        ]
            .filter(Boolean)
            .join(" ");

        return html`
            <div
                class=${classes}
                tabindex="0"
                role="button"
                aria-label=${copy.aria}
                title=${copy.aria}
                @click=${this._onClick}
                @keydown=${this._onKeydown}
                @dragover=${this._onDragOver}
                @dragleave=${this._onDragLeave}
                @drop=${this._onDrop}
            >
                ${this.empty
                    ? html`
                          <span class=${this.spanFull ? "gt-plus-lg" : "gt-plus"}
                              >+</span
                          >
                          <div class="gt-tile-title">${copy.title}</div>
                          <div class="gt-tile-hint">
                              ${this.spanFull ? copy.hintFull : copy.hintFuller}
                          </div>
                      `
                    : html`
                          <span class="gt-glyph">
                              <svg
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="1.6"
                                  aria-hidden="true"
                              >
                                  <circle cx="12" cy="12" r="10"></circle>
                                  <line x1="17.19" y1="12.13" x2="7.19" y2="12.13"></line>
                                  <line x1="12.19" y1="17.13" x2="12.19" y2="7.13"></line>
                              </svg>
                          </span>
                          <div class="gt-tile-hint">${t(copy.hintCompactKey)}</div>
                      `}
            </div>
        `;
    }

    static styles = css`
        :host {
            display: contents;
        }
        .gt-tile {
            border-radius: 8px;
            border: 1.5px dashed var(--divider-color);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            gap: 2px;
            cursor: pointer;
            transition: border-color 150ms ease, background 150ms ease,
                color 150ms ease;
            color: var(--secondary-text-color);
            padding: 12px;
        }
        /* At rest the tile is a faded grey and nothing more (punch
           list item 22). It sits in a grid of real cards carrying real
           names and counts, and at full strength it competed with them
           for attention it has not earned -- it is an invitation, not
           a thing that exists yet. One rule dims the whole tile, so
           the border, the glyph and the hint fade together and cannot
           drift apart. Opacity rather than three dimmer colors: the
           glyph already inherits currentColor and the hint already
           inherits on hover, so a single value keeps all three in step
           through every state, including whatever the theme does with
           them.

           Full strength returns on hover, focus and dragover, where
           the kind color takes over exactly as before -- item 21
           closed those states as built, and this does not touch them
           beyond restoring the tile to 1. */
        .gt-tile {
            opacity: 0.55;
            transition: border-color 150ms ease, background 150ms ease,
                color 150ms ease, opacity 150ms ease;
        }
        .gt-tile:hover,
        .gt-tile:focus-visible,
        .gt-tile.gt-dragover {
            opacity: 1;
        }
        .gt-tile:hover,
        .gt-tile:focus-visible {
            background: var(--secondary-background-color);
            outline: none;
        }
        .gt-tile.device:hover {
            border-color: ${unsafeCSS(ORIGIN_COLORS.device)};
            color: ${unsafeCSS(ORIGIN_COLORS.device)};
        }
        .gt-tile.remote:hover {
            border-color: ${unsafeCSS(ORIGIN_COLORS.remote)};
            color: ${unsafeCSS(ORIGIN_COLORS.remote)};
        }
        /* The populated-grid tile takes its height from the row,
           so it carries no floor of its own: with one, it became the
           tallest item in the Remotes grid and set the row instead of
           following it (punch list item 12, ~92px against ~72px
           cards). Devices never showed it -- those cards are taller
           than the floor was. */
        .gt-tile-fuller {
            min-height: 66px;
        }
        .gt-tile-full {
            grid-column: 1 / -1;
            min-height: 120px;
            padding: 24px;
        }
        .gt-plus {
            font-size: 20px;
            font-weight: 300;
            line-height: 1;
        }
        .gt-tile-fuller .gt-plus {
            font-size: 16px;
            font-weight: 400;
            margin-bottom: 2px;
        }
        .gt-plus-lg {
            font-size: 26px;
            font-weight: 300;
            line-height: 1;
            margin-bottom: 4px;
        }
        .gt-tile-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--primary-text-color);
        }
        /* Readability pass (punch list item 14): a 65-character
           sentence set italic at 11.5px was the actual cause of the
           owner's "hard to read", not a rendering artifact. Italic
           strokes cost disproportionately at this size, so it goes
           entirely, the size comes up, and the line box gets room to
           breathe. */
        .gt-tile-hint {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            line-height: 1.35;
        }
        /* The hint was the one part of the tile that stayed grey while
           everything around it took the kind color on hover. */
        .gt-tile:hover .gt-tile-hint,
        .gt-tile:focus-visible .gt-tile-hint {
            color: inherit;
        }
        /* plus-circle.svg is STROKE-based, like edit.svg. Rendered
           through ha-svg-icon it would come out as hairline garbage,
           because that element paints path data as fill -- the trap
           edit-button-pass.md already documents and which this pass
           does not walk into. Inline svg, stroke: currentColor, fill:
           none, so the kind-color hover carries the glyph too, for
           free. 22px against the retired 20px text character: close
           enough in footprint to sit in the same layout, heavy enough
           to read as a deliberate icon.

           Compact layout ONLY. The fuller and full layouts keep their
           text "+" through .gt-plus / .gt-plus-lg -- carrying this
           treatment into them is a separate decision the spec
           explicitly declines to assume. */
        .gt-glyph {
            width: 22px;
            height: 22px;
            flex-shrink: 0;
            display: inline-flex;
        }
        .gt-glyph svg {
            width: 22px;
            height: 22px;
        }
        .gt-tile.gt-dragover {
            border-style: solid;
        }
        .gt-tile.device.gt-dragover {
            border-color: ${unsafeCSS(ORIGIN_COLORS.device)};
            background: rgba(46, 125, 50, 0.12);
            color: ${unsafeCSS(ORIGIN_COLORS.device)};
        }
        .gt-tile.remote.gt-dragover {
            border-color: ${unsafeCSS(ORIGIN_COLORS.remote)};
            background: rgba(245, 166, 35, 0.12);
            color: ${unsafeCSS(ORIGIN_COLORS.remote)};
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-ghost-tile": IrGhostTile;
    }
}
