/**
 * The ghost tile (add-popups, signpost 3, Track 1 item 2).
 *
 * Replaces both section "+ Add" buttons in ir-device-list.ts. Renders
 * as the last cell of a section's grid: a dashed card whose plus button
 * opens that section's Add dialog, exactly as the retired button did,
 * whose folder button imports a file (see TWO BUTTONS below), and
 * which is also a drop target for code-set files (funnel
 * callability confirmed at Track 0 -- `api.wigsUpload()` is a plain,
 * standalone WS call, not entangled in ir-wigs.ts's own state, so drop
 * wiring builds this signpost as planned; see the commit message for
 * the full finding).
 *
 * Two layouts:
 *   - compact (default): the two buttons and the compact hint,
 *     card-sized. The populated-grid case, and the ONLY layout Remotes
 *     ever uses.
 *   - full: larger buttons, title and the long hint, `grid-column: 1 /
 *     -1`. The Devices-section-has-zero-devices case, asked for with
 *     `empty=true`; the tile IS the section body.
 *
 * The full layout is Devices-only, and the component now knows that
 * rather than trusting its consumer with it: a Remotes tile handed
 * `empty` renders compact. Remotes has no full-layout copy to render,
 * so the alternative would be a tile with a blank title, and the one
 * caller that could reach it is a future edit to ir-device-list.ts.
 *
 * THERE WAS A THIRD, AND IT IS GONE (0.10.1 item 6). A "fuller" middle
 * layout existed for Remotes-with-no-named-remote, and it was the wrong
 * shape for that case: the HAIR Triggers drawer always occupies a card,
 * so the Remotes grid is never truly empty and the tile always has a
 * neighbour to sit beside. Worse, it was the one layout a user could
 * reach whose copy had never been redlined, so a fresh install read
 * held English ("+ Add a Remote / Drag a code-set file or click") until
 * the first Remote existed and it flipped to the redlined compact hint.
 * Remotes is compact always; `spanFull` retired with the layout, since
 * Devices only ever passed it together with `empty`.
 *
 * COPY: the COMPACT HINT is redlined and localized; the Devices full
 * layout's title and hint are still held. Remotes carries neither,
 * because it has no layout that could show them.
 *
 * add-popups-signpost-2-coding-plan.md's carry-forward note (section
 * 0.5, restated for signpost 3) ruled the ghost tile's structure and
 * format list FINAL but held the phrasing out of `t()` pending the
 * owner's bench redline, so that a stale translation could not ship
 * ahead of the English it was translated from. The redline arrived for
 * the compact hint alone (ghost-tile-redesign-handoff.md, owner-
 * approved 2026-08-16, punch list item 14), which is why exactly one
 * string moved: `hintCompact` now reads through `t()` in ten
 * dictionaries. The title, the long hint and the aria label are still
 * awaiting their own redline and stay hardcoded English on purpose --
 * promote them when they are ruled, not before. The zero-devices case
 * that shows them is rarer than the Remotes one ever was: a HAIR
 * install with no Devices at all.
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
 *       @add-click=${this._add}
 *       @files-dropped=${this._onGhostTileDrop}
 *   ></ir-ghost-tile>
 *
 * Fires `add-click` (no detail) and `files-dropped` with detail
 * `{ files: File[] }` -- Track 2/3 wire the actual funnel call and the
 * drop-mode Add dialog; this component only knows tile presentation
 * and drag/drop capture.
 *
 * TWO BUTTONS, NOT A BUTTON (owner, 2026-11-13). The whole tile used to
 * be the control: a click anywhere opened the Add dialog, and the only
 * way to import from the home page was to drag a file onto it, which a
 * phone has nothing to drag from. Now the tile is a plain group and a
 * drop target, and two square buttons sit where the round plus was:
 *   - plus: `add-click`, exactly what the tile's click did;
 *   - folder: the shared file picker (file-pick.ts, the Closet's own
 *     Browse), then `files-dropped` with the chosen file. The same
 *     event a drop fires, so the host's drop path does the rest: the
 *     busy state, the upload, the supersession offer and the dialog.
 * A click on the rest of the tile does nothing (ruled). A drop anywhere
 * on it, buttons included, still imports. The tile still brightens on
 * hover so the buttons are easy to find; only the buttons take the
 * pointer. The tile holds no state while the dialog is open, so a
 * cancelled pick leaves nothing behind.
 */
import { LitElement, html, css, unsafeCSS } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { ORIGIN_COLORS } from "./ir-origin-colors.js";
import { pickOneFile } from "./file-pick.js";

type GhostKind = "device" | "remote";

// Held-back copy -- see file header. English only, on purpose.
// `title` and `hintFull` belong to the full layout, which only the
// Devices section can reach, so only Devices declares them and the
// types say so. The compact hint every user sees is localized and read
// through t() below.
const COPY: Record<
    GhostKind,
    {
        title?: string;
        hintFull?: string;
        hintCompactKey: string;
        aria: string;
    }
> = {
    device: {
        title: "Add a Device",
        hintFull: "Drag a Wig, SmartIR, Flipper, LIRC, Girr, Harmony, Global Cache, Tasmota, or irdb file here, or use the buttons above",
        hintCompactKey: "ghost.hint_compact_device",
        aria: "Add Device -- or drop a Wig, SmartIR, Flipper, LIRC, Girr, Harmony, Global Cache, Tasmota, or irdb file",
    },
    remote: {
        hintCompactKey: "ghost.hint_compact_remote",
        aria: "Add Remote -- or drop a Wig, SmartIR, Flipper, LIRC, Girr, Harmony, Global Cache, Tasmota, or irdb file",
    },
};

@customElement("ir-ghost-tile")
export class IrGhostTile extends LitElement {
    /** Drives color (device green / remote gold) and which copy set
     * this tile shows when `empty` is true. */
    @property() public kind: GhostKind = "device";

    /** The section has nothing in it: span the grid and show the title
     * and long hint. Devices only, and enforced here rather than
     * assumed -- Remotes never sets this, since its grid always holds
     * the HAIR Triggers drawer, and it renders compact if it ever
     * does. */
    @property({ type: Boolean }) public empty = false;

    /** A drop is being read and filed. The tile says so from the
     * moment the file lands (issue 6): the import parses, combs,
     * checks supersession and writes before the create dialog can
     * open, and with no feedback in between the owner doubted the
     * drop had registered at all. */
    @property({ type: Boolean }) public busy = false;

    /** Tile-only dragover lighting (owner-ruled 2026-08-15: no
     * section-wide lighting -- see the coding plan's open item 0.3). */
    @state() private _dragOver = false;

    /** The folder was used, so when the import it started ends (busy
     * goes back to false) focus returns to the folder. The busy render
     * has no buttons, and without this a keyboard or screen-reader
     * user would be dropped at the top of the page. */
    private _refocusFolder = false;

    protected updated(changed: Map<string, unknown>): void {
        if (
            changed.has("busy") &&
            changed.get("busy") === true &&
            !this.busy &&
            this._refocusFolder
        ) {
            this._refocusFolder = false;
            this.renderRoot
                .querySelector<HTMLButtonElement>(".gt-folder")
                ?.focus();
        }
    }

    private _onAdd(): void {
        this.dispatchEvent(
            new CustomEvent("add-click", { bubbles: true, composed: true }),
        );
    }

    /** The folder: pick one file and hand it on exactly as a drop
     * would. Nothing on the tile waits for the dialog, so a cancel
     * (which some browsers never report) changes nothing. */
    private async _onFolder(): Promise<void> {
        const file = await pickOneFile();
        if (!file) return;
        this._refocusFolder = true;
        this.dispatchEvent(
            new CustomEvent("files-dropped", {
                detail: { files: [file] },
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** The plus and the folder, side by side. Native buttons, so Tab
     * reaches each and Enter or Space works without a key handler. */
    private _renderButtons(large: boolean) {
        const addLabel = t(
            this.kind === "device" ? "adddev.heading" : "addtr.heading",
        );
        const browseLabel = t("wigs.drop.browse");
        return html`
            <div class="gt-buttons ${large ? "gt-buttons-lg" : ""}">
                <button
                    type="button"
                    class="gt-btn gt-add"
                    title=${addLabel}
                    aria-label=${addLabel}
                    @click=${this._onAdd}
                >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                </button>
                <button
                    type="button"
                    class="gt-btn gt-folder"
                    title=${browseLabel}
                    aria-label=${browseLabel}
                    @click=${this._onFolder}
                >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path
                            d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"
                        ></path>
                    </svg>
                </button>
            </div>
        `;
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
        // Devices only, whatever the consumer passes: Remotes has no
        // full-layout copy, so the fallback is the layout it does have.
        const full = this.empty && this.kind === "device";
        const classes = [
            "gt-tile",
            this.kind,
            full ? "gt-tile-full" : "gt-tile-compact",
            this._dragOver && !this.busy ? "gt-dragover" : "",
            this.busy ? "gt-busy" : "",
        ]
            .filter(Boolean)
            .join(" ");

        // Reading a dropped file: the tile says so and accepts
        // nothing else until it is done -- no click, no second drop
        // landing on top of the first (F10).
        if (this.busy) {
            return html`
                <div class=${classes} aria-busy="true" aria-label=${copy.aria}>
                    <span class="gt-spinner" aria-hidden="true"></span>
                    <div class="gt-tile-hint">${t("ghost.reading")}</div>
                </div>
            `;
        }

        return html`
            <div
                class=${classes}
                role="group"
                aria-label=${copy.aria}
                title=${copy.aria}
                @dragover=${this._onDragOver}
                @dragleave=${this._onDragLeave}
                @drop=${this._onDrop}
            >
                ${full
                    ? html`
                          ${this._renderButtons(true)}
                          <div class="gt-tile-title">${copy.title}</div>
                          <div class="gt-tile-hint">${copy.hintFull}</div>
                      `
                    : html`
                          ${this._renderButtons(false)}
                          <div class="gt-tile-hint">${t(copy.hintCompactKey)}</div>
                      `}
            </div>
        `;
    }

    static styles = css`
        .gt-tile.gt-busy {
            cursor: progress;
        }
        .gt-spinner {
            width: 16px;
            height: 16px;
            border: 2px solid currentColor;
            border-right-color: transparent;
            border-radius: 50%;
            opacity: 0.7;
            animation: gt-spin 900ms linear infinite;
        }
        @keyframes gt-spin {
            to {
                transform: rotate(360deg);
            }
        }
        @media (prefers-reduced-motion: reduce) {
            .gt-spinner {
                animation: none;
            }
        }
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
            /* Not a control any more: only the two buttons take the
               pointer (owner, 2026-11-13). */
            cursor: default;
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
        /* Focus now lands on a button inside the tile, not on the
           tile, so the tile answers a button's :focus-visible where it
           used to answer its own. Keyboard focus only: a mouse click
           leaves the button focused, and :focus-within would keep the
           tile lit after it. */
        .gt-tile:hover,
        .gt-tile:has(.gt-btn:focus-visible),
        .gt-tile.gt-dragover {
            opacity: 1;
        }
        .gt-tile:hover,
        .gt-tile:has(.gt-btn:focus-visible) {
            background: var(--secondary-background-color);
            outline: none;
        }
        .gt-tile.device:hover,
        .gt-tile.device:has(.gt-btn:focus-visible) {
            border-color: ${unsafeCSS(ORIGIN_COLORS.device)};
            color: ${unsafeCSS(ORIGIN_COLORS.device)};
        }
        .gt-tile.remote:hover,
        .gt-tile.remote:has(.gt-btn:focus-visible) {
            border-color: ${unsafeCSS(ORIGIN_COLORS.remote)};
            color: ${unsafeCSS(ORIGIN_COLORS.remote)};
        }
        /* The compact tile takes its height from the row and carries no
           floor of its own: with one, it became the tallest item in the
           Remotes grid and set the row instead of following it (punch
           list item 12, ~92px against ~72px cards). Devices never
           showed that -- those cards are taller than the floor was. */
        .gt-tile-full {
            grid-column: 1 / -1;
            min-height: 120px;
            padding: 24px;
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
        .gt-tile:has(.gt-btn:focus-visible) .gt-tile-hint {
            color: inherit;
        }
        /* The plus and the folder (owner, 2026-11-13): two squares
           with rounded corners, a little tighter than the tile's 8px
           so they read as the tile's own. Stroke icons inline, in
           currentColor, as the round plus was: rendered through
           ha-svg-icon a stroke icon comes out as hairline garbage,
           because that element paints path data as fill
           (edit-button-pass.md). Their border and icon take the
           tile's color, so the kind color on hover carries them too.
           Both layouts get them; the full layout's are larger, where
           its text "+" was. Owner, 2026-11-14 on VM999: about 20%
           smaller than first built (32 and 40 px), so 26 and 32 px. On a
           touch screen each button's hit area reaches 4 px past its
           edge, so the small pair is 34 px to a finger without looking
           bigger; the 8 px gap keeps the two hit areas from touching. */
        .gt-buttons {
            display: flex;
            gap: 8px;
            margin-bottom: 4px;
        }
        .gt-btn {
            position: relative;
            width: 26px;
            height: 26px;
            padding: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 5px;
            border: 1.5px solid currentColor;
            background: transparent;
            color: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .gt-buttons-lg .gt-btn {
            width: 32px;
            height: 32px;
            border-radius: 6px;
        }
        @media (pointer: coarse) {
            .gt-btn::after {
                content: "";
                position: absolute;
                inset: -4px;
            }
        }
        .gt-btn svg {
            width: 14px;
            height: 14px;
            fill: none;
            stroke: currentColor;
            stroke-width: 1.8;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .gt-buttons-lg .gt-btn svg {
            width: 18px;
            height: 18px;
        }
        .gt-btn:hover {
            background: color-mix(in srgb, currentColor 14%, transparent);
        }
        .gt-btn:focus-visible {
            outline: 2px solid currentColor;
            outline-offset: 2px;
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
