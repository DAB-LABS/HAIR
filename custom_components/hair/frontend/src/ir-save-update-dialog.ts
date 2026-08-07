/**
 * UPDATE CLOSET WIG (Second Fitting v3, coding plan Commit 4).
 *
 * The stripped recut, Save as New's sibling: the same metadata form,
 * but Save OVERRIDES the existing wig instead of minting a twin.
 * Under the hood, exactly the machinery already built and verified in
 * earlier commits -- this dialog only decides WHEN to ask for it:
 *
 * - Diverged content: the plan already says so (fetched by the
 *   decision window before this dialog opened), so Save sends
 *   `replace: true`. The server mints the successor and immediately
 *   runs the supersede action after the write (Commit 2) -- no post-
 *   save confirm, because the user already chose this by picking the
 *   route. The receipt names both acts.
 * - Matching content: today's plain UPDATE -- metadata edits applied
 *   in place, `replace` omitted. "Nothing changed" refuses honestly.
 *
 * Kept from v2's safety nets, rendered BEFORE the click instead of
 * after the save (spec section 3): when the wig being overridden
 * carries anyone's fittings, the graded line renders inline, amber for
 * a perfect fit; when replacing would discard rows the local wig
 * carries that the device lacks, the lost-rows line names them. Both
 * read straight off the plan the decision window already fetched --
 * informing, not blocking, never a second network round trip.
 *
 * No checklist here, no attestation -- that whole ceremony belongs to
 * VALIDATE FOR PERFECT FIT alone (Commit 5). This dialog only ever
 * touches metadata and, on diverged content, the mint-and-replace act.
 *
 * Bench fix (2026-08-07): the form and the receipt used to be two
 * separate <ha-dialog> elements, swapped on save -- see
 * ir-save-new-dialog.ts's header comment for the full write-up (an
 * uncaught InvalidStateError on the swap, reproduced live, was taking
 * the confirmation off-screen before it ever painted). One
 * <ha-dialog> now stays open for the component's whole life; only the
 * content inside it swaps between the form and the receipt.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import {
    renderMetadataFields,
    type MetadataFieldSetters,
    type MetadataFieldValues,
} from "./ir-save-metadata-fields.js";
import type { HairApi } from "./api.js";
import type { SavePlan, SaveResult } from "./types.js";

/** Second Fitting v3 punch list item 13: splits the localized
 * replaced-receipt sentence on its own {old}/{new} placeholder
 * tokens so only the two wig names carry the bold+blue styling,
 * whatever order the sentence puts them in per language. */
const REPLACED_RECEIPT_SPLIT = /\{(old|new)\}/g;

/** Second Fitting v3 punch list item 17: same technique as
 * REPLACED_RECEIPT_SPLIT above -- splits the top chip's sentence on
 * its own {name}/{who} tokens so only the wig name carries the
 * bold+blue .replaced-name styling. */
const GRADED_PERFECT_SPLIT = /\{(name|who)\}/g;

@customElement("ir-save-update-dialog")
export class IrSaveUpdateDialog extends LitElement {
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

    private get _diverged(): boolean {
        return this.plan.variant === "succession";
    }

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

    /** Renaming the name field on an UPDATE renames the wig itself
     * (Commit 8's ruling, unchanged here): it never forks a new file. */
    private get _renameWarning(): string | null {
        const before = (this.plan.metadata?.name ?? "").trim();
        if (!before || this._name.trim() === before) return null;
        // Second Fitting v3 punch list item 16: names the actual
        // file being renamed, terser than the old "this renames
        // {name} itself" copy.
        return t("wigs.save.rename_wig_warning", {
            filename: this.plan.source_filename ?? "",
        });
    }

    /** The graded line: null when there is nothing to grade (no
     * claims at all on the wig about to be overridden), matching the
     * self-supersession confirm's own "no claims is light" rule. */
    private get _gradedLine(): {
        amber: boolean;
        text: string;
        name: string;
        who: string;
    } | null {
        if (!this._diverged) return null;
        const grade = this.plan.old_fitting_grade;
        if (!grade || !grade.state) return null;
        const name = this.plan.source_wig_name ?? "";
        const who = grade.handles.join(", ");
        // Second Fitting v3 punch list item 17: a dedicated key, not
        // the drop-bar import confirm's shared supersede.fitted_perfect
        // (ir-supersede-dialog.ts, untouched this round) -- called
        // WITHOUT substitution so {name}/{who} stay literal for
        // _renderGradedPerfectLine's split-render below.
        return grade.state === "perfect"
            ? {
                  amber: true,
                  text: t("supersede.update_fitted_perfect"),
                  name,
                  who,
              }
            : {
                  amber: false,
                  text: tp("supersede.fitted_scoped", grade.count, {
                      count: String(grade.count),
                      name,
                      who,
                  }),
                  name,
                  who,
              };
    }

    /** The lost-rows line: rows the wig being overridden carries that
     * the device does not -- exactly the plan's own `missing_rows`,
     * the same digest comparison the checklist elsewhere already
     * draws its removals from. Never shown on matching content: there
     * is nothing about to be discarded when nothing is being
     * replaced. */
    private get _lostRowsLine(): string | null {
        if (!this._diverged) return null;
        const missing = this.plan.missing_rows ?? [];
        if (!missing.length) return null;
        return tp("supersede.lost", missing.length, {
            count: String(missing.length),
            names: this._formatNames(missing.map((r) => r.alias)),
        });
    }

    /** Second Fitting v3 punch list item 17: the add side of the same
     * delta _lostRowsLine names for removals -- rows the DEVICE
     * carries that the wig being overridden does not. `matched` is
     * false exactly when a device row didn't pair with a source wig
     * row (the plan's own comparison, already carrying aliases
     * client-side, not a client-side guess). */
    private get _addedRowsLine(): string | null {
        if (!this._diverged) return null;
        const added = (this.plan.rows ?? []).filter((r) => !r.matched);
        if (!added.length) return null;
        return tp("supersede.added", added.length, {
            count: String(added.length),
            names: this._formatNames(added.map((r) => r.alias)),
        });
    }

    /** Names, not counts (amendment v2 section 2's rule): truncate
     * past four so a big diff does not turn the chip into a wall of
     * text. Mirrors ir-supersede-dialog.ts's own _formatNames. */
    private _formatNames(names: string[]): string {
        const MAX = 4;
        if (names.length <= 1) return names[0] ?? "";
        const and = t("supersede.list_and");
        if (names.length <= MAX) {
            return `${names.slice(0, -1).join(", ")} ${and} ${
                names[names.length - 1]
            }`;
        }
        const more = names.length - MAX;
        return `${names.slice(0, MAX).join(", ")} ${and} ${tp(
            "supersede.topup_more",
            more,
            { count: String(more) },
        )}`;
    }

    /** Second Fitting v3 punch list item 17: same technique
     * _renderReplacedLine above uses -- splits the localized sentence
     * on its own placeholder tokens so only the wig name carries the
     * bold+blue styling, whatever order each language's word order
     * puts it in. "who" stays plain text. */
    private _renderGradedPerfectLine(
        template: string,
        name: string,
        who: string,
    ) {
        const segments = template.split(GRADED_PERFECT_SPLIT);
        return html`${segments.map((seg) =>
            seg === "name"
                ? html`<b class="replaced-name">${name}</b>`
                : seg === "who"
                  ? html`${who}`
                  : html`${seg}`,
        )}`;
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
     * this component's whole life -- see ir-save-new-dialog.ts's
     * header comment for why the form/receipt swap this used to
     * guard against is gone, not just patched. Plain dispatch, no
     * target to check. */
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
                ...this._metadata(),
                ...(this._diverged ? { replace: true } : {}),
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
            // Coding plan Commit 4: the stale-replace refusal from
            // Commit 2 (the device now matches its source, changed
            // while this dialog sat open) surfaces as a plain re-open
            // of the decision window with a fresh plan -- not another
            // error banner the person has to parse and act on
            // themselves.
            const code = (err as { code?: string }).code;
            if (code === "not_diverged") {
                this.dispatchEvent(
                    new CustomEvent("stale-replace", {
                        bubbles: true,
                        composed: true,
                    }),
                );
                return;
            }
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${t("wigs.route.update_closet_wig")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._done ? this._renderDone() : this._renderForm()}
            </ha-dialog>
        `;
    }

    private _renderForm() {
        const graded = this._gradedLine;
        const lost = this._lostRowsLine;
        const added = this._addedRowsLine;
        return html`
            ${this._error
                ? html`<ha-alert alert-type="error"
                      >${this._error}</ha-alert
                  >`
                : ""}
            ${graded
                ? html`<div
                      class=${graded.amber
                          ? "fitted-callout"
                          : "fitted-line"}
                  >
                      ${graded.amber
                          ? this._renderGradedPerfectLine(
                                graded.text,
                                graded.name,
                                graded.who,
                            )
                          : graded.text}
                  </div>`
                : ""}
            ${lost || added
                ? html`<div class="lost-callout">
                      ${lost ? html`<div>${lost}</div>` : ""}
                      ${added ? html`<div>${added}</div>` : ""}
                  </div>`
                : ""}
            ${renderMetadataFields(
                this._metadataValues,
                this._metadataSetters,
                this._renameWarning,
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

    private _renderDone() {
        const done = this._done as SaveResult;
        // Second Fitting v3 punch list item 13 (supersedes round one
        // item 5's anatomy): a replace's receipt names both wigs, bold
        // and blue, not their filenames -- this dialog never had
        // top-up/retirement machinery to strip, so only the line
        // content changes.
        const line = done.replaced
            ? this._renderReplacedLine(
                  done.replaced.old_name,
                  this._name.trim(),
              )
            : t("wigs.route.updated_metadata", {
                  filename: done.filename ?? "",
              });
        return html`
            <div class="saved-line">${line}</div>
            <div class="dialog-actions">
                <button class="action-btn" @click=${this._close}>
                    ${t("common.close")}
                </button>
            </div>
        `;
    }

    /** Second Fitting v3 punch list item 13: splitting the localized
     * sentence on its own {old}/{new} tokens -- rather than
     * substituting plain text into them -- keeps each language's own
     * word order while still letting just the two names carry the
     * style. Same technique ir-save-perfect-dialog.ts's own replace
     * receipt uses. */
    private _renderReplacedLine(oldName: string, newName: string) {
        const segments = t("wigs.route.replaced_receipt").split(
            REPLACED_RECEIPT_SPLIT,
        );
        return html`${segments.map((seg) =>
            seg === "old"
                ? html`<b class="replaced-name">${oldName}</b>`
                : seg === "new"
                  ? html`<b class="replaced-name">${newName}</b>`
                  : html`${seg}`,
        )}`;
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
            /* Amber, matching ir-supersede-dialog's own family exactly:
               a fitting about to retire and a row about to be lost are
               the same weight of news wherever they render. */
            .fitted-callout,
            .lost-callout {
                margin: 0 0 12px;
                padding: 10px 12px;
                border-radius: 6px;
                border: 1px solid rgba(217, 164, 65, 0.45);
                background: rgba(217, 164, 65, 0.07);
                color: var(--primary-text-color);
                font-size: 0.85rem;
                line-height: 1.5;
            }
            .fitted-line {
                margin: 0 0 12px;
                font-size: 0.9rem;
                line-height: 1.5;
                color: var(--primary-text-color);
            }
            /* Second Fitting v3 punch list item 17: the bottom chip
               can show one or two lines (remove, add) in the same
               box, as the diff dictates. */
            .lost-callout > div + div {
                margin-top: 4px;
            }
            /* Amber, matching the house family above (.fitted-callout /
               .lost-callout): renaming the wig here is the same weight
               of news, right where it's being typed. */
            .rename-warn {
                margin: 6px 0 0;
                padding: 8px 10px;
                border-radius: 6px;
                border: 1px solid rgba(217, 164, 65, 0.45);
                background: rgba(217, 164, 65, 0.07);
                color: var(--primary-text-color);
                font-size: 0.85rem;
                line-height: 1.5;
            }
            /* Second Fitting v3 punch list item 13: the replace
               receipt's two names, bold and blue -- matching
               ir-save-perfect-dialog.ts's own .replaced-name. */
            .replaced-name {
                font-weight: 600;
                color: #64b5f6;
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
        "ir-save-update-dialog": IrSaveUpdateDialog;
    }
}
