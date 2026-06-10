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
                <div class="title">Listening for IR signal…</div>
                <div class="instruction">
                    Point your remote at the IR receiver and press the
                    "${this.commandName}" button.
                </div>
                <div class="countdown">
                    ${this._timeRemaining}s remaining
                </div>
                <div class="actions">
                    <mwc-button @click=${this._cancel}>Cancel</mwc-button>
                </div>
            </div>
        `;
    }

    private _renderCaptured() {
        const result = this._result!;
        return html`
            <div class="phase captured" aria-live="polite">
                <div class="check" aria-hidden="true">✓</div>
                <div class="title">Signal Captured!</div>
                <div class="meta">
                    Protocol: ${result.protocol ?? "Raw"}${result.code
                        ? html` · <code>${result.code}</code>`
                        : ""}
                </div>
                <ha-alert alert-type="info">
                    Did it work? Press Test to verify.
                </ha-alert>
                <div class="actions">
                    <mwc-button @click=${this._testCommand}>▶ Test</mwc-button>
                    <mwc-button @click=${this._recapture}>↻ Re-capture</mwc-button>
                    <mwc-button raised @click=${() => this._save(true)}>
                        Save &amp; Learn Next ▶▶
                    </mwc-button>
                </div>
            </div>
        `;
    }

    private _renderTimeout() {
        return html`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">⚠ No signal detected</div>
                <ul class="tips">
                    <li>Point the remote directly at the IR receiver</li>
                    <li>Move closer (within 3 feet / 1 meter)</li>
                    <li>Press and hold the button briefly</li>
                </ul>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>↻ Try Again</mwc-button>
                    <mwc-button @click=${this._cancel}>Cancel</mwc-button>
                </div>
            </div>
        `;
    }

    private _renderDuplicate() {
        const result = this._result!;
        return html`
            <div class="phase warning" aria-live="assertive">
                <div class="title warn">⚠ Duplicate Signal Detected</div>
                <div class="instruction">
                    This matches your "${this._duplicate!.name}" command.
                    Some remotes use the same signal for multiple buttons.
                </div>
                <div class="meta">
                    Protocol: ${result.protocol ?? "Raw"}
                </div>
                <div class="actions">
                    <mwc-button @click=${this._recapture}>
                        Re-capture Different
                    </mwc-button>
                    <mwc-button raised @click=${() => this._save(true)}>
                        Save Anyway
                    </mwc-button>
                </div>
            </div>
        `;
    }

    private _renderError() {
        return html`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">⚠ Capture Error</div>
                <div class="instruction">${this._error}</div>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>
                        ↻ Try Again
                    </mwc-button>
                    <mwc-button @click=${this._cancel}>Cancel</mwc-button>
                </div>
            </div>
        `;
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${`Learning: "${this.commandName}"`}
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
