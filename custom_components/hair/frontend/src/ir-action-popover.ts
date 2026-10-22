/**
 * The "Map action" popover (heard state, round 2a).
 *
 * Extracted from ir-device-detail.ts, where it lived inline, so a typed
 * Remote's button rows open the very same popover a Device's command
 * rows do (kickoff: "reuse the Device's mapping editor"). The look is
 * the device-detail block's, through the shared popoverStyles; nothing
 * about a Device's popover changes.
 *
 * The host keeps what belongs to it: where the popover sits (it is
 * position: fixed, so the host passes viewport coordinates from the
 * label that opened it), when it closes on an outside click, and what
 * a choice does. This component renders the list and says what was
 * picked with a `select` event, `detail: { key: string | null }`, null
 * meaning "None (clear)".
 *
 * `allowCustom` keeps the Device's free-form key entry. A Remote passes
 * false: a key its entity cannot track would be a dead control.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tv } from "./localize.js";
import { popoverStyles } from "./ir-popover-styles.js";
import type { ActionOption } from "./types.js";

@customElement("ir-action-popover")
export class IrActionPopover extends LitElement {
    @property({ attribute: false }) public options: ActionOption[] = [];
    /** The key mapped to the row that opened the popover, or "". */
    @property({ attribute: false }) public currentKey = "";
    /** For each key mapped elsewhere, the name of the row that holds it,
     *  shown beside the option so a reassignment is visible. */
    @property({ attribute: false }) public holders: Record<string, string> = {};
    @property({ type: Boolean }) public allowCustom = false;
    @property({ type: Number }) public top = 0;
    @property({ type: Number }) public left = 0;

    @state() private _customOpen = false;
    @state() private _customValue = "";

    private _pick(key: string | null): void {
        this.dispatchEvent(
            new CustomEvent("select", {
                detail: { key },
                bubbles: true,
                composed: true,
            }),
        );
    }

    protected render() {
        return html`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">${t("devdetail.map_action")}</div>
                ${this.currentKey
                    ? html`
                          <button
                              class="popover-item clear"
                              @click=${() => this._pick(null)}
                          >
                              <span class="popover-label">${t("devdetail.none_clear")}</span>
                          </button>
                      `
                    : nothing}
                ${this.options.map((opt) => {
                    const isCurrent = this.currentKey === opt.key;
                    const holder = this.holders[opt.key];
                    return html`
                        <button
                            class="popover-item ${isCurrent ? "active" : ""}"
                            @click=${() => this._pick(opt.key)}
                        >
                            <span class="popover-label">${tv(opt.label)}</span>
                            ${isCurrent
                                ? html`<span class="popover-check">&#10003;</span>`
                                : holder
                                  ? html`<span class="popover-existing">${holder}</span>`
                                  : nothing}
                        </button>
                    `;
                })}
                ${this.allowCustom ? this._renderCustom() : nothing}
            </div>
        `;
    }

    private _renderCustom() {
        const value = this._customValue.trim();
        if (!this._customOpen) {
            return html`
                <button
                    class="popover-item custom-action-open"
                    @click=${(e: Event) => {
                        e.stopPropagation();
                        this._customOpen = true;
                        this.updateComplete.then(() => {
                            this.shadowRoot
                                ?.querySelector<HTMLInputElement>(".custom-action-input")
                                ?.focus();
                        });
                    }}
                >
                    <span class="popover-label">${t("devdetail.custom_action")}</span>
                </button>
            `;
        }
        return html`
            <div class="custom-action-row">
                <input
                    class="custom-action-input"
                    type="text"
                    placeholder=${t("devdetail.custom_action_placeholder")}
                    .value=${this._customValue}
                    @input=${(e: Event) =>
                        (this._customValue = (e.target as HTMLInputElement).value)}
                    @keydown=${(e: KeyboardEvent) => {
                        if (e.key === "Enter" && this._customValue.trim()) {
                            this._pick(this._customValue.trim());
                        }
                    }}
                />
                <button
                    class="custom-action-set"
                    ?disabled=${!value}
                    @click=${() => this._pick(value)}
                >
                    ${t("devdetail.set")}
                </button>
            </div>
        `;
    }

    static styles = [
        popoverStyles,
        css`
            /* Custom action entry (free-form key) inside the Map action
               popover. Input + Set on one row, matching popover chrome.
               Moved here from ir-device-detail.ts with the popover. */
            .custom-action-row {
                display: flex;
                gap: 6px;
                padding: 6px 10px 8px;
                align-items: center;
            }
            .custom-action-input {
                flex: 1;
                min-width: 0;
                padding: 5px 8px;
                border-radius: 4px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                color: var(--primary-text-color);
                font-size: 0.8rem;
                font-family: var(--code-font-family, monospace);
                box-sizing: border-box;
            }
            .custom-action-input:focus {
                outline: none;
                border-color: var(--primary-color);
            }
            .custom-action-set {
                border: 1px solid var(--divider-color);
                background: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 0.78rem;
                font-weight: 500;
                font-family: inherit;
                cursor: pointer;
                color: var(--primary-text-color);
            }
            .custom-action-set:disabled {
                opacity: 0.5;
                cursor: default;
            }
            .custom-action-set:hover:not(:disabled) {
                background: var(--secondary-background-color);
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-action-popover": IrActionPopover;
    }
}
