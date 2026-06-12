/**
 * One row in the device-detail command checklist.
 * - Captured commands show protocol info plus Test / Edit / Delete actions and an action badge.
 * - Unlearned templates show a single Learn button.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { customElement, property, state } from "./decorators.js";
import type { IRCommand } from "./types.js";

@customElement("ir-command-row")
export class IrCommandRow extends LitElement {
    @property({ attribute: false }) public templateName: string = "";
    @property({ attribute: false }) public command: IRCommand | null = null;
    @property({ type: Boolean }) public busy = false;

    /** Label of the mapped action (e.g. "Power On"), or empty/null if unmapped. */
    @property({ attribute: false }) public actionLabel: string | null = null;

    /** Whether this command already has an associated trigger. */
    @property({ type: Boolean }) public hasTrigger = false;

    /** Whether to show the action-mapping ("ACTIONS") button. Hidden for
     *  device types whose platform exposes no mappable feature actions
     *  (e.g. Other / the remote platform), where the popover would be empty. */
    @property({ type: Boolean }) public showActionMapping = true;

    @state() private _editOpen = false;
    @state() private _editValue = "";
    @state() private _editError = "";
    @state() private _editBusy = false;

    /** Human-friendly label for a captured command (plain text fallback). */
    private _commandLabel(): string {
        const cmd = this.command!;
        if (cmd.protocol && cmd.code) {
            return `${cmd.protocol}: ${cmd.code}`;
        }
        if (cmd.raw_timings?.length) {
            return `RAW: ${cmd.raw_timings.length} timings`;
        }
        return cmd.protocol ?? "IR";
    }

    /** Compute S/L boolean array from Pronto hex (mirrors backend logic). */
    private _prontoSlArray(hex: string): boolean[] | null {
        const words = hex.trim().split(/\s+/);
        if (words.length < 6) return null;
        const burst1 = parseInt(words[2], 16);
        const burst2 = parseInt(words[3], 16);
        const total = burst1 + burst2;
        const timings = words.slice(4);
        if (timings.length < total * 2) return null;
        const result: boolean[] = [];
        for (let i = 0; i < total * 2; i++) {
            const val = parseInt(timings[i], 16);
            result.push(val >= 0x30); // true = Long, false = Short
        }
        return result.length > 0 ? result : null;
    }

    /** Render diamond pattern: filled blue = Long, empty amber = Short. */
    private _renderDiamonds() {
        const cmd = this.command;
        if (!cmd || cmd.protocol?.toUpperCase() !== "PRONTO" || !cmd.code)
            return null;
        const arr = this._prontoSlArray(cmd.code);
        if (!arr) return null;
        return html`<span class="diamonds">${arr.map((isLong) =>
            isLong
                ? html`<span class="diamond long">◆</span>`
                : html`<span class="diamond short">◇</span>`
        )}</span>`;
    }

    private _emit(name: string) {
        this.dispatchEvent(
            new CustomEvent(name, {
                detail: { templateName: this.templateName, command: this.command },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _openEdit() {
        this._editValue = this.command?.code ?? "";
        this._editError = "";
        this._editOpen = true;
        // Focus the textarea after render
        this.updateComplete.then(() => {
            const ta = this.renderRoot.querySelector<HTMLTextAreaElement>(".edit-textarea");
            ta?.focus();
            ta?.select();
        });
    }

    private _closeEdit() {
        this._editOpen = false;
        this._editError = "";
        this._editBusy = false;
    }

    private async _saveEdit() {
        const pronto = this._editValue.trim();
        if (!pronto) {
            this._editError = "Pronto code cannot be empty.";
            return;
        }
        this._editBusy = true;
        this._editError = "";
        this.dispatchEvent(
            new CustomEvent("update-code", {
                detail: {
                    templateName: this.templateName,
                    command: this.command,
                    pronto,
                    onSuccess: () => {
                        this._editBusy = false;
                        this._editOpen = false;
                    },
                    onError: (msg: string) => {
                        this._editBusy = false;
                        this._editError = msg;
                    },
                },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _onEditKeydown(e: KeyboardEvent) {
        if (e.key === "Escape") this._closeEdit();
    }

    render() {
        const learned = this.command !== null;
        const diamonds = learned ? this._renderDiamonds() : null;
        return html`
            <div class="row" data-learned=${learned ? "true" : "false"}>
                <div class="status" aria-hidden="true">
                    <slot name="status"></slot>
                </div>
                <div class="info">
                    <div class="name">${this.templateName}</div>
                    <div class="meta">
                        ${diamonds
                            ? diamonds
                            : learned
                              ? html`${this._commandLabel()}`
                              : html`<span class="muted">Not yet learned</span>`}
                    </div>
                    ${this._editOpen ? html`
                        <div class="edit-panel">
                            <textarea
                                class="edit-textarea"
                                .value=${this._editValue}
                                @input=${(e: InputEvent) => {
                                    this._editValue = (e.target as HTMLTextAreaElement).value;
                                }}
                                @keydown=${this._onEditKeydown}
                                placeholder="Paste Pronto hex code here…"
                                rows="3"
                                spellcheck="false"
                                autocomplete="off"
                                ?disabled=${this._editBusy}
                            ></textarea>
                            ${this._editError ? html`
                                <div class="edit-error">${this._editError}</div>
                            ` : ""}
                            <div class="edit-actions">
                                <button
                                    class="action-btn save-btn"
                                    ?disabled=${this._editBusy}
                                    @click=${this._saveEdit}
                                >
                                    ${this._editBusy ? "Saving…" : "Save"}
                                </button>
                                <button
                                    class="action-btn cancel-btn"
                                    ?disabled=${this._editBusy}
                                    @click=${this._closeEdit}
                                >Cancel</button>
                            </div>
                        </div>
                    ` : ""}
                </div>
                <div class="actions">
                    ${learned
                        ? html`
                              ${this.showActionMapping
                                  ? html`<button
                                  class="action-btn badge-btn"
                                  ?data-mapped=${!!this.actionLabel}
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("map-action")}
                                  title="Assign action mapping"
                              >${this.actionLabel || "ACTIONS"}</button>`
                                  : ""}
                              <button
                                  class="action-btn test-btn"
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("test")}
                              >Test</button>
                              <button
                                  class="action-btn edit-btn ${this._editOpen ? "edit-active" : ""}"
                                  ?disabled=${this.busy}
                                  @click=${() => this._editOpen ? this._closeEdit() : this._openEdit()}
                                  title="Edit Pronto code"
                              >Edit</button>
                              <button
                                  class="action-btn trigger-btn ${this.hasTrigger ? "trigger-on" : ""}"
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("toggle-trigger")}
                                  title=${this.hasTrigger ? "Edit trigger" : "Create trigger"}
                              >Trigger</button>
                              ${this.command?.decoded_fingerprint
                                  ? html`<button
                                  class="action-btn tx-btn ${this.command.tx_force_raw ? "tx-raw-on" : ""}"
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("toggle-tx-raw")}
                                  title=${this.command.tx_force_raw
                                      ? "Transmitting the captured timings. Click to send clean decoded timings."
                                      : "Transmitting clean decoded timings. Click to replay the captured timings instead."}
                              >${this.command.tx_force_raw ? "RAW" : "AUTO"}</button>`
                                  : ""}
                              <button
                                  class="action-btn delete-btn"
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("delete")}
                              >Delete</button>
                          `
                        : html`
                              <button
                                  class="action-btn learn-btn"
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("learn")}
                              >Learn</button>
                          `}
                </div>
            </div>
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        :host(:not(:last-of-type)) {
            margin-bottom: 4px;
        }
        .row {
            display: grid;
            grid-template-columns: 32px 1fr auto;
            align-items: start;
            gap: 12px;
            padding: 8px 10px;
            background: var(--primary-background-color);
            border-radius: 4px;
        }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
            padding-top: 6px;
        }
        .name {
            font-weight: 500;
        }
        .meta {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-family: var(--code-font-family, monospace);
        }
        .muted {
            font-style: italic;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
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
        /* ── Edit panel ── */
        .edit-panel {
            margin-top: 8px;
        }
        .edit-textarea {
            width: 100%;
            box-sizing: border-box;
            font-family: var(--code-font-family, monospace);
            font-size: 0.78rem;
            padding: 6px 8px;
            background: var(--secondary-background-color);
            color: var(--primary-text-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            resize: vertical;
            outline: none;
            transition: border-color 150ms ease;
        }
        .edit-textarea:focus {
            border-color: var(--primary-color);
        }
        .edit-textarea:disabled {
            opacity: 0.6;
        }
        .edit-error {
            margin-top: 4px;
            font-size: 0.78rem;
            color: var(--error-color, #b00020);
        }
        .edit-actions {
            display: flex;
            gap: 6px;
            margin-top: 6px;
        }
        .action-btn.save-btn {
            color: #fff;
            background: var(--primary-color);
            border-color: var(--primary-color);
        }
        .action-btn.save-btn:hover:not(:disabled) {
            filter: brightness(0.9);
        }
        .action-btn.cancel-btn {
            color: var(--secondary-text-color);
        }
        .action-btn.edit-btn {
            color: #5c6bc0;
            border-color: rgba(92, 107, 192, 0.3);
        }
        .action-btn.edit-btn:hover {
            background: rgba(92, 107, 192, 0.08);
        }
        .action-btn.edit-btn.edit-active {
            color: #fff;
            background: #5c6bc0;
            border-color: #5c6bc0;
        }
        .action-btn.edit-btn.edit-active:hover {
            background: #4a5ab0;
        }
        /* ── Actions column ── */
        .actions {
            display: flex;
            gap: 4px;
            align-items: center;
            padding-top: 4px;
        }
        .action-btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            color: var(--primary-color);
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .action-btn:hover {
            background: var(--secondary-background-color);
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .action-btn.test-btn {
            color: #2e7d32;
            border-color: rgba(46, 125, 50, 0.3);
        }
        .action-btn.test-btn:hover {
            background: rgba(46, 125, 50, 0.08);
        }
        .action-btn.learn-btn {
            color: #fff;
            background: #2e7d32;
            border-color: #2e7d32;
        }
        .action-btn.learn-btn:hover {
            background: #1b5e20;
        }
        .action-btn.badge-btn {
            color: var(--secondary-text-color, #999);
            border-color: var(--divider-color);
            font-size: 0.65rem;
            min-width: 50px;
            text-align: center;
        }
        .action-btn.badge-btn[data-mapped] {
            color: var(--primary-color);
            border-color: var(--primary-color);
            background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.08);
        }
        .action-btn.badge-btn:hover {
            background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.12);
        }
        .action-btn.trigger-btn {
            color: #b89930;
            border-color: rgba(184, 153, 48, 0.3);
        }
        .action-btn.trigger-btn:hover {
            background: rgba(184, 153, 48, 0.08);
        }
        .action-btn.trigger-btn.trigger-on {
            color: #fff;
            background: #b89930;
            border-color: #b89930;
        }
        .action-btn.trigger-btn.trigger-on:hover {
            background: #a08328;
        }
        .action-btn.delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.25);
        }
        .action-btn.delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
        .action-btn.tx-btn {
            min-width: 46px;
            text-align: center;
        }
        .action-btn.tx-btn.tx-raw-on {
            color: #fff;
            background: #6a5acd;
            border-color: #6a5acd;
        }
        .action-btn.tx-btn.tx-raw-on:hover {
            background: #5847b8;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-command-row": IrCommandRow;
    }
}
