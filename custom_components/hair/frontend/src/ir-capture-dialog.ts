/**
 * 2-phase IR capture dialog.
 *
 * Phase 1 — Listening: subscribes to `hair/capture/start` events,
 * shows a pulsing indicator and countdown timer.
 *
 * Phase 2 — Captured: shows protocol info, lets the user Test the
 * command (sends the captured signal back through the emitter), then
 * Save (advances the parent's command queue) or Re-capture.
 *
 * Errors and duplicate detection render inline in the same dialog.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { HairApi } from "./api.js";
import type { CaptureEvent, CaptureResult, IRDevice } from "./types.js";

type Phase = "listening" | "captured" | "timeout" | "error" | "duplicate";

@customElement("ir-capture-dialog")
export class IrCaptureDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public device!: IRDevice;
    @property({ attribute: false }) public commandName: string = "";
    @property({ attribute: false }) public timeout: number = 15;

    @state() private _phase: Phase = "listening";
    @state() private _result: CaptureResult | null = null;
    @state() private _duplicate: { id: string; name: string } | null = null;
    @state() private _error: string | null = null;
    @state() private _timeRemaining: number = 0;
    @state() private _sessionId: string | null = null;

    private _unsubscribe: (() => Promise<void>) | null = null;
    private _countdown: number | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        void this._beginCapture();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._stopCountdown();
        if (this._unsubscribe) {
            void this._unsubscribe();
            this._unsubscribe = null;
        }
    }

    private async _beginCapture() {
        this._phase = "listening";
        this._result = null;
        this._duplicate = null;
        this._error = null;
        this._timeRemaining = this.timeout;
        this._startCountdown();

        try {
            const { session, unsubscribe } = await this.api.startCapture(
                this.device.id,
                this.timeout,
                (event) => this._onCaptureEvent(event),
            );
            this._sessionId = session.session_id;
            this._unsubscribe = unsubscribe;
        } catch (err) {
            this._stopCountdown();
            this._error = (err as Error).message;
            this._phase = "error";
        }
    }

    private _onCaptureEvent(event: CaptureEvent) {
        switch (event.type) {
            case "capture_listening":
                this._phase = "listening";
                break;
            case "capture_received":
                this._stopCountdown();
                this._result = event.result;
                if (event.duplicate_of) {
                    this._duplicate = event.duplicate_of;
                    this._phase = "duplicate";
                } else {
                    this._phase = "captured";
                }
                break;
            case "capture_timeout":
                this._stopCountdown();
                this._phase = "timeout";
                break;
            case "capture_error":
                this._stopCountdown();
                this._error = event.error;
                this._phase = "error";
                break;
            case "capture_cancelled":
                this._stopCountdown();
                this._close();
                break;
        }
    }

    private _startCountdown() {
        this._stopCountdown();
        const start = Date.now();
        this._countdown = window.setInterval(() => {
            const elapsed = (Date.now() - start) / 1000;
            this._timeRemaining = Math.max(0, Math.ceil(this.timeout - elapsed));
            if (this._timeRemaining <= 0) {
                this._stopCountdown();
            }
        }, 250);
    }

    private _stopCountdown() {
        if (this._countdown !== null) {
            clearInterval(this._countdown);
            this._countdown = null;
        }
    }

    private async _cancel() {
        if (this._sessionId) {
            try {
                await this.api.cancelCapture(this._sessionId);
            } catch {
                /* ignore */
            }
        }
        this._close();
    }

    private async _testCommand() {
        if (!this._sessionId) return;
        // Save into a temporary "_test_" slot, send, then delete it.
        const tempName = `__hair_test_${Date.now()}`;
        try {
            const saved = await this.api.saveCapturedCommand({
                device_id: this.device.id,
                session_id: this._sessionId,
                command_name: tempName,
            });
            await this.api.sendCommand(this.device.id, saved.id);
            await this.api.deleteCommand(this.device.id, saved.id);
        } catch (err) {
            this._error = (err as Error).message;
            this._phase = "error";
        }
    }

    private async _save(saveAndNext: boolean) {
        if (!this._sessionId) return;
        try {
            await this.api.saveCapturedCommand({
                device_id: this.device.id,
                session_id: this._sessionId,
                command_name: this.commandName,
            });
            this.dispatchEvent(
                new CustomEvent("command-saved", {
                    detail: { saveAndNext, commandName: this.commandName },
                    bubbles: true,
                    composed: true,
                }),
            );
            this._close();
        } catch (err) {
            this._error = (err as Error).message;
            this._phase = "error";
        }
    }

    private async _recapture() {
        if (this._unsubscribe) {
            await this._unsubscribe();
            this._unsubscribe = null;
        }
        await this._beginCapture();
    }

    private _close() {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _renderListening() {
        return html`
            <div class="phase listening" aria-live="polite">
                <div class="pulse" aria-hidden="true">
                    <span></span><span></span><span></span>
                </div>
                <div class="title">${t("capture.listening")}</div>
                <div class="instruction">
                    ${t("capture.instruction", { name: this.commandName })}
                </div>
                <div class="countdown">
                    ${t("capture.remaining", { seconds: this._timeRemaining })}
                </div>
                <div class="actions">
                    <mwc-button @click=${this._cancel}>${t("common.cancel")}</mwc-button>
                </div>
            </div>
        `;
    }

    private _renderCaptured() {
        const result = this._result!;
        return html`
            <div class="phase captured" aria-live="polite">
                <div class="check" aria-hidden="true">✓</div>
                <div class="title">${t("capture.captured")}</div>
                <div class="meta">
                    ${t("capture.protocol", { protocol: result.protocol ?? t("capture.protocol_raw") })}${result.code
                        ? html` · <code>${result.code}</code>`
                        : ""}
                </div>
                <ha-alert alert-type="info">
                    ${t("capture.verify")}
                </ha-alert>
                <div class="actions">
                    <mwc-button @click=${this._testCommand}>${t("capture.test")}</mwc-button>
                    <mwc-button @click=${this._recapture}>${t("capture.recapture")}</mwc-button>
                    <mwc-button raised @click=${() => this._save(true)}>
                        ${t("capture.save_next")}
                    </mwc-button>
                </div>
            </div>
        `;
    }

    private _renderTimeout() {
        return html`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">${t("capture.no_signal")}</div>
                <ul class="tips">
                    <li>${t("capture.tip_point")}</li>
                    <li>${t("capture.tip_closer")}</li>
                    <li>${t("capture.tip_hold")}</li>
                </ul>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>${t("capture.try_again")}</mwc-button>
                    <mwc-button @click=${this._cancel}>${t("common.cancel")}</mwc-button>
                </div>
            </div>
        `;
    }

    private _renderDuplicate() {
        const result = this._result!;
        return html`
            <div class="phase warning" aria-live="assertive">
                <div class="title warn">${t("capture.duplicate")}</div>
                <div class="instruction">
                    ${t("capture.duplicate_instruction", { name: this._duplicate!.name })}
                </div>
                <div class="meta">
                    ${t("capture.protocol", { protocol: result.protocol ?? t("capture.protocol_raw") })}
                </div>
                <div class="actions">
                    <mwc-button @click=${this._recapture}>
                        ${t("capture.recapture_different")}
                    </mwc-button>
                    <mwc-button raised @click=${() => this._save(true)}>
                        ${t("capture.save_anyway")}
                    </mwc-button>
                </div>
            </div>
        `;
    }

    private _renderError() {
        return html`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">${t("capture.error")}</div>
                <div class="instruction">${this._error}</div>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>
                        ${t("capture.try_again")}
                    </mwc-button>
                    <mwc-button @click=${this._cancel}>${t("common.cancel")}</mwc-button>
                </div>
            </div>
        `;
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${t("capture.learning", { name: this.commandName })}
                @closed=${this._cancel}
            >
                ${this._phase === "listening"
                    ? this._renderListening()
                    : this._phase === "captured"
                      ? this._renderCaptured()
                      : this._phase === "timeout"
                        ? this._renderTimeout()
                        : this._phase === "duplicate"
                          ? this._renderDuplicate()
                          : this._renderError()}
            </ha-dialog>
        `;
    }

    static styles = css`
        .phase {
            min-width: 320px;
            padding: 8px 0;
        }
        .title {
            font-size: 1.1rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .title.warn {
            color: var(--warning-color, #ffa600);
        }
        .instruction {
            color: var(--primary-text-color);
            margin-bottom: 8px;
        }
        .meta {
            color: var(--secondary-text-color);
            font-size: 0.85rem;
            margin-bottom: 8px;
        }
        .countdown {
            margin: 10px 0;
            font-variant-numeric: tabular-nums;
            color: var(--secondary-text-color);
        }
        .check {
            font-size: 3rem;
            color: var(--success-color, #43a047);
            text-align: center;
            margin: 8px 0;
        }
        .pulse {
            display: flex;
            justify-content: center;
            gap: 6px;
            margin: 8px 0 16px;
        }
        .pulse span {
            display: inline-block;
            width: 12px;
            height: 12px;
            background: var(--primary-color);
            border-radius: 50%;
            opacity: 0.4;
            animation: pulse 1s infinite ease-in-out;
        }
        .pulse span:nth-child(2) {
            animation-delay: 0.2s;
        }
        .pulse span:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes pulse {
            0%,
            100% {
                opacity: 0.3;
                transform: scale(0.85);
            }
            50% {
                opacity: 1;
                transform: scale(1.1);
            }
        }
        .actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
        .tips {
            margin: 4px 0 12px;
            padding-left: 22px;
            color: var(--primary-text-color);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-capture-dialog": IrCaptureDialog;
    }
}
