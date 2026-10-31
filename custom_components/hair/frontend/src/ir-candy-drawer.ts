/**
 * The Candy Drawer: a black, monospace window over the Mirror that prints
 * every infrared event as it happens, heard and sent, raw.
 *
 * Nothing is kept. The subscription opens with the window and closes
 * with it, and reopening starts empty. Blocks are laid out by
 * candy-text.ts; this element only appends them, in batches of one per
 * animation frame, so a held button cannot make the page stutter.
 *
 * - Pause queues: blocks that arrive while paused wait and are appended
 *   in order on resume. The cap counts the queue too.
 * - Blocks go in by arrival time, not delivery order (the backend
 *   prints a frame only once its echo verdict is known, a few ms late).
 * - The RX / TX chips hide blocks; they never drop them.
 * - Scrolling up stops the follow and offers "jump to latest";
 *   scrolling back to the bottom resumes it.
 * - Copy all selects the text and tries the clipboard; HA's panel iframe
 *   usually refuses, so the hint asks for Cmd/Ctrl+C (the editor's model).
 * - The window is black whatever the theme, on purpose.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { HairApi } from "./api.js";
import {
    CANDY_CAP,
    copyText,
    formatBlock,
    insertIndex,
    isVisible,
    openedLine,
    overflow,
    type CandyEvent,
} from "./candy-text.js";

interface Block {
    ts: number;
    dir: "rx" | "tx";
    text: string;
    node: HTMLDivElement | null;
}

@customElement("ir-candy-drawer")
export class IrCandyDrawer extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    @state() private _paused = false;
    @state() private _queued = 0;
    @state() private _rx = true;
    @state() private _tx = true;
    @state() private _following = true;
    @state() private _copyHint = "";

    private _blocks: Block[] = [];
    private _queue: Block[] = [];
    private _incoming: CandyEvent[] = [];
    private _frame: number | null = null;
    private _dropped = 0;
    private _opened = Date.now() / 1000;
    private _unsubscribe: (() => Promise<void>) | null = null;
    private _closed = false;

    private _onKey = (e: KeyboardEvent) => {
        if (e.key === "Escape") this._close();
    };

    /** HA's profile setting: the browser's zone, or the server's. */
    private get _zone(): string | undefined {
        return this.hass?.locale?.time_zone === "server"
            ? this.hass?.config?.time_zone || undefined
            : undefined;
    }

    connectedCallback(): void {
        super.connectedCallback();
        window.addEventListener("keydown", this._onKey);
        this._closed = false;
        this.api
            .subscribeCandy((event) => this._receive(event))
            .then((unsub) => {
                if (this._closed) void unsub();
                else this._unsubscribe = unsub;
            })
            .catch(() => {
                /* An admin-only stream: nothing to show otherwise. */
            });
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        window.removeEventListener("keydown", this._onKey);
        this._closed = true;
        if (this._frame !== null) cancelAnimationFrame(this._frame);
        this._frame = null;
        const unsub = this._unsubscribe;
        this._unsubscribe = null;
        if (unsub) void unsub();
    }

    private _receive(event: CandyEvent): void {
        this._incoming.push(event);
        // A hidden tab gets no animation frames, so the cap has to hold
        // here too or a background tab would collect without bound.
        if (this._incoming.length > CANDY_CAP) {
            this._incoming.shift();
            this._dropped += 1;
        }
        if (this._frame === null) {
            this._frame = requestAnimationFrame(() => this._flush());
        }
    }

    private get _log(): HTMLElement | null {
        return this.renderRoot.querySelector<HTMLElement>(".log");
    }

    private _flush(): void {
        this._frame = null;
        if (!this._log) {
            // Not rendered yet: try again on the next frame.
            this._frame = requestAnimationFrame(() => this._flush());
            return;
        }
        const zone = this._zone;
        const arrived = this._incoming.splice(0).map(
            (e): Block => ({ ts: e.ts, dir: e.dir, text: formatBlock(e, zone), node: null }),
        );
        if (this._paused) {
            this._queue.push(...arrived);
            this._queue.sort((a, b) => a.ts - b.ts);
        } else {
            for (const block of arrived) this._place(block);
        }
        this._enforceCap();
        this._queued = this._queue.length;
        if (this._following && !this._paused) this._scrollToEnd();
    }

    private _place(block: Block): void {
        const log = this._log;
        if (!log) return;
        const at = insertIndex(this._blocks.map((b) => b.ts), block.ts);
        const node = document.createElement("div");
        node.className = `blk ${block.dir}`;
        node.textContent = block.text;
        block.node = node;
        const before = this._blocks[at]?.node ?? null;
        log.insertBefore(node, before);
        this._blocks.splice(at, 0, block);
    }

    private _enforceCap(): void {
        let excess = overflow(this._blocks.length, this._queue.length, CANDY_CAP);
        while (excess > 0) {
            const gone = this._blocks.length ? this._blocks.shift() : this._queue.shift();
            gone?.node?.remove();
            this._dropped += 1;
            excess -= 1;
        }
        const line = this.renderRoot.querySelector<HTMLElement>(".capped");
        if (line) {
            line.hidden = this._dropped === 0;
            line.textContent = this._droppedLine() ?? "";
        }
    }

    private _droppedLine(): string | null {
        return this._dropped ? t("candy.capped", { count: this._dropped }) : null;
    }

    private _scrollToEnd(): void {
        const scroller = this.renderRoot.querySelector<HTMLElement>(".screen");
        if (scroller) scroller.scrollTop = scroller.scrollHeight;
    }

    private _onScroll(e: Event): void {
        const el = e.currentTarget as HTMLElement;
        this._following = el.scrollHeight - el.scrollTop - el.clientHeight < 8;
    }

    private _jump(): void {
        this._following = true;
        this._scrollToEnd();
    }

    private _togglePause(): void {
        this._paused = !this._paused;
        if (!this._paused) {
            for (const block of this._queue.splice(0)) this._place(block);
            this._queued = 0;
            if (this._following) this.updateComplete.then(() => this._scrollToEnd());
        }
    }

    private _clear(): void {
        for (const b of this._blocks) b.node?.remove();
        this._blocks = [];
        this._queue = [];
        this._queued = 0;
        this._dropped = 0;
        this._enforceCap();
    }

    private async _copy(): Promise<void> {
        const text = copyText(
            this._marker(),
            this._droppedLine(),
            this._blocks,
            { rx: this._rx, tx: this._tx },
        );
        const screen = this.renderRoot.querySelector<HTMLElement>(".screen");
        if (screen) {
            const range = document.createRange();
            range.selectNodeContents(screen);
            const sel = window.getSelection();
            sel?.removeAllRanges();
            sel?.addRange(range);
        }
        let copied = false;
        try {
            if (window.isSecureContext && navigator.clipboard) {
                await navigator.clipboard.writeText(text);
                copied = true;
            }
        } catch {
            copied = false;
        }
        this._copyHint = copied ? t("editor.copied") : t("editor.press_copy");
    }

    private _marker(): string {
        return openedLine(t("candy.opened"), this._opened, this._zone);
    }

    private _close(): void {
        this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
    }

    render() {
        const filter = { rx: this._rx, tx: this._tx };
        return html`
            <div class="overlay" @click=${this._close}>
                <div
                    class="window"
                    role="dialog"
                    aria-label=${t("candy.title")}
                    @click=${(e: Event) => e.stopPropagation()}
                >
                    <div class="bar">
                        <span class="title">${t("candy.title")}</span>
                        <button class="btn ${this._paused ? "on" : ""}" @click=${this._togglePause}>
                            ${this._paused
                                ? this._queued
                                    ? t("candy.queued", { count: this._queued })
                                    : t("candy.resume")
                                : t("candy.pause")}
                        </button>
                        <button class="btn" @click=${this._clear}>${t("candy.clear")}</button>
                        <button class="btn" @click=${this._copy}>${t("candy.copy")}</button>
                        <button
                            class="chip ${this._rx ? "on" : ""}"
                            aria-pressed=${this._rx ? "true" : "false"}
                            @click=${() => (this._rx = !this._rx)}
                        >${t("candy.rx")}</button>
                        <button
                            class="chip ${this._tx ? "on" : ""}"
                            aria-pressed=${this._tx ? "true" : "false"}
                            @click=${() => (this._tx = !this._tx)}
                        >${t("candy.tx")}</button>
                        ${this._copyHint
                            ? html`<span class="hint">${this._copyHint}</span>`
                            : ""}
                        <button class="x" aria-label=${t("common.close")} @click=${this._close}>
                            &times;
                        </button>
                    </div>
                    <div
                        class="screen ${isVisible("rx", filter) ? "" : "hide-rx"} ${isVisible("tx", filter) ? "" : "hide-tx"}"
                        @scroll=${this._onScroll}
                    >
                        <div class="blk marker">${this._marker()}</div>
                        <div class="blk capped" hidden></div>
                        <div class="log"></div>
                    </div>
                    ${this._following
                        ? ""
                        : html`<button class="jump" @click=${this._jump}>
                              ${t("candy.jump_latest")}
                          </button>`}
                </div>
            </div>
        `;
    }

    static styles = css`
        :host {
            --candy-bg: #0b0b0b;
            --candy-fg: #d8d8d8;
            --candy-dim: #8a8a8a;
            --candy-line: #2a2a2a;
            --candy-accent: #e8e8e8;
        }
        .overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.55);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .window {
            position: relative;
            width: min(1100px, calc(100vw - 48px));
            height: min(820px, calc(100vh - 48px));
            background: var(--candy-bg);
            color: var(--candy-fg);
            border: 1px solid var(--candy-line);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
        }
        .bar {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            padding: 8px 10px;
            border-bottom: 1px solid var(--candy-line);
        }
        .title {
            font-weight: 600;
            color: var(--candy-accent);
            margin-right: 8px;
        }
        .btn,
        .chip,
        .x,
        .jump {
            font: inherit;
            font-size: 12px;
            color: var(--candy-fg);
            background: transparent;
            border: 1px solid var(--candy-line);
            border-radius: 4px;
            padding: 3px 9px;
            cursor: pointer;
        }
        .btn:hover,
        .chip:hover,
        .x:hover,
        .jump:hover {
            border-color: var(--candy-dim);
        }
        .btn.on,
        .chip.on {
            background: #1f1f1f;
            border-color: var(--candy-dim);
            color: var(--candy-accent);
        }
        .chip:not(.on) {
            color: var(--candy-dim);
            text-decoration: line-through;
        }
        .hint {
            font-size: 12px;
            color: var(--candy-dim);
        }
        .x {
            margin-left: auto;
            font-size: 16px;
            line-height: 1;
            padding: 2px 8px;
        }
        .screen {
            flex: 1;
            overflow-y: auto;
            padding: 10px 12px 24px;
            font-size: 12.5px;
            line-height: 1.45;
        }
        .blk {
            white-space: pre-wrap;
            word-break: normal;
            overflow-wrap: break-word;
            margin: 0 0 1.45em;
        }
        .marker,
        .capped {
            color: var(--candy-dim);
        }
        .hide-rx .blk.rx,
        .hide-tx .blk.tx {
            display: none;
        }
        .jump {
            position: absolute;
            right: 16px;
            bottom: 14px;
            background: #1f1f1f;
        }
        @media (max-width: 768px) {
            .window {
                width: 100vw;
                height: 100vh;
                border-radius: 0;
                border: none;
            }
            .screen {
                font-size: 11.5px;
            }
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-candy-drawer": IrCandyDrawer;
    }
}
