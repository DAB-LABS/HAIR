/**
 * A Listen pill's small picker (RF hear round 1, frontend; design
 * sniffer-listen-pills.html): the frequency, the length or the type of
 * the receiver's next capture window.
 *
 * About 15px tall at 0.64rem, a rounded box with its value and a
 * caret, at the pill's end. A click opens a short menu under it, one
 * row per choice, each with an optional line of explanation under it
 * (the type picker says what each mode does). Choosing fires
 * ``pick`` with the value; the pill does the saving.
 *
 * Inactive while the receiver's window is open or the receiver is down:
 * it still shows its value in normal text (a sweep's band once found),
 * but has no menu. Every click and keydown stops here, because the pill
 * around it is the press.
 *
 * The menu is fixed to the viewport from the box's own position, the
 * way the capture switch menu is, since the Sniffer's header clips.
 */
import { LitElement, html, css, nothing, svg } from "lit";
import { customElement, property, state } from "./decorators.js";

const CARET = svg`<path d="M7,10L12,15L17,10H7Z" />`;
const CHECK = svg`<path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z" />`;

export interface PickerChoice {
    value: string;
    label: string;
    /** A line under the label, or empty. */
    note?: string;
}

@customElement("ir-pill-picker")
export class IrPillPicker extends LitElement {
    /** What the box reads now. */
    @property() public label = "";
    /** The box's accessible name: what it picks, and its value. */
    @property() public name = "";
    @property({ attribute: false }) public choices: PickerChoice[] = [];
    @property() public value: string | null = null;
    /** Shows its value but takes no choice. */
    @property({ type: Boolean, reflect: true }) public inactive = false;
    /** Inactive because the window is open, not because the receiver
     *  is down: the value reads in normal text (the "locked" look). */
    @property({ type: Boolean, reflect: true }) public locked = false;

    @state() private _menu: { top: number; left: number } | null = null;

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._close();
    }

    private _outside = (e: Event) => {
        if (!e.composedPath().includes(this)) this._close();
    };
    private _away = () => this._close();

    private _close(): void {
        if (this._menu === null) return;
        this._menu = null;
        document.removeEventListener("click", this._outside, true);
        window.removeEventListener("scroll", this._away, true);
        window.removeEventListener("resize", this._away);
    }

    private _open(): void {
        if (this.inactive || this.choices.length === 0) return;
        const box = this.renderRoot.querySelector<HTMLElement>(".box")?.getBoundingClientRect();
        if (!box) return;
        const left = Math.max(8, Math.min(box.left, window.innerWidth - 268));
        this._menu = { top: box.bottom + 4, left };
        document.addEventListener("click", this._outside, true);
        window.addEventListener("scroll", this._away, true);
        window.addEventListener("resize", this._away);
        void this.updateComplete.then(() =>
            this.renderRoot.querySelector<HTMLElement>(".item.cur, .item")?.focus(),
        );
    }

    /** The menu goes to the browser's top layer (owner bench, 19:27):
     *  the pill is its own stacking context (its drain sits behind its
     *  text), so a menu inside it painted under the pills and rows that
     *  follow. A browser without popovers keeps the fixed menu. */
    protected updated(): void {
        const menu = this.renderRoot.querySelector<HTMLElement & { showPopover?: () => void }>(
            ".menu",
        );
        if (menu && typeof menu.showPopover === "function" && !menu.matches(":popover-open")) {
            menu.showPopover();
        }
    }

    private _pick(value: string): void {
        this._close();
        if (value === this.value) return;
        this.dispatchEvent(new CustomEvent("pick", { detail: { value }, bubbles: true, composed: true }));
    }

    private _stop = (e: Event) => e.stopPropagation();

    private _onKey(e: KeyboardEvent): void {
        e.stopPropagation();
        if (e.key === "Escape") {
            this._close();
            return;
        }
        if (this._menu === null || (e.key !== "ArrowDown" && e.key !== "ArrowUp")) return;
        e.preventDefault();
        const items = Array.from(this.renderRoot.querySelectorAll<HTMLElement>(".item"));
        const at = items.indexOf((this.renderRoot as ShadowRoot).activeElement as HTMLElement);
        const next = e.key === "ArrowDown" ? Math.min(items.length - 1, at + 1) : Math.max(0, at - 1);
        items[next]?.focus();
    }

    render() {
        const interactive = !this.inactive && this.choices.length > 0;
        return html`<span class="wrap" @click=${this._stop} @keydown=${this._onKey}>
            <button
                class="box ${this._menu ? "open" : ""}"
                aria-haspopup=${interactive ? "menu" : "false"}
                aria-expanded=${this._menu ? "true" : "false"}
                aria-label=${this.name}
                title=${this.name}
                ?disabled=${!interactive}
                @click=${() => (this._menu ? this._close() : this._open())}
            >
                <span class="val">${this.label}</span>
                <svg class="caret ${interactive ? "" : "held"}" viewBox="0 0 24 24" aria-hidden="true">${CARET}</svg>
            </button>
            ${this._menu
                ? html`<div
                      class="menu"
                      role="menu"
                      popover="manual"
                      style="top:${this._menu.top}px;left:${this._menu.left}px"
                  >
                      ${this.choices.map(
                          (c) => html`<button
                              class="item ${c.value === this.value ? "cur" : ""}"
                              role="menuitemradio"
                              aria-checked=${c.value === this.value ? "true" : "false"}
                              @click=${() => this._pick(c.value)}
                          >
                              <span class="txt">
                                  <span class="ilabel">${c.label}</span>
                                  ${c.note ? html`<span class="inote">${c.note}</span>` : nothing}
                              </span>
                              ${c.value === this.value
                                  ? html`<svg class="check" viewBox="0 0 24 24" aria-hidden="true">${CHECK}</svg>`
                                  : nothing}
                          </button>`,
                      )}
                  </div>`
                : nothing}
        </span>`;
    }

    static styles = css`
        :host {
            display: inline-flex;
        }
        .wrap {
            display: inline-flex;
        }
        .box {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            height: 15px;
            box-sizing: border-box;
            padding: 0 3px 0 5px;
            border: 1px solid color-mix(in srgb, var(--primary-text-color) 22%, transparent);
            border-radius: 8px;
            background: var(--card-background-color, #fff);
            font: inherit;
            font-size: 0.64rem;
            line-height: 1;
            color: var(--primary-text-color);
            white-space: nowrap;
            cursor: pointer;
        }
        .box:disabled {
            cursor: default;
        }
        /* Inactive while the window is open or the receiver is down:
           greyed, no menu, and the same size (fix round 1, item 1): the
           caret keeps its room, unseen, so the pill does not shrink. */
        :host([inactive]) .box {
            background: transparent;
            border-color: color-mix(in srgb, var(--primary-text-color) 14%, transparent);
            color: var(--secondary-text-color);
        }
        .caret.held {
            visibility: hidden;
        }
        .box.open,
        .box:focus-visible {
            outline: none;
            box-shadow: 0 0 0 1px var(--primary-color);
        }
        .caret {
            width: 11px;
            height: 11px;
            fill: currentColor;
            margin-right: -2px;
        }
        .menu {
            position: fixed;
            z-index: 20;
            /* The popover's own defaults (centred, inset 0) undone: it
               sits where the box put it. */
            inset: auto;
            margin: 0;
            color: var(--primary-text-color);
            overflow: visible;
            min-width: 140px;
            max-width: min(260px, calc(100vw - 16px));
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
            padding: 4px 0;
            font-size: 0.8rem;
        }
        .item {
            display: flex;
            align-items: center;
            gap: 10px;
            width: 100%;
            padding: 6px 12px;
            border: none;
            background: none;
            font: inherit;
            text-align: left;
            color: var(--primary-text-color);
            cursor: pointer;
        }
        .item:hover,
        .item:focus-visible {
            outline: none;
            background: var(--secondary-background-color);
        }
        .item.cur {
            background: color-mix(in srgb, var(--primary-color) 10%, transparent);
        }
        .txt {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        .inote {
            font-size: 0.7rem;
            color: var(--secondary-text-color);
            margin-top: 1px;
            white-space: normal;
        }
        .check {
            width: 14px;
            height: 14px;
            flex: none;
            margin-left: auto;
            fill: var(--primary-color);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-pill-picker": IrPillPicker;
    }
}
