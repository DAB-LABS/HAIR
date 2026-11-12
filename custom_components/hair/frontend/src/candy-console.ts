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
 * - The chips (RX TX | IR RF | Known Unknown | Static) hide blocks; they
 *   never drop them. All but Static are kept in this browser; Static
 *   starts off every time, and turning it on or off asks the host to
 *   resubscribe (``onStaticChange``), since single static captures only
 *   come to a subscription that asked. Static is radio only, so it is
 *   off and disabled while RF is off.
 * - Static summaries are not blocks: each receiver gets one line that
 *   adds them up and updates in place.
 * - Scrolling up stops the follow and offers "jump to latest";
 *   scrolling back to the bottom resumes it.
 * - Copy all tries the clipboard, then the browser's copy command on the
 *   selected text, then asks for Cmd/Ctrl+C with the text selected.
 * - ``end()`` prints a closing line and stops; the text stays, to copy.
 */
import {
    CANDY_CAP,
    CANDY_CHIPS_KEY,
    addStatic,
    copyText,
    formatBlock,
    insertIndex,
    isStaticSummary,
    isVisible,
    kindOf,
    openedLine,
    overflow,
    parseChips,
    serializeChips,
    staticLine,
    type CandyEvent,
    type CandyFilter,
    type CandyKind,
} from "./candy-text.js";
import {
    CANDY_GLYPH_IR,
    CANDY_GLYPH_KNOWN,
    CANDY_GLYPH_RF,
    CANDY_GLYPH_STATIC,
    CANDY_GLYPH_UNKNOWN,
    type CandyGlyph,
} from "./candy-glyphs.js";
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
    ir: string;
    rf: string;
    known: string;
    unknown: string;
    static: string;
    /** One receiver's static line, with {count} and {name}. */
    staticHidden: string;
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
    /** The Static chip turned on or off: the host resubscribes. */
    onStaticChange?: (on: boolean) => void;
    /** This browser's storage for the chips; none keeps nothing. */
    storage?: Pick<Storage, "getItem" | "setItem">;
}

type ChipKey = keyof CandyFilter;

interface Block {
    ts: number;
    kind: CandyKind;
    hasVerdict: boolean;
    text: string;
    node: HTMLDivElement | null;
}

/** The glyph a received block carries in front of its text. */
function blockGlyph(kind: CandyKind, hasVerdict: boolean): CandyGlyph | null {
    if (kind.dir !== "rx" || !hasVerdict) return null;
    if (kind.verdict === "static") return CANDY_GLYPH_STATIC;
    return kind.verdict === "known" ? CANDY_GLYPH_KNOWN : CANDY_GLYPH_UNKNOWN;
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
    private chips = new Map<ChipKey, HTMLButtonElement>();
    private staticBox!: HTMLDivElement;
    private staticNodes = new Map<string, HTMLDivElement>();
    private staticTotals = new Map<string, { name: string; count: number }>();
    private controls: HTMLButtonElement[] = [];

    private blocks: Block[] = [];
    private queue: Block[] = [];
    private incoming: CandyEvent[] = [];
    private frame: number | null = null;
    private dropped = 0;
    private paused = false;
    private following = true;
    private filter: CandyFilter;
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
        let stored: string | null = null;
        try {
            stored = opts.storage?.getItem(CANDY_CHIPS_KEY) ?? null;
        } catch {
            stored = null;
        }
        this.filter = parseChips(stored);
        this.build();
        this.win.addEventListener("keydown", this.onKey);
    }

    /** One event from the subscription. */
    push(event: CandyEvent): void {
        if (this.ended) return;
        if (isStaticSummary(event)) {
            this.noteStatic(event);
            return;
        }
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

    /** A glyph as SVG in this console's document. */
    private glyph(g: CandyGlyph, cls: string): SVGSVGElement {
        const ns = "http://www.w3.org/2000/svg";
        const svg = this.doc.createElementNS(ns, "svg");
        svg.setAttribute("viewBox", g.viewBox);
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("focusable", "false");
        svg.setAttribute("class", cls);
        for (const part of g.parts) {
            const node = this.doc.createElementNS(ns, part.tag);
            for (const [k, v] of Object.entries(part.attrs)) node.setAttribute(k, v);
            node.setAttribute("class", part.fill ? "fill" : "stroke");
            svg.appendChild(node);
        }
        return svg;
    }

    /** One chip: a toggle, with its glyph when it has one. */
    private chip(key: ChipKey, label: string, g: CandyGlyph | null): HTMLButtonElement {
        const b = this.button("chip", "", () => this.toggle(key));
        if (g) b.append(this.glyph(g, "glyph"));
        b.append(this.doc.createTextNode(label));
        this.chips.set(key, b);
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
        const chips = this.el("span", "chips");
        chips.append(
            this.chip("rx", l.rx, null),
            this.chip("tx", l.tx, null),
            this.el("span", "sep"),
            this.chip("ir", l.ir, CANDY_GLYPH_IR),
            this.chip("rf", l.rf, CANDY_GLYPH_RF),
            this.el("span", "sep"),
            this.chip("known", l.known, CANDY_GLYPH_KNOWN),
            this.chip("unknown", l.unknown, CANDY_GLYPH_UNKNOWN),
            this.el("span", "sep"),
            this.chip("static", l.static, CANDY_GLYPH_STATIC),
        );
        this.hint = this.el("span", "hint");
        const close = this.button("x", "×", () => this.opts.onClose());
        close.setAttribute("aria-label", l.close);
        if (this.opts.mode === "popout") close.setAttribute("onclick", POPOUT_CLOSE);
        bar.append(this.pauseBtn, clear, this.copyBtn, chips, this.hint, close);
        this.controls = [this.pauseBtn, clear, this.copyBtn, ...this.chips.values()];

        this.screen = this.el("div", "screen");
        this.screen.addEventListener("scroll", () => this.onScroll());
        const marker = this.el(
            "div",
            "blk marker",
            openedLine(l.opened, this.opened, this.zone),
        );
        this.cappedLine = this.el("div", "blk capped");
        this.cappedLine.hidden = true;
        this.staticBox = this.el("div", "statics");
        this.log = this.el("div", "log");
        this.closedLine = this.el("div", "blk closed");
        this.closedLine.hidden = true;
        this.screen.append(marker, this.cappedLine, this.staticBox, this.log, this.closedLine);

        this.jump = this.button("jump", l.jumpLatest, () => {
            this.following = true;
            this.jump.hidden = true;
            this.scrollToEnd();
        });
        this.jump.hidden = true;

        win.append(bar, this.screen, this.jump);
        this.root.append(win);
        this.opts.mount.appendChild(this.root);
        this.paintChips();
    }

    // --- the stream ----------------------------------------------------------

    private flush(): void {
        if (this.frame !== null) this.win.cancelAnimationFrame(this.frame);
        this.frame = null;
        const arrived = this.incoming.splice(0).map(
            (e): Block => ({
                ts: e.ts,
                kind: kindOf(e),
                hasVerdict: !!e.verdict,
                text: formatBlock(e, this.zone),
                node: null,
            }),
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
        const node = this.el("div", `blk ${block.kind.dir}`);
        const g = blockGlyph(block.kind, block.hasVerdict);
        if (g) node.append(this.glyph(g, `mark ${block.kind.verdict}`));
        node.append(this.doc.createTextNode(block.text));
        node.hidden = !isVisible(block.kind, this.filter, block.hasVerdict);
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
            for (const key of this.staticTotals.keys()) this.paintStatic(key);
            for (const block of this.queue.splice(0)) this.place(block);
            if (this.following) this.scrollToEnd();
        }
        this.updatePauseLabel();
    }

    private toggle(key: ChipKey): void {
        if (key === "static" && !this.filter.rf) return;
        const staticWas = this.filter.static;
        this.filter[key] = !this.filter[key];
        // Static is radio only: RF off takes it off too.
        if (key === "rf" && !this.filter.rf) this.filter.static = false;
        this.paintChips();
        for (const b of this.blocks) {
            if (b.node) b.node.hidden = !isVisible(b.kind, this.filter, b.hasVerdict);
        }
        try {
            this.opts.storage?.setItem(CANDY_CHIPS_KEY, serializeChips(this.filter));
        } catch {
            /* a browser that keeps nothing */
        }
        if (this.filter.static !== staticWas) this.opts.onStaticChange?.(this.filter.static);
    }

    private paintChips(): void {
        for (const [key, chip] of this.chips) {
            const on = this.filter[key];
            chip.classList.toggle("on", on);
            chip.setAttribute("aria-pressed", on ? "true" : "false");
        }
        const staticChip = this.chips.get("static");
        if (staticChip && !this.ended) staticChip.disabled = !this.filter.rf;
        this.staticBox.classList.toggle("shown", this.staticShown());
    }

    /** The static lines show with RX and RF on and Static off: they are
     *  received radio, and with Static on the captures print one by one. */
    private staticShown(): boolean {
        return this.filter.rx && this.filter.rf && !this.filter.static;
    }

    /** A static summary: add it to its receiver's line, in place. While
     *  Static is on the captures print one by one, so they are not added
     *  to a count of hidden ones. While paused the count grows but the
     *  line waits for Resume, as blocks do. */
    private noteStatic(event: CandyEvent): void {
        if (this.filter.static) return;
        const key = addStatic(this.staticTotals, event);
        if (!this.paused) this.paintStatic(key);
    }

    private paintStatic(key: string): void {
        const seen = this.staticTotals.get(key);
        if (!seen) return;
        let node = this.staticNodes.get(key);
        if (!node) {
            node = this.el("div", "blk static-line");
            this.staticNodes.set(key, node);
            this.staticBox.append(node);
        }
        node.textContent = staticLine(this.labels.staticHidden, seen.name, seen.count);
    }

    private staticLines(): string[] {
        if (!this.staticShown()) return [];
        return [...this.staticNodes.values()].map((n) => n.textContent ?? "");
    }

    private clear(): void {
        for (const b of this.blocks) b.node?.remove();
        this.blocks = [];
        this.queue = [];
        this.dropped = 0;
        for (const n of this.staticNodes.values()) n.remove();
        this.staticNodes.clear();
        this.staticTotals.clear();
        this.enforceCap();
        this.updatePauseLabel();
    }

    private async copy(): Promise<void> {
        const text = copyText(
            openedLine(this.labels.opened, this.opened, this.zone),
            this.droppedLine(),
            this.blocks,
            this.filter,
            this.staticLines(),
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
.candy-root .chips {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
}
.candy-root .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}
.candy-root .sep {
    width: 1px;
    height: 16px;
    background: var(--candy-line);
    margin: 0 2px;
}
.candy-root svg.glyph,
.candy-root svg.mark {
    width: 14px;
    height: 14px;
    flex: none;
}
.candy-root svg .stroke {
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
}
.candy-root svg .fill {
    fill: currentColor;
    stroke: none;
}
.candy-root .chip.on svg.glyph {
    color: #03a9f4;
}
.candy-root svg.mark {
    display: inline-block;
    vertical-align: -2px;
    margin-right: 6px;
    color: var(--candy-dim);
}
.candy-root svg.mark.unknown {
    color: #ffb74d;
}
.candy-root .statics {
    display: none;
}
.candy-root .statics.shown {
    display: block;
}
.candy-root .static-line {
    color: var(--candy-dim);
    margin-bottom: 0.4em;
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
