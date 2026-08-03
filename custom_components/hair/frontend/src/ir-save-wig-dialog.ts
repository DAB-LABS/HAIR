/**
 * Save to Closet: one dialog, two verbs.
 *
 * Started life as the small metadata ask shared by every export surface
 * (v0.7.0 Big Wig). From v0.9.5 it belongs to DEVICES ALONE and it is
 * where fitting happens, because fitting stopped being a ceremony in
 * the closet and became what it physically is: living with a device
 * that works, and then saying so once, with your name on it.
 *
 * Sniffer, Clipper and Plucker no longer save wigs directly. Everything
 * goes through Make Device first (owner ruling 2026-08-03), so a wig is
 * always born from something somebody could actually press.
 *
 * Two variants, chosen by the backend's plan, not by this dialog:
 *
 * - CREATE. A new wig, born with the author's claims if they tick the
 *   box. New wigs are coverage-total by construction -- curation
 *   already happened on the device -- so the list opens all-checked and
 *   unchecking is the exception.
 * - UPDATE. The device remembers the wig it came from, so the same
 *   button offers to append a fitting to it. Rows match by recipe
 *   digest regardless of names, which is what lets a locally renamed
 *   command still find its row.
 *
 * THE TEST BUTTON IS STATELESS ABOUT PROOF. It transmits through the
 * device's own emitter routing and reports that the code went over the
 * air. It never ticks a checkbox, not even on a clean heard-back:
 * "heard" means a receiver caught the signal, not that the fan spun.
 * The check stays the human's act, and that line is what keeps this
 * button from quietly rebuilding the old fitting room.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { SavePlan, SavePlanRow, SaveResult } from "./types.js";
import "./ir-protocol-chip.js";
import "./ir-test-button.js";
import "./ir-tx-knobs.js";

type Verdict = "worked" | "not_on_device" | "wont_work";

@customElement("ir-save-wig-dialog")
export class IrSaveWigDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public sourceId = "";
    @property() public sourceName = "";
    /** True when the device has at least one emitter. TEST needs one. */
    @property({ type: Boolean }) public hasEmitter = true;

    @state() private _name = "";
    @state() private _brand = "";
    @state() private _model = "";
    @state() private _notes = "";
    // Identifier fields (v0.8.0), all optional; commas become the
    // format's list form server-side.
    @state() private _fccId = "";
    @state() private _upc = "";
    @state() private _asin = "";
    @state() private _oem = "";
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _done: SaveResult | null = null;

    // --- The fitting half (device source only) -------------------------
    @state() private _plan: SavePlan | null = null;
    @state() private _loading = false;
    /** The perfect-fit checkbox: arms the attestation block. */
    @state() private _perfect = false;
    /** Digests currently checked. Everything, until somebody unchecks. */
    @state() private _checked = new Set<string>();
    /** Why an unchecked row is unchecked. Absent means no claim at all,
     * which is a third state and has to stay one: silence is not a
     * verdict, and folding it into "did not work" would manufacture
     * evidence nobody gave. */
    @state() private _reasons = new Map<string, Verdict>();
    /** Rows whose local rename the person chose to propose upstream. */
    @state() private _renames = new Set<string>();
    @state() private _handle = "";
    @state() private _github = "";
    @state() private _oath = false;
    /** UPDATE only: the footer escape hatch, behind a confirm. */
    @state() private _saveAsNew = false;
    @state() private _confirmNew = false;

    private get _isUpdate(): boolean {
        return this._plan?.variant === "update" && !this._saveAsNew;
    }

    /** Every row the attestation list draws, matched rows first. */
    private get _allRows(): SavePlanRow[] {
        const plan = this._plan;
        if (!plan) return [];
        if (!this._isUpdate) return plan.rows;
        // On UPDATE the wig's uncovered rows join the list so they can
        // be excluded with a reason. They carry no command, so they get
        // no TEST button: there is nothing on this device to send.
        const missing: SavePlanRow[] = plan.missing_rows.map((row) => ({
            command_id: "",
            alias: row.alias,
            digest: row.digest,
            send_count: 1,
            ditto_count: 0,
            bypass: false,
            protocol: null,
            wig_index: row.wig_index,
            wig_alias: row.alias,
            matched: false,
            renamed: false,
        }));
        return [...plan.rows, ...missing];
    }

    private get _checkedCount(): number {
        return this._allRows.filter((r) => this._checked.has(r.digest))
            .length;
    }

    /** Perfect fit requires every row checked. The dialog says so
     * rather than hiding the button (RULED). */
    private get _isPerfectFit(): boolean {
        const rows = this._allRows;
        return rows.length > 0 && this._checkedCount === rows.length;
    }

    /** Metadata the person actually changed, against what the plan
     * prefilled. Compared rather than assumed: the dialog fills every
     * field from the wig and sends them all back, so treating "filled"
     * as "changed" would make an untouched dialog claim an edit. */
    private get _metaDirty(): boolean {
        const before = this._plan?.metadata ?? {};
        const pairs: [string, string][] = [
            ["name", this._name],
            ["brand", this._brand],
            ["model", this._model],
            ["notes", this._notes],
            ["fcc_id", this._fccId],
            ["upc", this._upc],
            ["asin", this._asin],
            ["oem", this._oem],
        ];
        return pairs.some(
            ([key, value]) => value.trim() !== (before[key] ?? "").trim(),
        );
    }

    /** Typing a new name on an UPDATE renames the EXISTING wig. It does
     * not fork a new one, and the file keeps the name it was first
     * written under, because identity is the wig_id and renaming files
     * would strand anything that referenced them. Said out loud,
     * because on the bench three renamed saves read as three lost wigs
     * when they were one wig wearing the latest name. */
    private get _renamingWig(): boolean {
        if (!this._isUpdate) return false;
        const before = (this._plan?.metadata.name ?? "").trim();
        return !!before && this._name.trim() !== before;
    }

    private get _signed(): boolean {
        return this._perfect && this._oath;
    }

    private get _canSave(): boolean {
        if (this._busy) return false;
        // An attestation is not signed until the oath is ticked, in
        // either verb. Hard rule 4: prefill fills fields, it never
        // pre-checks the oath, and nothing signs without it.
        if (this._perfect && !this._oath) return false;
        // An UPDATE writes a fitting, edited metadata, or both. With
        // neither there is nothing to write, so it refuses rather than
        // producing a shop PR that says nothing. A CREATE always has
        // something to write: the whole wig.
        if (this._isUpdate && !this._signed && !this._metaDirty) {
            return false;
        }
        return true;
    }

    /** Why the save button is gray, in the person's terms. Null when it
     * is not. This lives in the footer rather than a title tooltip
     * because browsers do not show tooltips on disabled buttons -- which
     * is exactly how this read as "you cannot update at all" on the
     * bench (owner report 2026-08-03). */
    private get _blockedReason(): string | null {
        if (this._canSave || this._busy) return null;
        // An unticked oath needs no sentence. The oath box is right
        // there, it is the biggest control in the block, and its own
        // label already says what ticking it means -- a second line
        // repeating the instruction was reading as nagging.
        if (this._perfect && !this._oath) return null;
        if (this._isUpdate) {
            return t("wigs.save.needs_something", {
                name: this._plan?.source_wig_name ?? "",
            });
        }
        return null;
    }

    private get _saveLabel(): string {
        if (this._busy) return t("common.saving");
        // While the toggle is armed the primary names the act, so the
        // pressed button and the button that performs it agree. The
        // toggle keeps ONE label and shows its state by looking
        // pressed; swapping its text to the opposite action is what
        // made it read as a navigation control on the bench.
        if (!this._perfect) {
            return this._saveAsNew
                ? t("wigs.save.new_confirm_yes")
                : t("common.save");
        }
        return this._isPerfectFit
            ? t("wigs.save.save_perfect")
            : t("wigs.save.save_fitted");
    }

    async firstUpdated(): Promise<void> {
        this._loading = true;
        try {
            const plan = await this.api.wigsSavePlan(this.sourceId);
            this._plan = plan;
            this._name = plan.metadata.name ?? this.sourceName;
            this._brand = plan.metadata.brand ?? "";
            this._model = plan.metadata.model ?? "";
            this._notes = plan.metadata.notes ?? "";
            this._fccId = plan.metadata.fcc_id ?? "";
            this._upc = plan.metadata.upc ?? "";
            this._asin = plan.metadata.asin ?? "";
            this._oem = plan.metadata.oem ?? "";
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._loading = false;
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    /** Arming the block checks everything. That is the whole shape of
     * the flow: the person built or adopted a device that works, so the
     * default claim is "all of it", and unchecking is the exception
     * path rather than the main road. */
    private _togglePerfect(e: Event): void {
        this._perfect = (e.target as HTMLInputElement).checked;
        if (this._perfect) {
            this._checked = new Set(this._allRows.map((r) => r.digest));
            this._reasons = new Map();
            // Attesting means attesting the wig you came from, so
            // arming the block returns to UPDATE and the save-as-new
            // toggle goes away (owner ruling 2026-08-03). Save as new
            // is the copy-the-metadata-into-a-fresh-wig road; it is not
            // a thing you reach for halfway through signing. Clearing
            // it here rather than only hiding it is what stops someone
            // from being stranded in create mode with no way back.
            this._saveAsNew = false;
        }
    }

    private _toggleRow(digest: string): void {
        const next = new Set(this._checked);
        if (next.has(digest)) {
            next.delete(digest);
        } else {
            next.add(digest);
            const reasons = new Map(this._reasons);
            reasons.delete(digest);
            this._reasons = reasons;
        }
        this._checked = next;
    }

    private _setReason(digest: string, verdict: Verdict | null): void {
        const next = new Map(this._reasons);
        if (verdict === null) next.delete(digest);
        else next.set(digest, verdict);
        this._reasons = next;
    }

    private _toggleRename(digest: string): void {
        const next = new Set(this._renames);
        if (next.has(digest)) next.delete(digest);
        else next.add(digest);
        this._renames = next;
    }

    private async _sendRow(row: SavePlanRow): Promise<boolean> {
        if (!row.command_id) return false;
        const result = await this.api.sendCommand(
            this.sourceId,
            row.command_id,
        );
        return !!(result as any)?.heard;
    }

    private _claims(): { digest: string; verdict: string }[] {
        const out: { digest: string; verdict: string }[] = [];
        for (const row of this._allRows) {
            if (this._checked.has(row.digest)) {
                out.push({ digest: row.digest, verdict: "worked" });
                continue;
            }
            const reason = this._reasons.get(row.digest);
            // No reason means no claim. The row simply does not appear.
            if (reason) out.push({ digest: row.digest, verdict: reason });
        }
        return out;
    }

    private _renameList(): {
        digest: string;
        alias_at_claim: string;
        alias: string;
    }[] {
        if (!this._isUpdate) return [];
        return this._allRows
            .filter((r) => r.renamed && this._renames.has(r.digest))
            .map((r) => ({
                digest: r.digest,
                alias_at_claim: r.wig_alias ?? "",
                alias: r.alias,
            }));
    }

    private async _save(): Promise<void> {
        if (!this._canSave) return;
        // Saving as new from a device that remembers a wig is a
        // different act from updating it, so it gets its own yes
        // (RULED). Nothing is written until that yes arrives.
        if (
            this._plan?.variant === "update" &&
            this._saveAsNew &&
            !this._confirmNew
        ) {
            this._confirmNew = true;
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const result = await this._saveDevice();
            this.dispatchEvent(
                new CustomEvent("wig-saved", {
                    detail: result,
                    bubbles: true,
                    composed: true,
                }),
            );
            // Confirm with the filename in place (wigs.md section 7)
            // instead of vanishing -- the filename IS the receipt.
            this._done = result as SaveResult;
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
            this._confirmNew = false;
        }
    }

    private _metadata(): Record<string, string> {
        const out: Record<string, string> = {};
        const pairs: [string, string][] = [
            ["name", this._name],
            ["brand", this._brand],
            ["model", this._model],
            ["notes", this._notes],
            ["fcc_id", this._fccId],
            ["upc", this._upc],
            ["asin", this._asin],
            ["oem", this._oem],
        ];
        for (const [key, value] of pairs) {
            if (value.trim()) out[key] = value.trim();
        }
        return out;
    }

    private async _saveDevice(): Promise<SaveResult> {
        const attest = this._perfect
            ? {
                  claims: this._claims(),
                  handle: this._handle.trim() || undefined,
                  github: this._github.trim() || undefined,
                  renames: this._renameList(),
              }
            : undefined;
        return this.api.wigsSave({
            device_id: this.sourceId,
            mode: this._isUpdate ? "update" : "create",
            ...this._metadata(),
            ...(attest ? { attest } : {}),
        });
    }

    // --- Rendering -----------------------------------------------------

    render() {
        if (this._done) return this._renderDone();
        if (this._confirmNew) return this._renderConfirmNew();
        const heading = this._isUpdate
            ? t("wigs.save.update_heading", {
                  name: this._plan?.source_wig_name ?? "",
              })
            : `${t("wigs.export.heading")} -- ${this.sourceName}`;
        return html`
            <ha-dialog
                open
                heading=${heading}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}
                ${this._plan?.source_missing
                    ? html`<ha-alert alert-type="warning"
                          >${t("wigs.save.source_missing")}</ha-alert
                      >`
                    : ""}
                ${this._renderMetadata()} ${this._renderFitting()}
                ${this._renderActions()}
            </ha-dialog>
        `;
    }

    private _renderDone() {
        const done = this._done as SaveResult;
        const line =
            done.variant === "update"
                ? t("wigs.save.updated", {
                      filename: done.filename ?? "",
                      count: String(done.attested),
                  })
                : done.skipped > 0
                  ? t("wigs.saved_skipped", {
                        filename: done.filename ?? "",
                        skipped: String(done.skipped),
                    })
                  : t("wigs.saved", { filename: done.filename ?? "" });
        return html`
            <ha-dialog
                open
                heading=${t("wigs.export.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <div class="saved-line">${line}</div>
                ${done.stale_renames?.length
                    ? html`<ha-alert alert-type="warning"
                          >${t("wigs.save.stale_renames", {
                              names: done.stale_renames.join(", "),
                          })}</ha-alert
                      >`
                    : ""}
                <div class="dialog-actions">
                    <button class="action-btn" @click=${this._close}>
                        ${t("common.close")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    private _renderConfirmNew() {
        return html`
            <ha-dialog
                open
                heading=${t("wigs.save.new_confirm_heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <div class="saved-line">
                    ${t("wigs.save.new_confirm_body", {
                        name: this._plan?.source_wig_name ?? "",
                    })}
                </div>
                <div class="dialog-actions">
                    <span class="spacer"></span>
                    <button
                        class="action-btn cancel-btn"
                        @click=${() => (this._confirmNew = false)}
                    >
                        ${t("common.cancel")}
                    </button>
                    <button class="action-btn save-wig-btn" @click=${this._save}>
                        ${t("wigs.save.new_confirm_yes")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    private _renderMetadata() {
        return html`
            ${html`<div class="field">
                      <label>${t("common.name")}</label>
                      <input
                          type="text"
                          .value=${this._name}
                          @input=${(e: Event) =>
                              (this._name = (
                                  e.target as HTMLInputElement
                              ).value)}
                      />
                      ${this._renamingWig
                          ? html`<div class="rename-warn">
                                ${t("wigs.save.rename_wig_warning", {
                                    name: this._plan?.metadata.name ?? "",
                                })}
                            </div>`
                          : ""}
                  </div>`}
            <div class="pair-grid">
                ${this._textField(
                    t("wigs.editor.brand"),
                    this._brand,
                    (v) => (this._brand = v),
                    t("wigs.export.brand_hint"),
                )}
                ${this._textField(
                    t("wigs.editor.model"),
                    this._model,
                    (v) => (this._model = v),
                )}
                ${this._textField(
                    t("wigs.editor.fcc_id"),
                    this._fccId,
                    (v) => (this._fccId = v),
                )}
                ${this._textField(t("wigs.editor.upc"), this._upc, (v) => (this._upc = v))}
                ${this._textField(
                    t("wigs.editor.asin"),
                    this._asin,
                    (v) => (this._asin = v),
                )}
                ${this._textField(t("wigs.editor.oem"), this._oem, (v) => (this._oem = v))}
            </div>
            <div class="ident-hint">${t("wigs.editor.ids_hint")}</div>
            <div class="field">
                <label>${t("wigs.editor.notes")}</label>
                <input
                    type="text"
                    .value=${this._notes}
                    placeholder=${t("wigs.editor.notes_placeholder")}
                    @input=${(e: Event) =>
                        (this._notes = (e.target as HTMLInputElement).value)}
                />
            </div>
        `;
    }

    private _textField(
        label: string,
        value: string,
        set: (v: string) => void,
        placeholder = "",
    ) {
        return html`
            <div class="field">
                <label>${label}</label>
                <input
                    type="text"
                    .value=${value}
                    placeholder=${placeholder}
                    @input=${(e: Event) =>
                        set((e.target as HTMLInputElement).value)}
                />
            </div>
        `;
    }

    private _renderFitting() {
        if (this._loading) {
            return html`<div class="ident-hint">${t("common.loading_plain")}</div>`;
        }
        if (!this._plan) return nothing;
        // A matrix device's lattice lives in the climate entity, not in
        // the command list, so the rows here are only its depth-0
        // extras. Offering the perfect-fit block over them would let
        // somebody attest a fraction of the device and call it whole,
        // which is worse than not offering it at all.
        if (this._plan.matrix) {
            return html`<div class="fit-block">
                <div class="fit-explainer">
                    ${t("wigs.save.matrix_pending")}
                </div>
            </div>`;
        }
        return html`
            <div class="fit-block">
                <label class="fit-check">
                    <input
                        type="checkbox"
                        .checked=${this._perfect}
                        @change=${this._togglePerfect}
                    />
                    <span>${t("wigs.save.perfect_label")}</span>
                </label>
                <div class="fit-explainer">${t("wigs.save.explainer")}</div>
                ${this._isUpdate && (this._plan?.existing_fittings ?? 0) > 0
                    ? html`<div class="joining">
                          ${t("wigs.save.joining", {
                              count: String(
                                  this._plan?.existing_fittings ?? 0,
                              ),
                              name: this._plan?.source_wig_name ?? "",
                          })}
                      </div>`
                    : ""}
                ${this._perfect ? this._renderList() : ""}
                ${this._perfect ? this._renderAttestation() : ""}
            </div>
        `;
    }

    private _renderList() {
        const rows = this._allRows;
        return html`
            <div class="fit-list">
                ${rows.map((row) => this._renderRow(row))}
            </div>
            ${this._isPerfectFit
                ? ""
                : html`<div class="downgrade">
                      ${t("wigs.save.downgrade", {
                          checked: String(this._checkedCount),
                          total: String(rows.length),
                      })}
                  </div>`}
        `;
    }

    private _renderRow(row: SavePlanRow) {
        const checked = this._checked.has(row.digest);
        return html`
            <div class="fit-row ${checked ? "" : "off"}">
                <input
                    type="checkbox"
                    .checked=${checked}
                    @change=${() => this._toggleRow(row.digest)}
                />
                <span class="fit-name">${row.alias}</span>
                <ir-tx-knobs
                    .sendCount=${row.send_count}
                    .repeatCount=${row.ditto_count}
                    .decoded=${!!row.protocol}
                    .bypassed=${row.bypass}
                ></ir-tx-knobs>
                <span class="pill-slot">
                    ${row.protocol
                        ? html`<ir-protocol-chip
                              .protocol=${row.protocol}
                              ?bypass=${row.bypass}
                          ></ir-protocol-chip>`
                        : ""}
                </span>
                <span class="test-slot">
                    ${row.command_id
                        ? html`<ir-test-button
                              .send=${() => this._sendRow(row)}
                              .disabledReason=${this.hasEmitter
                                  ? null
                                  : t("wigs.save.no_emitter")}
                          ></ir-test-button>`
                        : ""}
                </span>
            </div>
            ${checked ? "" : this._renderReasons(row)}
            ${checked && row.renamed ? this._renderRename(row) : ""}
        `;
    }

    /** No free text (RULED). Two reasons, or none at all -- and "none
     * at all" is a real answer, so it is the default rather than
     * something the picker forces the person out of. */
    private _renderReasons(row: SavePlanRow) {
        const current = this._reasons.get(row.digest) ?? null;
        return html`
            <div class="reason-row">
                ${(["not_on_device", "wont_work"] as Verdict[]).map(
                    (verdict) => html`
                        <button
                            class="reason-btn ${current === verdict
                                ? "on"
                                : ""}"
                            @click=${() =>
                                this._setReason(
                                    row.digest,
                                    current === verdict ? null : verdict,
                                )}
                        >
                            ${t(`wigs.save.reason.${verdict}`)}
                        </button>
                    `,
                )}
                <span class="reason-hint">${t("wigs.save.reason_hint")}</span>
            </div>
        `;
    }

    /** The rename line. Default is "that's just my alias" -- nothing
     * leaves the device -- because a local name is usually a local
     * preference, not a correction to somebody else's wig. */
    private _renderRename(row: SavePlanRow) {
        const proposing = this._renames.has(row.digest);
        return html`
            <div class="rename-row">
                <span
                    >${t("wigs.save.rename_line", {
                        theirs: row.wig_alias ?? "",
                        yours: row.alias,
                    })}</span
                >
                <button
                    class="reason-btn ${proposing ? "on" : ""}"
                    @click=${() => this._toggleRename(row.digest)}
                >
                    ${proposing
                        ? t("wigs.save.rename_proposing")
                        : t("wigs.save.rename_propose")}
                </button>
            </div>
        `;
    }

    private _renderAttestation() {
        return html`
            <div class="attest">
                <div class="pair-grid">
                    ${this._textField(
                        t("wigs.save.your_name"),
                        this._handle,
                        (v) => (this._handle = v),
                    )}
                    ${this._textField(
                        t("wigs.save.your_github"),
                        this._github,
                        (v) => (this._github = v),
                    )}
                </div>
                <label class="fit-check oath">
                    <input
                        type="checkbox"
                        .checked=${this._oath}
                        @change=${(e: Event) =>
                            (this._oath = (
                                e.target as HTMLInputElement
                            ).checked)}
                    />
                    <span>${t("wigs.save.oath")}</span>
                </label>
            </div>
        `;
    }

    private _renderActions() {
        const blocked = this._blockedReason;
        return html`
            ${blocked
                ? html`<div class="blocked">${blocked}</div>`
                : ""}
            <div class="dialog-actions">
                <span class="spacer"></span>
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    ${t("common.cancel")}
                </button>
                ${this._plan?.variant === "update" && !this._perfect
                    ? html`<button
                          class="action-btn as-new-btn ${this._saveAsNew ? "on" : ""}"
                          @click=${() => {
                              this._saveAsNew = !this._saveAsNew;
                          }}
                          ?disabled=${this._busy}
                      >
                          ${t("wigs.save.save_as_new")}
                      </button>`
                    : ""}
                <button
                    class="action-btn save-wig-btn ${this._isPerfectFit &&
                    this._signed
                        ? "perfect"
                        : ""}"
                    @click=${this._save}
                    ?disabled=${!this._canSave}
                >
                    ${this._saveLabel}
                </button>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            input[type="text"]:focus {
                outline: none;
                border-color: #8e3b3b;
            }
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            .pair-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                column-gap: 10px;
            }
            .ident-hint {
                font-size: 11px;
                color: var(--secondary-text-color);
                margin: -5px 0 10px;
                line-height: 1.4;
            }
            .save-wig-btn {
                background: #8e3b3b;
                color: #fff;
                border-color: #8e3b3b;
            }
            .save-wig-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
            .saved-line {
                padding: 8px 0 4px;
                font-size: 13.5px;
                line-height: 1.5;
            }
            .fit-block {
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid var(--divider-color);
            }
            .fit-check {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 13.5px;
                cursor: pointer;
            }
            .fit-explainer {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                line-height: 1.45;
                margin: 6px 0 8px 24px;
            }
            .fit-list {
                max-height: 320px;
                overflow-y: auto;
                border: 1px solid var(--divider-color);
                border-radius: 6px;
                padding: 4px 6px;
            }
            /* COLUMN DISCIPLINE. The pill sits in a fixed slot sized to
               the widest protocol name and the value chips sit in fixed
               slots, so glyphs, pills and TEST buttons align straight
               down the list. A list whose controls stagger by row reads
               as noise, and this list is the thing being attested. */
            .fit-row {
                display: grid;
                grid-template-columns: auto 1fr auto 72px auto;
                align-items: center;
                gap: 8px;
                padding: 3px 2px;
            }
            .fit-row.off .fit-name {
                opacity: 0.55;
                text-decoration: line-through;
            }
            .fit-name {
                font-size: 13px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .pill-slot {
                display: flex;
                justify-content: center;
            }
            .test-slot {
                display: flex;
                justify-content: flex-end;
            }
            .reason-row,
            .rename-row {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 0 2px 6px 26px;
                font-size: 11.5px;
                color: var(--secondary-text-color);
                flex-wrap: wrap;
            }
            .reason-btn {
                background: transparent;
                border: 1px solid var(--divider-color);
                border-radius: 4px;
                color: var(--secondary-text-color);
                font-size: 11px;
                padding: 2px 7px;
                cursor: pointer;
            }
            .reason-btn:hover {
                background: rgba(255, 255, 255, 0.06);
            }
            .reason-btn.on {
                border-color: #8e3b3b;
                color: #fff;
                background: rgba(142, 59, 59, 0.35);
            }
            .reason-hint {
                opacity: 0.75;
            }
            .downgrade {
                font-size: 11.5px;
                color: #d9a441;
                margin: 8px 0 2px;
                line-height: 1.4;
            }
            .attest {
                margin-top: 10px;
            }
            /* THE OATH BOX IS HALF AGAIN AS BIG as the row checks
               (owner ruling 2026-08-03). It is the one control in this
               dialog that turns a list of ticks into a signed claim, so
               it should not look like the thirty ticks above it. Its
               sentence centres against it rather than sitting at the
               top, because at this size a top-aligned label reads as
               having slipped. */
            .oath {
                margin-top: 8px;
                align-items: center;
                line-height: 1.4;
            }
            .oath input[type="checkbox"] {
                width: 22px;
                height: 22px;
                flex: none;
            }
            /* GREEN IS THE HOUSE COLOUR FOR "this one is good"
               (owner ruling 2026-08-03), so every check in the
               attestation list wears it and so does the button that
               ships a complete one. Fitted-but-partial stays oxblood:
               the colour is the difference between the two outcomes,
               and painting both green would spend it. */
            input[type="checkbox"] {
                accent-color: #4f9e5a;
                width: 15px;
                height: 15px;
                cursor: pointer;
            }
            .save-wig-btn.perfect {
                background: #3f8a4b;
                border-color: #3f8a4b;
            }
            /* The save-as-new escape hatch. A real button, not an
               underlined link: it is one of the two things you can do
               here, and the footer is where doing things lives. It
               stays outline-only so the primary is unambiguous, and it
               takes the same oxblood wash on hover that every other
               button in the house does -- a control with no mouse-over
               reads as decoration. */
            .as-new-btn:hover:not(:disabled) {
                border-color: #8e3b3b;
                color: #fff;
                background: rgba(142, 59, 59, 0.22);
            }
            .action-btn.on {
                border-color: #8e3b3b;
                color: #fff;
                background: rgba(142, 59, 59, 0.35);
            }
            /* Why the primary is gray, said out loud. A title tooltip
               was invisible here, because browsers do not show tooltips
               on disabled buttons -- which read as "you cannot update at
               all" on the bench. */
            /* You are joining a record, not starting one. Three
               renamed saves read as three lost wigs on the bench when
               they were one wig collecting three fittings. */
            .joining {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                line-height: 1.45;
                margin: 0 0 8px 24px;
            }
            .rename-warn {
                font-size: 11.5px;
                color: #d9a441;
                line-height: 1.45;
                margin: 4px 0 0;
            }
            .blocked {
                font-size: 11.5px;
                color: #d9a441;
                line-height: 1.45;
                margin: 10px 0 -2px;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-save-wig-dialog": IrSaveWigDialog;
    }
}
