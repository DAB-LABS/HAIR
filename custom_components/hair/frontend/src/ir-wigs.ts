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
import { actionChipStyles } from "./ir-action-chip-styles.js";
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
    signalNames: string[];
    wig?: WigInfo;
}

interface BrandRow {
    key: string;
    label: string;
    unbranded: boolean;
    rows: ClosetRow[];
}

const UNBRANDED_KEY = "_unbranded";

// Wig (SVG Repo, owner-supplied images/wig.svg), scaled to the 24x24
// tool-icon box like the clippers, mirror, and tweezers before it.
const ICON_WIG =
    "M 2.45,21.37 C 1.74,20.36 1.30,18.28 0.95,18.06 C 0.59,17.83 0.40,15.85 0.57,15.36 C 0.74,14.87 0.11,13.99 0.01,13.26 C -0.08,12.53 0.44,11.84 0.42,11.52 C 0.41,11.20 0.22,9.08 1.02,7.47 C 1.45,6.62 2.67,5.28 3.93,4.70 C 5.05,4.18 6.23,4.38 6.31,4.25 C 6.46,3.98 7.34,2.27 7.95,2.45 C 7.11,3.28 7.24,4.21 7.24,4.21 C 7.24,4.21 10.07,2.34 12.34,2.45 C 14.61,2.56 19.16,5.47 19.31,5.56 C 19.46,5.66 18.97,4.63 18.11,3.50 C 18.97,3.54 20.34,6.20 20.51,6.35 C 20.68,6.50 20.79,6.37 20.51,5.23 C 21.09,5.30 21.33,6.87 21.63,7.44 C 21.93,8.00 22.79,8.02 22.72,10.13 C 24.03,10.21 24.22,14.05 23.80,14.78 C 23.63,17.29 23.21,18.34 22.79,19.31 C 22.37,20.29 21.82,21.56 21.82,21.56 C 21.82,21.56 21.95,17.42 21.24,14.39 C 20.74,12.26 19.60,10.98 18.71,10.79 C 16.55,10.34 12.30,10.70 11.81,11.30 C 10.72,11.69 5.38,9.87 4.28,10.73 C 3.64,11.24 2.89,13.16 2.90,14.67 C 2.91,15.73 3.57,15.53 3.61,16.58 C 3.63,17.16 3.06,17.54 2.75,18.45 C 2.50,19.18 2.50,20.39 2.45,21.37";

// Shared expand chevrons -- the same mdi paths the Sniffer/Clipper
// cards use, so every disclosure arrow in the panel is one glyph.
const ICON_EXPAND = "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";
const ICON_COLLAPSE = "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z";

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
    @state() private _noticeKind: "ok" | "warn" = "ok";
    // The drop bar's receipt: persists until the NEXT drop (owner
    // ruling) so "where did it go" stays answered.
    @state() private _receipt: string | null = null;
    @state() private _receiptKind: "ok" | "dup" | "warn" = "ok";
    @state() private _receiptFiles: {
        filename: string;
        name: string;
        brand: string | null;
        duplicate_of: string | null;
        duplicates?: { filename: string; brand: string | null }[];
    }[] = [];
    @state() private _receiptSuffix = "";
    @state() private _bloomId: string | null = null;
    private _pendingScrollId: string | null = null;
    @state() private _busyId: string | null = null;
    @state() private _peekId: string | null = null;
    private _peekPos = { top: 0, left: 0 };
    private _peekNames: string[] = [];

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

    private _flash(message: string, kind: "ok" | "warn" = "ok"): void {
        this._noticeKind = kind;
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
                        signalNames: c.functions.map((f) => f.name),
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
                signalNames: wig.signals ?? [],
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

    /**
     * The signal peek (owner ask, 2026-07-20): clicking a row's signal
     * count opens a read-only list of the signal names -- the shop
     * window, not the workbench; the Clipper stays the real signal
     * viewer (c6 two-level ruling intact: this is a popover, not a
     * third hierarchy level). Same fixed-position anatomy as the
     * linked-devices popover so the gesture is already familiar.
     */
    private _togglePeek(row: ClosetRow, e: Event): void {
        e.stopPropagation();
        if (this._peekId === row.id) {
            this._peekId = null;
            return;
        }
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        this._peekPos = { top: rect.bottom + 6, left: rect.left };
        this._peekNames = row.signalNames;
        this._peekId = row.id;
    }

    private _renderPeek() {
        if (!this._peekId || this._peekNames.length === 0) return "";
        return html`<div
                class="linked-scrim"
                @click=${() => (this._peekId = null)}
            ></div>
            <div
                class="peek-popover"
                style="top: ${this._peekPos.top}px; left: ${this._peekPos
                    .left}px;"
            >
                ${this._peekNames.map(
                    (name) => html`<div class="peek-entry">${name}</div>`,
                )}
            </div>`;
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
                "warn",
            );
        } finally {
            this._busyId = null;
        }
    }

    // --- Upload (drop bar + browse) ---

    private async _uploadText(
        text: string, filename = "",
    ): Promise<void> {
        try {
            const result = await this.api.wigsUpload(text, filename);
            if (!result.success) {
                this._receiptKind = "warn";
                this._receiptFiles = [];
                this._receipt = t("wigs.upload_failed", {
                    reason: (result.errors ?? []).join("; "),
                });
                return;
            }
            const files = result.files ?? [];
            const anyDup = files.some((f) => f.duplicate_of);
            this._receiptFiles = files;
            this._receiptSuffix =
                (result.skipped ?? []).length > 0
                    ? t("wigs.upload_partial", {
                          count: String(result.skipped!.length),
                      })
                    : "";
            this._receiptKind = anyDup ? "dup" : "ok";
            this._receipt = "files";

            // No auto-jump (owner ruling): the receipt's name/brand
            // links are the invitation; the user pulls, we don't
            // shove. Just make sure a Library filter cannot hide the
            // arrival if they DO click.
            if (this._filter === "library") this._filter = "all";
            await this._refresh();
        } catch (err) {
            this._receiptKind = "warn";
            this._receiptFiles = [];
            this._receipt = t("wigs.upload_failed", {
                reason: (err as Error).message,
            });
        }
    }

    /**
     * Receipt line with the wig name and brand as links (owner ask):
     * the localized template is formatted with sentinel characters and
     * split, so the links land wherever the language puts the
     * placeholders.
     */
    private _renderReceiptLine() {
        if (this._receiptFiles.length === 0) {
            return html`${this._receipt}`;
        }
        const parts = this._receiptFiles.map((f) => {
            const brandLabel = f.brand?.trim() || t("wigs.unbranded");
            const dups = f.duplicates ?? [];
            const template = t(
                f.duplicate_of
                    ? "wigs.receipt.duplicate"
                    : "wigs.receipt.hung",
                { name: "\u0001", brand: "\u0002", brands: "\u0003" },
            );
            // The {brands} sentinel becomes one clickable link per
            // closet location already holding this device (owner ask,
            // 2026-07-20) -- each jumps to THAT duplicate's row.
            const brandsList = dups.map(
                (dup, i) => html`${i > 0 ? ", " : ""}<button
                        class="receipt-link"
                        @click=${() =>
                            this._jumpToWig({
                                filename: dup.filename,
                                brand: dup.brand,
                            })}
                    >${dup.brand?.trim() || t("wigs.unbranded")}</button>`,
            );
            const segments = template.split(/([\u0001\u0002\u0003])/);
            return html`${segments.map((seg) =>
                seg === "\u0001"
                    ? html`<button
                          class="receipt-link"
                          @click=${() => this._jumpToWig(f)}
                      >${f.name}</button>`
                    : seg === "\u0002"
                      ? html`<button
                            class="receipt-link"
                            @click=${() => this._jumpToBrand(f)}
                        >${brandLabel}</button>`
                      : seg === "\u0003"
                        ? html`${brandsList}`
                        : html`${seg}`,
            )}`;
        });
        return html`${parts.map(
            (part, i) => html`${i > 0 ? html` \u00b7 ` : ""}${part}`,
        )}${this._receiptSuffix
            ? html` \u00b7 ${this._receiptSuffix}`
            : ""}`;
    }

    private _jumpToWig(f: { filename: string; brand: string | null }): void {
        const open = new Set(this._openBrands);
        open.add(this._brandKeyFor(f.brand));
        this._openBrands = open;
        const id = `wig:${f.filename}`;
        this._pendingScrollId = id;
        this._bloomId = id;
        window.setTimeout(() => {
            this._bloomId = null;
        }, 2600);
    }

    private _jumpToBrand(f: { brand: string | null }): void {
        const key = this._brandKeyFor(f.brand);
        const open = new Set(this._openBrands);
        open.add(key);
        this._openBrands = open;
        this._pendingScrollId = `brand:${key}`;
    }

    updated(): void {
        if (!this._pendingScrollId) return;
        const row = this.shadowRoot?.querySelector(
            `[data-row-id="${CSS.escape(this._pendingScrollId)}"], ` +
                `[data-brand-id="${CSS.escape(this._pendingScrollId)}"]`,
        );
        if (row) {
            row.scrollIntoView({ behavior: "smooth", block: "center" });
            this._pendingScrollId = null;
        }
    }

    private async _onDrop(e: DragEvent): Promise<void> {
        e.preventDefault();
        this._dragOver = false;
        const files = e.dataTransfer?.files;
        if (!files) return;
        for (const file of Array.from(files)) {
            await this._uploadText(await file.text(), file.name);
        }
    }

    private _browse(): void {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = ".json,.ir,.conf,application/json,text/plain";
        input.multiple = true;
        input.onchange = async () => {
            for (const file of Array.from(input.files ?? [])) {
                await this._uploadText(await file.text(), file.name);
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
            this._flash((err as Error).message, "warn");
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
            <div class="page-title">
                <ha-svg-icon .path=${ICON_WIG}></ha-svg-icon>
                ${t("wigs.title")}
                <span class="page-count"
                    >(${tp("wigs.count", counts.all)})</span
                >
            </div>
            <div
                class="drop-bar ${this._dragOver ? "over" : ""} ${this
                    ._receipt
                    ? `receipt-${this._receiptKind}`
                    : ""}"
                @dragover=${(e: DragEvent) => {
                    e.preventDefault();
                    this._dragOver = true;
                }}
                @dragleave=${() => (this._dragOver = false)}
                @drop=${this._onDrop}
            >
                <span class="drop-icon"
                    >${this._receipt
                        ? this._receiptKind === "warn"
                            ? html`&#9888;`
                            : html`&#10003;`
                        : html`&#8853;`}</span
                >
                <div>
                    ${this._receipt
                        ? html`<div class="t1">
                                  ${this._renderReceiptLine()}
                              </div>
                              <div class="t2">${t("wigs.drop.title")}</div>`
                        : html`<div class="t1">${t("wigs.drop.title")}</div>
                              <div class="t2">${t("wigs.drop.hint")}</div>`}
                </div>
                <button class="browse" @click=${this._browse}>
                    ${t("wigs.drop.browse")}
                </button>
            </div>

            ${this._error
                ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                : ""}
            ${this._notice
                ? html`<div class="notice ${this._noticeKind}">
                      ${this._notice}
                  </div>`
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
            ${this._renderPeek()}
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
                data-brand-id="brand:${brand.key}"
            >
                <div
                    class="brand-head"
                    @click=${() => this._toggleBrand(brand.key)}
                >
                    <span class="brand-name">${brand.label}</span>
                    <span class="dots">
                        ${libCount > 0
                            ? html`<span class="count-chip lib"
                                  >${tp("wigs.count", libCount)}</span
                              >`
                            : ""}
                        ${mineCount > 0
                            ? html`<span class="count-chip mine"
                                  >${tp("wigs.count", mineCount)}</span
                              >`
                            : ""}
                    </span>
                    <ha-svg-icon
                        class="chev"
                        .path=${open ? ICON_COLLAPSE : ICON_EXPAND}
                    ></ha-svg-icon>
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
            <div
                class="wig-row ${this._bloomId === row.id ? "bloom" : ""}"
                data-row-id=${row.id}
            >
                <span class="wdot ${row.source === "local" ? "mine" : "lib"}"
                ></span>
                <span class="wig-name">${row.label}</span>
                ${row.wig?.model?.trim()
                    ? html`<span class="wig-model"
                          >&ndash; ${row.wig.model.trim()}</span
                      >`
                    : ""}
                <button
                    class="wig-count"
                    @click=${(e: Event) => this._togglePeek(row, e)}
                >
                    ${tp("wigs.signals", row.signalCount)}
                </button>
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
                        class="action-btn clip-btn"
                        ?disabled=${this._busyId === row.id}
                        @click=${() => this._tryOn(row)}
                    >
                        ${t("wigs.clip_it")}
                    </button>
                    ${row.wig
                        ? html`<button
                              class="action-btn delete-btn row-del"
                              @click=${() =>
                                  (this._confirmDelete = row.wig!)}
                          >
                              ${t("common.delete")}
                          </button>`
                        : ""}
                </span>
            </div>
        `;
    }

    private _renderEditor() {
        // One dialog at a time (the stacked-dialog z-order bug, owner
        // bench find 2026-07-20): while a delete confirmation is up --
        // opened from the editor OR straight from a row's delete glyph
        // -- it replaces the editor; Cancel restores whatever was open.
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
        const wig = this._editing;
        if (!wig) return "";
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

    static styles = [dialogStyles, actionChipStyles, css`
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
            color: var(--primary-text-color);
            font-size: 13px;
        }
        /* Success wears green (positive outcome, owner ruling); only a
           failure gets the warning tint. */
        .notice.ok {
            background: rgba(46, 125, 50, 0.12);
            border: 1px solid rgba(46, 125, 50, 0.45);
        }
        .notice.warn {
            background: rgba(230, 81, 0, 0.1);
            border: 1px solid rgba(230, 81, 0, 0.45);
        }
        .drop-bar {
            /* Idle: quiet gray furniture with the closet's oxblood as
               a dashed accent stroke only (owner ruling: a full red
               field reads as danger, not invitation). */
            border: 2px dashed var(--wigs-accent-border);
            border-radius: 10px;
            background: rgba(120, 144, 156, 0.08);
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 11px 16px;
            color: var(--secondary-text-color);
            margin-bottom: 14px;
        }
        .drop-bar.over {
            background: rgba(142, 59, 59, 0.28);
        }
        /* The bar IS the receipt after a drop (owner ruling): green for
           hung, yellow for a duplicate, warning tint for a failure;
           persists until the next drop replaces it. */
        .drop-bar.receipt-ok {
            background: rgba(46, 125, 50, 0.07);
            border-color: rgba(46, 125, 50, 0.55);
            color: #66bb6a;
            transition: background 0.4s ease, border-color 0.4s ease;
        }
        .drop-bar.receipt-dup {
            background: rgba(245, 166, 35, 0.12);
            border-color: rgba(245, 166, 35, 0.55);
            color: #f5a623;
            transition: background 0.4s ease, border-color 0.4s ease;
        }
        .drop-bar.receipt-warn {
            background: rgba(230, 81, 0, 0.1);
            border-color: rgba(230, 81, 0, 0.55);
            color: #e65100;
            transition: background 0.4s ease, border-color 0.4s ease;
        }
        .receipt-link {
            background: none;
            border: none;
            padding: 0;
            font: inherit;
            color: inherit;
            font-weight: 600;
            text-decoration: underline;
            text-underline-offset: 2px;
            cursor: pointer;
        }
        .drop-bar.receipt-ok .browse,
        .drop-bar.receipt-dup .browse,
        .drop-bar.receipt-warn .browse {
            border-color: currentColor;
            color: inherit;
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
            border: 1px solid var(--divider-color);
            color: var(--secondary-text-color);
            background: var(--card-background-color, #fff);
            border-radius: 6px;
            padding: 5px 12px;
            cursor: pointer;
        }
        .drop-bar .browse:hover {
            border-color: var(--wigs-accent);
            color: var(--wigs-accent);
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
        /* Count chips (owner re-ruling 2026-07-20, supersedes the c6
           14px dots): same anatomy as the linked-devices chip, worded
           counts, slate = library / oxblood = yours. */
        .count-chip {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
            flex-shrink: 0;
            /* One width for every chip, sized for "99 devices", so the
               column of chips reads as a column (owner ruling). */
            min-width: 92px;
            box-sizing: border-box;
            text-align: center;
        }
        .count-chip.lib {
            background: rgba(120, 144, 156, 0.15);
            color: var(--wigs-lib);
            border: 1px solid rgba(120, 144, 156, 0.3);
        }
        .count-chip.mine {
            background: rgba(142, 59, 59, 0.15);
            color: #b06a6a;
            border: 1px solid rgba(142, 59, 59, 0.35);
        }
        .chev {
            color: var(--secondary-text-color);
            --mdc-icon-size: 20px;
            margin-left: 4px;
        }
        .brand.open .chev {
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
        /* Landing bloom: the freshly-hung wig glows briefly so the eye
           finds where the drop went (same cue language as the Mirror's
           live-send bloom). */
        .wig-row.bloom {
            animation: wig-bloom 2.4s ease-out;
        }
        @keyframes wig-bloom {
            0% {
                background: rgba(46, 125, 50, 0.35);
            }
            100% {
                background: transparent;
            }
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
        /* Page title -- same anatomy as the Clipper/Sniffer/Plucker
           toolbars (24px tool icon in the tab accent, 1.1rem title,
           gray count), so the Closet introduces itself like every
           other station in the shop. */
        .page-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
            margin-bottom: 16px;
        }
        .page-title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--wigs-accent);
        }
        .page-count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .wig-name {
            font-weight: 500;
            color: var(--primary-text-color);
        }
        /* Model rides inline after the name in secondary gray (owner
           ask, 2026-07-20): keeps the 46px row and reads as a detail,
           not a second name. */
        .wig-model {
            color: var(--secondary-text-color);
            font-size: 12.5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .wig-count {
            font-size: 12px;
            color: var(--secondary-text-color);
            background: none;
            border: none;
            padding: 0;
            font-family: inherit;
            cursor: pointer;
            text-decoration: underline dotted transparent;
        }
        .wig-count:hover {
            color: var(--primary-text-color);
            text-decoration-color: var(--secondary-text-color);
        }
        .linked-scrim {
            position: fixed;
            inset: 0;
            z-index: 39;
        }
        .peek-popover {
            position: fixed;
            z-index: 40;
            min-width: 180px;
            max-height: 260px;
            overflow-y: auto;
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
            padding: 6px 4px;
        }
        .peek-entry {
            padding: 5px 12px;
            font-size: 12.5px;
            color: var(--primary-text-color);
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
        /* CLIP is the shared action-chip anatomy (same radius, padding,
           and uppercase as every other button) in the Clipper's copper,
           because it does the same kind of thing as Add Remote. Delete
           is the stock shared delete chip, untouched. */
        .action-btn.clip-btn {
            color: #b87333;
            border-color: rgba(184, 115, 51, 0.35);
        }
        .action-btn.clip-btn:hover:not(:disabled) {
            background: rgba(184, 115, 51, 0.08);
        }
        .row-del {
            margin-left: 8px;
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
