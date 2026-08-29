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
 * new is designed here" (brief section 4). Resolve by renaming either
 * row (updateCommand) or deleting the extra (deleteCommand, standard
 * confirm; the survivor keeps its name; the row settles as "duplicate
 * removed").
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HairApi } from "./api.js";
import type { TangleRow } from "./types.js";
import { t } from "./localize.js";
import { targetWords } from "./ir-tangle-copy.js";
import { actionChipStyles } from "./ir-action-chip-styles.js";
import "./ir-test-button.js";

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

    @state() private _snapshot: DecidePairProp[] = [];
    @state() private _resolved = new Set<string>();
    @state() private _editing: string | null = null;
    @state() private _draftName = "";
    @state() private _confirmingDelete: string | null = null;
    @state() private _busy = new Set<string>();

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

    private _startRename(row: TangleRow): void {
        this._editing = row.id;
        this._draftName = row.target.command_id ?? "";
    }

    private async _commitRename(pair: DecidePairProp, row: TangleRow): Promise<void> {
        const commandId = row.target.command_id;
        if (!commandId || !this._draftName.trim()) {
            this._editing = null;
            return;
        }
        this._busy = new Set(this._busy).add(row.id);
        try {
            await this.api.updateCommand({
                device_id: this.deviceId,
                command_id: commandId,
                name: this._draftName.trim(),
            });
            this._resolved = new Set(this._resolved).add(pair.cluster.id);
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
            this._resolved = new Set(this._resolved).add(pair.cluster.id);
            this._confirmingDelete = null;
            this._emitMutated(null);
        } finally {
            const next = new Set(this._busy);
            next.delete(row.id);
            this._busy = next;
        }
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
        if (this._resolved.has(pair.cluster.id)) {
            return html`<div class="pair-intro done">${t("tangles.decide_removed")}</div>`;
        }
        const [rowA, rowB] = pair.rows;
        return html`
            <div class="pair">
                <div class="pair-intro">
                    ${t("tangles.decide_pair_intro", {
                        name: rowA?.target.command_id ?? "",
                    })}
                </div>
                ${pair.rows.map((row) => this._renderRow(pair, row))}
            </div>
        `;
    }

    private _renderRow(pair: DecidePairProp, row: TangleRow) {
        const busy = this._busy.has(row.id);
        const editing = this._editing === row.id;
        const confirming = this._confirmingDelete === row.id;
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
                              >${targetWords(row.target)}</span
                          >`}
                </span>
                <span class="dactions">
                    <ir-test-button
                        .send=${() => this._send(row)}
                        .idleLabelKey=${"tangles.send"}
                        ?disabled=${busy}
                    ></ir-test-button>
                    <button
                        class="action-btn trashbtn"
                        ?disabled=${busy}
                        @click=${() =>
                            (this._confirmingDelete =
                                this._confirmingDelete === row.id ? null : row.id)}
                    >
                        ${t("tangles.delete")}
                    </button>
                </span>
                ${confirming
                    ? html`
                          <div class="confirmbar">
                              <span>${t("tangles.delete_confirm")}</span>
                              <button
                                  class="action-btn"
                                  @click=${() => this._confirmDelete(pair, row)}
                              >
                                  ${t("tangles.delete")}
                              </button>
                              <button
                                  class="action-btn"
                                  @click=${() => (this._confirmingDelete = null)}
                              >
                                  ${t("tangles.cancel")}
                              </button>
                          </div>
                      `
                    : nothing}
            </div>
        `;
    }

    static styles = [
        actionChipStyles,
        css`
            :host {
                display: block;
            }
            .work {
                margin: 8px 0 0 0;
                padding: 10px 12px;
                background: var(--card-background-color, var(--primary-background-color));
                border-radius: 4px;
            }
            .pairs {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .pair {
                border-left: 3px solid var(--tangle-copper, #b5651d);
                padding-left: 10px;
            }
            .pair-intro {
                font-size: 0.8rem;
                color: var(--secondary-text-color);
                margin-bottom: 6px;
            }
            .pair-intro.done {
                border-left: 3px solid var(--tangle-copper, #b5651d);
                padding-left: 10px;
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
            .confirmbar {
                flex: 1 0 100%;
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.75rem;
                color: var(--secondary-text-color);
                padding: 4px 0;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tangle-decide": IrTangleDecide;
    }
}
