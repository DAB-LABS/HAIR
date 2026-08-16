/**
 * Dialog for minting a named HAIR Trigger Remote straight from a USE
 * fork's "Remote" tile (add-popups signpost 3, Track 2 item 2 / Track
 * 3 item 1) -- the remote-side sibling of ir-promote-dialog.ts.
 *
 * Same grammar the Add Trigger Remote dialog already established
 * (name field, ir-receiver-picker footer, Create), reused piece for
 * piece per signpost-3-mockup-s11.html section 1's "Use-as-a-Remote
 * flow" frames: name prefilled from the source, a preview line
 * ("Creates N triggers from {source}") using the row's own already-
 * known signal count (no extra round trip -- Sniffer/Clipper/Plucker
 * rows carry signal_count, wig rows carry signal_count, library rows
 * carry signalCount), and for a matrix-shaped source the same plain
 * "matrix" reduced-note the Add dialog's drop mode already uses (not
 * a separate heading badge -- one treatment, not two).
 *
 * THE MATRIX RULE (trigger-remotes-release-a.md): a matrix source
 * still seeds only its flat/discrete signals -- ws_wig_make_remote and
 * the promoted_from_unknown_id path both already enforce this
 * server-side (see websocket_api.py), so isMatrix here is display-only,
 * unlike ir-promote-dialog.ts where it locks a real field (device
 * type). Remotes have no device-type concept to lock.
 *
 * Exactly one of sourceUnknownId / wigFilename / codebookId /
 * sourceDeviceId is set by the caller, mirroring ir-promote-dialog.ts's
 * own source shape:
 *   - sourceUnknownId: a Sniffer/Clipper/Plucker catalog row (the
 *     promoted_from_unknown_id door, Track 2 item 2).
 *   - wigFilename: a closet wig (the hair/wigs/make-remote door).
 *   - codebookId: a library codebook row (same door, EITHER/OR with
 *     wigFilename per wigMakeRemote's own source shape).
 *   - sourceDeviceId: a live HAIR Device's own commands (signpost 3,
 *     Track 3.5, owner-directed 2026-08-15 -- the "Make a Remote"
 *     mirror-door mint, ir-device-settings-dialog.ts's convert
 *     section). hair/device/make-remote, not a wig door at all;
 *     matrix-cell porthole rows are excluded server-side, so isMatrix
 *     stays purely the display-only note it already is for every
 *     other door.
 *
 * Fires `remote-created` on success (bubbles/composed, detail is the
 * minted TriggerRemoteInfo -- every door, not just the mirror-door
 * one, per signpost 3 Track 3 item 5's USE-fork pin-prompt trigger),
 * `closed` on cancel / close.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-receiver-picker.js";
import type { HairApi } from "./api.js";

@customElement("ir-promote-remote-dialog")
export class IrPromoteRemoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;

    /** Pre-filled remote name from the source's own label. */
    @property() public suggestedName = "";
    /** Sniffer/Clipper/Plucker catalog door. */
    @property() public sourceUnknownId = "";
    /** Closet wig door (mutually exclusive with codebookId). */
    @property() public wigFilename = "";
    /** Library codebook door (mutually exclusive with wigFilename). */
    @property() public codebookId = "";
    /** Live Device door (signpost 3, Track 3.5): mutually exclusive
     *  with every door above -- the "Make a Remote" mirror-door mint,
     *  sourced from this device's own commands rather than a wig. */
    @property() public sourceDeviceId = "";
    /** The source's own known signal count, for the preview line --
     *  already in hand from the row data, no live lookup needed. */
    @property({ type: Number }) public previewCount = 0;
    /** Display-only matrix note (see module doc -- seeding itself is
     *  already flat-signal-only server-side regardless). */
    @property({ type: Boolean }) public isMatrix = false;

    @state() private _name = "";
    @state() private _receiverIds: string[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.suggestedName && !this._name) {
            this._name = this.suggestedName;
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _create(): Promise<void> {
        const name = this._name.trim();
        if (!name) {
            this._error = t("common.name_required");
            return;
        }

        this._busy = true;
        this._error = null;

        try {
            // Every door's minted object rides as the event's detail
            // (signpost 3, Track 3 item 5, owner-directed
            // 2026-08-15): the USE fork's already-linked pin-prompt
            // trigger needs the new remote's id/name on all four
            // catalog surfaces, not just the Track 3.5 mirror door
            // this shape originally shipped for.
            let minted: Awaited<ReturnType<typeof this.api.wigMakeRemote>>;
            if (this.sourceDeviceId) {
                minted = await this.api.deviceMakeRemote(
                    this.sourceDeviceId,
                    name,
                    this._receiverIds,
                );
            } else if (this.wigFilename || this.codebookId) {
                minted = await this.api.wigMakeRemote(
                    this.wigFilename
                        ? { filename: this.wigFilename }
                        : { codebookId: this.codebookId },
                    name,
                    this._receiverIds,
                );
            } else {
                minted = await this.api.createTriggerRemote({
                    name,
                    receiver_scope: this._receiverIds,
                    promoted_from_unknown_id: this.sourceUnknownId || null,
                });
            }
            this.dispatchEvent(
                new CustomEvent("remote-created", {
                    detail: minted,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${t("promote.remote_heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <div class="field">
                    <label>${t("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        required
                        autofocus
                        @input=${(e: Event) =>
                            (this._name = (e.target as HTMLInputElement)
                                .value)}
                        @keydown=${(e: KeyboardEvent) => {
                            if (e.key === "Enter") void this._create();
                        }}
                        @focus=${(e: Event) =>
                            (e.target as HTMLInputElement).select()}
                    />
                </div>

                <div class="dlg-preview-line">
                    ${t("addtr.preview_creates", {
                        count: String(this.previewCount),
                        name: this.suggestedName,
                    })}
                    ${this.isMatrix
                        ? html`<span class="reduced-note"
                              >${t("common.matrix_tag")}</span
                          >`
                        : ""}
                </div>

                <ir-receiver-picker
                    .api=${this.api}
                    .value=${this._receiverIds}
                    ?disabled=${this._busy}
                    @receivers-changed=${(e: CustomEvent) =>
                        (this._receiverIds = e.detail.value)}
                ></ir-receiver-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn wide cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${t("common.cancel")}
                    </button>
                    <button
                        class="action-btn wide create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy ? t("common.creating") : t("common.create")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            .field {
                margin: 12px 0;
            }
            .dlg-preview-line {
                font-size: 0.82rem;
                color: var(--secondary-text-color);
                margin: 4px 0 12px;
            }
            .reduced-note {
                margin-left: 6px;
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: var(--secondary-text-color);
            }
            .create-btn {
                background: #f5a623;
                color: #fff;
            }
            .create-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-promote-remote-dialog": IrPromoteRemoteDialog;
    }
}
