/**
 * The self-reporting TEST button.
 *
 * Press it and it says what it did: SENT, or SENT . HEARD when a
 * receiver caught the transmission, held for five seconds so you can
 * look at the device and back, then settled to TEST again. A grey
 * corner dot counts how many times this row has been tried.
 *
 * It exists because the alternative kept failing. The result first
 * lived inline beside the row, where its width changed with what
 * happened and shoved every control after it into a staircase; then
 * on a line below the row, where it read as orphaned from the button
 * that produced it AND was never rendered at all by the matrix row
 * renderer, so TEST looked dead on an entire class of device. Putting
 * the result on the button that caused it fixes both at once (owner
 * design 2026-08-02).
 *
 * THE THREE LABELS ARE STACKED IN ONE GRID CELL with only the active
 * one visible, rather than swapped in and out. The button is therefore
 * always as wide as its widest state in whatever language it is
 * reading, and cannot change width when the label changes -- which
 * would reintroduce exactly the staggering it was built to remove.
 * Measuring would also have worked; this needs no measuring and no
 * maintenance.
 *
 * STATELESS ABOUT PROOF. It reports that a code went over the air. It
 * does not tick a checkbox, mark a verdict, or otherwise claim the
 * device responded -- "heard" means a receiver caught the signal, not
 * that the fan spun. Whoever hosts this button owns the judgement;
 * this button owns only the sending.
 *
 * Usage:
 *   <ir-test-button
 *       .send=${() => this._sendRow(i)}
 *       .disabledReason=${emitter ? null : t("...")}
 *   ></ir-test-button>
 *
 * ``send`` resolves to whether a receiver heard it. Throwing is fine:
 * the button settles and re-enables, and the host surfaces the error.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import "./ir-count-dot.js";

/** How long the result holds before settling back to the name.
 * Five seconds (owner ruling 2026-08-02): long enough to press, look
 * at the device across the room, and look back. */
export const FLASH_HOLD_MS = 5000;

@customElement("ir-test-button")
export class IrTestButton extends LitElement {
    /** Transmit. Resolves true when a receiver heard it back. */
    @property({ attribute: false })
    public send!: () => Promise<boolean>;

    /** Non-null disables the button and becomes its tooltip. The
     * reason is the host's to word: this button does not know why it
     * cannot send, only that it cannot. */
    @property({ attribute: false }) public disabledReason: string | null =
        null;
    /** Locale key for the idle label. Defaults to the component's own
     * word (TEST); a host may pass a different key so the same button
     * can read differently on its surface without forking anything
     * else about it (owner ruling 2026-08-27, Tangles). */
    @property({ attribute: false }) public idleLabelKey = "cmdrow.test";


    /** Seed for the corner dot when a host restores a prior session.
     * Left alone it starts at zero and the button counts its own. */
    @property({ attribute: false }) public count = 0;

    @state() private _busy = false;
    @state() private _flash: "sent" | "heard" | null = null;
    private _timer: number | null = null;

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._clearTimer();
    }

    private _clearTimer(): void {
        if (this._timer !== null) {
            clearTimeout(this._timer);
            this._timer = null;
        }
    }

    private async _press(): Promise<void> {
        if (this._busy || this.disabledReason) return;
        this._busy = true;
        try {
            const heard = await this.send();
            this.count += 1;
            // THIS press, not the row's history: a row heard once and
            // missed twice must not keep claiming HEARD.
            this._show(heard ? "heard" : "sent");
        } catch (err) {
            // The host owns the message. The button's job is to stop
            // looking busy and let the person try again.
            this.dispatchEvent(
                new CustomEvent("test-failed", {
                    detail: { error: err },
                    bubbles: true,
                    composed: true,
                }),
            );
        }
        this._busy = false;
    }

    /** Re-pressing restarts the hold rather than stacking timers. */
    private _show(state: "sent" | "heard"): void {
        this._clearTimer();
        this._flash = state;
        this._timer = window.setTimeout(() => {
            this._flash = null;
            this._timer = null;
        }, FLASH_HOLD_MS);
    }

    render() {
        const flash = this._flash;
        return html`<button
            class="tbtn ${flash ? `flash ${flash}` : ""}"
            ?disabled=${this._busy || !!this.disabledReason}
            title=${this.disabledReason ?? ""}
            @click=${() => void this._press()}
        >
            <span class="stack">
                <span class="lay ${flash ? "" : "on"}"
                    >${t(this.idleLabelKey)}</span
                >
                <span class="lay ${flash === "sent" ? "on" : ""}"
                    >${t("testbtn.sent")}</span
                >
                <span class="lay ${flash === "heard" ? "on" : ""}"
                    >${t("testbtn.sent")} &middot;
                    ${t("testbtn.heard")}</span
                >
            </span>
            ${this.count > 0
                ? html`<ir-count-dot
                      color="grey"
                      .count=${this.count}
                  ></ir-count-dot>`
                : nothing}
        </button>`;
    }

    static styles = css`
        :host {
            display: inline-flex;
            flex: none;
        }
        /* Matches the house row button: same metrics as the Sniffer
           and Clipper action buttons, so it sits in a row of them
           without announcing itself. */
        .tbtn {
            position: relative;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            cursor: pointer;
            font-family: inherit;
            background: none;
            border: 1px solid var(--divider-color);
            color: var(--secondary-text-color);
        }
        .tbtn:hover:not(:disabled) {
            background: rgba(127, 127, 127, 0.14);
            border-color: var(--secondary-text-color);
        }
        .tbtn:active:not(:disabled) {
            background: rgba(127, 127, 127, 0.26);
        }
        .tbtn:disabled {
            opacity: 0.4;
            cursor: default;
        }
        /* All three labels laid out in the same cell; only the active
           one is visible. The grid sizes to the widest, so the button
           never changes width mid-session. */
        .stack {
            display: grid;
        }
        .lay {
            grid-area: 1 / 1;
            visibility: hidden;
            white-space: nowrap;
        }
        .lay.on {
            visibility: visible;
        }
        /* Both results are green (owner ruling 2026-08-02). The first
           cut greyed a send nothing heard back, on the reasoning that
           only a confirmed round trip had earned the colour -- but the
           green means "that press did something", and a send with no
           receiver in the room is still a send. The words already tell
           the two apart. */
        .tbtn.flash {
            color: #66bb6a;
            border-color: rgba(76, 175, 80, 0.5);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-test-button": IrTestButton;
    }
}
