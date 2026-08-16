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
 * COPY IS DELIBERATELY HARDCODED ENGLISH, NOT RUN THROUGH t():
 * add-popups-signpost-2-coding-plan.md's carry-forward note (section
 * 0.5, restated for signpost 3) rules the ghost tile's structure and
 * format list FINAL but the exact phrasing still pending the owner's
 * bench redline -- ship the s11 strings to the test box, do not push
 * locale-dictionary entries for them until redlined, so a stale
 * translation cannot ship ahead of the English it was translated from.
 * Once redlined, promote these five strings through `t()` and
 * `add_locale_keys`-style parity additions across all ten dictionaries
 * in one pass, the same way ir-use-fork-popup.ts's already-final copy
 * was done (Track 1 item 1).
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
import { ORIGIN_COLORS } from "./ir-origin-colors.js";

type GhostKind = "device" | "remote";

// Held-back copy -- see file header. English only, on purpose.
const COPY: Record<
    GhostKind,
    {
        title: string;
        hintFull: string;
        hintFuller: string;
        hintCompact: string;
        aria: string;
    }
> = {
    device: {
        title: "Add a Device",
        hintFull: "Drag a Wig, SmartIR, Flipper, LIRC, or Girr file here, or click to add",
        hintFuller: "Drag a code-set file or click",
        hintCompact: "Click to add, or drop a Wig, SmartIR, Flipper, LIRC, or Girr file",
        aria: "Add Device -- or drop a Wig, SmartIR, Flipper, LIRC, or Girr file",
    },
    remote: {
        title: "Add a Remote",
        hintFull: "Drag a Wig, SmartIR, Flipper, LIRC, or Girr file here, or click to add",
        hintFuller: "Drag a code-set file or click",
        hintCompact: "Click to add, or drop a Wig, SmartIR, Flipper, LIRC, or Girr file",
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
                          <span class="gt-plus">+</span>
                          <div class="gt-tile-hint">${copy.hintCompact}</div>
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
        .gt-tile-compact,
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
        .gt-tile-hint {
            font-size: 0.72rem;
            color: var(--secondary-text-color);
            font-style: italic;
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
