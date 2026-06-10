/**
 * Shared signal-alias control used by both the Clips and Sniffer tabs.
 *
 * Renders a signal's S/L diamonds when it has no alias; once named, the
 * alias replaces the diamonds ("alias" in copper-amber + the name in the
 * diamond blue). Click the diamonds (or the alias) to edit inline; the x
 * clears it back to the diamonds, Enter/blur saves, Esc cancels.
 *
 * Owns its own edit state and persists via api.setSignalAlias. Emits
 * ``alias-changed`` ({ id, alias }) on save so the host can sync
 * its local model, and ``alias-error`` (message) on failure.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { customElement, property, state } from "./decorators.js";
import type { HairApi } from "./api.js";
import type { UnknownSignal } from "./types.js";

// mdi:pencil-outline
const ICON_PENCIL =
    "M14.06,9L15,9.94L5.92,19H5V18.08L14.06,9M17.66,3C17.41,3 17.15,3.1 16.96,3.29L15.13,5.12L18.88,8.87L20.71,7.04C21.1,6.65 21.1,6.02 20.71,5.63L18.37,3.29C18.17,3.09 17.92,3 17.66,3M14.06,6.19L3,17.25V21H6.75L17.81,9.94L14.06,6.19Z";

@customElement("ir-signal-alias")
export class IrSignalAlias extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public deviceId = "";
    @property({ attribute: false }) public signal!: UnknownSignal;
    @property({ type: Boolean }) public disabled = false;

    @state() private _editing = false;
    @state() private _draft = "";

    protected updated(changed: PropertyValues): void {
        if (changed.has("_editing") && this._editing) {
            const input = this.shadowRoot?.querySelector<HTMLInputElement>(".alias-input");
            input?.focus();
            input?.select();
        }
    }

    private _startEdit(e?: Event): void {
        if (this.disabled) return;
        e?.stopPropagation();
        this._draft = this.signal.alias ?? "";
        this._editing = true;
    }

    private _onKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            void this._commit();
        } else if (e.key === "Escape") {
            this._editing = false;
        }
    }

    private async _commit(): Promise<void> {
        if (!this._editing) return;
        const alias = this._draft.trim();
        this._editing = false;
        await this._save(alias);
    }

    private async _clear(): Promise<void> {
        this._editing = false;
        await this._save("");
    }

    private async _save(alias: string): Promise<void> {
        try {
            await this.api.setSignalAlias(this.deviceId, this.signal.id, alias);
            this.dispatchEvent(
                new CustomEvent("alias-changed", {
                    detail: { id: this.signal.id, alias },
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this.dispatchEvent(
                new CustomEvent("alias-error", {
                    detail: (err as Error).message,
                    bubbles: true,
                    composed: true,
                }),
            );
        }
    }

    render() {
        const sig = this.signal;
        if (this._editing) {
            return html`
                <span class="alias-edit" @click=${(e: Event) => e.stopPropagation()}>
                    <input
                        class="alias-input"
                        type="text"
                        .value=${this._draft}
                        placeholder="Alias for this signal"
                        @input=${(e: Event) => {
                            this._draft = (e.target as HTMLInputElement).value;
                        }}
                        @keydown=${this._onKeydown}
                        @blur=${() => void this._commit()}
                    />
                    <button
                        class="alias-clear"
                        title="Clear alias"
                        @mousedown=${(e: Event) => e.preventDefault()}
                        @click=${() => void this._clear()}
                    >✕</button>
                </span>
            `;
        }
        if (sig.alias) {
            return html`
                <span
                    class="alias-display ${this.disabled ? "locked" : ""}"
                    title=${this.disabled ? "" : "Click to edit alias"}
                    @click=${(e: Event) => this._startEdit(e)}
                >
                    <span class="alias-label">alias</span>
                    <span class="alias-name">${sig.alias}</span>
                </span>
            `;
        }
        return html`
            <span
                class="diamonds-wrap ${this.disabled ? "locked" : ""}"
                title=${this.disabled ? "" : "Click to name this signal"}
                @click=${(e: Event) => this._startEdit(e)}
            >
                ${sig.sl_pattern
                    ? html`<span class="diamonds"
                          >${[...sig.sl_pattern].map((ch) =>
                              ch === "L"
                                  ? html`<span class="diamond long">◆</span>`
                                  : html`<span class="diamond short">◇</span>`,
                          )}</span
                      >`
                    : html`<span class="signal-short-label">IR Signal</span>`}
                <ha-svg-icon class="alias-pencil" .path=${ICON_PENCIL}></ha-svg-icon>
            </span>
        `;
    }

    static styles = css`
        :host {
            display: inline-flex;
            align-items: center;
            min-width: 0;
        }
        .diamonds-wrap {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }
        .diamonds-wrap.locked,
        .alias-display.locked {
            cursor: default;
        }
        .diamonds-wrap.locked .alias-pencil {
            display: none;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .signal-short-label {
            font-size: 0.82rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .alias-pencil {
            --mdc-icon-size: 13px;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .diamonds-wrap:hover .alias-pencil {
            opacity: 0.7;
        }
        .alias-display {
            display: inline-flex;
            align-items: baseline;
            gap: 7px;
            cursor: pointer;
        }
        .alias-label {
            font-size: 0.6rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: #ba7517;
        }
        .alias-name {
            font-size: 0.9rem;
            color: var(--primary-color);
        }
        .alias-edit {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .alias-input {
            font-size: 0.85rem;
            font-family: inherit;
            border: 1px solid #b87333;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 150px;
        }
        .alias-clear {
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: none;
            color: var(--secondary-text-color);
            cursor: pointer;
            font-size: 0.8rem;
            line-height: 1;
            padding: 3px 6px;
            transition: color 150ms ease, border-color 150ms ease;
        }
        .alias-clear:hover {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.4);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-signal-alias": IrSignalAlias;
    }
}
