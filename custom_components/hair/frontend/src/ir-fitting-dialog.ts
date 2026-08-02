/**
 * The fitting dialog (Perfect Fit) -- proving a wig on real hardware.
 *
 * Owner rulings baked in (fitting-flow.md Sections 12, 13, 15):
 * - The row's Fit button opens STRAIGHT into the session; there is no
 *   editor detour and no Resume button -- reopening IS resuming,
 *   because marks persist in the wig file as you go.
 * - No auto-advance: after a verdict the list stays put. Untested
 *   signals sort first ON OPEN only; the order never shuffles
 *   mid-session.
 * - SEND stays after sending; the machine facts (sent count, heard
 *   back) update per send.
 * - Actions are CLOSE / DISCARD / FINISH -- no "fitting" in the
 *   labels. Close keeps everything; Discard is the explicit
 *   throw-away, confirmed inline.
 * - The green moment: every signal marked worked flips the progress
 *   line and fills FINISH solid green. "Perfect Fit" appears in the
 *   signing sentence (State C), never on a button.
 * - Standard dialog size at every signal count; the list scrolls.
 *
 * Smart Perm adds REPLACE as the fourth button on EVERY row (mockup
 * RP2, ruled 2026-07-30): no verdict is required first, because a
 * fitter should not have to declare failure before repairing. The
 * strip opens inline under its row with a paste box and a LISTEN
 * button that captures from the real remote through the Sniffer.
 * Confirming rolls the wig's identity, so the dialog refetches state
 * and says plainly what happened: the row returns untested, the other
 * verdicts carried, finishing re-signs everything.
 *
 * Two views in one dialog: the session (State B) and the signing
 * confirm (State C). Dispatches ``closed`` always, plus ``recorded``
 * with the finish result so the closet can refresh its check marks.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-protocol-chip.js";
import type { HairApi } from "./api.js";
import type {
    FittingListenEvent,
    FittingRow,
    FittingState,
    WigInfo,
} from "./types.js";
import { displayTemp, installUnit } from "./temperature.js";
import { isDittoable } from "./ir-tx-knobs.js";

// Curated kind suggestions; the input accepts anything (custom kinds
// welcome) and the server squashes to lowercase alphanumerics.
const KIND_SUGGESTIONS = [
    "tv", "soundbar", "receiver", "settopbox", "projector",
    "fan", "light", "candles", "ac", "heater", "blinds",
];

interface RowFacts {
    sent: number;
    heard: boolean;
    busy: boolean;
}

/** What the Replace strip knows about the code currently in its box.
 * Null while the box holds a hand-typed paste: the quality line
 * describes a CAPTURE, and saying "clean capture" over text somebody
 * pasted would be a claim nothing made. */
interface CaptureQuality {
    decoded: boolean;
    protocol: string | null;
    receiver: string | null;
}

/** Display cleanup for a prefilled GitHub handle: strip a profile URL
 * down to its account (everything up to the first remaining slash, so
 * a copied repo URL yields the owner, not owner/repo), drop a typed @.
 * Prefill only; the backend normalizes again at record time. */
/** Row verdicts, read off the ROWS rather than the draft lists.
 * The rows are authoritative: when a replace has rolled the hash and
 * no draft exists on the new codes yet, they carry the carry-forward
 * preview, and reading the (absent) draft instead would show a wiped
 * session that then appeared to invent verdicts on the first tap. */
function _verdictsOf(fit: FittingState): Map<number, "worked" | "failed"> {
    const verdicts = new Map<number, "worked" | "failed">();
    fit.rows.forEach((row, i) => {
        if (row.failed) verdicts.set(i, "failed");
        else if (row.confirmed) verdicts.set(i, "worked");
    });
    return verdicts;
}

function _cleanGithubHandle(value: string): string {
    let v = value.trim();
    v = v.replace(/^https?:\/\/(www\.)?github\.com\//i, "");
    v = v.replace(/^@+/, "");
    const slash = v.indexOf("/");
    if (slash !== -1) v = v.slice(0, slash);
    return v.trim();
}

// The comb, from images/comb.svg. The skipped chip wears the tool that
// made the decision (owner ruling CS1, option A) in the chip's own
// muted grey rather than a signal colour: amber means doubt, and a
// bypassed row is not in doubt, somebody decided.
/** How long TEST holds its result before settling back to its name.
 * Five seconds (owner ruling 2026-08-02): long enough to press, look
 * at the device across the room, and look back. */
const FLASH_HOLD_MS = 5000;

const ICON_COMB =
    "M367.808,240.512c-37.163-31.232-58.475-60.565-58.475-80.512c0-23.019,5.568-37.077,10.944-50.667c5.099-12.885,10.389-26.24,10.389-45.333c0-43.669-23.723-64-74.667-64s-74.667,20.331-74.667,64c0,19.093,5.291,32.448,10.389,45.355c5.376,13.589,10.944,27.648,10.944,50.667c0,19.925-21.312,49.259-58.475,80.512c-17.067,14.357-26.859,35.264-26.859,57.344v203.456c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667v-160H160v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667S224,507.221,224,501.333v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160H288v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667V297.856C394.667,275.776,384.875,254.891,367.808,240.512z M373.333,320H138.667v-22.123c0-15.765,7.019-30.741,19.264-41.024C188.075,231.509,224,194.133,224,160c0-27.093-6.613-43.797-12.437-58.517c-4.779-12.075-8.896-22.464-8.896-37.483c0-27.669,8.491-42.667,53.333-42.667S309.333,36.331,309.333,64c0,15.019-4.117,25.408-8.896,37.483C294.613,116.203,288,132.885,288,160c0,34.133,35.925,71.509,66.069,96.853c12.245,10.304,19.264,25.259,19.264,41.024V320z";
// mdi:repeat -- whole-frame send count, gold. Same mark the catalog
// rows use, so the two surfaces read as one vocabulary.
const ICON_REPEAT =
    "M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z";
// mdi:dots-horizontal -- NEC dittos, blue.
const ICON_DITTO =
    "M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z";
// mdi:thumb-up-outline / mdi:thumb-up, and their down twins. The
// verdict rides the DIRECTION, so it survives colourblindness.
const ICON_THUMB_UP_OUTLINE =
    "M5,9V21H1V9H5M9,21A2,2 0 0,1 7,19V9C7,8.45 7.22,7.95 7.59,7.59L14.17,1L15.23,2.06C15.5,2.33 15.67,2.7 15.67,3.11L15.64,3.43L14.69,8H21C22.11,8 23,8.9 23,10V12C23,12.26 22.95,12.5 22.86,12.73L19.84,19.78C19.54,20.5 18.83,21 18,21H9M9,19H18.03L21,12V10H12.21L13.34,4.68L9,9.03V19Z";
const ICON_THUMB_UP_SOLID =
    "M23,10C23,8.89 22.1,8 21,8H14.68L15.64,3.43C15.66,3.33 15.67,3.22 15.67,3.11C15.67,2.7 15.5,2.32 15.23,2.05L14.17,1L7.59,7.58C7.22,7.95 7,8.45 7,9V19A2,2 0 0,0 9,21H18C18.83,21 19.54,20.5 19.84,19.78L22.86,12.73C22.95,12.5 23,12.26 23,12V10M1,21H5V9H1V21Z";
const ICON_THUMB_DOWN_OUTLINE =
    "M19,15V3H23V15H19M15,3A2,2 0 0,1 17,5V15C17,15.55 16.78,16.05 16.41,16.41L9.83,23L8.77,21.94C8.5,21.67 8.33,21.3 8.33,20.88L8.36,20.57L9.31,16H3C1.89,16 1,15.1 1,14V12C1,11.74 1.05,11.5 1.14,11.27L4.16,4.22C4.46,3.5 5.17,3 6,3H15M15,5H5.97L3,12V14H11.79L10.66,19.32L15,14.97V5Z";
const ICON_THUMB_DOWN_SOLID =
    "M19,15H23V3H19M15,3H6C5.17,3 4.46,3.5 4.16,4.22L1.14,11.27C1.05,11.5 1,11.74 1,12V14A2,2 0 0,0 3,16H9.31L8.36,20.57C8.34,20.67 8.33,20.77 8.33,20.88C8.33,21.3 8.5,21.67 8.77,21.94L9.83,23L16.41,16.41C16.78,16.05 17,15.55 17,15V5C17,3.89 16.1,3 15,3Z";

@customElement("ir-fitting-dialog")
export class IrFittingDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public wig!: WigInfo;

    @state() private _fit: FittingState | null = null;
    @state() private _order: number[] = [];
    @state() private _verdicts = new Map<number, "worked" | "failed">();
    @state() private _facts = new Map<number, RowFacts>();
    @state() private _emitter = "";
    // Session send-times control (fine-tuned-fittings). Every fresh
    // session starts at 1; NEVER carried between wigs, because a
    // remembered 3 quietly inflates every later wig's claim. Restored
    // from the state payload on open so a resumed session shows what
    // was used rather than snapping back to 1.
    @state() private _sendTimes = 1;
    @state() private _receiverIds = new Set<string>();
    @state() private _view: "session" | "sign" | "ledger" = "session";
    @state() private _confirmDiscard = false;
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _handle = "";
    @state() private _github = "";
    @state() private _note = "";
    @state() private _kind = "";
    // Replace (Smart Perm). One strip at a time: the row whose strip
    // is open, and everything that strip holds.
    @state() private _replaceRow: number | null = null;
    /** Ditto values tuned but not yet proven, row index -> count.
     *
     * Session state, mirrored server-side so TEST transmits the staged
     * recipe. A tuned ditto cannot enter the wig without a WORKED
     * against it, so this is the whole staging story: thumb-up commits,
     * thumb-down leaves it staged for another try, closing discards. */
    @state() private _stagedDittos = new Map<number, number>();
    /** Which chip is currently expanded into its stepper.
     *
     * Exactly one at a time, and it closes on its own glyph, on any
     * click that lands outside it, and on Escape. The FT5 build opened
     * chips and never closed them (owner bench 2026-08-02): a stepper
     * left open on every row it had ever touched, with no way back to
     * the compact reading. */
    @state() private _openChip: string | null = null;
    @state() private _applyBusy = false;
    /** Rows whose TEST is currently showing its result instead of its
     * name, and the timers that will settle them back. */
    @state() private _flash = new Map<number, "sent" | "heard">();
    private _flashTimers = new Map<number, number>();
    @state() private _replaceText = "";
    @state() private _replaceQuality: CaptureQuality | null = null;
    @state() private _replaceBusy = false;
    // REPLACE STARTS FRESH (owner ruling 2026-08-01): a replace clears
    // the pin, the strip shows what the NEW capture decoded as, and the
    // fitter chooses again. The code and the flag are written in one
    // hash roll, so the row never exists in a state where the bytes and
    // the send decision disagree.
    @state() private _replaceBypass = false;
    @state() private _replaceError: string | null = null;
    @state() private _listening = false;
    @state() private _listenMissed = false;
    // Which row's chip is armed for revert (two-click confirm).
    @state() private _revertArmed: number | null = null;
    // The post-replace line: what changed, and what it cost.
    @state() private _notice: string | null = null;
    private _unlisten: (() => Promise<void>) | null = null;
    private _scrollToKey: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
        // Click-away for the tune steppers. Bound on the host rather
        // than the document: a stepper is a transient reading aid, not
        // a modal, so it should not outlive a click anywhere in the
        // dialog -- and a document listener would fight the overlay.
        this.addEventListener("click", this._onHostClick, true);
        this.addEventListener("keydown", this._onHostKey);
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this.removeEventListener("click", this._onHostClick, true);
        this.removeEventListener("keydown", this._onHostKey);
        this._clearFlashTimers();
        // Closing the dialog IS cancelling the listen window.
        void this._stopListening();
    }

    /** Any click that did not land inside the open stepper closes it.
     * Capture phase, so the stepper's own buttons still fire first via
     * the composed path check rather than being swallowed. */
    private _onHostClick = (e: Event): void => {
        if (this._openChip === null) return;
        const path = e.composedPath();
        const inside = path.some(
            (node) =>
                node instanceof HTMLElement &&
                (node.classList?.contains("tstep") ||
                    node.classList?.contains("tchip")),
        );
        if (!inside) this._openChip = null;
    };

    /** Escape closes the stepper before it closes the dialog. */
    private _onHostKey = (e: KeyboardEvent): void => {
        if (e.key === "Escape" && this._openChip !== null) {
            e.stopPropagation();
            this._openChip = null;
        }
    };

    private async _load(): Promise<void> {
        try {
            const [fit, receivers] = await Promise.all([
                this.api.fittingState(this.wig.filename),
                this.api.listReceivers().catch(() => []),
            ]);
            this._receiverIds = new Set(receivers.map((r) => r.entity_id));
            this._fit = fit;
            this._handle = fit.username;
            this._kind = fit.kind ?? "";
            if (fit.send_times)
                this._sendTimes = Math.max(
                    1,
                    Math.min(fit.send_times, 10),
                );
            // Prefill the GitHub handle from the user's previous
            // fitting on this install ("remembered per install").
            const mine = fit.ledger.find(
                (row) =>
                    row.github &&
                    row.handle.toLowerCase() ===
                        fit.username.toLowerCase(),
            );
            // Normalized on prefill: a previous fitting may carry an
            // imported wig's dirty value (URL, @-prefixed), and a URL
            // sitting behind the field's decorative @ reads as a bug.
            // The backend cleans again on record either way.
            this._github = _cleanGithubHandle(mine?.github ?? "");
            const verdicts = _verdictsOf(fit);
            this._verdicts = verdicts;
            // Untested first, on open only; stable within each half.
            // Matrix sessions keep checklist order instead (mockup
            // CC1): the sectioned walk start / modes / fan / swing /
            // temp / wrap / changed IS the session's shape, and
            // resorting by verdict would scatter rows across headers.
            const idx = fit.signals.map((_, i) => i);
            this._order = fit.matrix
                ? idx
                : [
                      ...idx.filter((i) => !verdicts.has(i)),
                      ...idx.filter((i) => verdicts.has(i)),
                  ];
            const emitters = this._emitters();
            if (emitters.length === 1) this._emitter = emitters[0].id;
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
    }

    private _emitters(): { id: string; name: string }[] {
        const states = (this.hass?.states ?? {}) as Record<string, any>;
        const out: { id: string; name: string }[] = [];
        for (const [id, st] of Object.entries(states)) {
            if (
                id.startsWith("infrared.") &&
                !this._receiverIds.has(id) &&
                !st.attributes?.hair_observer
            ) {
                out.push({
                    id,
                    name: st.attributes?.friendly_name ?? id,
                });
            }
        }
        return out;
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _onSendTimesInput(e: Event): void {
        const raw = Number((e.target as HTMLInputElement).value);
        if (!Number.isFinite(raw)) return;
        this._sendTimes = Math.max(1, Math.min(Math.round(raw), 10));
    }

    private async _send(i: number): Promise<void> {
        if (!this._emitter || !this._fit) return;
        const facts = this._facts.get(i) ?? {
            sent: 0,
            heard: false,
            busy: false,
        };
        if (facts.busy) return;
        this._facts = new Map(this._facts).set(i, {
            ...facts,
            busy: true,
        });
        try {
            const res = await this.api.fittingSend(
                this.wig.filename,
                i,
                this._emitter,
                this._sendTimes,
            );
            this._facts = new Map(this._facts).set(i, {
                sent: facts.sent + 1,
                heard: facts.heard || res.heard,
                busy: false,
            });
            // THIS send's result, not the row's history: the button is
            // reporting the press that just happened, so a row heard
            // once and missed twice must not keep claiming HEARD.
            this._flashResult(i, res.heard);
        } catch (err: any) {
            this._facts = new Map(this._facts).set(i, {
                ...facts,
                busy: false,
            });
            this._error = err?.message ?? String(err);
        }
    }

    private async _mark(
        i: number,
        verdict: "worked" | "failed",
    ): Promise<void> {
        const current = this._verdicts.get(i);
        const next = current === verdict ? "untested" : verdict;
        const verdicts = new Map(this._verdicts);
        if (next === "untested") verdicts.delete(i);
        else verdicts.set(i, next);
        this._verdicts = verdicts;
        try {
            await this.api.fittingMark(this.wig.filename, i, next);
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
    }

    // -- Replace (Smart Perm) ------------------------------------------

    /** Refetch state after a replace without reshuffling the session.
     * The untested-first sort is an ON OPEN behaviour; re-running it
     * mid-session would slide rows out from under the fitter's cursor
     * the moment they repaired one. Rows appended by the replace (a
     * Changed Codes cell) join at the end, where they render. */
    private async _refresh(): Promise<void> {
        const fit = await this.api.fittingState(this.wig.filename);
        this._fit = fit;
        this._verdicts = _verdictsOf(fit);
        if (fit.rows.length !== this._order.length) {
            const known = new Set(this._order);
            this._order = [
                ...this._order.filter((i) => i < fit.rows.length),
                ...fit.rows
                    .map((_, i) => i)
                    .filter((i) => !known.has(i)),
            ];
        }
    }

    private async _stopListening(): Promise<void> {
        const unlisten = this._unlisten;
        this._unlisten = null;
        this._listening = false;
        if (unlisten) {
            try {
                await unlisten();
            } catch {
                // The connection went away; the window is gone with it.
            }
        }
    }

    private async _openReplace(i: number): Promise<void> {
        if (this._replaceRow === i) {
            await this._closeReplace();
            return;
        }
        await this._stopListening();
        // Any other action disarms a chip left half-pressed.
        this._revertArmed = null;
        this._replaceRow = i;
        this._replaceText = "";
        this._replaceQuality = null;
        this._replaceBypass = false;
        this._replaceError = null;
        this._listenMissed = false;
        this._notice = null;
    }

    private async _closeReplace(): Promise<void> {
        await this._stopListening();
        this._replaceRow = null;
        this._replaceText = "";
        this._replaceQuality = null;
        this._replaceBypass = false;
        this._replaceError = null;
        this._listenMissed = false;
    }

    private _onReplaceInput(e: Event): void {
        this._replaceText = (e.target as HTMLTextAreaElement).value;
        // Hand-edited text is no longer the capture the quality line
        // described.
        this._replaceQuality = null;
        this._listenMissed = false;
    }

    private async _listen(): Promise<void> {
        if (this._listening) {
            await this._stopListening();
            return;
        }
        this._replaceError = null;
        this._listenMissed = false;
        this._listening = true;
        try {
            this._unlisten = await this.api.fittingListen(
                (event: FittingListenEvent) => {
                    if (event.type === "fitting_capture") {
                        this._replaceText = event.pronto;
                        this._replaceQuality = {
                            decoded: event.decoded,
                            protocol: event.protocol,
                            receiver: event.receiver,
                        };
                        void this._stopListening();
                    } else {
                        this._listenMissed = true;
                        void this._stopListening();
                    }
                },
            );
        } catch (err: any) {
            this._listening = false;
            this._replaceError = err?.message ?? String(err);
        }
    }

    private async _confirmReplace(): Promise<void> {
        const i = this._replaceRow;
        if (i === null || !this._replaceText.trim()) return;
        this._replaceBusy = true;
        this._replaceError = null;
        const source = this._replaceQuality ? "captured" : "pasted";
        try {
            const result = await this.api.fittingReplace(
                this.wig.filename,
                i,
                this._replaceText.trim(),
                source,
                this._replaceBypass,
            );
            await this._closeReplace();
            await this._refresh();
            this._notice =
                result.carried > 0
                    ? t("fitting.replaced_notice", {
                          count: String(result.carried),
                      })
                    : t("fitting.replaced_notice_none");
            // The closet's check marks and coverage moved with the hash.
            this._recordedRefresh();
        } catch (err: any) {
            this._replaceError = err?.message ?? String(err);
        }
        this._replaceBusy = false;
    }

    /** A ledger row's failed count NAVIGATES (owner ruling
     * 2026-07-30): back to the session, scrolled to the first row that
     * fitting failed, with Replace one click away. No replace from the
     * ledger itself -- the send-and-judge proof loop stays attached. */
    private _navigateToFailed(keys: string[]): void {
        this._scrollToKey = keys[0] ?? null;
        this._view = "session";
    }

    protected updated(): void {
        if (!this._scrollToKey || this._view !== "session") return;
        const key = this._scrollToKey;
        this._scrollToKey = null;
        const index = this._fit?.rows.findIndex((r) => r.key === key) ?? -1;
        if (index < 0) return;
        this.renderRoot
            ?.querySelector(`[data-row-index="${index}"]`)
            ?.scrollIntoView({ block: "center" });
    }

    private async _discard(): Promise<void> {
        this._busy = true;
        try {
            await this.api.fittingDiscard(this.wig.filename);
        } catch {
            // No draft to discard is fine -- nothing was marked yet.
        }
        this._busy = false;
        this._recordedRefresh();
        this._close();
    }

    private async _record(): Promise<void> {
        this._busy = true;
        this._error = null;
        try {
            const result = await this.api.fittingFinish(
                this.wig.filename,
                {
                    ...(this._handle.trim()
                        ? { handle: this._handle.trim() }
                        : {}),
                    ...(this._github.trim()
                        ? { github: this._github.trim() }
                        : {}),
                    ...(this._note.trim()
                        ? { note: this._note.trim() }
                        : {}),
                    ...(this._kind.trim() && !this._fit?.kind
                        ? { kind: this._kind.trim() }
                        : {}),
                },
            );
            this.dispatchEvent(
                new CustomEvent("recorded", {
                    detail: result,
                    bubbles: true,
                    composed: true,
                }),
            );
            this._close();
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
        this._busy = false;
    }

    private _recordedRefresh(): void {
        this.dispatchEvent(
            new CustomEvent("recorded", {
                detail: null,
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** Progress over the CHECKLIST, and only the checklist.
     *
     * Comb suspects became judgeable on 2026-08-02, which put verdicts
     * in the map for rows that are not part of the count. They have to
     * be filtered here or the two halves of the fraction come from
     * different populations: total is signals.length, which the backend
     * already builds with advisory rows excluded, so counting their
     * verdicts gave "35 of 31 tested" and fired PERFECT FIT early.
     *
     * The exclusion itself is older and load-bearing. Combing stamps a
     * receipt without rolling the content hash, so if suspects counted,
     * one person running a comb would retroactively demote every
     * complete fitting in the ledger -- other people's included --
     * with no code having changed anywhere. Replacing a suspect is what
     * legitimately promotes it: that rolls the hash and makes it a
     * Changed Codes row, which does count.
     */
    private get _counts() {
        let worked = 0;
        let failed = 0;
        for (const [i, v] of this._verdicts) {
            if (this._fit?.rows[i]?.advisory) continue;
            if (v === "worked") worked += 1;
            else failed += 1;
        }
        const total = this._fit?.signals.length ?? 0;
        return {
            worked,
            failed,
            tested: worked + failed,
            total,
            perfect: total > 0 && worked === total,
        };
    }

    render() {
        return html`
            <div class="overlay" @click=${this._close}>
                <div
                    class="dialog fit-dialog"
                    @click=${(e: Event) => e.stopPropagation()}
                >
                    ${this._view === "sign"
                        ? this._renderSign()
                        : this._view === "ledger"
                          ? this._renderLedger()
                          : this._renderSession()}
                </div>
            </div>
        `;
    }

    /** The user's own ledger row (valid hash), and everyone else's. */
    private _ledgerSplit() {
        const me = (this._fit?.username ?? "").trim().toLowerCase();
        const rows = this._fit?.ledger ?? [];
        const mine = rows.find(
            (r) => r.valid && r.handle.trim().toLowerCase() === me,
        );
        const others = rows.filter((r) => r !== mine);
        return { mine, others };
    }

    private _chipDate(date: string | null): string {
        if (!date) return "";
        const parsed = new Date(`${date}T00:00:00`);
        if (Number.isNaN(parsed.getTime())) return date;
        return parsed.toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
        });
    }

    /** Fitted-status chips (owner rulings 2026-07-27): your fitting
     * leads, everyone else folds into one quiet chip, and both open
     * the ledger -- which is where the ledger lives. Unfitted wigs
     * render nothing, so first-time fitting looks unchanged. */
    private _renderFitChips() {
        const { mine, others } = this._ledgerSplit();
        if (!mine && others.length === 0) return nothing;
        const total = this._fit?.signals.length ?? 0;
        return html`
            <div class="fitrow">
                ${mine
                    ? html`<button
                          class="fstat you ${mine.complete
                              ? ""
                              : "partial"}"
                          @click=${() => (this._view = "ledger")}
                      >
                          <span class="tick">&check;</span>
                          ${mine.complete
                              ? t("fitting.chip_you", {
                                    date: this._chipDate(mine.date),
                                })
                              : t("fitting.chip_you_partial", {
                                    confirmed: String(mine.confirmed),
                                    total: String(total),
                                })}
                      </button>`
                    : nothing}
                ${others.length
                    ? html`<button
                          class="fstat others"
                          @click=${() => (this._view = "ledger")}
                      >
                          ${tp("fitting.chip_others", others.length)}
                      </button>`
                    : nothing}
            </div>
        `;
    }

    private _renderSession() {
        const c = this._counts;
        return html`
            <h3 class="heading">${this.wig.name}</h3>
            ${this._fit?.matrix
                ? html`<div class="matrix-claim">
                      ${t("fitting.matrix_claim", {
                          sends: String(this._fit.rows.length),
                          cells: String(
                              this.wig.matrix?.cells ??
                                  this._fit.rows.length,
                          ),
                      })}
                  </div>`
                : nothing}
            <div class="sess-head">${t("fitting.header")}</div>
            ${this._renderFitChips()}
            ${this._error
                ? html`<div class="err">${this._error}</div>`
                : nothing}
            ${this._notice
                ? html`<div class="notice">${this._notice}</div>`
                : this._fit?.carried
                  ? html`<div class="notice">
                        ${t("fitting.carried_notice")}
                    </div>`
                  : nothing}
            <div class="field">
                <label>${t("fitting.emitter")}</label>
                <select
                    .value=${this._emitter}
                    @change=${(e: Event) =>
                        (this._emitter = (
                            e.target as HTMLSelectElement
                        ).value)}
                >
                    <option value="" ?selected=${!this._emitter}>
                        ${t("fitting.pick_emitter")}
                    </option>
                    ${this._emitters().map(
                        (em) => html`<option
                            value=${em.id}
                            ?selected=${em.id === this._emitter}
                        >
                            ${em.name}
                        </option>`,
                    )}
                </select>
            </div>
            <div class="field">
                <label>${t("fitting.send_times")}</label>
                <input
                    class="send-count"
                    type="number"
                    min="1"
                    max="10"
                    .value=${String(this._sendTimes)}
                    @input=${this._onSendTimesInput}
                />
                <button
                    class="apply-btn"
                    ?disabled=${this._applyBusy || !!this._fit?.matrix}
                    @click=${() => void this._applySends()}
                >
                    ${t("fitting.apply")}
                </button>
                <div class="hint">
                    ${t("fitting.send_times_hint")}
                    <span class="hint-apply">${t("fitting.apply_hint")}</span>
                </div>
            </div>
            <div class="sig-list">
                ${this._fit
                    ? this._fit.matrix
                        ? this._renderMatrixList()
                        : this._order.map((i) => this._renderRow(i))
                    : html`<div class="loading">
                          ${t("common.loading_plain")}
                      </div>`}
            </div>
            <div class="progress-line ${c.perfect ? "perfect" : ""}">
                <span>
                    ${c.perfect
                        ? t("fitting.all_worked", {
                              count: String(c.total),
                          })
                        : html`${t("fitting.progress", {
                              tested: String(c.tested),
                              total: String(c.total),
                          })}${c.failed > 0
                              ? html` &middot;
                                    <span class="fail-note"
                                        >${tp(
                                            "fitting.failed",
                                            c.failed,
                                        )}</span
                                    >`
                              : nothing}`}
                </span>
                <span class="bar"
                    ><i
                        style="width:${c.total
                            ? Math.round((c.tested / c.total) * 100)
                            : 0}%"
                    ></i
                ></span>
            </div>
            <div class="dialog-actions fit-actions">
                ${this._confirmDiscard
                    ? html`
                          <span class="discard-q"
                              >${t("fitting.discard_confirm")}${this
                                  ._fit?.pending_replaces
                                  ? html` <span class="discard-revert"
                                        >${tp(
                                            "fitting.discard_reverts",
                                            this._fit.pending_replaces,
                                        )}</span
                                    >`
                                  : nothing}</span
                          >
                          <span class="spacer"></span>
                          <button
                              class="action-btn cancel-btn"
                              @click=${() =>
                                  (this._confirmDiscard = false)}
                          >
                              ${t("fitting.keep")}
                          </button>
                          <button
                              class="action-btn discard-yes"
                              ?disabled=${this._busy}
                              @click=${this._discard}
                          >
                              ${t("fitting.discard")}
                          </button>
                      `
                    : html`
                          <button
                              class="action-btn cancel-btn"
                              @click=${this._close}
                          >
                              ${t("common.close")}
                          </button>
                          <span class="spacer"></span>
                          <button
                              class="action-btn discard-btn"
                              ?disabled=${c.tested === 0 &&
                              !this._fit?.pending_replaces}
                              @click=${() =>
                                  (this._confirmDiscard = true)}
                          >
                              ${t("fitting.discard")}
                          </button>
                          <button
                              class="action-btn finish-btn ${c.perfect
                                  ? "green"
                                  : ""}"
                              ?disabled=${c.tested === 0}
                              @click=${() => (this._view = "sign")}
                          >
                              ${t("fitting.finish")}
                          </button>
                      `}
            </div>
            <div class="hint">${t("fitting.close_hint")}</div>
        `;
    }

    private _renderRow(i: number) {
        const alias = this._fit!.signals[i];
        return html`
            <div class="sig-row" data-row-index=${i}>
                <span class="sig-alias" title=${alias}
                    >${alias}${this._renderChip(i)}</span
                >
                ${this._renderTuneChips(i)} ${this._renderRowChip(i)}
                ${this._renderRowControls(i)}
            </div>
            ${this._renderStagedNotice(i)}
            ${this._renderReplaceStrip(i)}
        `;
    }

    /** The provenance chip: this row's code came off a real remote, or
     * out of somebody's clipboard, rather than out of the file as
     * shipped.
     *
     * When the wig still has the row's earlier code on record the chip
     * becomes the way back: hovering offers REVERT, and it takes two
     * clicks, because one stray click would throw away a capture the
     * fitter may have walked across the house for. A chip that arrived
     * inside a shared wig has nothing on record and stays a label. */
    /** The row's chip, sitting inside the name rather than after it: a
     * chip placed after a flex:1 label gets pushed against the buttons and
     * reads as a fourth control (owner bench 2026-07-31).
     *
     * Neutral pill in every state; the MARK carries the meaning. An amber
     * warning glyph for a comb suspect, which is a doubt rather than a
     * claim; a blue tick for a replaced code, captured or pasted. When an
     * earlier code is on record the chip is also the way back: hovering
     * swaps the tick for an undo arrow and the label for "revert", because
     * leaving a tick in place while the word says revert would assert the
     * state and offer the action in the same breath.
     */
    private _renderChip(i: number) {
        const row = this._fit?.rows[i];
        const marker = row?.provenance;
        // A row the comb deliberately did not judge. Its own glyph and
        // its own grey: amber means doubt, and a pinned code is not in
        // doubt, somebody decided. Without this the comb recorded the
        // skip in the report and the receipt and NO surface said so, so
        // a clean-looking wig implied a check that never ran.
        if (row?.bypass_protocol && !marker) {
            return html`<span
                class="prov-chip"
                title=${t("fitting.chip_comb_skipped_title")}
                ><span class="cmark comb"
                    ><svg viewBox="0 0 512 512">
                        <path d=${ICON_COMB}></path></svg></span
                >${t("fitting.chip_comb_skipped")}</span
            >`;
        }
        if (row?.advisory && !marker) {
            return html`<span class="prov-chip"
                ><span class="cmark warn">&#9888;</span
                >${t("fitting.chip_suspect")}</span
            >`;
        }
        if (!marker) return nothing;
        const label = t(
            marker.replaced === "captured"
                ? "fitting.chip_replaced_captured"
                : "fitting.chip_replaced_pasted",
        );
        if (!row?.revertible) {
            return html`<span class="prov-chip" title=${marker.date ?? ""}
                ><span class="cmark tick">&check;</span>${label}</span
            >`;
        }
        const armed = this._revertArmed === i;
        // The alternate label overlays rather than replaces, so the chip
        // keeps its width and the row does not shift under the pointer.
        return html`<button
            class="prov-chip revertible ${armed ? "armed" : ""}"
            title=${t("fitting.revert_title")}
            @click=${() => void this._onChipClick(i)}
        >
            <span class="chip-face"
                ><span class="cmark tick">&check;</span>${label}</span
            >
            <span class="chip-alt"
                ><span class="cmark undo">&#8634;</span
                >${armed
                    ? t("fitting.revert_confirm")
                    : t("fitting.revert")}</span
            >
        </button>`;
    }

    private async _onChipClick(i: number): Promise<void> {
        if (this._revertArmed !== i) {
            this._revertArmed = i;
            return;
        }
        this._revertArmed = null;
        this._replaceBusy = true;
        this._error = null;
        try {
            const result = await this.api.fittingRevert(
                this.wig.filename,
                i,
            );
            await this._closeReplace();
            await this._refresh();
            this._notice = t("fitting.reverted_notice", {
                count: String(result.carried),
            });
            this._recordedRefresh();
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
        this._replaceBusy = false;
    }

    /** The row anatomy every session row shares (Cold Cuts): machine
     * facts, SEND, WORKED, DID NOT. Extracted verbatim from the signal
     * row so the matrix rows carry the identical controls -- only the
     * label anatomy differs between the two wig kinds. */
    /** The row's protocol chip: same pill as the Sniffer and Clipper,
     * but read-only. Toggling here would change a code from inside an
     * attestation, which would roll the content hash mid-fitting. The
     * interactive copy lives on the device command and in REPLACE. */
    private _renderRowChip(i: number) {
        const row = this._fit?.rows[i];
        return html`<span class="chip-col"
            ><ir-protocol-chip
                .protocol=${row?.protocol ?? null}
                .bypass=${!!row?.bypass_protocol}
            ></ir-protocol-chip
        ></span>`;
    }


    /** The transmit-recipe chips, left of the protocol pill.
     *
     * Two families that look alike and behave differently, which is the
     * whole design: the SEND chip (gold) edits a ride-along and costs
     * nothing, the DITTO chip (blue) stages a change to what the wig
     * claims and can only be committed by a thumb-up. Colour and glyph
     * come from the catalog rows so the marks read identically across
     * the UI; grey when the value is at its default.
     *
     * Both sit in fixed slots. A bypassed row keeps an EMPTY ditto slot
     * rather than collapsing it, so the gating reads as an aligned gap
     * instead of a jog down a fourteen-row checklist.
     */
    /** APPLY: push the typed number onto every row's send chip.
     *
     * A real file edit, and harmless now that sends are unpinned --
     * which is exactly what makes the gesture possible. Bulk-setting a
     * device floor (the candle at 3, across the board) should not mean
     * clicking twenty steppers, and before the recipe break it would
     * have meant twenty hash rolls.
     *
     * Without applying, the control keeps its v0.9.0 role untouched:
     * contributes at transmit, recorded as send_times_used, monotonic.
     */
    private async _applySends(): Promise<void> {
        if (this._applyBusy || this._fit?.matrix) return;
        this._applyBusy = true;
        this._error = null;
        try {
            const result = await this.api.fittingSetSends(
                this.wig.filename, null, this._sendTimes,
            );
            if (result.success) {
                this._notice = t("fitting.applied_notice", {
                    count: String(result.written),
                });
                await this._refresh();
            }
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
        this._applyBusy = false;
    }

    private _renderTuneChips(i: number) {
        const row = this._fit?.rows[i];
        if (!row || this._fit?.matrix) return nothing;
        const sends = row.send_count ?? 1;
        const staged = this._stagedDittos.get(i);
        const dittos = staged ?? row.ditto_count ?? 0;
        // Dittos are the NEC repeat frame and nothing else (owner
        // ruling 2026-08-02, measured against infrared-protocols): NEC
        // appends a 4-entry ditto, Samsung32 and RC-5 duplicate the
        // whole frame -- which is send_count wearing the wrong name,
        // inside the hash -- and Sharp and Sony ignore repeat_count
        // outright. Offering the knob anywhere else either lies or
        // does nothing. A row pinned to raw is out too: the repeats
        // already live in the bytes.
        const dittoable = isDittoable(row.protocol, row.bypass_protocol);
        return html`<span class="tune-cell"
                >${this._renderTuneChip(i, "sends", sends, 1)}</span
            ><span class="tune-cell"
                >${dittoable
                    ? this._renderTuneChip(i, "dittos", dittos, 0)
                    : nothing}</span
            >`;
    }

    private _renderTuneChip(
        i: number,
        kind: "sends" | "dittos",
        value: number,
        base: number,
    ) {
        const id = `${kind}:${i}`;
        const open = this._openChip === id;
        const at = value <= base;
        const icon = kind === "sends" ? ICON_REPEAT : ICON_DITTO;
        const hint =
            kind === "dittos" ? this._fit?.rows[i]?.observed_repeat_count : null;
        if (!open) {
            return html`<button
                class="tchip ${kind} ${at ? "at-default" : ""}"
                title=${t(
                    kind === "sends"
                        ? "fitting.chip_sends_title"
                        : "fitting.chip_dittos_title",
                )}
                @click=${() => (this._openChip = id)}
            >
                <ha-svg-icon .path=${icon}></ha-svg-icon>${value}
            </button>`;
        }
        // Open: bare, no pill (owner ruling 2026-08-02). The chip wore a
        // tinted capsule to say "this is one control"; expanded, the
        // stepper is already unmistakably one control, and the capsule
        // only made a row look permanently edited.
        return html`<span class="tstep ${kind}">
            <button
                class="tstep-btn"
                aria-label=${t("fitting.chip_less")}
                @click=${() => void this._bump(i, kind, value - 1)}
            >
                &minus;
            </button>
            <button
                class="tstep-val"
                title=${t("fitting.chip_close")}
                @click=${() => (this._openChip = null)}
            >
                ${value}
            </button>
            <button
                class="tstep-btn"
                aria-label=${t("fitting.chip_more")}
                @click=${() => void this._bump(i, kind, value + 1)}
            >
                +
            </button>
            ${hint
                ? html`<span class="tstep-hint"
                      >${t("fitting.chip_observed", {
                          count: String(hint),
                      })}</span
                  >`
                : nothing}
        </span>`;
    }

    /** A stepper press. Sends write straight through (they are not
     * hashed); dittos only stage, because a value nothing has proven
     * must not reach the wig. */
    private async _bump(
        i: number,
        kind: "sends" | "dittos",
        next: number,
    ): Promise<void> {
        if (kind === "sends") {
            const value = Math.max(1, Math.min(next, 10));
            const row = this._fit?.rows[i];
            if (!row || value === (row.send_count ?? 1)) return;
            row.send_count = value;
            this.requestUpdate();
            try {
                await this.api.fittingSetSends(this.wig.filename, i, value);
            } catch (err: any) {
                this._error = err?.message ?? String(err);
            }
            return;
        }
        const value = Math.max(0, Math.min(next, 20));
        const staged = new Map(this._stagedDittos);
        const stored = this._fit?.rows[i]?.ditto_count ?? 0;
        if (value === stored) staged.delete(i);
        else staged.set(i, value);
        this._stagedDittos = staged;
        try {
            await this.api.fittingStageDitto(
                this.wig.filename,
                i,
                value === stored ? null : value,
            );
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
    }

    /** Thumb-up. When a staged ditto is riding this row, commit it
     * FIRST -- one hash roll, provenance, draft re-bind, carry-forward
     * -- and only then record the verdict, so the wig never carries a
     * tuned value nothing proved. */
    private async _onWorked(i: number): Promise<void> {
        const staged = this._stagedDittos.get(i);
        if (staged !== undefined) {
            try {
                const result = await this.api.fittingTune(
                    this.wig.filename, i, staged,
                );
                if (!result.success) {
                    this._error = t("fitting.tune_failed");
                    return;
                }
                const next = new Map(this._stagedDittos);
                next.delete(i);
                this._stagedDittos = next;
                this._notice = t("fitting.tuned_notice", {
                    count: String(staged),
                });
                await this._refresh();
            } catch (err: any) {
                this._error = err?.message ?? String(err);
                return;
            }
        }
        await this._mark(i, "worked");
    }

    /** TEST, which reports its own result.
     *
     * The result used to be a separate run of text: first inline in the
     * row, where its variable width shoved every control after it, then
     * on a line below, where it read as orphaned from the button that
     * produced it. It now lives ON that button (owner design
     * 2026-08-02): press it, it says SENT, or SENT . HEARD when a
     * receiver caught the transmission, holds for five seconds so you
     * can look at the device and back, and collapses to TEST again. How
     * many times the row has been tested rides in the corner dot, which
     * is grey because it is a tally rather than a flag.
     *
     * The three labels are STACKED in one grid cell with only the
     * active one visible, rather than swapped in and out. The button
     * therefore sizes to its widest state in whatever language it is
     * reading, and cannot change width when the label changes -- which
     * would have reintroduced the staggering this whole pass removed.
     * Same trick the provenance chip uses for its revert label.
     */
    private _renderTestButton(i: number) {
        const facts = this._facts.get(i);
        const flash = this._flash.get(i);
        return html`<button
            class="vbtn test-btn ${flash ? `flash ${flash}` : ""}"
            ?disabled=${!this._emitter || facts?.busy}
            title=${this._emitter ? "" : t("fitting.pick_emitter")}
            @click=${() => void this._send(i)}
        >
            <span class="tb-stack">
                <span class="tb-lay ${flash ? "" : "on"}"
                    >${t("cmdrow.test")}</span
                >
                <span class="tb-lay ${flash === "sent" ? "on" : ""}"
                    >${t("fitting.sent")}</span
                >
                <span class="tb-lay ${flash === "heard" ? "on" : ""}"
                    >${t("fitting.sent")} &middot;
                    ${t("fitting.heard")}</span
                >
            </span>
            <ir-count-dot
                color="grey"
                .count=${facts?.sent ?? 0}
            ></ir-count-dot>
        </button>`;
    }

    /** Show a send's result on its button, then let it settle back.
     * Re-pressing restarts the hold rather than stacking timers. */
    private _flashResult(i: number, heard: boolean): void {
        const existing = this._flashTimers.get(i);
        if (existing !== undefined) clearTimeout(existing);
        this._flash = new Map(this._flash).set(i, heard ? "heard" : "sent");
        const timer = window.setTimeout(() => {
            const next = new Map(this._flash);
            next.delete(i);
            this._flash = next;
            this._flashTimers.delete(i);
        }, FLASH_HOLD_MS);
        this._flashTimers.set(i, timer);
    }

    private _clearFlashTimers(): void {
        for (const timer of this._flashTimers.values()) {
            clearTimeout(timer);
        }
        this._flashTimers.clear();
    }

    /** The staged-but-unproven notice. The chip itself stays plain
     * (owner ruling FT3: no outline, no tint); the status lives here. */
    private _renderStagedNotice(i: number) {
        const staged = this._stagedDittos.get(i);
        if (staged === undefined) return nothing;
        return html`<div class="qline staged">
            ${t("fitting.ditto_staged", { count: String(staged) })}
        </div>`;
    }

    private _renderRowControls(i: number) {
        const verdict = this._verdicts.get(i);
        // A comb suspect is judged like anything else now (owner
        // ruling 2026-08-02): a matrix checklist samples 31 of 288
        // cells, so the other 48 the comb flagged were rows you could
        // send and repair but never tick, with no way to track which
        // ones you had already been through. What has NOT changed is
        // the arithmetic -- see _counts. Combing stamps a receipt
        // without rolling the content hash, so a suspect that counted
        // toward completeness would let one person's comb retroactively
        // demote somebody else's signed PERFECT FIT with no code having
        // changed anywhere.
        return html`<span class="row-tail"
            >${this._renderTestButton(i)}
            <button
                class="thumb up ${verdict === "worked" ? "on" : ""}"
                title=${t("fitting.worked")}
                aria-label=${t("fitting.worked")}
                @click=${() => void this._onWorked(i)}
            >
                <ha-svg-icon
                    .path=${verdict === "worked"
                        ? ICON_THUMB_UP_SOLID
                        : ICON_THUMB_UP_OUTLINE}
                ></ha-svg-icon>
            </button>
            <button
                class="thumb down ${verdict === "failed" ? "on" : ""}"
                title=${t("fitting.did_not")}
                aria-label=${t("fitting.did_not")}
                @click=${() => void this._mark(i, "failed")}
            >
                <ha-svg-icon
                    .path=${verdict === "failed"
                        ? ICON_THUMB_DOWN_SOLID
                        : ICON_THUMB_DOWN_OUTLINE}
                ></ha-svg-icon>
            </button>
            <button
                class="vbtn replace-btn ${this._replaceRow === i
                    ? "open"
                    : ""}"
                title=${t("fitting.replace_title")}
                @click=${() => void this._openReplace(i)}
            >
                ${t("fitting.replace")}
            </button></span
        >`;
    }

    /** What to set the physical remote to before pressing it, for a
     * matrix row. The whole reason a captured cell is the strongest
     * repair in the pipeline: the remote's own display IS the state,
     * so the capture is the cell, whole and correct. */
    private _rowStateInstruction(i: number): string {
        const row = this._fit?.rows[i];
        if (!row || !this._fit?.matrix) return "";
        if (row.section === "start") return t("fitting.row_on");
        if (row.section === "wrap") return t("fitting.row_off");
        const parts: string[] = [];
        if (row.mode) parts.push(row.mode);
        if (row.fan) parts.push(t("fitting.ctx_fan", { fan: row.fan }));
        if (row.swing)
            parts.push(t("fitting.ctx_swing", { swing: row.swing }));
        if (row.temp != null)
            parts.push(`${this._displayTemp(row.temp)}°`);
        return parts.join(" · ");
    }

    private _renderQualityLine(i: number) {
        if (this._listening) {
            const state = this._rowStateInstruction(i);
            return html`<div class="qline listen">
                <span class="pulse"></span>
                <span
                    >${state
                        ? t("fitting.listening_state", { state })
                        : t("fitting.listening")}</span
                >
            </div>`;
        }
        if (this._listenMissed) {
            return html`<div class="qline warn">
                ${t("fitting.listen_missed")}
            </div>`;
        }
        const quality = this._replaceQuality;
        if (!quality) return nothing;
        if (!quality.decoded) {
            // Warn and allow (RULED): a rough capture is the fitter's
            // call, and the send-and-judge loop is right there to
            // settle it.
            return html`<div class="qline warn">
                ${t("fitting.capture_rough")}
            </div>`;
        }
        // The protocol name rides OUTSIDE the sentence: it is a proper
        // noun ("NEC", "SONY15") and it can legitimately be absent, so
        // interpolating it would leave a hole in the translation.
        return html`<div class="qline good">
            &check;
            <span
                >${quality.receiver
                    ? t("fitting.capture_clean_via", {
                          receiver: this._receiverName(quality.receiver),
                      })
                    : t("fitting.capture_clean")}${quality.protocol
                    ? ` · ${quality.protocol}`
                    : ""}</span
            >
        </div>`;
    }

    private _receiverName(entityId: string): string {
        const st = this.hass?.states?.[entityId];
        return st?.attributes?.friendly_name ?? entityId;
    }

    /** The inline strip (mockup RP2): paste a Pronto, or capture one
     * from the real remote. Nothing changes until Replace is pressed. */
    private _renderReplaceStrip(i: number) {
        if (this._replaceRow !== i) return nothing;
        const rough = !!this._replaceQuality && !this._replaceQuality.decoded;
        const ready = !!this._replaceText.trim() && !this._replaceBusy;
        return html`
            <div class="repstrip">
                <div class="titleline">
                    <span class="t">${t("fitting.replace_heading")}</span>
                    <span class="why">${t("fitting.replace_why")}</span>
                </div>
                <textarea
                    class="prontobox"
                    spellcheck="false"
                    placeholder="0000 006d 0022 0002 ..."
                    .value=${this._replaceText}
                    @input=${this._onReplaceInput}
                ></textarea>
                ${this._renderQualityLine(i)}
                ${this._replaceError
                    ? html`<div class="qline bad">
                          ${this._replaceError}
                      </div>`
                    : nothing}
                <div class="repactions">
                    <button
                        class="vbtn listen-btn ${this._listening
                            ? "on"
                            : ""}"
                        @click=${() => void this._listen()}
                    >
                        ${this._listening
                            ? t("fitting.listening_btn")
                            : this._replaceQuality
                              ? t("fitting.listen_again")
                              : t("fitting.listen")}
                    </button>
                    ${this._replaceQuality?.protocol
                        ? html`<ir-protocol-chip
                              .protocol=${this._replaceQuality.protocol}
                              .bypass=${this._replaceBypass}
                              ?interactive=${!this._fit?.matrix}
                              @toggle-bypass=${(e: CustomEvent) =>
                                  (this._replaceBypass = e.detail.bypass)}
                          ></ir-protocol-chip>`
                        : nothing}
                    <span class="rep-hint"
                        >${t("fitting.replace_hint")}</span
                    >
                    <button
                        class="vbtn"
                        @click=${() => void this._closeReplace()}
                    >
                        ${t("common.cancel")}
                    </button>
                    <button
                        class="vbtn replace-confirm"
                        ?disabled=${!ready}
                        @click=${() => void this._confirmReplace()}
                    >
                        ${rough
                            ? t("fitting.replace_anyway")
                            : t("fitting.replace")}
                    </button>
                </div>
            </div>
        `;
    }

    /** The dimension-check list (mockup CC1): the same scrolling list,
     * grouped under uppercase section headers with a thin rule. Rows
     * keep their session index, so marks and sends address the backend
     * exactly as the signal flow does. */
    private _renderMatrixList() {
        const rows = this._fit!.rows;
        const out: unknown[] = [];
        let section: string | null = null;
        rows.forEach((row, i) => {
            if (row.section !== section) {
                section = row.section;
                out.push(this._renderSectionHead(row));
            }
            out.push(this._renderMatrixRow(i));
        });
        return out;
    }

    /** One matrix temperature as display text, converted to the
     * viewer's install unit when it differs from the wig's native
     * unit (unit ruling 2026-07-29). Labels only -- row KEYS and the
     * mark/send indexing stay native and untouched. */
    private _displayTemp(temp: number): string {
        return displayTemp(
            temp,
            this._fit?.unit ?? "C",
            installUnit(this.hass),
            this._fit?.precision ?? 1,
        );
    }

    /** The section's dim context note: what stays constant while this
     * section's rows walk one dimension, read off the section's FIRST
     * row (owner ruling 2026-07-28, e.g. "in cool 23, fan auto"). */
    private _sectionNote(row: FittingRow): string {
        if (row.section === "modes") return t("fitting.sec_modes_note");
        if (row.section === "changed") return t("fitting.sec_changed_note");
        if (
            row.section !== "fan" &&
            row.section !== "swing" &&
            row.section !== "temp"
        ) {
            return "";
        }
        const parts: string[] = [];
        if (row.mode) {
            const temp = row.section === "temp" ? null : row.temp;
            parts.push(
                temp != null
                    ? `${row.mode} ${this._displayTemp(temp)}`
                    : row.mode,
            );
        }
        if (row.section !== "fan" && row.fan != null) {
            parts.push(t("fitting.ctx_fan", { fan: row.fan }));
        }
        if (row.section !== "swing" && row.swing != null) {
            parts.push(t("fitting.ctx_swing", { swing: row.swing }));
        }
        if (parts.length === 0) return "";
        return t("fitting.sec_in", { context: parts.join(", ") });
    }

    private _renderSectionHead(row: FittingRow) {
        const note = this._sectionNote(row);
        return html`
            <div class="sec-head">
                <span>${t(`fitting.sec_${row.section}`)}</span>
                ${note
                    ? html`<span class="sec-note">${note}</span>`
                    : nothing}
            </div>
        `;
    }

    private _renderMatrixRow(i: number) {
        const row = this._fit!.rows[i];
        let label: string = row.key;
        let caps = false;
        let dim = "";
        if (row.section === "start") {
            label = t("fitting.row_on");
            caps = true;
        } else if (row.section === "wrap") {
            label = t("fitting.row_off");
            caps = true;
        } else if (row.section === "modes") {
            label = row.mode ?? row.key;
            caps = true;
            dim = [
                row.fan,
                row.temp != null
                    ? `${this._displayTemp(row.temp)}\u00b0`
                    : null,
            ]
                .filter(Boolean)
                .join(" \u00b7 ");
            if (row.temp_less) {
                dim = [dim, t("fitting.no_temp_note")]
                    .filter(Boolean)
                    .join(" ");
            }
        } else if (row.section === "fan") {
            label = row.fan ?? row.key;
        } else if (row.section === "swing") {
            label = row.swing ?? row.key;
        } else if (row.section === "temp") {
            label = t(
                row.temp_role === "min"
                    ? "fitting.temp_min"
                    : "fitting.temp_max",
                { temp: row.temp != null ? this._displayTemp(row.temp) : "" },
            );
        } else if (row.section === "changed") {
            // A cell the checklist does not sample, listed so the human
            // proves exactly what the machine touched. Its own
            // coordinates ARE its label.
            label = row.mode ?? row.key;
            caps = true;
            dim = [
                row.fan,
                row.swing,
                row.temp != null
                    ? `${this._displayTemp(row.temp)}°`
                    : null,
            ]
                .filter(Boolean)
                .join(" · ");
        }
        return html`
            <div class="sig-row" data-row-index=${i}>
                <span
                    class="sig-alias ${caps ? "caps" : ""}"
                    title=${row.key}
                    >${label}${dim
                        ? html` <span class="row-dim">${dim}</span>`
                        : nothing}${this._renderChip(i)}</span
                >
                ${this._renderTuneChips(i)} ${this._renderRowChip(i)}
                ${this._renderRowControls(i)}
            </div>
            ${this._renderReplaceStrip(i)}
        `;
    }

    /** The fittings ledger (placement ruled 2026-07-27: it lives here,
     * behind the status chips). Each row: handle, signature state,
     * date, then the evidence line. A bad signature discredits the
     * attribution, not the data, and the wording says which. */
    private _renderLedger() {
        const rows = this._fit?.ledger ?? [];
        const total = this._fit?.signals.length ?? 0;
        return html`
            <h3 class="heading">${t("fitting.ledger_heading")}</h3>
            <div class="ledger">
                ${rows.map((r) => {
                    const evidence: string[] = [];
                    if (r.hair_version)
                        evidence.push(`HAIR ${r.hair_version}`);
                    if (r.emitter)
                        evidence.push(
                            r.receiver
                                ? `${r.emitter} → ${r.receiver}`
                                : r.emitter,
                        );
                    evidence.push(
                        t("fitting.ledger_coverage", {
                            confirmed: String(r.confirmed),
                            total: String(total),
                        }),
                    );
                    if (r.signals_heard)
                        evidence.push(
                            t("fitting.ledger_heard", {
                                count: String(r.signals_heard),
                            }),
                        );
                    if (r.send_times_used)
                        // Absent renders nothing: unknown is not 1.
                        evidence.push(
                            t("fitting.ledger_send_times", {
                                count: String(r.send_times_used),
                            }),
                        );
                    if (r.key_fingerprint)
                        evidence.push(`key ${r.key_fingerprint}`);
                    return html`
                        <div class="led-row">
                            <div class="led-head">
                                <span class="led-handle"
                                    >${r.handle}</span
                                >
                                ${r.github
                                    ? html`<span class="led-gh"
                                          >@${r.github.replace(
                                              /^@/,
                                              "",
                                          )}</span
                                      >`
                                    : nothing}
                                ${r.draft
                                    ? html`<span
                                          class="led-sig unsigned"
                                          >${t(
                                              "fitting.ledger_in_progress",
                                          )}</span
                                      >`
                                    : r.signed === "valid"
                                      ? html`<span
                                            class="led-sig valid"
                                            >&check;
                                            ${t(
                                                "fitting.ledger_signed",
                                            )}</span
                                        >`
                                      : r.signed === "invalid"
                                        ? html`<span
                                              class="led-sig bad"
                                              >${t(
                                                  "fitting.ledger_bad_sig",
                                              )}</span
                                          >`
                                        : html`<span
                                              class="led-sig unsigned"
                                              >${t(
                                                  "fitting.ledger_unsigned",
                                              )}</span
                                          >`}
                                <span class="led-date"
                                    >${r.date ?? ""}</span
                                >
                            </div>
                            <div class="led-evidence">
                                ${evidence.join(" · ")}${r.failed
                                    ? html` ·
                                          ${r.failed_keys?.length
                                              ? html`<button
                                                    class="led-failed"
                                                    title=${t(
                                                        "fitting.ledger_goto_failed",
                                                    )}
                                                    @click=${() =>
                                                        this._navigateToFailed(
                                                            r.failed_keys!,
                                                        )}
                                                >
                                                    ${tp(
                                                        "fitting.failed",
                                                        r.failed,
                                                    )}
                                                </button>`
                                              : html`<span class="fail-note"
                                                    >${tp(
                                                        "fitting.failed",
                                                        r.failed,
                                                    )}</span
                                                >`}`
                                    : nothing}
                            </div>
                            ${!r.valid
                                ? html`<div class="led-invalid">
                                      ${t("fitting.ledger_invalid")}
                                  </div>`
                                : nothing}
                            ${r.note
                                ? html`<div class="led-note">
                                      “${r.note}”
                                  </div>`
                                : nothing}
                        </div>
                    `;
                })}
            </div>
            <div class="dialog-actions fit-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${() => (this._view = "session")}
                >
                    ${t("common.back")}
                </button>
            </div>
        `;
    }

    private _renderSign() {
        const c = this._counts;
        const emitterName =
            this._emitters().find((em) => em.id === this._emitter)
                ?.name ?? t("fitting.your_emitter");
        return html`
            <h3 class="heading">${t("fitting.sign_heading")}</h3>
            <div class="sign-line ${c.perfect ? "perfect" : ""}">
                ${c.perfect
                    ? t("fitting.sign_perfect", {
                          count: String(c.total),
                          emitter: emitterName,
                      })
                    : t("fitting.sign_partial", {
                          worked: String(c.worked),
                          failed: String(c.failed),
                          total: String(c.total),
                          emitter: emitterName,
                      })}
            </div>
            ${this._error
                ? html`<div class="err">${this._error}</div>`
                : nothing}
            <div class="field">
                <label>${t("fitting.handle")}</label>
                <input
                    .value=${this._handle}
                    @input=${(e: Event) =>
                        (this._handle = (
                            e.target as HTMLInputElement
                        ).value)}
                />
            </div>
            <div class="field">
                <label>${t("fitting.github")}</label>
                <!-- Decorative @ (roadmap, 2026-07-30): the format is
                     visible without being typed. Never enters _github;
                     the record payload is unchanged. Placeholder stays
                     "octocat" on purpose -- "@octocat" would suggest
                     typing the symbol, the opposite of the point. -->
                <div class="gh-wrap">
                    <span class="gh-at" aria-hidden="true">@</span>
                    <input
                        .value=${this._github}
                        placeholder="octocat"
                        @input=${(e: Event) =>
                            (this._github = (
                                e.target as HTMLInputElement
                            ).value)}
                    />
                </div>
                <div class="hint">${t("fitting.github_hint")}</div>
            </div>
            ${!this._fit?.kind
                ? html`<div class="field">
                      <label>${t("fitting.kind")}</label>
                      <input
                          list="kind-suggestions"
                          .value=${this._kind}
                          placeholder=${t("fitting.kind_placeholder")}
                          @input=${(e: Event) =>
                              (this._kind = (
                                  e.target as HTMLInputElement
                              ).value)}
                      />
                      <datalist id="kind-suggestions">
                          ${KIND_SUGGESTIONS.map(
                              (k) => html`<option value=${k}></option>`,
                          )}
                      </datalist>
                      <div class="hint">${t("fitting.kind_hint")}</div>
                  </div>`
                : nothing}
            <div class="field">
                <label>${t("fitting.note")}</label>
                <input
                    .value=${this._note}
                    placeholder=${t("fitting.note_placeholder")}
                    @input=${(e: Event) =>
                        (this._note = (
                            e.target as HTMLInputElement
                        ).value)}
                />
            </div>
            <div class="hint">${t("fitting.signed_hint")}</div>
            <div class="dialog-actions fit-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${() => (this._view = "session")}
                >
                    ${t("common.back")}
                </button>
                <span class="spacer"></span>
                <button
                    class="action-btn record-btn"
                    ?disabled=${this._busy}
                    @click=${this._record}
                >
                    ${t("fitting.record")}
                </button>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            /* Wider than the house 400px (owner bench 2026-07-30): a
               row now carries four buttons AND can carry a provenance
               chip, and at 440px the chip squeezed the signal's own
               name down to nothing. */
            .fit-dialog {
                max-width: 680px;
            }
            /* Decorative @ inside the GitHub field's left edge. */
            .gh-wrap {
                position: relative;
            }
            .gh-wrap .gh-at {
                position: absolute;
                left: 10px;
                top: 50%;
                transform: translateY(-50%);
                color: var(--secondary-text-color);
                pointer-events: none;
            }
            .gh-wrap input {
                width: 100%;
                box-sizing: border-box;
                padding-left: 24px;
            }
            .sess-head {
                font-size: 12.5px;
                color: var(--secondary-text-color);
                line-height: 1.5;
                margin-bottom: 12px;
            }
            /* The dimension-check claim (mockup CC1): sits under the
               title and says exactly what the 12-20 sends stand for. */
            .matrix-claim {
                font-size: 12.5px;
                color: var(--primary-text-color);
                line-height: 1.5;
                margin-bottom: 8px;
            }
            /* Sectioned list anatomy (matrix sessions only): uppercase
               header over a thin rule, dim context note alongside. */
            .sec-head {
                display: flex;
                align-items: baseline;
                gap: 8px;
                padding: 9px 12px 4px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--secondary-text-color);
                border-bottom: 1px solid var(--divider-color);
            }
            .sec-note {
                font-weight: 400;
                letter-spacing: normal;
                text-transform: none;
                font-size: 10.5px;
                opacity: 0.8;
            }
            .sig-alias.caps {
                text-transform: uppercase;
            }
            .row-dim {
                font-weight: 400;
                font-size: 11px;
                color: var(--secondary-text-color);
                text-transform: none;
            }
            .fitrow {
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
                margin: -4px 0 12px;
            }
            .fstat {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-size: 11px;
                font-weight: 500;
                padding: 3px 9px;
                border-radius: 12px;
                letter-spacing: 0.02em;
                font-family: inherit;
                cursor: pointer;
                background: none;
            }
            .fstat .tick {
                font-weight: 700;
            }
            .fstat.you {
                color: #66bb6a;
                background: rgba(76, 175, 80, 0.12);
                border: 1px solid rgba(76, 175, 80, 0.3);
            }
            .fstat.you.partial {
                color: #ffb300;
                background: rgba(255, 179, 0, 0.1);
                border-color: rgba(255, 179, 0, 0.35);
            }
            .fstat.others {
                color: var(--secondary-text-color);
                border: 1px solid var(--divider-color);
            }
            .fstat:hover {
                filter: brightness(1.2);
            }
            .ledger {
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                max-height: 340px;
                overflow-y: auto;
            }
            .led-row {
                padding: 9px 12px;
                border-bottom: 1px solid var(--divider-color);
                font-size: 12.5px;
                line-height: 1.5;
            }
            .led-row:last-child {
                border-bottom: none;
            }
            .led-head {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            .led-handle {
                font-weight: 600;
            }
            .led-gh {
                color: #78909c;
                font-size: 11.5px;
            }
            .led-date {
                color: var(--secondary-text-color);
                margin-left: auto;
                font-size: 11.5px;
            }
            .led-sig {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                border-radius: 3px;
                padding: 1px 6px;
            }
            .led-sig.valid {
                color: #66bb6a;
                background: rgba(76, 175, 80, 0.12);
                border: 1px solid rgba(76, 175, 80, 0.3);
            }
            .led-sig.bad {
                color: #e57373;
                background: rgba(198, 40, 40, 0.12);
                border: 1px solid rgba(198, 40, 40, 0.45);
            }
            .led-sig.unsigned {
                color: var(--secondary-text-color);
                border: 1px solid var(--divider-color);
            }
            .led-evidence {
                color: var(--secondary-text-color);
                font-size: 11.5px;
                margin-top: 2px;
            }
            .led-invalid {
                color: #e57373;
                font-size: 11.5px;
                margin-top: 2px;
            }
            .led-note {
                color: var(--primary-text-color);
                font-size: 11.5px;
                margin-top: 2px;
                font-style: italic;
            }
            .err {
                font-size: 12px;
                color: var(--error-color, #c62828);
                margin-bottom: 8px;
            }
            .field label {
                font-size: 11px;
                letter-spacing: 0.4px;
                text-transform: uppercase;
            }
            .field select {
                width: 100%;
                border: 1px solid var(--divider-color);
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
                font-family: inherit;
                background: var(--card-background-color);
                color: var(--primary-text-color);
            }
            .sig-list {
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                max-height: 300px;
                overflow-y: auto;
                margin-top: 4px;
            }
            .loading {
                padding: 16px;
                font-size: 12.5px;
                color: var(--secondary-text-color);
            }
            .sig-row {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 7px 12px;
                border-bottom: 1px solid var(--divider-color);
                font-size: 13px;
                min-height: 40px;
                box-sizing: border-box;
            }
            .sig-row:last-child {
                border-bottom: none;
            }
            .sig-alias {
                font-weight: 500;
                flex: 1;
                min-width: 96px;
                display: flex;
                align-items: center;
                gap: 7px;
                overflow: hidden;
                white-space: nowrap;
            }
            /* Only the NAME truncates; the chip beside it keeps its size,
               so a long alias never eats the row's state. */
            .sig-alias > .row-dim,
            .sig-alias {
                text-overflow: ellipsis;
            }
            /* The same fixed 96px centred column as the Sniffer and
               Clipper, immediately left of SEND, with extra right margin:
               the row gap alone leaves the widest label (KASEIKYO64)
               crowding the button. Empty rather than absent on a row that
               decoded nothing, so SEND stays on one vertical line. */
            .chip-col {
                flex: 0 0 96px;
                display: flex;
                justify-content: center;
                align-items: center;
                margin-right: 10px;
            }
            /* The row's controls are anchored hard right and every one
               of them keeps its slot, so REPLACE draws a straight
               column down the list no matter what any row has been
               through (owner ruling 2026-08-02). Nothing variable is
               allowed in the run any more; the facts moved out. */
            .row-tail {
                margin-left: auto;
                display: flex;
                align-items: center;
                gap: 8px;
                flex: none;
            }
            /* TEST reports its own result. The three labels occupy ONE
               grid cell, all of them laid out, only the active one
               visible -- so the button is always as wide as its widest
               state in the reader's language and cannot resize when the
               label changes. Measuring would have worked too; this
               needs no measuring and no maintenance. */
            .test-btn {
                position: relative;
            }
            .tb-stack {
                display: grid;
            }
            .tb-lay {
                grid-area: 1 / 1;
                visibility: hidden;
                white-space: nowrap;
            }
            .tb-lay.on {
                visibility: visible;
            }
            /* Both results wear the same green (owner ruling
               2026-08-02). The first cut greyed a send nothing heard
               back, on the reasoning that only a confirmed round trip
               had earned the colour -- but the green here means "that
               press did something", and a send with no receiver in the
               room is still a send. The two states are already told
               apart by the words on the button, so the colour was
               carrying a distinction it did not need to and made half
               the presses look like failures. */
            .vbtn.test-btn.flash {
                color: #66bb6a;
                border-color: rgba(76, 175, 80, 0.5);
            }
            .send-btn {
                background: none;
                border: 1px solid var(--divider-color);
                color: var(--primary-text-color);
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11.5px;
                font-weight: 500;
                text-transform: uppercase;
                cursor: pointer;
                font-family: inherit;
                flex: none;
            }
            .send-btn:hover:not(:disabled) {
                border-color: var(--secondary-text-color);
            }
            .send-btn:disabled {
                opacity: 0.45;
                cursor: default;
            }
            .vbtn {
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                cursor: pointer;
                font-family: inherit;
                flex: none;
                background: none;
                border: 1px solid var(--divider-color);
                color: var(--secondary-text-color);
            }
            /* The row buttons had no feedback states at all: TEST was
               already gated on an emitter being picked but looked
               identical either way, and neither TEST nor REPLACE
               acknowledged a hover or a press (owner bench 2026-08-02).
               A translucent grey fill on hover and a firmer one on
               press, which is the house gesture everywhere else. */
            .vbtn:hover:not(:disabled) {
                background: rgba(127, 127, 127, 0.14);
                border-color: var(--secondary-text-color);
            }
            .vbtn:active:not(:disabled) {
                background: rgba(127, 127, 127, 0.26);
            }
            .vbtn:disabled {
                opacity: 0.4;
                cursor: default;
            }
            /* The copper family keeps its own tint on hover rather than
               going grey, so REPLACE stays legibly the code-handling
               action while it is being pointed at. */
            .vbtn.replace-btn:hover:not(:disabled) {
                background: rgba(201, 138, 75, 0.16);
                border-color: rgba(201, 138, 75, 0.6);
            }
            .vbtn.replace-btn:active:not(:disabled) {
                background: rgba(201, 138, 75, 0.28);
            }
            .thumb:hover:not(:disabled) {
                background: rgba(127, 127, 127, 0.14);
                border-color: var(--secondary-text-color);
            }
            .thumb.up.on:hover {
                background: #2e7d32;
            }
            .thumb.down.on:hover {
                background: #c62828;
            }
            .vbtn.worked-on {
                background: rgba(76, 175, 80, 0.12);
                border-color: rgba(76, 175, 80, 0.45);
                color: #66bb6a;
            }
            .vbtn.failed-on {
                background: rgba(198, 40, 40, 0.14);
                border-color: rgba(198, 40, 40, 0.5);
                color: #e57373;
            }
            /* The replace family is copper (RULED 2026-07-30), which is
               the Clipper's accent: both are "you are handling the
               codes themselves", as against the green/red of judging
               what a code did. */
            .vbtn.replace-btn {
                color: #c98a4b;
                border-color: rgba(201, 138, 75, 0.35);
            }
            .vbtn.replace-btn.open {
                background: rgba(201, 138, 75, 0.15);
                border-color: rgba(201, 138, 75, 0.6);
            }
            /* Theme-safe by construction: a mid-grey alpha fill reads
               correctly on a light card and a dark one, and the marks ride
               Home Assistant's semantic colours rather than fixed hexes, so
               a pale blue that works on #111 cannot go invisible on white
               (owner bench 2026-07-31). */

            /* ---- the transmit-recipe chips (FT5) ---- */
            /* Fixed slots, not content-sized. A bypassed row keeps an
               empty ditto cell so the gating reads as an aligned gap
               rather than a jog down a long checklist. */
            .tune-cell {
                flex: none;
                width: 44px;
                display: inline-flex;
                justify-content: center;
                align-items: center;
            }
            .tchip {
                display: inline-flex;
                align-items: center;
                gap: 2px;
                font-size: 9px;
                font-weight: 600;
                font-family: inherit;
                line-height: 1;
                padding: 3px 5px;
                border: none;
                border-radius: 8px;
                background: rgba(127, 127, 127, 0.14);
                cursor: pointer;
                /* At default the chip is a fact, not a signal. It only
                   wears its catalog colour once it carries a number
                   somebody chose. */
                color: var(--secondary-text-color);
            }
            .tchip ha-svg-icon {
                --mdc-icon-size: 10px;
            }
            .tchip.sends:not(.at-default) {
                color: var(--warning-color, #e6a23c);
            }
            .tchip.dittos:not(.at-default) {
                color: var(--primary-color);
            }
            .tstep {
                display: inline-flex;
                align-items: center;
                gap: 1px;
                padding: 1px;
            }
            .tstep-btn {
                /* Two side-by-side 20px targets beat stacked arrows on
                   a wall tablet, which is where fittings actually
                   happen. */
                width: 20px;
                height: 20px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border: none;
                background: none;
                border-radius: 6px;
                cursor: pointer;
                color: var(--primary-text-color);
                font-family: inherit;
                font-size: 12px;
                line-height: 1;
            }
            .tstep-btn:hover {
                background: rgba(127, 127, 127, 0.2);
            }
            /* The number is also the way out: clicking it collapses the
               stepper back to the chip. */
            .tstep-val {
                min-width: 14px;
                text-align: center;
                font-size: 10px;
                font-weight: 600;
                border: none;
                background: none;
                padding: 0;
                cursor: pointer;
                font-family: inherit;
                color: var(--primary-text-color);
                line-height: 1;
            }
            .tstep-val:hover {
                color: var(--secondary-text-color);
            }
            .tstep-hint {
                font-size: 9px;
                color: var(--secondary-text-color);
                padding: 0 4px;
                white-space: nowrap;
            }
            .prov-chip .cmark.comb {
                display: inline-flex;
                align-items: center;
            }
            .prov-chip .cmark.comb svg {
                width: 10px;
                height: 10px;
                display: block;
                opacity: 0.8;
            }
            .prov-chip .cmark.comb svg path {
                fill: var(--secondary-text-color);
            }
            /* ---- thumb verdicts ---- */
            /* The verdict rides the DIRECTION, so it survives
               colourblindness; colour only reinforces it. The reclaimed
               width funds the tune chips, and the row stops depending on
               how long the verdict words are in the reader's language --
               they were the two widest translated things in the row. */
            .thumb {
                flex: none;
                width: 27px;
                height: 27px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border: 1px solid var(--divider-color);
                border-radius: 4px;
                background: none;
                cursor: pointer;
                color: var(--secondary-text-color);
                padding: 0;
            }
            .thumb ha-svg-icon {
                --mdc-icon-size: 15px;
            }
            .thumb.up.on {
                color: #fff;
                background: #2e7d32;
                border-color: #2e7d32;
            }
            .thumb.down.on {
                color: #fff;
                background: #c62828;
                border-color: #c62828;
            }
            /* Subordinate to the number it acts on (owner ruling
               2026-08-02): about 30 percent tighter than the row's
               other buttons, so it reads as a modifier attached to
               Send times rather than a peer of TEST and REPLACE. */
            .apply-btn {
                font-size: 9.5px;
                font-weight: 600;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                font-family: inherit;
                padding: 3px 7px;
                margin-left: 4px;
                border-radius: 4px;
                cursor: pointer;
                background: none;
                color: var(--warning-color, #e6a23c);
                border: 1px solid rgba(230, 162, 60, 0.45);
            }
            .apply-btn:hover:not(:disabled) {
                background: rgba(230, 162, 60, 0.14);
                border-color: var(--warning-color, #e6a23c);
            }
            .apply-btn:active:not(:disabled) {
                background: rgba(230, 162, 60, 0.26);
            }
            .apply-btn:disabled {
                opacity: 0.4;
                cursor: default;
            }
            .hint-apply {
                display: block;
                margin-top: 2px;
            }
            .qline.staged {
                color: var(--secondary-text-color);
            }
            .prov-chip {
                flex: none;
                display: inline-flex;
                align-items: center;
                gap: 5px;
                position: relative;
                font-size: 9px;
                font-weight: 600;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                white-space: nowrap;
                padding: 2px 8px 2px 6px;
                border: none;
                border-radius: 9px;
                background: rgba(127, 127, 127, 0.14);
                color: var(--secondary-text-color);
                font-family: inherit;
            }
            .prov-chip .cmark {
                flex: none;
                line-height: 1;
            }
            .prov-chip .cmark.warn {
                color: var(--warning-color, #e6a23c);
                font-size: 9.5px;
            }
            .prov-chip .cmark.tick {
                color: var(--info-color, #64b5f6);
                font-size: 10px;
                font-weight: 700;
            }
            .prov-chip .cmark.undo {
                color: var(--info-color, #64b5f6);
                font-size: 11px;
            }
            .prov-chip.revertible {
                cursor: pointer;
            }
            .prov-chip .chip-face,
            .prov-chip .chip-alt {
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }
            .prov-chip .chip-alt {
                position: absolute;
                inset: 0;
                justify-content: center;
                visibility: hidden;
            }
            .prov-chip.revertible:hover .chip-face,
            .prov-chip.armed .chip-face {
                visibility: hidden;
            }
            .prov-chip.revertible:hover .chip-alt,
            .prov-chip.armed .chip-alt {
                visibility: visible;
            }
            /* Armed has to be unmistakable: the next click throws away a
               capture somebody may have walked across the house for. */
            .prov-chip.armed {
                background: var(--info-color, #1565c0);
                color: #fff;
            }
            .prov-chip.armed .cmark {
                color: #fff;
            }
            .repstrip {
                margin: 2px 12px 10px 12px;
                background: var(--card-background-color);
                border: 1px solid rgba(201, 138, 75, 0.35);
                border-radius: 8px;
                padding: 10px 12px;
            }
            .repstrip .titleline {
                display: flex;
                align-items: baseline;
                gap: 8px;
                flex-wrap: wrap;
                margin-bottom: 8px;
            }
            .repstrip .t {
                font-size: 10.5px;
                font-weight: 600;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: #c98a4b;
            }
            .repstrip .why {
                font-size: 11.5px;
                color: var(--secondary-text-color);
            }
            .prontobox {
                width: 100%;
                box-sizing: border-box;
                min-height: 54px;
                background: var(--primary-background-color);
                color: var(--primary-text-color);
                border: 1px solid var(--divider-color);
                border-radius: 5px;
                font-family: ui-monospace, "SF Mono", Menlo, monospace;
                font-size: 11px;
                line-height: 1.5;
                padding: 8px 10px;
                resize: vertical;
            }
            .qline {
                display: flex;
                align-items: center;
                gap: 7px;
                margin-top: 7px;
                font-size: 11.5px;
                line-height: 1.4;
            }
            .qline.listen {
                color: #64b5f6;
            }
            .qline.good {
                color: #66bb6a;
            }
            .qline.warn {
                color: #e6a23c;
            }
            .qline.bad {
                color: var(--error-color, #c62828);
            }
            .pulse {
                flex: none;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #64b5f6;
                animation: fit-pulse 1.1s ease-in-out infinite;
            }
            @keyframes fit-pulse {
                0%,
                100% {
                    opacity: 0.25;
                }
                50% {
                    opacity: 1;
                }
            }
            .repactions {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 10px;
                flex-wrap: wrap;
            }
            .rep-hint {
                flex: 1;
                min-width: 120px;
                font-size: 11px;
                color: var(--secondary-text-color);
            }
            .vbtn.listen-btn {
                color: #64b5f6;
                border-color: rgba(100, 181, 246, 0.35);
            }
            .vbtn.listen-btn.on {
                background: rgba(100, 181, 246, 0.15);
            }
            .vbtn.replace-confirm {
                background: #c98a4b;
                border-color: #c98a4b;
                color: #fff;
            }
            .vbtn.replace-confirm:disabled {
                opacity: 0.4;
                cursor: default;
            }
            .notice {
                margin: 0 0 10px;
                padding: 8px 12px;
                border-radius: 6px;
                background: rgba(201, 138, 75, 0.08);
                border: 1px solid rgba(201, 138, 75, 0.35);
                font-size: 11.5px;
                color: var(--secondary-text-color);
                line-height: 1.5;
            }
            .led-failed {
                background: none;
                border: none;
                padding: 0;
                font: inherit;
                cursor: pointer;
                color: #e57373;
                text-decoration: underline dotted;
                text-underline-offset: 3px;
            }
            .progress-line {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 12.5px;
                color: var(--secondary-text-color);
                padding: 10px 2px 0;
            }
            .progress-line.perfect {
                color: #66bb6a;
            }
            .progress-line .bar {
                flex: 1;
                height: 4px;
                border-radius: 2px;
                background: var(--divider-color);
                overflow: hidden;
            }
            .progress-line .bar i {
                display: block;
                height: 100%;
                background: #66bb6a;
            }
            .fail-note {
                color: #e57373;
            }
            .fit-actions {
                margin-top: 14px;
            }
            .spacer {
                flex: 1;
            }
            .discard-q {
                font-size: 12.5px;
                color: var(--primary-text-color);
            }
            .discard-revert {
                color: #c98a4b;
            }
            /* Discard is disabled until there is something to discard,
               and the two states used to look identical (owner bench
               2026-08-02). Armed, it says so in red text; hovering
               fills the same red at the house opacity. */
            .discard-btn {
                color: var(--error-color, #c62828);
                border-color: rgba(198, 40, 40, 0.4);
            }
            .discard-btn:hover:not(:disabled) {
                background: rgba(198, 40, 40, 0.14);
                border-color: var(--error-color, #c62828);
            }
            .discard-btn:active:not(:disabled) {
                background: rgba(198, 40, 40, 0.26);
            }
            .discard-btn:disabled {
                color: var(--secondary-text-color);
                border-color: var(--divider-color);
                opacity: 0.4;
                cursor: default;
            }
            .discard-yes {
                color: var(--error-color, #c62828);
                border-color: var(--error-color, #c62828);
            }
            .finish-btn {
                color: #66bb6a;
                border-color: rgba(76, 175, 80, 0.45);
            }
            .finish-btn.green {
                background: #2e7d32;
                border-color: #2e7d32;
                color: #fff;
            }
            .record-btn {
                background: #2e7d32;
                border-color: #2e7d32;
                color: #fff;
            }
            .sign-line {
                border-radius: 8px;
                padding: 9px 12px;
                font-size: 12.5px;
                line-height: 1.45;
                margin-bottom: 12px;
                background: rgba(255, 160, 0, 0.1);
                border: 1px solid rgba(255, 160, 0, 0.4);
            }
            .sign-line.perfect {
                background: rgba(76, 175, 80, 0.12);
                border-color: rgba(76, 175, 80, 0.45);
            }
            .hint {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                margin-top: 6px;
                line-height: 1.4;
            }
        `,
    ];
}
