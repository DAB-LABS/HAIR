/**
 * HAIR admin panel — bundled output.
 *
 * This file is the compiled equivalent of frontend/src/*.ts. Lit is
 * imported from an ESM CDN so the panel works without a local build
 * step; run `npm run build` from the frontend/ directory to produce
 * a fully self-contained bundle.
 */
import { LitElement, html, css } from "https://esm.sh/lit@3.1.0?bundle";

/* -------------------------------------------------------------------------- */
/*  HairApi — WebSocket client                                                 */
/* -------------------------------------------------------------------------- */

class HairApi {
    constructor(hass) {
        this._hass = hass;
    }

    listDevices() {
        return this._hass.connection.sendMessagePromise({ type: "hair/devices" });
    }
    getDevice(deviceId) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/device",
            device_id: deviceId,
        });
    }
    createDevice(payload) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/device/create",
            ...payload,
        });
    }
    updateDevice(deviceId, patch) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/device/update",
            device_id: deviceId,
            ...patch,
        });
    }
    deleteDevice(deviceId) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/device/delete",
            device_id: deviceId,
        });
    }
    deleteCommand(deviceId, commandId) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/command/delete",
            device_id: deviceId,
            command_id: commandId,
        });
    }
    sendCommand(deviceId, commandId) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/command/send",
            device_id: deviceId,
            command_id: commandId,
        });
    }
    listTemplates(deviceType) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/templates",
            device_type: deviceType,
        });
    }
    listCaptureProviders() {
        return this._hass.connection.sendMessagePromise({
            type: "hair/capture/providers",
        });
    }
    cancelCapture(sessionId) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/capture/cancel",
            session_id: sessionId,
        });
    }
    saveCapturedCommand(payload) {
        return this._hass.connection.sendMessagePromise({
            type: "hair/capture/save",
            ...payload,
        });
    }

    async startCapture(deviceId, timeout, onEvent) {
        let session = null;
        const unsubscribe = await this._hass.connection.subscribeMessage(
            (message) => {
                if (message?.type?.startsWith?.("capture_")) {
                    onEvent(message);
                } else if (message?.session_id) {
                    session = message;
                }
            },
            { type: "hair/capture/start", device_id: deviceId, timeout },
        );
        await Promise.resolve();
        if (!session) throw new Error("Capture session did not start");
        return { session, unsubscribe };
    }
}

/* -------------------------------------------------------------------------- */
/*  Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEVICE_TYPE_ICONS = {
    tv: "M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",
    ac: "M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",
    fan: "M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",
    soundbar: "M16,4V8H8V4H16M3,9V14H21V9H3M2,16C2,17.1 2.9,18 4,18H20C21.1,18 22,17.1 22,16V8C22,6.89 21.1,6 20,6H4C2.89,6 2,6.89 2,8V16Z",
    projector: "M4,5A2,2 0 0,0 2,7V17A2,2 0 0,0 4,19H10V21H14V19H20A2,2 0 0,0 22,17V7A2,2 0 0,0 20,5H4M14,8A4,4 0 0,1 18,12A4,4 0 0,1 14,16A4,4 0 0,1 10,12A4,4 0 0,1 14,8Z",
    other: "M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z",
};

const DEVICE_TYPE_LABELS = {
    tv: "TV",
    ac: "Air Conditioner",
    fan: "Fan",
    soundbar: "Soundbar",
    projector: "Projector",
    other: "IR Device",
};

const DEVICE_TYPE_OPTIONS = [
    { value: "tv", label: "TV / Monitor" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "soundbar", label: "Soundbar / Audio" },
    { value: "projector", label: "Projector" },
    { value: "other", label: "Other" },
];

/* -------------------------------------------------------------------------- */
/*  ir-progress-bar                                                            */
/* -------------------------------------------------------------------------- */

class IrProgressBar extends LitElement {
    static properties = {
        learned: { type: Number },
        total: { type: Number },
    };

    constructor() {
        super();
        this.learned = 0;
        this.total = 0;
    }

    render() {
        const ratio = this.total > 0 ? this.learned / this.total : 0;
        const pct = Math.min(100, Math.max(0, Math.round(ratio * 100)));
        return html`
            <div class="bar" role="progressbar" aria-valuenow=${this.learned} aria-valuemax=${this.total}>
                <div class="fill" style="width: ${pct}%"></div>
            </div>
            <div class="label">${this.learned}/${this.total} commands</div>
        `;
    }

    static styles = css`
        :host { display: block; margin: 12px 0 16px; }
        .bar { background: var(--secondary-background-color); border-radius: 4px; height: 8px; overflow: hidden; }
        .fill { background: var(--primary-color); height: 100%; transition: width 200ms ease; }
        .label { margin-top: 6px; font-size: 0.85rem; color: var(--secondary-text-color); }
    `;
}
customElements.define("ir-progress-bar", IrProgressBar);

/* -------------------------------------------------------------------------- */
/*  ir-command-row                                                             */
/* -------------------------------------------------------------------------- */

class IrCommandRow extends LitElement {
    static properties = {
        templateName: { attribute: false },
        command: { attribute: false },
        busy: { type: Boolean },
    };

    constructor() {
        super();
        this.templateName = "";
        this.command = null;
        this.busy = false;
    }

    _emit(name) {
        this.dispatchEvent(
            new CustomEvent(name, {
                detail: { templateName: this.templateName, command: this.command },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const learned = this.command !== null;
        return html`
            <div class="row" data-learned=${learned ? "true" : "false"}>
                <div class="status" aria-hidden="true">${learned ? "✅" : "○"}</div>
                <div class="info">
                    <div class="name">${this.templateName}</div>
                    <div class="meta">
                        ${learned
                            ? html`${this.command.protocol ?? "Raw"} · ${this.command.code ?? "timings"}`
                            : html`<span class="muted">Not yet learned</span>`}
                    </div>
                </div>
                <div class="actions">
                    ${learned
                        ? html`
                              <button class="btn ghost" ?disabled=${this.busy} @click=${() => this._emit("test")}>▶ Test</button>
                              <button class="btn ghost" ?disabled=${this.busy} @click=${() => this._emit("relearn")}>↻ Re-learn</button>
                              <button class="btn ghost danger" ?disabled=${this.busy} @click=${() => this._emit("delete")} aria-label="Delete">✕</button>
                          `
                        : html`<button class="btn primary" ?disabled=${this.busy} @click=${() => this._emit("learn")}>Learn</button>`}
                </div>
            </div>
        `;
    }

    static styles = css`
        :host { display: block; }
        .row { display: grid; grid-template-columns: 32px 1fr auto; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 8px; }
        .row[data-learned="false"] { background: var(--secondary-background-color); }
        .status { font-size: 1.1rem; text-align: center; }
        .name { font-weight: 500; }
        .meta { font-size: 0.8rem; color: var(--secondary-text-color); font-family: var(--code-font-family, monospace); }
        .muted { font-style: italic; }
        .actions { display: flex; gap: 6px; align-items: center; }
        .btn { padding: 6px 12px; border-radius: 4px; border: 1px solid var(--divider-color); background: transparent; cursor: pointer; color: var(--primary-text-color); font-size: 0.85rem; }
        .btn.primary { background: var(--primary-color); color: var(--text-primary-color, white); border-color: var(--primary-color); }
        .btn.ghost:hover { background: var(--secondary-background-color); }
        .btn.danger:hover { background: var(--error-color, #c62828); color: white; border-color: var(--error-color, #c62828); }
        .btn[disabled] { opacity: 0.5; cursor: not-allowed; }
    `;
}
customElements.define("ir-command-row", IrCommandRow);

/* -------------------------------------------------------------------------- */
/*  ir-device-list                                                             */
/* -------------------------------------------------------------------------- */

class IrDeviceList extends LitElement {
    static properties = {
        devices: { attribute: false },
        loading: { type: Boolean },
    };

    constructor() {
        super();
        this.devices = [];
        this.loading = false;
    }

    _select(deviceId) {
        this.dispatchEvent(
            new CustomEvent("device-selected", {
                detail: deviceId,
                bubbles: true,
                composed: true,
            }),
        );
    }

    _add() {
        this.dispatchEvent(
            new CustomEvent("add-device", { bubbles: true, composed: true }),
        );
    }

    render() {
        if (this.loading) {
            return html`<div class="loading">Loading IR devices…</div>`;
        }
        if (this.devices.length === 0) {
            return html`
                <div class="empty">
                    <h2>No IR devices yet</h2>
                    <p>Add your first device to get started.</p>
                    <button class="btn primary" @click=${this._add}>+ Add Device</button>
                </div>
            `;
        }
        return html`
            <div class="grid">
                ${this.devices.map(
                    (device) => html`
                        <div
                            class="card"
                            tabindex="0"
                            role="button"
                            @click=${() => this._select(device.id)}
                            @keydown=${(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    this._select(device.id);
                                }
                            }}
                        >
                            <div class="card-header">
                                <svg viewBox="0 0 24 24" class="icon">
                                    <path d=${DEVICE_TYPE_ICONS[device.device_type] ?? DEVICE_TYPE_ICONS.other}></path>
                                </svg>
                                <div class="card-name">${device.name}</div>
                            </div>
                            <div class="card-meta">
                                ${[device.manufacturer, DEVICE_TYPE_LABELS[device.device_type], device.emitter_entity_id]
                                    .filter(Boolean)
                                    .join(" • ")}
                            </div>
                            <div class="card-footer">
                                <span class="badge">${device.command_count} commands</span>
                            </div>
                        </div>
                    `,
                )}
            </div>
        `;
    }

    static styles = css`
        :host { display: block; }
        .loading, .empty { padding: 32px; text-align: center; color: var(--secondary-text-color); }
        .empty h2 { margin-top: 8px; color: var(--primary-text-color); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
        .card { background: var(--card-background-color, white); border-radius: 12px; padding: 16px; cursor: pointer; box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.1)); transition: transform 120ms ease, box-shadow 120ms ease; }
        .card:hover, .card:focus-visible { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.18); outline: none; }
        .card-header { display: flex; align-items: center; gap: 12px; }
        .icon { width: 28px; height: 28px; fill: var(--primary-color); }
        .card-name { font-size: 1.1rem; font-weight: 500; color: var(--primary-text-color); }
        .card-meta { margin-top: 8px; font-size: 0.85rem; color: var(--secondary-text-color); }
        .card-footer { margin-top: 12px; }
        .badge { background: var(--secondary-background-color); border-radius: 999px; padding: 2px 10px; font-size: 0.85rem; color: var(--primary-text-color); }
        .btn { padding: 8px 16px; border-radius: 4px; border: 1px solid var(--primary-color); background: var(--primary-color); color: var(--text-primary-color, white); cursor: pointer; font-size: 0.95rem; }
    `;
}
customElements.define("ir-device-list", IrDeviceList);

/* -------------------------------------------------------------------------- */
/*  ir-capture-dialog                                                          */
/* -------------------------------------------------------------------------- */

class IrCaptureDialog extends LitElement {
    static properties = {
        api: { attribute: false },
        hass: { attribute: false },
        device: { attribute: false },
        commandName: { attribute: false },
        timeout: { type: Number },
        _phase: { state: true },
        _result: { state: true },
        _duplicate: { state: true },
        _error: { state: true },
        _timeRemaining: { state: true },
    };

    constructor() {
        super();
        this.timeout = 15;
        this._phase = "listening";
        this._result = null;
        this._duplicate = null;
        this._error = null;
        this._timeRemaining = 0;
        this._sessionId = null;
        this._unsubscribe = null;
        this._countdown = null;
    }

    connectedCallback() {
        super.connectedCallback();
        this._beginCapture();
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        this._stopCountdown();
        if (this._unsubscribe) {
            this._unsubscribe();
            this._unsubscribe = null;
        }
    }

    async _beginCapture() {
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
            this._error = err.message;
            this._phase = "error";
        }
    }

    _onCaptureEvent(event) {
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

    _startCountdown() {
        this._stopCountdown();
        const start = Date.now();
        this._countdown = window.setInterval(() => {
            const elapsed = (Date.now() - start) / 1000;
            this._timeRemaining = Math.max(0, Math.ceil(this.timeout - elapsed));
            if (this._timeRemaining <= 0) this._stopCountdown();
        }, 250);
    }

    _stopCountdown() {
        if (this._countdown !== null) {
            clearInterval(this._countdown);
            this._countdown = null;
        }
    }

    async _cancel() {
        if (this._sessionId) {
            try { await this.api.cancelCapture(this._sessionId); } catch {}
        }
        this._close();
    }

    async _testCommand() {
        if (!this._sessionId) return;
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
            this._error = err.message;
            this._phase = "error";
        }
    }

    async _save(saveAndNext) {
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
            this._error = err.message;
            this._phase = "error";
        }
    }

    async _recapture() {
        if (this._unsubscribe) {
            await this._unsubscribe();
            this._unsubscribe = null;
        }
        await this._beginCapture();
    }

    _close() {
        this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
    }

    render() {
        return html`
            <div class="backdrop" @click=${this._cancel}></div>
            <div class="dialog" role="dialog" aria-modal="true" aria-live="polite">
                <header>
                    <span class="heading">Learning: "${this.commandName}"</span>
                    <button class="close" @click=${this._cancel} aria-label="Close">✕</button>
                </header>
                <div class="body">
                    ${this._phase === "listening" ? this._renderListening() : ""}
                    ${this._phase === "captured" ? this._renderCaptured() : ""}
                    ${this._phase === "timeout" ? this._renderTimeout() : ""}
                    ${this._phase === "duplicate" ? this._renderDuplicate() : ""}
                    ${this._phase === "error" ? this._renderError() : ""}
                </div>
            </div>
        `;
    }

    _renderListening() {
        return html`
            <div class="phase">
                <div class="pulse" aria-hidden="true"><span></span><span></span><span></span></div>
                <div class="title">Listening for IR signal…</div>
                <div class="instruction">
                    Point your remote at the IR receiver and press the "${this.commandName}" button.
                </div>
                <div class="countdown">${this._timeRemaining}s remaining</div>
                <div class="actions">
                    <button class="btn" @click=${this._cancel}>Cancel</button>
                </div>
            </div>
        `;
    }

    _renderCaptured() {
        const result = this._result;
        return html`
            <div class="phase">
                <div class="check" aria-hidden="true">✓</div>
                <div class="title">Signal Captured!</div>
                <div class="meta">
                    Protocol: ${result.protocol ?? "Raw"}${result.code ? html` · <code>${result.code}</code>` : ""}
                </div>
                <div class="info-banner">Did it work? Press Test to verify.</div>
                <div class="actions">
                    <button class="btn" @click=${this._testCommand}>▶ Test</button>
                    <button class="btn" @click=${this._recapture}>↻ Re-capture</button>
                    <button class="btn primary" @click=${() => this._save(true)}>Save & Learn Next ▶▶</button>
                </div>
            </div>
        `;
    }

    _renderTimeout() {
        return html`
            <div class="phase">
                <div class="title warn">⚠ No signal detected</div>
                <ul class="tips">
                    <li>Point the remote directly at the IR receiver</li>
                    <li>Move closer (within 3 feet / 1 meter)</li>
                    <li>Press and hold the button briefly</li>
                </ul>
                <div class="actions">
                    <button class="btn primary" @click=${this._recapture}>↻ Try Again</button>
                    <button class="btn" @click=${this._cancel}>Cancel</button>
                </div>
            </div>
        `;
    }

    _renderDuplicate() {
        const result = this._result;
        return html`
            <div class="phase">
                <div class="title warn">⚠ Duplicate Signal Detected</div>
                <div class="instruction">
                    This matches your "${this._duplicate.name}" command.
                    Some remotes use the same signal for multiple buttons.
                </div>
                <div class="meta">Protocol: ${result.protocol ?? "Raw"}</div>
                <div class="actions">
                    <button class="btn" @click=${this._recapture}>Re-capture Different</button>
                    <button class="btn primary" @click=${() => this._save(true)}>Save Anyway</button>
                </div>
            </div>
        `;
    }

    _renderError() {
        return html`
            <div class="phase">
                <div class="title warn">⚠ Capture Error</div>
                <div class="instruction">${this._error}</div>
                <div class="actions">
                    <button class="btn primary" @click=${this._recapture}>↻ Try Again</button>
                    <button class="btn" @click=${this._cancel}>Cancel</button>
                </div>
            </div>
        `;
    }

    static styles = css`
        :host { position: fixed; inset: 0; z-index: 1000; }
        .backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.5); }
        .dialog { position: relative; max-width: 480px; margin: 10vh auto; background: var(--card-background-color, white); border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
        .heading { font-weight: 500; color: var(--primary-text-color); }
        .close { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--primary-text-color); }
        .body { padding: 16px; }
        .phase { min-width: 280px; }
        .title { font-size: 1.1rem; font-weight: 500; margin-bottom: 8px; color: var(--primary-text-color); }
        .title.warn { color: var(--warning-color, #ffa600); }
        .instruction { color: var(--primary-text-color); margin-bottom: 8px; }
        .meta { color: var(--secondary-text-color); font-size: 0.85rem; margin-bottom: 8px; }
        .countdown { margin: 10px 0; font-variant-numeric: tabular-nums; color: var(--secondary-text-color); }
        .check { font-size: 3rem; color: var(--success-color, #43a047); text-align: center; margin: 8px 0; }
        .pulse { display: flex; justify-content: center; gap: 6px; margin: 8px 0 16px; }
        .pulse span { display: inline-block; width: 12px; height: 12px; background: var(--primary-color); border-radius: 50%; opacity: 0.4; animation: pulse 1s infinite ease-in-out; }
        .pulse span:nth-child(2) { animation-delay: 0.2s; }
        .pulse span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes pulse {
            0%, 100% { opacity: 0.3; transform: scale(0.85); }
            50% { opacity: 1; transform: scale(1.1); }
        }
        .info-banner { background: var(--secondary-background-color); border-radius: 4px; padding: 8px 12px; margin: 8px 0; }
        .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
        .tips { margin: 4px 0 12px; padding-left: 22px; color: var(--primary-text-color); }
        .btn { padding: 8px 16px; border-radius: 4px; border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color); cursor: pointer; }
        .btn.primary { background: var(--primary-color); color: var(--text-primary-color, white); border-color: var(--primary-color); }
        .btn:hover { background: var(--secondary-background-color); }
        .btn.primary:hover { filter: brightness(1.05); }
    `;
}
customElements.define("ir-capture-dialog", IrCaptureDialog);

/* -------------------------------------------------------------------------- */
/*  ir-add-device-dialog                                                       */
/* -------------------------------------------------------------------------- */

class IrAddDeviceDialog extends LitElement {
    static properties = {
        api: { attribute: false },
        hass: { attribute: false },
        _name: { state: true },
        _manufacturer: { state: true },
        _model: { state: true },
        _deviceType: { state: true },
        _emitterId: { state: true },
        _captureProviderId: { state: true },
        _captureProviders: { state: true },
        _emitters: { state: true },
        _busy: { state: true },
        _error: { state: true },
    };

    constructor() {
        super();
        this._name = "";
        this._manufacturer = "";
        this._model = "";
        this._deviceType = "tv";
        this._emitterId = "";
        this._captureProviderId = "";
        this._captureProviders = [];
        this._emitters = [];
        this._busy = false;
        this._error = null;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadEmitters();
        this._loadCaptureProviders();
    }

    _loadEmitters() {
        const states = this.hass?.states ?? {};
        const emitters = [];
        for (const [entityId, state] of Object.entries(states)) {
            if (entityId.startsWith("infrared.")) {
                emitters.push({
                    entity_id: entityId,
                    name: state.attributes?.friendly_name ?? entityId,
                });
            }
        }
        this._emitters = emitters;
        if (emitters.length === 1) this._emitterId = emitters[0].entity_id;
    }

    async _loadCaptureProviders() {
        try {
            this._captureProviders = await this.api.listCaptureProviders();
            if (this._captureProviders.length === 1) {
                this._captureProviderId = this._captureProviders[0].device_id;
            }
        } catch (err) {
            this._error = `Could not load capture providers: ${err.message}`;
        }
    }

    _close() {
        this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
    }

    async _create() {
        if (!this._name.trim()) {
            this._error = "Name is required.";
            return;
        }
        if (!this._emitterId) {
            this._error = "Pick an IR emitter.";
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const provider = this._captureProviders.find((p) => p.device_id === this._captureProviderId);
            const created = await this.api.createDevice({
                name: this._name.trim(),
                device_type: this._deviceType,
                emitter_entity_id: this._emitterId,
                manufacturer: this._manufacturer.trim() || null,
                model: this._model.trim() || null,
                capture_device_id: this._captureProviderId || null,
                capture_provider_type: provider?.type ?? "esphome",
            });
            this.dispatchEvent(
                new CustomEvent("device-created", {
                    detail: created,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = err.message;
        } finally {
            this._busy = false;
        }
    }

    render() {
        return html`
            <div class="backdrop" @click=${this._close}></div>
            <div class="dialog" role="dialog" aria-modal="true">
                <header>
                    <span class="heading">Add IR Device</span>
                    <button class="close" @click=${this._close} aria-label="Close">✕</button>
                </header>
                <div class="body">
                    ${this._error ? html`<div class="alert error">${this._error}</div>` : ""}

                    <label class="field">
                        <span>Device type</span>
                        <select
                            .value=${this._deviceType}
                            @change=${(e) => (this._deviceType = e.target.value)}
                        >
                            ${DEVICE_TYPE_OPTIONS.map(
                                (t) => html`<option value=${t.value} ?selected=${this._deviceType === t.value}>${t.label}</option>`,
                            )}
                        </select>
                    </label>

                    <label class="field">
                        <span>Name *</span>
                        <input
                            type="text"
                            .value=${this._name}
                            @input=${(e) => (this._name = e.target.value)}
                            placeholder="Living Room TV"
                        />
                    </label>

                    <label class="field">
                        <span>Brand (optional)</span>
                        <input
                            type="text"
                            .value=${this._manufacturer}
                            @input=${(e) => (this._manufacturer = e.target.value)}
                            placeholder="Samsung"
                        />
                    </label>

                    <label class="field">
                        <span>Model (optional)</span>
                        <input
                            type="text"
                            .value=${this._model}
                            @input=${(e) => (this._model = e.target.value)}
                        />
                    </label>

                    <label class="field">
                        <span>IR emitter (sends commands)</span>
                        ${this._emitters.length === 0
                            ? html`<div class="alert warn">
                                  No IR emitters found. Set up an ESPHome remote_transmitter or a Broadlink device first.
                              </div>`
                            : html`
                                  <select
                                      .value=${this._emitterId}
                                      @change=${(e) => (this._emitterId = e.target.value)}
                                  >
                                      <option value="" disabled>Select emitter…</option>
                                      ${this._emitters.map(
                                          (em) => html`<option value=${em.entity_id} ?selected=${this._emitterId === em.entity_id}>${em.name}</option>`,
                                      )}
                                  </select>
                              `}
                    </label>

                    <label class="field">
                        <span>IR receiver (learns commands)</span>
                        ${this._captureProviders.length === 0
                            ? html`<div class="alert info">
                                  No capture-capable devices detected. You can still create the device and import commands later.
                              </div>`
                            : html`
                                  <select
                                      .value=${this._captureProviderId}
                                      @change=${(e) => (this._captureProviderId = e.target.value)}
                                  >
                                      <option value="">None (no learning)</option>
                                      ${this._captureProviders.map(
                                          (p) => html`<option value=${p.device_id} ?selected=${this._captureProviderId === p.device_id}>${p.name} (${p.type})</option>`,
                                      )}
                                  </select>
                              `}
                    </label>
                </div>
                <footer>
                    <button class="btn" @click=${this._close} ?disabled=${this._busy}>Cancel</button>
                    <button class="btn primary" @click=${this._create} ?disabled=${this._busy}>Create</button>
                </footer>
            </div>
        `;
    }

    static styles = css`
        :host { position: fixed; inset: 0; z-index: 1000; }
        .backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.5); }
        .dialog { position: relative; max-width: 480px; margin: 8vh auto; background: var(--card-background-color, white); border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); display: flex; flex-direction: column; max-height: 80vh; }
        header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
        .heading { font-weight: 500; color: var(--primary-text-color); }
        .close { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--primary-text-color); }
        .body { padding: 16px; overflow-y: auto; flex: 1; }
        footer { padding: 12px 16px; border-top: 1px solid var(--divider-color); display: flex; justify-content: flex-end; gap: 8px; }
        .field { display: block; margin: 12px 0; }
        .field span { display: block; font-size: 0.85rem; color: var(--secondary-text-color); margin-bottom: 6px; }
        select, input { width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); box-sizing: border-box; font-size: 0.95rem; }
        .alert { padding: 8px 12px; border-radius: 4px; margin: 8px 0; font-size: 0.9rem; }
        .alert.error { background: rgba(198,40,40,0.1); color: var(--error-color, #c62828); }
        .alert.warn { background: rgba(255,166,0,0.1); color: var(--warning-color, #ffa600); }
        .alert.info { background: var(--secondary-background-color); color: var(--secondary-text-color); }
        .btn { padding: 8px 16px; border-radius: 4px; border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color); cursor: pointer; }
        .btn.primary { background: var(--primary-color); color: var(--text-primary-color, white); border-color: var(--primary-color); }
        .btn:hover { background: var(--secondary-background-color); }
        .btn.primary:hover { filter: brightness(1.05); }
        .btn[disabled] { opacity: 0.5; cursor: not-allowed; }
    `;
}
customElements.define("ir-add-device-dialog", IrAddDeviceDialog);

/* -------------------------------------------------------------------------- */
/*  ir-device-detail                                                           */
/* -------------------------------------------------------------------------- */

class IrDeviceDetail extends LitElement {
    static properties = {
        api: { attribute: false },
        hass: { attribute: false },
        device: { attribute: false },
        _templates: { state: true },
        _busy: { state: true },
        _captureName: { state: true },
        _captureQueue: { state: true },
        _customDialogOpen: { state: true },
        _customName: { state: true },
        _toast: { state: true },
        _confirmDelete: { state: true },
    };

    constructor() {
        super();
        this._templates = [];
        this._busy = false;
        this._captureName = null;
        this._captureQueue = [];
        this._customDialogOpen = false;
        this._customName = "";
        this._toast = null;
        this._confirmDelete = false;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadTemplates();
    }

    updated(changed) {
        if (changed.has("device") && this.device) {
            this._loadTemplates();
        }
    }

    async _loadTemplates() {
        try {
            this._templates = await this.api.listTemplates(this.device.device_type);
        } catch {
            this._templates = [];
        }
    }

    get _entries() {
        const captured = new Map(this.device.commands.map((c) => [c.name.toLowerCase(), c]));
        const seen = new Set();
        const entries = [];
        for (const t of this._templates) {
            seen.add(t.name.toLowerCase());
            entries.push({
                template: t,
                name: t.name,
                command: captured.get(t.name.toLowerCase()) ?? null,
                essential: t.essential,
                custom: false,
            });
        }
        for (const c of this.device.commands) {
            if (!seen.has(c.name.toLowerCase())) {
                entries.push({ template: null, name: c.name, command: c, essential: false, custom: true });
            }
        }
        return entries;
    }

    async _refresh() {
        this.device = await this.api.getDevice(this.device.id);
        this.dispatchEvent(new CustomEvent("device-changed", { bubbles: true, composed: true }));
    }

    _flash(message) {
        this._toast = message;
        setTimeout(() => (this._toast = null), 2400);
    }

    _onLearn(e) {
        this._captureQueue = [];
        this._captureName = e.detail.templateName;
    }

    _onRelearn(e) {
        this._captureQueue = [];
        this._captureName = e.detail.templateName;
    }

    async _onTest(e) {
        const command = e.detail.command;
        if (!command) return;
        this._busy = true;
        try {
            await this.api.sendCommand(this.device.id, command.id);
            this._flash(`Sent "${command.name}"`);
        } catch (err) {
            this._flash(`Send failed: ${err.message}`);
        } finally {
            this._busy = false;
        }
    }

    async _onDelete(e) {
        const command = e.detail.command;
        if (!command) return;
        this._busy = true;
        try {
            await this.api.deleteCommand(this.device.id, command.id);
            await this._refresh();
            this._flash(`Removed "${command.name}"`);
        } catch (err) {
            this._flash(`Delete failed: ${err.message}`);
        } finally {
            this._busy = false;
        }
    }

    _onCaptureClosed() {
        this._captureName = null;
        this._captureQueue = [];
    }

    async _onCommandSaved(e) {
        const { saveAndNext, commandName } = e.detail;
        await this._refresh();
        this._flash(`Saved "${commandName}"`);
        if (saveAndNext) {
            const queue = this._buildNextQueue(commandName);
            if (queue.length > 0) {
                this._captureQueue = queue;
                this._captureName = queue[0];
                return;
            }
        }
        this._captureName = null;
    }

    _buildNextQueue(justSaved) {
        const captured = new Set(this.device.commands.map((c) => c.name.toLowerCase()));
        captured.add(justSaved.toLowerCase());
        return this._templates
            .filter((t) => t.essential && !captured.has(t.name.toLowerCase()))
            .map((t) => t.name);
    }

    _openCustomDialog() {
        this._customName = "";
        this._customDialogOpen = true;
    }

    _closeCustomDialog() {
        this._customDialogOpen = false;
    }

    _confirmCustom() {
        const name = this._customName.trim();
        if (!name) return;
        this._customDialogOpen = false;
        this._captureName = name;
        this._captureQueue = [];
    }

    async _deleteDevice() {
        this._busy = true;
        try {
            await this.api.deleteDevice(this.device.id);
            this.dispatchEvent(new CustomEvent("device-deleted", { bubbles: true, composed: true }));
        } catch (err) {
            this._flash(`Delete failed: ${err.message}`);
        } finally {
            this._busy = false;
            this._confirmDelete = false;
        }
    }

    render() {
        const entries = this._entries;
        const essential = entries.filter((e) => e.essential);
        const optional = entries.filter((e) => !e.essential && !e.custom);
        const custom = entries.filter((e) => e.custom);
        const learned = entries.filter((e) => e.command !== null).length;
        const total = entries.length || essential.length;
        const mappedFeatures = Object.keys(this.device.entity_config.command_mapping || {});
        const platform = this.device.entity_config.platform;

        return html`
            <section class="header">
                <div>
                    <h1>${this.device.name}</h1>
                    <div class="subtitle">
                        ${[this.device.manufacturer, this.device.model, this.device.emitter_entity_id]
                            .filter(Boolean)
                            .join(" • ")}
                    </div>
                </div>
                <div class="header-actions">
                    <button class="btn" @click=${() => (this._confirmDelete = true)} ?disabled=${this._busy}>
                        Delete
                    </button>
                </div>
            </section>

            <ir-progress-bar .learned=${learned} .total=${total}></ir-progress-bar>

            ${essential.length > 0 ? html`
                <div class="card">
                    <h2>Essential Commands</h2>
                    ${essential.map((entry) => html`
                        <ir-command-row
                            .templateName=${entry.name}
                            .command=${entry.command}
                            .busy=${this._busy}
                            @learn=${this._onLearn}
                            @relearn=${this._onRelearn}
                            @test=${this._onTest}
                            @delete=${this._onDelete}
                        ></ir-command-row>
                    `)}
                </div>
            ` : ""}
            ${optional.length > 0 ? html`
                <div class="card">
                    <h2>Optional Commands</h2>
                    ${optional.map((entry) => html`
                        <ir-command-row
                            .templateName=${entry.name}
                            .command=${entry.command}
                            .busy=${this._busy}
                            @learn=${this._onLearn}
                            @relearn=${this._onRelearn}
                            @test=${this._onTest}
                            @delete=${this._onDelete}
                        ></ir-command-row>
                    `)}
                </div>
            ` : ""}
            ${custom.length > 0 ? html`
                <div class="card">
                    <h2>Custom Commands</h2>
                    ${custom.map((entry) => html`
                        <ir-command-row
                            .templateName=${entry.name}
                            .command=${entry.command}
                            .busy=${this._busy}
                            @relearn=${this._onRelearn}
                            @test=${this._onTest}
                            @delete=${this._onDelete}
                        ></ir-command-row>
                    `)}
                </div>
            ` : ""}

            <div class="custom-add">
                <button class="btn primary" @click=${this._openCustomDialog} ?disabled=${this._busy}>
                    + Add Custom Command
                </button>
            </div>

            <div class="card entity-summary">
                <h2>Entity</h2>
                <div class="meta">Platform: <code>${platform}</code></div>
                <div class="meta">
                    Mapped features:
                    ${mappedFeatures.length > 0 ? mappedFeatures.join(", ") : "None yet — capture commands to enable features."}
                </div>
            </div>

            ${this._captureName ? html`
                <ir-capture-dialog
                    .api=${this.api}
                    .hass=${this.hass}
                    .device=${this.device}
                    .commandName=${this._captureName}
                    @closed=${this._onCaptureClosed}
                    @command-saved=${this._onCommandSaved}
                ></ir-capture-dialog>
            ` : ""}

            ${this._customDialogOpen ? html`
                <div class="modal-backdrop" @click=${this._closeCustomDialog}></div>
                <div class="modal" role="dialog" aria-modal="true">
                    <header><span class="heading">Add Custom Command</span></header>
                    <div class="body">
                        <label class="field">
                            <span>Command name</span>
                            <input
                                type="text"
                                .value=${this._customName}
                                @input=${(e) => (this._customName = e.target.value)}
                                placeholder="My custom command"
                            />
                        </label>
                    </div>
                    <footer>
                        <button class="btn" @click=${this._closeCustomDialog}>Cancel</button>
                        <button class="btn primary" @click=${this._confirmCustom}>Start Learning</button>
                    </footer>
                </div>
            ` : ""}

            ${this._confirmDelete ? html`
                <div class="modal-backdrop" @click=${() => (this._confirmDelete = false)}></div>
                <div class="modal" role="dialog" aria-modal="true">
                    <header><span class="heading">Delete ${this.device.name}?</span></header>
                    <div class="body">
                        <p>This removes all captured commands and the auto-created entity. The action cannot be undone.</p>
                    </div>
                    <footer>
                        <button class="btn" @click=${() => (this._confirmDelete = false)}>Cancel</button>
                        <button class="btn destructive" @click=${this._deleteDevice}>Delete</button>
                    </footer>
                </div>
            ` : ""}

            ${this._toast ? html`<div class="toast" role="status">${this._toast}</div>` : ""}
        `;
    }

    static styles = css`
        :host { display: block; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
        h1 { font-size: 1.5rem; margin: 0; color: var(--primary-text-color); }
        .subtitle { color: var(--secondary-text-color); margin-top: 4px; font-size: 0.9rem; }
        .header-actions { display: flex; gap: 6px; }
        .card { background: var(--card-background-color, white); border-radius: 12px; box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,0.1)); margin: 16px 0; padding: 16px; }
        .card h2 { margin: 0 0 8px; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--secondary-text-color); }
        .custom-add { margin: 16px 0; }
        .entity-summary .meta { font-size: 0.9rem; color: var(--primary-text-color); margin: 4px 0; }
        .btn { padding: 8px 16px; border-radius: 4px; border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color); cursor: pointer; font-size: 0.9rem; }
        .btn.primary { background: var(--primary-color); color: var(--text-primary-color, white); border-color: var(--primary-color); }
        .btn.destructive { background: var(--error-color, #c62828); color: white; border-color: var(--error-color, #c62828); }
        .btn:hover { filter: brightness(1.05); }
        .btn[disabled] { opacity: 0.5; cursor: not-allowed; }
        .modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; }
        .modal { position: fixed; top: 15vh; left: 50%; transform: translateX(-50%); max-width: 420px; width: calc(100% - 32px); background: var(--card-background-color, white); border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); z-index: 1001; }
        .modal header { padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
        .modal .heading { font-weight: 500; color: var(--primary-text-color); }
        .modal .body { padding: 16px; color: var(--primary-text-color); }
        .modal footer { padding: 12px 16px; border-top: 1px solid var(--divider-color); display: flex; justify-content: flex-end; gap: 8px; }
        .field { display: block; }
        .field span { display: block; font-size: 0.85rem; color: var(--secondary-text-color); margin-bottom: 6px; }
        .field input { width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); box-sizing: border-box; }
        .toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--primary-color); color: var(--text-primary-color, white); padding: 8px 16px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); z-index: 1100; }
        code { font-family: var(--code-font-family, monospace); }
    `;
}
customElements.define("ir-device-detail", IrDeviceDetail);

/* -------------------------------------------------------------------------- */
/*  ha-panel-ir-devices (root)                                                 */
/* -------------------------------------------------------------------------- */

class HaPanelIrDevices extends LitElement {
    static properties = {
        hass: { attribute: false },
        narrow: { type: Boolean },
        route: { attribute: false },
        panel: { attribute: false },
        _devices: { state: true },
        _selectedDevice: { state: true },
        _loading: { state: true },
        _error: { state: true },
        _addDialogOpen: { state: true },
    };

    constructor() {
        super();
        this.narrow = false;
        this._devices = [];
        this._selectedDevice = null;
        this._loading = true;
        this._error = null;
        this._addDialogOpen = false;
        this._api = null;
    }

    connectedCallback() {
        super.connectedCallback();
        if (this.hass) this._init();
    }

    updated(changed) {
        if (changed.has("hass") && this.hass && !this._api) {
            this._init();
        }
    }

    _init() {
        this._api = new HairApi(this.hass);
        this._refreshDevices();
    }

    async _refreshDevices() {
        if (!this._api) return;
        this._loading = true;
        try {
            this._devices = await this._api.listDevices();
            this._error = null;
        } catch (err) {
            this._error = `Failed to load devices: ${err.message}`;
        } finally {
            this._loading = false;
        }
    }

    async _openDevice(deviceId) {
        if (!this._api) return;
        try {
            this._selectedDevice = await this._api.getDevice(deviceId);
        } catch (err) {
            this._error = `Failed to open device: ${err.message}`;
        }
    }

    _backToList() {
        this._selectedDevice = null;
    }

    _openAddDialog() {
        this._addDialogOpen = true;
    }

    _closeAddDialog() {
        this._addDialogOpen = false;
    }

    async _onDeviceCreated(e) {
        this._addDialogOpen = false;
        await this._refreshDevices();
        this._selectedDevice = e.detail;
    }

    async _onDeviceChanged() {
        await this._refreshDevices();
        if (this._selectedDevice && this._api) {
            this._selectedDevice = await this._api.getDevice(this._selectedDevice.id);
        }
    }

    async _onDeviceDeleted() {
        this._selectedDevice = null;
        await this._refreshDevices();
    }

    render() {
        if (!this._api) {
            return html`<div class="loading">Loading…</div>`;
        }
        return html`
            <div class="bar">
                <button
                    class="bar-icon"
                    @click=${this._selectedDevice ? this._backToList : null}
                    aria-label="${this._selectedDevice ? "Back" : "Menu"}"
                >
                    <svg viewBox="0 0 24 24" class="icon-svg">
                        <path d=${this._selectedDevice
                            ? "M19,11H7.83L12.83,6L11.41,4.59L4,12L11.41,19.41L12.83,18L7.83,13H19V11Z"
                            : "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}></path>
                    </svg>
                </button>
                <span class="bar-title">${this._selectedDevice ? this._selectedDevice.name : "IR Devices"}</span>
            </div>

            <div class="content">
                ${this._error ? html`<div class="alert error">${this._error}</div>` : ""}
                ${this._selectedDevice
                    ? html`
                          <ir-device-detail
                              .api=${this._api}
                              .device=${this._selectedDevice}
                              .hass=${this.hass}
                              @device-changed=${this._onDeviceChanged}
                              @device-deleted=${this._onDeviceDeleted}
                          ></ir-device-detail>
                      `
                    : html`
                          <ir-device-list
                              .devices=${this._devices}
                              .loading=${this._loading}
                              @device-selected=${(e) => this._openDevice(e.detail)}
                              @add-device=${this._openAddDialog}
                          ></ir-device-list>
                          ${!this._loading && this._devices.length > 0
                              ? html`
                                    <button class="fab" @click=${this._openAddDialog} aria-label="Add device">
                                        +
                                    </button>
                                `
                              : ""}
                      `}
            </div>

            ${this._addDialogOpen
                ? html`
                      <ir-add-device-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          @closed=${this._closeAddDialog}
                          @device-created=${this._onDeviceCreated}
                      ></ir-add-device-dialog>
                  `
                : ""}
        `;
    }

    static styles = css`
        :host {
            display: block;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            min-height: 100vh;
            font-family: var(--paper-font-body1_-_font-family, "Roboto", sans-serif);
        }
        .bar {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: var(--app-header-background-color, var(--primary-color));
            color: var(--app-header-text-color, white);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
        }
        .bar-icon {
            background: transparent;
            border: none;
            cursor: pointer;
            padding: 4px;
            color: inherit;
            display: flex;
            align-items: center;
            border-radius: 4px;
        }
        .bar-icon:hover { background: rgba(255,255,255,0.1); }
        .bar-icon[disabled] { cursor: default; opacity: 0.5; }
        .icon-svg { width: 24px; height: 24px; fill: currentColor; }
        .bar-title { font-size: 1.1rem; font-weight: 500; }
        .content { padding: 16px; max-width: 1100px; margin: 0 auto; }
        .loading { padding: 48px; text-align: center; color: var(--secondary-text-color); }
        .alert { padding: 8px 12px; border-radius: 4px; margin: 8px 0; font-size: 0.9rem; }
        .alert.error { background: rgba(198,40,40,0.1); color: var(--error-color, #c62828); }
        .fab {
            position: fixed;
            right: 24px;
            bottom: 24px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: var(--primary-color);
            color: var(--text-primary-color, white);
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        }
        .fab:hover { filter: brightness(1.05); }
    `;
}
customElements.define("ha-panel-ir-devices", HaPanelIrDevices);
