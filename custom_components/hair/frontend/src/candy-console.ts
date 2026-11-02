/**
 * The Candy Drawer's console: the black window itself, as plain DOM.
 *
 * It is not a Lit element on purpose. The same console renders in the
 * pop-out window and in the in-panel dialog, and a pop-out is a second
 * document: custom elements are registered per window and Lit's
 * constructed stylesheets cannot be adopted there. So the console builds
 * its nodes with the target document's own ``createElement`` and carries
 * its styles as one ``<style>`` text (``CANDY_CSS``).
 *
 * Blocks are laid out by candy-text.ts and appended in batches, one per
 * animation frame of the window they are shown in.
 *
 * - Pause queues: blocks that arrive while paused wait and are appended
 *   in order on resume. The cap counts the queue too.
 * - Blocks go in by arrival time, not delivery order.
 * - The RX / TX chips hide blocks; they never drop them.
 * - Scrolling up stops the follow and offers "jump to latest";
 *   scrolling back to the bottom resumes it.
 * - Copy all tries the clipboard, then the browser's copy command on the
 *   selected text, then asks for Cmd/Ctrl+C with the text selected.
 * - ``end()`` prints a closing line and stops; the text stays, to copy.
 */
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
import { CANDY_VIEWBOX, ICON_CANDY } from "./ir-icons.js";

export interface CandyLabels {
    title: string;
    pause: string;
    resume: string;
    queued: (count: number) => string;
    clear: string;
    copy: string;
    rx: string;
    tx: string;
    jumpLatest: string;
    /** The opened marker's template, with {time} and {zone}. */
    opened: string;
    capped: (count: number) => string;
    closed: string;
    close: string;
    copied: string;
    pressCopy: string;
}

export interface CandyConsoleOptions {
    /** The document the console lives in (the pop-out's or the panel's). */
    doc: Document;
    /** Where the console's root node goes. */
    mount: Node;
    labels: CandyLabels;
    /** IANA zone for times, or undefined for the browser's own. */
    zone?: string;
    /** "popout" fills its window; "dialog" sits in the panel's overlay. */
    mode: "popout" | "dialog";
    onClose: () => void;
}

interface Block {
    ts: number;
    dir: "rx" | "tx";
    text: string;
    node: HTMLDivElement | null;
}

/** Inline handlers for the pop-out's X and Copy all, compiled in the
 * pop-out's own window so they keep working once the panel's window
 * has gone (its listeners stop running with it). */
const POPOUT_CLOSE = "window.close()";
const POPOUT_SELECT_COPY =
    "var s=document.querySelector('.screen');var r=document.createRange();" +
    "r.selectNodeContents(s);var g=getSelection();g.removeAllRanges();g.addRange(r);" +
    "try{document.execCommand('copy')}catch(e){}";

export class CandyConsole {
    private readonly doc: Document;
    private readonly win: Window;
    private readonly labels: CandyLabels;
    private readonly zone: string | undefined;
    private readonly opts: CandyConsoleOptions;
    private readonly opened = Date.now() / 1000;

    private root!: HTMLDivElement;
    private screen!: HTMLDivElement;
    private log!: HTMLDivElement;
    private cappedLine!: HTMLDivElement;
    private closedLine!: HTMLDivElement;
    private jump!: HTMLButtonElement;
    private pauseBtn!: HTMLButtonElement;
    private copyBtn!: HTMLButtonElement;
    private hint!: HTMLSpanElement;
    private rxChip!: HTMLButtonElement;
    private txChip!: HTMLButtonElement;
    private controls: HTMLButtonElement[] = [];

    private blocks: Block[] = [];
    private queue: Block[] = [];
    private incoming: CandyEvent[] = [];
    private frame: number | null = null;
    private dropped = 0;
    private paused = false;
    private following = true;
    private filter = { rx: true, tx: true };
    private ended = false;
    private readonly onKey = (e: KeyboardEvent) => {
        if (e.key === "Escape") this.opts.onClose();
    };

    constructor(opts: CandyConsoleOptions) {
        this.opts = opts;
        this.doc = opts.doc;
        this.win = opts.doc.defaultView as Window;
        this.labels = opts.labels;
        this.zone = opts.zone;
        this.build();
        this.win.addEventListener("keydown", this.onKey);
    }

    /** One event from the subscription. */
    push(event: CandyEvent): void {
        if (this.ended) return;
        this.incoming.push(event);
        // A hidden window gets no animation frames, so the cap has to
        // hold here too or a background window would collect without bound.
        if (this.incoming.length > CANDY_CAP) {
            this.incoming.shift();
            this.dropped += 1;
        }
        if (this.frame === null) {
            this.frame = this.win.requestAnimationFrame(() => this.flush());
        }
    }

    /** Print the closing line and stop. The text stays, to select and copy. */
    end(): void {
        if (this.ended) return;
        this.flush();
        if (this.paused) this.togglePause();
        this.ended = true;
        this.closedLine.textContent = this.labels.closed;
        this.closedLine.hidden = false;
        for (const button of this.controls) button.disabled = true;
        if (this.opts.mode === "popout") {
            // From here on only the pop-out's own window runs code: the
            // inline Copy all selects the whole text and copies what it can.
            this.copyBtn.disabled = false;
            this.copyBtn.setAttribute("onclick", POPOUT_SELECT_COPY);
            const fresh = this.copyBtn.cloneNode(true) as HTMLButtonElement;
            this.copyBtn.replaceWith(fresh);
            this.copyBtn = fresh;
        }
        this.scrollToEnd();
    }

    /** Stop any pending frame. The nodes go with their document. */
    destroy(): void {
        if (this.frame !== null) this.win.cancelAnimationFrame(this.frame);
        this.frame = null;
        this.ended = true;
        this.win.removeEventListener("keydown", this.onKey);
    }

    // --- building ----------------------------------------------------------

    private el<K extends keyof HTMLElementTagNameMap>(
        tag: K,
        cls?: string,
        text?: string,
    ): HTMLElementTagNameMap[K] {
        const node = this.doc.createElement(tag);
        if (cls) node.className = cls;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    /**
     * The header's mark: the candy icon in place of the drawer's name. The
     * name stays as the tooltip and the accessible name. Built with the
     * target document's own createElementNS, as everything here is.
     */
    private mark(name: string): HTMLSpanElement {
        const mark = this.el("span", "title");
        mark.setAttribute("role", "img");
        mark.setAttribute("aria-label", name);
        mark.title = name;
        const ns = "http://www.w3.org/2000/svg";
        const svg = this.doc.createElementNS(ns, "svg");
        svg.setAttribute("viewBox", CANDY_VIEWBOX);
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("focusable", "false");
        const path = this.doc.createElementNS(ns, "path");
        path.setAttribute("d", ICON_CANDY);
        svg.appendChild(path);
        mark.appendChild(svg);
        return mark;
    }

    private button(cls: string, text: string, onClick: () => void): HTMLButtonElement {
        const b = this.el("button", cls, text);
        b.type = "button";
        b.addEventListener("click", onClick);
        return b;
    }

    private build(): void {
        const l = this.labels;
        this.root = this.el("div", `candy-root ${this.opts.mode}`);
        const win = this.el("div", "window");
        win.setAttribute("role", this.opts.mode === "dialog" ? "dialog" : "document");
        win.setAttribute("aria-label", l.title);
        if (this.opts.mode === "dialog") {
            win.addEventListener("click", (e) => e.stopPropagation());
        }

        const bar = this.el("div", "bar");
        bar.append(this.mark(l.title));
        this.pauseBtn = this.button("btn", l.pause, () => this.togglePause());
        const clear = this.button("btn", l.clear, () => this.clear());
        this.copyBtn = this.button("btn", l.copy, () => void this.copy());
        this.rxChip = this.button("chip on", l.rx, () => this.toggle("rx"));
        this.txChip = this.button("chip on", l.tx, () => this.toggle("tx"));
        this.rxChip.setAttribute("aria-pressed", "true");
        this.txChip.setAttribute("aria-pressed", "true");
        this.hint = this.el("span", "hint");
        const close = this.button("x", "×", () => this.opts.onClose());
        close.setAttribute("aria-label", l.close);
        if (this.opts.mode === "popout") close.setAttribute("onclick", POPOUT_CLOSE);
        bar.append(this.pauseBtn, clear, this.copyBtn, this.rxChip, this.txChip, this.hint, close);
        this.controls = [this.pauseBtn, clear, this.copyBtn, this.rxChip, this.txChip];

        this.screen = this.el("div", "screen");
        this.screen.addEventListener("scroll", () => this.onScroll());
        const marker = this.el(
            "div",
            "blk marker",
            openedLine(l.opened, this.opened, this.zone),
        );
        this.cappedLine = this.el("div", "blk capped");
        this.cappedLine.hidden = true;
        this.log = this.el("div", "log");
        this.closedLine = this.el("div", "blk closed");
        this.closedLine.hidden = true;
        this.screen.append(marker, this.cappedLine, this.log, this.closedLine);

        this.jump = this.button("jump", l.jumpLatest, () => {
            this.following = true;
            this.jump.hidden = true;
            this.scrollToEnd();
        });
        this.jump.hidden = true;

        win.append(bar, this.screen, this.jump);
        this.root.append(win);
        this.opts.mount.appendChild(this.root);
    }

    // --- the stream ----------------------------------------------------------

    private flush(): void {
        if (this.frame !== null) this.win.cancelAnimationFrame(this.frame);
        this.frame = null;
        const arrived = this.incoming.splice(0).map(
            (e): Block => ({ ts: e.ts, dir: e.dir, text: formatBlock(e, this.zone), node: null }),
        );
        if (this.paused) {
            this.queue.push(...arrived);
            this.queue.sort((a, b) => a.ts - b.ts);
        } else {
            for (const block of arrived) this.place(block);
        }
        this.enforceCap();
        this.updatePauseLabel();
        if (this.following && !this.paused) this.scrollToEnd();
    }

    private place(block: Block): void {
        const at = insertIndex(this.blocks.map((b) => b.ts), block.ts);
        const node = this.el("div", `blk ${block.dir}`, block.text);
        block.node = node;
        this.log.insertBefore(node, this.blocks[at]?.node ?? null);
        this.blocks.splice(at, 0, block);
    }

    private enforceCap(): void {
        let excess = overflow(this.blocks.length, this.queue.length, CANDY_CAP);
        while (excess > 0) {
            const gone = this.blocks.length ? this.blocks.shift() : this.queue.shift();
            gone?.node?.remove();
            this.dropped += 1;
            excess -= 1;
        }
        this.cappedLine.hidden = this.dropped === 0;
        this.cappedLine.textContent = this.droppedLine() ?? "";
    }

    private droppedLine(): string | null {
        return this.dropped ? this.labels.capped(this.dropped) : null;
    }

    // --- controls -------------------------------------------------------------

    private updatePauseLabel(): void {
        const l = this.labels;
        this.pauseBtn.textContent = this.paused
            ? this.queue.length
                ? l.queued(this.queue.length)
                : l.resume
            : l.pause;
        this.pauseBtn.classList.toggle("on", this.paused);
    }

    private togglePause(): void {
        this.paused = !this.paused;
        if (!this.paused) {
            for (const block of this.queue.splice(0)) this.place(block);
            if (this.following) this.scrollToEnd();
        }
        this.updatePauseLabel();
    }

    private toggle(dir: "rx" | "tx"): void {
        this.filter[dir] = !this.filter[dir];
        const chip = dir === "rx" ? this.rxChip : this.txChip;
        chip.classList.toggle("on", this.filter[dir]);
        chip.setAttribute("aria-pressed", this.filter[dir] ? "true" : "false");
        this.screen.classList.toggle("hide-rx", !isVisible("rx", this.filter));
        this.screen.classList.toggle("hide-tx", !isVisible("tx", this.filter));
    }

    private clear(): void {
        for (const b of this.blocks) b.node?.remove();
        this.blocks = [];
        this.queue = [];
        this.dropped = 0;
        this.enforceCap();
        this.updatePauseLabel();
    }

    private async copy(): Promise<void> {
        const text = copyText(
            openedLine(this.labels.opened, this.opened, this.zone),
            this.droppedLine(),
            this.blocks,
            this.filter,
        );
        const range = this.doc.createRange();
        range.selectNodeContents(this.screen);
        const selection = this.win.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);
        let copied = false;
        try {
            const clipboard = this.win.navigator?.clipboard;
            if (this.win.isSecureContext && clipboard) {
                await clipboard.writeText(text);
                copied = true;
            }
        } catch {
            copied = false;
        }
        if (!copied) {
            try {
                // Not a secure origin (a plain http Home Assistant): the
                // browser's own copy of the selected text still works in
                // a window of its own.
                copied = this.doc.execCommand("copy");
            } catch {
                copied = false;
            }
        }
        // Copied: let the selection go. Not copied: leave the text
        // selected for Cmd/Ctrl+C, which the hint asks for.
        if (copied) selection?.removeAllRanges();
        this.hint.textContent = copied ? this.labels.copied : this.labels.pressCopy;
    }

    private onScroll(): void {
        const el = this.screen;
        this.following = el.scrollHeight - el.scrollTop - el.clientHeight < 8;
        this.jump.hidden = this.following;
    }

    private scrollToEnd(): void {
        this.screen.scrollTop = this.screen.scrollHeight;
    }
}

/** The console's styles, as one text for a ``<style>`` in either document. */
export const CANDY_CSS = `
.candy-root {
    --candy-bg: #0b0b0b;
    --candy-fg: #d8d8d8;
    --candy-dim: #8a8a8a;
    --candy-line: #2a2a2a;
    --candy-accent: #e8e8e8;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}
.candy-root .window {
    position: relative;
    background: var(--candy-bg);
    color: var(--candy-fg);
    border: 1px solid var(--candy-line);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-sizing: border-box;
}
.candy-root.dialog .window {
    width: 100%;
    height: 100%;
}
.candy-root.popout .window {
    position: fixed;
    inset: 0;
    border: none;
    border-radius: 0;
}
.candy-root .bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-bottom: 1px solid var(--candy-line);
}
.candy-root .title {
    display: inline-flex;
    align-items: center;
    color: var(--candy-accent);
    margin-right: 8px;
}
.candy-root .title svg {
    display: block;
    width: 20px;
    height: 20px;
    fill: currentColor;
}
.candy-root .btn,
.candy-root .chip,
.candy-root .x,
.candy-root .jump {
    font: inherit;
    font-size: 12px;
    color: var(--candy-fg);
    background: transparent;
    border: 1px solid var(--candy-line);
    border-radius: 4px;
    padding: 3px 9px;
    cursor: pointer;
}
.candy-root button:disabled {
    opacity: 0.4;
    cursor: default;
}
.candy-root .btn:hover:not(:disabled),
.candy-root .chip:hover:not(:disabled),
.candy-root .x:hover,
.candy-root .jump:hover {
    border-color: var(--candy-dim);
}
.candy-root .btn.on,
.candy-root .chip.on {
    background: #1f1f1f;
    border-color: var(--candy-dim);
    color: var(--candy-accent);
}
.candy-root .chip:not(.on) {
    color: var(--candy-dim);
    text-decoration: line-through;
}
.candy-root .hint {
    font-size: 12px;
    color: var(--candy-dim);
}
.candy-root .x {
    margin-left: auto;
    font-size: 16px;
    line-height: 1;
    padding: 2px 8px;
}
.candy-root .screen {
    flex: 1;
    overflow-y: auto;
    padding: 10px 12px 24px;
    font-size: 12.5px;
    line-height: 1.45;
}
.candy-root .blk {
    white-space: pre-wrap;
    word-break: normal;
    overflow-wrap: break-word;
    margin: 0 0 1.45em;
}
.candy-root .marker,
.candy-root .capped,
.candy-root .closed {
    color: var(--candy-dim);
}
.candy-root [hidden] {
    display: none !important;
}
.candy-root .hide-rx .blk.rx,
.candy-root .hide-tx .blk.tx {
    display: none;
}
.candy-root .jump {
    position: absolute;
    right: 16px;
    bottom: 14px;
    background: #1f1f1f;
}
@media (max-width: 768px) {
    .candy-root .screen {
        font-size: 11.5px;
    }
}
`;

/** The pop-out document's own base, beside ``CANDY_CSS``. */
export const CANDY_POPOUT_BASE_CSS = `
html, body {
    margin: 0;
    height: 100%;
    background: #0b0b0b;
    color-scheme: dark;
}
`;
