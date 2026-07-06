/**
 * Reusable multi-receiver picker with chip-based UI.
 *
 * The mirror image of ir-emitter-picker: it lists native
 * ``InfraredReceiverEntity`` instances (from ``api.listReceivers()``) so a
 * trigger can be scoped to fire only when specific receivers observe the
 * signal. Empty selection = "Any receiver" (backward-compat: fires on any
 * capture). Unlike the emitter picker there is NO auto-select -- leaving the
 * field empty is the meaningful default.
 *
 * Usage:
 *   <ir-receiver-picker
 *       .api=${this.api}
 *       .value=${["infrared.garage_receiver"]}
 *       @receivers-changed=${(e) => this._ids = e.detail.value}
 *   ></ir-receiver-picker>
 *
 * Fires `receivers-changed` with detail: { value: string[] }
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import type { HairApi } from "./api.js";
import type { ReceiverInfo } from "./types.js";

@customElement("ir-receiver-picker")
export class IrReceiverPicker extends LitElement {
    /** HAIR API client. Required -- the receiver list comes from it. */
    @property({ attribute: false }) public api?: HairApi;

    /** Currently selected receiver entity IDs. */
    @property({ attribute: false }) public value: string[] = [];

    /** Disable all interactions. */
    @property({ type: Boolean }) public disabled = false;

    @state() private _receivers: ReceiverInfo[] = [];
    private _receiversLoaded = false;

    updated(changed: Map<string, unknown>): void {
        super.updated(changed);
        if (changed.has("api") && this.api && !this._receiversLoaded) {
            this._receiversLoaded = true;
            void this._loadReceivers();
        }
    }

    private async _loadReceivers(): Promise<void> {
        if (!this.api) return;
        try {
            this._receivers = await this.api.listReceivers();
        } catch {
            // Pre-2026.6 HA versions don't expose receivers; treat as empty.
            this._receivers = [];
        }
    }

    private _receiverName(entityId: string): string {
        const match = this._receivers.find((r) => r.entity_id === entityId);
        return match?.name ?? entityId;
    }

    private _onAdd(e: Event): void {
        const select = e.target as HTMLSelectElement;
        const entityId = select.value;
        if (!entityId) return;
        select.value = "";
        if (this.value.includes(entityId)) return;
        this._fireChange([...this.value, entityId]);
    }

    private _onRemove(entityId: string): void {
        this._fireChange(this.value.filter((id) => id !== entityId));
    }

    private _fireChange(newValue: string[]): void {
        this.value = newValue;
        this.dispatchEvent(
            new CustomEvent("receivers-changed", {
                detail: { value: newValue },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const available = this._receivers.filter(
            (r) => !this.value.includes(r.entity_id),
        );

        return html`
            <label>Via receiver(s):</label>

            ${this.value.length > 0
                ? html`
                      <div class="chips">
                          ${this.value.map(
                              (id) => html`
                                  <span class="chip">
                                      <span class="chip-name"
                                          >${this._receiverName(id)}</span
                                      >
                                      ${!this.disabled
                                          ? html`<button
                                                class="chip-remove"
                                                @click=${() => this._onRemove(id)}
                                                title="Remove"
                                            >
                                                &times;
                                            </button>`
                                          : ""}
                                  </span>
                              `,
                          )}
                      </div>
                  `
                : ""}

            ${this._receivers.length === 0
                ? html`<div class="no-receivers">No IR receivers found.</div>`
                : available.length > 0
                  ? html`
                        <select @change=${this._onAdd} ?disabled=${this.disabled}>
                            <option value="">+ Add receiver...</option>
                            ${available.map(
                                (r) => html`
                                    <option value=${r.entity_id}>
                                        ${r.name}
                                    </option>
                                `,
                            )}
                        </select>
                    `
                  : html`<div class="all-selected">All receivers selected.</div>`}
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        label {
            display: var(--picker-label-display, block);
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--primary-text-color);
            margin-bottom: 6px;
        }
        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--secondary-background-color);
            color: var(--primary-color);
            font-size: 0.82rem;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 4px;
            line-height: 1;
        }
        .chip-name {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }
        .chip-remove {
            background: none;
            border: none;
            color: inherit;
            font-size: 1rem;
            cursor: pointer;
            padding: 0 2px;
            line-height: 1;
            opacity: 0.65;
            transition: opacity 120ms ease;
        }
        .chip-remove:hover {
            opacity: 1;
        }
        select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .no-receivers,
        .all-selected {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-receiver-picker": IrReceiverPicker;
    }
}
