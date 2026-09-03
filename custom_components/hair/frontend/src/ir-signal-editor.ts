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
import type { ProntoValidation, RepeatVote, UnknownSignal } from "./types.js";
import { isDittoable } from "./ir-tx-knobs.js";

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

    /** Set once the apply door has refused an undeclared cross-reading
     * paste. The person is then offered the same ladder the LISTEN flow
     * offers: use it anyway, or go back. */
    @state() private _tangleLadder = false;

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
        const minPx = 64;
        const maxPx = Math.round(window.innerHeight * 0.45);
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
            const result = await this.api.tangleApply({
                deviceId: this.deviceId,
                target: this.tangleTarget as string,
                pronto: this._pronto,
                tested: true,
                // A paste is evidence of bytes, not of a transmission,
                // so zero is the true tally and the receipt reads
                // accepted rather than air-tested. Same value the
                // listen flow sends for the same reason.
                sendsFired: 0,
                source: "paste",
                ...(declared ? { readingDisagreed: true } : {}),
            });
            this.dispatchEvent(
                new CustomEvent("tangle-mutated", {
                    detail: { wigWritten: result.wig?.written ?? null },
                    bubbles: true,
                    composed: true,
                }),
            );
            this._close();
        } catch (err) {
            const message = (err as Error).message || String(err);
            if (message.includes("reading_disagreed_required")) {
                this._tangleLadder = true;
                this._error = t("tangles.listen_mismatch_3_noread");
            } else {
                this._error = message;
            }
        } finally {
            this._busy = false;
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
        const heading = this._isCommand
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
                ${this._isTangle && this.tangleReason
                    ? html`<div class="tangle-reason">
                          ${this.tangleReason}
                      </div>`
                    : ""}
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <div class="field">
                    <label>${t("editor.pronto_code")}</label>
                    <div class="code-wrap">
                        <textarea
                            class=${this._snapFlash ? "snap-flash" : ""}
                            rows="4"
                            .value=${this._pronto}
                            placeholder="0000 006D ..."
                            autofocus
                            spellcheck="false"
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
                                      <ha-svg-icon
                                          .path=${ICON_COPY}
                                      ></ha-svg-icon>
                                  </button>
                              `
                            : ""}
                    </div>
                </div>

                ${this._renderReplace()} ${this._renderFeedback()}
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

                <div class="dialog-actions">
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
                              @click=${() => void this._applyToTangle(true)}
                              ?disabled=${this._busy}
                          >
                              ${t("tangles.use_anyway")}
                          </button>`
                        : html`<button
                              class="action-btn create-btn"
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
            /* The row's own reason, leading the dialog so the person can
               see what they are fixing while they fix it. */
            .tangle-reason {
                font-size: 0.8rem;
                color: var(--secondary-text-color);
                margin-bottom: 10px;
                line-height: 1.4;
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
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-signal-editor": IrSignalEditor;
    }
}
