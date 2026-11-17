/**
 * Where a radio receiver listens, on its Sniffer pill: per receiver,
 * and only there.
 *
 * A small box at the pill's end, the same as the other pill pickers,
 * reading the frequency the receiver holds now ("433.92"), "setting
 * 433.00..." while a change is on its way, or "band unknown". A click
 * opens a panel under it: "Listening at", the shared frequency control
 * (rf-frequency-control.ts: the band pills, Other with its list), and
 * one line when there is something to say:
 *
 *   outside the receiver's limits  "Outside what this receiver
 *                                   supports; trying anyway." (HAIR
 *                                   still tries)
 *   it did not take                "This receiver did not change; it
 *                                   is still listening at {mhz} MHz."
 *   it cannot be tuned             "HAIR can't tune this receiver; it
 *                                   listens where its hardware does."
 *
 * Offered on every radio receiver; nothing hides it up front. The server says what happened; nothing here guesses.
 * Every click and keydown stops here, because the pill around it is
 * the press.
 */
import { LitElement, html, css, nothing, svg } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { HairApi } from "./api.js";
import type { ReceiverTuneResult, ReceiverTuning } from "./types.js";
import { hzToMhz } from "./rf-code.js";
import "./rf-frequency-control.js";

const CARET = svg`<path d="M7,10L12,15L17,10H7Z" />`;

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
    private _away = () => this._close();

    private _close(): void {
        if (this._panel === null) return;
        this._panel = null;
        document.removeEventListener("click", this._outside, true);
        window.removeEventListener("scroll", this._away, true);
        window.removeEventListener("resize", this._away);
    }

    private _open(): void {
        if (this.inactive) return;
        const box = this.renderRoot.querySelector<HTMLElement>(".box")?.getBoundingClientRect();
        if (!box) return;
        const left = Math.max(8, Math.min(box.left, window.innerWidth - 300));
        this._panel = { top: box.bottom + 4, left };
        this._result = null;
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

    private async _tune(hz: number): Promise<void> {
        this._pendingHz = hz;
        this._pendingOutside = outsideLimits(this.tuning, hz);
        this._result = null;
        let result: ReceiverTuneResult | null = null;
        try {
            result = await this.api.receiverTune(this.receiverEntityId, hz);
        } catch {
            result = { result: "did_not_change", current_mhz: this.tuning?.current_mhz ?? null };
        }
        this._pendingHz = null;
        this._pendingOutside = false;
        this._result = result;
        // The row reads every receiver's tuning again, so the box shows
        // the value the receiver holds now.
        this.dispatchEvent(
            new CustomEvent("tuned", { detail: { receiverEntityId: this.receiverEntityId }, bubbles: true, composed: true }),
        );
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
                      <div class="heading">${t("listen.tune_heading")}</div>
                      <hair-frequency-control
                          .valueHz=${this._pendingHz ?? currentHz}
                          .label=${t("listen.tune_heading")}
                          ?disabled=${this._pendingHz !== null}
                          @frequency-changed=${(e: CustomEvent<{ hz: number }>) => void this._tune(e.detail.hz)}
                      ></hair-frequency-control>
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
            width: min(292px, calc(100vw - 16px));
            padding: 10px 12px;
            color: var(--primary-text-color);
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
            font-size: 0.8rem;
        }
        .heading {
            margin-bottom: 8px;
            font-weight: 500;
        }
        .note {
            margin-top: 8px;
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
