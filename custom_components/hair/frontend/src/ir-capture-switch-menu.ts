/**
 * The switch menu behind the caret of a capture device's RX-CAPTURE chip
 * (windowed receivers, round 3; one split chip since the owner's ruling
 * of 2026-10-20, which retired the separate switch pill).
 *
 * A capture device's window is opened by toggling an entity, and HAIR
 * resolves which one on the server: the one the receiver declares
 * (``capture_switch``), else the user's choice, else the only switch on
 * the receiver's device. The Devices card shows one RX-CAPTURE chip,
 * split in two (ir-listen-chip.ts): the main part starts and stops a
 * capture, and this element is the caret beside it, behind a thin
 * divider. It looks small, the arrow plus a couple of pixels each side
 * (owner bench, 2026-10-21), but a transparent hit area of 24 by 24px
 * sits over it so a thumb can still hit it. It is a focus stop of its
 * own, and its accessible name is "Choose a switch".
 *
 * Every capture device has the caret, even with one option. Its menu
 * (ir-listen-state.ts pickerMenu):
 * - a receiver that declares its switch: that switch alone, checked.
 *   Nothing else on the device is offered (an RM4 Pro's RF capture
 *   never appears), choosing it again changes nothing, and the server
 *   refuses a choice for such a receiver anyway;
 * - one switch on the device, nothing declared: that switch, already
 *   picked and checked, then "Choose another...";
 * - several switches, nothing declared: all of them, none checked until
 *   the user picks, then "Choose another...".
 * Each row shows its entity's health on the shared dot (green dot or
 * ember ring, healthDotStyles) and is a full-width, two-line row tall
 * enough for a thumb. "Choose another..." opens a house-built search, a
 * plain ``<input>`` over a list built from ``hass.states``, limited to
 * ``switch`` and ``input_boolean``, each row showing the friendly name
 * and the entity id. Not ``ha-entity-picker`` and not ``ha-textfield``:
 * both come from the lazily loaded family that renders as an empty
 * shell inside a custom panel.
 *
 * The chip opens the same menu from its main part while nothing is
 * picked (open()), since there is nothing to capture with yet. Offline,
 * the chip disables the caret too (``disabled``).
 *
 * Its colours come from the chip around it, ``--split-fg`` and
 * ``--split-bg``, so the two parts read as one chip in every state.
 * Choosing saves through ``hair/receivers/capture_switch`` and fires
 * ``capture-switch-changed`` so the page re-reads its rows. Every click
 * and keydown stops here: the card around it navigates.
 */
import { LitElement, html, css, nothing, svg } from "lit";
import type { HairApi } from "./api.js";
import { customElement, property, state } from "./decorators.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import { entityFullName } from "./entity-names.js";
import { healthDotClass, isEntityOnline } from "./entity-health.js";
import { healthDotStyles } from "./ir-header-chip-styles.js";
import { pickerEntities, pickerMenu } from "./ir-listen-state.js";
import { t } from "./localize.js";
import type { CaptureReceiverRow } from "./types.js";

/** MDI menu-down and check, from @mdi/js like the card's other icons. */
const CARET = svg`<path d="M7,10L12,15L17,10H7Z" />`;
const CHECK = svg`<path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z" />`;

@customElement("ir-capture-switch-menu")
export class IrCaptureSwitchMenu extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public row!: CaptureReceiverRow;
    /** The chip is offline: no menu, caret included. */
    @property({ type: Boolean, reflect: true }) public disabled = false;

    @state() private _menu: { top: number; left: number } | null = null;
    @state() private _picking = false;
    @state() private _query = "";
    @state() private _busy = false;
    @state() private _error = "";

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._unlisten();
    }

    private _stop = (e: Event) => e.stopPropagation();

    /** The full name: HA's friendly name, or the server's name for a
     *  switch HA has no state for (an integration that has not loaded). */
    private _name(entityId: string): string {
        if (this.hass?.states?.[entityId]) return entityFullName(this.hass, entityId);
        return this.row.device_switches.find((s) => s.entity_id === entityId)?.name ?? entityId;
    }

    private _online(entityId: string): boolean {
        return isEntityOnline(this.hass?.states, entityId);
    }

    private _healthWord(entityId: string): string {
        return t(this._online(entityId) ? "common.online" : "common.offline");
    }

    /** The shared health dot for a menu or search row. */
    private _dot(entityId: string) {
        return html`<span class="dot ${healthDotClass(this._online(entityId))}"></span>`;
    }

    /** Closes the menu on a click anywhere else, a scroll or a resize. */
    private _outside = (e: Event) => {
        if (!e.composedPath().includes(this)) this._closeMenu();
    };
    private _away = () => this._closeMenu();

    private _listen(): void {
        document.addEventListener("click", this._outside, true);
        window.addEventListener("scroll", this._away, true);
        window.addEventListener("resize", this._away);
    }

    private _unlisten(): void {
        document.removeEventListener("click", this._outside, true);
        window.removeEventListener("scroll", this._away, true);
        window.removeEventListener("resize", this._away);
    }

    private _closeMenu(): void {
        this._menu = null;
        this._unlisten();
    }

    /** Opens the menu under ``anchor`` (the whole chip when the chip's
     *  main part asks, while nothing is picked), or under the caret. */
    public open(anchor?: HTMLElement): void {
        if (this.disabled || this._menu) return;
        // Fixed, from the anchor's own box: the card around it clips.
        const target = anchor ?? this.renderRoot.querySelector<HTMLElement>(".caret-btn");
        const box = (target ?? this).getBoundingClientRect();
        this._menu = { top: box.bottom + 4, left: box.left };
        this._listen();
    }

    private _toggleMenu(): void {
        if (this._menu) this._closeMenu();
        else this.open();
    }

    private async _choose(entityId: string): Promise<boolean> {
        if (this._busy) return false;
        this._busy = true;
        this._error = "";
        try {
            await this.api.setCaptureSwitch(this.row.receiver_entity_id, entityId);
            this.dispatchEvent(
                new CustomEvent("capture-switch-changed", {
                    detail: { receiver_entity_id: this.row.receiver_entity_id, entity_id: entityId },
                    bubbles: true,
                    composed: true,
                }),
            );
            return true;
        } catch (err) {
            this._error = t("capswitch.save_failed");
            return false;
        } finally {
            this._busy = false;
        }
    }

    private async _pickFromMenu(entityId: string): Promise<void> {
        this._closeMenu();
        // A declared switch is final: picking it again changes nothing.
        if (entityId !== this.row.switch_entity_id) await this._choose(entityId);
    }

    private _openPicker(): void {
        this._closeMenu();
        this._query = "";
        this._error = "";
        this._picking = true;
        void this.updateComplete.then(() =>
            this.renderRoot.querySelector<HTMLInputElement>(".pick-search")?.focus(),
        );
    }

    private async _pickFromSearch(entityId: string): Promise<void> {
        if (await this._choose(entityId)) this._picking = false;
    }

    private _onKey(e: KeyboardEvent): void {
        e.stopPropagation();
        if (e.key === "Escape") {
            if (this._picking) this._picking = false;
            else this._closeMenu();
        }
    }

    render() {
        if (!this.row) return nothing;
        return html`
            <span class="wrap" @click=${this._stop} @keydown=${this._onKey}>
                <button
                    class="caret-btn ${this._menu ? "open" : ""}"
                    title=${t("capswitch.choose")}
                    aria-label=${t("capswitch.choose")}
                    aria-haspopup="menu"
                    aria-expanded=${this._menu ? "true" : "false"}
                    ?disabled=${this.disabled || this._busy}
                    @click=${this._toggleMenu}
                >
                    <svg class="caret" viewBox="0 0 24 24" aria-hidden="true">${CARET}</svg>
                </button>
                ${this._menu ? this._renderMenu() : nothing}
                ${this._picking ? this._renderPicker() : nothing}
            </span>
        `;
    }

    private _renderMenu() {
        const items = pickerMenu(this.row, this.row.switch_entity_id ? this._name(this.row.switch_entity_id) : undefined);
        return html`
            <div
                class="menu"
                role="menu"
                style="top:${this._menu!.top}px;left:${this._menu!.left}px"
            >
                ${items.map((item) =>
                    item.kind === "switch"
                        ? html`<button
                              class="item ${item.current ? "cur" : ""}"
                              role="menuitemradio"
                              aria-checked=${item.current ? "true" : "false"}
                              title="${item.name}, ${this._healthWord(item.entityId!)} · ${item.entityId}"
                              @click=${() => void this._pickFromMenu(item.entityId!)}
                          >
                              ${this._dot(item.entityId!)}
                              <span class="txt">
                                  <span class="iname">${item.name}</span>
                                  <span class="iid">${item.entityId}</span>
                              </span>
                              ${item.current
                                  ? html`<svg class="check" viewBox="0 0 24 24" aria-hidden="true">${CHECK}</svg>`
                                  : nothing}
                          </button>`
                        : html`<div class="div" role="separator"></div>
                              <button class="item more" role="menuitem" @click=${this._openPicker}>
                                  ${t("capswitch.choose_other")}
                              </button>`,
                )}
            </div>
        `;
    }

    private _renderPicker() {
        const found = pickerEntities(this.hass?.states, this._query);
        const current = this.row.switch_entity_id;
        return html`
            <div class="overlay" @click=${() => (this._picking = false)}>
                <div
                    class="dialog"
                    role="dialog"
                    aria-label=${t("capswitch.dialog_title", { name: this.row.name })}
                    @click=${this._stop}
                >
                    <h3 class="heading">${t("capswitch.dialog_title", { name: this.row.name })}</h3>
                    <p class="intro">${t("capswitch.dialog_intro")}</p>
                    <input
                        class="pick-search"
                        type="text"
                        .value=${this._query}
                        placeholder=${t("capswitch.search_placeholder")}
                        aria-label=${t("capswitch.search_placeholder")}
                        @input=${(e: Event) => (this._query = (e.target as HTMLInputElement).value)}
                    />
                    <div class="results" role="listbox">
                        ${found.length === 0
                            ? html`<div class="none">${t("capswitch.no_match")}</div>`
                            : found.map(
                                  (e) => html`<button
                                      class="result ${e.entityId === current ? "cur" : ""}"
                                      role="option"
                                      aria-selected=${e.entityId === current ? "true" : "false"}
                                      ?disabled=${this._busy}
                                      title="${e.name}, ${this._healthWord(e.entityId)} · ${e.entityId}"
                                      @click=${() => void this._pickFromSearch(e.entityId)}
                                  >
                                      ${this._dot(e.entityId)}
                                      <span class="txt">
                                          <span class="iname">${e.name}</span>
                                          <span class="iid">${e.entityId}</span>
                                      </span>
                                  </button>`,
                              )}
                    </div>
                    ${this._error ? html`<div class="error">${this._error}</div>` : nothing}
                    <div class="dialog-actions">
                        <button class="action-btn cancel-btn" @click=${() => (this._picking = false)}>
                            ${t("common.cancel")}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            :host {
                display: inline-flex;
                /* The offline ring, one pixel wider than the 7px dot,
                   as in the emitter and receiver pickers. */
                --hair-ring: 8px;
            }
            .wrap {
                display: inline-flex;
                align-self: stretch;
            }
            /* The caret half of the split chip: the chip's own colours,
               behind a thin divider. Visibly just the arrow plus 2px each
               side (owner bench, 2026-10-21); the ::before below is the
               24 by 24px hit area a thumb needs. */
            .caret-btn {
                position: relative;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 0 2px;
                border: none;
                border-left: 1px solid color-mix(in srgb, var(--split-fg, currentColor) 35%, transparent);
                border-radius: 0 4px 4px 0;
                font: inherit;
                color: var(--split-fg, var(--secondary-text-color));
                background: var(--split-bg, var(--secondary-background-color));
                cursor: pointer;
            }
            .caret-btn .caret {
                width: 13px;
                height: 13px;
                flex: none;
                margin: 0 -1px;
                fill: currentColor;
            }
            /* Invisible, centred on the caret, wider and taller than it. */
            .caret-btn::before {
                content: "";
                position: absolute;
                top: 50%;
                left: 50%;
                width: 24px;
                height: 24px;
                transform: translate(-50%, -50%);
            }
            .caret-btn.open,
            .caret-btn:focus-visible {
                outline: none;
                box-shadow: inset 0 0 0 1px var(--split-fg, var(--primary-color));
            }
            .caret-btn:disabled {
                cursor: not-allowed;
            }
            .menu {
                position: fixed;
                z-index: 20;
                min-width: 250px;
                max-width: min(340px, calc(100vw - 24px));
                background: var(--card-background-color);
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
                padding: 6px 0;
                font-size: 0.85rem;
            }
            .item {
                display: flex;
                align-items: center;
                gap: 10px;
                width: 100%;
                padding: 7px 14px;
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
            .item.more {
                color: var(--primary-color);
            }
            .txt {
                display: flex;
                flex-direction: column;
                min-width: 0;
            }
            .iname,
            .iid {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .iid {
                font-size: 0.7rem;
                color: var(--secondary-text-color);
                margin-top: 1px;
            }
            .check {
                width: 15px;
                height: 15px;
                flex: none;
                margin-left: auto;
                fill: var(--primary-color);
            }
            .div {
                height: 1px;
                background: var(--divider-color);
                margin: 5px 0;
            }
            /* The search dialog. */
            .dialog {
                font-size: 0.9rem;
                text-align: left;
                cursor: default;
            }
            .intro {
                margin: -6px 0 12px;
                color: var(--secondary-text-color);
                font-size: 0.85rem;
                line-height: 1.4;
            }
            .results {
                margin-top: 8px;
                max-height: 280px;
                overflow-y: auto;
                border: 1px solid var(--divider-color);
                border-radius: 4px;
            }
            .dot {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                flex: none;
            }
            .result {
                display: flex;
                align-items: center;
                gap: 10px;
                width: 100%;
                padding: 7px 10px;
                border: none;
                border-bottom: 1px solid var(--divider-color);
                background: none;
                font: inherit;
                text-align: left;
                color: var(--primary-text-color);
                cursor: pointer;
            }
            .result:last-child {
                border-bottom: none;
            }
            .result:hover,
            .result:focus-visible {
                outline: none;
                background: var(--secondary-background-color);
            }
            .result.cur {
                background: color-mix(in srgb, var(--primary-color) 10%, transparent);
            }
            .none {
                padding: 14px 10px;
                color: var(--secondary-text-color);
                font-style: italic;
            }
            .error {
                margin-top: 10px;
                color: var(--error-color, #db4437);
                font-size: 0.85rem;
            }
        `,
        healthDotStyles,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-capture-switch-menu": IrCaptureSwitchMenu;
    }
}
