/**
 * Remote tab picker for the Add Controlled Device / Add Trigger Remote
 * dialogs (add-popups, signpost 2) -- SHELL ONLY this signpost. Real
 * interaction (click a row to source a device/trigger from it) lands in
 * signpost 3, per the coding plan's own framing: "Rows render inert
 * (full detail, no click handler)... wiring lands signpost 3."
 *
 * Because wiring is deferred, so is picking a live data source per
 * kind -- Trigger Remotes now has a backend (Track 1B, this same
 * signpost) but Sniffer / Clipper / Plucker do not yet have an agreed
 * "what counts as a row" contract for THIS picker. Rather than guess
 * four data-fetching integrations a signpost early, this component
 * takes its rows as an input property: the consumer (a Track 2/3
 * dialog, or a bench harness page per the Track 1 owner checkpoint --
 * "bench the two new pickers... in isolation") supplies
 * `RemotePickGroup[]`, and this component owns only the shell:
 * grouping, search, chip-filtering, and the inert-row/Preview-flag
 * treatment. Signpost 3 is expected to either keep feeding it from the
 * dialog or grow a thin per-kind data-loading wrapper around it -- this
 * module doesn't need to know which yet.
 *
 * Search and chip-filter ARE live in this signpost even though
 * row-click isn't -- cheap to build now, and it's the truest preview of
 * signpost 3's real interaction.
 *
 * Group order is fixed: Trigger Remotes, Sniffer, Clipper, Plucker.
 * Each group header and each filter chip is colored per its kind
 * (ir-origin-colors.ts REMOTE_KIND_COLORS). Plucker is conditional: its
 * chip and group render only when `pluckerConfigured` is true (not
 * every HA install has a Plucker source) -- four chips/three groups
 * otherwise, nothing disabled or greyed for a kind that doesn't apply.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { REMOTE_KIND_COLORS, type RemoteKind } from "./ir-origin-colors.js";

export interface RemotePickRow {
    id: string;
    name: string;
    /** One-line caption, e.g. a trigger/signal/command count -- the
     *  consumer formats this per kind, this component just renders it. */
    sub?: string;
}

export interface RemotePickGroup {
    kind: RemoteKind;
    rows: RemotePickRow[];
}

const GROUP_ORDER: RemoteKind[] = ["trigger", "sniffer", "clipper", "plucker"];

type ChipFilter = "all" | RemoteKind;

@customElement("ir-remote-picker")
export class IrRemotePicker extends LitElement {
    /** Row data, grouped by source kind. Supplied by the consumer --
     *  see module doc for why this component doesn't fetch its own. */
    @property({ attribute: false }) public groups: RemotePickGroup[] = [];

    /** Whether this install has a Plucker source configured at all.
     *  Gates the Plucker chip/group entirely (not just an empty count). */
    @property({ type: Boolean }) public pluckerConfigured = false;

    @state() private _search = "";
    @state() private _filter: ChipFilter = "all";

    private _groupRows(kind: RemoteKind): RemotePickRow[] {
        return this.groups.find((g) => g.kind === kind)?.rows ?? [];
    }

    private _allRows(): { kind: RemoteKind; row: RemotePickRow }[] {
        const kinds = this.pluckerConfigured
            ? GROUP_ORDER
            : GROUP_ORDER.filter((k) => k !== "plucker");
        return kinds.flatMap((kind) =>
            this._groupRows(kind).map((row) => ({ kind, row })),
        );
    }

    private _counts(): Record<ChipFilter, number> {
        const all = this._allRows();
        const counts: Record<ChipFilter, number> = {
            all: all.length,
            trigger: 0,
            sniffer: 0,
            clipper: 0,
            plucker: 0,
        };
        for (const { kind } of all) counts[kind]++;
        return counts;
    }

    private _visibleByKind(kind: RemoteKind): RemotePickRow[] {
        if (this._filter !== "all" && this._filter !== kind) return [];
        const query = this._search.trim().toLowerCase();
        const rows = this._groupRows(kind);
        if (!query) return rows;
        return rows.filter((r) => r.name.toLowerCase().includes(query));
    }

    render() {
        const totalRows = this._allRows().length;
        if (totalRows === 0) {
            return html`<div class="dlg-empty-line">${t("remotepicker.empty")}</div>`;
        }

        const counts = this._counts();
        const kinds = this.pluckerConfigured
            ? GROUP_ORDER
            : GROUP_ORDER.filter((k) => k !== "plucker");
        const visibleGroups = kinds
            .map((kind) => ({ kind, rows: this._visibleByKind(kind) }))
            .filter((g) => g.rows.length > 0);

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
                <div class="chip-row">
                    <button
                        class="fchip ${this._filter === "all" ? "on" : ""}"
                        style=${this._filter === "all"
                            ? `background:${REMOTE_KIND_COLORS.trigger};border-color:${REMOTE_KIND_COLORS.trigger};color:#241c00;`
                            : ""}
                        @click=${() => (this._filter = "all")}
                    >
                        ${t("remotepicker.chip.all", { count: String(counts.all) })}
                    </button>
                    ${kinds.map((kind) => this._renderChip(kind, counts[kind]))}
                </div>
            </div>
            <div class="list-wrap">
                <span
                    class="preview-tag"
                    title=${t("remotepicker.preview_tooltip")}
                    >${t("remotepicker.preview_flag")}</span
                >
                <div class="list">
                    ${visibleGroups.map((g) => this._renderGroup(g.kind, g.rows))}
                    ${visibleGroups.length === 0
                        ? html`<div class="no-matches">
                              ${t("remotepicker.no_matches")}
                          </div>`
                        : ""}
                </div>
            </div>
        `;
    }

    private _renderChip(kind: RemoteKind, count: number) {
        const on = this._filter === kind;
        const color = REMOTE_KIND_COLORS[kind];
        return html`
            <button
                class="fchip ${on ? "on" : ""}"
                style=${on ? `background:${color};border-color:${color};` : ""}
                @click=${() => (this._filter = kind)}
            >
                ${t(`remotepicker.chip.${kind}`, { count: String(count) })}
            </button>
        `;
    }

    private _renderGroup(kind: RemoteKind, rows: RemotePickRow[]) {
        const color = REMOTE_KIND_COLORS[kind];
        return html`
            <div class="group-label" style="color:${color}">
                ${t(`remotepicker.group.${kind}`)}
            </div>
            ${rows.map((row) => this._renderRow(row))}
        `;
    }

    private _renderRow(row: RemotePickRow) {
        return html`
            <div class="row inert" inert>
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
        .chip-row {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .fchip {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-family: inherit;
            color: var(--secondary-text-color);
            cursor: pointer;
        }
        .list-wrap {
            position: relative;
        }
        /* Not a filled pill the same shape as the clickable chips above --
           a dashed, unfilled corner flag instead, a shape nothing
           clickable in this component uses, with a hover tooltip so the
           reason reaches anyone who checks even without clicking. */
        .preview-tag {
            position: absolute;
            top: -8px;
            right: 10px;
            background: var(--card-background-color);
            border: 1px dashed var(--secondary-text-color);
            color: var(--secondary-text-color);
            font-size: 0.6rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 2px 6px;
            border-radius: 4px;
            pointer-events: none;
            z-index: 1;
        }
        .list {
            max-height: 320px;
            overflow-y: auto;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 4px 0;
        }
        .group-label {
            font-size: 0.65rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin: 10px 12px 4px;
            padding-top: 8px;
            border-top: 1px solid var(--divider-color);
        }
        .group-label:first-child {
            margin-top: 0;
            padding-top: 0;
            border-top: none;
        }
        .row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            cursor: default;
            opacity: 0.92;
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
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-remote-picker": IrRemotePicker;
    }
}
