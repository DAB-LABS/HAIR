/**
 * One row in the device-detail command checklist.
 * - Captured commands show protocol info plus Test / Delete actions and an action badge.
 * - Unlearned templates show a single Learn button.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import type { IRCommand } from "./types.js";

// mdi:content-copy -- shared view/edit glyph (matches the signal rows).
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";
// mdi:repeat -- stubbed per-command repeat indicator (Feature 7, deferred).
const ICON_REPEAT =
    "M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z";

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

    @state() private _editingName = false;
    @state() private _draftName = "";

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

    private _startRename(e: Event): void {
        if (!this.command || this.busy) return;
        e.stopPropagation();
        this._draftName = this.command.name;
        this._editingName = true;
        void this.updateComplete.then(() => {
            const input =
                this.shadowRoot?.querySelector<HTMLInputElement>(".name-input");
            input?.focus();
            input?.select();
        });
    }

    private _commitRename(): void {
        if (!this._editingName) return;
        const name = this._draftName.trim();
        this._editingName = false;
        if (!this.command || !name || name === this.command.name) return;
        this.dispatchEvent(
            new CustomEvent("rename-command", {
                detail: { command: this.command, name },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _onRenameKeydown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            e.preventDefault();
            this._commitRename();
        } else if (e.key === "Escape") {
            this._editingName = false;
        }
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
                    <div class="name">
                        ${learned
                            ? this._editingName
                                ? html`<input
                                      class="name-input"
                                      type="text"
                                      .value=${this._draftName}
                                      @input=${(e: Event) =>
                                          (this._draftName = (
                                              e.target as HTMLInputElement
                                          ).value)}
                                      @keydown=${this._onRenameKeydown}
                                      @blur=${this._commitRename}
                                  />`
                                : html`<span
                                      class="editable-name"
                                      title="Click to rename"
                                      @click=${this._startRename}
                                      >${this.templateName}<span class="rename-pencil"
                                          >&#9998;</span
                                      ></span
                                  >`
                            : html`${this.templateName}`}
                        ${learned &&
                        this.command &&
                        this.command.repeat_count > 1
                            ? html`<span
                                  class="repeat-indicator"
                                  title="Repeats the IR frame ${this.command
                                      .repeat_count - 1} extra time(s)"
                                  ><ha-svg-icon
                                      .path=${ICON_REPEAT}
                                  ></ha-svg-icon
                                  >${this.command.repeat_count}</span
                              >`
                            : ""}
                    </div>
                    <div class="meta">
                        ${diamonds
                            ? diamonds
                            : learned
                              ? html`${this._commandLabel()}`
                              : html`<span class="muted">Not yet learned</span>`}
                    </div>
                </div>
                <div class="actions">
                    ${learned
                        ? html`
                              <button
                                  class="icon-btn edit-btn"
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("edit-command")}
                                  title="View or edit code"
                              ><ha-svg-icon
                                      class="edit-glyph"
                                      .path=${ICON_COPY}
                                  ></ha-svg-icon></button>
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
            align-items: center;
            gap: 12px;
            padding: 8px 10px;
            /* Match the page background so the long horizontal command
               strips visually merge with the device-detail backdrop
               instead of reading as highlighted bands. Themes that
               distinguish primary vs secondary background colors will
               carry both through naturally; themes that keep them
               equal end up with the same visual effect. The hover
               state on action buttons inside the row still uses
               --secondary-background-color so the button hover remains
               distinguishable. */
            background: var(--primary-background-color);
            border-radius: 4px;
        }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .name {
            font-weight: 500;
        }
        .editable-name {
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .rename-pencil {
            font-size: 0.7rem;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .editable-name:hover .rename-pencil {
            opacity: 1;
        }
        .name-input {
            font-size: inherit;
            font-weight: 500;
            font-family: inherit;
            border: none;
            border-bottom: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-text-color);
            outline: none;
            padding: 0 0 1px;
            min-width: 120px;
        }
        .repeat-indicator {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            margin-left: 8px;
            font-size: 0.72rem;
            font-weight: 600;
            color: #e65100;
            vertical-align: middle;
        }
        .repeat-indicator ha-svg-icon {
            --mdc-icon-size: 13px;
        }
        .icon-btn {
            background: none;
            border: none;
            padding: 2px;
            display: inline-flex;
            align-items: center;
            cursor: pointer;
            color: var(--secondary-text-color);
        }
        .icon-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .icon-btn:hover:not(:disabled) {
            color: var(--primary-text-color);
        }
        .edit-glyph {
            --mdc-icon-size: 10px;
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
        .actions {
            display: flex;
            gap: 4px;
            align-items: center;
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
        /* TX-mode toggle: AUTO (canonical decoded timings) is the neutral
           default; RAW (replay captured timings) reads as the active,
           deliberately-chosen override. */
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
