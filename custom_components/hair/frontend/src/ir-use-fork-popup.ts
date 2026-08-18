/**
 * The USE fork popup (add-popups, signpost 3, Track 1).
 *
 * One component, four entry points: closet rows, Sniffer cards, Clipper
 * remotes, Plucker remotes each open this same popup off their USE
 * button (replacing today's ADOPT / ADOPT DEVICE at the same slot and
 * weight -- Track 3 wires each surface's button and source-name/line
 * text; this component only knows how to render the fork and fire the
 * two events once picked). Design source: signpost-3-mockup-s11.html
 * section 1 ("The USE fork"), confirmed final by
 * signpost-3-mockup-handoff.md section 1 -- copy and both glyphs are
 * carried verbatim from there, not re-authored here.
 *
 * COLOR CORRECTION FROM THE MOCKUP: s11's standalone CSS defines the
 * device tile's accent as `--green-peak: #43a047`, a value that does
 * not otherwise exist anywhere in the shipped app as a "device" color
 * -- the real, pervasive device green used everywhere else (Devices
 * tab, action chips, count dots, ir-origin-colors.ts's own `device`
 * entry) is #2e7d32. Using the mockup's #43a047 here would put two
 * visibly different greens next to each other across the same UI,
 * which reads as a bug, not a deliberate second accent. This component
 * uses ORIGIN_COLORS.device (#2e7d32) for the device tile instead, and
 * reuses ORIGIN_COLORS.remote (#f5a623) for the remote tile, which
 * already matches the mockup's gold exactly. Flagging this plainly
 * since it is a deliberate, silent-in-the-doc deviation from the
 * mockup's literal hex value, not an oversight.
 *
 * Usage:
 *   <ir-use-fork-popup
 *       .sourceName=${"Living Room AC"}
 *       .sourceLine=${"Closet wig · 24 signals"}
 *       @use-device=${this._onUseDevice}
 *       @use-remote=${this._onUseRemote}
 *       @closed=${this._onClosed}
 *   ></ir-use-fork-popup>
 *
 * Fires `use-device` / `use-remote` (no detail -- the caller already
 * has the source in hand) and `closed` (X, overlay click, or Escape).
 */
import { LitElement, html, css, unsafeCSS } from "lit";
import { customElement, property } from "./decorators.js";
import { t } from "./localize.js";
import { ORIGIN_COLORS } from "./ir-origin-colors.js";

@customElement("ir-use-fork-popup")
export class IrUseForkPopup extends LitElement {
    /** The source's display name, substituted into both tile titles and
     * the popup heading ("Use {name}"). Same substitution regardless of
     * source kind -- a Closet wig, a Sniffer/Clipper/Plucker remote all
     * read identically. */
    @property() public sourceName = "";

    /** One line describing the source, e.g. "Closet wig · 24 signals"
     * or "Sniffed remote · 40 signals". Caller-computed -- this
     * component has no source-kind knowledge of its own. */
    @property() public sourceLine = "";

    connectedCallback(): void {
        super.connectedCallback();
        document.addEventListener("keydown", this._onKeydown);
    }

    disconnectedCallback(): void {
        document.removeEventListener("keydown", this._onKeydown);
        super.disconnectedCallback();
    }

    private _onKeydown = (e: KeyboardEvent): void => {
        if (e.key === "Escape") {
            this._close();
        }
    };

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _useDevice(): void {
        this.dispatchEvent(
            new CustomEvent("use-device", { bubbles: true, composed: true }),
        );
    }

    private _useRemote(): void {
        this.dispatchEvent(
            new CustomEvent("use-remote", { bubbles: true, composed: true }),
        );
    }

    render() {
        return html`
            <div class="overlay" @click=${this._close}>
                <div class="fork-dlg" @click=${(e: Event) => e.stopPropagation()}>
                    <div class="fork-head">
                        <h4>${t("usefork.title", { name: this.sourceName })}</h4>
                        <span class="x" @click=${this._close} title=${t("common.close")}
                            >&times;</span
                        >
                    </div>
                    ${this.sourceLine
                        ? html`<div class="fork-source">${this.sourceLine}</div>`
                        : ""}
                    <div class="fork-tiles">
                        <div class="fork-tile t-device" @click=${this._useDevice}>
                            <div class="glyph">
                                <svg viewBox="0 0 490.797 490.797" fill="currentColor">
                                    <g>
                                        <g>
                                            <path
                                                d="M56.879,450.427c9.517,1.554,20.216,3.072,32.626,4.621c0.508,1.838,1.041,3.661,1.569,5.484c1.153,3.966,2.351,8.059,3.22,12.115c1.412,6.607,7.978,11.583,15.279,11.583c1.356,0,2.691-0.178,3.961-0.522c8.079-2.225,12.781-10.42,10.938-19.062c-0.432-2.026-0.939-4.022-1.453-5.911c46.662,4.397,99.148,6.622,156.087,6.622c29.071,0,58.971-0.59,88.91-1.752c-0.396,2.392-1.025,4.656-1.985,7.17c-1.314,3.468-1.03,7.378,0.817,11.014c2.093,4.123,5.84,7.271,10.009,8.42c1.402,0.386,2.813,0.589,4.199,0.589l0,0c6.571,0,12.289-4.316,14.925-11.253c1.909-5.018,3.011-10.45,3.514-17.387c15.991-0.838,31.347-1.788,45.682-2.839c9.485-0.69,14.619-8.439,14.904-15.899c32.245-93.363,31.478-201.943-2.225-314.032c-2.026-6.743-7.643-10.933-14.665-10.933c-0.828,0-1.66,0.061-2.488,0.175c-1.514-0.437-2.925-0.645-4.383-0.645c-32.772-0.084-68.237-0.734-105.784-1.424c-39.166-0.719-79.587-1.462-119.602-1.597c26.334-17.189,52.131-35.561,76.779-54.692c4.946-3.836,6.713-9.161,4.845-14.609c-2.229-6.51-9.283-11.42-16.402-11.42c-3.595,0-7.063,1.216-10.034,3.521c-35.688,27.677-74.326,53.771-114.869,77.538l-4.108,0.063c-7.003-37.315-16.595-71.648-29.29-104.901C115.388,4.009,109.502,0,102.49,0c-5.535,0-10.705,2.501-13.472,6.535c-2.478,3.596-2.869,8.107-1.112,12.7c11.811,30.922,20.886,62.657,27.695,96.918c-26.096,0.868-48.982,2.178-69.873,3.994c-5.967,0.516-10.75,3.895-13.213,9.303c-1.742,1.785-3.011,3.94-3.773,6.421c-32.575,106.863-28.335,212.94,12.258,306.75C43.87,449.259,50.192,452.296,56.879,450.427z M57.032,150.517c37.923-2.93,84.092-4.354,141.051-4.354c44.26,0,89.327,0.822,132.916,1.617c35.476,0.645,69.025,1.259,100.006,1.394c28.386,101.054,28.701,195.174,0.925,279.825c-50.582,3.478-104.114,5.321-154.935,5.321c-82.177,0-155.305-4.834-211.614-13.995C32.226,338.899,29.342,245.688,57.032,150.517z"
                                            ></path>
                                            <path
                                                d="M99.306,407.589c43.6,7.114,89.738,10.572,140.995,10.572c0,0,0,0,0.005,0c32.662,0,67.853-1.411,107.577-4.326c8.506-0.625,13.208-7.363,13.686-14.005c23.008-66.994,22.424-144.794-1.701-225.025c-2.037-6.762-8.171-10.766-15.168-10.096c-1.123-0.269-2.229-0.403-3.352-0.403c-24.359-0.063-49.155-0.584-73.128-1.087c-25.634-0.541-52.136-1.092-78.216-1.092c-38.156,0-69.639,1.191-99.061,3.743c-5.215,0.452-9.592,3.433-11.908,8.039c-1.417,1.571-2.452,3.417-3.092,5.507c-23.41,76.8-20.353,153.061,8.851,220.547C87.373,405.913,93.223,408.95,99.306,407.589z M101.85,193.971c26.472-1.983,54.761-2.913,88.626-2.913c25.908,0,52.278,0.546,77.784,1.082c21.876,0.452,44.448,0.924,66.75,1.049c19.104,69.464,19.342,134.208,0.717,192.554c-35.871,2.438-67.599,3.621-96.888,3.621c-47.931,0-90.896-3.144-131.235-9.613C85.23,323.579,83.24,259.495,101.85,193.971z"
                                            ></path>
                                            <path
                                                d="M411.912,232.147c4.672,0,8.617-1.722,11.415-4.972c2.433-2.828,3.773-6.608,3.773-10.638c0-7.759-5.216-15.61-15.188-15.61c-4.672,0-8.617,1.722-11.415,4.972c-2.433,2.828-3.773,6.609-3.773,10.638C396.723,224.294,401.938,232.147,411.912,232.147z"
                                            ></path>
                                            <path
                                                d="M413.537,249.715c-4.667,0-8.612,1.727-11.41,4.977c-2.433,2.823-3.778,6.606-3.778,10.633c0,7.759,5.215,15.61,15.184,15.61c4.672,0,8.617-1.717,11.41-4.967c2.432-2.834,3.777-6.611,3.777-10.644C428.725,257.575,423.504,249.715,413.537,249.715z"
                                            ></path>
                                        </g>
                                    </g>
                                </svg>
                            </div>
                            <div class="t-title">
                                ${t("usefork.device_title", { name: this.sourceName })}
                            </div>
                            <div class="t-line">${t("usefork.device_line")}</div>
                        </div>
                        <div class="fork-tile t-remote" @click=${this._useRemote}>
                            <div class="glyph">
                                <svg viewBox="0 0 50 50" fill="currentColor">
                                    <path
                                        d="M36.78125 0C36.230469 0.0703125 35.835938 0.574219 35.90625 1.125C35.976563 1.675781 36.480469 2.070313 37.03125 2C37.03125 2 37.820313 1.960938 39.1875 2.40625C40.554688 2.851563 42.402344 3.757813 44.28125 5.6875C46.171875 7.625 47.105469 9.480469 47.5625 10.84375C48.019531 12.207031 48 13 48 13C47.996094 13.359375 48.183594 13.695313 48.496094 13.878906C48.808594 14.058594 49.191406 14.058594 49.503906 13.878906C49.816406 13.695313 50.003906 13.359375 50 13C50 13 49.980469 11.832031 49.4375 10.21875C48.894531 8.605469 47.828125 6.476563 45.71875 4.3125C43.597656 2.140625 41.445313 1.03125 39.8125 0.5C38.179688 -0.03125 36.96875 0 36.96875 0C36.9375 0 36.90625 0 36.875 0C36.84375 0 36.8125 0 36.78125 0 Z M 28.6875 6C27.625 6 26.554688 6.382813 25.71875 7.15625C25.707031 7.167969 25.699219 7.175781 25.6875 7.1875L1.1875 31.78125C-0.40625 33.375 -0.390625 36.011719 1.15625 37.6875C1.167969 37.699219 1.175781 37.707031 1.1875 37.71875L12.40625 48.90625C14 50.5 16.605469 50.484375 18.28125 48.9375C18.292969 48.925781 18.300781 48.917969 18.3125 48.90625L42.8125 24.40625C42.824219 24.386719 42.835938 24.363281 42.84375 24.34375C44.351563 22.585938 44.40625 20 42.8125 18.40625L31.59375 7.1875C30.796875 6.390625 29.75 6 28.6875 6 Z M 36.8125 6C36.261719 6.050781 35.855469 6.542969 35.90625 7.09375C35.957031 7.644531 36.449219 8.050781 37 8C37 8 37.3125 7.980469 37.9375 8.1875C38.5625 8.394531 39.398438 8.835938 40.28125 9.71875C41.164063 10.601563 41.605469 11.4375 41.8125 12.0625C42.019531 12.6875 42 13 42 13C41.996094 13.359375 42.183594 13.695313 42.496094 13.878906C42.808594 14.058594 43.191406 14.058594 43.503906 13.878906C43.816406 13.695313 44.003906 13.359375 44 13C44 13 43.980469 12.3125 43.6875 11.4375C43.394531 10.5625 42.835938 9.398438 41.71875 8.28125C40.601563 7.164063 39.4375 6.605469 38.5625 6.3125C37.6875 6.019531 37 6 37 6C36.96875 6 36.9375 6 36.90625 6C36.875 6 36.84375 6 36.8125 6 Z M 28.6875 8C29.25 8 29.785156 8.191406 30.1875 8.59375L41.40625 19.8125C42.214844 20.621094 42.238281 22.019531 41.34375 23.0625L16.90625 47.46875C15.980469 48.320313 14.621094 48.308594 13.8125 47.5L2.625 36.3125C2.613281 36.300781 2.605469 36.292969 2.59375 36.28125C1.769531 35.355469 1.796875 34.015625 2.59375 33.21875L27.09375 8.625C27.554688 8.199219 28.125 8 28.6875 8 Z M 28 14C23.59375 14 20 17.59375 20 22C20 26.40625 23.59375 30 28 30C32.40625 30 36 26.40625 36 22C36 17.59375 32.40625 14 28 14 Z M 28 16C31.324219 16 34 18.675781 34 22C34 25.324219 31.324219 28 28 28C24.675781 28 22 25.324219 22 22C22 18.675781 24.675781 16 28 16 Z M 28 20C26.894531 20 26 20.894531 26 22C26 23.105469 26.894531 24 28 24C29.105469 24 30 23.105469 30 22C30 20.894531 29.105469 20 28 20 Z M 15 27C13.894531 27 13 27.894531 13 29C13 30.105469 13.894531 31 15 31C16.105469 31 17 30.105469 17 29C17 27.894531 16.105469 27 15 27 Z M 10 32C8.894531 32 8 32.894531 8 34C8 35.105469 8.894531 36 10 36C11.105469 36 12 35.105469 12 34C12 32.894531 11.105469 32 10 32 Z M 21 33C19.894531 33 19 33.894531 19 35C19 36.105469 19.894531 37 21 37C22.105469 37 23 36.105469 23 35C23 33.894531 22.105469 33 21 33 Z M 16 38C14.894531 38 14 38.894531 14 40C14 41.105469 14.894531 42 16 42C17.105469 42 18 41.105469 18 40C18 38.894531 17.105469 38 16 38Z"
                                    ></path>
                                </svg>
                            </div>
                            <div class="t-title">
                                ${t("usefork.remote_title", { name: this.sourceName })}
                            </div>
                            <div class="t-line">${t("usefork.remote_line")}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        .overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .fork-dlg {
            width: 420px;
            max-width: calc(100vw - 32px);
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 10px;
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
            overflow: hidden;
        }
        .fork-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 16px;
            border-bottom: 1px solid var(--divider-color);
        }
        .fork-head h4 {
            margin: 0;
            font-size: 1.02rem;
            font-weight: 600;
            color: var(--primary-text-color);
        }
        .fork-head .x {
            color: var(--secondary-text-color);
            font-size: 18px;
            line-height: 1;
            cursor: pointer;
            padding: 2px 4px;
        }
        .fork-source {
            padding: 10px 16px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            border-bottom: 1px solid var(--divider-color);
        }
        .fork-tiles {
            display: flex;
            gap: 12px;
            padding: 16px;
        }
        .fork-tile {
            flex: 1;
            border: 1.5px solid var(--divider-color);
            border-radius: 8px;
            padding: 16px 12px;
            text-align: center;
            cursor: pointer;
            transition: border-color 120ms ease, background 120ms ease;
        }
        .fork-tile:hover {
            background: var(--secondary-background-color);
        }
        .fork-tile.t-device:hover {
            border-color: ${unsafeCSS(ORIGIN_COLORS.device)};
        }
        .fork-tile.t-device .glyph {
            background: rgba(46, 125, 50, 0.14);
            color: ${unsafeCSS(ORIGIN_COLORS.device)};
        }
        .fork-tile.t-remote:hover {
            border-color: ${unsafeCSS(ORIGIN_COLORS.remote)};
        }
        .fork-tile.t-remote .glyph {
            background: rgba(245, 166, 35, 0.14);
            color: ${unsafeCSS(ORIGIN_COLORS.remote)};
        }
        .glyph {
            width: 40px;
            height: 40px;
            margin: 0 auto 10px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .glyph svg {
            width: 20px;
            height: 20px;
        }
        .t-title {
            font-size: 0.88rem;
            font-weight: 600;
            margin-bottom: 4px;
            color: var(--primary-text-color);
        }
        .t-line {
            font-size: 0.72rem;
            color: var(--secondary-text-color);
            line-height: 1.35;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-use-fork-popup": IrUseForkPopup;
    }
}
