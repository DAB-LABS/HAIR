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
 * rows stay non-editable but carry download / CLIP / ADOPT since
 * v0.8.1 via the codebook->wig snapshot primitive) and TRY ON flush
 * right. TRY ON materializes through the same import path as the
 * Clipper picker:
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
import {
    ICON_TRASH,
    TRASH_VIEWBOX,
    trashButtonStyles,
} from "./ir-icons.js";
import { HairApi } from "./api.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";
import { popoverStyles } from "./ir-popover-styles.js";
import { COMB_PATH } from "./ir-comb-report.js";
import "./ir-comb-report.js";
import { displayTemp, installUnit } from "./temperature.js";
import "./ir-confirm-dialog.js";
import "./ir-supersede-dialog.js";
import "./ir-count-dot.js";
import "./ir-claims-ledger.js";
import "./ir-promote-dialog.js";
import type {
    CodeBrand,
    CodeCodebook,
    FittingSummary,
    MatrixSummary,
    ReverseSupersessionBlock,
    SupersessionBlock,
    WigInfo,
    WigInvalid,
    WigsList,
} from "./types.js";

type FilterChip = "all" | "library" | "yours" | "fitted" | "unfitted";

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
export const ICON_WIG =
    "M 2.45,21.37 C 1.74,20.36 1.30,18.28 0.95,18.06 C 0.59,17.83 0.40,15.85 0.57,15.36 C 0.74,14.87 0.11,13.99 0.01,13.26 C -0.08,12.53 0.44,11.84 0.42,11.52 C 0.41,11.20 0.22,9.08 1.02,7.47 C 1.45,6.62 2.67,5.28 3.93,4.70 C 5.05,4.18 6.23,4.38 6.31,4.25 C 6.46,3.98 7.34,2.27 7.95,2.45 C 7.11,3.28 7.24,4.21 7.24,4.21 C 7.24,4.21 10.07,2.34 12.34,2.45 C 14.61,2.56 19.16,5.47 19.31,5.56 C 19.46,5.66 18.97,4.63 18.11,3.50 C 18.97,3.54 20.34,6.20 20.51,6.35 C 20.68,6.50 20.79,6.37 20.51,5.23 C 21.09,5.30 21.33,6.87 21.63,7.44 C 21.93,8.00 22.79,8.02 22.72,10.13 C 24.03,10.21 24.22,14.05 23.80,14.78 C 23.63,17.29 23.21,18.34 22.79,19.31 C 22.37,20.29 21.82,21.56 21.82,21.56 C 21.82,21.56 21.95,17.42 21.24,14.39 C 20.74,12.26 19.60,10.98 18.71,10.79 C 16.55,10.34 12.30,10.70 11.81,11.30 C 10.72,11.69 5.38,9.87 4.28,10.73 C 3.64,11.24 2.89,13.16 2.90,14.67 C 2.91,15.73 3.57,15.53 3.61,16.58 C 3.63,17.16 3.06,17.54 2.75,18.45 C 2.50,19.18 2.50,20.39 2.45,21.37";

// Shared expand chevrons -- the same mdi paths the Sniffer/Clipper
// cards use, so every disclosure arrow in the panel is one glyph.
const ICON_EXPAND = "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";
const ICON_COLLAPSE = "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z";

// The drop-bar title names the five formats the closet accepts; each
// name links to the format's home. The locale strings carry {wig}-style
// placeholders so every language keeps its own sentence around the
// untranslated format names (localize.ts owner ruling), and the render
// splits on the placeholders instead of substituting text.
const DROP_FORMAT_LINKS: Record<string, { label: string; url: string }> = {
    wig: {
        label: "Wig",
        // Points at the community wig-sharing repo now that it exists,
        // replacing the docs/wig-format.md link (owner ruling 2026-07-29).
        url: "https://github.com/DAB-LABS/WigShop",
    },
    smartir: {
        label: "SmartIR",
        url: "https://github.com/smartHomeHub/SmartIR",
    },
    flipper: {
        label: "Flipper",
        url: "https://github.com/logickworkshop/Flipper-IRDB",
    },
    lirc: { label: "LIRC", url: "https://lirc.sourceforge.net/remotes/" },
    girr: { label: "Girr", url: "https://www.harctoolbox.org/Girr.html" },
};
const DROP_FORMAT_SPLIT = /\{(wig|smartir|flipper|lirc|girr)\}/g;

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
    // The drop-bar doorway: an arriving Wig named an ancestor still here.
    @state() private _supersede: {
        block: SupersessionBlock;
        newFilename: string;
    } | null = null;
    // The reverse-direction re-confirm (v0.9.7 Second Fitting, amendment
    // v2 section 3): the arrival names an id a newer LOCAL wig already
    // supersedes. Holds the original text/filename so Import Anyway can
    // resend the identical upload with confirmed set.
    @state() private _reverseSupersede: {
        block: ReverseSupersessionBlock;
        text: string;
        filename: string;
    } | null = null;
    @state() private _bloomId: string | null = null;
    private _pendingScrollId: string | null = null;
    @state() private _busyId: string | null = null;
    // The claims ledger: the row's check opens the record of who
    // attested what. Read only -- attesting happens on the device, at
    // SAVE TO CLOSET (v0.9.5).
    @state() private _ledgerWig: WigInfo | null = null;
    // Smart Perm: the wig whose comb report is open.
    @state() private _combWig: WigInfo | null = null;
    // Adopt Device (v0.8.1): the wig the promote dialog is open for.
    @state() private _adoptWig: WigInfo | null = null;
    // Adopt from a library row: the codebook row instead (no wig file).
    @state() private _adoptCodebook: ClosetRow | null = null;
    @state() private _linkedPopoverId: string | null = null;
    private _linkedPopoverPos = { top: 0, left: 0 };
    @state() private _peekId: string | null = null;
    private _peekPos = { top: 0, left: 0 };
    private _peekNames: string[] = [];
    // Matrix rows peek a SUMMARY, not 300 cell names (Cold Cuts,
    // owner ruling 2026-07-28): vocabularies and the temp range.
    private _peekMatrix: MatrixSummary | null = null;
    // The gated matrix clip (Cold Cuts second half, 2026-07-29): CLIP
    // on a matrix row confirms first -- the open clip mints one
    // Clipper row per state, and 2,689 rows must be a choice, never a
    // surprise. Non-matrix rows keep the instant clip.
    @state() private _clipConfirm: ClosetRow | null = null;

    // Editor dialog state.
    @state() private _editing: WigInfo | null = null;
    @state() private _editName = "";
    @state() private _editBrand = "";
    @state() private _editModel = "";
    @state() private _editKind = "";
    @state() private _editNotes = "";
    // Identifier fields (v0.8.0): single input each; commas become
    // the format's list form server-side.
    @state() private _editFccId = "";
    @state() private _editUpc = "";
    @state() private _editAsin = "";
    @state() private _editOem = "";
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

    /** Reload the closet. ``quiet`` skips the loading state, which
     * matters more than it sounds: render() short-circuits to a
     * spinner while loading, so a normal refresh removes every open
     * dialog from the DOM and rebuilds it from scratch. That is fine
     * for refreshes that follow a dialog closing, and wrong for one
     * that happens WHILE a dialog is open -- rebuilding it would throw
     * away whatever the person has typed into it (owner bench
     * 2026-07-30, when a replace mid-fitting reset the session's
     * emitter and send-times picks). */
    private async _refresh(quiet = false): Promise<void> {
        this._loading = !quiet;
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

    /** Open the comb ledger on a wig named by filename.
     *
     * The upload and adopt receipts carry a filename; the report wants
     * the live WigInfo, so it is looked up in the list _refresh has
     * just reloaded. Silently does nothing if the lookup misses --
     * an unopened report is a far smaller failure than an exception
     * thrown over a successful import. */
    private _combAfterUpload(filename: string | undefined): void {
        if (!filename) return;
        const wig = this._wigs.find((w) => w.filename === filename);
        if (wig) this._combWig = wig;
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
        } else if (this._filter === "fitted") {
            // Fitted mirrors the check mark: any fitting state, green
            // or yellow (owner ruling 2026-07-26).
            rows = rows.filter((r) => r.wig?.fitting?.state);
        } else if (this._filter === "unfitted") {
            // Only fittable things count as unfitted: local wig files.
            // Library codebooks cannot carry fittings.
            rows = rows.filter((r) => r.wig && !r.wig.fitting?.state);
        }
        const query = this._search.trim().toLowerCase();
        if (query && !brand.label.toLowerCase().includes(query)) {
            rows = rows.filter((r) => this._rowMatches(r, query));
        }
        return rows;
    }

    /** Search coverage beyond the label (v0.8.1, paying off the
     * v0.8.0 identifiers block): the kind and every identifier value,
     * so typing a UPC straight off the box (or "candles") finds the
     * wig. Library rows have neither and keep the label-only match. */
    private _rowMatches(r: ClosetRow, query: string): boolean {
        if (r.label.toLowerCase().includes(query)) return true;
        const wig = r.wig;
        if (!wig) return false;
        if (wig.kind?.toLowerCase().includes(query)) return true;
        for (const value of Object.values(wig.identifiers ?? {})) {
            const list = Array.isArray(value) ? value : [value];
            if (
                list.some((v) =>
                    String(v).toLowerCase().includes(query),
                )
            ) {
                return true;
            }
        }
        return false;
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
        this._peekMatrix = row.wig?.matrix ?? null;
        this._peekId = row.id;
    }

    /** The peek's temperature line, converted to the viewer's install
     * unit when it differs from the file's (unit ruling 2026-07-29:
     * displays convert dynamically, the summary payload stays
     * native). Whole-degree fallback for the conversion: the summary
     * carries no precision, and corpus bounds are whole degrees. */
    private _renderPeekTempRange(): string {
        const m = this._peekMatrix!;
        const viewUnit = installUnit(this.hass);
        return t("wigs.peek.temp", {
            min: displayTemp(m.min_temp, m.unit, viewUnit),
            max: displayTemp(m.max_temp, m.unit, viewUnit),
            unit: viewUnit,
        });
    }

    private _renderPeek() {
        if (!this._peekId) return "";
        if (!this._peekMatrix && this._peekNames.length === 0) return "";
        // Matrix rows: the shop window shows the shape of the lattice
        // (modes / fans / swings / temp range), never a cell list --
        // 300 rows is not a popover (owner ruling 2026-07-28).
        const body = this._peekMatrix
            ? html`<div class="peek-entry">
                      ${t("wigs.peek.modes", {
                          list: this._peekMatrix.modes.join(", "),
                      })}
                  </div>
                  ${this._peekMatrix.fan_modes.length
                      ? html`<div class="peek-entry">
                            ${t("wigs.peek.fans", {
                                list: this._peekMatrix.fan_modes.join(
                                    ", ",
                                ),
                            })}
                        </div>`
                      : ""}
                  ${this._peekMatrix.swing_modes.length
                      ? html`<div class="peek-entry">
                            ${t("wigs.peek.swings", {
                                list: this._peekMatrix.swing_modes.join(
                                    ", ",
                                ),
                            })}
                        </div>`
                      : ""}
                  <div class="peek-entry">
                      ${this._renderPeekTempRange()}
                  </div>`
            : this._peekNames.map(
                  (name) => html`<div class="peek-entry">${name}</div>`,
              );
        return html`<div
                class="linked-scrim"
                @click=${() => (this._peekId = null)}
            ></div>
            <div
                class="peek-popover"
                style="top: ${this._peekPos.top}px; left: ${this._peekPos
                    .left}px;"
            >
                ${body}
            </div>`;
    }

    // --- Try on ---

    private async _tryOn(
        row: ClosetRow,
        includeMatrix = false,
    ): Promise<void> {
        this._busyId = row.id;
        try {
            const result = await this.api.importCodeRemote(
                row.id,
                undefined,
                includeMatrix,
            );
            if (includeMatrix) {
                // The matrix clip's receipt (2026-07-28): the confirm
                // promised "up to N", so the receipt reports what was
                // actually created and, when byte-identical cells
                // collapsed under the one-code-per-remote rule, says
                // where the shortfall went. Non-matrix clips keep the
                // plain tried-on flash below.
                const duplicates = result.duplicates ?? 0;
                this._flash(
                    duplicates > 0
                        ? t("wigs.clip_matrix_done_duplicates", {
                              imported: String(result.imported),
                              duplicates: String(duplicates),
                          })
                        : t("wigs.clip_matrix_done", {
                              imported: String(result.imported),
                          }),
                );
            } else {
                this._flash(
                    t("wigs.tried_on", {
                        name: result.device.label ?? row.label,
                    }),
                );
            }
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

    /** What the open clip will mint at most: every cell, Off, On when
     * the matrix has one, and the wig's flat extras (its plain
     * signals). */
    private _clipCount(row: ClosetRow): number {
        const matrix = row.wig?.matrix;
        if (!matrix) return row.signalCount;
        // An upper bound, not an exact count: byte-identical duplicate
        // cells collapse on the Clipper (one-code-per-remote rule), so
        // the true number is unknowable upfront. The confirm text says
        // "up to" for the same reason.
        return matrix.cells + 1 + (matrix.has_on ? 1 : 0) + row.signalCount;
    }

    /** CLIP click: matrix rows confirm the row count first; signal
     * wigs keep today's instant clip. */
    private _onClipClick(row: ClosetRow): void {
        if (row.wig?.matrix) {
            this._clipConfirm = row;
            return;
        }
        void this._tryOn(row);
    }

    private _renderClipConfirm() {
        const row = this._clipConfirm;
        if (!row) return "";
        const count = this._clipCount(row);
        const message =
            t("wigs.clip_matrix_confirm", { count: String(count) }) +
            (count > 500 ? ` ${t("wigs.clip_matrix_slow")}` : "");
        return html`<ir-confirm-dialog
            title=${row.label}
            message=${message}
            confirmLabel=${t("wigs.clip_it")}
            @confirmed=${() => {
                const target = this._clipConfirm!;
                this._clipConfirm = null;
                void this._tryOn(target, true);
            }}
            @closed=${() => (this._clipConfirm = null)}
        ></ir-confirm-dialog>`;
    }

    private _renderSupersede() {
        const s = this._supersede;
        if (!s) return "";
        return html`<ir-supersede-dialog
            .block=${s.block}
            .newFilename=${s.newFilename}
            @replace=${this._onSupersedeReplace}
            @keep-both=${this._onSupersedeKeepBoth}
            @cancel-import=${this._onSupersedeCancelImport}
            @closed=${() => (this._supersede = null)}
        ></ir-supersede-dialog>`;
    }

    /** The reverse-direction re-confirm (v0.9.7 Second Fitting,
     * amendment v2 section 3): the arrival names an id a newer LOCAL
     * wig already lists as superseded. Same dialog anatomy as the
     * clip-matrix confirm above -- a plain two-action ir-confirm-dialog,
     * not the elaborate replace/keep-both/cancel doorway, because
     * there is only ever one decision here. */
    private _renderReverseSupersede() {
        const r = this._reverseSupersede;
        if (!r) return "";
        return html`<ir-confirm-dialog
            title=${t("supersede.reverse_title")}
            message=${t("supersede.reverse_message", {
                name: r.block.name,
                count: String(r.block.signal_count),
            })}
            confirmLabel=${t("supersede.reverse_import_anyway")}
            @confirmed=${() => {
                const target = this._reverseSupersede!;
                this._reverseSupersede = null;
                void this._uploadText(target.text, target.filename, true);
            }}
            @closed=${() => (this._reverseSupersede = null)}
        ></ir-confirm-dialog>`;
    }

    private async _onSupersedeReplace(e: CustomEvent): Promise<void> {
        const { newFilename, oldFilename, relink, topupDeviceIds } = e.detail;
        const oldName = this._supersede?.block.old_name ?? oldFilename;
        try {
            await this.api.wigsSupersede(
                newFilename, oldFilename, relink, topupDeviceIds,
            );
            // Name what happened onto the existing receipt line.
            this._receiptSuffix = [
                this._receiptSuffix,
                t("supersede.receipt_replaced", { name: oldName }),
            ].filter(Boolean).join(" · ");
            this._supersede = null;
            await this._refresh();
        } catch (err) {
            this._receiptKind = "warn";
            this._receiptFiles = [];
            this._receipt = (err as Error).message;
            this._supersede = null;
        }
    }

    private _onSupersedeKeepBoth(): void {
        this._receiptSuffix = [
            this._receiptSuffix,
            t("supersede.receipt_kept"),
        ].filter(Boolean).join(" · ");
        this._supersede = null;
    }

    /** CANCEL, drop-bar doorway only (owner ruling: "Cancel means undo
     * this import"): the arrival just written is deleted outright, not
     * merely dismissed -- Keep Both is the dismiss-and-leave-it action;
     * this one undoes the import. */
    private async _onSupersedeCancelImport(): Promise<void> {
        const s = this._supersede;
        if (!s) return;
        try {
            await this.api.wigsDelete(s.newFilename);
            this._receiptSuffix = [
                this._receiptSuffix,
                t("supersede.receipt_cancelled"),
            ].filter(Boolean).join(" · ");
        } catch (err) {
            this._receiptKind = "warn";
            this._receipt = (err as Error).message;
        } finally {
            this._supersede = null;
            await this._refresh();
        }
    }

    // --- Upload (drop bar + browse) ---

    private async _uploadText(
        text: string, filename = "", confirmed = false,
    ): Promise<void> {
        try {
            const result = await this.api.wigsUpload(text, filename, confirmed);
            // Reverse-direction check first: dialog before filing, so
            // nothing here has written anything yet -- Cancel is just
            // dropping this state, not undoing a file already on disk
            // (that is the forward doorway's CANCEL, further below).
            if (result.reverse_supersession) {
                this._reverseSupersede = {
                    block: result.reverse_supersession,
                    text,
                    filename,
                };
                return;
            }
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
            const suffixes: string[] = [];
            if ((result.skipped ?? []).length > 0) {
                suffixes.push(t("wigs.upload_partial", {
                    count: String(result.skipped!.length),
                }));
            }
            // Old whole-file fittings are set aside on import -- they
            // cannot become per-row claims (hard rule 6), and a drop
            // nobody is told about reads as silent data loss. The
            // count comes from the same entries the receipt renders.
            const dropped = files.reduce(
                (n, f) => n + (f.dropped_fittings ?? 0), 0,
            );
            if (dropped > 0) {
                suffixes.push(tp("wigs.upload_dropped_fittings", dropped));
            }
            this._receiptSuffix = suffixes.join(" \u00b7 ");
            this._receiptKind = anyDup ? "dup" : "ok";
            this._receipt = "files";

            // Still no auto-jump: the receipt's name/brand links are
            // the invitation, and the user pulls rather than being
            // shoved down the list. Just make sure a Library filter
            // cannot hide the arrival if they DO click.
            if (this._filter === "library") this._filter = "all";
            await this._refresh();
            // The comb IS shown unasked, which is the one exception
            // (owner ruling 2026-08-02) and a different thing from
            // jumping: an arriving wig's codes have never been checked
            // against each other on this install, and the moment to
            // learn that 48 of them disagree is now, not after a
            // fitting. Only when exactly one wig landed -- a foreign
            // format can convert to five at once, and five stacked
            // dialogs is not a report.
            // A superseding Wig opens the replace dialog instead of the
            // auto-comb: two stacked dialogs is not a report, and the
            // replace decision comes first. The comb stays a click away.
            if (result.supersession && result.filename) {
                this._supersede = {
                    block: result.supersession,
                    newFilename: result.filename,
                };
            } else {
                const fresh = files.filter((f) => !f.duplicate_of);
                if (fresh.length === 1) {
                    this._combAfterUpload(fresh[0].filename);
                }
            }
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

    /**
     * Drop-bar title with each accepted format linked to its home
     * (owner ask, 2026-07-29). Splitting on the placeholder tokens
     * keeps the alternation text/token, so the links land wherever
     * the language puts them. stopPropagation keeps a link click from
     * reaching the drop-bar's handlers.
     */
    private _renderDropTitle() {
        const segments = t("wigs.drop.title").split(DROP_FORMAT_SPLIT);
        return html`${segments.map((seg, i) => {
            const link = i % 2 === 1 ? DROP_FORMAT_LINKS[seg] : undefined;
            return link
                ? html`<a
                      class="fmt-link"
                      href=${link.url}
                      target="_blank"
                      rel="noopener"
                      @click=${(e: Event) => e.stopPropagation()}
                      >${link.label}</a
                  >`
                : html`${seg}`;
        })}`;
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

    /** One file per drop (owner ruling 2026-08-02).
     *
     * The loop that used to be here hung every dropped file but wrote
     * the receipt fresh each time, so a five-file drop reported the
     * fifth and the other four landed with no trace. Refusing the
     * whole drop is the honest version: nothing arrives that the
     * fitter cannot see arrive. */
    private async _onDrop(e: DragEvent): Promise<void> {
        e.preventDefault();
        this._dragOver = false;
        const files = Array.from(e.dataTransfer?.files ?? []);
        if (files.length === 0) return;
        if (!this._acceptsOne(files.length)) return;
        await this._uploadText(await files[0].text(), files[0].name);
    }

    private _browse(): void {
        const input = document.createElement("input");
        input.type = "file";
        input.accept =
            ".json,.ir,.conf,.girr,.xml,application/json,text/plain";
        input.onchange = async () => {
            const files = Array.from(input.files ?? []);
            if (files.length === 0) return;
            if (!this._acceptsOne(files.length)) return;
            await this._uploadText(await files[0].text(), files[0].name);
        };
        input.click();
    }

    /** Guard for both entry points: true when exactly one file came
     * in, false after posting the refusal receipt. */
    private _acceptsOne(count: number): boolean {
        if (count <= 1) return true;
        this._receiptKind = "warn";
        this._receiptFiles = [];
        this._receiptSuffix = "";
        this._receipt = t("wigs.upload_one_at_a_time", {
            count: String(count),
        });
        return false;
    }

    // --- Editor dialog ---

    private _openEditor(wig: WigInfo): void {
        this._editing = wig;
        this._editName = wig.name;
        this._editBrand = wig.brand ?? "";
        this._editModel = wig.model ?? "";
        this._editNotes = wig.notes ?? "";
        const ident = (key: string): string => {
            const value = wig.identifiers?.[key];
            if (!value) return "";
            return Array.isArray(value) ? value.join(", ") : value;
        };
        this._editFccId = ident("fcc_id");
        this._editUpc = ident("upc");
        this._editAsin = ident("asin");
        this._editOem = ident("oem");
        this._editError = null;
    }

    /** Seed the promote dialog's type from the wig's kind (ruled
     * 2026-07-28): the deferred type-inference, nearly free now that
     * kind exists. Unknown kinds fall back to empty (dialog default). */
    private _typeFromKind(kind: string | null | undefined): string {
        const map: Record<string, string> = {
            fan: "fan",
            ac: "ac",
            heater: "ac",
            light: "light",
            candles: "light",
            tv: "media_player",
            soundbar: "media_player",
            receiver: "media_player",
            settopbox: "media_player",
            projector: "media_player",
            blinds: "screen",
            screen: "screen",
        };
        return map[kind ?? ""] ?? "";
    }

    /**
     * ADOPT DEVICE click, count-dot convention (v0.6.6 Assign/Trigger
     * precedent, owner ask 2026-07-27): zero linked devices opens the
     * adopt dialog directly; one or more opens the linked-devices
     * popover, which carries its own "+ new device" accent entry for
     * adopting again.
     */
    private _onAdoptClick(row: ClosetRow, e: Event): void {
        if (!row.wig) {
            // Library row (v0.8.1): no wig file, no linked scan --
            // straight to the dialog on the codebook road.
            this._adoptCodebook = row;
            return;
        }
        if (!row.wig.linked_devices?.length) {
            this._adoptWig = row.wig;
            return;
        }
        this._toggleLinkedPopover(row.id, e);
    }

    private _toggleLinkedPopover(rowId: string, e: Event): void {
        e.stopPropagation();
        if (this._linkedPopoverId === rowId) {
            this._linkedPopoverId = null;
            return;
        }
        const rect = (
            e.currentTarget as HTMLElement
        ).getBoundingClientRect();
        // Right-aligned under the Adopt button (the anchor now lives on
        // the row's right edge), mirroring the Assign popover's math.
        this._linkedPopoverPos = {
            top: rect.bottom + 6,
            left: Math.max(8, rect.right - 220),
        };
        this._linkedPopoverId = rowId;
    }

    private _renderLinkedWigPopover() {
        if (!this._linkedPopoverId) return "";
        const wig = this._wigs.find(
            (w) => `wig:${w.filename}` === this._linkedPopoverId,
        );
        const linked = wig?.linked_devices ?? [];
        if (!wig || linked.length === 0) return "";
        return html`<div
                class="linked-scrim"
                @click=${() => (this._linkedPopoverId = null)}
            ></div>
            <div
                class="action-popover"
                style="top: ${this._linkedPopoverPos.top}px; left: ${this
                    ._linkedPopoverPos.left}px;"
            >
                <div class="popover-header">
                    ${tp("wigs.linked", linked.length)}
                </div>
                <button
                    class="popover-item accent"
                    @click=${(e: Event) => {
                        e.stopPropagation();
                        this._linkedPopoverId = null;
                        this._adoptWig = wig;
                    }}
                >
                    <span>${t("wigs.linked_new")}</span>
                </button>
                <div class="popover-divider"></div>
                ${linked.map(
                    (entry) => html`<button
                        class="popover-item"
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._linkedPopoverId = null;
                            this.dispatchEvent(
                                new CustomEvent("navigate-device", {
                                    detail: entry.device_id,
                                    bubbles: true,
                                    composed: true,
                                }),
                            );
                        }}
                    >
                        <span class="popover-name"
                            >${entry.device_name}</span
                        >
                        <ha-svg-icon
                            class="linked-chevron"
                            .path=${"M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z"}
                        ></ha-svg-icon>
                    </button>`,
                )}
            </div>`;
    }

    /** Curated kinds plus every kind already used in this closet, so
     * a custom kind typed once becomes a suggestion from then on
     * (owner ruling 2026-07-27: dropdown plus custom, self-growing,
     * no central registry). */
    private _kindSuggestions(): string[] {
        const curated = [
            "tv", "soundbar", "receiver", "settopbox", "projector",
            "fan", "light", "candles", "ac", "heater", "blinds",
        ];
        const seen = new Set(curated);
        for (const wig of this._wigs) {
            if (wig.kind && !seen.has(wig.kind)) {
                seen.add(wig.kind);
                curated.push(wig.kind);
            }
        }
        return curated;
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
            library: t("wigs.origin.library"),
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
                kind: this._editKind.trim(),
                notes: this._editNotes.trim(),
                fcc_id: this._editFccId.trim(),
                upc: this._editUpc.trim(),
                asin: this._editAsin.trim(),
                oem: this._editOem.trim(),
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

    private async _downloadText(
        filename: string, text: string,
    ): Promise<void> {
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
    }

    private async _download(wig: WigInfo | null): Promise<void> {
        if (!wig) return;
        try {
            // The tier now rides in the name the server composes from the
            // wig's own fields (<brand>-<kind>-<model>[-<tier>]), so the
            // filename and the row's check glyph can never disagree and
            // the client no longer composes a name at all. Hyphenated,
            // never dotted -- the dot was what failed the shop's upload.
            const { download_filename, text } = await this.api.wigsGet(
                wig.filename,
            );
            await this._downloadText(download_filename, text);
        } catch (err) {
            this._flash((err as Error).message);
        }
    }

    /** Download for a library row (v0.8.1): the codebook rendered as
     * wig text through the snapshot primitive, nothing saved. */
    private async _downloadLibrary(row: ClosetRow): Promise<void> {
        try {
            const { filename, text } = await this.api.wigRender(row.id);
            await this._downloadText(filename, text);
        } catch (err) {
            this._flash((err as Error).message, "warn");
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

    private _counts(): {
        all: number;
        library: number;
        yours: number;
        fitted: number;
        unfitted: number;
    } {
        const library = this._library.reduce(
            (n, b) =>
                n +
                b.codebooks.filter((c: CodeCodebook) => c.source !== "local")
                    .length,
            0,
        );
        const yours = this._wigs.length;
        const fitted = this._wigs.filter((w) => w.fitting?.state).length;
        return {
            all: library + yours,
            library,
            yours,
            fitted,
            // Unfitted counts only fittable rows (local wig files).
            unfitted: yours - fitted,
        };
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
                              <div class="t2">${this._renderDropTitle()}</div>`
                        : html`<div class="t1">${this._renderDropTitle()}</div>
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
                <button
                    class="fchip ${this._filter === "fitted" ? "on" : ""}"
                    @click=${() => (this._filter = "fitted")}
                >
                    <span class="chip-tick">&check;</span>
                    ${t("wigs.chip.fitted", { count: String(counts.fitted) })}
                </button>
                <button
                    class="fchip ${this._filter === "unfitted" ? "on" : ""}"
                    @click=${() => (this._filter = "unfitted")}
                >
                    ${t("wigs.chip.unfitted", {
                        count: String(counts.unfitted),
                    })}
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
            ${this._renderClipConfirm()}
            ${this._renderSupersede()}
            ${this._renderReverseSupersede()}
            ${this._renderEditor()}
            ${this._adoptWig
                ? html`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._adoptWig.name}
                      .suggestedType=${this._typeFromKind(
                          this._adoptWig.kind,
                      )}
                      .isMatrix=${!!this._adoptWig.matrix}
                      .wigFilename=${this._adoptWig.filename}
                      @device-created=${this._onWigAdopted}
                      @closed=${() => (this._adoptWig = null)}
                  ></ir-promote-dialog>`
                : ""}
            ${this._adoptCodebook
                ? html`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._adoptCodebook.label}
                      .codebookId=${this._adoptCodebook.id}
                      @device-created=${this._onWigAdopted}
                      @closed=${() => (this._adoptCodebook = null)}
                  ></ir-promote-dialog>`
                : ""}
            ${this._renderLinkedWigPopover()}
            ${this._combWig
                ? html`<ir-comb-report
                      .api=${this.api}
                      .wig=${this._combWig}
                      @combed=${() => void this._refresh(true)}
                      @closed=${() => (this._combWig = null)}
                      @adopt-wig=${(e: CustomEvent) => {
                          // The report's handoff offers ADOPT when the
                          // wig is on no device yet. It hands the wig
                          // straight to the dialog the closet row's own
                          // ADOPT would have opened, so there is one
                          // adopt path and not two.
                          this._combWig = null;
                          this._adoptWig = e.detail as WigInfo;
                      }}
                  ></ir-comb-report>`
                : ""}
            ${this._ledgerWig
                ? html`<ir-claims-ledger
                      .api=${this.api}
                      .wig=${this._ledgerWig}
                      @closed=${() => (this._ledgerWig = null)}
                  ></ir-claims-ledger>`
                : ""}
        `;
    }

    private async _onWigAdopted(): Promise<void> {
        const name =
            this._adoptWig?.name ?? this._adoptCodebook?.label ?? "";
        // Held before the fields are cleared: the comb runs on the wig
        // that was adopted, and only when a wig is what was adopted.
        // The codebook path has no file to comb -- adopting from the
        // library builds a device from catalog entries.
        const adopted = this._adoptWig?.filename;
        this._adoptWig = null;
        this._adoptCodebook = null;
        this._flash(t("wigs.adopted", { name }), "ok");
        await this._refresh();
        // Same reasoning as the upload: a wig becoming a live device is
        // the last moment before its codes start being pressed in
        // anger (owner ruling 2026-08-02).
        this._combAfterUpload(adopted);
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

    /** The comb glyph's state class. Neutral grey with no glow covers BOTH
     * "nobody has combed this" and "combed, nothing found" (owner ruling
     * CG3); the tooltip is what separates them. Red outranks yellow by
     * taxonomy rather than count -- one duplicated neighbour is worse than
     * thirty-four malformed frames, because the device answers that one. */
    /**
     * The check's tooltip: the derived detail the glyph cannot carry.
     *
     * Three tiers only (RULED 2026-08-03), matching the download
     * filename tiers exactly -- a row and a filename disagreeing about
     * the same wig is a contradiction somebody has to open the file to
     * resolve.
     *
     * Union coverage is reported here rather than in the colour, on
     * purpose: three people who each proved a different third have not
     * produced anybody who can say the whole wig works.
     */
    private _fitTitle(fitting: FittingSummary): string {
        if (fitting.state === "perfect") {
            const who = (fitting.perfect_by ?? []).filter(Boolean);
            return who.length
                ? t("wigs.fit_tick.perfect_by", { who: who.join(", ") })
                : t("wigs.fit_tick.perfect");
        }
        return t("wigs.fit_tick.scoped", {
            fitters: String(fitting.fitters ?? 0),
            covered: String(fitting.covered ?? 0),
            total: String(fitting.total ?? 0),
        });
    }

    private _combState(wig: WigInfo): string {
        const comb = wig.comb;
        if (!comb || comb.suspects === 0) return "";
        return comb.dangerous ? "bad" : "warn";
    }

    private _combTitle(wig: WigInfo): string {
        const comb = wig.comb;
        if (!comb) return t("comb.action");
        if (comb.suspects === 0)
            return t("comb.tip_clean", { date: comb.date ?? "" });
        return tp("comb.tip_suspects", comb.suspects);
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
                    ${row.wig?.matrix
                        ? tp("wigs.states", row.wig.matrix.cells)
                        : tp("wigs.signals", row.signalCount)}
                </button>
                ${row.wig?.fitting?.state
                    ? html`<button
                          class="fit-tick ${row.wig.fitting.state} ${row
                              .wig.fitting.user_state === "perfect"
                              ? "yours"
                              : ""} ${row.wig.matrix ? "matrix" : ""}"
                          title=${this._fitTitle(row.wig.fitting)}
                          @click=${() => (this._ledgerWig = row.wig!)}
                      >
                          &check;
                      </button>`
                    : ""}
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
                                  title=${this._combTitle(row.wig)}
                                  @click=${() =>
                                      (this._combWig = row.wig!)}
                              >
                                  <svg
                                      class="comb-glyph ${this._combState(
                                          row.wig,
                                      )}"
                                      viewBox="0 0 512 512"
                                      width="15"
                                      height="15"
                                      aria-hidden="true"
                                  >
                                      <path d=${COMB_PATH}></path>
                                  </svg>
                              </button>`
                            : ""}
                    </span>
                    <span class="glyph-slot">
                        <button
                            class="copy-glyph"
                            title=${t("wigs.editor.download")}
                            @click=${() =>
                                row.wig
                                    ? void this._download(row.wig)
                                    : void this._downloadLibrary(row)}
                        >
                            <ha-svg-icon
                                class="dl-icon"
                                .path=${"M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z"}
                            ></ha-svg-icon>
                        </button>
                    </span>
                    <button
                        class="action-btn adopt-btn"
                        title=${row.wig?.linked_devices?.length
                            ? tp(
                                  "wigs.linked",
                                  row.wig.linked_devices.length,
                              )
                            : t("wigs.adopt")}
                        @click=${(e: Event) =>
                            this._onAdoptClick(row, e)}
                    >
                        ${t("wigs.adopt")}<ir-count-dot
                            color="green"
                            .count=${row.wig?.linked_devices
                                ?.length ?? 0}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn clip-btn"
                        ?disabled=${this._busyId === row.id}
                        @click=${() => this._onClipClick(row)}
                    >
                        ${t("wigs.clip_it")}
                    </button>
                    <span class="glyph-slot">
                        ${row.wig
                            ? html`<button
                                  class="trash-btn"
                                  title=${t("wigs.delete_title")}
                                  aria-label=${t("wigs.delete_title")}
                                  @click=${() =>
                                      (this._confirmDelete = row.wig!)}
                              >
                                  <ha-svg-icon
                                      .path=${ICON_TRASH}
                                      .viewBox=${TRASH_VIEWBOX}
                                  ></ha-svg-icon>
                              </button>`
                            : ""}
                    </span>
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
                    <label>${t("wigs.editor.kind")}</label>
                    <input
                        type="text"
                        list="wig-kind-suggestions"
                        placeholder=${t("wigs.editor.kind_placeholder")}
                        .value=${this._editKind}
                        @input=${(e: Event) =>
                            (this._editKind = (
                                e.target as HTMLInputElement
                            ).value)}
                    />
                    <datalist id="wig-kind-suggestions">
                        ${this._kindSuggestions().map(
                            (k) => html`<option value=${k}></option>`,
                        )}
                    </datalist>
                    <div class="ident-hint">
                        ${t("wigs.editor.kind_hint")}
                    </div>
                </div>
                <div class="ident-grid">
                    <div class="field">
                        <label>${t("wigs.editor.fcc_id")}</label>
                        <input
                            type="text"
                            .value=${this._editFccId}
                            @input=${(e: Event) =>
                                (this._editFccId = (
                                    e.target as HTMLInputElement
                                ).value)}
                        />
                    </div>
                    <div class="field">
                        <label>${t("wigs.editor.upc")}</label>
                        <input
                            type="text"
                            .value=${this._editUpc}
                            @input=${(e: Event) =>
                                (this._editUpc = (
                                    e.target as HTMLInputElement
                                ).value)}
                        />
                    </div>
                    <div class="field">
                        <label>${t("wigs.editor.asin")}</label>
                        <input
                            type="text"
                            .value=${this._editAsin}
                            @input=${(e: Event) =>
                                (this._editAsin = (
                                    e.target as HTMLInputElement
                                ).value)}
                        />
                    </div>
                    <div class="field">
                        <label>${t("wigs.editor.oem")}</label>
                        <input
                            type="text"
                            .value=${this._editOem}
                            @input=${(e: Event) =>
                                (this._editOem = (
                                    e.target as HTMLInputElement
                                ).value)}
                        />
                    </div>
                </div>
                <div class="ident-hint">${t("wigs.editor.ids_hint")}</div>
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

    static styles = [dialogStyles, actionChipStyles, popoverStyles, trashButtonStyles, css`
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
        /* Format links in the drop-bar title: same dim ink as the
           surrounding sentence, underline only on hover -- reference,
           not call to action. */
        .drop-bar .fmt-link {
            color: inherit;
            text-decoration: none;
        }
        .drop-bar .fmt-link:hover {
            text-decoration: underline;
            text-underline-offset: 2px;
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
            /* 4px, the signal-row tolerance (owner ruling 2026-07-28:
               one button rhythm everywhere -- the Clipper/Sniffer
               signal rows set it, everything else matches). Delete
               sits at the same gap, exactly like the signal rows. */
            gap: 4px;
        }
        /* Reserved, not conditional. The row's trailing controls are
           anchored right by .row-actions{margin-left:auto}, so anything
           missing at the end drags everything before it sideways: a
           library row with no DELETE sat 64px right of a local one --
           DELETE's width plus the 4px gap -- and the download icons
           never lined up down the list (owner bench 2026-08-02). The
           edit glyph already had a reserved slot; comb and DELETE
           did not. */
        .glyph-slot {
            width: 30px;
            display: flex;
            justify-content: center;
            flex: none;
        }
        /* The ghost that used to hold DELETE's place is gone. It
           rendered the real localized label so the reservation stayed
           right in any language, which was sound reasoning right up
           until DELETE stopped being a word: a text-width ghost against
           an 18px can would have re-broken this alignment inverted.
           A fixed 30px slot is locale-proof by construction. */
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
        /* Row-button palette (owner re-ruling 2026-07-28, consistency
           pass): ADOPT green, CLIP gold/copper, DELETE last. Border
           alpha stays quieter than the text across the family (owner
           bench note 2026-07-27). FIT was the blue one between ADOPT
           and CLIP; it went in v0.9.5 (ruled 2026-08-03), because
           proving a wig now means adopting it and pressing the buttons
           on the device. ADOPT is the path. */

        /* The row's check (owner ruling 2026-07-26, re-ruled
           2026-08-03 to three tiers): green = somebody proved the
           whole wig, amber = signed but scoped, nothing = no
           attestations. Coverage detail lives in the tooltip, and the
           check itself opens the ledger. */
        .fit-tick {
            font-size: 13px;
            font-weight: 700;
            flex: none;
            cursor: pointer;
            background: none;
            border: none;
            padding: 0 2px;
            line-height: 1;
        }
        .fit-tick:hover {
            filter: brightness(1.25);
        }
        .fit-tick.perfect {
            color: #66bb6a;
        }
        /* YOUR perfect fit glows, statically -- the one state you
           earned yourself (owner ruling 2026-07-27). Someone else's
           perfect fit is the same green, flat; partials stay flat
           amber. */
        .fit-tick.perfect.yours {
            text-shadow:
                0 0 6px rgba(102, 187, 106, 0.9),
                0 0 12px rgba(102, 187, 106, 0.45);
        }
        /* The old partial-yellow reborn with a better meaning: it
           used to say somebody stopped early. It now says a complete,
           signed, honest attestation that carries exclusions. */
        .fit-tick.scoped {
            color: #ffb300;
        }
        /* Matrix wigs' stateful signature (owner design 2026-07-28:
           green check, blue glow, "like a cold glow"): the check keeps
           its fitted color, the GLOW goes cold blue -- faint for any
           fitting, brighter when YOUR fitting is perfect. Signal wigs
           keep the green glow above untouched. */
        .fit-tick.matrix {
            text-shadow: 0 0 6px rgba(79, 195, 247, 0.55);
        }
        .fit-tick.matrix.perfect.yours {
            text-shadow:
                0 0 6px rgba(79, 195, 247, 0.95),
                0 0 12px rgba(79, 195, 247, 0.5);
        }
        .chip-tick {
            font-size: 11px;
            font-weight: 700;
            color: #66bb6a;
        }
        .fchip.on .chip-tick {
            color: #fff;
        }
        /* ADOPT DEVICE (v0.8.1): the closet-native make-it-live action,
           first in the row and green (owner re-ruling 2026-07-28 --
           the oxblood chip retired with the color-consistency pass;
           green matches the Assign family and its own linked dot). */
        .action-btn.adopt-btn {
            color: #4caf50;
            border-color: rgba(76, 175, 80, 0.3);
            position: relative; /* anchor for the green linked-count dot */
        }
        .action-btn.adopt-btn:hover:not(:disabled) {
            background: rgba(76, 175, 80, 0.08);
        }
        /* Linked-devices popover (v0.8.1 dot conversion, owner ask
           2026-07-27): the shared action-popover anatomy replaces the
           left-side chip -- count now rides the ADOPT button's dot. */
        .linked-chevron {
            --mdc-icon-size: 14px;
            color: var(--secondary-text-color);
            flex: none;
        }
        /* CLIP is the shared action-chip anatomy (same radius, padding,
           and uppercase as every other button) in the Clipper's copper,
           because it does the same kind of thing as Add Remote. Delete
           is the stock shared delete chip, untouched. Matrix rows got
           CLIP back in the second half (owner ruling 2026-07-29),
           gated behind a row-count confirm -- the open clip mints one
           Clipper row per state. */
        .action-btn.clip-btn {
            color: #b87333;
            border-color: rgba(184, 115, 51, 0.35);
        }
        .action-btn.clip-btn:hover:not(:disabled) {
            background: rgba(184, 115, 51, 0.08);
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
        .ident-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            column-gap: 10px;
        }
        .ident-hint {
            font-size: 11px;
            color: var(--secondary-text-color);
            margin: -5px 0 11px;
            line-height: 1.4;
        }
        /* Inside a .field the hint sits directly under its input (no
           12px field margin to eat), so the -5px pull-up above would
           overlap the input box (owner bench find 2026-07-28). */
        .field .ident-hint {
            margin: 4px 0 0;
        }
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
        /* The comb glyph (Smart Perm, ruled CG3 at glow level C): ALWAYS
           the neutral glyph grey, like edit and download, and 15px against
           their 16. Only the glow moves, so a closet of clean wigs stays
           calm and colour appears only when something is actually wrong. */
        .comb-glyph {
            fill: currentColor;
        }
        .comb-glyph.warn {
            filter: drop-shadow(0 0 2px rgba(255, 193, 7, 0.55))
                drop-shadow(0 0 4px rgba(255, 193, 7, 0.32));
        }
        .comb-glyph.bad {
            filter: drop-shadow(0 0 2px rgba(255, 82, 82, 0.55))
                drop-shadow(0 0 5px rgba(255, 82, 82, 0.4));
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
