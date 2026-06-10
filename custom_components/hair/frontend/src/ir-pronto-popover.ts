/**
 * Shared "view / copy Pronto" control for signal rows (Sniffer + Clipper).
 *
 * A subdued copy glyph that opens a small popover showing the signal's
 * raw Pronto hex in a selectable monospace box, with Copy and Close
 * buttons. Copy uses the modern clipboard API and falls back to the
 * legacy execCommand path for plain-http (non-secure) contexts; the
 * shown text is selectable so the user can always copy by hand.
 *
 * The popover is position: fixed so it escapes the card's overflow:hidden
 * clipping; its position is computed from the glyph on open.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";

// mdi:content-copy
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";

const POPOVER_WIDTH = 320;

@customElement("ir-pronto-popover")
export class IrProntoPopover extends LitElement {
    @property() public code = "";
    @property({ type: Boolean }) public disabled = false;

    @state() private _open = false;
    @state() private _copied = false;
    @state() private _top = 0;
    @state() private _left = 0;

    private _onDocClick = (e: MouseEvent) => {
        if (this._open && !e.composedPath().includes(this)) {
            this._open = false;
        }
    };
    private _onDocKey = (e: KeyboardEvent) => {
        if (this._open && e.key === "Escape") {
            this._open = false;
        }
    };

    connectedCallback(): void {
        super.connectedCallback();
        document.addEventListener("click", this._onDocClick);
        document.addEventListener("keydown", this._onDocKey);
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        document.removeEventListener("click", this._onDocClick);
        document.removeEventListener("keydown", this._onDocKey);
    }

    private _toggle(e: Event): void {
        e.stopPropagation();
        if (this.disabled) return;
        if (this._open) {
            this._open = false;
            return;
        }
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        let left = rect.left;
        if (left + POPOVER_WIDTH > window.innerWidth - 8) {
            left = window.innerWidth - POPOVER_WIDTH - 8;
        }
        this._left = Math.max(8, left);
        this._top = rect.bottom + 6;
        this._copied = false;
        this._open = true;
        void this.updateComplete.then(() => {
            const box = this.shadowRoot?.querySelector<HTMLTextAreaElement>(".code-box");
            box?.focus();
            box?.select();
        });
    }

    private async _copy(e: Event): Promise<void> {
        e.stopPropagation();
        const ok = await this._writeClipboard(this.code);
        if (ok) {
            this._copied = true;
            setTimeout(() => {
                this._copied = false;
            }, 1500);
        }
    }

    /** Modern clipboard in secure contexts; legacy fallback on plain http. */
    private async _writeClipboard(text: string): Promise<boolean> {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                return true;
            }
        } catch {
            // Fall through to the legacy path.
        }
        try {
            const ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.top = "-1000px";
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            const ok = document.execCommand("copy");
            ta.remove();
            return ok;
        } catch {
            return false;
        }
    }

    render() {
        return html`
            <ha-svg-icon
                class="copy-icon ${this.disabled ? "disabled" : ""}"
                .path=${ICON_COPY}
                title=${this.disabled ? "" : "Show Pronto"}
                @click=${this._toggle}
            ></ha-svg-icon>
            ${this._open
                ? html`<div
                      class="popover"
                      style="top:${this._top}px; left:${this._left}px;"
                      @click=${(e: Event) => e.stopPropagation()}
                  >
                      <textarea class="code-box" readonly .value=${this.code}></textarea>
                      <div class="pop-actions">
                          <button class="pbtn copy-btn" @click=${this._copy}>
                              ${this._copied ? "Copied" : "Copy"}
                          </button>
                          <button
                              class="pbtn close-btn"
                              @click=${() => (this._open = false)}
                          >Close</button>
                      </div>
                  </div>`
                : ""}
        `;
    }

    static styles = css`
        :host {
            display: inline-flex;
            align-items: center;
        }
        .copy-icon {
            --mdc-icon-size: 10px;
            color: var(--secondary-text-color);
            cursor: pointer;
            opacity: 0.4;
            transition: opacity 150ms ease, color 150ms ease;
        }
        .copy-icon:hover {
            opacity: 1;
            color: var(--primary-text-color);
        }
        .copy-icon.disabled {
            opacity: 0.25;
            cursor: default;
            pointer-events: none;
        }
        .popover {
            position: fixed;
            width: 320px;
            box-sizing: border-box;
            background: var(--card-background-color, #fff);
            border: 0.5px solid var(--divider-color);
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            padding: 10px;
            z-index: 100;
        }
        .code-box {
            width: 100%;
            box-sizing: border-box;
            height: 90px;
            font-family: monospace;
            font-size: 0.78rem;
            resize: vertical;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            padding: 6px;
        }
        .pop-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 8px;
        }
        .pbtn {
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: none;
            font-family: inherit;
            font-size: 0.78rem;
            font-weight: 500;
            padding: 4px 12px;
            cursor: pointer;
        }
        .copy-btn {
            color: #b87333;
            border-color: #b87333;
        }
        .copy-btn:hover {
            background: rgba(184, 115, 51, 0.08);
        }
        .close-btn {
            color: var(--secondary-text-color);
        }
        .close-btn:hover {
            background: var(--secondary-background-color);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-pronto-popover": IrProntoPopover;
    }
}
