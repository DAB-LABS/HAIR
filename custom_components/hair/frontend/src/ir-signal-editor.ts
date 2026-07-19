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
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { ProntoValidation, UnknownSignal } from "./types.js";

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

    private _debounce: ReturnType<typeof setTimeout> | null = null;

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
            this._ditto !== this.initialDitto
        );
    }

    private get _canSave(): boolean {
        if (this._busy || this._validation?.valid !== true) return false;
        return this._isEdit ? this._dirty : true;
    }

    /**
     * The Ditto count input is meaningful only when transmit will take the
     * decoded (NEC) path. Generic across decoded protocols, not NEC-specific.
     */
    private get _dittoCountDisabled(): boolean {
        // Signal-edit / create mode: gate on the live-validated decoded form.
        if (!this._isCommand) {
            if (!this._pronto.trim()) return true;
            if (this._validation === null) return true;
            if (!this._validation.recognized_protocol) return true;
            return false;
        }
        // Command-edit mode: gate on the command's stored decoded form AND
        // honor the per-command PRONTO toggle. Ditto only fires when TX takes
        // the decoded path (build_decoded_command); a command with
        // tx_force_raw=True goes through build_command and the dittos do not
        // fire on the wire.
        if (!this.initialDecodedProtocol) return true;
        if (this.initialTxForceRaw) return true;
        return false;
    }

    /** Tooltip for the disabled Ditto count input, by reason. */
    private get _dittoDisabledTooltip(): string {
        if (
            this._isCommand &&
            this.initialDecodedProtocol &&
            this.initialTxForceRaw
        ) {
            return "Ditto count applies when the command transmits as NEC. Toggle the pill to NEC to enable.";
        }
        return "Ditto count applies to decoded signals (NEC today). Raw Pronto codes transmit as captured.";
    }

    firstUpdated(): void {
        // Properties bound by the parent are set by first render; seed the
        // editable copies and validate a pre-filled code immediately.
        this._pronto = this.initialPronto;
        this._alias = this.initialAlias;
        this._sendCount = this.initialSendCount;
        this._ditto = this.initialDitto;
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

    private _onProntoInput(e: Event): void {
        this._pronto = (e.target as HTMLTextAreaElement).value;
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

    private async _save(): Promise<void> {
        if (!this._canSave) return;
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
        this._copyHint = copied ? "Copied" : "Press Cmd/Ctrl+C";
        setTimeout(() => {
            this._copyHint = null;
        }, 2000);
    }

    private _renderFeedback() {
        const v = this._validation;
        if (!v) return "";
        const sl = this._slPreview();
        return html`
            <div class="feedback">
                <div class="status ${v.valid ? "ok" : "bad"}">
                    <span class="mark">${v.valid ? "✓" : "✗"}</span>
                    ${v.valid ? "Valid Pronto code" : "Not valid yet"}
                </div>
                ${v.valid
                    ? html`
                          <div class="metrics">
                              ${v.frequency_khz !== null
                                  ? html`<span>${v.frequency_khz} kHz</span>`
                                  : ""}
                              ${v.burst_pair_count !== null
                                  ? html`<span
                                        >${v.burst_pair_count} burst
                                        ${v.burst_pair_count === 1 ? "pair" : "pairs"}</span
                                    >`
                                  : ""}
                              ${v.recognized_protocol
                                  ? html`<span class="recognized"
                                        >Recognized as ${v.recognized_protocol}</span
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
                    Carrier is ${curKhz} kHz, off the IR standards. Some
                    receivers reject it.
                </div>
                <button
                    class="snap-btn"
                    ?disabled=${this._snapping}
                    @click=${() => this._snap(target)}
                >
                    ${this._snapping ? "Snapping..." : `Snap to ${tgtKhz} kHz`}
                </button>
            </div>
        `;
    }

    render() {
        const heading = this._isCommand
            ? "Edit command"
            : this._isEdit
              ? "Edit signal"
              : "Create signal";
        const primaryLabel = this._isEdit
            ? this._busy
                ? "Saving..."
                : "Save"
            : this._busy
              ? "Creating..."
              : "Create";
        const showTriggerNote =
            this._isEdit && this.hasTrigger && this._dirty;
        const triggerNoteText = this._isCommand
            ? "This command has a trigger that will automatically re-point."
            : "This signal has a trigger that will automatically re-point.";
        const nameLabel = this._isCommand
            ? "Command name"
            : `Alias${this._isEdit ? "" : " (optional)"}`;
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

                <div class="field">
                    <label>Pronto code</label>
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
                                      title="Select all (then Cmd/Ctrl+C)"
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

                ${this._renderFeedback()} ${this._renderSnap()}

                <div class="field">
                    <label>${nameLabel}</label>
                    <input
                        type="text"
                        .value=${this._alias}
                        placeholder="e.g. Power"
                        @input=${(e: Event) =>
                            (this._alias = (e.target as HTMLInputElement).value)}
                        @keydown=${this._onKeydown}
                    />
                </div>

                <div class="field tx-knobs">
                    <div class="knob">
                        <label>Send times</label>
                        <input
                            class="num-input"
                            type="number"
                            min="1"
                            max="10"
                            .value=${String(this._sendCount)}
                            title="Transmit the whole command this many times as independent presses, for devices that need a repeat to register."
                            @input=${this._onSendCountInput}
                            @keydown=${this._onKeydown}
                        />
                    </div>
                    ${this._dittoCountDisabled
                        ? ""
                        : html`<div class="knob">
                              <label>Ditto count</label>
                              <input
                                  class="num-input"
                                  type="number"
                                  min="0"
                                  max="20"
                                  .value=${String(this._ditto)}
                                  title='Append repeat frames after the main frame. Some strict receivers, notably commercial audio gear, need at least one to register the command.'
                                  @input=${this._onDittoInput}
                                  @keydown=${this._onKeydown}
                              />
                          </div>`}
                </div>
                ${this.initialObservedRepeatCount > 0
                    ? html`<div class="observed-hint">
                          Observed at capture:
                          ${this.initialObservedRepeatCount}
                          ${this.initialObservedRepeatCount === 1
                              ? "ditto"
                              : "dittos"}
                      </div>`
                    : ""}

                ${showTriggerNote
                    ? html`<div class="note">${triggerNoteText}</div>`
                    : ""}

                <div class="dialog-actions">
                    <span class="spacer"></span>
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        Cancel
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._save}
                        ?disabled=${!this._canSave}
                    >
                        ${primaryLabel}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
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
