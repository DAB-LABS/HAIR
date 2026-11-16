/**
 * The radio code editor (RF send round, T3; plan 6.3).
 *
 * A radio row is edited the way an infrared one is, with radio details
 * where the infrared editor has Pronto ones. It opens on the row's code
 * as a Flipper `.sub` (the text its corner copy icon hands out), and takes a paste
 * in any of the three shapes the server reads: a `.sub`, a list of
 * signed timings, or a Broadlink RF base64 code. The paste is read live
 * (`hair/rf/validate`): how many frames were found and how many agree,
 * or why it is not a radio code.
 *
 * Under it, the frequency: the two common bands as one click, any other
 * typed in MHz, and where the value came from (the signal itself, the
 * receiver, assumed from a band, or set here). A row with no frequency
 * is not sent until one is set here; this field is the user's step of
 * the frequency ladder (go-rf-send-beta.md, decision 5). Then Send N
 * times. No snap, no ditto, no spacing: those are infrared settings.
 *
 * With neither a signal nor a command it CREATES (T6): the Clipper's
 * "Add radio code" opens it empty on a clipped remote, and Save adds the
 * paste as a new row (`signal-created`).
 *
 * A separate dialog from ir-signal-editor rather than a mode inside it:
 * that editor's Pronto, snap, ditto and repair paths do not apply to a
 * radio frame, and a second code path inside them would be easy to
 * break from either side. The callers open this one for a radio row,
 * and it fires the same events (`command-edited`, `signal-edited`).
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import { codeBoxStyles, diamondStyles, feedbackStyles, fitCodeBox } from "./ir-code-box-styles.js";
import { sendRefusal } from "./rf-errors.js";
import { sendTimesHint } from "./rf-send-count.js";
import { EMBER_VAR } from "./ir-header-chip-styles.js";
import {
    RF_PRESETS_HZ,
    hzToMhz,
    mhzToHz,
    pasteRefusalKey,
    presetOf,
    sourceKey,
    toSub,
    withSubFrequency,
} from "./rf-code.js";
import type { HairApi } from "./api.js";
import type { RfValidation } from "./types.js";
import "./ir-protocol-chip.js";
import { familyEditorText, type RfFamily } from "./rf-family-label.js";

const VALIDATE_DELAY_MS = 300;

// mdi:content-copy, the infrared code window's corner copy icon (N17).
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";
const MAX_SEND_COUNT = 10;

@customElement("ir-rf-editor")
export class IrRfEditor extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    /** A Sniffer or Mirror row; or */
    @property({ attribute: false }) public signalId: string | null = null;
    /** a device command. */
    @property({ attribute: false }) public commandId: string | null = null;
    @property({ attribute: false }) public initialFrame: number[] = [];
    @property({ attribute: false }) public initialFrequencyHz: number | null = null;
    @property({ attribute: false }) public initialFrequencySource: string | null = null;
    @property({ attribute: false }) public initialGapUs: number | null = null;
    @property({ attribute: false }) public initialAlias = "";
    @property({ attribute: false }) public initialSendCount = 1;
    /** How many agreeing frames the press carried, for the line under
     *  the count (N20); null for a paste or an unmeasured press. */
    @property({ attribute: false }) public repeatsObserved: number | null = null;
    @property({ type: Boolean }) public hasTrigger = false;
    /** The saved row's family (`rf_family`), for the pill row; null for
     *  a paste, a new code or a frame no shown family reads. */
    @property({ attribute: false }) public initialFamily: RfFamily | null = null;

    @state() private _code = "";
    @state() private _alias = "";
    @state() private _sendCount = 1;
    @state() private _frequencyHz: number | null = null;
    @state() private _frequencySource: string | null = null;
    @state() private _frequencyChanged = false;
    @state() private _typed = "";
    @state() private _validation: RfValidation | null = null;
    @state() private _validating = false;
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _copyHint: string | null = null;

    private _initialCode = "";
    /** What the saved code read as when the dialog opened, so the strip
     *  comes back as it was when an edit is undone. */
    private _initialValidation: RfValidation | null = null;
    private _timer: ReturnType<typeof setTimeout> | null = null;
    private _asked = 0;

    connectedCallback(): void {
        super.connectedCallback();
        // A new code opens empty; an existing row opens on its .sub.
        this._initialCode = this._creating
            ? ""
            : toSub(this.initialFrame, this.initialFrequencyHz, this.initialGapUs);
        this._code = this._initialCode;
        this._alias = this.initialAlias;
        this._sendCount = Math.max(1, this.initialSendCount || 1);
        this._frequencyHz = this.initialFrequencyHz;
        this._frequencySource = this.initialFrequencySource;
        this._typed =
            this._frequencyHz && presetOf(this._frequencyHz) === null ? hzToMhz(this._frequencyHz) : "";
    }

    /** The strip is always shown, as the infrared editor's is: the saved
     *  code is read once when the dialog opens. */
    firstUpdated(): void {
        if (!this._creating && this._code.trim()) {
            this._validating = true;
            void this._validate();
        }
    }

    /** The box fits its code, as the infrared box does: 64 px up to 45%
     *  of the viewport, then it scrolls below the copy icon's strip. */
    updated(): void {
        const ta = this.shadowRoot?.querySelector<HTMLTextAreaElement>("textarea");
        if (ta) fitCodeBox(ta, 64, Math.round(window.innerHeight * 0.45));
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        if (this._timer !== null) clearTimeout(this._timer);
    }

    /** No row yet: a new radio code on a clipped remote (T6). */
    private get _creating(): boolean {
        return this.signalId === null && this.commandId === null;
    }

    private get _codeChanged(): boolean {
        return this._code.trim() !== this._initialCode.trim();
    }

    private _onCode(e: Event): void {
        this._code = (e.target as HTMLTextAreaElement).value;
        this._validation = null;
        if (this._timer !== null) clearTimeout(this._timer);
        // Any read still in flight is for a code that is no longer in the
        // box, the open-read included.
        this._asked++;
        if (!this._codeChanged) {
            // Back to the saved code: its own reading, as it opened, or a
            // fresh one if the open-read had not come back yet.
            if (this._initialValidation) {
                this._validating = false;
                this._validation = this._initialValidation;
            } else {
                this._validating = true;
                void this._validate();
            }
            return;
        }
        this._validating = true;
        this._timer = setTimeout(() => void this._validate(), VALIDATE_DELAY_MS);
    }

    private async _validate(): Promise<void> {
        const asked = ++this._asked;
        try {
            const result = await this.api.rfValidate(
                this._code,
                this._frequencyChanged ? this._frequencyHz : null,
            );
            if (asked !== this._asked) return;
            this._validation = result;
            if (!this._codeChanged) {
                // The saved code, read on open: nothing to bring over, its
                // frequency and where it came from are the row's own.
                this._initialValidation = result;
                return;
            }
            // A paste that says its own frequency brings it, unless the
            // user has set one here.
            if (result.ok && result.frequency_hz && !this._frequencyChanged) {
                this._frequencyHz = result.frequency_hz;
                this._frequencySource = result.frequency_source ?? null;
                this._typed = presetOf(this._frequencyHz) === null ? hzToMhz(this._frequencyHz) : "";
            }
        } catch (err) {
            if (asked !== this._asked) return;
            this._validation = { ok: false, code: (err as { code?: string }).code ?? "rf_paste_unreadable" };
        } finally {
            if (asked === this._asked) this._validating = false;
        }
    }

    private _pick(hz: number): void {
        this._frequencyHz = hz;
        this._frequencySource = "user";
        this._frequencyChanged = true;
        this._typed = "";
        this._codeFollows(hz);
    }

    private _onTyped(e: Event): void {
        this._typed = (e.target as HTMLInputElement).value;
        const hz = mhzToHz(this._typed);
        if (hz !== null) {
            this._frequencyHz = hz;
            this._frequencySource = "user";
            this._frequencyChanged = true;
            this._codeFollows(hz);
        }
    }

    /** The Code box follows the frequency buttons (N15): a .sub's
     *  Frequency line becomes the band picked here. The row's own .sub
     *  stays "unchanged", so Save sends only the frequency; a pasted
     *  .sub is read again so the paste and the band agree. */
    private _codeFollows(hz: number): void {
        const code = withSubFrequency(this._code, hz);
        if (code === this._code) return;
        const pasted = this._codeChanged;
        this._code = code;
        if (!pasted) {
            this._initialCode = withSubFrequency(this._initialCode, hz);
            // The strip follows the band too: the saved code's reading,
            // with the new frequency. A read still in flight was for the
            // old one, so it is asked again.
            if (this._validating) {
                this._asked++;
                void this._validate();
            } else {
                if (this._validation?.ok) this._validation = { ...this._validation, frequency_hz: hz };
                if (this._initialValidation?.ok) {
                    this._initialValidation = { ...this._initialValidation, frequency_hz: hz };
                }
            }
            return;
        }
        this._asked++;
        this._validation = null;
        this._validating = true;
        if (this._timer !== null) clearTimeout(this._timer);
        this._timer = setTimeout(() => void this._validate(), VALIDATE_DELAY_MS);
    }

    private get _typedInvalid(): boolean {
        return this._typed.trim() !== "" && mhzToHz(this._typed) === null;
    }

    private get _canSave(): boolean {
        if (this._busy || this._validating || this._typedInvalid) return false;
        if (this._codeChanged && !this._validation?.ok) return false;
        if (this._creating && !this._codeChanged) return false;
        return true;
    }

    /** The corner copy icon, as the infrared code window has it (N17):
     *  selects the code and copies the .sub, Frequency line and all.
     *  Without a clipboard (an insecure origin) the selection stands and
     *  the hint says to press copy. */
    private async _copy(): Promise<void> {
        const text = this._codeChanged && this._validation?.ok && this._validation.sub_text
            ? this._validation.sub_text
            : this._code;
        const ta = this.shadowRoot?.querySelector("textarea");
        if (ta) {
            ta.focus();
            ta.select();
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
        setTimeout(() => (this._copyHint = null), 2000);
    }

    /** Delete, where Copy .sub was (N17): the host closes the editor and
     *  opens the confirmation the row's own trash glyph opens. */
    private _requestDelete(): void {
        this.dispatchEvent(new CustomEvent("delete-requested"));
    }

    private async _save(): Promise<void> {
        if (!this._canSave) return;
        this._busy = true;
        this._error = null;
        const rfCode = this._codeChanged ? this._code : undefined;
        const rfFrequency = this._frequencyChanged && this._frequencyHz ? this._frequencyHz : undefined;
        try {
            if (this.commandId !== null) {
                const result = await this.api.updateCommand({
                    device_id: this.deviceId,
                    command_id: this.commandId,
                    ...(this._alias.trim() && this._alias.trim() !== this.initialAlias
                        ? { name: this._alias.trim() }
                        : {}),
                    ...(rfCode !== undefined ? { rf_code: rfCode } : {}),
                    ...(rfFrequency !== undefined ? { rf_frequency_hz: rfFrequency } : {}),
                    send_count: this._sendCount,
                });
                this._fire("command-edited", result);
            } else if (this._creating) {
                const result = await this.api.createRfSignal({
                    device_id: this.deviceId,
                    rf_code: this._code,
                    ...(rfFrequency !== undefined ? { rf_frequency_hz: rfFrequency } : {}),
                    alias: this._alias.trim(),
                    send_count: this._sendCount,
                });
                this._fire("signal-created", result);
            } else if (this.signalId !== null) {
                const result = await this.api.editRfSignal({
                    device_id: this.deviceId,
                    signal_id: this.signalId,
                    alias: this._alias.trim(),
                    send_count: this._sendCount,
                    ...(rfCode !== undefined ? { rf_code: rfCode } : {}),
                    ...(rfFrequency !== undefined ? { rf_frequency_hz: rfFrequency } : {}),
                });
                this._fire("signal-edited", result);
            }
        } catch (err) {
            const code = (err as { code?: string }).code;
            const key = pasteRefusalKey(code);
            this._error =
                (key ? t(key) : null) ??
                (code === "duplicate_signal" ? t("rfedit.duplicate") : null) ??
                sendRefusal(err) ??
                (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private _fire(name: string, detail: unknown): void {
        this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
    }

    private _close(): void {
        this._fire("closed", null);
    }

    /** The strip under the box, as the infrared editor's (owner,
     *  2026-11-15): always shown once there is a code, the saved one read
     *  on open. Valid: the check mark, "Valid radio code", then one line
     *  with the code's frequency, how many frames agree and its identity
     *  (the family pill and its fields), then the diamonds. Refused: the
     *  reason, in place of all of that. */
    private _renderFeedback() {
        if (this._validating) {
            return html`<div class="feedback"><div class="metrics">${t("rfedit.reading")}</div></div>`;
        }
        const v = this._validation;
        if (!v) return nothing;
        if (!v.ok) {
            const key = pasteRefusalKey(v.code);
            return html`<div class="feedback" role="alert">
                <div class="status bad"><span class="mark">✗</span>${t("editor.not_valid")}</div>
                <div class="msg err">${key ? t(key) : (v.error ?? "")}</div>
            </div>`;
        }
        const found = v.frames_found ?? 1;
        const agreeing = v.frames_agreeing ?? 1;
        return html`<div class="feedback">
            <div class="status ok"><span class="mark">✓</span>${t("rfedit.valid")}</div>
            <div class="metrics">
                ${v.frequency_hz ? html`<span>${t("rfedit.mhz", { mhz: hzToMhz(v.frequency_hz) })}</span>` : nothing}
                <span
                    >${found <= 1
                        ? t("rfedit.one_frame")
                        : t("rfedit.frames_agree", { agreeing: String(agreeing), found: String(found) })}</span
                >
                ${this._renderFamily()}
            </div>
            ${v.sl_pattern
                ? html`<div class="diamonds">
                      ${[...v.sl_pattern].map((c) =>
                          c === "L"
                              ? html`<span class="diamond long">◆</span>`
                              : html`<span class="diamond short">◇</span>`,
                      )}
                  </div>`
                : nothing}
        </div>`;
    }

    private _renderFrequency() {
        const preset = presetOf(this._frequencyHz);
        const source = sourceKey(this._frequencySource);
        return html`<div class="field">
            <label id="freq-label">${t("rfedit.frequency")}</label>
            <div class="freq-row" role="group" aria-labelledby="freq-label">
                ${RF_PRESETS_HZ.map(
                    (hz) => html`<button
                        class="preset ${preset === hz ? "on" : ""}"
                        aria-pressed=${preset === hz ? "true" : "false"}
                        @click=${() => this._pick(hz)}
                    >
                        ${t("rfedit.mhz", { mhz: hzToMhz(hz) })}
                    </button>`,
                )}
                <span class="other">
                    <input
                        type="text"
                        inputmode="decimal"
                        class=${this._typedInvalid ? "invalid" : ""}
                        placeholder=${t("rfedit.other_mhz")}
                        aria-label=${t("rfedit.other_mhz")}
                        .value=${this._typed}
                        @input=${this._onTyped}
                    />
                    <span class="unit">MHz</span>
                </span>
            </div>
            <div class="freq-note ${this._frequencyHz ? "" : "missing"}">
                ${this._typedInvalid
                    ? t("rfedit.frequency_invalid")
                    : this._frequencyHz
                      ? source
                          ? t(source)
                          : ""
                      : t("rfedit.frequency_missing")}
            </div>
        </div>`;
    }

    /** The line under the count (N20): what one press carried, or the
     *  usual count when it was not measured, while the field holds it. */
    private _countHint() {
        const hint = sendTimesHint("rf", this.repeatsObserved, this._sendCount);
        return hint
            ? html`<div class="count-hint">${t(hint.key, { count: String(hint.count) })}</div>`
            : nothing;
    }

    /** The code's identity, inside the strip's info line (owner,
     *  2026-11-16, at #274's look: once, in the box, as the infrared
     *  editor shows it): the family's pill, then its fields as plain
     *  text. Read-only. It describes the saved code, so it goes as soon
     *  as the code in the box changes. */
    private _renderFamily() {
        if (this._creating || this._codeChanged || !this.initialFamily) return nothing;
        return html`<span class="identity">
            <ir-protocol-chip .family=${this.initialFamily}></ir-protocol-chip>
            <span class="family-fields">${familyEditorText(this.initialFamily)}</span>
        </span>`;
    }

    render() {
        const heading = this._creating
            ? t("rfedit.new_signal")
            : this.commandId !== null
              ? t("rfedit.edit_command")
              : t("rfedit.edit_signal");
        return html`<ha-dialog open heading=${heading} scrimClickAction="" @closed=${this._close}>
            ${this._error ? html`<ha-alert alert-type="error">${this._error}</ha-alert>` : nothing}
            <div class="field">
                <label for="rf-code">${t("rfedit.code")}</label>
                <div class="code-wrap">
                    <textarea
                        id="rf-code"
                        rows="4"
                        spellcheck="false"
                        placeholder=${t("rfedit.code_placeholder")}
                        .value=${this._code}
                        @input=${this._onCode}
                    ></textarea>
                    ${this._code.trim()
                        ? html`${this._copyHint
                                  ? html`<span class="copy-flash">${this._copyHint}</span>`
                                  : nothing}
                              <button
                                  class="copy-icon"
                                  title=${t("editor.select_all")}
                                  aria-label=${t("editor.select_all")}
                                  @click=${() => void this._copy()}
                              >
                                  <ha-svg-icon .path=${ICON_COPY}></ha-svg-icon>
                              </button>`
                        : nothing}
                </div>
                ${this._renderFeedback()}
            </div>

            ${this._renderFrequency()}

            <div class="field">
                <label for="rf-name">${this.commandId !== null ? t("assign.command_name") : t("editor.alias_label")}</label>
                <input
                    id="rf-name"
                    type="text"
                    .value=${this._alias}
                    @input=${(e: Event) => (this._alias = (e.target as HTMLInputElement).value)}
                />
            </div>

            <div class="field knob">
                <label for="rf-count">${t("assign.send_times")}</label>
                <input
                    id="rf-count"
                    class="num-input"
                    type="number"
                    min="1"
                    max=${MAX_SEND_COUNT}
                    .value=${String(this._sendCount)}
                    title=${t("rfedit.send_times_title")}
                    @input=${(e: Event) => {
                        const n = parseInt((e.target as HTMLInputElement).value, 10);
                        if (Number.isFinite(n)) this._sendCount = Math.min(MAX_SEND_COUNT, Math.max(1, n));
                    }}
                />
                ${this._countHint()}
            </div>

            ${this.hasTrigger && this._codeChanged
                ? html`<div class="note">${t("editor.trigger_note_sig")}</div>`
                : nothing}

            <div class="dialog-actions">
                ${this._creating
                    ? nothing
                    : html`<button
                          class="action-btn delete-btn"
                          @click=${this._requestDelete}
                          ?disabled=${this._busy}
                      >
                          ${t("common.delete")}
                      </button>`}
                <span class="actions-spacer"></span>
                <button class="action-btn cancel-btn" @click=${this._close} ?disabled=${this._busy}>
                    ${t("common.cancel")}
                </button>
                <button class="action-btn create-btn" @click=${() => void this._save()} ?disabled=${!this._canSave}>
                    ${this._busy ? t("common.saving") : t("common.save")}
                </button>
            </div>
        </ha-dialog>`;
    }

    static styles = [
        dialogStyles,
        codeBoxStyles,
        feedbackStyles,
        diamondStyles,
        css`
            .count-hint {
                margin-top: 6px;
                font-size: 0.78rem;
                color: var(--secondary-text-color);
            }
            .family-fields {
                font-family: var(--code-font-family, monospace);
                font-size: 0.78rem;
                color: var(--secondary-text-color);
                overflow-wrap: anywhere;
            }
            /* The code box, its copy icon, the strip and the diamonds are
               the infrared editor's (ir-code-box-styles.ts), loaded above. */
            /* Delete: outlined ember, as the other dialogs' Delete. */
            .delete-btn {
                background: none;
                border-color: ${EMBER_VAR};
                color: ${EMBER_VAR};
            }
            .delete-btn:hover:not(:disabled) {
                background: color-mix(in srgb, ${EMBER_VAR} 14%, transparent);
            }
            .freq-row {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 6px;
            }
            .preset {
                padding: 5px 12px;
                border-radius: 14px;
                border: 1px solid var(--divider-color);
                background: none;
                color: var(--primary-text-color);
                font: inherit;
                font-size: 0.85rem;
                cursor: pointer;
            }
            .preset.on {
                border-color: #03a9f4;
                background: color-mix(in srgb, #03a9f4 14%, transparent);
            }
            .other {
                display: inline-flex;
                align-items: center;
                gap: 4px;
            }
            .other input {
                width: 7.5em;
            }
            .other input.invalid {
                border-color: var(--error-color, #db4437);
            }
            .unit {
                font-size: 0.8rem;
                color: var(--secondary-text-color);
            }
            .freq-note {
                font-size: 0.75rem;
                color: var(--secondary-text-color);
                margin-top: 4px;
                min-height: 1em;
            }
            .freq-note.missing {
                color: var(--warning-color, #ffa600);
            }
            .num-input {
                width: 5em;
                padding: 6px 8px;
                border-radius: 4px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                color: var(--primary-text-color);
                font: inherit;
            }
            .note {
                font-size: 0.8rem;
                color: var(--secondary-text-color);
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
        "ir-rf-editor": IrRfEditor;
    }
}
