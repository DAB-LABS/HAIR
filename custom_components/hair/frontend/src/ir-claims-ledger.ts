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

/** Rows shown inside an open entry before Show all. Two rows sit per
 * line now, so 24 is twelve lines: a whole flat wig fits without the
 * cap ever biting, and a 74-row matrix checklist still cannot wall you
 * in. It was 6 when the rows ran one per line. */
const PREVIEW_ROWS = 24;

/** The same right-pointing mdi chevron ir-assigned-popover uses, so the
 * panel keeps one glyph for "there is more behind this". It rotates a
 * quarter turn when the entry is open. */
const ICON_CHEVRON = "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z";

@customElement("ir-claims-ledger")
export class IrClaimsLedger extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public wig!: WigInfo;

    @state() private _ledger: ClaimsLedger | null = null;
    @state() private _error: string | null = null;
    /** Which entries are disclosed. */
    @state() private _open = new Set<number>();
    /** Which disclosed entries have had their row cap lifted. */
    @state() private _showAll = new Set<number>();

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
            this._open = this._openByDefault(this._ledger);
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
    }

    /**
     * A single entry always opens, because one collapsed row is a
     * chevron hiding the entire dialog. Past that, yours opens and
     * everybody else's stays shut: a wig that has travelled collects
     * fittings, and four people at twelve rows each is the wall this
     * disclosure exists to prevent.
     *
     * Free rather than accordion, deliberately. Opening a second entry
     * does not shut the first, because the question people bring here
     * is usually "who disagreed with whom about which row", and that
     * needs two entries on screen at once.
     */
    private _openByDefault(ledger: ClaimsLedger): Set<number> {
        const entries = ledger.entries;
        if (entries.length === 1) return new Set([0]);
        const mine = entries.findIndex((e) => e.mine);
        return mine < 0 ? new Set<number>() : new Set([mine]);
    }

    /**
     * THE TOP LAYER, and why this dialog is a native one.
     *
     * The ledger is opened from inside the save dialog, and as of
     * HA 2026.7 <ha-dialog> is a wrapper around <wa-dialog>, which
     * opens a real <dialog> with showModal(). A modal dialog is
     * promoted to the browser's TOP LAYER, which sits above the whole
     * z-index scale -- there is no number large enough to paint over
     * it, and everything outside it is inert besides, so the ledger
     * was both invisible and unclickable (bench 2026-08-03).
     *
     * The only thing that stacks above a modal dialog is another modal
     * dialog: the top layer is a stack, last opened on top. So the
     * ledger opens one of its own and keeps the panel's own overlay
     * cosmetics inside it. Escape and the backdrop are wired back to
     * the same close path the button uses.
     */
    firstUpdated(): void {
        this._native()?.showModal();
    }

    private _native(): HTMLDialogElement | null {
        return this.renderRoot.querySelector("dialog");
    }

    /**
     * NOT composed, and that is the whole point.
     *
     * The save dialog is mounted by the device page as
     * <ir-save-wig-dialog @closed=...>, which unmounts it. The ledger
     * is mounted by the save dialog as <ir-claims-ledger @closed=...>,
     * which does the same one level down. Same event name, two owners.
     *
     * A composed event crosses shadow boundaries, so closing the ledger
     * also reached the device page and took the save dialog down with
     * it: you lost the form you were filling in and had to start again
     * (bench 2026-08-03). Non-composed stops at the shadow root it was
     * dispatched into, which is the save dialog's, where the handler
     * that actually owns this element is listening.
     */
    private _close(): void {
        this._native()?.close();
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: false }),
        );
    }

    private static _flip(set: Set<number>, index: number): Set<number> {
        const next = new Set(set);
        if (next.has(index)) next.delete(index);
        else next.add(index);
        return next;
    }

    private _toggleEntry(index: number): void {
        this._open = IrClaimsLedger._flip(this._open, index);
    }

    private _toggleRows(index: number): void {
        this._showAll = IrClaimsLedger._flip(this._showAll, index);
    }

    render() {
        return html`
            <dialog
                class="top-layer"
                @cancel=${(e: Event) => {
                    e.preventDefault();
                    this._close();
                }}
            >
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
            </dialog>
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

    /**
     * One entry, as a disclosure.
     *
     * The closed head still carries everything anybody scans a ledger
     * for: who, whether they signed, what tier, and how much. Opening
     * it is what buys you the row by row detail, and that is the part
     * that does not scale past one person.
     */
    private _renderEntry(entry: ClaimBundle, index: number) {
        const open = this._open.has(index);
        return html`
            <div class="entry ${entry.mine ? "mine" : ""} ${open ? "open" : ""}">
                <button
                    class="ehead"
                    aria-expanded=${open ? "true" : "false"}
                    @click=${() => this._toggleEntry(index)}
                >
                    <span class="l1">
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
                        <ha-svg-icon
                            class="chev"
                            .path=${ICON_CHEVRON}
                        ></ha-svg-icon>
                    </span>
                    <span class="l2">
                        <span
                            class="tier ${entry.complete ? "perfect" : "scoped"}"
                            >${entry.complete
                                ? t("claims.tier_perfect")
                                : t("claims.tier_scoped")}</span
                        >
                        <span class="counts">${this._counts(entry)}</span>
                    </span>
                </button>
                ${open ? this._renderEntryBody(entry, index) : nothing}
            </div>
        `;
    }

    private _renderEntryBody(entry: ClaimBundle, index: number) {
        const all = this._showAll.has(index);
        const shown = all ? entry.rows : entry.rows.slice(0, PREVIEW_ROWS);
        const hidden = entry.rows.length - shown.length;
        return html`
            <div class="ebody">
                ${this._renderLattice(entry)}
                ${entry.note
                    ? html`<div class="note">&ldquo;${entry.note}&rdquo;</div>`
                    : nothing}
                <div class="rows">
                    ${shown.map((row) => this._renderRow(row))}
                </div>
                ${hidden > 0
                    ? html`<div class="more">
                          <button @click=${() => this._toggleRows(index)}>
                              ${tp("claims.show_all", hidden)}
                          </button>
                      </div>`
                    : all && entry.rows.length > PREVIEW_ROWS
                      ? html`<div class="more">
                            <button @click=${() => this._toggleRows(index)}>
                                ${t("claims.show_fewer")}
                            </button>
                        </div>`
                      : nothing}
            </div>
        `;
    }

    /**
     * THE ROW IS A BOX, and it has to be.
     *
     * This used to be `display: contents` spilling two loose cells into
     * a three column grid whose third column existed for the orphan
     * note that most rows do not have. Every row therefore shifted one
     * column further along than the last, and by row two the alias and
     * its verdict were on different lines in different columns (bench
     * 2026-08-03). A row that owns its own children cannot come apart
     * however many of them it has.
     *
     * The leader is what carries the eye across the gap to the verdict.
     */
    private _renderRow(row: ClaimBundle["rows"][number]) {
        return html`
            <div
                class="row ${row.present ? "" : "orphaned"}"
                title=${row.digest}
            >
                <span class="alias">${row.alias}</span>
                <span class="leader"></span>
                <span class="verdict v-${row.verdict}"
                    >${t(`claims.verdict.${row.verdict}`)}</span
                >
                ${row.present
                    ? nothing
                    : html`<span class="orphan-note"
                          >${t("claims.orphaned")}</span
                      >`}
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
            /* The native dialog is a carrier and nothing else: it buys
               the top layer, and every pixel people see still comes
               from .overlay and .dialog, so the ledger matches the rest
               of the panel's pop-ups. The user-agent chrome and the
               user-agent backdrop are both stripped, since .overlay
               already draws the scrim. */
            dialog.top-layer {
                margin: 0;
                padding: 0;
                border: 0;
                max-width: none;
                max-height: none;
                width: 100%;
                height: 100%;
                background: transparent;
                overflow: visible;
            }
            dialog.top-layer::backdrop {
                background: transparent;
            }
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
                margin-bottom: 10px;
                overflow: hidden;
            }
            /* Your own attestation, marked but not promoted: it sorts in
               file order like everybody else's, because the ledger is a
               record and not a profile page. */
            .entry.mine {
                border-color: rgba(100, 181, 246, 0.35);
            }
            /* The whole head is the control. A chevron alone is a 15px
               target sitting beside 500px of dead text that looks just
               as pressable. */
            .ehead {
                display: block;
                width: 100%;
                padding: 10px 12px;
                text-align: left;
                background: transparent;
                border: 0;
                font-family: inherit;
                color: inherit;
                cursor: pointer;
            }
            .ehead:hover {
                background: rgba(255, 255, 255, 0.03);
            }
            .l1 {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .chev {
                --mdc-icon-size: 15px;
                flex: none;
                color: #64b5f6;
                transition: transform 160ms ease;
            }
            .entry.open .chev {
                transform: rotate(90deg);
            }
            /* Indented past the chevron's column so the two head lines
               align on the left and nothing sits under the arrow. */
            .l2 {
                display: flex;
                align-items: baseline;
                gap: 9px;
                margin-top: 3px;
                padding-right: 23px;
            }
            .ebody {
                border-top: 1px solid var(--divider-color);
                background: rgba(255, 255, 255, 0.018);
                padding: 10px 12px;
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
            /* Both sit above the rows inside an open entry, so the gap
               they own is below them, not above. */
            .lattice-moved,
            .note {
                margin: 0 0 9px;
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
            /* Two rows per line. The grid holds the LINES; each row is
               its own flex box that owns its alias, leader, verdict and
               orphan note, so a row with a note cannot push the next
               row's verdict into the wrong column. That is exactly what
               the old display:contents did. */
            .rows {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2px 22px;
                max-height: 280px;
                overflow-y: auto;
                align-content: start;
            }
            /* One column when the panel is too narrow to keep an alias
               and its verdict on the same line twice over. */
            @media (max-width: 560px) {
                .rows {
                    grid-template-columns: 1fr;
                }
            }
            .row {
                display: flex;
                align-items: baseline;
                gap: 8px;
                min-width: 0;
                padding: 2px 0;
                font-size: 11.5px;
                line-height: 1.6;
            }
            .alias {
                font-family: ui-monospace, "SF Mono", Menlo, monospace;
                font-size: 11px;
                word-break: break-word;
            }
            /* The leader is what carries the eye across the gap. Without
               it a short alias and a long verdict read as two unrelated
               words with a hole between them. */
            .leader {
                flex: 1;
                min-width: 10px;
                border-bottom: 1px dotted rgba(127, 127, 127, 0.35);
                transform: translateY(-3px);
            }
            .verdict {
                color: var(--secondary-text-color);
                white-space: nowrap;
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
                font-size: 10px;
                white-space: nowrap;
            }
            .more {
                padding-top: 7px;
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
