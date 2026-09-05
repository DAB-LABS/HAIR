/**
 * One row in the device-detail command checklist.
 * - Captured commands show protocol info plus Test / Delete actions and an action-mapping label.
 * - Unlearned templates show a single Learn button.
 *
 * TWO-LINE ANATOMY (command-row-restructure.md, commit 1 of 2, rides
 * 0.9.8): the row used to be a 3-column grid (status | info | actions)
 * where "info" stacked the name above whatever .meta held (a plain
 * protocol:code label, "not learned," or -- for a PRONTO command -- a
 * S/L diamond pattern that can wrap to several lines for a long
 * AC/matrix code). That variable-height diamond stack was the actual
 * bug: the drag grip in the status column sat vertically centered
 * against the row's full height, so on a tall row it drifted well
 * below the name it's supposed to sit beside.
 *
 * The fix is a deliberately minimal rearrangement, not a redesign:
 * every control below keeps its exact component, styling, hover
 * state, and behavior from before this pass -- only DOM position
 * changes, and only the grip's. Line one (.top-line) is a flex row
 * that always stays whatever height the name needs: grip, then the
 * name (with its rename pencil) in .name-line, then the SAME
 * .actions cluster as before this pass -- protocol chip, edit,
 * mapping label, TEST, TRIGGER, delete -- pushed to the far right via
 * margin-left: auto (owner ruling 2026-08-09: the chip and label
 * stay put on the right; only the grip moves). Line two (.meta) is
 * what used to be nested under the name -- diamonds, the plain
 * label, or "not learned" -- now a full-width block of its own
 * underneath, indented to align under the name's first letter, so a
 * long diamond pattern wraps in its own space without ever touching
 * line one's height. flex-wrap on .top-line is the whole answer to
 * narrow widths (RULED: no container queries, no collapse logic this
 * pass -- the wrap itself is the win).
 *
 * EDIT GLYPH + ACTION-MAPPING LABEL (edit-and-actions-coding-plan.md,
 * 2026-08-11, device-detail bench pilot): the edit button now renders
 * via the shared renderEditBtn helper (ir-icons.ts) rather than a
 * local ICON_COPY button. BENCH RULING (2026-08-11, first look at
 * VM999): the button moved again -- immediately left of the trash
 * can, matching edit-button-pass.md's general position rule for
 * every other surface -- after the initial pass kept it in the
 * pre-existing restructured slot per the standing sequencing ruling
 * and the owner found it read too small and too far from delete on
 * the actual bench. This also means commit 3's five-surface rollout
 * now matches this row's position exactly, so there is no longer a
 * device-detail exception to carry forward. The mapping badge is a
 * link-style label, not a button: blue "-> action name" when mapped,
 * muted gray "Map action" when empty. mobile-polish.md 2.2's
 * hide-when-equal rule (skip the label when the mapped action's name
 * equals the command name) shipped in the first bench pass and was
 * DROPPED the same day (owner ruling 2026-08-11, second look at
 * VM999): most self-descriptive command names (Power On, Volume Up,
 * Mute) are mapped to an action of the same name, so hiding on match
 * thinned out most of the list rather than the occasional row --
 * every mapped command now shows what it is mapped to, unconditionally.
 * THIRD bench ruling (2026-08-11): the label lost the word "Map" --
 * it now reads plain "Action" empty / "-> action name" mapped
 * (cmdrow.map_action_label; devdetail.map_action, the popover's own
 * title, is a separately-translated string left untouched this pass)
 * -- and gained a bit of trailing margin so it does not crowd TEST.
 * A "returning arrow" glyph the owner recalled from an earlier comp,
 * to replace the plain "->" here, was not found in either spec doc
 * (edit-and-actions-coding-plan.md, mobile-polish.md 2.2 -- both say
 * only "small arrow glyph"); left as-is pending the owner tracking
 * that comp down.
 * FOURTH bench ruling (2026-08-11): edit glyph 20px -> 22px, still
 * catching up to the trash can's visual weight (see ir-icons.ts).
 * Edit and trash now sit in their own .edit-trash-group wrapper with
 * a zero gap, so their hover boxes butt directly against each other
 * rather than sitting the shared .actions gap (4px) apart. The
 * action-mapping label's fixed-width reservation (actionBadgeLabel /
 * actionBadgeFontPx) is reinstated -- dropped in commit 2 on the
 * theory that a plain label was free to change width row to row, but
 * the owner wants every row's action column, and everything after
 * it, landing at the same x position, same as the old bordered
 * .badge-btn did (git 159b6b3^) before the link-A swap.
 * FIFTH bench ruling (2026-08-11): settles the empty-state glyph
 * question left open after the "U-turn" comp didn't turn up
 * anywhere searchable (checked the repo's own screenshot assets,
 * images/screenshots/action-mapping.png and neighbors -- all three
 * predate the link-A redesign) -- a plain "+" before "Action"
 * instead, same muted gray as the rest of the empty state
 * (.map-plus).
 * The remaining mobile-polish.md 2.2 items (pencil removal, hairline,
 * TEST vs SEND) stay queued for their own pass.
 *
 * CLIMATE PRESET STAR (climate-presets-star-handoff.md, owner-approved
 * 2026-08-17): AC rows gain one more member of .actions, between
 * TRIGGER and the edit/trash pair -- a star that toggles the command
 * into a Home Assistant preset on the device's climate entity, named
 * exactly what the row is named. Grey outline at rest, solid #4dabf7
 * once starred, edit's own hover wash in either state; no gold
 * anywhere (the plan's original #f5a623 is retired, not parked). It
 * reuses .edit-btn's box wholesale rather than copying its numbers
 * (see renderStarBtn in ir-icons.ts), and it sits INSIDE
 * .edit-trash-group, butted against the pencil at zero gap like the
 * pencil is against the can -- owner bench ruling 2026-08-17, which
 * supersedes the handoff's "deliberately NOT fused" line: on the box
 * the 4px read as the star drifting away from a tight pair. The
 * group's own 4px from TRIGGER is untouched. One click toggles, no
 * dialog.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import {
    ICON_TRASH,
    TRASH_VIEWBOX,
    trashButtonStyles,
    editButtonStyles,
    starButtonStyles,
    renderEditBtn,
    renderStarBtn,
} from "./ir-icons.js";
import "./ir-protocol-chip.js";

// The comb, from images/comb.svg -- the same mark the closet uses for
// byte doubt. A row wearing it and a closet row wearing it are making
// the same kind of statement, so they use the same symbol rather than
// two vocabularies for one idea.
const ICON_COMB =
    "M367.808,240.512c-37.163-31.232-58.475-60.565-58.475-80.512c0-23.019,5.568-37.077,10.944-50.667c5.099-12.885,10.389-26.24,10.389-45.333c0-43.669-23.723-64-74.667-64s-74.667,20.331-74.667,64c0,19.093,5.291,32.448,10.389,45.355c5.376,13.589,10.944,27.648,10.944,50.667c0,19.925-21.312,49.259-58.475,80.512c-17.067,14.357-26.859,35.264-26.859,57.344v203.456c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667v-160H160v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667S224,507.221,224,501.333v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160H288v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667V297.856C394.667,275.776,384.875,254.891,367.808,240.512z M373.333,320H138.667v-22.123c0-15.765,7.019-30.741,19.264-41.024C188.075,231.509,224,194.133,224,160c0-27.093-6.613-43.797-12.437-58.517c-4.779-12.075-8.896-22.464-8.896-37.483c0-27.669,8.491-42.667,53.333-42.667S309.333,36.331,309.333,64c0,15.019-4.117,25.408-8.896,37.483C294.613,116.203,288,132.885,288,160c0,34.133,35.925,71.509,66.069,96.853c12.245,10.304,19.264,25.259,19.264,41.024V320z";

import "./ir-tx-knobs.js";
import "./ir-count-dot.js";
import type { IRCommand } from "./types.js";

@customElement("ir-command-row")
export class IrCommandRow extends LitElement {
    @property({ attribute: false }) public templateName: string = "";
    @property({ attribute: false }) public command: IRCommand | null = null;

    /** Does this row carry a matrix state rather than a captured button?
     *
     * B2, and it pairs with the GH #134 send guard. A state row still
     * DECODES as something, often as a coincidence -- a long opaque AC
     * blob with a short addressed frame hiding inside it. The send path
     * now ignores that decode for these rows and always replays the
     * stored bytes, so a chip offering to toggle between decoded and
     * captured would be offering a choice that no longer has two sides.
     *
     * The chip still SAYS the protocol, because what a row decodes as is
     * true and useful; it just stops presenting as a control. That is
     * the read-only mode the chip already has for the fitting rows, so
     * this needs no new visual language.
     *
     * Both fields are read for the same reason the backend guard reads
     * both: a clone keeps source and drops matrix_cell, and a saved
     * STATE row has historically set source alone.
     */
    private get _isMatrixState(): boolean {
        return (
            this.command?.matrix_cell != null ||
            this.command?.source === "matrix"
        );
    }

    /** When the chip states the protocol rather than offering it.
     *
     * TWO REASONS, ONE MODE (GH #134). A matrix state row was the first:
     * it never re-encodes, so a toggle between decoded and captured has
     * no two sides. A row whose decode does not cover its own capture is
     * the second, and it is the same situation arrived at from the other
     * end -- the server has already decided this row transmits its
     * stored bytes, so the chip has nothing left to switch.
     *
     * THE VERDICT IS READ, NOT RECOMPUTED. There is no client-side rule
     * here for what covers what; ``decode_covers`` rides ``to_dict``
     * into the device payload and this reads it. Absent means not
     * judged and stays interactive, which is what every row shipped
     * before the verdict existed does.
     *
     * A STATE row gets no second cue out of this: it is already
     * informational, and one fact per row is the ruling.
     */
    private get _chipIsInformational(): boolean {
        return this._isMatrixState || this.command?.decode_covers === false;
    }
    @property({ type: Boolean }) public busy = false;

    /** Label of the mapped action (e.g. "Power On"), or empty/null if unmapped. */
    @property({ attribute: false }) public actionLabel: string | null = null;

    /** Whether this command already has an associated trigger. */
    @property({ type: Boolean }) public hasTrigger = false;

    /** Number of triggers bound to this command's signal (yellow dot count).
     * Falls back to hasTrigger (0/1) when the parent doesn't supply a count. */
    @property({ type: Number }) public triggerCount = 0;

    /** The widest label this device type's action list can render (with
     *  its arrow prefix), used as an invisible sizer so the link-A label
     *  never changes width row to row -- FOURTH bench ruling (2026-08-11):
     *  reinstated after commit 2 dropped this reservation on the theory
     *  that a plain label was allowed to change width; the owner wants
     *  every row's action column, TEST, TRIGGER, edit and trash all
     *  landing at the same x position instead, which needs the fixed
     *  width back. Null leaves the label sized to its own content. */
    @property({ attribute: false }) public actionBadgeLabel: string | null =
        null;
    /** Font size the sizer renders at, so the reserved width matches the
     *  size that label will really be drawn at. */
    @property({ attribute: false }) public actionBadgeFontPx: number | null =
        null;
    /** Font size for THIS row's visible label. Long labels step down so
     *  they read cleanly rather than crowding the actions cluster. */
    @property({ attribute: false }) public actionFontPx: number | null = null;

    /** Whether to show the action-mapping ("ACTIONS") button. Hidden for
     *  device types whose platform exposes no mappable feature actions
     *  (e.g. Other / the remote platform), where the popover would be empty. */
    @property({ type: Boolean }) public showActionMapping = true;

    /** Whether to show the climate-preset star. Decided per row by the
     *  parent, which passes AC device AND not a porthole row.
     *
     *  Flat rows and saved-state rows from "+ Command" both get one:
     *  those are real stored commands, and starring one is the whole
     *  gesture. PORTHOLE rows do not (owner ruling 2026-08-17,
     *  narrowing the plan's "all AC rows"): a porthole is a view onto
     *  a lattice cell the comb doubted, not a command of its own, so
     *  there is nothing stable for a preset to name -- editing the
     *  cell or repairing the row would leave the preset pointing at a
     *  coordinate rather than at a code the user chose. */
    @property({ type: Boolean }) public showStar = false;

    /** Whether THIS command is starred, i.e. currently a preset on the
     *  device's climate entity. Drives the solid-vs-outline glyph and
     *  which of the two titles the button carries. */
    @property({ type: Boolean }) public starred = false;

    @state() private _editingName = false;
    @state() private _draftName = "";

    /** Human-friendly label for a captured command (plain text fallback). */
    private _commandLabel(): string {
        const cmd = this.command!;
        if (cmd.protocol && cmd.code) {
            // The copyable form (GH #144). This label is the one place a
            // row shows the code itself rather than a name, so it is a
            // read surface like the editor box and serves the same form.
            return `${cmd.protocol}: ${cmd.code_export ?? cmd.code}`;
        }
        if (cmd.raw_timings?.length) {
            return t("cmdrow.raw_timings", { count: cmd.raw_timings.length });
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
    /**
     * What the comb actually found on this row.
     *
     * NEVER a generic "suspect" (bench 2026-08-03). The comb recorded a
     * class; saying only that something is wrong names a problem and
     * hides which one, and the person is about to decide whether to
     * test it, replace it, or leave it. Falls back to the plain line
     * only for a row flagged by a build that did not record the class.
     */
    private _combTitle(): string {
        const found = this.command?.comb_finding;
        if (!found) return t("cmdrow.comb_suspect");
        return `${t(`comb.class.${found}`)} -- ${t(`comb.what.${found}`)}`;
    }

    /** What a repair on this row actually did, for the chip's tooltip
     * (kickoff ruling: the repair reads alongside the comb flag,
     * never as more doubt). Falls back to the plain word if the date
     * cannot be parsed rather than showing nothing. */
    private _repairTitle(): string {
        const record = this.command?.hair_repair;
        if (!record) return "";
        let when = record.applied;
        try {
            when = new Date(record.applied).toLocaleString();
        } catch {
            // Keep the raw ISO string.
        }
        return t("cmdrow.repaired_tooltip", { date: when });
    }

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
        const showActionLabel = learned && this.showActionMapping;
        return html`
            <div class="row" data-learned=${learned ? "true" : "false"}>
                <div class="top-line">
                    <div class="status" aria-hidden="true">
                        <slot name="status"></slot>
                    </div>
                    <div class="name-line">
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
                                          title=${t("cmdrow.rename")}
                                          @click=${this._startRename}
                                          >${this.templateName}<span class="rename-pencil"
                                              >&#9998;</span
                                          ></span
                                      >`
                                : html`${this.templateName}`}
                            ${learned && this.command?.source === "matrix"
                                ? html`<span class="state-chip"
                                      >${t("devices.state_chip")}</span
                                  >`
                                : ""}
                            ${learned && this.command?.comb_suspect
                                ? html`<span
                                      class="comb-mark"
                                      title=${this._combTitle()}
                                  ><svg viewBox="0 0 512 512"><path
                                              d=${ICON_COMB}
                                          ></path></svg></span
                                  >`
                                : ""}
                            ${learned && this.command?.hair_repair
                                ? html`<span
                                      class="repair-chip"
                                      title=${this._repairTitle()}
                                      >${t("cmdrow.repaired")}</span
                                  >`
                                : ""}
                            ${learned && this.command
                                ? html`<ir-tx-knobs
                                      .sendCount=${this.command.send_count}
                                      .repeatCount=${this.command.repeat_count}
                                      .decoded=${!!this.command
                                          .decoded_protocol &&
                                      this.command.decode_covers !== false}
                                      .bypassed=${!!this.command.tx_force_raw}
                                  ></ir-tx-knobs>`
                                : ""}
                        </div>
                    </div>
                    <div class="actions">
                        ${learned
                            ? html`
                                  <div class="chip-col">
                                      ${this.command?.decoded_protocol
                                          ? html`<ir-protocol-chip
                                                .protocol=${this.command
                                                    .decoded_protocol}
                                                .bypass=${!!this.command
                                                    .tx_force_raw}
                                                ?interactive=${!this
                                                    ._chipIsInformational}
                                                ?disabled=${this.busy}
                                                @toggle-bypass=${() =>
                                                    this._emit("toggle-tx-raw")}
                                            ></ir-protocol-chip>`
                                          : ""}
                                  </div>
                                  ${showActionLabel
                                      ? html`<button
                                      class="map-action-label"
                                      ?data-mapped=${!!this.actionLabel}
                                      ?disabled=${this.busy}
                                      @click=${() => this._emit("map-action")}
                                      title=${t("cmdrow.map_action")}
                                      aria-label=${t("cmdrow.map_action")}
                                  >${this.actionBadgeLabel
                                          ? html`<span
                                                class="action-sizer"
                                                aria-hidden="true"
                                                style="font-size:${this
                                                    .actionBadgeFontPx ?? 10.5}px"
                                                ><span class="map-arrow"
                                                    >&#8594;</span
                                                ><span class="map-label"
                                                    >${this
                                                        .actionBadgeLabel}</span
                                                ></span
                                            >`
                                          : ""}<span class="action-visible"
                                          >${this.actionLabel
                                              ? html`<span
                                                    class="map-arrow"
                                                    aria-hidden="true"
                                                    >&#8594;</span
                                                ><span
                                                    class="map-label"
                                                    style=${this.actionFontPx
                                                        ? `font-size:${this.actionFontPx}px`
                                                        : ""}
                                                    >${this
                                                        .actionLabel}</span
                                                >`
                                              : html`<span
                                                    class="map-plus"
                                                    aria-hidden="true"
                                                    >+</span
                                                ><span class="map-label"
                                                    >${t(
                                                        "cmdrow.map_action_label",
                                                    )}</span
                                                >`}</span
                                      ></button>`
                                      : ""}
                                  <button
                                      class="action-btn test-btn"
                                      ?disabled=${this.busy}
                                      @click=${() => this._emit("test")}
                                  >${t("cmdrow.test")}</button>
                                  ${this.command?.comb_suspect
                                      ? ""
                                      : html`<button
                                      class="action-btn trigger-btn"
                                      ?disabled=${this.busy}
                                      @click=${(e: Event) => this._emit("toggle-trigger", e)}
                                      title=${this.hasTrigger ? t("cmdrow.edit_trigger") : t("cmdrow.create_trigger")}
                                  >${t("cmdrow.trigger")}<ir-count-dot
                                          color="yellow"
                                          .count=${this.triggerCount ||
                                          (this.hasTrigger ? 1 : 0)}
                                      ></ir-count-dot></button>`}
                                  <div class="edit-trash-group">
                                      ${this.showStar
                                          ? renderStarBtn(
                                                () =>
                                                    this._emit("star-toggle"),
                                                this.starred
                                                    ? t("cmdrow.star_remove")
                                                    : t("cmdrow.star_add"),
                                                this.starred,
                                                this.busy,
                                            )
                                          : ""}
                                      ${renderEditBtn(
                                          () => this._emit("edit-command"),
                                          t("cmdrow.edit_code"),
                                          this.busy,
                                      )}
                                      <button
                                          class="trash-btn"
                                          title=${t("cmdrow.delete_title")}
                                          aria-label=${t("cmdrow.delete_title")}
                                          ?disabled=${this.busy}
                                          @click=${() => this._emit("delete")}
                                      >
                                          <ha-svg-icon
                                              .path=${ICON_TRASH}
                                              .viewBox=${TRASH_VIEWBOX}
                                          ></ha-svg-icon>
                                      </button>
                                  </div>
                              `
                            : html`
                                  <button
                                      class="action-btn learn-btn"
                                      ?disabled=${this.busy}
                                      @click=${() => this._emit("learn")}
                                  >${t("cmdrow.learn")}</button>
                              `}
                    </div>
                </div>
                <div class="meta">
                    ${diamonds
                        ? diamonds
                        : learned
                          ? html`${this._commandLabel()}`
                          : html`<span class="muted">${t("cmdrow.not_learned")}</span>`}
                </div>
            </div>
        `;
    }

    static styles = [
        trashButtonStyles,
        editButtonStyles,
        // The star wears .edit-btn as well as .star-btn, so edit's box
        // and hover are its box and hover; this block only adds the
        // starred colour and the focus ring (ir-icons.ts).
        starButtonStyles,
        css`
        :host {
            display: block;
        }
        :host(:not(:last-of-type)) {
            margin-bottom: 4px;
        }
        /* Two-line anatomy (command-row-restructure.md, commit 1 of 2):
           .row stacks .top-line above .meta in a column flex rather
           than the old 3-column grid, so .meta (diamonds, the plain
           label, or "not learned") is a full-width block underneath
           that can wrap to any height without affecting .top-line's
           height or the grip's vertical position within it. */
        .row {
            display: flex;
            flex-direction: column;
            gap: 4px;
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
        /* Status | name-line | actions, same three-part shape the old
           grid had (32px | flexible | auto), now flex so narrow widths
           can wrap a whole cluster onto its own line instead of
           clipping it (RULED: flex-wrap is the entire narrow-width
           answer this pass -- no container queries, no collapse
           logic). align-items: center centers the grip against
           whatever .name-line's height actually is -- typically one
           line now that diamonds live in .meta instead, which is the
           fix for "the grip isn't next to the name." */
        .top-line {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 32px;
        }
        /* Holds only the name cluster (name, state chip, comb mark,
           tx-knobs). The protocol chip and mapping badge stay in
           .actions on the right, per the owner's 2026-08-01 ruling
           documented on .chip-col below -- the restructure moves the
           grip up here, not those. flex: 1 1 auto plus min-width: 0
           lets it shrink/wrap instead of pushing .actions off the
           row's right edge. */
        .name-line {
            display: flex;
            align-items: center;
            gap: 7px;
            flex-wrap: wrap;
            flex: 1 1 auto;
            min-width: 0;
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
        /* STATE origin chip (Cold Cuts): a command saved off the state
           matrix says so, in the matrix card's cold blue. Driven purely
           by command.source === "matrix" -- no extra payload key. */
        .state-chip {
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            line-height: 1.4;
            padding: 1px 5px;
            border-radius: 4px;
            color: #58a6d8;
            background: rgba(88, 166, 216, 0.12);
            border: 1px solid rgba(88, 166, 216, 0.45);
        }
        /* What the comb doubted, carried from the wig this command was
           adopted from. A dot, not a badge: it is a note about where the
           code came from, not a verdict on it, and the row still works
           exactly as any other row does. The tooltip carries the whole
           message. */
        .comb-mark {
            display: inline-flex;
            align-items: center;
            cursor: help;
            flex: none;
        }
        .comb-mark svg {
            width: 11px;
            height: 11px;
            fill: #d9a441;
        }
        /* A repair's record, alongside the comb mark rather than in
           place of it (kickoff ruling, 2026-08-27): a repaired row
           still wears its suspect flag, and this chip is what keeps
           that from reading as unresolved doubt. Same chip grammar as
           .state-chip, assign green rather than the state chip's
           blue. */
        .repair-chip {
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            line-height: 1.4;
            padding: 1px 5px;
            border-radius: 4px;
            color: #2e7d32;
            background: rgba(46, 125, 50, 0.12);
            border: 1px solid rgba(46, 125, 50, 0.45);
            cursor: help;
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
        /* 44px = .status's flex-basis (32px) + .top-line's gap
           (12px) -- the exact distance from the row's left edge to
           where .name-line (and the name's first letter) starts.
           Lining .meta up under that instead of the row's own edge
           is what puts the first diamond under the "P" of the name
           above it, rather than under the grip. */
        .meta {
            margin-left: 44px;
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
        /* The protocol chip sits in its own fixed cell to the left of the
           edit glyph (owner ruling, 2026-08-01), matching the Sniffer and
           Clipper rows. It used to sit beside the command name, which was
           the odd one out: every other list in the panel puts the chip in
           a column, and a name-anchored chip walks left and right down the
           list as names change length.

           88px is the same measurement the Sniffer uses, set by the widest
           label the chip can render (SYMPHONY12, 83.5px). A command that
           decoded nothing holds the cell EMPTY rather than absent, so the
           buttons after it stay on one vertical line. */
        .chip-col {
            flex: 0 0 88px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        /* Protocol chip / edit / mapping badge / TEST / TRIGGER /
           delete, pinned to the top line's right edge -- same cluster
           and order as before the restructure. margin-left: auto
           (rather than relying on the old grid's separate "auto"
           column) is what keeps this cluster right-aligned now that
           .top-line is a wrapping flex row -- when .name-line grows
           tall enough to need its own line, .actions still lands
           flush right on whichever line it ends up on. */
        /* flex-wrap here is the missing half of the ruling above. .top-line
           wraps, so .actions can drop onto a line of its own -- but the
           cluster itself was an unbreakable 263px, so on a narrow row it
           overflowed .row's right edge whether it wrapped or not, and the
           trash can ended up sitting outside the card.

           It read as a 320px-only problem in Chrome, where the cluster
           fit a 393px row with 10px to spare. It is not: 10px of slack is
           inside the margin by which font metrics vary between engines.
           iOS Safari does not have Roboto and falls back to a wider face,
           which spent that slack and put the trash outside the card on a
           real iPhone at a width Chrome rendered as clean. Reported from
           a phone screenshot, 2026-08-23.

           Wrapping removes the fixed-width assumption instead of buying
           back a few pixels, so it holds for any face at any width -- it
           survives a 0.25em letter-spacing stress at 320px, far past any
           real font difference. It costs nothing until it is needed:
           the row is 87px tall at 393px before and after, and only grows
           when the cluster genuinely has to take a second line.

           justify-content: flex-end keeps the wrapped line hard right,
           matching the band the owner approved on .signal-actions rather
           than inventing a second convention. */
        .actions {
            display: flex;
            gap: 4px;
            align-items: center;
            margin-left: auto;
            flex-wrap: wrap;
            justify-content: flex-end;
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
        /* The action-mapping label, link style (mobile-polish.md 2.2,
           owner ruling 2026-08-04): a LABEL, not a button -- no fill,
           no border, no button padding -- so only TEST/TRIGGER read as
           pressable. MAPPED is accent blue with a small arrow glyph
           ("-> turn on"); EMPTY is muted gray ("Action"). Shows
           unconditionally when mapped (owner ruling 2026-08-11, second
           bench look) -- an earlier pass hid the label when the mapped
           name equalled the command name, but that collapsed most of
           the list since self-descriptive names map to themselves.

           FIXED WIDTH, CENTERED (owner ruling 2026-08-11, fourth bench
           look): reinstates the pre-commit-2 badge-button's own
           technique (git 159b6b3^, .badge-btn/.badge-sizer) rather than
           inventing a new one -- .action-sizer and .action-visible are
           both direct children stacked in the SAME grid cell
           (grid-area: 1/1 below), so the (invisible) sizer's width sets
           the column's width in the font actually rendered, and the
           visible content centers within it. actionBadgeLabel /
           actionBadgeFontPx (ir-device-detail.ts) already computed the
           widest label this device type's action list can produce and
           its font tier; only the reservation on THIS side was missing
           since commit 2 dropped the old badge-button markup. The sizer
           always includes the arrow, since a row can go from unmapped
           to mapped without changing width -- see
           ir-device-detail.ts's _measureActionBadges for the matching
           box-model rework (no more padding/border chrome, an arrow's
           width instead). */
        .map-action-label {
            display: inline-grid;
            justify-items: center;
            align-items: center;
            background: none;
            border: none;
            padding: 0;
            /* Extra breathing room before TEST (bench ruling 2026-08-11,
               third look): .actions' own 4px flex gap read too tight
               between a plain-text label and the first real button --
               this only widens the label's own trailing edge, so the
               rest of the cluster (chip/test/trigger/edit/trash) keeps
               the standard 4px. */
            margin-right: 6px;
            font-size: 0.75rem;
            font-family: inherit;
            cursor: pointer;
            color: var(--secondary-text-color, #999);
        }
        .map-action-label > * {
            grid-area: 1 / 1;
        }
        .action-sizer {
            visibility: hidden;
            pointer-events: none;
        }
        .action-sizer,
        .action-visible {
            display: inline-flex;
            align-items: center;
            gap: 3px;
        }
        .map-action-label:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .map-action-label[data-mapped] {
            color: var(--primary-color);
        }
        .map-arrow {
            font-size: 0.8em;
        }
        /* Empty-state glyph (owner ruling 2026-08-11, fifth bench look):
           settles the "little glyph" question from the previous round --
           a plain "+" rather than chasing the U-turn arrow from an
           untraced comp. Stays the label's own muted gray; no separate
           color rule needed since it only ever renders in the unmapped
           branch, never alongside [data-mapped]'s blue. */
        .map-plus {
            font-size: 0.8em;
        }
        .map-action-label:hover:not(:disabled) .action-visible .map-label {
            text-decoration: underline;
        }
        /* Edit + trash, butted together (bench ruling 2026-08-11, fourth
           look): a wrapper with its own zero gap, rather than touching
           either button's own padding, so their hover boxes sit flush
           against each other -- the shared .actions gap (4px) still
           separates this pair, as one unit, from TRIGGER on its left.
           The star joined them (owner bench ruling 2026-08-17,
           superseding climate-presets-star-handoff.md's "deliberately
           NOT fused" line): at 4px out here it read further from the
           pencil than the pencil sits from the can, and the owner wants
           the three evenly spaced. Zero gap all round does that, and
           the group's own 4px from TRIGGER is unchanged, which is the
           relationship he asked to keep. */
        .edit-trash-group {
            display: inline-flex;
            align-items: center;
            gap: 0;
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
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-command-row": IrCommandRow;
    }
}
