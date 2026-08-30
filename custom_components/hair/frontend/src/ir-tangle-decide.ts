/**
 * DECIDE -- "Requires your answer" (design brief v6 section 4, signed)
 * -- the duplicate-name portion only. See ir-tangle-section.ts's
 * bucketDecide doc comment for why: the brief's "keep or fix, this
 * code looks unusual" item type has no backend-provided data source
 * in the merged PR #129 today (advisories are explicitly informational
 * only, and every row already resolves to a FIX/LISTEN mechanic with
 * no ambiguous fourth case). Flagged for the owner; not guessed at.
 *
 * A duplicate pair renders as its two rows stacked adjacently. Each
 * row keeps its own SEND (the real ir-test-button, same as FIX),
 * inline click-to-edit rename, and the standard trash affordance --
 * "rename, send, and delete are all existing row behaviors; nothing
 * new is designed here" (brief section 4).
 *
 * ROUND THREE (owner rulings 2026-08-30):
 *
 * - The intro told the truth for a flat pair and not for a matrix one.
 *   Two cells with identical bytes do not share a NAME, they share a
 *   CODE, so a matrix pair gets its own sentence. And no surface here
 *   prints an id where words exist: the intro used to interpolate the
 *   command uuid, and the rename box used to prefill it (issue 20).
 * - Enter commits the TEXT and nothing else. Renaming used to resolve
 *   the whole pair and move on, which decides for the person; a green
 *   pair-level KEEP BOTH, live only once the two names actually
 *   differ, is what settles it now, and DELETE is still the other way
 *   out (issue 21).
 * - Delete is the panel's trash can with the panel's confirm dialog,
 *   the same pair a command row carries, instead of a text button and
 *   a bespoke inline bar.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { TangleRow, TangleTarget } from "./types.js";
import { t } from "./localize.js";
import { targetWords } from "./ir-tangle-copy.js";
import { installUnit, type MatrixUnit } from "./temperature.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";
import {
    ICON_TRASH,
    TRASH_VIEWBOX,
    editButtonStyles,
    renderEditBtn,
    trashButtonStyles,
} from "./ir-icons.js";
import "./ir-test-button.js";
import "./ir-confirm-dialog.js";

interface HassLike {
    [key: string]: unknown;
}

export interface DecidePairProp {
    cluster: { id: string };
    rows: TangleRow[];
}

@customElement("ir-tangle-decide")
export class IrTangleDecide extends LitElement {
    @property({ attribute: false }) public hass!: HassLike;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public pairs: DecidePairProp[] = [];
    /** The matrix's own native unit; display converts off it. */
    @property({ attribute: false }) public matrixUnit: MatrixUnit = "C";

    @state() private _snapshot: DecidePairProp[] = [];
    /** Settled pairs, and HOW they settled: a pair somebody kept did
     * not have a duplicate removed, and saying so would be a small
     * lie on the one surface whose whole job is telling two things
     * apart. */
    @state() private _resolved = new Map<string, "removed" | "kept">();
    @state() private _editing: string | null = null;
    @state() private _draftName = "";
    @state() private _confirmingDelete: string | null = null;
    @state() private _busy = new Set<string>();
    /** Names committed in this session, by row. The snapshot is frozen
     * at open, so without this a renamed row would keep showing the
     * name it arrived with and KEEP BOTH could never tell that the two
     * had stopped matching. */
    @state() private _names = new Map<string, string>();

    connectedCallback(): void {
        super.connectedCallback();
        this._snapshot = this.pairs;
    }

    private _emitMutated(wigWritten: boolean | null): void {
        this.dispatchEvent(
            new CustomEvent("tangle-mutated", {
                detail: { wigWritten },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private async _send(row: TangleRow): Promise<boolean> {
        const result = await this.api.tangleTestSend(this.deviceId, row.pronto);
        return result.heard;
    }

    /** What this row is called right now: the name committed here if
     * there is one, otherwise its own words. Never an id (issue 20).*/
    private _displayName(row: TangleRow): string {
        return this._names.get(row.id) ?? this._words(row.target);
    }

    private _startRename(row: TangleRow): void {
        this._editing = row.id;
        // The uuid used to be the prefill, so click-to-rename opened
        // on a field full of hex (issue 20).
        this._draftName = this._displayName(row);
    }

    private async _commitRename(pair: DecidePairProp, row: TangleRow): Promise<void> {
        const commandId = row.target.command_id;
        if (!commandId || !this._draftName.trim()) {
            this._editing = null;
            return;
        }
        this._busy = new Set(this._busy).add(row.id);
        try {
            const name = this._draftName.trim();
            await this.api.updateCommand({
                device_id: this.deviceId,
                command_id: commandId,
                name,
            });
            // THE TEXT, AND ONLY THE TEXT (issue 21). This used to
            // settle the whole pair and move on, which answers the
            // question on the person's behalf. KEEP BOTH is the
            // answer now, and it cannot arm until this has actually
            // changed something.
            this._names = new Map(this._names).set(row.id, name);
            this._editing = null;
            this._emitMutated(null);
        } finally {
            const next = new Set(this._busy);
            next.delete(row.id);
            this._busy = next;
        }
    }

    private async _confirmDelete(pair: DecidePairProp, row: TangleRow): Promise<void> {
        const commandId = row.target.command_id;
        if (!commandId) {
            this._confirmingDelete = null;
            return;
        }
        this._busy = new Set(this._busy).add(row.id);
        try {
            await this.api.deleteCommand(this.deviceId, commandId);
            this._resolved = new Map(this._resolved).set(
                pair.cluster.id, "removed",
            );
            this._confirmingDelete = null;
            this._emitMutated(null);
        } finally {
            const next = new Set(this._busy);
            next.delete(row.id);
            this._busy = next;
        }
    }


    /** Both of these are wanted, and saying so is the answer (issue
     * 21). Nothing is written: the rename already wrote, and a pair
     * kept on purpose has nothing left to save. */
    private _keepBoth(pair: DecidePairProp): void {
        this._resolved = new Map(this._resolved).set(pair.cluster.id, "kept");
    }

    private _anyBusy(pair: DecidePairProp): boolean {
        return pair.rows.some((row) => this._busy.has(row.id));
    }

    /** This row's words, in the panel's unit (F9). */
    private _words(target: TangleTarget): string {
        return targetWords(target, this.matrixUnit, installUnit(this.hass));
    }

    protected render() {
        return html`
            <div class="work">
                <div class="pairs">
                    ${this._snapshot.map((pair) => this._renderPair(pair))}
                </div>
            </div>
        `;
    }

    private _renderPair(pair: DecidePairProp) {
        const settled = this._resolved.get(pair.cluster.id);
        if (settled) {
            return html`<div class="pair-intro done">
                ${t(settled === "kept"
                    ? "tangles.decide_kept"
                    : "tangles.decide_removed")}
            </div>`;
        }
        const [rowA, rowB] = pair.rows;
        // A matrix pair shares BYTES, not a name (issue 20). "Two
        // buttons are both named X" was untrue of it in every part
        // except the word "two", and the X it printed was a uuid.
        const isMatrix = pair.rows.some((row) => row.target.kind === "cell");
        const namesDiffer =
            rowA !== undefined &&
            rowB !== undefined &&
            this._displayName(rowA) !== this._displayName(rowB);
        return html`
            <div class="pair">
                <div class="pair-intro">
                    ${isMatrix
                        ? t("tangles.decide_pair_intro_matrix")
                        : t("tangles.decide_pair_intro", {
                              name: rowA ? this._displayName(rowA) : "",
                          })}
                </div>
                <div class="pair-hint">${t("tangles.decide_pair_hint")}</div>
                ${pair.rows.map((row) => this._renderRow(pair, row))}
                <div class="pair-actions">
                    <button
                        class="action-btn keep-both"
                        ?disabled=${!namesDiffer || this._anyBusy(pair)}
                        @click=${() => this._keepBoth(pair)}
                    >
                        ${t("tangles.decide_keep_both")}
                    </button>
                </div>
            </div>
        `;
    }

    private _renderRow(pair: DecidePairProp, row: TangleRow) {
        const busy = this._busy.has(row.id);
        const editing = this._editing === row.id;
        const confirming = this._confirmingDelete === row.id;
        // A lattice cell has no name of its own to change; its pair is
        // about the bytes two states share. The pencil would open a
        // box that could not answer the question.
        const renameable = row.target.kind === "command";
        return html`
            <div class="drow">
                <span class="dname">
                    ${editing
                        ? html`<input
                              class="editname"
                              .value=${this._draftName}
                              @input=${(e: InputEvent) =>
                                  (this._draftName = (e.target as HTMLInputElement).value)}
                              @keydown=${(e: KeyboardEvent) => {
                                  if (e.key === "Enter") void this._commitRename(pair, row);
                                  if (e.key === "Escape") this._editing = null;
                              }}
                              @blur=${() => this._commitRename(pair, row)}
                          />`
                        : html`<span
                              class="editableval"
                              @click=${() => this._startRename(row)}
                              >${this._displayName(row)}</span
                          >`}
                    ${editing || !renameable
                        ? nothing
                        : renderEditBtn(
                              () => this._startRename(row),
                              t("cmdrow.rename"),
                              busy,
                          )}
                </span>
                <span class="dactions">
                    <ir-test-button
                        .send=${() => this._send(row)}
                        .idleLabelKey=${"tangles.send"}
                        ?disabled=${busy}
                    ></ir-test-button>
                    <button
                        class="trash-btn"
                        title=${t("cmdrow.delete_title")}
                        aria-label=${t("cmdrow.delete_title")}
                        ?disabled=${busy}
                        @click=${() => (this._confirmingDelete = row.id)}
                    >
                        <ha-svg-icon
                            .path=${ICON_TRASH}
                            .viewBox=${TRASH_VIEWBOX}
                        ></ha-svg-icon>
                    </button>
                </span>
                ${confirming
                    ? html`
                          <ir-confirm-dialog
                              title=${t("devdetail.del_cmd_title")}
                              message=${t("devdetail.del_cmd_msg", {
                                  name: this._displayName(row),
                              })}
                              .destructive=${true}
                              @confirmed=${() => this._confirmDelete(pair, row)}
                              @closed=${() => (this._confirmingDelete = null)}
                          ></ir-confirm-dialog>
                      `
                    : nothing}
            </div>
        `;
    }

    static styles = [
        actionChipStyles,
        editButtonStyles,
        trashButtonStyles,
        css`
            :host {
                display: block;
            }
            /* THE CARD PAINTS THE BOX (issue 19). This used to be a
               separate rounded panel with its own background and an
               8px gap above it, so an opened bucket read as a second
               thing that had appeared near the card rather than as
               the card opening. The block in ir-tangle-section owns
               the surface and the corners now; what is left here is
               the padding the rows sit in. */
            .work {
                margin: 0;
                padding: 10px 12px;
                background: none;
                border-radius: 0;
            }
            .pairs {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            /* The copper edge went with the card chrome (issue 19).
               It was the card's own left border leaking onto the work
               area, and with the bucket now inside the card there is
               nothing for it to distinguish. */
            .pair {
                padding-left: 0;
            }
            .pair-intro {
                font-size: 0.8rem;
                color: var(--secondary-text-color);
                margin-bottom: 2px;
            }
            /* Discoverability, not decoration: nothing on the row said
               the name could be clicked (issue 21). */
            .pair-hint {
                font-size: 0.75rem;
                color: var(--secondary-text-color);
                margin-bottom: 6px;
            }
            .pair-actions {
                display: flex;
                justify-content: flex-end;
                margin-top: 6px;
            }
            /* Green, because it is the settling answer rather than a
               destructive one, and the panel's settled green is the
               one this surface already wears on a done line. */
            .keep-both {
                color: #2e7d32;
                border-color: rgba(46, 125, 50, 0.4);
            }
            .keep-both:hover:not(:disabled) {
                background: rgba(46, 125, 50, 0.08);
            }
            .pair-intro.done {
                color: #2e7d32;
            }
            .drow {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
                padding: 4px 0;
            }
            .dname {
                flex: 1 1 auto;
                min-width: 0;
                font-size: 0.8rem;
                font-family: var(--code-font-family, monospace);
            }
            .editableval {
                cursor: pointer;
                border-bottom: 1px dashed var(--divider-color);
            }
            .editname {
                font: inherit;
                background: var(--primary-background-color);
                border: 1px solid var(--divider-color);
                border-radius: 3px;
                padding: 2px 4px;
                color: var(--primary-text-color);
            }
            .dactions {
                display: flex;
                gap: 6px;
                align-items: center;
                flex: 0 0 auto;
            }
            .trashbtn {
                color: #e65100;
                border-color: rgba(230, 81, 0, 0.25);
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tangle-decide": IrTangleDecide;
    }
}
