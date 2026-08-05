/**
 * SAVE AS NEW (Second Fitting v3, coding plan Commit 4).
 *
 * The stripped recut: the metadata form alone, no perfect-fit section
 * beside it. Save always mints -- the server verb is CREATE for a
 * from-scratch device, or a SUCCESSION that keeps both files standing
 * for a sourced one (ancestry stamped silently; the existing wig is
 * never touched, per spec section 2). No confirm after, even when the
 * mint happens to name a local ancestor still on the shelf -- v2's
 * post-save self-doorway supersede confirm retires as a decision
 * point here (spec section 6); the receipt just names the file.
 *
 * The plan driving the name prefill and the source line was already
 * fetched by the decision window before this dialog opened (Commit
 * 3), so `plan` arrives as a required property -- this dialog never
 * calls `wigsSavePlan` itself.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import {
    renderMetadataFields,
    type MetadataFieldSetters,
    type MetadataFieldValues,
} from "./ir-save-metadata-fields.js";
import type { HairApi } from "./api.js";
import type { SavePlan, SaveResult } from "./types.js";

@customElement("ir-save-new-dialog")
export class IrSaveNewDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public sourceId = "";
    @property({ attribute: false }) public plan!: SavePlan;

    @state() private _name = "";
    @state() private _brand = "";
    @state() private _model = "";
    @state() private _notes = "";
    @state() private _fccId = "";
    @state() private _upc = "";
    @state() private _asin = "";
    @state() private _oem = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _done: SaveResult | null = null;

    firstUpdated(): void {
        const md = this.plan.metadata ?? {};
        this._name = md.name ?? "";
        this._brand = md.brand ?? "";
        this._model = md.model ?? "";
        this._notes = md.notes ?? "";
        this._fccId = md.fcc_id ?? "";
        this._upc = md.upc ?? "";
        this._asin = md.asin ?? "";
        this._oem = md.oem ?? "";
    }

    private get _metadataValues(): MetadataFieldValues {
        return {
            name: this._name,
            brand: this._brand,
            model: this._model,
            notes: this._notes,
            fccId: this._fccId,
            upc: this._upc,
            asin: this._asin,
            oem: this._oem,
        };
    }

    private get _metadataSetters(): MetadataFieldSetters {
        return {
            setName: (v) => (this._name = v),
            setBrand: (v) => (this._brand = v),
            setModel: (v) => (this._model = v),
            setNotes: (v) => (this._notes = v),
            setFccId: (v) => (this._fccId = v),
            setUpc: (v) => (this._upc = v),
            setAsin: (v) => (this._asin = v),
            setOem: (v) => (this._oem = v),
        };
    }

    private _metadata(): Record<string, string> {
        const out: Record<string, string> = {};
        const pairs: [string, string][] = [
            ["name", this._name],
            ["brand", this._brand],
            ["model", this._model],
            ["notes", this._notes],
            ["fcc_id", this._fccId],
            ["upc", this._upc],
            ["asin", this._asin],
            ["oem", this._oem],
        ];
        for (const [key, value] of pairs) {
            if (value.trim()) out[key] = value.trim();
        }
        return out;
    }

    /** The bench addendum's lifecycle fix (Commit 12), carried into
     * every dialog in this family: a swapped-out `<ha-dialog>` (the
     * form giving way to the receipt) keeps running its own closing
     * animation and fires a late `closed` on itself regardless. A real
     * close always originates from whichever `<ha-dialog>` is
     * CURRENTLY part of this render, checked via shadow-root
     * containment rather than component state so it holds for both
     * screens without special-casing either. */
    private _close(e?: Event): void {
        const target = e?.target as Node | null;
        if (target && !this.shadowRoot?.contains(target)) return;
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _save(): Promise<void> {
        if (this._busy) return;
        this._busy = true;
        this._error = null;
        try {
            const result = await this.api.wigsSave({
                device_id: this.sourceId,
                ...this._metadata(),
            });
            this.dispatchEvent(
                new CustomEvent("wig-saved", {
                    detail: result,
                    bubbles: true,
                    composed: true,
                }),
            );
            this._done = result;
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    render() {
        if (this._done) return this._renderDone();
        return html`
            <ha-dialog
                open
                heading=${t("wigs.route.save_as_new")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error"
                          >${this._error}</ha-alert
                      >`
                    : ""}
                ${renderMetadataFields(
                    this._metadataValues,
                    this._metadataSetters,
                    null,
                )}
                <div class="dialog-actions">
                    <span class="spacer"></span>
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${t("common.cancel")}
                    </button>
                    <button
                        class="action-btn save-wig-btn"
                        @click=${this._save}
                        ?disabled=${this._busy}
                    >
                        ${this._busy ? t("common.saving") : t("common.save")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    private _renderDone() {
        const done = this._done as SaveResult;
        const line =
            done.skipped > 0
                ? t("wigs.saved_skipped", {
                      filename: done.filename ?? "",
                      skipped: String(done.skipped),
                  })
                : t("wigs.saved", { filename: done.filename ?? "" });
        return html`
            <ha-dialog
                open
                heading=${t("wigs.route.save_as_new")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <div class="saved-line">${line}</div>
                <div class="dialog-actions">
                    <button class="action-btn" @click=${this._close}>
                        ${t("common.close")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            .pair-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                column-gap: 10px;
            }
            .ident-hint {
                font-size: 11px;
                color: var(--secondary-text-color);
                margin: -5px 0 10px;
                line-height: 1.4;
            }
            .saved-line {
                font-size: 0.95rem;
                color: var(--primary-text-color);
                margin: 4px 0 8px;
            }
            .save-wig-btn {
                background: #3f8a4b;
                color: #fff;
                border-color: #3f8a4b;
            }
            .save-wig-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-save-new-dialog": IrSaveNewDialog;
    }
}
