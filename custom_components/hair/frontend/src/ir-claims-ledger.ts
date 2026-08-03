/**
 * The ledger: who attested what about a wig, and when.
 *
 * READ ONLY, and structurally so. This used to be a tab inside the
 * fitting dialog, which meant it sat next to controls that could edit
 * the very rows it reported on -- and it grew one of its own (jump to
 * the first failed row) because that was cheap to add from there.
 *
 * v0.9.5 moved attestation onto the device: you prove a wig by adopting
 * it, pressing the buttons, and signing once at SAVE TO CLOSET. So the
 * ledger has no session to drive. What is left is a record, and a
 * record's job is to be legible and hard to argue with.
 *
 * Three things it says that the closet row's check cannot:
 *
 * - WHO. A green check means somebody proved the whole wig; this names
 *   them, with their signature state beside the name.
 * - WHAT EXACTLY. Per-row verdicts, including the rows a fitter
 *   deliberately excluded, which are not failures and are not silence.
 * - WHAT HAS MOVED SINCE. A claim about a row whose bytes were later
 *   edited is shown as orphaned rather than quietly dropped. Somebody
 *   really did prove that recipe; it just is not the recipe on the file
 *   any more, and hiding that would make the ledger read as coverage it
 *   does not have.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { ClaimBundle, ClaimsLedger, WigInfo } from "./types.js";

/** Rows shown inside an entry before Show all. Enough to see the shape
 * of what was claimed without a 74-row wall from a matrix checklist. */
const PREVIEW_ROWS = 6;

@customElement("ir-claims-ledger")
export class IrClaimsLedger extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public wig!: WigInfo;

    @state() private _ledger: ClaimsLedger | null = null;
    @state() private _error: string | null = null;
    @state() private _expanded = new Set<number>();

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
    }

    /** Always reads on open. Everything in the payload is derived from
     * the file, so a stale copy would misreport exactly the case this
     * dialog exists to show: a row edited since somebody proved it. */
    private async _load(): Promise<void> {
        this._error = null;
        try {
            this._ledger = await this.api.wigsClaims(this.wig.filename);
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _toggle(index: number): void {
        const next = new Set(this._expanded);
        if (next.has(index)) next.delete(index);
        else next.add(index);
        this._expanded = next;
    }

    render() {
        return html`
            <div class="overlay" @click=${this._close}>
                <div
                    class="dialog ledger-dialog"
                    @click=${(e: Event) => e.stopPropagation()}
                >
                    <h3 class="heading">
                        ${t("claims.heading", { name: this.wig.name })}
                    </h3>
                    ${this._renderBody()}
                    <div class="foot-note">${t("claims.footer")}</div>
                    <div class="dialog-actions">
                        <span class="spacer"></span>
                        <button
                            class="action-btn cancel-btn"
                            @click=${this._close}
                        >
                            ${t("common.close")}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    private _renderBody() {
        if (this._error)
            return html`<div class="err">${this._error}</div>`;
        if (!this._ledger)
            return html`<div class="loading">
                ${t("common.loading_plain")}
            </div>`;
        const entries = this._ledger.entries;
        if (!entries.length)
            return html`<div class="empty">${t("claims.none")}</div>`;
        return html`
            ${this._renderSummary()}
            ${entries.map((e, i) => this._renderEntry(e, i))}
        `;
    }

    /** The union line. Deliberately separate from any entry, because it
     * is nobody's claim: three people who each proved a different third
     * have not, between them, produced anyone who can say the wig works.
     * That is why it never turns the closet check green, and why it says
     * "between everyone" rather than sitting under a name. */
    private _renderSummary() {
        const l = this._ledger!;
        if (l.matrix)
            return html`<div class="summary">
                ${tp("claims.attestations", l.entries.length)}
            </div>`;
        return html`<div class="summary">
            ${tp("claims.attestations", l.entries.length)} &middot;
            ${t("claims.union", {
                covered: String(l.covered),
                total: String(l.total),
            })}
        </div>`;
    }

    private _renderEntry(entry: ClaimBundle, index: number) {
        const open = this._expanded.has(index);
        const shown = open ? entry.rows : entry.rows.slice(0, PREVIEW_ROWS);
        const hidden = entry.rows.length - shown.length;
        return html`
            <div class="entry ${entry.mine ? "mine" : ""}">
                <div class="ehead">
                    <span class="handle"
                        >${entry.handle ?? t("claims.anonymous")}</span
                    >
                    ${entry.github
                        ? html`<span class="gh"
                              >@${entry.github.replace(/^@/, "")}</span
                          >`
                        : nothing}
                    ${this._renderSignature(entry)}
                    <span class="spacer"></span>
                    <span class="date">${entry.date ?? ""}</span>
                </div>
                <div class="everdict">
                    <span class="tier ${entry.complete ? "perfect" : "scoped"}"
                        >${entry.complete
                            ? t("claims.tier_perfect")
                            : t("claims.tier_scoped")}</span
                    >
                    <span class="counts">${this._counts(entry)}</span>
                </div>
                ${this._renderLattice(entry)}
                ${entry.note
                    ? html`<div class="note">&ldquo;${entry.note}&rdquo;</div>`
                    : nothing}
                <div class="rows">
                    ${shown.map(
                        (row) => html`
                            <div
                                class="row ${row.present ? "" : "orphaned"}"
                                title=${row.digest}
                            >
                                <span class="alias">${row.alias}</span>
                                <span class="verdict v-${row.verdict}"
                                    >${t(`claims.verdict.${row.verdict}`)}</span
                                >
                                ${row.present
                                    ? nothing
                                    : html`<span class="orphan-note"
                                          >${t("claims.orphaned")}</span
                                      >`}
                            </div>
                        `,
                    )}
                    ${hidden > 0
                        ? html`<div class="more">
                              <button @click=${() => this._toggle(index)}>
                                  ${t("claims.show_all", {
                                      count: String(hidden),
                                  })}
                              </button>
                          </div>`
                        : open && entry.rows.length > PREVIEW_ROWS
                          ? html`<div class="more">
                                <button @click=${() => this._toggle(index)}>
                                    ${t("claims.show_fewer")}
                                </button>
                            </div>`
                          : nothing}
                </div>
            </div>
        `;
    }

    /** A bad signature discredits the ATTRIBUTION, not the data, and
     * the wording has to say which. The claims are still on the file
     * and still legible; what is in doubt is whether this person made
     * them. */
    private _renderSignature(entry: ClaimBundle) {
        if (entry.signed === "valid")
            return html`<span
                class="sig valid"
                title=${entry.key_fingerprint
                    ? t("claims.key", { key: entry.key_fingerprint })
                    : ""}
                >&check; ${t("claims.signed")}</span
            >`;
        if (entry.signed === "invalid")
            return html`<span class="sig bad" title=${t("claims.bad_sig_what")}
                >${t("claims.bad_sig")}</span
            >`;
        return html`<span class="sig unsigned">${t("claims.unsigned")}</span>`;
    }

    /** Matrix only: a checklist bundle vouches for the lattice as a SET,
     * so it pins the set it sampled. If the lattice has moved, what the
     * person signed is no longer what the file holds -- and unlike a
     * flat wig, there is no per-row way to say which part survived. */
    private _renderLattice(entry: ClaimBundle) {
        if (entry.lattice_current === null) return nothing;
        if (entry.lattice_current) return nothing;
        return html`<div class="lattice-moved">
            ${t("claims.lattice_moved")}
        </div>`;
    }

    private _counts(entry: ClaimBundle): string {
        const parts = [tp("claims.worked", entry.worked)];
        if (entry.excluded)
            parts.push(tp("claims.excluded", entry.excluded));
        if (entry.orphaned)
            parts.push(tp("claims.orphaned_count", entry.orphaned));
        return parts.join(" · ");
    }

    static styles = [
        dialogStyles,
        css`
            .ledger-dialog {
                max-width: 620px;
            }
            .summary {
                font-size: 12px;
                color: var(--secondary-text-color);
                margin: -8px 0 14px;
            }
            .entry {
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                padding: 10px 12px;
                margin-bottom: 10px;
            }
            /* Your own attestation, marked but not promoted: it sorts in
               file order like everybody else's, because the ledger is a
               record and not a profile page. */
            .entry.mine {
                border-color: rgba(100, 181, 246, 0.35);
            }
            .ehead {
                display: flex;
                align-items: baseline;
                gap: 8px;
            }
            .handle {
                font-size: 13px;
                font-weight: 600;
            }
            .gh {
                font-size: 11.5px;
                color: var(--secondary-text-color);
            }
            .date {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                font-variant-numeric: tabular-nums;
            }
            .spacer {
                flex: 1;
            }
            .sig {
                font-size: 11px;
                padding: 1px 6px;
                border-radius: 9px;
                border: 1px solid var(--divider-color);
                color: var(--secondary-text-color);
            }
            .sig.valid {
                color: #66bb6a;
                border-color: rgba(102, 187, 106, 0.4);
            }
            .sig.bad {
                color: #ff5252;
                border-color: rgba(255, 82, 82, 0.4);
            }
            .everdict {
                display: flex;
                align-items: baseline;
                gap: 9px;
                margin-top: 6px;
            }
            .tier {
                font-size: 11.5px;
                font-weight: 600;
            }
            .tier.perfect {
                color: #66bb6a;
            }
            .tier.scoped {
                color: #ffc107;
            }
            .counts {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                font-variant-numeric: tabular-nums;
            }
            .lattice-moved,
            .note {
                margin-top: 7px;
                font-size: 11.5px;
                line-height: 1.5;
                color: var(--secondary-text-color);
            }
            .lattice-moved {
                color: #ffc107;
            }
            .note {
                font-style: italic;
            }
            .rows {
                margin-top: 9px;
                padding-top: 8px;
                border-top: 1px solid var(--divider-color);
                display: grid;
                grid-template-columns: max-content max-content minmax(0, 1fr);
                gap: 3px 14px;
                max-height: 260px;
                overflow-y: auto;
                align-content: start;
            }
            .row {
                display: contents;
            }
            .row > * {
                font-size: 11.5px;
                line-height: 1.6;
            }
            .alias {
                font-family: ui-monospace, "SF Mono", Menlo, monospace;
                font-size: 11px;
                word-break: break-word;
            }
            .verdict {
                color: var(--secondary-text-color);
            }
            .verdict.v-worked {
                color: #66bb6a;
            }
            /* An orphaned row is struck through rather than removed: the
               claim was real, it is just no longer about anything on this
               file. */
            .row.orphaned .alias {
                text-decoration: line-through;
                opacity: 0.65;
            }
            .orphan-note {
                color: #ffc107;
            }
            .more {
                grid-column: 1 / -1;
                padding-top: 4px;
            }
            .more button {
                background: none;
                border: none;
                padding: 0;
                font: inherit;
                font-size: 11.5px;
                color: #64b5f6;
                cursor: pointer;
                text-decoration: underline dotted;
                text-underline-offset: 3px;
            }
            .empty {
                padding: 14px 4px;
                font-size: 13px;
                color: var(--secondary-text-color);
            }
            .foot-note {
                margin-top: 14px;
                padding: 9px 12px;
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid var(--divider-color);
                font-size: 11.5px;
                color: var(--secondary-text-color);
                line-height: 1.5;
            }
            .err {
                font-size: 12px;
                color: var(--error-color, #c62828);
                margin-bottom: 8px;
            }
            .loading {
                padding: 16px;
                font-size: 12.5px;
                color: var(--secondary-text-color);
            }
        `,
    ];
}
