/**
 * Unified Pronto editor dialog for Sniffer / Clipper signals.
 *
 * One ha-dialog that creates a new signal (blank, from "+ Add Signal") or
 * edits an existing one (pre-filled, from a row's copy/edit glyph). Live-
 * validates the Pronto (debounced), shows the carrier, burst-pair count,
 * S/L diamond preview, and "Recognized as NEC". In edit mode it exposes a
 * Copy code button and, when the signal has a bound trigger, a note that
 * the trigger re-points automatically on a code change.
 *
 * Replaces ir-create-signal-dialog (create) and the read-only
 * ir-pronto-popover (view/copy). Snap is layered on in a later step.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type {
    ProntoValidation,
    RepeatVote,
    TangleApplyResult,
    TangleCaptureEvent,
    TangleCluster,
    TangleListenEvent,
    TangleRow,
    UnknownSignal,
} from "./types.js";
import { isDittoable } from "./ir-tx-knobs.js";
import { claimedFor, fieldWords, sameReading } from "./ir-tangle-copy.js";
import { installUnit, type MatrixUnit } from "./temperature.js";

// Mirrors PRONTO_SL_THRESHOLD / PRONTO_GAP_THRESHOLD in const.py. Used only
// for the dialog's S/L preview; the stored pattern is computed server-side.
const SL_THRESHOLD = 0x30;
const GAP_THRESHOLD = 0x0400;

// Mirrors frequency_standards.py. Drives the off-standard snap notice; the
// authoritative re-encode happens server-side via snap-preview.
const IR_CARRIER_STANDARDS_HZ = [30000, 33000, 36000, 38000, 40000, 56000];
const ON_STANDARD_TOLERANCE_HZ = 500;
// Nearest standard; on a tie the lower one wins (matches Python's min), since
// reduce keeps the earlier value when the new distance is not strictly less.
const nearestStandard = (hz: number): number =>
    IR_CARRIER_STANDARDS_HZ.reduce((a, b) =>
        Math.abs(b - hz) < Math.abs(a - hz) ? b : a,
    );
const isOnStandard = (hz: number): boolean =>
    Math.abs(hz - nearestStandard(hz)) <= ON_STANDARD_TOLERANCE_HZ;

// mdi:content-copy -- corner copy/select affordance on the code box.
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";

@customElement("ir-signal-editor")
export class IrSignalEditor extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    /** Present => edit a stored signal; absent => create (or command mode). */
    @property({ attribute: false }) public signalId: string | null = null;
    /** Present => edit a device command instead of a catalog signal. */
    @property({ attribute: false }) public commandId: string | null = null;
    @property({ attribute: false }) public initialPronto = "";
    @property({ attribute: false }) public initialAlias = "";
    /** Current whole-frame send count (all modes). */
    @property({ attribute: false }) public initialSendCount = 1;
    /** Current NEC ditto count (all modes). */
    @property({ attribute: false }) public initialDitto = 1;
    /** Read-only hint: dittos observed following this signal at capture. */
    @property({ attribute: false }) public initialObservedRepeatCount = 0;
    /** Command mode only: the command's per-command PRONTO toggle. */
    @property({ attribute: false }) public initialTxForceRaw = false;
    /** Command mode only: the command's stored decoded protocol (null if raw). */
    @property({ attribute: false }) public initialDecodedProtocol: string | null =
        null;
    @property({ type: Boolean }) public hasTrigger = false;
    /** Sniffer-only: enables the off-standard carrier snap affordance. */
    @property({ type: Boolean }) public allowSnap = false;

    /** TANGLE CONTEXT (0.14.1 B1). The row id this popup is repairing.
     *
     * Set means the dialog is the Fix entry on a tangle row rather than
     * an ordinary editor, and three things change: the fields that have
     * no meaning here are not rendered, the row's reason line leads,
     * and Save routes through the tangle apply door instead of the
     * command or signal update.
     *
     * It is the SAME dialog on purpose. A person repairing a code and a
     * person editing one are doing the same thing to the same bytes,
     * and a second component would be a second place for the validation
     * and the carrier snap to drift.
     */
    @property({ attribute: false }) public tangleTarget: string | null = null;

    /** The row's own reason line, rendered at the top of the popup so
     * the person can see what they are fixing while they fix it. */
    @property({ attribute: false }) public tangleReason: string | null = null;

    /** The whole row, for the press flow that moved in here on
     * 2026-09-03. The read-back needs the row's own coordinates to
     * judge a witness press, which the bare target id cannot carry. */
    @property({ attribute: false }) public tangleRow: TangleRow | null = null;

    /** The row's cluster, or null. Its mechanic decides which match
     * logic a press is judged by, and a witness cluster is the only
     * shape a good press can seed further fixes from. */
    @property({ attribute: false }) public tangleCluster: TangleCluster | null =
        null;

    /** Whether this row's wig is covered by a field map, straight
     * off the listing's own ``field_tier`` (owner field case,
     * 2026-09-04).
     *
     * It is what tells the two meanings of ``verdict.matches: null``
     * apart, and it comes from the listing rather than from the verdict
     * because the verdict cannot say it: an unmapped wig and a mapped
     * wig that could not read the press both arrive with no protocol
     * and nothing to compare. The listing knows which wig it is. */
    @property({ type: Boolean }) public tangleMapped = false;

    /** The matrix's native unit, so a quoted reading is spoken in the
     * unit the panel is showing (T5) rather than the lattice's own. */
    @property({ attribute: false }) public matrixUnit: MatrixUnit = "C";

    /** Only for installUnit; this dialog reads nothing else off it. */
    @property({ attribute: false }) public hass: unknown = null;

    /** Set once an apply has been refused for an undeclared
     * cross-reading, or once three presses in a row have read as
     * something else. Both offer the same answer -- use it anyway --
     * and the two roads differ only in WHICH bytes that answer
     * applies and under which source, which is what the two fields
     * below carry. */
    @state() private _tangleLadder = false;
    @state() private _tangleLadderPronto: string | null = null;
    @state() private _tangleLadderSource: "paste" | "capture" = "paste";

    /** The press flow's own state, relocated whole from
     * ir-tangle-listen. Arming and listening are distinct because an
     * arm can fail before it takes; heard is distinct from both
     * because a press that has ARRIVED is being judged and applied,
     * and the button that asked for it has to say so (issue 14). */
    @state() private _tangleArming = false;
    @state() private _tangleListening = false;
    @state() private _tangleHeard = false;
    @state() private _tangleMisses = 0;
    @state() private _tangleMessage: string | null = null;
    /** The most recent decoded press, good or mismatched. USE IT
     * ANYWAY has to apply THIS, never the row's own current (still
     * wrong) bytes and never whatever is in the box. */
    private _tangleLastPronto: string | null = null;
    private _tangleUnlisten: (() => Promise<void>) | null = null;

    @state() private _pronto = "";
    @state() private _alias = "";
    @state() private _sendCount = 1;
    @state() private _ditto = 1;
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _validation: ProntoValidation | null = null;
    @state() private _copyHint: string | null = null;
    @state() private _snapping = false;
    @state() private _snapFlash = false;
    /** Has the person touched the code box? Only the tangle context
     * asks: there the box is the second road, so it stays small and
     * quiet until it is the road being taken. */
    @state() private _codeFocused = false;
    /** Command mode: the live bypass choice, saved on Save like the rest. */
    @state() private _bypass = false;
    @state() private _listening = false;
    @state() private _listenMissed = false;
    /** What the last capture was, for the status line. Null once the box
     * is hand-edited: the line described a capture that is no longer
     * what is in the box. */
    @state() private _captured: {
        decoded: boolean;
        protocol: string | null;
        receiver: string | null;
        repeats?: RepeatVote;
    } | null = null;

    private _debounce: ReturnType<typeof setTimeout> | null = null;
    private _unlisten: (() => Promise<void>) | null = null;

    private get _isCommand(): boolean {
        return this.commandId !== null;
    }

    private get _isEdit(): boolean {
        return this.signalId !== null || this.commandId !== null;
    }

    private get _dirty(): boolean {
        return (
            this._pronto !== this.initialPronto ||
            this._alias !== this.initialAlias ||
            this._sendCount !== this.initialSendCount ||
            this._ditto !== this.initialDitto ||
            (this._isCommand && this._bypass !== this.initialTxForceRaw)
        );
    }

    private get _canSave(): boolean {
        if (this._busy || this._validation?.valid !== true) return false;
        return this._isEdit ? this._dirty : true;
    }

    /**
     * The Ditto count input is meaningful only on NEC.
     *
     * This gate used to read "any decoded protocol", on the reasoning
     * that dittos were generic across the rebuild tier. Measuring the
     * library says otherwise (see isDittoable in ir-tx-knobs): NEC
     * appends a real 4-entry repeat frame, Samsung32 and RC-5 duplicate
     * the whole frame, and Sharp and Sony ignore repeat_count entirely.
     * Only NEC is a ditto, so only NEC gets the knob (owner ruling
     * 2026-08-02).
     *
     * A pinned raw signal is excluded on top of that, in both modes: it
     * transmits through build_command, so its dittos never reach the
     * wire and offering the count would mislead (GH #78).
     */
    private get _dittoCountDisabled(): boolean {
        // Signal-edit / create mode: gate on the live-validated decoded
        // form, which names the protocol it recognized.
        if (!this._isCommand) {
            if (!this._pronto.trim()) return true;
            if (this._validation === null) return true;
            if (!this._validation.recognized_protocol) return true;
            return !isDittoable(
                this._validation.recognized_protocol,
                this.initialTxForceRaw,
            );
        }
        // Command-edit mode: gate on the decoded form and honour the
        // per-command PRONTO toggle. A code captured in this dialog has
        // not been stored yet, so the LIVE validation wins when there is
        // one -- otherwise replacing a raw code with a clean NEC capture
        // would leave the ditto knob hidden until after a save and
        // reopen.
        const protocol =
            this._validation?.recognized_protocol ??
            this.initialDecodedProtocol;
        return !isDittoable(protocol, this._bypass);
    }

    /** Tooltip for the disabled Ditto count input, by reason. */
    private get _dittoDisabledTooltip(): string {
        const stored = this._isCommand
            ? (this._validation?.recognized_protocol ??
              this.initialDecodedProtocol)
            : null;
        if (this._isCommand && stored && this._bypass) {
            return t("editor.ditto_disabled_cmd");
        }
        // Decoded, not pinned, still no ditto: the protocol simply has
        // no repeat frame. Name it, rather than leaving the fitter to
        // wonder why a perfectly good decode is refused.
        const decoded = this._isCommand
            ? stored
            : this._validation?.recognized_protocol;
        if (decoded && !this._bypass) {
            return t("editor.ditto_disabled_protocol", {
                protocol: decoded,
            });
        }
        return t("editor.ditto_disabled");
    }

    firstUpdated(): void {
        // Properties bound by the parent are set by first render; seed the
        // editable copies and validate a pre-filled code immediately.
        this._pronto = this.initialPronto;
        this._alias = this.initialAlias;
        this._sendCount = this.initialSendCount;
        this._ditto = this.initialDitto;
        this._bypass = this.initialTxForceRaw;
        if (this._pronto.trim()) {
            void this._validate();
        }
    }

    updated(): void {
        // Size the code box to fit its content so a long Pronto opens fully
        // visible. Reset to 0 first so scrollHeight reports the true content
        // height (not the current box height -- that overshoots), then clamp
        // between a small baseline and ~45% of the viewport.
        const ta = this.shadowRoot?.querySelector<HTMLTextAreaElement>("textarea");
        if (!ta) return;
        // A tangle popup's box is the code the row HAS, offered for
        // replacing rather than for reading, and a long Pronto sized to
        // fit pushed the press road off the bottom of the dialog. Until
        // it is focused it gets a low ceiling; touching it hands back
        // the ordinary fit-to-content behaviour.
        const held = this._isTangle && !this._codeFocused;
        const minPx = held ? 40 : 64;
        const maxPx = held ? 96 : Math.round(window.innerHeight * 0.45);
        ta.style.height = "0px";
        const fit = Math.min(Math.max(ta.scrollHeight + 2, minPx), maxPx);
        ta.style.height = `${fit}px`;
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        if (this._debounce !== null) {
            clearTimeout(this._debounce);
        }
        // A listen window outlives the dialog if nobody closes it, and
        // the next one would then land a capture in a box that is gone.
        void this._stopListening();
        // The tangle arm is a second, separate window on the same
        // principle: closing the popup IS the skip, and a skip that
        // left the server armed would spend the next press on a row
        // nobody is looking at.
        void this._tangleTeardown();
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _onSendCountInput(e: Event): void {
        const raw = parseInt((e.target as HTMLInputElement).value, 10);
        this._sendCount = Number.isNaN(raw)
            ? 1
            : Math.max(1, Math.min(raw, 10));
    }

    private _onDittoInput(e: Event): void {
        const raw = parseInt((e.target as HTMLInputElement).value, 10);
        this._ditto = Number.isNaN(raw) ? 0 : Math.max(0, Math.min(raw, 20));
    }

    /**
     * The raw pin follows the bytes (RULED 2026-08-03).
     *
     * A pin is a claim a SPECIFIC capture earned: "these bytes break
     * when re-encoded". New bytes have not earned it, so replacing a
     * code clears it and the chip re-derives from the live decode --
     * the protocol name, or RAW only when nothing decodes. The person
     * re-pins by clicking the chip, deliberately, which is the only way
     * a pin was ever meant to exist.
     *
     * Keyed on the code actually DIFFERING from what was opened, not on
     * the input event firing. Typing a character and deleting it again
     * leaves the pin exactly where it was; so does pasting back the
     * same code. Anything less precise would make an undo destroy a
     * setting the person never meant to touch.
     *
     * Deliberately NOT called from the carrier snap: snapping re-times
     * the same waveform to a standard frequency. It is a normalisation
     * of the capture that earned the pin, not a replacement for it.
     */
    private _syncPinToPronto(): void {
        if (!this._isCommand) return;
        this._bypass =
            this._pronto.trim() === this.initialPronto.trim()
                ? this.initialTxForceRaw
                : false;
    }

    private _onProntoInput(e: Event): void {
        this._pronto = (e.target as HTMLTextAreaElement).value;
        this._syncPinToPronto();
        // Hand-edited text is no longer the capture the status line
        // described.
        this._captured = null;
        this._listenMissed = false;
        if (this._debounce !== null) {
            clearTimeout(this._debounce);
        }
        if (!this._pronto.trim()) {
            this._validation = null;
            return;
        }
        this._debounce = setTimeout(() => void this._validate(), 250);
    }

    private _onKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (this._canSave) {
                void this._save();
            }
        }
    }

    private async _validate(): Promise<void> {
        try {
            this._validation = await this.api.validatePronto(this._pronto);
        } catch {
            this._validation = null;
        }
    }

    private _slPreview(): string[] | null {
        const norm = this._validation?.normalized;
        if (!norm) return null;
        const words = norm.split(" ").map((w) => parseInt(w, 16));
        if (words.length < 5 || words.some((n) => Number.isNaN(n))) return null;
        const out: string[] = [];
        for (const t of words.slice(4)) {
            if (t >= GAP_THRESHOLD) break;
            out.push(t < SL_THRESHOLD ? "S" : "L");
        }
        return out.length ? out : null;
    }

    private get _isTangle(): boolean {
        return this.tangleTarget !== null;
    }

    /** Apply these bytes to the tangle row (0.14.1 B1).
     *
     * Through the SAME door the Fixes ready card and the listen flow
     * use, with source paste, so a pasted repair is recorded exactly
     * like any other: origin stamped, prior bytes kept, revert
     * available. Nothing new was added on the server for this.
     *
     * A paste that reads as a different state than the row claims is
     * refused rather than written, and the refusal is not an error
     * message to dismiss: it is the declared-override ladder. Saying
     * yes to it re-sends the identical bytes with the declaration
     * attached, which is what turns an accident into a decision.
     */
    private async _applyToTangle(declared: boolean): Promise<void> {
        this._busy = true;
        this._error = null;
        try {
            await this._tangleTeardown();
            const result = await this.api.tangleApply({
                deviceId: this.deviceId,
                target: this.tangleTarget as string,
                pronto: this._pronto,
                tested: true,
                // A paste is evidence of bytes, not of a transmission,
                // so zero is the true tally and the receipt reads
                // accepted rather than air-tested. Same value the
                // press road sends for the same reason.
                sendsFired: 0,
                source: "paste",
                ...(declared ? { readingDisagreed: true } : {}),
            });
            // A PASTE IS NOT A PRESS, so it carries no replaced count.
            // The section's closing receipt says "Got your press. N
            // codes replaced", and a paste that added itself to that
            // tally would put words in the person's hands they never
            // did. Nothing is lost: the wig write-through still
            // reports, and "Your wig has been updated." still lands.
            this._afterTangleApply(result, 0, 0);
        } catch (err) {
            const message = (err as Error).message || String(err);
            if (message.includes("reading_disagreed_required")) {
                this._raiseTangleLadder(this._pronto, "paste");
            } else {
                this._error = message;
            }
        } finally {
            this._busy = false;
        }
    }

    /** The ladder, from either road (2026-09-03).
     *
     * A refused paste and a third mismatched press are the same
     * situation said two ways: the bytes read as something other than
     * this row claims, and only the person can say whether the reading
     * or the remote is wrong. Saying yes re-sends the SAME bytes with
     * the declaration attached, which is what turns an accident into a
     * decision, so the bytes and the source both have to be remembered
     * rather than re-derived from whatever is in the box by then. */
    private _raiseTangleLadder(
        pronto: string,
        source: "paste" | "capture",
    ): void {
        this._tangleLadder = true;
        this._tangleLadderPronto = pronto;
        this._tangleLadderSource = source;
        this._error = t("tangles.listen_mismatch_3_noread");
    }

    private async _useTangleAnyway(): Promise<void> {
        const pronto = this._tangleLadderPronto;
        if (this._tangleLadderSource === "capture") {
            if (!pronto) return;
            await this._finishTangleCapture(pronto, true);
            return;
        }
        await this._applyToTangle(true);
    }

    /** Common tail of any settled tangle apply: tell the surface what
     * happened and get out of the way.
     *
     * ``replaced`` is how many codes THIS press put right, and
     * ``gained`` is how many further fixes it licensed. The section
     * adds the first up for its closing receipt and renders the second
     * as the cascade line, because a press that builds more fixes has
     * to say so and the popup is about to close. */
    private _afterTangleApply(
        result: TangleApplyResult,
        replaced: number,
        gained: number,
    ): void {
        this.dispatchEvent(
            new CustomEvent("tangle-mutated", {
                detail: {
                    wigWritten: result.wig?.written ?? null,
                    replaced,
                    gained,
                },
                bubbles: true,
                composed: true,
            }),
        );
        this._close();
    }

    /** Drop the current arm, tolerating one that is already gone.
     *
     * The server tears its own arm down after FITTING_LISTEN_TIMEOUT_S
     * of silence, and the stored unsubscribe then points at a
     * subscription that no longer exists, so calling it REJECTS. That
     * rejection was the first await in both the arm and the settle,
     * which is how USE IT ANYWAY could die before apply was ever
     * called and stay dead on every retry (issue 4). A dead arm is a
     * normal outcome, not an error. */
    private async _tangleTeardown(): Promise<void> {
        const unlisten = this._tangleUnlisten;
        this._tangleUnlisten = null;
        this._tangleListening = false;
        if (!unlisten) return;
        try {
            await unlisten();
        } catch {
            // Already gone server-side; nothing to release.
        }
    }

    private static _tangleError(err: unknown): string {
        if (err instanceof Error && err.message) return err.message;
        const message = (err as { message?: unknown } | null)?.message;
        return typeof message === "string" && message ? message : String(err);
    }

    /** Arm this row's listen window. One row listens at a time, and
     * only one popup is ever open, so that is now structural. */
    private async _armTangle(): Promise<void> {
        if (this._tangleArming || this._busy) return;
        if (!this._isTangle) return;
        this._tangleArming = true;
        this._error = null;
        try {
            await this._tangleTeardown();
            this._tangleListening = true;
            this._tangleMessage = null;
            this._tangleUnlisten = await this.api.tangleListen(
                this.deviceId,
                (event) => void this._onTangleEvent(event),
                this.tangleTarget as string,
            );
        } catch (err) {
            // The arm never took. Say so and leave it re-armable
            // rather than pretending it is listening.
            this._tangleListening = false;
            this._tangleMessage = IrSignalEditor._tangleError(err);
        } finally {
            this._tangleArming = false;
        }
    }

    /** Judge a press against this row, exactly as the inline card did.
     *
     * WITNESS-CLASS MATCH LOGIC (kickoff ruling, bench finding 1): a
     * legitimate witness capture can honestly read
     * ``verdict.matches: false``, because it demonstrates a value from
     * a DIFFERENT cell's coordinates on an axis this row's own label
     * does not cover. So a witness row keys on the witnessed field's
     * own value, never on bare ``matches``. A recapture row -- re-
     * proving one already-correct code -- has no such axis problem and
     * uses ``matches`` directly. */
    private async _onTangleEvent(event: TangleListenEvent): Promise<void> {
        if (event.type === "tangle_listen_timeout") {
            // The server has already torn this arm down, so the stored
            // unsubscribe is dead and must not be called (issue 4).
            this._tangleUnlisten = null;
            this._tangleListening = false;
            this._tangleHeard = false;
            this._tangleMessage = t("tangles.listen_timeout");
            return;
        }
        const capture = event as TangleCaptureEvent;
        // A PRESS ARRIVED (issue 14). The button stops waiting and says
        // so, and keeps saying so through judgment and apply -- nothing
        // used to acknowledge the press the button was sitting there
        // asking for, so the wait read as a control that had died.
        this._tangleHeard = true;
        if (!capture.decoded) {
            this._tangleHeard = false;
            this._tangleMessage = t("tangles.listen_garbled");
            return;
        }
        this._tangleLastPronto = capture.pronto;

        const cluster = this.tangleCluster;
        const isWitness = cluster?.mechanic === "witness";
        let good: boolean;
        if (isWitness && cluster?.field) {
            // THE WITNESS COMPARISON (issue 18, ship-blocker). reads_as
            // is keyed by map FIELD NAME and coordinates by cell AXIS,
            // and this read one with the other's key, so for every
            // temperature cluster the claim was undefined and a capture
            // reading exactly the right value went to the ladder.
            const readsAs = capture.verdict.reads_as as Record<
                string,
                unknown
            > | null;
            const witnessed = readsAs?.[cluster.field];
            const coords = this.tangleRow?.target.coordinates as
                | Record<string, unknown>
                | undefined;
            const asked = claimedFor(cluster.field, coords);
            good = sameReading(witnessed, asked);
        } else {
            // TWO DIFFERENT NULLS (owner field case, 2026-09-04).
            //
            // ``matches`` is null whenever nothing could be compared,
            // and that happens for two unrelated reasons.
            //
            // On a wig with no field map there is no claim to check a
            // press against at all. That is "nothing to disagree
            // with", not "wrong", and reading it as a miss made
            // recapture structurally impossible on flat wigs (issue 3,
            // owner ruled). Those presses still accept, unchanged.
            //
            // On a MAP-COVERED wig the same null also means the press
            // could not be read under the wig's own map -- a Samsung
            // remote pressed at a BAXI cell. Accepting that wrote a
            // foreign code into the lattice and the comb re-flagged the
            // row on the next pass, which is the field case this
            // distinguishes. There the reading is not absent, it
            // FAILED, and the noread ladder is exactly the thing that
            // says so.
            //
            // ``protocol`` is the verdict's own word for whether the
            // bytes were read at all, and ``tangleMapped`` is the
            // listing's word for whether there was a map to read them
            // with. Both are needed: neither alone separates the two.
            const claim = capture.verdict.matches;
            if (claim === null || claim === undefined) {
                good = !(this.tangleMapped && capture.verdict.protocol === null);
            } else {
                good = claim === true;
            }
        }

        if (good) {
            await this._finishTangleCapture(capture.pronto, false);
            return;
        }

        const misses = this._tangleMisses + 1;
        this._tangleMisses = misses;
        // Defensively (F3): where there is no reading to quote, say so
        // in words rather than interpolating a bare "?" into the
        // sentence, which is what a flat wig used to render.
        const heardWord = (
            capture.verdict.reads_as as Record<string, unknown> | null
        )?.[cluster?.field ?? ""];
        // The ladder speaks the panel's unit (T5). The reading is a
        // native lattice value, and quoting it raw put "Heard 26" under
        // a row named 79, which reads as the panel disagreeing with
        // itself rather than with the remote.
        const heard = fieldWords(
            cluster?.field,
            heardWord,
            this.matrixUnit,
            installUnit(this.hass),
        );
        const rung = misses >= 3 ? 3 : misses === 1 ? 1 : 2;
        this._tangleMessage =
            heard === null
                ? t(`tangles.listen_mismatch_${rung}_noread`)
                : t(`tangles.listen_mismatch_${rung}`, { heard });
        if (misses >= 3) {
            this._raiseTangleLadder(capture.pronto, "capture");
            // The ladder speaks for itself in the actions row; a red
            // alert saying the same thing twice would read as a
            // refusal of a press that has not been offered yet.
            this._error = null;
        }
        // The arm is NOT dropped -- a miss never reverted it -- so the
        // button goes back to waiting for the next press.
        this._tangleHeard = false;
    }

    /** A settled press: write the row, then -- witness clusters only --
     * ask what else this reading could seed and hand it up. */
    private async _finishTangleCapture(
        pronto: string,
        readingDisagreed: boolean,
    ): Promise<void> {
        if (this._busy) return;
        this._busy = true;
        this._error = null;
        try {
            await this._tangleTeardown();
            const result = await this.api.tangleApply({
                deviceId: this.deviceId,
                target: this.tangleTarget as string,
                pronto,
                tested: true,
                // A captured press is evidence of a press, not of a
                // transmission, so zero is the true tally and the
                // receipt reads accepted, never air-tested.
                sendsFired: 0,
                source: "capture",
                ...(readingDisagreed ? { readingDisagreed: true } : {}),
            });
            const gained = await this._planCascade(pronto);
            this._afterTangleApply(result, 1, gained);
        } catch (err) {
            // An apply can be refused for real reasons (the target no
            // longer carries a finding, an unusable pronto, an
            // undeclared disagreement). Put the reason where it can be
            // read and leave the popup usable, instead of pulsing at
            // something that has stopped (issue 4).
            const message = IrSignalEditor._tangleError(err);
            if (message.includes("reading_disagreed_required")) {
                this._raiseTangleLadder(pronto, "capture");
            } else {
                this._error = message;
            }
        } finally {
            this._busy = false;
            this._tangleHeard = false;
        }
    }

    /** What else this press licensed, for the cascade line.
     *
     * Pure: ``tangle/plan`` writes nothing. The candidates are handed
     * up so they can appear as ordinary Fix rows and move the "Fixes
     * ready" count live, exactly per the brief's closing line. Writing
     * them is still ACCEPT's job, in FIX, same as any other candidate.
     * A recapture cluster never plans -- "nothing can be derived" is
     * the whole meaning of that mechanic. Nor does a PASTE: the press
     * road is the only one that was ever a witness reading. */
    private async _planCascade(pronto: string): Promise<number> {
        const cluster = this.tangleCluster;
        if (cluster?.mechanic !== "witness" || !cluster.field) return 0;
        try {
            const plan = await this.api.tanglePlan({
                deviceId: this.deviceId,
                cluster: cluster.id,
                witness: pronto,
                witnessTarget: this.tangleTarget as string,
            });
            if (plan.refused) return 0;
            const gained = Object.keys(plan.candidates).filter(
                (member) => member !== this.tangleTarget,
            ).length;
            this.dispatchEvent(
                new CustomEvent("tangle-batch-planned", {
                    detail: {
                        clusterId: cluster.id,
                        witness: pronto,
                        witnessTarget: this.tangleTarget as string,
                        plan,
                    },
                    bubbles: true,
                    composed: true,
                }),
            );
            return gained;
        } catch {
            // Best-effort. The row this press was working is already
            // applied and settled; a plan that fails to resolve just
            // means no sibling rows show up early -- they are still
            // reachable the ordinary way once this cell counts as a
            // donor.
            return 0;
        }
    }

    private async _save(): Promise<void> {
        if (!this._canSave) return;
        if (this._isTangle) {
            await this._applyToTangle(false);
            return;
        }
        this._busy = true;
        this._error = null;
        // Ditto count persists only when the code is decodable; on a raw /
        // non-decoded code the input is disabled and we omit the field so the
        // saved record keeps the default rather than a stale tuned value.
        const ditto = this._dittoCountDisabled ? undefined : this._ditto;
        try {
            if (this._isCommand) {
                const result = await this.api.updateCommand({
                    device_id: this.deviceId,
                    command_id: this.commandId as string,
                    name: this._alias.trim(),
                    pronto: this._pronto,
                    send_count: this._sendCount,
                    repeat_count: ditto,
                });
                // The pin rides its own command, so it is written after
                // the content and only when it actually changed. Doing
                // it unconditionally would stamp a provenance marker on
                // every ordinary rename.
                if (this._bypass !== this.initialTxForceRaw) {
                    await this.api.setCommandTxForceRaw(
                        this.deviceId,
                        this.commandId as string,
                        this._bypass,
                    );
                    (result as any).tx_force_raw = this._bypass;
                }
                this.dispatchEvent(
                    new CustomEvent("command-edited", {
                        detail: result,
                        bubbles: true,
                        composed: true,
                    }),
                );
            } else if (this.signalId !== null) {
                const result = await this.api.editSignalPronto({
                    device_id: this.deviceId,
                    signal_id: this.signalId as string,
                    pronto: this._pronto,
                    alias: this._alias.trim(),
                    send_count: this._sendCount,
                    repeat_count: ditto,
                });
                this.dispatchEvent(
                    new CustomEvent("signal-edited", {
                        detail: result,
                        bubbles: true,
                        composed: true,
                    }),
                );
            } else {
                const result: { signal: UnknownSignal } =
                    await this.api.createSignal({
                        device_id: this.deviceId,
                        pronto: this._pronto,
                        alias: this._alias.trim() || undefined,
                        send_count: this._sendCount,
                        repeat_count: ditto,
                    });
                this.dispatchEvent(
                    new CustomEvent("signal-created", {
                        detail: result.signal,
                        bubbles: true,
                        composed: true,
                    }),
                );
            }
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private async _selectCode(): Promise<void> {
        // HA custom panels run in an iframe that is not granted
        // clipboard-write, so neither navigator.clipboard nor execCommand
        // reaches the system clipboard. The reliable path is to select the
        // code so the user copies it with their own keyboard gesture. We
        // still try the real clipboard silently in case a future HA build
        // allows it.
        const ta = this.shadowRoot?.querySelector<HTMLTextAreaElement>("textarea");
        if (ta) {
            ta.focus();
            ta.select();
        }
        let copied = false;
        try {
            if (window.isSecureContext && navigator.clipboard) {
                await navigator.clipboard.writeText(this._pronto);
                copied = true;
            }
        } catch {
            copied = false;
        }
        this._copyHint = copied ? t("editor.copied") : t("editor.press_copy");
        setTimeout(() => {
            this._copyHint = null;
        }, 2000);
    }

    /**
     * Replace this code: grab one live off the air, in place.
     *
     * NO ACCEPT STEP (RULED). A heard code lands in the Pronto box
     * directly, the validation line and the pill re-evaluate against it,
     * and Listen again re-captures. The box IS the accept -- an extra
     * confirm would only let a person say yes to something they can
     * already see, edit and cancel.
     */
    private async _listen(): Promise<void> {
        if (this._listening) {
            await this._stopListening();
            return;
        }
        this._error = null;
        this._listenMissed = false;
        this._listening = true;
        try {
            this._unlisten = await this.api.commandListen((event) => {
                if (event.type === "command_capture") {
                    this._onCaptured(event);
                } else {
                    this._listenMissed = true;
                }
                void this._stopListening();
            });
        } catch (err: any) {
            this._listening = false;
            this._error = err?.message ?? String(err);
        }
    }

    private _onCaptured(event: {
        pronto: string;
        decoded: boolean;
        protocol: string | null;
        receiver: string | null;
        repeats_disagree?: RepeatVote;
    }): void {
        this._pronto = event.pronto;
        this._syncPinToPronto();
        this._captured = {
            decoded: event.decoded,
            protocol: event.protocol,
            receiver: event.receiver,
            repeats: event.repeats_disagree,
        };
        // Dittos reset to the new decode's default on a swap; send times
        // keep the person's setting (RULED). A ditto count describes THIS
        // waveform's repeat frame, so carrying it across a code change
        // would apply one code's tuning to another's bytes. Send count
        // describes the room -- the distance, the sensor, the lamp in the
        // way -- and the room did not change.
        this._ditto = event.decoded ? 1 : 0;
        void this._validate();
    }

    private async _stopListening(): Promise<void> {
        this._listening = false;
        const unlisten = this._unlisten;
        this._unlisten = null;
        if (unlisten) {
            try {
                await unlisten();
            } catch {
                // The window is closing either way; a failed unsubscribe
                // is not something to put in front of the person.
            }
        }
    }

    /** PRESS THE BUTTON, from the footer (owner ruled 2026-09-03).
     *
     * It began as a copy of the ordinary editor's Replace block, on the
     * reasoning that it was the same offer: a second way to fill the
     * code box. The owner's bench walk read it the other way round. In
     * a repair the press is not an alternative to the box, it is the
     * road the window is for, so the button belongs on the line where
     * the window's decisions are made rather than in a block halfway
     * up the body. What differs from the ordinary Replace is unchanged
     * underneath: this press is judged against the row before anything
     * is written, and a clean one applies and closes rather than
     * landing in the box for a separate save.
     *
     * WHAT THE FLOW SAYS did not come with it: a footer has no room
     * for a sentence, so the status line stayed on the press road, in
     * _renderTangleStatus below. The three-miss answer is in neither
     * -- it is the dialog's primary button, so that saying yes to it
     * is the same gesture as saying yes to anything else. */
    private _renderTangleListenButton() {
        if (!this._isTangle) return "";
        const waiting = this._tangleListening && !this._tangleHeard;
        return html`
            <button
                class="action-btn listen-btn ${this._tangleHeard
                    ? "heard"
                    : waiting
                      ? "pulsing"
                      : ""}"
                ?disabled=${this._busy ||
                this._tangleArming ||
                this._tangleHeard}
                @click=${() => void this._armTangle()}
            >
                ${this._tangleHeard
                    ? t("tangles.listen_heard")
                    : waiting
                      ? html`<span class="pulse"
                            ><span class="dot"></span
                            ><span class="dot"></span
                            ><span class="dot"></span
                        ></span>`
                      : t("tangles.listen")}
            </button>
        `;
    }

    /** What the press flow last said: the waiting hint, a garbled
     * press, a mismatch with the heard values quoted in the panel's own
     * unit, or the timeout. It stays in the body, on the press road,
     * rather than following the button into a footer with no room for a
     * sentence. Nothing renders while there is nothing to say, so the
     * landing view is no longer than it was. */
    private _renderTangleStatus() {
        if (!this._isTangle) return "";
        const waiting = this._tangleListening && !this._tangleHeard;
        const line = this._tangleMessage
            ? this._tangleMessage
            : waiting
              ? t("editor.listen_hint")
              : "";
        if (!line) return "";
        return html`<div class="tangle-status">${line}</div>`;
    }

    /** THE SENTENCE (owner ruled 2026-09-03, rewritten on the bench
     * walk the same day). One plain line naming both roads out of
     * here, the press and the paste, before either control is reached.
     * It is also what names the code box now that the box carries no
     * label of its own. */
    private _renderTangleIntro() {
        if (!this._isTangle) return "";
        return html`<div class="tangle-intro">${t("tangles.popup_intro")}</div>`;
    }

    /** The code box, extracted so the tangle context can put it after
     * the press road without the ordinary editor's copy moving. */
    private _renderCodeBox() {
        const held = this._isTangle && !this._codeFocused;
        return html`
            <div class="field">
                <!-- NO LABEL IN A REPAIR (owner ruled 2026-09-03).
                     The sentence above the box already says what the
                     box holds and what to do with it; a label over it
                     was a third line saying the same one thing. -->
                ${this._isTangle
                    ? ""
                    : html`<label>${t("editor.pronto_code")}</label>`}
                <div class="code-wrap">
                    <textarea
                        class="${this._snapFlash ? "snap-flash" : ""} ${held
                            ? "held"
                            : ""}"
                        rows="4"
                        .value=${this._pronto}
                        placeholder="0000 006D ..."
                        ?autofocus=${!this._isTangle}
                        spellcheck="false"
                        @focus=${() => (this._codeFocused = true)}
                        @blur=${() => (this._codeFocused = false)}
                        @input=${this._onProntoInput}
                        @keydown=${this._onKeydown}
                    ></textarea>
                    ${this._pronto.trim()
                        ? html`
                              ${this._copyHint
                                  ? html`<span class="copy-flash"
                                        >${this._copyHint}</span
                                    >`
                                  : ""}
                              <button
                                  class="copy-icon"
                                  title=${t("editor.select_all")}
                                  @click=${this._selectCode}
                              >
                                  <ha-svg-icon .path=${ICON_COPY}></ha-svg-icon>
                              </button>
                          `
                        : ""}
                </div>
            </div>
        `;
    }

    private _renderReplace() {
        if (!this._isCommand) return "";
        return html`
            <div class="replace">
                <div class="replace-head">${t("editor.replace_title")}</div>
                <div class="replace-row">
                    <button
                        class="action-btn listen-btn ${this._listening
                            ? "on"
                            : ""}"
                        @click=${this._listen}
                        ?disabled=${this._busy}
                    >
                        ${this._listening
                            ? t("editor.listening")
                            : t("editor.listen")}
                    </button>
                    <span class="replace-status">
                        ${this._listening
                            ? t("editor.listen_hint")
                            : this._listenMissed
                              ? t("editor.listen_missed")
                              : this._captured
                                ? this._capturedLine()
                                : t("editor.replace_hint")}
                    </span>
                </div>
                ${this._renderRepeatNotice()}
            </div>
        `;
    }

    /**
     * This capture's repeats do not agree with each other.
     *
     * The one thing HAIR can say at capture time that nobody can say
     * later: press it again, it is free. NEVER A BLOCK and never an
     * auto-drop -- the code lands in the box like any other and the
     * person decides. Same check, same words as the comb's report; only
     * the moment is different.
     */
    private _renderRepeatNotice() {
        const vote = this._captured?.repeats;
        if (!vote) return "";
        return html`
            <div class="repeat-notice">
                ${t("comb.capture_repeats", {
                    frames: String(vote.frames),
                    readings: String(vote.readings),
                })}
            </div>
        `;
    }

    private _capturedLine(): string {
        const c = this._captured;
        if (!c) return "";
        const where = c.receiver ? ` · ${c.receiver}` : "";
        // Warn-and-allow: a rough capture stays editable and saveable.
        // The line says what it is; the person decides.
        return c.decoded
            ? `${t("editor.heard_clean")}${
                  c.protocol ? ` · ${c.protocol}` : ""
              }${where}`
            : `${t("editor.heard_rough")}${where}`;
    }

    /**
     * The standard one-pill, live, in command mode.
     *
     * Same component as every other home, so the choice reads the same
     * here as on the row. It is live because this is where a replaced
     * code most often needs pinning: a rough capture that will not
     * re-encode cleanly is exactly what BYPASS is for, and making the
     * person save, close, and toggle from the row would put two steps
     * between the problem and its fix.
     *
     * The protocol shown is the LIVE decode when there is one, so a
     * capture that has not been saved yet still names itself.
     */
    private _renderPill() {
        if (!this._isCommand) return "";
        const protocol =
            this._validation?.recognized_protocol ??
            this.initialDecodedProtocol;
        if (!protocol) return "";
        return html`
            <div class="pill-row">
                <ir-protocol-chip
                    .protocol=${protocol}
                    ?bypass=${this._bypass}
                    interactive
                    ?disabled=${this._busy}
                    @toggle-bypass=${(e: CustomEvent) => {
                        this._bypass = e.detail.bypass;
                    }}
                ></ir-protocol-chip>
            </div>
        `;
    }

    private _renderFeedback() {
        const v = this._validation;
        if (!v) return "";
        const sl = this._slPreview();
        return html`
            <div class="feedback">
                <div class="status ${v.valid ? "ok" : "bad"}">
                    <span class="mark">${v.valid ? "✓" : "✗"}</span>
                    ${v.valid ? t("editor.valid") : t("editor.not_valid")}
                </div>
                ${v.valid
                    ? html`
                          <div class="metrics">
                              ${v.frequency_khz !== null
                                  ? html`<span>${v.frequency_khz} kHz</span>`
                                  : ""}
                              ${v.burst_pair_count !== null
                                  ? html`<span
                                        >${tp("editor.burst_pair", v.burst_pair_count)}</span
                                    >`
                                  : ""}
                              ${v.recognized_protocol
                                  ? html`<span class="recognized"
                                        >${t("editor.recognized_as", { protocol: v.recognized_protocol })}</span
                                    >`
                                  : ""}
                          </div>
                          ${sl
                              ? html`<div class="diamonds">
                                    ${sl.map((c) =>
                                        c === "L"
                                            ? html`<span class="diamond long">◆</span>`
                                            : html`<span class="diamond short">◇</span>`,
                                    )}
                                </div>`
                              : ""}
                      `
                    : ""}
                ${v.errors.map((msg) => html`<div class="msg err">${msg}</div>`)}
                ${v.warnings.map((msg) => html`<div class="msg warn">${msg}</div>`)}
            </div>
        `;
    }

    /** Current valid carrier in Hz, or null when not validatable. */
    private get _carrierHz(): number | null {
        const khz = this._validation?.valid ? this._validation.frequency_khz : null;
        return khz != null ? Math.round(khz * 1000) : null;
    }

    /** Snap is offered only on the Sniffer when the carrier reads off-standard. */
    private get _showSnap(): boolean {
        if (!this.allowSnap) return false;
        const hz = this._carrierHz;
        return hz != null && !isOnStandard(hz);
    }

    private async _snap(target: number): Promise<void> {
        this._snapping = true;
        this._error = null;
        try {
            const res = await this.api.snapPreview({
                pronto: this._pronto,
                target_frequency: target,
            });
            this._pronto = res.pronto;
            // Re-validate so the carrier reads the standard value and the
            // off-standard notice clears; the flash settles the staged code.
            await this._validate();
            this._snapFlash = true;
            setTimeout(() => {
                this._snapFlash = false;
            }, 700);
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._snapping = false;
        }
    }

    private _renderSnap() {
        if (!this._showSnap) return "";
        const hz = this._carrierHz as number;
        const target = nearestStandard(hz);
        const curKhz = (hz / 1000).toFixed(1);
        const tgtKhz = (target / 1000).toFixed(0);
        return html`
            <div class="snap-notice">
                <div class="snap-text">
                    ${t("editor.snap_notice", { khz: curKhz })}
                </div>
                <button
                    class="snap-btn"
                    ?disabled=${this._snapping}
                    @click=${() => this._snap(target)}
                >
                    ${this._snapping ? t("editor.snapping") : t("editor.snap_to", { khz: tgtKhz })}
                </button>
            </div>
        `;
    }

    render() {
        // THE REASON IS THE HEADER (owner ruled 2026-09-03). In a
        // repair this window is about one broken row, so the row's own
        // sentence takes the window's header slot and wears the header
        // treatment every other window in the panel uses. Two things
        // go with that: it stops being a light gray line inside the
        // body, and the title stops reading "Create signal" over a
        // repair, which is what it said before.
        const heading =
            this._isTangle && this.tangleReason
                ? this.tangleReason
                : this._isCommand
                  ? t("editor.edit_command")
                  : this._isEdit
                    ? t("editor.edit_signal")
                    : t("editor.create_signal");
        const primaryLabel = this._isEdit
            ? this._busy
                ? t("common.saving")
                : t("common.save")
            : this._busy
              ? t("common.creating")
              : t("common.create");
        const showTriggerNote =
            this._isEdit && this.hasTrigger && this._dirty;
        const triggerNoteText = this._isCommand
            ? t("editor.trigger_note_cmd")
            : t("editor.trigger_note_sig");
        const nameLabel = this._isCommand
            ? t("assign.command_name")
            : this._isEdit
              ? t("editor.alias_label")
              : t("editor.alias_optional");
        return html`
            <ha-dialog
                open
                heading=${heading}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <!-- THE RULED ORDER (owner, 2026-09-03, twice).
                     In a repair the press road leads and the body is
                     short: the sentence, whatever the press flow last
                     said, then the code the row has now. Listen itself
                     is downstairs in the footer and the reason is
                     upstairs in the header, so what is left here is
                     only what has to be read on the way. Everywhere
                     else the code box leads exactly as it always has,
                     and the validation, pill and snap keep following
                     the box they describe either way. -->
                ${this._isTangle
                    ? html`${this._renderTangleIntro()}
                      ${this._renderTangleStatus()} ${this._renderCodeBox()}`
                    : html`${this._renderCodeBox()} ${this._renderReplace()}`}
                ${this._renderFeedback()}
                ${this._renderPill()} ${this._renderSnap()}

                ${this._isTangle
                    ? ""
                    : html`<div class="field">
                          <label>${nameLabel}</label>
                          <input
                              type="text"
                              .value=${this._alias}
                              placeholder=${t("editor.alias_placeholder")}
                              @input=${(e: Event) =>
                                  (this._alias = (
                                      e.target as HTMLInputElement
                                  ).value)}
                              @keydown=${this._onKeydown}
                          />
                      </div>`}

                <div class="field tx-knobs" ?hidden=${this._isTangle}>
                    <div class="knob">
                        <label>${t("assign.send_times")}</label>
                        <input
                            class="num-input"
                            type="number"
                            min="1"
                            max="10"
                            .value=${String(this._sendCount)}
                            title=${t("editor.send_times_title")}
                            @input=${this._onSendCountInput}
                            @keydown=${this._onKeydown}
                        />
                    </div>
                    ${this._dittoCountDisabled
                        ? ""
                        : html`<div class="knob">
                              <label>${t("assign.ditto_count")}</label>
                              <input
                                  class="num-input"
                                  type="number"
                                  min="0"
                                  max="20"
                                  .value=${String(this._ditto)}
                                  title=${t("editor.ditto_title")}
                                  @input=${this._onDittoInput}
                                  @keydown=${this._onKeydown}
                              />
                          </div>`}
                </div>
                ${this.initialObservedRepeatCount > 0 && !this._isTangle
                    ? html`<div class="observed-hint">
                          ${tp("editor.observed", this.initialObservedRepeatCount)}
                      </div>`
                    : ""}

                ${showTriggerNote && !this._isTangle
                    ? html`<div class="note">${triggerNoteText}</div>`
                    : ""}

                <!-- LISTEN IN THE CORNER (owner ruled 2026-09-03).
                     The press road ends on the line where the window's
                     decisions are made: Listen at the far left, the
                     spacer, then Cancel and the primary. -->
                <div class="dialog-actions">
                    ${this._renderTangleListenButton()}
                    <span class="spacer"></span>
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${t("common.cancel")}
                    </button>
                    ${this._isTangle && this._tangleLadder
                        ? html`<button
                              class="action-btn create-btn"
                              @click=${() => void this._useTangleAnyway()}
                              ?disabled=${this._busy}
                          >
                              ${t("tangles.use_anyway")}
                          </button>`
                        : html`<button
                              class="action-btn create-btn ${this._isTangle
                                  ? "tangle"
                                  : ""}"
                              @click=${this._save}
                              ?disabled=${!this._canSave}
                          >
                              ${primaryLabel}
                          </button>`}
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            /* The press flow's own line, on the press road. It sits
               where the block that used to hold both it and the button
               sat, minus the heading and the rule: the sentence above
               is already the separation, and the button is downstairs
               in the footer. */
            .tangle-status {
                font-size: 0.78rem;
                line-height: 1.35;
                color: var(--secondary-text-color);
                margin: 0 0 10px;
            }
            /* One plain line, in the dialog's own reading voice rather
               than a label's. */
            .tangle-intro {
                font-size: 0.82rem;
                line-height: 1.45;
                color: var(--primary-text-color);
                margin: 0 0 10px;
            }
            /* HELD BACK, NOT HIDDEN. The code is there to read and to
               replace, but until it is touched it should not be the
               first thing the eye lands on. Focus returns it to an
               ordinary field. */
            textarea.held {
                opacity: 0.6;
                font-size: 0.82rem;
                border-color: var(--divider-color);
                background: var(--secondary-background-color);
            }
            textarea.held:hover {
                opacity: 0.85;
            }
            textarea.held:focus {
                opacity: 1;
            }
            /* THE CORNER BUTTON (owner ruled 2026-09-03, restyled
               2026-09-04). Listen keeps the amber it has worn on this
               surface all along, but it wears it as a fill now rather
               than as an outline: the two things this footer offers are
               a press and a save, they are equally the point of the
               window, and an outlined chip beside a solid Create read
               as the lesser of the two. Same weight, same shape, one
               colour apart. Scoped by the footer rather than by a new
               class, so the button's own class list is untouched. */
            .dialog-actions .listen-btn {
                background: var(--tangle-amber, #b89930);
                border-color: var(--tangle-amber, #b89930);
                color: #fff;
                font-weight: 600;
            }
            /* THE DOTS SURVIVE THE RESTYLE (owner ruling with a pin
               behind it, issue 14). They were amber on the card's own
               background, which is exactly the fill they now sit on, so
               keeping the declaration would have kept the dots and lost
               the ability to see them. White is the same treatment the
               word beside them gets. */
            .dialog-actions .listen-btn .pulse .dot {
                background: #fff;
            }
            /* HEARD, through judgment and apply. Green is already this
               panel's word for a receiver caught it. It is reporting
               rather than offering, so it is disabled -- but the shared
               disabled fade would leave the one word the person is
               waiting to read as the faintest thing in the row. */
            .listen-btn.heard {
                color: #2e7d32;
                border-color: rgba(46, 125, 50, 0.4);
            }
            .listen-btn.heard:disabled {
                opacity: 1;
            }
            /* HEARD, on a filled button. Green is still the word, but a
               green word on an amber fill is not a state change anybody
               can read, so on this one the fill turns instead. The
               outlined Listen in the ordinary editor is untouched. */
            .dialog-actions .listen-btn.heard {
                background: #2e7d32;
                border-color: #2e7d32;
                color: #fff;
            }
            /* The dots came with the flow (issue 14, ruled
               2026-08-30). They were never the problem: the problem was
               that nothing acknowledged the press, so they ran on and
               read as a button that had died. With HEARD arriving at
               the end they read as what they are, which is waiting. */
            .pulse {
                display: inline-flex;
                gap: 3px;
                align-items: center;
                justify-content: center;
            }
            .pulse .dot {
                width: 4px;
                height: 4px;
                border-radius: 50%;
                background: var(--tangle-amber, #b89930);
                animation: tangle-pulse 1s ease-in-out infinite;
            }
            .pulse .dot:nth-child(2) {
                animation-delay: 0.15s;
            }
            .pulse .dot:nth-child(3) {
                animation-delay: 0.3s;
            }
            @keyframes tangle-pulse {
                0%,
                80%,
                100% {
                    opacity: 0.3;
                }
                40% {
                    opacity: 1;
                }
            }
            /* Three dots at rest still read as a distinct state, and
               the button says HEARD when the press lands either way. */
            @media (prefers-reduced-motion: reduce) {
                .pulse .dot {
                    animation: none;
                    opacity: 0.6;
                }
            }
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        input[type="text"],
        textarea {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        textarea {
            font-family: monospace;
            resize: vertical;
            /* Extra top padding keeps the first line of code clear of the
               corner copy icon. */
            padding-top: 24px;
            /* updated() sizes the height to fit the code (clamped in JS), so
               a long Pronto scrolls instead of overflowing the dialog. */
            overflow-y: auto;
        }
        .code-wrap {
            position: relative;
        }
        .copy-icon {
            position: absolute;
            top: 6px;
            right: 8px;
            z-index: 2;
            display: inline-flex;
            align-items: center;
            padding: 2px;
            border: none;
            background: none;
            color: var(--secondary-text-color);
            cursor: pointer;
            opacity: 0.55;
            transition: opacity 150ms ease;
        }
        .copy-icon:hover {
            opacity: 0.9;
        }
        .copy-icon ha-svg-icon {
            --mdc-icon-size: 12px;
        }
        .copy-flash {
            position: absolute;
            top: 7px;
            right: 34px;
            z-index: 2;
            font-size: 0.72rem;
            white-space: nowrap;
            color: var(--secondary-text-color);
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 1px 6px;
            pointer-events: none;
        }
        input[type="text"]:focus,
        textarea:focus {
            outline: none;
            border-color: #b87333;
        }
        .tx-knobs {
            display: flex;
            gap: 16px;
        }
        .knob {
            display: flex;
            flex-direction: column;
        }
        input.num-input {
            width: 80px;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        input.num-input:focus {
            outline: none;
            border-color: #b87333;
        }
        input.num-input:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .observed-hint {
            margin: -4px 0 12px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        /* Replace this code. A divider above it rather than a box
           around it: it is a second way to fill the field above, not a
           separate thing the dialog does. */
        .replace {
            margin: 10px 0 4px;
            padding-top: 10px;
            border-top: 1px solid var(--divider-color);
        }
        .replace-head {
            font-size: 0.78rem;
            font-weight: 500;
            letter-spacing: 0.02em;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        .replace-row {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .replace-status {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            line-height: 1.3;
        }
        .listen-btn {
            flex: 0 0 auto;
        }
        /* Amber, not red: this is a notice about the capture, not a
           refusal of it. The code is already in the box. */
        .repeat-notice {
            margin-top: 8px;
            font-size: 0.78rem;
            line-height: 1.35;
            color: #ffc107;
        }
        /* Listening is a state, not an action in progress, so it holds
           rather than pulses: the button stays pressed-looking until a
           code lands or the window times out. */
        .listen-btn.on {
            border-color: var(--primary-color);
            color: var(--primary-color);
            background: rgba(255, 255, 255, 0.06);
        }
        .pill-row {
            display: flex;
            align-items: center;
            margin: 2px 0 10px;
        }
        .hint {
            margin-top: 6px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        @keyframes snap-flash {
            0% {
                border-color: #ff9800;
                background: rgba(255, 152, 0, 0.18);
            }
            100% {
                border-color: var(--divider-color);
                background: var(--card-background-color);
            }
        }
        textarea.snap-flash {
            animation: snap-flash 700ms ease-out;
        }
        .snap-notice {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 4px 0 12px;
            padding: 10px 12px;
            border-radius: 6px;
            background: rgba(255, 152, 0, 0.1);
            border: 1px solid rgba(255, 152, 0, 0.35);
        }
        .snap-text {
            flex: 1;
            font-size: 0.8rem;
            line-height: 1.3;
            color: #b26500;
        }
        .snap-btn {
            flex-shrink: 0;
            background: none;
            border: 1px solid #e65100;
            color: #e65100;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 0.8rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .snap-btn:hover:not(:disabled) {
            background: rgba(255, 152, 0, 0.12);
        }
        .snap-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .feedback {
            margin: 4px 0 12px;
            padding: 10px 12px;
            border-radius: 6px;
            background: var(--secondary-background-color);
        }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            font-weight: 500;
        }
        .status .mark {
            font-size: 1rem;
        }
        .status.ok {
            color: #2e7d32;
        }
        .status.bad {
            color: #e65100;
        }
        .metrics {
            display: flex;
            gap: 14px;
            margin-top: 6px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
        }
        .recognized {
            color: #2e7d32;
        }
        .diamonds {
            display: flex;
            flex-wrap: wrap;
            gap: 1px;
            margin-top: 8px;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .msg {
            margin-top: 6px;
            font-size: 0.8rem;
        }
        .msg.err {
            color: #e65100;
        }
        .msg.warn {
            color: #b89930;
        }
        .note {
            margin: 4px 0 12px;
            padding: 8px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            background: var(--secondary-background-color);
        }
        /* Left-aligned actions row (a spacer pushes the main buttons
           right so Delete can sit flush left); ships this way. */
        .dialog-actions {
            align-items: center;
            justify-content: flex-start;
        }
        .spacer {
            flex: 1;
        }
        .copy-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .copy-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .create-btn {
            background: #b87333;
            color: #fff;
            border-color: #b87333;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
        /* GREEN IN A REPAIR (owner ruled 2026-09-03). Copper is this
           dialog's create color everywhere else. On a repair the button
           is the yes at the end of a fix, and green is already this
           panel's word for that: the settled row, the closing line, and
           HEARD on the button sharing this footer. */
        .create-btn.tangle {
            background: #2e7d32;
            border-color: #2e7d32;
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-signal-editor": IrSignalEditor;
    }
}
