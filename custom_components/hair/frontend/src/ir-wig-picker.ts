/**
 * Flat, searchable wig picker for the Closet tab of the Add Controlled
 * Device / Add Trigger Remote dialogs (add-popups, signpost 2).
 *
 * A genuine divergence from ir-wigs.ts's own closet browser, not a
 * subset of its behavior: the real Closet already groups by brand with
 * collapsible headers and auto-expand-on-search (ir-wigs.ts
 * `_isOpen()` / `_toggleBrand()`). Owner ruling this round (Option A):
 * "I think being able to search by the name is going to be enough...
 * If it starts to get too crazy, we can change it to the collapsible
 * brands." A deliberate simplification for THIS narrower "pick a
 * source" picker, not a claim that flat-plus-search is what the real
 * Closet does -- the brand-grouped fallback stays proven there if this
 * picker is ever extended toward it later.
 *
 * Rows mix local wigs (yours) and installed-library codebooks
 * (library), same as the toolbar's All / Library / Yours split in
 * ir-wigs.ts. Search matches the row label plus, for local wigs, `kind`
 * and every `identifiers` value (mirrors ir-wigs.ts `_rowMatches()`);
 * library rows have neither and keep the label-only match.
 *
 * Matrix rule (2026-08-08, "the matrix rule"): a matrix-backed local
 * wig still renders -- full detail, legible -- but disabled with a
 * one-line reason ("Matrix wig -- Fan") instead of hidden or erroring.
 * The count badge on a matrix row reads the discrete-press subset only
 * (`wig.signal_count`, i.e. the wig's flat extra signals), never the
 * matrix's own cell count -- a matrix source has no single fireable
 * signal a trigger or a flat device-command list can point at. Library
 * codebooks never carry a matrix (WigsList's `library` entries have no
 * `matrix` field), so this only ever applies to local rows.
 *
 * Selection is presentational only: this component resolves and emits
 * the picked row, it does not call any create/import/use API itself --
 * that decision (call `wigsUpload`+adopt machinery for a local wig vs.
 * `importCodeRemote` for a library codebook) belongs to the consuming
 * dialog (Track 2/3), which reads `row.source` off the event detail.
 *
 * Fires `wig-picked` with detail: { value: string | null, row: WigPickRow | null }
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { HairApi } from "./api.js";
import type { CodeBrand, CodeCodebook, WigInfo } from "./types.js";

const UNBRANDED_KEY = "__unbranded__";

export type WigPickFilter = "all" | "library" | "yours";

export interface WigPickRow {
    source: "local" | "library";
    /** Stable id: `wig:<filename>` for local rows, `lib:<brand>:<codebookId>`
     *  for library rows -- matches this.value when the row is selected. */
    id: string;
    label: string;
    /** Discrete-press count: wig.signal_count for a local row (matrix
     *  cells excluded, see module doc), functions.length for a library
     *  codebook. */
    signalCount: number;
    wig: WigInfo | null;
    brand: CodeBrand | null;
    codebook: CodeCodebook | null;
}

@customElement("ir-wig-picker")
export class IrWigPicker extends LitElement {
    /** HAIR API client. Required -- the wig list comes from it. */
    @property({ attribute: false }) public api!: HairApi;

    /** Currently selected row id (`row.id`), or null for no selection. */
    @property({ attribute: false }) public value: string | null = null;

    /** Disable all interactions. */
    @property({ type: Boolean }) public disabled = false;

    @state() private _wigs: WigInfo[] = [];
    @state() private _library: CodeBrand[] = [];
    @state() private _search = "";
    @state() private _filter: WigPickFilter = "all";
    @state() private _loaded = false;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
    }

    private async _load(): Promise<void> {
        if (!this.api) return;
        try {
            const list = await this.api.wigsList();
            this._wigs = list.wigs;
            this._library = list.library;
        } catch {
            this._wigs = [];
            this._library = [];
        } finally {
            this._loaded = true;
        }
    }

    private _rows(): WigPickRow[] {
        const rows: WigPickRow[] = [];
        for (const brand of this._library) {
            for (const cb of brand.codebooks) {
                if (cb.source === "local") continue; // covered by _wigs below
                rows.push({
                    source: "library",
                    id: `lib:${brand.brand}:${cb.id}`,
                    label: `${brand.label} ${cb.label}`.trim(),
                    signalCount: cb.functions.length,
                    wig: null,
                    brand,
                    codebook: cb,
                });
            }
        }
        for (const wig of this._wigs) {
            rows.push({
                source: "local",
                id: `wig:${wig.filename}`,
                label: wig.name,
                signalCount: wig.signal_count,
                wig,
                brand: null,
                codebook: null,
            });
        }
        rows.sort((a, b) => a.label.toLowerCase().localeCompare(b.label.toLowerCase()));
        return rows;
    }

    private _rowMatches(row: WigPickRow, query: string): boolean {
        if (row.label.toLowerCase().includes(query)) return true;
        const wig = row.wig;
        if (!wig) return false;
        if (wig.kind?.toLowerCase().includes(query)) return true;
        for (const value of Object.values(wig.identifiers ?? {})) {
            const list = Array.isArray(value) ? value : [value];
            if (list.some((v) => String(v).toLowerCase().includes(query))) {
                return true;
            }
        }
        return false;
    }

    private _visibleRows(): WigPickRow[] {
        let rows = this._rows();
        if (this._filter === "library") {
            rows = rows.filter((r) => r.source === "library");
        } else if (this._filter === "yours") {
            rows = rows.filter((r) => r.source === "local");
        }
        const query = this._search.trim().toLowerCase();
        if (query) {
            rows = rows.filter((r) => this._rowMatches(r, query));
        }
        return rows;
    }

    private _counts(): { all: number; library: number; yours: number } {
        const rows = this._rows();
        return {
            all: rows.length,
            library: rows.filter((r) => r.source === "library").length,
            yours: rows.filter((r) => r.source === "local").length,
        };
    }

    private _pick(row: WigPickRow): void {
        if (this.disabled || row.wig?.matrix) return;
        this.value = row.id;
        this.dispatchEvent(
            new CustomEvent("wig-picked", {
                detail: { value: row.id, row },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _matrixNote(wig: WigInfo): string {
        return wig.kind
            ? t("wigpicker.matrix_note_kind", {
                  kind: wig.kind.charAt(0).toUpperCase() + wig.kind.slice(1),
              })
            : t("wigpicker.matrix_note_plain");
    }

    render() {
        const counts = this._counts();
        const rows = this._visibleRows();

        if (this._loaded && counts.all === 0) {
            return html`<div class="dlg-empty-line">${t("wigpicker.empty")}</div>`;
        }

        return html`
            <div class="toolbar">
                <input
                    class="search"
                    type="text"
                    .value=${this._search}
                    placeholder=${t("wigpicker.search")}
                    ?disabled=${this.disabled}
                    @input=${(e: Event) =>
                        (this._search = (e.target as HTMLInputElement).value)}
                />
                <div class="chip-row">
                    <button
                        class="fchip ${this._filter === "all" ? "on" : ""}"
                        ?disabled=${this.disabled}
                        @click=${() => (this._filter = "all")}
                    >
                        ${t("wigs.chip.all", { count: String(counts.all) })}
                    </button>
                    <button
                        class="fchip ${this._filter === "library" ? "on" : ""}"
                        ?disabled=${this.disabled}
                        @click=${() => (this._filter = "library")}
                    >
                        <span class="chip-dot lib"></span
                        >${t("wigs.chip.library", { count: String(counts.library) })}
                    </button>
                    <button
                        class="fchip ${this._filter === "yours" ? "on" : ""}"
                        ?disabled=${this.disabled}
                        @click=${() => (this._filter = "yours")}
                    >
                        <span class="chip-dot mine"></span
                        >${t("wigs.chip.yours", { count: String(counts.yours) })}
                    </button>
                </div>
            </div>
            <div class="list">
                ${rows.map((row) => this._renderRow(row))}
                ${rows.length === 0
                    ? html`<div class="no-matches">${t("wigpicker.no_matches")}</div>`
                    : ""}
            </div>
        `;
    }

    private _renderRow(row: WigPickRow) {
        const isMatrix = !!row.wig?.matrix;
        const selected = this.value === row.id;
        const cls = [
            "row",
            selected ? "selected" : "",
            isMatrix ? "matrix" : "",
        ]
            .filter(Boolean)
            .join(" ");
        return html`
            <div
                class=${cls}
                ?inert=${this.disabled}
                @click=${() => this._pick(row)}
            >
                <div class="row-main">
                    <div class="row-name">
                        ${row.label}
                        ${row.source === "library"
                            ? html`<span class="lib-tag">${t("wigpicker.library_tag")}</span>`
                            : ""}
                    </div>
                    <div class="row-sub ${isMatrix ? "matrix-note" : ""}">
                        ${isMatrix
                            ? this._matrixNote(row.wig!)
                            : t("wigs.states.other", { count: String(row.signalCount) })}
                    </div>
                </div>
                <div class="row-count">${row.signalCount}</div>
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
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-family: inherit;
            color: var(--secondary-text-color);
            cursor: pointer;
        }
        .fchip.on {
            border-color: var(--origin-closet, #8e3b3b);
            color: var(--primary-text-color);
            background: rgba(142, 59, 59, 0.1);
        }
        .chip-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            display: inline-block;
        }
        .chip-dot.lib {
            background: #8e9aaf;
        }
        .chip-dot.mine {
            background: #8e3b3b;
        }
        .list {
            max-height: 320px;
            overflow-y: auto;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
        }
        .row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 9px 12px;
            border-bottom: 1px solid var(--divider-color);
            cursor: pointer;
        }
        .row:last-child {
            border-bottom: none;
        }
        .row:hover {
            background: var(--secondary-background-color);
        }
        .row.selected {
            background: rgba(142, 59, 59, 0.12);
            border-left: 3px solid var(--origin-closet, #8e3b3b);
            padding-left: 9px;
        }
        .row.matrix {
            cursor: default;
        }
        .row.matrix:hover {
            background: transparent;
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
        .lib-tag {
            margin-left: 6px;
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
            border: 1px solid var(--divider-color);
            border-radius: 3px;
            padding: 1px 4px;
        }
        .row-sub {
            font-size: 0.74rem;
            color: var(--secondary-text-color);
        }
        .row-sub.matrix-note {
            color: #b8860b;
        }
        .row-count {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            flex: none;
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
        "ir-wig-picker": IrWigPicker;
    }
}
