/**
 * The Candy Drawer as a dialog inside the panel: the fallback for when a
 * window of its own cannot be used (a blocked pop-out, the companion app,
 * a phone). See candy-surface.ts for the choice and candy-controller.ts
 * for the pop-out.
 *
 * The console itself is candy-console.ts, the same one the pop-out shows;
 * this element only places it. The overlay covers the panel's own area,
 * taken from the panel element's rect, so nothing sits under Home
 * Assistant's sidebar whether it is open, narrow or hidden. It follows
 * the panel as the sidebar moves.
 *
 * The subscription opens with the dialog and closes with it, and
 * reopening starts empty.
 */
import { LitElement, html, css, unsafeCSS } from "lit";
import { customElement, property } from "./decorators.js";
import type { HairApi } from "./api.js";
import { CANDY_CSS, CandyConsole, type CandyLabels } from "./candy-console.js";
import { CandyFeed } from "./candy-feed.js";
import { browserStorage } from "./media-filter.js";
import { dialogSize, overlayBox, type Box } from "./candy-surface.js";

/** The panel element an element sits in, across shadow roots, or null. */
export function findPanelHost(from: Element): Element | null {
    let node: Node | null = from;
    while (node) {
        if (node instanceof Element && node.tagName === "HA-PANEL-IR-DEVICES") return node;
        node = node.parentNode ?? (node instanceof ShadowRoot ? node.host : null);
    }
    return null;
}

@customElement("ir-candy-drawer")
export class IrCandyDrawer extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public labels!: CandyLabels;
    @property({ attribute: false }) public zone?: string;
    /** The element whose rect is the panel's area (null: the viewport). */
    @property({ attribute: false }) public bounds: Element | null = null;

    private _console: CandyConsole | null = null;
    private _feed: CandyFeed | null = null;
    private _gone = false;
    private _resize: ResizeObserver | null = null;
    private _onResize = () => this._place();

    connectedCallback(): void {
        super.connectedCallback();
        this._gone = false;
        window.addEventListener("resize", this._onResize);
    }

    firstUpdated(): void {
        const mount = this.renderRoot.querySelector<HTMLElement>(".frame");
        if (!mount) return;
        this._console = new CandyConsole({
            doc: document,
            mount,
            labels: this.labels,
            zone: this.zone,
            mode: "dialog",
            onClose: () => this._close(),
            storage: browserStorage(),
            onStaticChange: (on) => this._feed?.start(on),
        });
        if (typeof ResizeObserver !== "undefined" && this.bounds) {
            this._resize = new ResizeObserver(this._onResize);
            this._resize.observe(this.bounds);
        }
        this._place();
        if (this._gone) return;
        this._feed = new CandyFeed(this.api, (event) => this._console?.push(event));
        // Static starts off every time, so the first subscription never asks.
        this._feed.start(false);
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._gone = true;
        window.removeEventListener("resize", this._onResize);
        this._resize?.disconnect();
        this._resize = null;
        this._console?.destroy();
        this._console = null;
        this._feed?.stop();
        this._feed = null;
    }

    /** Fit the overlay to the panel's area and the window inside it. */
    private _place(): void {
        const overlay = this.renderRoot.querySelector<HTMLElement>(".overlay");
        const frame = this.renderRoot.querySelector<HTMLElement>(".frame");
        if (!overlay || !frame) return;
        const rect = this.bounds?.getBoundingClientRect();
        const panel: Box | null = rect
            ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height }
            : null;
        const box = overlayBox(panel, { width: window.innerWidth, height: window.innerHeight });
        Object.assign(overlay.style, {
            left: `${box.left}px`,
            top: `${box.top}px`,
            width: `${box.width}px`,
            height: `${box.height}px`,
        });
        const size = dialogSize(box);
        frame.style.width = `${size.width}px`;
        frame.style.height = `${size.height}px`;
    }

    private _close(): void {
        this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
    }

    render() {
        return html`
            <div class="overlay" @click=${this._close}>
                <div class="frame"></div>
            </div>
        `;
    }

    static styles = [
        unsafeCSS(CANDY_CSS),
        css`
            .overlay {
                position: fixed;
                left: 0;
                top: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0, 0, 0, 0.55);
                z-index: 1000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .frame {
                display: flex;
            }
            .frame > .candy-root {
                flex: 1;
                display: flex;
            }
            .frame > .candy-root > .window {
                flex: 1;
            }
            @media (max-width: 768px) {
                .frame .window {
                    border-radius: 0;
                    border: none;
                }
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-candy-drawer": IrCandyDrawer;
    }
}
