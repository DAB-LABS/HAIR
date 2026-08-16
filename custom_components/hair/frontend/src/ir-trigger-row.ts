/**
 * One row in the HAIR Triggers drawer's expanded detail (Trigger
 * Remotes signpost 1, Track B item 7). Sibling component to
 * ir-command-row.ts, and deliberately built to the same two-line
 * anatomy that command-row-restructure.md settled: a full-height-
 * stable top line plus a diamond fingerprint isolated on its own
 * wrapping line underneath.
 *
 * RULED anatomy (trigger-remotes-mockup-t2a.html, owner-approved
 * 2026-08-12, three iteration rounds -- this supersedes the earlier
 * anatomy sketched in ux.md 3.3 and the design brief, both of which
 * predate the final pass and disagree with it on where the protocol
 * chip, min_hits knob, and the hit-count/last-fired readout live):
 *
 *   Line 1 LEFT (name cluster): drag grip (slotted, see below), name
 *     with in-place rename, the min_hits "button press count" knob
 *     (icon+number, ir-tx-knobs.ts's ICON_REPEAT glyph reused here --
 *     shown only when min_hits > 1, same conditional that knob's own
 *     send-count already uses), then the protocol chip. Name and
 *     arming facts read together.
 *   Line 1 RIGHT (trailing cluster, pinned flush right via
 *     margin-left: auto): the receiver-scope chip when scoped (drawer
 *     semantics -- the picker stays per-trigger HERE, not a header
 *     concept), the live hit count + last-fired read as ONE phrase
 *     inside a reserved, right-justified width (144px, the mockup's
 *     bench starting point -- see .alive-text below for why the WHOLE
 *     phrase is gated and not just the digit count), the enabled
 *     toggle, a hairline divider, then edit-left-of-delete per the
 *     settled six-surface anatomy (edit-button-pass.md).
 *   Line 2: S/L diamonds alone, full width, wrapping freely -- unlike
 *     command-row-restructure.md, the protocol chip and the aliveness
 *     readout stay UP on line 1 here rather than following the
 *     diamonds down.
 *
 * NO Test chip (ux.md 3.3, deliberate absence -- a trigger cannot be
 * fired on demand; the brief's own words: "leave the absence honest").
 *
 * The drag grip is a light-DOM <slot>, not drawn in this component's
 * own shadow DOM -- SortableJS's ``handle`` option matches against the
 * light DOM tree from the drag gesture's real event target, and a
 * shadow-encapsulated icon is invisible to that traversal. Same
 * technique ir-command-row.ts's own status slot uses; see
 * ir-device-list.ts for the supplied `<ha-svg-icon slot="grip">`.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import {
    ICON_TRASH,
    TRASH_VIEWBOX,
    trashButtonStyles,
    editButtonStyles,
    renderEditBtn,
} from "./ir-icons.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";
import { bloomStyles } from "./ir-bloom-styles.js";
import "./ir-protocol-chip.js";
import type {
    IRTrigger,
    PinMapEntry,
    ReceiverInfo,
} from "./types.js";
import { PIN_BLUE } from "./ir-pin-flag.js";

// mdi:repeat -- imported verbatim from ir-tx-knobs.ts's own (unexported)
// ICON_REPEAT, reused here for the min_hits "button press count" knob
// (owner ruling 2026-08-13: same icon+number idiom, not a text badge).
const ICON_MIN_HITS =
    "M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z";

@customElement("ir-trigger-row")
export class IrTriggerRow extends LitElement {
    @property({ attribute: false }) public trigger!: IRTrigger;
    /** Resolves receiver_entity_ids to friendly names for the scope chip. */
    @property({ attribute: false }) public receivers: ReceiverInfo[] = [];
    @property({ type: Boolean }) public busy = false;
    /** True while this row's fire-bloom glow is active (see
     *  ir-bloom-styles.ts's BloomTracker; the parent owns the sequence). */
    @property({ type: Boolean }) public bloom = false;
    /** Signpost 4, Track 4: what this trigger drives on the owning
     *  remote's pinned devices, already resolved to names by the
     *  backend (see TriggerRemoteInfo.pin_map -- the frontend has no
     *  device commands to resolve against). */
    @property({ attribute: false }) public mappings: PinMapEntry[] = [];
    /** True when the owning remote has at least one pinned device.
     *  Gates the whole treatment, so an unpinned remote's rows stay
     *  quiet instead of every one of them reading "unmapped". */
    @property({ type: Boolean }) public showMappings = false;

    @state() private _editingName = false;
    @state() private _draftName = "";

    private _emit(name: string, e?: Event): void {
        const buttonRect =
            (e?.currentTarget as HTMLElement | undefined)?.getBoundingClientRect() ??
            null;
        this.dispatchEvent(
            new CustomEvent(name, {
                detail: { trigger: this.trigger, buttonRect },
                bubbles: true,
                composed: true,
            }),
        );
    }

    // ---------------------------------------------------------------
    // Inline rename (riding alias history server-side; see
    // device_trigger.py -- this row just sends the new name)
    // ---------------------------------------------------------------

    private _startRename(e: Event): void {
        if (this.busy) return;
        e.stopPropagation();
        this._draftName = this.trigger.name;
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
        if (!name || name === this.trigger.name) return;
        this.dispatchEvent(
            new CustomEvent("rename-trigger", {
                detail: { trigger: this.trigger, name },
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

    // ---------------------------------------------------------------
    // Diamonds (S/L fingerprint) -- same Pronto-hex decode as
    // ir-command-row.ts / ir-trigger-dialog.ts. Not extracted to a
    // shared helper in this pass (restraint discipline: this commit
    // adds a row, it does not go refactor two existing components
    // that already carry their own copy).
    // ---------------------------------------------------------------

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

    private _renderDiamonds() {
        const { protocol, code } = this.trigger;
        if (protocol?.toUpperCase() !== "PRONTO" || !code) return nothing;
        const arr = this._prontoSlArray(code);
        if (!arr) return nothing;
        return html`<span class="diamonds">${arr.map((isLong) =>
            isLong
                ? html`<span class="diamond long">&#9670;</span>`
                : html`<span class="diamond short">&#9671;</span>`
        )}</span>`;
    }

    // ---------------------------------------------------------------
    // Receiver scope (drawer-only per-trigger scoping, v0.5.7)
    // ---------------------------------------------------------------

    private _friendly(entityId: string): string {
        const match = this.receivers.find((r) => r.entity_id === entityId);
        return match?.name ?? entityId;
    }

    /** The pin readout: one chip per pinned device this trigger
     *  drives, or a single "unmapped" when the remote is pinned and
     *  nothing on those devices matches this trigger's content. The
     *  second case is the honest answer rather than a gap -- a user
     *  who pins two devices needs to see which buttons found nothing
     *  on them. */
    private _renderMappings() {
        if (!this.showMappings) return nothing;
        if (this.mappings.length === 0) {
            return html`<span class="pin-chip unmapped"
                title=${t("trow.unmapped_title")}
                >${t("trow.unmapped")}</span
            >`;
        }
        return html`${this.mappings.map(
            (m) => html`<span
                class="pin-chip"
                style="border-color:${PIN_BLUE};color:${PIN_BLUE}"
                title=${t("trow.drives_title", {
                    device: m.device_name,
                    command: m.command_name,
                })}
                >&#8594;&nbsp;${t("trow.drives", {
                    device: m.device_name,
                    command: m.command_name,
                })}</span
            >`,
        )}`;
    }

    private _renderScope() {
        const ids = this.trigger.receiver_entity_ids ?? [];
        if (ids.length === 0) return nothing;
        return html`${ids.map(
            (id) => html`<span class="scope-chip">${this._friendly(id)}</span>`,
        )}`;
    }

    // ---------------------------------------------------------------
    // Aliveness readout: hit count + last fired, one reserved-width,
    // right-justified phrase (see .alive-text below for why the whole
    // phrase is gated, not just the digit count).
    // ---------------------------------------------------------------

    /** Relative time like "2 min ago". Same four-tier shape as
     *  ir-signal-monitor.ts's own (unexported) relTime -- a third
     *  small local copy, matching the precedent ir-mirror.ts's own
     *  differently-formatted relShort already set rather than forcing
     *  a cross-module extraction for one pure four-line function. */
    private _relTime(iso: string | null): string {
        if (!iso) return "";
        try {
            const diff = Date.now() - new Date(iso).getTime();
            if (diff < 60_000) return t("rel.just_now");
            if (diff < 3_600_000)
                return t("rel.min_ago", { count: Math.floor(diff / 60_000) });
            if (diff < 86_400_000)
                return t("rel.h_ago", { count: Math.floor(diff / 3_600_000) });
            return t("rel.d_ago", { count: Math.floor(diff / 86_400_000) });
        } catch {
            return "";
        }
    }

    private _renderAlive() {
        const hits = this.trigger.fire_count;
        const body =
            hits > 0
                ? html`<span class="hit-n">${hits}</span> ${tp(
                      "sniffer.hit_word",
                      hits,
                  )} &middot; ${this._relTime(this.trigger.last_fired_at)}`
                : t("trow.never_fired");
        return html`<span class="alive-text">${body}</span>`;
    }

    render() {
        const trig = this.trigger;
        const minHits = trig.min_hits;
        return html`
            <div
                class="trow ${trig.enabled ? "" : "disabled"} ${this.bloom
                    ? "bloom"
                    : ""}"
            >
                <div class="trow-top">
                    <div class="trow-grip">
                        <slot name="grip"></slot>
                    </div>
                    <div class="trow-namewrap">
                        ${this._editingName
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
                                  ?disabled=${this.busy}
                              />`
                            : html`<span
                                  class="trow-name editable-name"
                                  title=${t("cmdrow.rename")}
                                  @click=${this._startRename}
                                  >${trig.name}<span class="rename-pencil"
                                      >&#9998;</span
                                  ></span
                              >`}
                        ${minHits > 1
                            ? html`<span
                                  class="min-hits-knob"
                                  title=${t("trow.min_hits_tooltip", {
                                      count: minHits,
                                  })}
                                  ><ha-svg-icon
                                      .path=${ICON_MIN_HITS}
                                  ></ha-svg-icon
                                  >${minHits}</span
                              >`
                            : nothing}
                        <ir-protocol-chip
                            .protocol=${trig.protocol}
                        ></ir-protocol-chip>
                    </div>
                    <div class="trow-controls">
                        ${this._renderMappings()} ${this._renderScope()}
                        ${this._renderAlive()}
                        <button
                            class="action-btn ${trig.enabled
                                ? "assign-btn"
                                : "dismiss-btn"} toggle-btn"
                            ?disabled=${this.busy}
                            @click=${(e: Event) => this._emit("toggle-enabled", e)}
                        >${trig.enabled ? t("devlist.on") : t("devlist.off")}</button>
                        <span class="ctrl-divider"></span>
                        <span class="edit-trash-group">
                            ${renderEditBtn(
                                (e: Event) => this._emit("edit-trigger", e),
                                t("cmdrow.edit_trigger"),
                                this.busy,
                            )}
                            <button
                                class="trash-btn"
                                title=${t("devlist.delete_trigger")}
                                aria-label=${t("devlist.delete_trigger")}
                                ?disabled=${this.busy}
                                @click=${(e: Event) => this._emit("delete-trigger", e)}
                            >
                                <ha-svg-icon
                                    .path=${ICON_TRASH}
                                    .viewBox=${TRASH_VIEWBOX}
                                ></ha-svg-icon>
                            </button>
                        </span>
                    </div>
                </div>
                <div class="trow-diamonds">${this._renderDiamonds()}</div>
            </div>
        `;
    }

    static styles = [
        trashButtonStyles,
        editButtonStyles,
        actionChipStyles,
        bloomStyles,
        css`
            :host {
                display: block;
            }
            :host(:not(:last-of-type)) {
                margin-bottom: 4px;
            }
            .trow {
                padding: 8px 10px;
                border-radius: 4px;
                background: var(--primary-background-color);
                border: 1px solid transparent;
            }
            .trow.disabled {
                opacity: 0.5;
            }
            .trow.disabled .diamond {
                opacity: 0.7;
            }
            .trow-top {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }
            .trow-grip {
                flex: 0 0 24px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .trow-namewrap {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
                flex: 1 1 auto;
                min-width: 0;
                font-weight: 500;
            }
            .trow-name {
                font-size: 0.92rem;
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
            /* Out of layout flow so it reserves no width, matching
               ir-command-row.ts's own rename pencil -- the name-to-chip
               gap stays the true flex gap regardless of hover state. */
            .rename-pencil {
                position: absolute;
                left: 100%;
                margin-left: 4px;
                top: 50%;
                transform: translateY(-50%);
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
                font-size: 0.92rem;
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
            /* Button-press-count (min_hits) knob -- same icon+number
               idiom as ir-tx-knobs.ts's own send-count glyph. */
            .min-hits-knob {
                display: inline-flex;
                align-items: center;
                gap: 1px;
                font-size: 9px;
                font-weight: 600;
                color: var(--warning-color, #ff9800);
                font-variant-numeric: tabular-nums;
                white-space: nowrap;
            }
            .min-hits-knob ha-svg-icon {
                --mdc-icon-size: 12px;
            }
            .trow-controls {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-left: auto;
            }
            /* Pin readout (signpost 4, Track 4). Shares the scope
               action idiom (mobile-polish ruling 2026-08-04): arrow
               plus name, mapped-blue text, a LABEL and not a button --
               no border, no background, no padding. It states where a
               press goes; it is not something to press. The mapped
               variant takes PIN_BLUE inline from ir-pin-flag.ts rather
               than duplicating the token here (owner ruling
               2026-08-15: do not merge the pin and Sniffer blues).
               "unmapped" reads in the same ruling's empty-gray -- it
               is an absence, not a second colour of fact. */
            .pin-chip {
                font-size: 11px;
                white-space: nowrap;
            }
            .pin-chip.unmapped {
                color: var(--secondary-text-color);
            }
            .scope-chip {
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                border: 1px solid var(--divider-color);
                border-radius: 4px;
                padding: 2px 7px;
                color: var(--secondary-text-color);
                white-space: nowrap;
            }
            /* The toggle reuses actionChipStyles' semantic pair (ON =
               assign-btn's green, OFF = dismiss-btn's neutral gray)
               rather than a third bespoke on/off pill -- Track B's own
               sequencing note calls for this row to share
               actionChipStyles. No local size override -- the toggle
               takes the exact same chip weight (padding, font-size,
               1px border stroke) as every other actionChipStyles
               consumer, including the device detail's Test/Trigger
               buttons (owner ruling 2026-08-13: "same weight, so same
               size and stroke and everything"). */
            .ctrl-divider {
                width: 1px;
                align-self: stretch;
                background: var(--divider-color);
                margin: 0 1px;
                opacity: 0.8;
            }
            .edit-trash-group {
                display: inline-flex;
                align-items: center;
                gap: 0;
            }
            /* Live hit count + last-fired ("the aliveness fact") --
               owner ruling 2026-08-13, amended the same day (bench
               catch): gating just the digit count wasn't enough --
               "just now" vs "4 min ago" vs "never fired" vary by up to
               ten characters, so the TOGGLE right after this block was
               still sliding left/right with it even though edit/delete
               (pinned via .trow-controls' margin-left: auto) looked
               stable. Fix: reserve the WHOLE phrase's width, not just
               the number, and right-justify inside it -- the toggle's
               own left edge is what needs to be gated. 144px is the
               mockup's bench starting point ("999 hits · 59 min ago"
               with room to spare); tune against real copy on the bench. */
            .alive-text {
                display: inline-block;
                width: 144px;
                flex: 0 0 144px;
                font-size: 0.74rem;
                color: var(--secondary-text-color);
                white-space: nowrap;
                text-align: right;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .alive-text .hit-n {
                color: var(--primary-text-color);
                font-weight: 500;
                font-variant-numeric: tabular-nums;
            }
            /* Line 2: diamonds alone, full width, wrapping freely.
               36px aligns the first diamond under the name's first
               letter: the grip's flex-basis (24px) + .trow-top's gap
               (12px). */
            .trow-diamonds {
                margin-left: 36px;
                margin-top: 4px;
                min-height: 1px;
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
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-trigger-row": IrTriggerRow;
    }
}
