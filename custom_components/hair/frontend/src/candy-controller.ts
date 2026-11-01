/**
 * The Candy Drawer's pop-out window, owned by the panel's window.
 *
 * The pop-out is a same-origin blank window that this module renders
 * into with the panel's own code (candy-console.ts). The subscription to
 * ``hair/candy/subscribe`` lives here, at module level, not in the Mirror
 * element, so it keeps printing when the Mirror unmounts (another tab of
 * the panel, another Home Assistant page). No new way in: the pop-out
 * never talks to Home Assistant itself and carries no token; the events
 * come over the panel's own connection.
 *
 * - One pop-out at a time, found by its window name: a second click
 *   focuses it.
 * - Closing the pop-out unsubscribes. Reopening starts empty.
 * - When the panel's window reloads or closes, the pop-out prints a
 *   closing line and stops, and keeps its text to copy.
 */
import type { HairApi } from "./api.js";
import {
    CANDY_CSS,
    CANDY_POPOUT_BASE_CSS,
    CandyConsole,
    type CandyLabels,
} from "./candy-console.js";
import { CANDY_POPUP_NAME, popupFeatures } from "./candy-surface.js";

export interface CandyPopoutOptions {
    api: HairApi;
    labels: CandyLabels;
    zone?: string;
    /** The pop-out's window title. */
    title: string;
}

interface Popout {
    win: Window;
    console: CandyConsole;
    unsubscribe: (() => Promise<void>) | null;
    timer: number;
}

let current: Popout | null = null;
let watchingPageHide = false;

/** Whether a pop-out is open and printing. */
export function candyPopoutOpen(): boolean {
    return current !== null && !current.win.closed;
}

/**
 * Open the pop-out, or focus the open one. Call it straight from the
 * click handler, before any await, so popup blockers let it through.
 * Returns false when the browser blocked the window: the caller then
 * opens the in-panel dialog instead.
 */
export function openCandyPopout(opts: CandyPopoutOptions): boolean {
    if (current && !current.win.closed) {
        current.win.focus();
        return true;
    }
    const win = window.open(
        "",
        CANDY_POPUP_NAME,
        popupFeatures(window.screen?.availWidth, window.screen?.availHeight),
    );
    if (!win) return false;
    start(win, opts);
    win.focus();
    return true;
}

function start(win: Window, opts: CandyPopoutOptions): void {
    const doc = win.document;
    // A window of the same name may survive from an earlier load of the
    // panel, still holding that session's text: start it empty.
    doc.documentElement.setAttribute("lang", document.documentElement.lang || "en");
    doc.head.replaceChildren();
    const meta = doc.createElement("meta");
    meta.setAttribute("charset", "utf-8");
    const title = doc.createElement("title");
    title.textContent = opts.title;
    const style = doc.createElement("style");
    style.textContent = CANDY_POPOUT_BASE_CSS + CANDY_CSS;
    doc.head.append(meta, title, style);
    doc.body.replaceChildren();
    // Esc, compiled in the pop-out's own window: it keeps working after
    // the panel's window has gone and its listeners with it.
    doc.body.setAttribute("onkeydown", "if(event.key==='Escape')window.close()");

    const candy = new CandyConsole({
        doc,
        mount: doc.body,
        labels: opts.labels,
        zone: opts.zone,
        mode: "popout",
        onClose: () => win.close(),
    });
    const popout: Popout = {
        win,
        console: candy,
        unsubscribe: null,
        timer: window.setInterval(() => {
            if (win.closed) stop(popout);
        }, 1000),
    };
    current = popout;
    win.addEventListener("pagehide", () => stop(popout));
    if (!watchingPageHide) {
        watchingPageHide = true;
        window.addEventListener("pagehide", panelGone);
    }
    opts.api
        .subscribeCandy((event) => popout.console.push(event))
        .then((unsubscribe) => {
            if (current === popout) popout.unsubscribe = unsubscribe;
            else void unsubscribe().catch(() => undefined);
        })
        .catch(() => {
            /* An admin-only stream: nothing to show otherwise. */
        });
}

/** The pop-out closed (or reloaded): unsubscribe and forget it. */
function stop(popout: Popout): void {
    if (current !== popout) return;
    current = null;
    window.clearInterval(popout.timer);
    popout.console.destroy();
    const unsubscribe = popout.unsubscribe;
    popout.unsubscribe = null;
    if (unsubscribe) void unsubscribe().catch(() => undefined);
}

/** The panel's window is going: the pop-out says so, stops, keeps its text. */
function panelGone(): void {
    const popout = current;
    if (!popout) return;
    current = null;
    window.clearInterval(popout.timer);
    if (!popout.win.closed) popout.console.end();
    const unsubscribe = popout.unsubscribe;
    popout.unsubscribe = null;
    if (unsubscribe) void unsubscribe().catch(() => undefined);
}

/** For the component check: what the pop-out is, without exporting state. */
export function _candyPopoutWindow(): Window | null {
    return current?.win ?? null;
}
