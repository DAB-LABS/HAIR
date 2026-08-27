/**
 * FIX -- "Fixes ready" (design brief v6 section 2, signed). A donor
 * candidate already exists for every row here; the flow is SEND
 * (optional, no question follows it) and ACCEPT (settles the row in
 * place), plus one ACCEPT ALL that cascades every remaining row and
 * collapses the card to its receipt.
 *
 * SEND is the panel's real, already-shipped `ir-test-button` --
 * unforked, per the kickoff's own rule -- with its idle label pointed
 * at the "tangles.send" locale key instead of the component's own
 * default (TEST). `hair/device/tangle/test-send`'s corrected contract
 * (owner-ruled 2026-08-27, matching sendCommand/matrixSend) reports
 * `heard`, so a receiver catch renders SENT . HEARD exactly like every
 * other send button in the panel.
 *
 * Row order is snapshotted on open and held stable -- "no reordering
 * while the workspace is open" (brief section 7). Accepted rows render
 * as a done line IN PLACE rather than disappearing, until the parent
 * re-fetches and this component is torn down/rebuilt on next open.
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

@customElement("ir-tangle-fix")
export class IrTangleFix extends LitElement {
    @property({ attribute: false }) public hass!: HassLike;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public rows: TangleRow[] = [];

    @state() private _snapshot: TangleRow[] = [];
    @state() private _accepted = new Set<string>();
    @state() private _accepting = new Set<string>();
    @state() private _acceptAllBusy = false;
    @state() private _receipt: { count: number; targets: string[] } | null = null;
    @state() private _undoing = false;

    connectedCallback(): void {
        super.connectedCallback();
        this._snapshot = this.rows;
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

    /** Wired straight to <ir-test-button>.send: resolves to whether a
     * receiver heard the echo, so the button itself decides SENT vs.
     * SENT . HEARD. No question ever follows a send (brief section 2)
     * -- this never touches _accepted. */
    private async _send(row: TangleRow): Promise<boolean> {
        const result = await this.api.tangleTestSend(this.deviceId, row.pronto);
        return result.heard;
    }

    private async _accept(row: TangleRow): Promise<void> {
        this._accepting = new Set(this._accepting).add(row.id);
        try {
            const result = await this.api.tangleApply({
                deviceId: this.deviceId,
                target: row.id,
                pronto: row.pronto,
                tested: true,
                source: "donor",
            });
            this._accepted = new Set(this._accepted).add(row.id);
            this._emitMutated(result.wig.written);
        } finally {
            const next = new Set(this._accepting);
            next.delete(row.id);
            this._accepting = next;
        }
    }

    private async _acceptAll(): Promise<void> {
        this._acceptAllBusy = true;
        const targets: string[] = [];
        let lastWigWritten: boolean | null = null;
        try {
            for (const row of this._snapshot) {
                if (this._accepted.has(row.id)) continue;
                try {
                    // eslint-disable-next-line no-await-in-loop -- a
                    // visible top-to-bottom cascade is the point
                    // (brief section 2): each row settles before the
                    // next fires, so the user can watch it happen.
                    const result = await this.api.tangleApply({
                        deviceId: this.deviceId,
                        target: row.id,
                        pronto: row.pronto,
                        tested: true,
                        source: "donor",
                    });
                    this._accepted = new Set(this._accepted).add(row.id);
                    targets.push(row.id);
                    lastWigWritten = result.wig.written;
                } catch {
                    // A row that did not convince stays un-accepted and
                    // remains a finding (brief section 2) -- no halt,
                    // the cascade continues past a single failure.
                }
            }
            this._receipt = { count: targets.length, targets };
            this._emitMutated(lastWigWritten);
        } finally {
            this._acceptAllBusy = false;
        }
    }

    private async _undo(): Promise<void> {
        if (!this._receipt) return;
        this._undoing = true;
        let lastWigWritten: boolean | null = null;
        try {
            for (const target of this._receipt.targets) {
                // eslint-disable-next-line no-await-in-loop
                const result = await this.api.tangleRevert(this.deviceId, target);
                lastWigWritten = result.wig.written;
            }
            this._receipt = null;
            this._accepted = new Set();
            this._emitMutated(lastWigWritten);
        } finally {
            this._undoing = false;
        }
    }

    protected render() {
        if (this._receipt) {
            return html`
                <div class="work">
                    <div class="receipt">
                        ${t("tangles.fix_receipt", { count: this._receipt.count })}
                        <button
                            class="action-btn"
                            ?disabled=${this._undoing}
                            @click=${() => this._undo()}
                        >
                            ${t("tangles.undo")}
                        </button>
                    </div>
                </div>
            `;
        }

        const remaining = this._snapshot.filter((r) => !this._accepted.has(r.id));

        return html`
            <div class="work">
                <div class="case">${t("tangles.fix_case", { count: this._snapshot.length })}</div>
                <div class="rows">
                    ${this._snapshot.map((row) => this._renderRow(row))}
                </div>
                ${remaining.length > 0
                    ? html`
                          <button
                              class="accept-all-btn"
                              ?disabled=${this._acceptAllBusy}
                              @click=${() => this._acceptAll()}
                          >
                              ${t("tangles.accept_all", { count: remaining.length })}
                          </button>
                      `
                    : nothing}
            </div>
        `;
    }

    private _renderRow(row: TangleRow) {
        const done = this._accepted.has(row.id);
        const accepting = this._accepting.has(row.id);
        if (done) {
            return html`
                <div class="rrow done">
                    <span class="rname">${targetWords(row.target)}</span>
                    <span class="done-mark">${t("tangles.row_done")}</span>
                </div>
            `;
        }
        return html`
            <div class="rrow">
                <span class="rname">${targetWords(row.target)}</span>
                <span class="ractions">
                    <ir-test-button
                        .send=${() => this._send(row)}
                        .idleLabelKey=${"tangles.send"}
                        ?disabled=${accepting}
                    ></ir-test-button>
                    <button
                        class="action-btn accept-btn"
                        ?disabled=${accepting}
                        @click=${() => this._accept(row)}
                    >
                        ${t("tangles.accept")}
                    </button>
                </span>
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
            .case {
                font-size: 0.85rem;
                color: var(--primary-text-color);
                margin-bottom: 10px;
                max-width: 640px;
            }
            .rows {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .rrow {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
                padding: 6px 8px;
                border-radius: 4px;
            }
            .rrow.done {
                opacity: 0.65;
            }
            .rname {
                flex: 1 1 auto;
                font-size: 0.8rem;
                font-family: var(--code-font-family, monospace);
                color: var(--primary-text-color);
                min-width: 0;
            }
            .ractions {
                display: flex;
                gap: 6px;
                flex: 0 0 auto;
                align-items: center;
            }
            .accept-btn {
                color: #2e7d32;
                border-color: rgba(46, 125, 50, 0.3);
            }
            .done-mark {
                font-size: 0.75rem;
                color: #2e7d32;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }
            .accept-all-btn {
                margin-top: 10px;
                padding: 9px 20px;
                font-size: 0.85rem;
                font-weight: 500;
                font-family: inherit;
                text-transform: uppercase;
                letter-spacing: 0.03em;
                color: #fff;
                background: var(--tangle-blue, #2196f3);
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .accept-all-btn:disabled {
                opacity: 0.5;
                cursor: default;
            }
            .receipt {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 0.85rem;
                color: #2e7d32;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-tangle-fix": IrTangleFix;
    }
}
