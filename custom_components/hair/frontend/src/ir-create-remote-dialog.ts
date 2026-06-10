/**
 * Dialog for creating a new clipped (manual) remote in the Clips tab.
 *
 * Default is an empty remote (name only) -- device type is chosen at
 * Promote time, exactly like the Sniffer flow. A "Type" dropdown also
 * lets the user pick a known manufacturer + model from the installed
 * infrared-protocols codebooks; choosing one materializes a remote
 * pre-filled with one signal per function. No "database" framing -- just
 * a blank remote plus the manufacturers the installed library happens to
 * carry, grouped under "From code library".
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import type { HairApi } from "./api.js";
import type { CodeBrand, UnknownDevice } from "./types.js";

@customElement("ir-create-remote-dialog")
export class IrCreateRemoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;

    @state() private _name = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;

    @state() private _brands: CodeBrand[] = [];
    @state() private _selectedBrand = "";
    @state() private _selectedCodebook = "";
    private _nameEdited = false;

    connectedCallback(): void {
        super.connectedCallback();
        void this._loadBrands();
    }

    private async _loadBrands(): Promise<void> {
        try {
            this._brands = await this.api.getCodeBrands();
        } catch {
            // Library unavailable or no codebooks -> only the blank-remote
            // option is offered, which is the existing behavior.
            this._brands = [];
        }
    }

    private _brand(key: string): CodeBrand | undefined {
        return this._brands.find((b) => b.brand === key);
    }

    private _codebookLabel(brandKey: string, codebookId: string): string {
        const cb = this._brand(brandKey)?.codebooks.find(
            (c) => c.id === codebookId,
        );
        return cb?.label ?? "";
    }

    private _maybeAutofillName(): void {
        if (this._nameEdited) return;
        const brand = this._brand(this._selectedBrand);
        if (!brand || !this._selectedCodebook) {
            return;
        }
        const cbLabel = this._codebookLabel(
            this._selectedBrand,
            this._selectedCodebook,
        );
        this._name = `${brand.label} ${cbLabel}`.trim();
    }

    private _onBrandChange(e: Event): void {
        this._selectedBrand = (e.target as HTMLSelectElement).value;
        const brand = this._brand(this._selectedBrand);
        // Auto-select the only model when a manufacturer has just one.
        if (brand && brand.codebooks.length === 1) {
            this._selectedCodebook = brand.codebooks[0].id;
        } else {
            this._selectedCodebook = "";
        }
        this._maybeAutofillName();
    }

    private _onCodebookChange(e: Event): void {
        this._selectedCodebook = (e.target as HTMLSelectElement).value;
        this._maybeAutofillName();
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _create(): Promise<void> {
        if (!this._name.trim()) {
            this._error = "Name is required.";
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            let remote: UnknownDevice;
            if (this._selectedCodebook) {
                const result = await this.api.importCodeRemote(
                    this._selectedCodebook,
                    this._name.trim(),
                );
                remote = result.device;
            } else {
                remote = await this.api.createRemote(this._name.trim());
            }
            this.dispatchEvent(
                new CustomEvent("remote-created", {
                    detail: remote,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private _onKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            void this._create();
        }
    }

    render() {
        const brand = this._brand(this._selectedBrand);
        return html`
            <ha-dialog
                open
                heading="Create Remote"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <div class="field">
                    <label>Name</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder="e.g. Living Room TV"
                        required
                        autofocus
                        @input=${(e: Event) => {
                            this._name = (e.target as HTMLInputElement).value;
                            this._nameEdited = true;
                        }}
                        @keydown=${this._onKeydown}
                    />
                </div>

                ${this._brands.length > 0
                    ? html`
                          <div class="field">
                              <label>Type</label>
                              <select
                                  .value=${this._selectedBrand}
                                  @change=${this._onBrandChange}
                              >
                                  <option value="">Blank remote</option>
                                  <optgroup label="From code library">
                                      ${this._brands.map(
                                          (b) => html`<option value=${b.brand}>
                                              ${b.label}
                                          </option>`,
                                      )}
                                  </optgroup>
                              </select>
                          </div>

                          ${brand
                              ? html`<div class="field">
                                    <label>Model</label>
                                    <select
                                        .value=${this._selectedCodebook}
                                        @change=${this._onCodebookChange}
                                    >
                                        <option value="">
                                            Select a model
                                        </option>
                                        ${brand.codebooks.map(
                                            (c) => html`<option value=${c.id}>
                                                ${c.label}
                                                (${c.functions.length})
                                            </option>`,
                                        )}
                                    </select>
                                </div>`
                              : ""}
                      `
                    : ""}

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        Cancel
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy ? "Creating..." : "Create"}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = css`
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        input[type="text"],
        select {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        input[type="text"]:focus,
        select:focus {
            outline: none;
            border-color: #b87333;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .dialog-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid var(--divider-color);
        }
        .action-btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .cancel-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .create-btn {
            background: #b87333;
            color: #fff;
            border-color: #b87333;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-create-remote-dialog": IrCreateRemoteDialog;
    }
}
