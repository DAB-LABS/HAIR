/**
 * Single-kind source picker for the Add Controlled Device / Add Trigger
 * Remote dialogs (add-popups, signpost 3, Track 1 item 4; wired live
 * signpost 3, Track 4 bench-gate fix, 2026-08-17 -- see
 * signpost-3-coding-plan.md section 3a).
 *
 * Retires ir-remote-picker.ts (signpost 2, Track 1c) outright -- that
 * component's whole reason for existing was grouping all four kinds
 * (Trigger Remotes, Sniffer, Clipper, Plucker) under ONE "Remote" tab
 * with an inner chip filter to tell them apart. The coding plan's own
 * per-kind-tabs item invited exactly this retirement ("retire the
 * inert treatment and ir-remote-picker's grouped-with-chips inner
 * filter if the per-kind split makes it dead weight... do not leave
 * two ways to do it"): once each kind gets its OWN tab, a chip filter
 * that re-splits by kind INSIDE one tab is the two-ways-to-do-it this
 * plan warns against. ir-remote-picker had no other consumer (grep
 * confirmed both Add dialogs were its only callers), so nothing else
 * breaks.
 *
 * What survives from ir-remote-picker: the search box, the no-matches
 * state, the empty-state copy per kind. What's gone: multi-group
 * rendering, the chip row, the "trigger" kind's special standing
 * (every kind is now just "the kind this instance was given"), the
 * "Preview" corner flag, and the blanket `inert` on every row.
 *
 * LIVE NOW: clicking a row fires `row-picked` with
 * `{ value: row.id, row }` -- same shape ir-wig-picker.ts's
 * `wig-picked` and ir-device-picker.ts's `device-picked` already use,
 * so the two Add dialogs wire it the same way they wire those. The
 * consumer feeds the pick back via `selectedId` for the highlight and
 * sets `disabled` while its own create is in flight (same pattern as
 * the other two pickers) -- this component still does not know or
 * care what "picking" a row actually creates; that machinery
 * (`hair/device/create` / `hair/trigger-remote/create`'s
 * `promoted_from_unknown_id`, both landed Track 2 item 2, or the
 * `trigger-remote/make-device` mirror path for the Remotes tab) lives
 * entirely in the two dialogs that use this component.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { REMOTE_KIND_COLORS, type RemoteKind } from "./ir-origin-colors.js";

/** REMOTE_KIND_COLORS, restated as a 0.12-alpha wash for the selected-
 *  row background -- same alpha ir-wig-picker.ts's own `.row.selected`
 *  uses for its closet accent. Kept as a sibling constant rather than
 *  computed at render time so there is one obvious place to look if a
 *  kind's wash ever needs to move independently of its solid color. */
const KIND_ROW_WASH: Record<RemoteKind, string> = {
    trigger: "rgba(245, 166, 35, 0.12)",
    sniffer: "rgba(33, 150, 243, 0.12)",
    clipper: "rgba(184, 115, 51, 0.12)",
    plucker: "rgba(69, 90, 100, 0.12)",
};

export interface SourcePickRow {
    id: string;
    name: string;
    /** One-line caption, e.g. a signal/trigger count -- the consumer
     *  formats this per kind, this component just renders it. */
    sub?: string;
    /** The same count `sub` describes, unformatted -- the consumer's
     *  preview line substitutes this into "{count} commands/triggers
     *  from {name}" once a row is picked (signpost 3, Track 4 bench-
     *  gate fix). Optional so existing callers that never set it keep
     *  compiling; both Add dialogs set it. */
    count?: number;
}

@customElement("ir-source-picker")
export class IrSourcePicker extends LitElement {
    /** Row data. Supplied by the consumer -- this component still
     *  doesn't fetch its own, per ir-remote-picker's original module
     *  doc; only WHERE the fetch happens moved (into the dialog). */
    @property({ attribute: false }) public rows: SourcePickRow[] = [];

    /** Which kind this instance is showing -- drives color and the
     *  empty-state copy. One instance per tab now, not one shared
     *  instance grouping all four. */
    @property() public kind: RemoteKind = "trigger";

    /** True while the consumer's fetch is in flight. */
    @property({ type: Boolean }) public loading = false;

    /** True while the consumer's own create is in flight -- same
     *  convention ir-wig-picker.ts / ir-device-picker.ts already use
     *  to freeze the list mid-submit. */
    @property({ type: Boolean }) public disabled = false;

    /** The consumer's current pick (`row.id`), or null for no
     *  selection -- drives the selected-row highlight. */
    @property() public selectedId: string | null = null;

    @state() private _search = "";

    private _visibleRows(): SourcePickRow[] {
        const query = this._search.trim().toLowerCase();
        if (!query) return this.rows;
        return this.rows.filter((r) => r.name.toLowerCase().includes(query));
    }

    render() {
        if (this.loading) {
            return html`<div class="dlg-empty-line">${t("common.loading_plain")}</div>`;
        }
        if (this.rows.length === 0) {
            return html`<div class="dlg-empty-line">
                ${t(`sourcepicker.empty.${this.kind}`)}
            </div>`;
        }

        const visible = this._visibleRows();
        return html`
            <div class="toolbar">
                <input
                    class="search"
                    type="text"
                    .value=${this._search}
                    placeholder=${t("remotepicker.search")}
                    @input=${(e: Event) =>
                        (this._search = (e.target as HTMLInputElement).value)}
                />
            </div>
            <div class="list-wrap">
                <div class="list">
                    ${visible.map((row) => this._renderRow(row))}
                    ${visible.length === 0
                        ? html`<div class="no-matches">
                              ${t("remotepicker.no_matches")}
                          </div>`
                        : ""}
                </div>
            </div>
        `;
    }

    private _pick(row: SourcePickRow): void {
        if (this.disabled) return;
        this.dispatchEvent(
            new CustomEvent("row-picked", {
                detail: { value: row.id, row },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _renderRow(row: SourcePickRow) {
        const selected = this.selectedId === row.id;
        const color = REMOTE_KIND_COLORS[this.kind];
        return html`
            <div
                class="row ${selected ? "selected" : ""}"
                style=${selected
                    ? `border-left-color:${color};background:${KIND_ROW_WASH[this.kind]};`
                    : ""}
                ?inert=${this.disabled}
                @click=${() => this._pick(row)}
            >
                <div class="row-main">
                    <div class="row-name">${row.name}</div>
                    ${row.sub ? html`<div class="row-sub">${row.sub}</div>` : ""}
                </div>
            </div>
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        .toolbar {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
        }
        .search {
            flex: 1;
            min-width: 160px;
            padding: 7px 10px;
            border-radius: 6px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.85rem;
            font-family: inherit;
        }
        .list-wrap {
            position: relative;
        }
        .list {
            max-height: 320px;
            overflow-y: auto;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 4px 0;
        }
        .row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            border-left: 3px solid transparent;
            cursor: pointer;
        }
        .row:hover {
            background: var(--secondary-background-color);
        }
        .row.selected {
            padding-left: 9px;
        }
        .row[inert] {
            cursor: default;
            opacity: 0.6;
        }
        .row-main {
            flex: 1;
            min-width: 0;
        }
        .row-name {
            font-size: 0.88rem;
            color: var(--primary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .row-sub {
            font-size: 0.74rem;
            color: var(--secondary-text-color);
        }
        .no-matches {
            padding: 16px 4px;
            text-align: center;
            font-size: 0.8rem;
            font-style: italic;
            color: var(--secondary-text-color);
        }
        .dlg-empty-line {
            font-size: 0.82rem;
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 18px 4px;
            text-align: center;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-source-picker": IrSourcePicker;
    }
}

// Re-export so consumers migrating off ir-remote-picker's REMOTE_KIND_COLORS
// import path don't also need a second import line.
export { REMOTE_KIND_COLORS };
