/**
 * Add Remote dialog for the Plucker tab.
 *
 * Lets the user mirror a vendor IR blaster as a plucked blaster. The user
 * picks a discovered blaster (vendor entity), types the appliance name they
 * used at learn time, and an editable display name is auto-filled. On Create
 * an empty plucked blaster is created and the dialog emits "blaster-created".
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import type { HairApi } from "./api.js";
import type { PluckVendor, UnknownDevice } from "./types.js";

interface Candidate {
    integration: string;
    entityId: string;
    vendorName: string;
    blasterName: string;
    applianceLabel: string;
    applianceHelp: string;
}

@customElement("ir-pluck-add-remote-dialog")
export class IrPluckAddRemoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public pendingEntity = "";

    @state() private _candidates: Candidate[] = [];
    @state() private _entityId = "";
    @state() private _appliance = "";
    @state() private _name = "";
    @state() private _busy = false;
    @state() private _loading = true;
    @state() private _error: string | null = null;
    private _nameEdited = false;

    connectedCallback(): void {
        super.connectedCallback();
        void this._loadVendors();
    }

    private async _loadVendors(): Promise<void> {
        this._loading = true;
        try {
            const { vendors } = await this.api.listPluckVendors();
            this._candidates = this._flatten(vendors);
            // Preselect the requested entity (Open in Plucker), else the only one.
            const pre =
                this._candidates.find((c) => c.entityId === this.pendingEntity) ??
                (this._candidates.length === 1 ? this._candidates[0] : undefined);
            if (pre) {
                this._entityId = pre.entityId;
                this._autofillName();
            }
        } catch (err) {
            this._error = (err as Error).message;
            this._candidates = [];
        } finally {
            this._loading = false;
        }
    }

    private _flatten(vendors: PluckVendor[]): Candidate[] {
        const out: Candidate[] = [];
        for (const v of vendors) {
            for (const b of v.blasters) {
                out.push({
                    integration: v.integration,
                    entityId: b.entity_id,
                    vendorName: v.name,
                    blasterName: b.name,
                    applianceLabel: v.appliance_label || "Appliance",
                    applianceHelp: v.appliance_help || "",
                });
            }
        }
        return out;
    }

    private get _selected(): Candidate | undefined {
        return this._candidates.find((c) => c.entityId === this._entityId);
    }

    private _autofillName(): void {
        if (this._nameEdited) return;
        const c = this._selected;
        if (!c) return;
        const appliance = this._appliance.trim();
        this._name = (
            appliance ? `${c.blasterName}: ${appliance}` : c.blasterName
        ).trim();
    }

    private _onVendorChange(e: Event): void {
        this._entityId = (e.target as HTMLSelectElement).value;
        this._autofillName();
    }

    private _onApplianceInput(e: Event): void {
        this._appliance = (e.target as HTMLInputElement).value;
        this._autofillName();
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _create(): Promise<void> {
        const c = this._selected;
        if (!c) {
            this._error = "Pick a blaster to pluck from.";
            return;
        }
        if (!this._appliance.trim()) {
            this._error = "Appliance is required.";
            return;
        }
        if (!this._name.trim()) {
            this._error = "Name is required.";
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const device: UnknownDevice = await this.api.createPluckedBlaster({
                vendor_entity_id: c.entityId,
                appliance: this._appliance.trim(),
                name: this._name.trim(),
            });
            this.dispatchEvent(
                new CustomEvent("blaster-created", {
                    detail: device,
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

    render() {
        const c = this._selected;
        return html`
            <ha-dialog
                open
                heading="Add Blaster"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                ${this._loading
                    ? html`<div class="muted">Loading blasters...</div>`
                    : this._candidates.length === 0
                      ? html`<div class="muted">
                            No compatible blasters found. Install a supported IR
                            integration (such as Tuya Local) and learn a code
                            first.
                        </div>`
                      : html`
                            <div class="field">
                                <label>Pluck from</label>
                                <select
                                    .value=${this._entityId}
                                    @change=${this._onVendorChange}
                                >
                                    <option value="">Select a blaster</option>
                                    ${this._candidates.map(
                                        (cand) => html`<option
                                            value=${cand.entityId}
                                        >
                                            ${cand.vendorName}: ${cand.blasterName}
                                        </option>`,
                                    )}
                                </select>
                            </div>

                            <div class="field">
                                <label>${c?.applianceLabel ?? "Appliance"}</label>
                                <input
                                    type="text"
                                    .value=${this._appliance}
                                    placeholder="e.g. candles"
                                    required
                                    @input=${this._onApplianceInput}
                                />
                                ${c?.applianceHelp
                                    ? html`<div class="help">
                                          ${c.applianceHelp}
                                      </div>`
                                    : ""}
                            </div>

                            <div class="field">
                                <label>Name</label>
                                <input
                                    type="text"
                                    .value=${this._name}
                                    placeholder="e.g. Living Room candles"
                                    @input=${(e: Event) => {
                                        this._name = (
                                            e.target as HTMLInputElement
                                        ).value;
                                        this._nameEdited = true;
                                    }}
                                />
                            </div>
                        `}

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
                        ?disabled=${this._busy || this._candidates.length === 0}
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
        .help {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        .muted {
            color: var(--secondary-text-color);
            font-size: 0.9rem;
            margin: 12px 0;
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
            border-color: #455a64;
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
            background: #455a64;
            color: #fff;
            border-color: #455a64;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-pluck-add-remote-dialog": IrPluckAddRemoteDialog;
    }
}
