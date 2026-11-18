/**
 * Where a radio receiver listens, on its Sniffer pill: per receiver,
 * and only there.
 *
 * A small box at the pill's end, the same as the other pill pickers,
 * reading the frequency the receiver holds now ("433.92"; for a receiver
 * with one fixed frequency, that one), "setting 433.00..." while a
 * change is on its way, or "band unknown". A click opens a menu under
 * it: the shared frequency control in its list form (every common band,
 * the current one marked, then "Other..." to type one). One click picks
 * and closes the menu. When there is something to say about the pick,
 * a small note takes the menu's place:
 *
 *   outside the receiver's limits  "Outside what this receiver
 *                                   supports; trying anyway." (HAIR
 *                                   still tries)
 *   it did not take                "This receiver did not change; it
 *                                   is still listening at {mhz} MHz."
 *   it cannot be tuned             "HAIR can't tune this receiver; it
 *                                   listens where its hardware does."
 *
 * Offered on every radio receiver; nothing hides it up front. The
 * server says what happened; nothing here guesses. Every click and
 * keydown stops here, because the pill around it is the press. The menu
 * follows its box when the page scrolls or the window resizes (a phone's
 * keyboard opening resizes it) and closes on a click outside, Escape, a
 * pick, or its box leaving the screen.
 */
import { LitElement, html, css, nothing, svg } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { HairApi } from "./api.js";
import type { ReceiverTuneResult, ReceiverTuning } from "./types.js";
import { hzToMhz } from "./rf-code.js";
import "./rf-frequency-control.js";

const CARET = svg`<path d="M7,10L12,15L17,10H7Z" />`;

/** How long the note after a pick stays, unless clicked away first. */
const NOTE_MS = 6000;

/** A receiver's limit in MHz as Hz, or null. */
function mhzOrNull(mhz: number | null | undefined): number | null {
    return mhz == null ? null : Math.round(mhz * 1_000_000);
}

/** What the box reads: the frequency being set, else the one held now,
 *  else "band unknown". Pure, for the node tests. */
export function tuneLabel(tuning: ReceiverTuning | null, pendingHz: number | null): string {
    if (pendingHz !== null) return t("listen.tune_setting", { mhz: hzToMhz(pendingHz) });
    if (tuning?.current_mhz != null) return hzToMhz(Math.round(tuning.current_mhz * 1_000_000));
    return t("listen.band_unknown");
}

/** Whether a frequency is outside the receiver's limits (its number's,
 *  or the ranges it declares). Unknown limits are never "outside". */
export function outsideLimits(tuning: ReceiverTuning | null, hz: number): boolean {
    if (!tuning) return false;
    if (tuning.min_mhz != null && hz < Math.round(tuning.min_mhz * 1_000_000)) return true;
    if (tuning.max_mhz != null && hz > Math.round(tuning.max_mhz * 1_000_000)) return true;
    return false;
}

/** The one line under the control, or null. A pending set outside the
 *  limits says it is trying anyway; an answer says what came of it. */
export function tuneNote(
    pendingOutside: boolean,
    result: ReceiverTuneResult | null,
): { key: string; params?: Record<string, string> } | null {
    if (pendingOutside) return { key: "listen.tune_outside" };
    if (!result) return null;
    if (result.result === "cannot_tune") return { key: "listen.tune_cannot" };
    if (result.result === "did_not_change") {
        const mhz = result.current_mhz != null ? hzToMhz(Math.round(result.current_mhz * 1_000_000)) : "";
        return mhz ? { key: "listen.tune_did_not_change", params: { mhz } } : { key: "listen.tune_cannot" };
    }
    return null;
}

@customElement("ir-listen-tune")
export class IrListenTune extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public receiverEntityId = "";
    @property({ attribute: false }) public tuning: ReceiverTuning | null = null;
    /** Shows its value but takes no change (the receiver is down). */
    @property({ type: Boolean, reflect: true }) public inactive = false;

    @state() private _panel: { top: number; left: number } | null = null;
    /** What the open panel shows: the list, or the note after a pick. */
    @state() private _mode: "list" | "note" = "list";
    private _noteTimer: ReturnType<typeof setTimeout> | null = null;
    @state() private _pendingHz: number | null = null;
    @state() private _pendingOutside = false;
    @state() private _result: ReceiverTuneResult | null = null;

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._close();
    }

    private _outside = (e: Event) => {
        if (!e.composedPath().includes(this)) this._close();
    };
    /** The page scrolled or the window resized: follow the box, and
     *  close only when the box has left the screen. */
    private _away = () => {
        const box = this._boxRect();
        if (!box || box.bottom < 0 || box.top > window.innerHeight) {
            this._close();
            return;
        }
        this._panel = this._placeFor(box);
    };

    private _boxRect(): DOMRect | null {
        return this.renderRoot.querySelector<HTMLElement>(".box")?.getBoundingClientRect() ?? null;
    }

    private _placeFor(box: DOMRect): { top: number; left: number } {
        return { top: box.bottom + 4, left: Math.max(8, Math.min(box.left, window.innerWidth - 220)) };
    }

    private _close(): void {
        if (this._noteTimer !== null) {
            clearTimeout(this._noteTimer);
            this._noteTimer = null;
        }
        if (this._panel === null) return;
        this._panel = null;
        document.removeEventListener("click", this._outside, true);
        window.removeEventListener("scroll", this._away, true);
        window.removeEventListener("resize", this._away);
    }

    private _open(mode: "list" | "note" = "list"): void {
        if (this.inactive && mode === "list") return;
        const box = this._boxRect();
        if (!box) return;
        if (this._panel !== null) {
            this._mode = mode;
            return;
        }
        this._panel = this._placeFor(box);
        this._mode = mode;
        if (mode === "list") this._result = null;
        document.addEventListener("click", this._outside, true);
        window.addEventListener("scroll", this._away, true);
        window.addEventListener("resize", this._away);
    }

    /** The panel goes to the browser's top layer, as the pill pickers'
     *  menus do: the pill is its own stacking context. */
    protected updated(): void {
        const panel = this.renderRoot.querySelector<HTMLElement & { showPopover?: () => void }>(".panel");
        if (panel && typeof panel.showPopover === "function" && !panel.matches(":popover-open")) {
            panel.showPopover();
        }
    }

    /** A pick from the list: the list closes; a note shows only when
     *  there is something to say. */
    private async _tune(hz: number): Promise<void> {
        this._pendingHz = hz;
        this._pendingOutside = outsideLimits(this.tuning, hz);
        this._result = null;
        if (this._pendingOutside) this._open("note");
        else this._close();
        let result: ReceiverTuneResult | null = null;
        try {
            result = await this.api.receiverTune(this.receiverEntityId, hz);
        } catch {
            result = { result: "did_not_change", current_mhz: this.tuning?.current_mhz ?? null };
        }
        this._pendingHz = null;
        this._pendingOutside = false;
        this._result = result;
        if (tuneNote(false, result)) this._showNote();
        else if (this._mode === "note") this._close();
        // The row reads every receiver's tuning again, so the box shows
        // the value the receiver holds now.
        this.dispatchEvent(
            new CustomEvent("tuned", { detail: { receiverEntityId: this.receiverEntityId }, bubbles: true, composed: true }),
        );
    }

    /** The answer's line, under the box, for a few seconds. */
    private _showNote(): void {
        this._open("note");
        if (this._noteTimer !== null) clearTimeout(this._noteTimer);
        this._noteTimer = setTimeout(() => {
            this._noteTimer = null;
            if (this._mode === "note") this._close();
        }, NOTE_MS);
    }

    private _stop = (e: Event) => e.stopPropagation();

    private _onKey(e: KeyboardEvent): void {
        e.stopPropagation();
        if (e.key === "Escape") this._close();
    }

    render() {
        const label = tuneLabel(this.tuning, this._pendingHz);
        const name = t("listen.tune_title", { value: label });
        const note = tuneNote(this._pendingOutside, this._result);
        const currentHz =
            this.tuning?.current_mhz != null ? Math.round(this.tuning.current_mhz * 1_000_000) : null;
        return html`<span class="wrap" @click=${this._stop} @keydown=${this._onKey}>
            <button
                class="box ${this._panel ? "open" : ""} ${this._pendingHz !== null ? "pending" : ""}"
                aria-haspopup=${this.inactive ? "false" : "dialog"}
                aria-expanded=${this._panel ? "true" : "false"}
                aria-label=${name}
                title=${name}
                ?disabled=${this.inactive}
                @click=${() => (this._panel ? this._close() : this._open())}
            >
                <span class="val">${label}</span>
                <svg class="caret ${this.inactive ? "held" : ""}" viewBox="0 0 24 24" aria-hidden="true">${CARET}</svg>
            </button>
            ${this._panel
                ? html`<div
                      class="panel"
                      role="dialog"
                      aria-label=${t("listen.tune_heading")}
                      popover="manual"
                      style="top:${this._panel.top}px;left:${this._panel.left}px"
                  >
                      ${this._mode === "list"
                          ? html`<div class="heading">${t("listen.tune_heading")}</div>
                                <hair-frequency-control
                                    form="list"
                                    .valueHz=${this._pendingHz ?? currentHz}
                                    .minHz=${mhzOrNull(this.tuning?.min_mhz)}
                                    .maxHz=${mhzOrNull(this.tuning?.max_mhz)}
                                    .label=${t("listen.tune_heading")}
                                    ?disabled=${this._pendingHz !== null}
                                    @frequency-changed=${(e: CustomEvent<{ hz: number }>) =>
                                        void this._tune(e.detail.hz)}
                                    @frequency-done=${() => {
                                        if (this._pendingHz === null) this._close();
                                    }}
                                ></hair-frequency-control>`
                          : nothing}
                      ${note ? html`<div class="note">${t(note.key, note.params)}</div>` : nothing}
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
        /* The pill pickers' box (ir-pill-picker.ts), so it reads as one
           of them. */
        .box {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            height: 15px;
            box-sizing: border-box;
            padding: 0 3px 0 5px;
            border: 1px solid color-mix(in srgb, var(--primary-text-color) 22%, transparent);
            border-radius: 8px;
            background: color-mix(in srgb, var(--primary-text-color) 14%, var(--card-background-color, #fff));
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
        :host([inactive]) .box {
            background: transparent;
            border-color: color-mix(in srgb, var(--primary-text-color) 14%, transparent);
            color: var(--secondary-text-color);
        }
        .box.pending .val {
            font-style: italic;
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
        .caret.held {
            visibility: hidden;
        }
        .panel {
            position: fixed;
            z-index: 20;
            inset: auto;
            margin: 0;
            box-sizing: border-box;
            width: max-content;
            min-width: 150px;
            max-width: min(292px, calc(100vw - 16px));
            padding: 8px 6px;
            color: var(--primary-text-color);
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
            font-size: 0.8rem;
        }
        .heading {
            margin: 0 6px 4px;
            font-size: 0.75rem;
            color: var(--secondary-text-color);
        }
        .note {
            margin: 2px 6px;
            font-size: 0.75rem;
            color: var(--secondary-text-color);
            white-space: normal;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-listen-tune": IrListenTune;
    }
}
