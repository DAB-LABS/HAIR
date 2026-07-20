/**
 * Save as wig (v0.7.0 Big Wig): one small dialog shared by every export
 * surface -- Sniffer, Clipper, and Plucker remote cards plus the HAIR
 * device editor (device exports ruled into v1, 2026-07-20).
 *
 * The dialog asks for BRAND (and optional notes) on purpose: the brand
 * field is what keeps the Wigs tab's Unbranded bucket small (wigs.md
 * section 5). Name and signals come from the source; origin is stamped
 * server-side by acquisition road.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";

@customElement("ir-save-wig-dialog")
export class IrSaveWigDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public source: "catalog" | "device" = "catalog";
    @property() public sourceId = "";
    @property() public sourceName = "";

    @state() private _brand = "";
    @state() private _notes = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _done: {
        filename: string;
        signal_count: number;
        skipped: number;
    } | null = null;

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _save(): Promise<void> {
        this._busy = true;
        this._error = null;
        try {
            const extras: Record<string, string> = {};
            if (this._brand.trim()) extras.brand = this._brand.trim();
            if (this._notes.trim()) extras.notes = this._notes.trim();
            const result = await this.api.wigsExport(
                this.source,
                this.sourceId,
                extras,
            );
            this.dispatchEvent(
                new CustomEvent("wig-saved", {
                    detail: result,
                    bubbles: true,
                    composed: true,
                }),
            );
            // Confirm with the filename in place (wigs.md section 7)
            // instead of vanishing -- the filename IS the receipt.
            this._done = result;
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    render() {
        if (this._done) {
            return html`
                <ha-dialog
                    open
                    heading=${t("wigs.export.heading")}
                    scrimClickAction=""
                    @closed=${this._close}
                >
                    <div class="saved-line">
                        ${this._done.skipped > 0
                            ? t("wigs.saved_skipped", {
                                  filename: this._done.filename,
                                  skipped: String(this._done.skipped),
                              })
                            : t("wigs.saved", {
                                  filename: this._done.filename,
                              })}
                    </div>
                    <div class="dialog-actions">
                        <button class="action-btn" @click=${this._close}>
                            ${t("common.close")}
                        </button>
                    </div>
                </ha-dialog>
            `;
        }
        return html`
            <ha-dialog
                open
                heading="${t("wigs.export.heading")} -- ${this.sourceName}"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}
                <div class="field">
                    <label>${t("wigs.editor.brand")}</label>
                    <input
                        type="text"
                        .value=${this._brand}
                        placeholder=${t("wigs.export.brand_hint")}
                        autofocus
                        @input=${(e: Event) =>
                            (this._brand = (e.target as HTMLInputElement).value)}
                        @keydown=${(e: KeyboardEvent) => {
                            if (e.key === "Enter") void this._save();
                        }}
                    />
                </div>
                <div class="field">
                    <label>${t("wigs.editor.notes")}</label>
                    <input
                        type="text"
                        .value=${this._notes}
                        placeholder=${t("wigs.editor.notes_placeholder")}
                        @input=${(e: Event) =>
                            (this._notes = (e.target as HTMLInputElement).value)}
                    />
                </div>
                <div class="dialog-actions">
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

    static styles = [
        dialogStyles,
        css`
            input[type="text"]:focus {
                outline: none;
                border-color: #8e3b3b;
            }
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            .save-wig-btn {
                background: #8e3b3b;
                color: #fff;
                border-color: #8e3b3b;
            }
            .save-wig-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
            .saved-line {
                padding: 8px 0 4px;
                font-size: 13.5px;
                line-height: 1.5;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-save-wig-dialog": IrSaveWigDialog;
    }
}
