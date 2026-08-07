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
 *
 * Bench fix (2026-08-07): the form and the receipt used to be two
 * separate <ha-dialog> elements, swapped on save. As of HA 2026.7,
 * <ha-dialog> opens a real native <dialog> (showModal()) under the
 * hood, and removing one mid-transition to open the other raced the
 * outgoing close() against the incoming showModal() -- an uncaught
 * "InvalidStateError: Transition was aborted", reproduced live
 * against the test instance, that took the whole dialog off-screen
 * before the receipt ever painted (the save itself always succeeded;
 * only the confirmation was crashing invisibly). One <ha-dialog> now
 * stays open for the component's whole life.
 *
 * Bench fix, part 2 (2026-08-07, same day): one persistent dialog
 * element wasn't enough on its own. Live re-testing turned up a
 * second failure mode on the same mechanism -- swapping the dialog's
 * entire light-DOM content in one commit (every form field removed,
 * an unrelated receipt tree added) still made the dialog go dark
 * sometime after the swap, with no explicit close() call and no
 * "closed" event from anywhere in our own code (confirmed live: a
 * global dispatchEvent trap never saw one). The form and the done
 * screen now both live in permanently-mounted wrapper <div>s inside
 * the one <ha-dialog>, toggled with a plain `hidden` attribute --
 * the dialog's direct children never change identity or count for
 * the component's whole life, so there is no wholesale content
 * mutation left for anything downstream to react to.
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
        // Second Fitting v3 punch list item 4: this is the one route
        // that differentiates its name prefill -- `suggested_new_name`
        // is only ever set when there is a source wig to collide
        // with; a from-scratch device falls back to the plain
        // metadata prefill (empty, here).
        this._name = this.plan.suggested_new_name ?? md.name ?? "";
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

    /** Bench fix (2026-08-07): one `<ha-dialog>` now stays open for
     * this component's whole life -- see the file-level comment on
     * why the form/receipt swap this used to guard against is gone,
     * not just patched. Plain dispatch, no target to check. */
    private _close(): void {
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
                // Second Fitting v3 punch list item 2: this route
                // always mints, even over matching content -- the
                // route choice itself is the signal, carried
                // explicitly since the server no longer infers it.
                mode: "create",
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
        return html`
            <ha-dialog
                open
                heading=${t("wigs.route.save_as_new")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <div ?hidden=${!!this._done}>${this._renderForm()}</div>
                <div ?hidden=${!this._done}>${this._renderDone()}</div>
            </ha-dialog>
        `;
    }

    private _renderForm() {
        return html`
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
        `;
    }

    /** Rendered even before there is anything to show (see the
     * bench fix part 2 file-header comment) -- stays behind `hidden`
     * until `_done` lands, so the dialog's children never change
     * count or identity when the save actually completes. */
    private _renderDone() {
        const done = this._done;
        const line = done
            ? done.skipped > 0
                ? t("wigs.saved_skipped", {
                      filename: done.filename ?? "",
                      skipped: String(done.skipped),
                  })
                : t("wigs.saved", { filename: done.filename ?? "" })
            : "";
        return html`
            <div class="saved-line">${line}</div>
            <div class="dialog-actions">
                <button class="action-btn" @click=${this._close}>
                    ${t("common.close")}
                </button>
            </div>
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
