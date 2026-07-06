/**
 * One row in the device-detail command checklist.
 * - Captured commands show protocol info plus Test / Delete actions and an action badge.
 * - Unlearned templates show a single Learn button.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import "./ir-count-dot.js";
import type { IRCommand } from "./types.js";

// mdi:content-copy -- shared view/edit glyph (matches the signal rows).
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";
// mdi:repeat -- whole-frame send-count indicator (orange).
const ICON_REPEAT =
    "M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z";
// mdi:dots-horizontal -- NEC ditto-count indicator (blue), paired with the
// decoded-protocol blue diamond.
const ICON_DITTO =
    "M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z";

@customElement("ir-command-row")
export class IrCommandRow extends LitElement {
    @property({ attribute: false }) public templateName: string = "";
    @property({ attribute: false }) public command: IRCommand | null = null;
    @property({ type: Boolean }) public busy = false;

    /** Label of the mapped action (e.g. "Power On"), or empty/null if unmapped. */
    @property({ attribute: false }) public actionLabel: string | null = null;

    /** Whether this command already has an associated trigger. */
    @property({ type: Boolean }) public hasTrigger = false;

    /** Number of triggers bound to this command's signal (yellow dot count).
     * Falls back to hasTrigger (0/1) when the parent doesn't supply a count. */
    @property({ type: Number }) public triggerCount = 0;

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

    private _emit(name: string, ev?: Event) {
        // When the originating click is passed (the Trigger button), include
        // the button's viewport rect so the parent can position the trigger
        // popover next to it (mirrors the catalog views' currentTarget rect).
        const buttonRect =
            (ev?.currentTarget as HTMLElement | undefined)?.getBoundingClientRect() ??
            null;
        this.dispatchEvent(
            new CustomEvent(name, {
                detail: {
                    templateName: this.templateName,
                    command: this.command,
                    buttonRect,
                },
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
                        ${learned && this.command?.decoded_fingerprint
                            ? html`<button
                                  class="tx-pill ${this.command.tx_force_raw ? "tx-raw-on" : ""}"
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("toggle-tx-raw")}
                                  title=${this.command.tx_force_raw
                                      ? "Replaying the captured Pronto. Click to transmit clean decoded packet timings instead."
                                      : "Transmitting clean decoded packet timings. Click to replay the captured Pronto instead."}
                              >${this.command.tx_force_raw
                                      ? "PRONTO"
                                      : this.command.decoded_protocol ?? "AUTO"}</button>`
                            : ""}
                        ${learned && this.command && this.command.send_count > 1
                            ? html`<span
                                  class="repeat-indicator"
                                  title="Sends this command ${this.command
                                      .send_count} times"
                                  ><ha-svg-icon
                                      .path=${ICON_REPEAT}
                                  ></ha-svg-icon
                                  >${this.command.send_count}</span
                              >`
                            : ""}
                        ${
                            // Hide the ditto chip when tx_force_raw is set: TX
                            // takes the raw replay path in that case and the
                            // dittos would not fire on the wire, so showing the
                            // chip would mislead about transmit behavior.
                            learned &&
                            this.command &&
                            this.command.repeat_count > 1 &&
                            this.command.decoded_protocol &&
                            !this.command.tx_force_raw
                            ? html`<span
                                  class="ditto-indicator"
                                  title="Appends ${this.command
                                      .repeat_count} NEC dittos"
                                  ><ha-svg-icon
                                      .path=${ICON_DITTO}
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
                                  class="action-btn trigger-btn"
                                  ?disabled=${this.busy}
                                  @click=${(e: Event) => this._emit("toggle-trigger", e)}
                                  title=${this.hasTrigger ? "Edit trigger" : "Create trigger"}
                              >Trigger<ir-count-dot
                                      color="yellow"
                                      .count=${this.triggerCount ||
                                      (this.hasTrigger ? 1 : 0)}
                                  ></ir-count-dot></button>
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
            display: flex;
            align-items: center;
            gap: 7px;
            flex-wrap: wrap;
            font-weight: 500;
        }
        .editable-name {
            cursor: pointer;
            position: relative;
            display: inline-flex;
            align-items: center;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .rename-pencil {
            /* Out of layout flow so it reserves no width: the name-to-pill
               gap stays the true 7px flex gap (matches pill-to-count).
               Tucked over the tail of the name; fades in on hover and never
               reaches the pill. */
            position: absolute;
            left: 100%;
            top: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
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
            font-size: 9px;
            font-weight: 600;
            /* Match the short-diamond orange; bare (no pill) on the name line.
               Vertically centered in line with the pill via the name flex.
               Slight knock-down to sit softer next to the pill. */
            color: var(--warning-color, #ff9800);
            opacity: 0.85;
        }
        .repeat-indicator ha-svg-icon {
            --mdc-icon-size: 10px;
        }
        .ditto-indicator {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            font-size: 9px;
            font-weight: 600;
            /* Match the long-diamond blue (decoded protocol); same size as the
               orange send-count indicator it sits beside. */
            color: var(--primary-color);
            opacity: 0.85;
        }
        .ditto-indicator ha-svg-icon {
            --mdc-icon-size: 10px;
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
            position: relative;
            color: #b89930;
            border-color: rgba(184, 153, 48, 0.3);
        }
        .action-btn.trigger-btn:hover {
            background: rgba(184, 153, 48, 0.08);
        }
        .action-btn.delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.25);
        }
        .action-btn.delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
        /* Protocol toggle on the name line: a tiny solid pill with white
           text. Blue fill = decoded protocol (NEC); orange fill = the
           captured-replay (PRONTO) override. Same tx_force_raw toggle. */
        .tx-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            height: 11px;
            border: none;
            border-radius: 999px;
            /* Slightly more top than bottom pad to optically center the caps. */
            padding: 1px 5px 0;
            font-size: 9px;
            font-weight: 500;
            font-family: inherit;
            letter-spacing: 0.03em;
            line-height: 1;
            color: #fff;
            /* Soften the fill (not the whole pill) so the white text stays
               crisp while the hue reads lighter / less poppy than the diamonds. */
            background: color-mix(in srgb, var(--primary-color) 82%, transparent);
            cursor: pointer;
            transition: opacity 150ms ease;
        }
        .tx-pill.tx-raw-on {
            /* Match the short-diamond orange, softened the same amount. */
            background: color-mix(in srgb, var(--warning-color, #ff9800) 82%, transparent);
        }
        .tx-pill:hover:not(:disabled) {
            opacity: 0.85;
        }
        .tx-pill:disabled {
            opacity: 0.5;
            cursor: default;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-command-row": IrCommandRow;
    }
}
