/**
 * The Wigs tab (v0.7.0 Big Wig) -- the closet of portable code sets.
 *
 * Brand rows per the owner-approved C6/C8 mockups: one collapsible row
 * per brand (the panel's established expand gesture), Unbranded bucket
 * pinned at TOP, alphabetical always, no drag reorder -- the closet is
 * a reference catalog and the sort IS the feature. Uniform 14px count
 * dots (slate = library codebooks inside, oxblood = your wigs inside;
 * bare dot = 1, numbered = more); the toolbar filter chips wear the
 * same dots and ARE the legend. Search matches brand and wig names and
 * auto-expands hits.
 *
 * Wig rows: source dot, name, signal count, then a fixed-width glyph
 * slot (copy glyph opens the editor popover, user wigs only; library
 * wigs are read-only with no glyph) and TRY ON flush right. TRY ON
 * materializes through the same import path as the Clipper picker:
 * fresh decode per signal, and re-trying a wig collapses onto the
 * existing clipped remote instead of minting a twin.
 *
 * The editor dialog carries the plain-English origin sentence (the
 * tested/untested fact is diagnostic, not navigational -- design
 * history in wigs.md section 5), NAME / BRAND / MODEL / NOTES, and
 * SAVE / DOWNLOAD / DELETE. Download tries a blob anchor and falls
 * back to copy-JSON -- the panel iframe taught us to distrust it
 * (v0.5.x clipboard affair).
 *
 * Accent: oxblood leather (owner ruling 2026-07-20) -- the barber
 * chair, not the AI-design plum the early mockups wore.
 *
 * Authoritative design: docs/internal/plans/wigs-tab-mockup-c8.html.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { HairApi } from "./api.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type {
    CodeBrand,
    CodeCodebook,
    WigInfo,
    WigInvalid,
    WigsList,
} from "./types.js";

type FilterChip = "all" | "library" | "yours";

interface ClosetRow {
    // One entry a brand row can hold: a library codebook or a local wig.
    source: "library" | "local";
    id: string; // codebook id ("module:Class" or "wig:<filename>")
    label: string;
    signalCount: number;
    wig?: WigInfo;
}

interface BrandRow {
    key: string;
    label: string;
    unbranded: boolean;
    rows: ClosetRow[];
}

const UNBRANDED_KEY = "_unbranded";

@customElement("ir-wigs")
export class IrWigs extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _wigs: WigInfo[] = [];
    @state() private _invalid: WigInvalid[] = [];
    @state() private _library: CodeBrand[] = [];
    @state() private _libraryVersion: string | null = null;
    @state() private _search = "";
    @state() private _filter: FilterChip = "all";
    @state() private _openBrands: Set<string> = new Set();
    @state() private _dragOver = false;
    @state() private _notice: string | null = null;
    @state() private _busyId: string | null = null;

    // Editor dialog state.
    @state() private _editing: WigInfo | null = null;
    @state() private _editName = "";
    @state() private _editBrand = "";
    @state() private _editModel = "";
    @state() private _editNotes = "";
    @state() private _editBusy = false;
    @state() private _editError: string | null = null;
    @state() private _confirmDelete: WigInfo | null = null;

    private _noticeTimer: number | undefined;

    connectedCallback(): void {
        super.connectedCallback();
        void this._refresh();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        if (this._noticeTimer) window.clearTimeout(this._noticeTimer);
    }

    private async _refresh(): Promise<void> {
        this._loading = true;
        try {
            const list: WigsList = await this.api.wigsList();
            this._wigs = list.wigs;
            this._invalid = list.invalid;
            this._library = list.library;
            this._libraryVersion = list.library_version;
            this._error = null;
        } catch (err) {
            this._error = t("wigs.load_failed", {
                message: (err as Error).message,
            });
        } finally {
            this._loading = false;
        }
    }

    private _flash(message: string): void {
        this._notice = message;
        if (this._noticeTimer) window.clearTimeout(this._noticeTimer);
        this._noticeTimer = window.setTimeout(() => {
            this._notice = null;
        }, 5000);
    }

    // --- Closet assembly ---

    private _brandKeyFor(brand: string | null): string {
        if (!brand || !brand.trim()) return UNBRANDED_KEY;
        return brand.trim().toLowerCase().replace(/\s+/g, "_");
    }

    private _brandRows(): BrandRow[] {
        const byKey = new Map<string, BrandRow>();
        for (const brand of this._library) {
            byKey.set(brand.brand, {
                key: brand.brand,
                label: brand.label,
                unbranded: brand.brand === UNBRANDED_KEY,
                rows: brand.codebooks
                    .filter((c: CodeCodebook) => c.source !== "local")
                    .map((c: CodeCodebook) => ({
                        source: "library" as const,
                        id: c.id,
                        label: c.label,
                        signalCount: c.functions.length,
                    })),
            });
        }
        for (const wig of this._wigs) {
            const key = this._brandKeyFor(wig.brand);
            let row = byKey.get(key);
            if (!row) {
                row = {
                    key,
                    label:
                        key === UNBRANDED_KEY
                            ? t("wigs.unbranded")
                            : (wig.brand ?? "").trim(),
                    unbranded: key === UNBRANDED_KEY,
                    rows: [],
                };
                byKey.set(key, row);
            }
            row.rows.push({
                source: "local",
                id: `wig:${wig.filename}`,
                label: wig.name,
                signalCount: wig.signal_count,
                wig,
            });
        }
        const all = [...byKey.values()].filter((b) => b.rows.length > 0);
        for (const brand of all) {
            brand.rows.sort((a, b) =>
                a.label.toLowerCase().localeCompare(b.label.toLowerCase()),
            );
        }
        // Unbranded pinned at top, then the alphabet.
        all.sort((a, b) => {
            if (a.unbranded !== b.unbranded) return a.unbranded ? -1 : 1;
            return a.label.toLowerCase().localeCompare(b.label.toLowerCase());
        });
        return all;
    }

    private _visibleRows(brand: BrandRow): ClosetRow[] {
        let rows = brand.rows;
        if (this._filter === "library") {
            rows = rows.filter((r) => r.source === "library");
        } else if (this._filter === "yours") {
            rows = rows.filter((r) => r.source === "local");
        }
        const query = this._search.trim().toLowerCase();
        if (query && !brand.label.toLowerCase().includes(query)) {
            rows = rows.filter((r) =>
                r.label.toLowerCase().includes(query),
            );
        }
        return rows;
    }

    private _isOpen(brand: BrandRow, visible: ClosetRow[]): boolean {
        const query = this._search.trim().toLowerCase();
        if (query) {
            // Search auto-expands hits.
            return visible.length > 0;
        }
        return this._openBrands.has(brand.key);
    }

    private _toggleBrand(key: string): void {
        const open = new Set(this._openBrands);
        if (open.has(key)) open.delete(key);
        else open.add(key);
        this._openBrands = open;
    }

    // --- Try on ---

    private async _tryOn(row: ClosetRow): Promise<void> {
        this._busyId = row.id;
        try {
            const result = await this.api.importCodeRemote(row.id);
            this._flash(
                t("wigs.tried_on", {
                    name: result.device.label ?? row.label,
                }),
            );
            this.dispatchEvent(
                new CustomEvent("wig-tried-on", {
                    detail: result.device,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._flash(
                t("wigs.try_on_failed", { message: (err as Error).message }),
            );
        } finally {
            this._busyId = null;
        }
    }

    // --- Upload (drop bar + browse) ---

    private async _uploadText(text: string): Promise<void> {
        try {
            const result = await this.api.wigsUpload(text);
            if (result.success && result.filename) {
                this._flash(t("wigs.upload_ok", { filename: result.filename }));
                await this._refresh();
            } else {
                this._flash(
                    t("wigs.upload_failed", {
                        reason: (result.errors ?? []).join("; "),
                    }),
                );
            }
        } catch (err) {
            this._flash(
                t("wigs.upload_failed", { reason: (err as Error).message }),
            );
        }
    }

    private async _onDrop(e: DragEvent): Promise<void> {
        e.preventDefault();
        this._dragOver = false;
        const files = e.dataTransfer?.files;
        if (!files) return;
        for (const file of Array.from(files)) {
            await this._uploadText(await file.text());
        }
    }

    private _browse(): void {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = ".json,application/json";
        input.multiple = true;
        input.onchange = async () => {
            for (const file of Array.from(input.files ?? [])) {
                await this._uploadText(await file.text());
            }
        };
        input.click();
    }

    // --- Editor dialog ---

    private _openEditor(wig: WigInfo): void {
        this._editing = wig;
        this._editName = wig.name;
        this._editBrand = wig.brand ?? "";
        this._editModel = wig.model ?? "";
        this._editNotes = wig.notes ?? "";
        this._editError = null;
    }

    private _originSentence(origin: string | null): string {
        if (!origin) return t("wigs.origin.unknown");
        if (origin.startsWith("converted")) {
            const parts = origin.split(":");
            return t("wigs.origin.converted", {
                format: parts[1] ?? "another format",
            });
        }
        if (origin.startsWith("plucked")) return t("wigs.origin.plucked");
        const known: Record<string, string> = {
            captured: t("wigs.origin.captured"),
            clipped: t("wigs.origin.clipped"),
            device: t("wigs.origin.device"),
        };
        return known[origin] ?? t("wigs.origin.unknown");
    }

    private async _saveEdit(): Promise<void> {
        if (!this._editing) return;
        this._editBusy = true;
        this._editError = null;
        try {
            const result = await this.api.wigsUpdate(this._editing.filename, {
                name: this._editName.trim() || this._editing.name,
                brand: this._editBrand.trim(),
                model: this._editModel.trim(),
                notes: this._editNotes.trim(),
            });
            if (!result.success) {
                this._editError = (result.errors ?? []).join("; ");
                return;
            }
            this._editing = null;
            await this._refresh();
        } catch (err) {
            this._editError = (err as Error).message;
        } finally {
            this._editBusy = false;
        }
    }

    private async _download(wig: WigInfo | null): Promise<void> {
        if (!wig) return;
        try {
            const { filename, text } = await this.api.wigsGet(
                wig.filename,
            );
            try {
                const blob = new Blob([text], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = filename;
                anchor.click();
                URL.revokeObjectURL(url);
            } catch {
                // The iframe is hostile to downloads on some hosts; the
                // clipboard fallback keeps the file reachable.
                await navigator.clipboard.writeText(text);
                this._flash(t("wigs.editor.copied"));
            }
        } catch (err) {
            this._flash((err as Error).message);
        }
    }

    private async _confirmDeleteWig(): Promise<void> {
        const wig = this._confirmDelete;
        this._confirmDelete = null;
        if (!wig) return;
        try {
            await this.api.wigsDelete(wig.filename);
            this._editing = null;
            await this._refresh();
        } catch (err) {
            this._flash((err as Error).message);
        }
    }

    // --- Render ---

    private _counts(): { all: number; library: number; yours: number } {
        const library = this._library.reduce(
            (n, b) =>
                n +
                b.codebooks.filter((c: CodeCodebook) => c.source !== "local")
                    .length,
            0,
        );
        const yours = this._wigs.length;
        return { all: library + yours, library, yours };
    }

    render() {
        if (this._loading) {
            return html`<div class="loading">${t("common.loading_plain")}</div>`;
        }
        const counts = this._counts();
        const brands = this._brandRows();
        return html`
            <div
                class="drop-bar ${this._dragOver ? "over" : ""}"
                @dragover=${(e: DragEvent) => {
                    e.preventDefault();
                    this._dragOver = true;
                }}
                @dragleave=${() => (this._dragOver = false)}
                @drop=${this._onDrop}
            >
                <span class="drop-icon">&#8853;</span>
                <div>
                    <div class="t1">${t("wigs.drop.title")}</div>
                    <div class="t2">${t("wigs.drop.hint")}</div>
                </div>
                <button class="browse" @click=${this._browse}>
                    ${t("wigs.drop.browse")}
                </button>
            </div>

            ${this._error
                ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                : ""}
            ${this._notice
                ? html`<div class="notice">${this._notice}</div>`
                : ""}

            <div class="toolbar">
                <input
                    class="search"
                    type="text"
                    .value=${this._search}
                    placeholder=${t("wigs.search")}
                    @input=${(e: Event) =>
                        (this._search = (e.target as HTMLInputElement).value)}
                />
                <button
                    class="fchip ${this._filter === "all" ? "on" : ""}"
                    @click=${() => (this._filter = "all")}
                >
                    ${t("wigs.chip.all", { count: String(counts.all) })}
                </button>
                <button
                    class="fchip ${this._filter === "library" ? "on" : ""}"
                    @click=${() => (this._filter = "library")}
                >
                    <span class="chip-dot lib"></span>
                    ${t("wigs.chip.library", { count: String(counts.library) })}
                </button>
                <button
                    class="fchip ${this._filter === "yours" ? "on" : ""}"
                    @click=${() => (this._filter = "yours")}
                >
                    <span class="chip-dot mine"></span>
                    ${t("wigs.chip.yours", { count: String(counts.yours) })}
                </button>
                ${this._libraryVersion
                    ? html`<span class="lib-ver"
                          >${t("wigs.library_version", {
                              version: this._libraryVersion,
                          })}</span
                      >`
                    : ""}
            </div>

            ${counts.all === 0
                ? html`<div class="empty">${t("wigs.empty")}</div>`
                : html`<div class="brands">
                      ${brands.map((brand) => this._renderBrand(brand))}
                  </div>`}
            ${this._invalid.map(
                (bad) => html`<div class="invalid-row">
                    &#9888;&nbsp;${t("wigs.invalid_file", {
                        filename: bad.filename,
                        reason: `${bad.errors[0] ?? ""}.`,
                    })}
                </div>`,
            )}
            ${this._renderEditor()}
        `;
    }

    private _renderBrand(brand: BrandRow) {
        const visible = this._visibleRows(brand);
        if (visible.length === 0 && this._search.trim()) return "";
        if (visible.length === 0 && this._filter !== "all") return "";
        const open = this._isOpen(brand, visible);
        const libCount = brand.rows.filter(
            (r) => r.source === "library",
        ).length;
        const mineCount = brand.rows.filter(
            (r) => r.source === "local",
        ).length;
        return html`
            <div
                class="brand ${open ? "open" : ""} ${brand.unbranded
                    ? "unbranded"
                    : ""}"
            >
                <div
                    class="brand-head"
                    @click=${() => this._toggleBrand(brand.key)}
                >
                    <span class="brand-name">${brand.label}</span>
                    <span class="dots">
                        ${libCount > 0
                            ? html`<span class="cdot lib"
                                  >${libCount > 1 ? libCount : ""}</span
                              >`
                            : ""}
                        ${mineCount > 0
                            ? html`<span class="cdot mine"
                                  >${mineCount > 1 ? mineCount : ""}</span
                              >`
                            : ""}
                    </span>
                    <span class="chev">&#9660;</span>
                </div>
                ${open
                    ? html`<div class="wigs-list">
                          ${visible.map((row) => this._renderRow(row))}
                      </div>`
                    : ""}
            </div>
        `;
    }

    private _renderRow(row: ClosetRow) {
        return html`
            <div class="wig-row">
                <span class="wdot ${row.source === "local" ? "mine" : "lib"}"
                ></span>
                <span class="wig-name">${row.label}</span>
                <span class="wig-count"
                    >${tp("wigs.signals", row.signalCount)}</span
                >
                <span class="row-actions">
                    <span class="glyph-slot">
                        ${row.wig
                            ? html`<button
                                  class="copy-glyph"
                                  title=${t("wigs.edit")}
                                  @click=${() => this._openEditor(row.wig!)}
                              >
                                  &#10697;
                              </button>`
                            : ""}
                    </span>
                    <span class="glyph-slot">
                        ${row.wig
                            ? html`<button
                                  class="copy-glyph"
                                  title=${t("wigs.editor.download")}
                                  @click=${() =>
                                      void this._download(row.wig!)}
                              >
                                  <ha-svg-icon
                                      class="dl-icon"
                                      .path=${"M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z"}
                                  ></ha-svg-icon>
                              </button>`
                            : ""}
                    </span>
                    <button
                        class="try-btn"
                        ?disabled=${this._busyId === row.id}
                        @click=${() => this._tryOn(row)}
                    >
                        ${t("wigs.clip_it").toUpperCase()}
                    </button>
                </span>
            </div>
        `;
    }

    private _renderEditor() {
        const wig = this._editing;
        if (!wig) return "";
        // The delete confirmation renders INSIDE this dialog: a second
        // stacked ha-dialog lands behind the first (owner bench find,
        // 2026-07-20), so the editor swaps its own content instead.
        if (this._confirmDelete) {
            return html`
                <ha-dialog
                    open
                    heading=${t("common.are_you_sure")}
                    scrimClickAction=""
                    @closed=${() => (this._confirmDelete = null)}
                >
                    <div class="confirm-msg">
                        ${t("wigs.delete_confirm", {
                            filename: this._confirmDelete.filename,
                        })}
                    </div>
                    <div class="dialog-actions wig-actions">
                        <span class="spacer"></span>
                        <button
                            class="action-btn cancel-btn"
                            @click=${() => (this._confirmDelete = null)}
                        >
                            ${t("common.cancel")}
                        </button>
                        <button
                            class="action-btn delete-btn"
                            @click=${this._confirmDeleteWig}
                        >
                            ${t("common.delete")}
                        </button>
                    </div>
                </ha-dialog>
            `;
        }
        return html`
            <ha-dialog
                open
                heading=${wig.name}
                scrimClickAction=""
                @closed=${() => (this._editing = null)}
            >
                ${this._editError
                    ? html`<ha-alert alert-type="error"
                          >${this._editError}</ha-alert
                      >`
                    : ""}
                <div class="origin-line">
                    ${this._originSentence(wig.origin)}
                </div>
                <div class="field">
                    <label>${t("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._editName}
                        @input=${(e: Event) =>
                            (this._editName = (
                                e.target as HTMLInputElement
                            ).value)}
                    />
                </div>
                <div class="field">
                    <label>${t("wigs.editor.brand")}</label>
                    <input
                        type="text"
                        .value=${this._editBrand}
                        @input=${(e: Event) =>
                            (this._editBrand = (
                                e.target as HTMLInputElement
                            ).value)}
                    />
                </div>
                <div class="field">
                    <label>${t("wigs.editor.model")}</label>
                    <input
                        type="text"
                        .value=${this._editModel}
                        @input=${(e: Event) =>
                            (this._editModel = (
                                e.target as HTMLInputElement
                            ).value)}
                    />
                </div>
                <div class="field">
                    <label>${t("wigs.editor.notes")}</label>
                    <textarea
                        rows="2"
                        placeholder=${t("wigs.editor.notes_placeholder")}
                        .value=${this._editNotes}
                        @input=${(e: Event) =>
                            (this._editNotes = (
                                e.target as HTMLTextAreaElement
                            ).value)}
                    ></textarea>
                </div>
                <div class="dialog-actions wig-actions">
                    <button
                        class="action-btn delete-btn"
                        @click=${() => (this._confirmDelete = wig)}
                    >
                        ${t("common.delete")}
                    </button>
                    <button
                        class="action-btn"
                        @click=${() => void this._download(this._editing)}
                    >
                        ${t("wigs.editor.download")}
                    </button>
                    <span class="spacer"></span>
                    <button
                        class="action-btn cancel-btn"
                        @click=${() => (this._editing = null)}
                    >
                        ${t("common.cancel")}
                    </button>
                    <button
                        class="action-btn save-btn"
                        ?disabled=${this._editBusy}
                        @click=${this._saveEdit}
                    >
                        ${this._editBusy
                            ? t("common.saving")
                            : t("common.save")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [dialogStyles, css`
        /* Oxblood leather, the closet's accent (owner ruling 2026-07-20). */
        :host {
            --wigs-accent: #8e3b3b;
            --wigs-accent-soft: rgba(142, 59, 59, 0.14);
            --wigs-accent-border: rgba(142, 59, 59, 0.45);
            --wigs-lib: #78909c;
            display: block;
        }
        .loading {
            padding: 48px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty {
            padding: 40px 16px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .notice {
            margin-bottom: 12px;
            padding: 8px 14px;
            border-radius: 8px;
            background: var(--wigs-accent-soft);
            border: 1px solid var(--wigs-accent-border);
            color: var(--primary-text-color);
            font-size: 13px;
        }
        .drop-bar {
            border: 2px dashed var(--wigs-accent-border);
            border-radius: 10px;
            background: var(--wigs-accent-soft);
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 11px 16px;
            color: var(--wigs-accent);
            margin-bottom: 14px;
        }
        .drop-bar.over {
            background: rgba(142, 59, 59, 0.28);
        }
        .drop-icon {
            font-size: 19px;
        }
        .drop-bar .t1 {
            font-size: 13px;
            font-weight: 500;
        }
        .drop-bar .t2 {
            font-size: 11.5px;
            opacity: 0.75;
        }
        .drop-bar .browse {
            margin-left: auto;
            font-size: 12px;
            font-weight: 500;
            border: 1px solid var(--wigs-accent);
            color: var(--wigs-accent);
            background: var(--card-background-color, #fff);
            border-radius: 6px;
            padding: 5px 12px;
            cursor: pointer;
        }
        .toolbar {
            display: flex;
            gap: 8px;
            align-items: center;
            margin-bottom: 14px;
            flex-wrap: wrap;
        }
        .search {
            flex: 1 1 220px;
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            padding: 7px 12px;
            font-size: 13px;
            background: var(--card-background-color);
            color: var(--primary-text-color);
        }
        .search:focus {
            outline: none;
            border-color: var(--wigs-accent);
        }
        .fchip {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12.5px;
            padding: 5px 13px;
            border-radius: 16px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--secondary-text-color);
            cursor: pointer;
        }
        .fchip.on {
            background: var(--wigs-accent);
            border-color: var(--wigs-accent);
            color: #fff;
        }
        .chip-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex: none;
        }
        .chip-dot.lib {
            background: var(--wigs-lib);
        }
        .chip-dot.mine {
            background: var(--wigs-accent);
        }
        .fchip.on .chip-dot.mine {
            background: #fff;
        }
        .lib-ver {
            font-size: 11.5px;
            color: var(--secondary-text-color);
            margin-left: auto;
        }
        .brands {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .brand {
            border: 1px solid var(--divider-color);
            border-radius: 10px;
            background: var(--card-background-color);
            overflow: hidden;
        }
        .brand.open {
            border-color: var(--wigs-accent-border);
        }
        .brand.unbranded {
            border-style: dashed;
        }
        .brand.unbranded .brand-name {
            color: var(--secondary-text-color);
        }
        .brand-head {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 16px;
            height: 54px;
            cursor: pointer;
        }
        .brand.open .brand-head {
            background: var(--wigs-accent-soft);
        }
        .brand-name {
            font-size: 14.5px;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .dots {
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        /* Uniform 14px, deliberately off the ir-count-dot size ramp:
           bare = 1 inside, numbered = more (owner ruling, c6). */
        .cdot {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            flex: none;
            color: #fff;
            font-size: 9.5px;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .cdot.lib {
            background: var(--wigs-lib);
        }
        .cdot.mine {
            background: var(--wigs-accent);
        }
        .chev {
            color: var(--secondary-text-color);
            font-size: 13px;
            transition: transform 0.15s;
            margin-left: 4px;
        }
        .brand.open .chev {
            transform: rotate(180deg);
            color: var(--wigs-accent);
        }
        .wigs-list {
            border-top: 1px solid var(--divider-color);
        }
        .wig-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 16px 0 30px;
            height: 46px;
            border-bottom: 1px solid var(--divider-color);
            font-size: 13.5px;
        }
        .wig-row:last-child {
            border-bottom: none;
        }
        .wdot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            flex: none;
        }
        .wdot.lib {
            background: var(--wigs-lib);
        }
        .wdot.mine {
            background: var(--wigs-accent);
        }
        .wig-name {
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .wig-count {
            font-size: 12px;
            color: var(--secondary-text-color);
        }
        .row-actions {
            margin-left: auto;
            display: flex;
            align-items: center;
        }
        .glyph-slot {
            width: 30px;
            display: flex;
            justify-content: center;
            flex: none;
        }
        .copy-glyph {
            font-size: 14px;
            color: var(--secondary-text-color);
            background: none;
            border: none;
            cursor: pointer;
        }
        .copy-glyph:hover {
            color: var(--wigs-accent);
        }
        /* CLIP IT wears the Clipper's copper: the action's destination,
           not the closet's own color (owner ruling, 2026-07-20 bench). */
        .try-btn {
            font-size: 12px;
            font-weight: 500;
            color: #b87333;
            background: none;
            border: none;
            letter-spacing: 0.4px;
            cursor: pointer;
            min-width: 54px;
            text-align: right;
        }
        .try-btn:disabled {
            opacity: 0.5;
        }
        .invalid-row {
            margin-top: 14px;
            display: flex;
            gap: 10px;
            align-items: center;
            background: rgba(230, 81, 0, 0.08);
            border: 1px solid rgba(230, 81, 0, 0.4);
            border-radius: 8px;
            padding: 9px 14px;
            font-size: 12.5px;
            color: var(--warning-color, #e65100);
        }
        /* Editor dialog */
        .origin-line {
            display: flex;
            gap: 8px;
            align-items: flex-start;
            background: rgba(255, 160, 0, 0.1);
            border: 1px solid rgba(255, 160, 0, 0.4);
            border-radius: 8px;
            padding: 9px 12px;
            font-size: 12.5px;
            line-height: 1.45;
            margin-bottom: 12px;
            color: var(--primary-text-color);
        }
        .field {
            margin-bottom: 11px;
        }
        .field label {
            display: block;
            font-size: 11px;
            color: var(--secondary-text-color);
            letter-spacing: 0.4px;
            margin-bottom: 3px;
            text-transform: uppercase;
        }
        .field input,
        .field textarea {
            width: 100%;
            box-sizing: border-box;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 7px 10px;
            font-size: 13px;
            font-family: inherit;
            background: var(--card-background-color);
            color: var(--primary-text-color);
        }
        .field input:focus,
        .field textarea:focus {
            outline: none;
            border-color: var(--wigs-accent);
        }
        .editor-actions {
            display: flex;
            align-items: center;
            gap: 16px;
            padding-top: 10px;
            border-top: 1px solid var(--divider-color);
        }
        .wig-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .wig-actions .save-btn {
            background: var(--wigs-accent);
            border-color: var(--wigs-accent);
            color: #fff;
        }
        .wig-actions .delete-btn {
            color: var(--error-color, #c62828);
            border-color: var(--error-color, #c62828);
        }
        .dl-icon {
            --mdc-icon-size: 15px;
            width: 15px;
            height: 15px;
        }
        .spacer {
            flex: 1;
        }
        .confirm-msg {
            padding: 4px 0 10px;
            font-size: 13.5px;
            line-height: 1.5;
        }
    `];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-wigs": IrWigs;
    }
}
