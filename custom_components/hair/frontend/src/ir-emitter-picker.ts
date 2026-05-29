/**
 * Reusable multi-emitter picker with chip-based UI.
 *
 * Shows selected emitters as removable chips and a dropdown to add
 * from available infrared.* entities. Auto-selects when only one
 * emitter exists.
 *
 * Usage:
 *   <ir-emitter-picker
 *       .hass=${this.hass}
 *       .value=${["infrared.living_room"]}
 *       @emitters-changed=${(e) => this._ids = e.detail.value}
 *   ></ir-emitter-picker>
 *
 * Fires `emitters-changed` with detail: { value: string[] }
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";

interface EmitterInfo {
    entity_id: string;
    name: string;
}

@customElement("ir-emitter-picker")
export class IrEmitterPicker extends LitElement {
    @property({ attribute: false }) public hass?: any;

    /** Currently selected emitter entity IDs. */
    @property({ attribute: false }) public value: string[] = [];

    /** Disable all interactions. */
    @property({ type: Boolean }) public disabled = false;

    /** Entity IDs to exclude from the dropdown (e.g. receiver entities). */
    @property({ attribute: false }) public excludeEntityIds: string[] = [];

    @state() private _didAutoSelect = false;

    updated(changed: Map<string, unknown>): void {
        super.updated(changed);
        // Auto-select if exactly one emitter exists and nothing is selected yet.
        if (
            !this._didAutoSelect &&
            this.value.length === 0
        ) {
            const emitters = this._getEmitters();
            if (emitters.length === 1) {
                this._didAutoSelect = true;
                this._fireChange([emitters[0].entity_id]);
            }
        }
    }

    private _getEmitters(): EmitterInfo[] {
        const states = (this.hass?.states ?? {}) as Record<
            string,
            { entity_id: string; attributes: { friendly_name?: string } }
        >;
        const excludeSet = new Set(this.excludeEntityIds);
        const emitters: EmitterInfo[] = [];
        for (const [entityId, st] of Object.entries(states)) {
            if (entityId.startsWith("infrared.") && !excludeSet.has(entityId)) {
                emitters.push({
                    entity_id: entityId,
                    name: st.attributes.friendly_name ?? entityId,
                });
            }
        }
        return emitters;
    }

    private _emitterName(entityId: string): string {
        const stateObj = this.hass?.states?.[entityId];
        return stateObj?.attributes?.friendly_name ?? entityId;
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
            new CustomEvent("emitters-changed", {
                detail: { value: newValue },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const allEmitters = this._getEmitters();
        const available = allEmitters.filter(
            (em) => !this.value.includes(em.entity_id),
        );

        return html`
            <label>IR emitters</label>

            ${this.value.length > 0
                ? html`
                      <div class="chips">
                          ${this.value.map(
                              (id) => html`
                                  <span class="chip">
                                      <span class="chip-name">${this._emitterName(id)}</span>
                                      ${!this.disabled
                                          ? html`<button
                                                class="chip-remove"
                                                @click=${() => this._onRemove(id)}
                                                title="Remove"
                                            >&times;</button>`
                                          : ""}
                                  </span>
                              `,
                          )}
                      </div>
                  `
                : ""}

            ${allEmitters.length === 0
                ? html`<div class="no-emitters">No IR emitters found.</div>`
                : available.length > 0
                  ? html`
                        <select
                            @change=${this._onAdd}
                            ?disabled=${this.disabled}
                        >
                            <option value="">+ Add emitter...</option>
                            ${available.map(
                                (em) => html`
                                    <option value=${em.entity_id}>
                                        ${em.name}
                                    </option>
                                `,
                            )}
                        </select>
                    `
                  : this.value.length > 0
                    ? html`<div class="all-selected">All emitters selected.</div>`
                    : ""}
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        label {
            display: var(--picker-label-display, block);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
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
            color: #ff9800;
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
        .no-emitters {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .all-selected {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-emitter-picker": IrEmitterPicker;
    }
}
