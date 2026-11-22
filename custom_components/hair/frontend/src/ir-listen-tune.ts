/**
 * Where a radio receiver listens, on its Sniffer pill: per receiver,
 * and only there.
 *
 * One control for every radio receiver, drawn from the server's one
 * description of it (``hair/rf/receiver_tuning``, its ``form``):
 *
 *   select  the receiver's own presets in order, "Sweep" among them
 *           when it has one; "Other..." when its number feeds an option
 *   number  the common bands, then "Other..."; a band the receiver
 *           doesn't accept is greyed and can't be picked
 *   both    the presets, then "Other..."
 *   fixed   one declared frequency (an Athom): that frequency, no menu,
 *           "This receiver only listens here." on hover
 *   none    a receiver that declares nothing: "auto", or where its open
 *           window locked; no menu, "HAIR can't set where this receiver
 *           listens." on hover
 *
 * A small box at the pill's end, the same as the other pill pickers,
 * reading where the receiver listens now ("433.92", "Sweep"), "setting
 * 433.00..." while a change is on its way, or "band unknown" when a
 * receiver HAIR can set gives nothing. A click opens the menu under it.
 * One click picks and closes the menu. When there is something to say
 * about the pick, a small note takes the menu's place:
 *
 *   a value it doesn't accept      "This receiver doesn't take 390
 *                                   MHz. It takes 305 to 335 and 433.42
 *                                   to 438 MHz." Typed in "Other...",
 *                                   it stays in the box, outlined red,
 *                                   and nothing is sent.
 *   it did not take                "This receiver did not change; it
 *                                   is still listening at {mhz} MHz."
 *   it cannot be tuned             "HAIR can't tune this receiver; it
 *                                   listens where its hardware does."
 *
 * What a receiver accepts is the server's ``accepts`` (its declared
 * ranges, or else its number's own limits); the box's hint shows it.
 * The server says what happened; nothing here guesses. Every click and
 * keydown stops here, because the pill around it is the press. The menu
 * follows its box when the page scrolls or the window resizes (a phone's
 * keyboard opening resizes it) and closes on a click outside, Escape, a
 * pick, or its box leaving the screen.
 */
import { LitElement, html, css, nothing, svg } from "lit";
import { customElement, property, state } from "./decorators.js";
import { formatLanguage, t } from "./localize.js";
import type { HairApi } from "./api.js";
import type { ReceiverTuneResult, ReceiverTuning } from "./types.js";
import { hzToMhz } from "./rf-code.js";
import { listBands, type ListRow } from "./rf-frequency-control.js";

/** A pick: a frequency, or a select option by name. */
export type TunePick = { hz: number } | { option: string };

const CARET = svg`<path d="M7,10L12,15L17,10H7Z" />`;

/** How long the note after a pick stays, unless clicked away first. */
const NOTE_MS = 6000;

/** What the box reads. A pick on its way reads "setting ...". Then
 *  where the receiver listens now, by the server's own order: a
 *  frequency, or "Sweep". A receiver that declares nothing reads "auto";
 *  one HAIR can set but that gives nothing reads "band unknown". The
 *  row's ``trusted`` is for stamping codes in the moment after a set,
 *  not for the box: right after a pick the box shows the value the
 *  receiver now holds, not "band unknown". Pure, for the node tests. */
export function tuneLabel(row: ReceiverTuning | null, pending: TunePick | null): string {
    if (pending !== null) {
        return "hz" in pending
            ? t("listen.tune_setting", { mhz: hzToMhz(pending.hz) })
            : t("listen.tune_setting", { mhz: optionLabel(row, pending.option) });
    }
    if (!row) return t("listen.band_unknown");
    if (row.now.kind === "hz" && row.now.hz) return hzToMhz(row.now.hz);
    if (row.now.kind === "sweep") return t("listen.sweep");
    return row.form === "none" ? t("listen.tune_auto") : t("listen.band_unknown");
}

/** A select option as the list shows it: its band, or "Sweep". */
function optionLabel(row: ReceiverTuning | null, option: string): string {
    const preset = row?.presets.find((p) => p.option === option);
    return preset?.hz ? hzToMhz(preset.hz) : t("listen.sweep");
}

/** The hover line on a receiver HAIR can't set, or null for one it can.
 *  Pure, for the node tests. */
export function stillTitle(row: ReceiverTuning | null): string | null {
    if (row?.form === "fixed") return t("listen.tune_fixed_title");
    if (row?.form === "none") return t("listen.tune_auto_title");
    return null;
}

/** Whether a frequency is outside what the receiver accepts: the
 *  server's ``accepts`` (its declared ranges, or else its number's own
 *  limits). An empty list is no check. Pure, for the node tests. */
export function outsideLimits(row: ReceiverTuning | null, hz: number): boolean {
    const accepts: [number, number][] = row?.accepts ?? [];
    return accepts.length > 0 && !accepts.some(([lo, hi]) => hz >= lo && hz <= hi);
}

/** What a receiver accepts, as words: "305 to 335 and 433.42 to 438"
 *  (``and``) or "... or ..." (``or``), in the panel's language, without
 *  trailing zeros. Pure, for the node tests. */
export function rangesText(accepts: [number, number][], joiner: "and" | "or", lang: string): string {
    const parts = accepts.map(([lo, hi]) =>
        lo === hi ? hzToMhz(lo) : t("listen.tune_range", { low: hzToMhz(lo), high: hzToMhz(hi) }),
    );
    try {
        const type = joiner === "and" ? "conjunction" : "disjunction";
        // Intl.ListFormat joins in the panel's language ("y", "oder");
        // the project's TypeScript lib predates its typing.
        const ListFormat = (Intl as unknown as { ListFormat: new (l: string, o: object) => { format(p: string[]): string } })
            .ListFormat;
        return new ListFormat(lang || "en", { style: "long", type }).format(parts);
    } catch {
        return parts.join(", ");
    }
}

/** The line for a frequency the receiver doesn't take. Pure, for the
 *  node tests. */
export function refusedLine(
    accepts: [number, number][],
    hz: number,
    lang: string,
): { key: string; params: Record<string, string> } {
    return { key: "listen.tune_refused", params: { mhz: hzToMhz(hz), ranges: rangesText(accepts, "and", lang) } };
}

/** The menu for a receiver, or null when there is nothing to pick.
 *  - a select: its presets in order (the number's option is "Other...");
 *  - a number: the common bands, then "Other..."; a band the receiver
 *    doesn't accept is greyed and can't be picked;
 *  - both: the presets, then "Other...";
 *  - fixed or none: no menu.
 *  Pure, for the node tests. */
export function tuneMenu(row: ReceiverTuning | null): { rows: ListRow[]; other: boolean } | null {
    if (!row || row.form === "fixed" || row.form === "none") return null;
    const nowHz = row.now.kind === "hz" ? row.now.hz : null;
    if (row.form === "number") {
        return {
            rows: listBands(nowHz).map((hz) => ({
                key: String(hz),
                label: t("rfedit.mhz", { mhz: hzToMhz(hz) }),
                hz,
                option: null,
                current: hz === nowHz,
                dim: outsideLimits(row, hz),
                blocked: outsideLimits(row, hz),
                title: outsideLimits(row, hz) ? t("listen.tune_band_refused", { mhz: hzToMhz(hz) }) : undefined,
            })),
            other: true,
        };
    }
    const rows = row.presets
        .filter((p) => !p.number)
        .map((p) => ({
            key: p.option,
            label: p.hz ? t("rfedit.mhz", { mhz: hzToMhz(p.hz) }) : t("listen.sweep"),
            hz: p.hz,
            option: p.option,
            current: p.current,
            dim: false,
        }));
    return { rows, other: row.form === "both" || row.presets.some((p) => p.number === true) };
}

/** The one line under the control, or null: a typed frequency the
 *  receiver doesn't take (refused before anything is sent), or what came
 *  of a pick. ``lang`` is for joining the ranges. Pure, for the node
 *  tests. */
export function tuneNote(
    refused: { hz: number; accepts: [number, number][] } | null,
    result: ReceiverTuneResult | null,
    lang = "en",
): { key: string; params?: Record<string, string> } | null {
    if (refused) return refusedLine(refused.accepts, refused.hz, lang);
    if (!result) return null;
    if (result.result === "not_accepted" && result.hz != null) {
        return refusedLine(result.accepts ?? [], result.hz, lang);
    }
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
    /** Shows its value but takes no change (the receiver is down, or
     *  its window is open). */
    @property({ type: Boolean, reflect: true }) public inactive = false;

    @state() private _panel: { top: number; left: number } | null = null;
    /** What the open panel shows: the list, or the note after a pick. */
    @state() private _mode: "list" | "note" = "list";
    private _noteTimer: ReturnType<typeof setTimeout> | null = null;
    @state() private _pending: TunePick | null = null;
    /** A typed frequency the receiver doesn't take: refused here,
     *  nothing sent; it stays in the box, outlined red. */
    @state() private _refused: { hz: number; accepts: [number, number][] } | null = null;
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
        if (mode === "list") {
            this._result = null;
            this._refused = null;
        }
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
    private async _tune(pick: TunePick): Promise<void> {
        this._pending = pick;
        this._refused = null;
        this._result = null;
        this._close();
        let result: ReceiverTuneResult | null = null;
        try {
            result = await this.api.receiverTune(this.receiverEntityId, pick);
        } catch {
            const hz = this.tuning?.now.kind === "hz" ? this.tuning.now.hz : null;
            result = { result: "did_not_change", current_mhz: hz ? hz / 1_000_000 : null };
        }
        // The door refuses what the panel should have: say so with the
        // value that was tried.
        if (result.result === "not_accepted") {
            const tried =
                "hz" in pick ? pick.hz : (this.tuning?.presets.find((p) => p.option === pick.option)?.hz ?? null);
            if (tried !== null) result = { ...result, hz: tried };
        }
        this._pending = null;
        this._result = result;
        if (tuneNote(null, result)) this._showNote();
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
        const label = tuneLabel(this.tuning, this._pending);
        const name = t("listen.tune_title", { value: label });
        const still = stillTitle(this.tuning);
        if (still !== null) {
            // Nothing to pick: a plain value, its line on hover.
            return html`<span class="wrap" @click=${this._stop}>
                <span class="box still" title=${still} aria-label=${`${name}. ${still}`}>
                    <span class="val">${label}</span>
                </span>
            </span>`;
        }
        const lang = formatLanguage();
        const note = tuneNote(this._refused, this._result, lang);
        const accepts: [number, number][] = this.tuning?.accepts ?? [];
        const menu = tuneMenu(this.tuning);
        return html`<span class="wrap" @click=${this._stop} @keydown=${this._onKey}>
            <button
                class="box ${this._panel ? "open" : ""} ${this._pending !== null ? "pending" : ""}"
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
                      ${this._mode === "list" && menu
                          ? html`<div class="heading">${t("listen.tune_heading")}</div>
                                <hair-frequency-control
                                    form="list"
                                    .rows=${menu.rows}
                                    .other=${menu.other}
                                    .accepts=${accepts}
                                    .otherHint=${rangesText(accepts, "or", lang)}
                                    .label=${t("listen.tune_heading")}
                                    ?disabled=${this._pending !== null}
                                    @frequency-pick=${(e: CustomEvent<{ hz?: number; option?: string }>) =>
                                        void this._tune(
                                            e.detail.option !== undefined
                                                ? { option: e.detail.option }
                                                : { hz: e.detail.hz as number },
                                        )}
                                    @frequency-refused=${(e: CustomEvent<{ hz: number | null }>) => {
                                        this._refused = e.detail.hz === null ? null : { hz: e.detail.hz, accepts };
                                    }}
                                    @frequency-done=${() => {
                                        if (this._pending === null) this._close();
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
        .box:disabled,
        .box.still {
            cursor: default;
        }
        /* Nothing to pick: the box's shape, no caret, no press. */
        .box.still {
            padding: 0 5px;
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
