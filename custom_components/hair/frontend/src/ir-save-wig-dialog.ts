/**
 * Save to Closet: one dialog, three verbs.
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
 * THE VERB IS DERIVED (Second Fitting amendment v2, owner-ruled on
 * the bench 2026-08-04) -- nobody picks it, and the toggle that used
 * to offer the choice is gone from this dialog entirely:
 *
 * - CREATE. A new wig, born with the author's claims if they tick the
 *   box. New wigs are coverage-total by construction -- curation
 *   already happened on the device -- so the list opens all-checked and
 *   unchecking is the exception.
 * - UPDATE. The device's commands still match its source wig's rows
 *   by digest (renames and metadata edits do not count as divergence),
 *   so the same button offers to append a fitting to it. Rows match by
 *   recipe digest regardless of names, which is what lets a locally
 *   renamed command still find its row.
 * - SUCCESSION. The device's commands have diverged from the source
 *   wig -- an addition, a removal, or both -- so the save mints a
 *   successor instead: matched rows render as an UPDATE would, then a
 *   "Changes with new fitting" section shows what is arriving and what
 *   is leaving. The attestation binds the successor's own rows, never
 *   a row set the device has outgrown. The deliberate-fork case (same
 *   content, want a separate wig) lives on through duplicate-device-
 *   then-save and needs no toggle.
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
import { t, tp } from "./localize.js";
import { displayTemp, installUnit } from "./temperature.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type {
    SavePlan,
    SavePlanMissingRow,
    SavePlanRow,
    SaveResult,
    SupersessionBlock,
} from "./types.js";
import "./ir-protocol-chip.js";
import "./ir-supersede-dialog.js";
import "./ir-test-button.js";
import "./ir-tx-knobs.js";
import "./ir-claims-ledger.js";

type Verdict = "worked" | "not_on_device" | "wont_work";

@customElement("ir-save-wig-dialog")
export class IrSaveWigDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public sourceId = "";
    @property() public sourceName = "";
    /** True when the device has at least one emitter. TEST needs one. */
    @property({ type: Boolean }) public hasEmitter = true;
    /** Needed only to read the install's temperature unit, so a
     * checklist written in Celsius reads in whatever the person set. */
    @property({ attribute: false }) public hass: any;

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
    // A SUCCESSION save whose ancestor is still local: the second
    // supersession doorway (v0.9.7). The dialog opens on the successor
    // just written, with "your old Wig" copy and the refit note dropped.
    @state() private _selfSupersede: {
        block: SupersessionBlock;
        newFilename: string;
    } | null = null;

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
    /** MATRIX UPDATE: send the repaired lattice upstream. Explicit,
     * because proposing a content change is a different act from
     * attesting that codes work. */
    @state() private _proposeLattice = false;
    /** The ledger, opened from the joining line. Read only; it cannot
     * change anything this dialog is about to save. */
    @state() private _ledgerOpen = false;

    private get _isUpdate(): boolean {
        return this._plan?.variant === "update";
    }

    /** Second Fitting amendment v2: the device's commands have diverged
     * from the source wig -- an addition, a removal, or both -- so the
     * save mints a successor rather than appending to a row set the
     * device has outgrown. */
    private get _isSuccession(): boolean {
        return this._plan?.variant === "succession";
    }

    /** Every row the attestation list draws. A wig row the device no
     * longer covers never merges in here (v0.9.7 Second Fitting: a
     * missing row always diverges the save to SUCCESSION instead of
     * offering per-row exclusion), so this is simply the device's own
     * rows -- matched, or, on SUCCESSION, newly added. */
    private get _allRows(): SavePlanRow[] {
        return this._plan?.rows ?? [];
    }

    /** Rows that can actually be attested: every row the plan carries.
     * Second Fitting amendment v2: an unmatched row is no longer
     * excluded here -- under SUCCESSION it is a normal addition that
     * travels in the successor, so the perfect-fit denominator is
     * matched rows plus additions. A removal (missing_rows) never
     * reaches this list; nobody can vouch for a command that is not
     * there. */
    private get _attestableRows(): SavePlanRow[] {
        return this._allRows;
    }

    private get _checkedCount(): number {
        return this._attestableRows.filter((r) =>
            this._checked.has(r.digest),
        ).length;
    }

    /** Perfect fit requires every attestable row checked. The dialog says
     * so rather than hiding the button (RULED). */
    private get _isPerfectFit(): boolean {
        const rows = this._attestableRows;
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

    /** A device with no codes and no lattice has nothing to vouch for.
     * Offering the box anyway produced "0 of 0 checked. This saves as a
     * scoped fitting rather than a perfect fit" over an empty list --
     * an invitation to attest nothing, phrased as a downgrade. */
    private get _nothingToAttest(): boolean {
        return !!this._plan && this._allRows.length === 0;
    }

    /** The device's lattice has moved away from the wig's -- a repair
     * through a porthole row, or a cell deleted through one. */
    private get _diverged(): boolean {
        return this._isUpdate && !!this._plan?.lattice_diverged;
    }

    /** A checklist bundle binds cells_hash, which is a SET, so a
     * diverged lattice cannot be attested as it stands: signing would
     * bind bytes the fitter never tested. Proposing resolves it,
     * because then the lattice being bound is the one going in. */
    private get _attestBlocked(): boolean {
        return this._diverged && !this._proposeLattice;
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


    private get _saveLabel(): string {
        if (this._busy) return t("common.saving");
        if (!this._perfect) return t("common.save");
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

    /**
     * Bench addendum (2026-08-05): the self-doorway confirm that killed
     * itself. Whichever screen this render is showing -- the form, the
     * supersede confirm, the done screen -- swaps its `<ha-dialog>` out
     * for the next one, and mwc-dialog's own closing animation keeps
     * running on that REMOVED element regardless: it fires a late
     * `closed` on itself roughly 2.6s later, and that stale event still
     * reaches this handler because the listener was bound directly to
     * the element, not to anything Lit re-checks on removal.
     *
     * A real close always originates from whatever `<ha-dialog>` is
     * CURRENTLY part of this render (checked via shadow-root
     * containment, not component state, so it holds for the form, the
     * confirm, and the done screen alike without needing to special-
     * case any of them). A stale one no longer is. The supersede
     * confirm itself never wires this handler at all -- `_closeAll()`
     * is its only exit -- so this guard is what keeps the ghost from
     * reaching past it and unmounting the whole dialog mid-decision.
     */
    private _close(e?: Event): void {
        const target = e?.target as Node | null;
        if (target && !this.shadowRoot?.contains(target)) return;
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    /** Arming the block checks everything. That is the whole shape of
     * the flow: the person built or adopted a device that works, so the
     * default claim is "all of it", and unchecking is the exception
     * path rather than the main road. */
    private _togglePerfect(e: Event): void {
        if (this._attestBlocked) {
            (e.target as HTMLInputElement).checked = false;
            return;
        }
        this._setPerfect((e.target as HTMLInputElement).checked);
    }

    /**
     * Arming the banner, from the tick or from the banner itself.
     *
     * Split out of ``_togglePerfect`` so the banner head can drive it
     * without inventing a fake input event. The tick still owns the
     * checkbox; this owns what arming MEANS.
     */
    private _setPerfect(on: boolean): void {
        this._perfect = on;
        if (this._perfect) {
            this._checked = new Set(
                this._attestableRows.map((r) => r.digest),
            );
            this._reasons = new Map();
        }
    }

    private _toggleProposeLattice(e: Event): void {
        this._proposeLattice = (e.target as HTMLInputElement).checked;
        // Withdrawing the proposal re-blocks the attestation, so an
        // armed block cannot outlive the thing that unblocked it.
        if (!this._proposeLattice) this._perfect = false;
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
        if (row.command_id) {
            const result = await this.api.sendCommand(
                this.sourceId,
                row.command_id,
            );
            return !!(result as any)?.heard;
        }
        if (!this._isCell(row)) return false;
        // A cell is addressed by coordinate, not by command id, and it
        // routes through the device's own emitters exactly as the
        // climate entity does. The matrix send reports what it sent
        // rather than whether anything heard it back, so this settles
        // on SENT -- honest, and the same thing the STATE MATRIX card
        // has always said.
        await this.api.matrixSend(
            this.sourceId,
            row.power
                ? { power: row.power as "on" | "off" }
                : {
                      mode: row.mode ?? undefined,
                      fan: row.fan ?? null,
                      swing: row.swing ?? null,
                      temp: row.temp ?? null,
                  },
        );
        return false;
    }

    /** A checklist row: no command behind it, but coordinates or a
     * power code that TEST can send. */
    private _isCell(row: SavePlanRow): boolean {
        return !!row.power || !!row.mode;
    }

    private _displayTemp(temp: number): string {
        return displayTemp(
            temp,
            (this._plan?.unit ?? "C") as "C" | "F",
            installUnit(this.hass),
            this._plan?.precision ?? 1,
        );
    }

    /**
     * A checklist row's human label.
     *
     * Ported from the fitting dialog it replaces, because the labels
     * describe the DIMENSION CHECKLIST rather than that dialog: the
     * sample is the same sample, whoever is drawing it. Its locale keys
     * come with it for the same reason.
     */
    private _rowLabel(row: SavePlanRow): string {
        if (row.power === "on") return t("fitting.row_on");
        if (row.power === "off") return t("fitting.row_off");
        switch (row.section) {
            case "modes":
                return row.mode ?? row.alias;
            case "fan":
                return row.fan ?? row.alias;
            case "swing":
                return row.swing ?? row.alias;
            case "temp":
                return t(
                    row.temp_role === "min"
                        ? "fitting.temp_min"
                        : "fitting.temp_max",
                    {
                        temp:
                            row.temp != null
                                ? this._displayTemp(row.temp)
                                : "",
                    },
                );
            default:
                return row.alias;
        }
    }

    /** The coordinates held constant on a row, for the second line.
     * "Cool" alone does not say which cell was pressed. */
    private _rowContext(row: SavePlanRow): string {
        if (row.power) return "";
        const parts = [
            row.section === "modes" ? null : row.mode,
            row.fan,
            row.swing,
            row.temp != null ? `${this._displayTemp(row.temp)}\u00b0` : null,
        ].filter(Boolean);
        const context = parts.join(" \u00b7 ");
        if (row.temp_less) {
            return [context, t("fitting.no_temp_note")]
                .filter(Boolean)
                .join(" ");
        }
        return context;
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
            // A self-superseding Wig (a SUCCESSION save whose ancestor
            // is still local) opens the replace dialog on the successor
            // just written, instead of the plain done confirmation.
            const sup = (result as SaveResult).supersession;
            if (sup && (result as SaveResult).filename) {
                this._selfSupersede = {
                    block: sup,
                    newFilename: (result as SaveResult).filename!,
                };
            } else {
                // Confirm with the filename in place (wigs.md section 7)
                // instead of vanishing -- the filename IS the receipt.
                this._done = result as SaveResult;
            }
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
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
            ...this._metadata(),
            ...(attest ? { attest } : {}),
            ...(this._isUpdate && this._proposeLattice
                ? { propose_lattice: true }
                : {}),
        });
    }

    // --- Rendering -----------------------------------------------------

    private _onSelfReplace = async (e: CustomEvent): Promise<void> => {
        const { newFilename, oldFilename, relink, topupDeviceIds } = e.detail;
        try {
            await this.api.wigsSupersede(
                newFilename, oldFilename, relink, topupDeviceIds,
            );
        } catch {
            // The successor is already written and the wig-saved event
            // fired; a failed replace leaves both files standing, which
            // is a safe outcome to fall back to.
        }
        this._closeAll();
    };

    private _closeAll(): void {
        this._selfSupersede = null;
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _renderSelfSupersede() {
        const s = this._selfSupersede!;
        return html`<ir-supersede-dialog
            .block=${s.block}
            .newFilename=${s.newFilename}
            .self=${true}
            .viewerHandle=${this._handle}
            @replace=${this._onSelfReplace}
            @keep-both=${() => this._closeAll()}
            @closed=${() => this._closeAll()}
        ></ir-supersede-dialog>`;
    }

    render() {
        if (this._selfSupersede) return this._renderSelfSupersede();
        if (this._done) return this._renderDone();
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
            ${this._ledgerOpen && this._plan?.source_filename
                ? html`<ir-claims-ledger
                      .api=${this.api}
                      .wig=${{
                          filename: this._plan.source_filename,
                          name: this._plan.source_wig_name ?? "",
                      } as any}
                      @closed=${() => (this._ledgerOpen = false)}
                  ></ir-claims-ledger>`
                : ""}
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
                ${done.cells_proposed
                    ? html`<div class="saved-line">
                          ${tp(
                              "wigs.save.cells_proposed",
                              done.cells_proposed,
                          )}
                      </div>`
                    : ""}
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

    /**
     * The banner's HEAD is the click target, not the whole banner.
     *
     * Generous enough that nobody has to hit a 15px checkbox, and
     * bounded so it stops before the row list. Once armed, this block
     * holds thirty ticks and a signature form; a stray click in that
     * region disarming the whole thing would throw away work somebody
     * just did. The head is the part that means "do you want to do
     * this at all", so the head is what answers it.
     *
     * The label stops propagation itself: a click there toggles the
     * checkbox natively and would then bubble here and toggle it back,
     * netting to nothing.
     */
    private _onHeadClick(): void {
        if (this._nothingToAttest || this._attestBlocked) return;
        this._setPerfect(!this._perfect);
    }

    /**
     * You would be joining a record, not starting one.
     *
     * Three renamed saves read as three lost wigs on the bench when
     * they were one wig collecting three fittings, so this line has
     * always been here. What it never was is a DOOR: the count sat as
     * grey text under a grey paragraph, and the people behind it were
     * unreachable. It opens the ledger now.
     *
     * Cardinal, not ordinal. The first draft read "you would be the
     * 3rd person" and the English was broken by its own template:
     * "{n}rd" is right for 3 and wrong for 2, 4 and 21, and fixing it
     * properly needs an ordinal plural ruleset that tp() does not have,
     * plus ja/ru/pl having no such construction at all. A cardinal
     * count is one ordinary plural key that translates everywhere.
     */
    private _renderJoining() {
        const n = this._plan?.existing_fittings ?? 0;
        if (!this._isUpdate || n < 1) return "";
        return html`
            <button
                class="joining"
                @click=${(e: Event) => {
                    e.stopPropagation();
                    this._ledgerOpen = true;
                }}
            >
                <span class="j-line">${tp("wigs.save.joining_proven", n)}</span>
                <span class="j-see"
                    ><u>${tp("wigs.save.joining_see", n)}</u> &rsaquo;</span
                >
            </button>
        `;
    }

    /** Bench addendum ruling (2026-08-05): a succession save is never
     * silent. v2 hung the whole checklist inside the perfect-fit box,
     * so an unfitted SUCCESSION save showed nothing at all -- no
     * checklist, no delta, no hint that saving was about to mint a
     * successor. The list now renders on any succession regardless of
     * whether perfect fit is armed; `_renderList` is what draws it
     * read-only when it is not. The attestation block (the oath,
     * handle, github) stays perfect-fit only -- nothing is signed
     * unarmed, so nothing there has anything to show. */
    private _renderFitting() {
        if (this._loading) {
            return html`<div class="ident-hint">${t("common.loading_plain")}</div>`;
        }
        if (!this._plan) return nothing;
        return html`
            ${this._renderLatticeChanges()}
            <div class="fit-block ${this._perfect ? "on" : ""}">
                <div class="fit-head" @click=${this._onHeadClick}>
                    <label
                        class="fit-check"
                        @click=${(e: Event) => e.stopPropagation()}
                    >
                        <input
                            type="checkbox"
                            .checked=${this._perfect}
                            ?disabled=${this._nothingToAttest ||
                            this._attestBlocked}
                            @change=${this._togglePerfect}
                        />
                        <span>${t("wigs.save.perfect_label")}</span>
                    </label>
                    ${this._nothingToAttest
                        ? html`<div class="fit-explainer">
                              ${t("wigs.save.nothing_to_attest")}
                          </div>`
                        : ""}
                    <div class="fit-explainer">
                        ${t("wigs.save.explainer")}
                    </div>
                    ${this._attestBlocked
                        ? html`<div class="fit-gate">
                              ${t("wigs.save.lattice_blocks_attestation")}
                          </div>`
                        : ""}
                    ${this._renderJoining()}
                </div>
                ${(this._perfect && !this._nothingToAttest) ||
                this._isSuccession
                    ? this._renderList()
                    : ""}
                ${this._perfect && !this._nothingToAttest
                    ? this._renderAttestation()
                    : ""}
            </div>
        `;
    }


    /**
     * The content-change prompt for a matrix.
     *
     * Cells the person repaired or deleted through a porthole row on
     * the device. They are named by coordinate with the same rule the
     * rows use, so the "Cool 24" here is recognizably the row they just
     * worked on.
     *
     * Proposing is a CONTENT change and attesting is a claim about
     * hardware; keeping them separate ticks is what stops one from
     * being mistaken for the other.
     */
    private _renderLatticeChanges() {
        const changes = this._plan?.cell_changes ?? [];
        if (!this._isUpdate || changes.length === 0) return "";
        return html`
            <div class="lattice-block">
                <div class="lattice-head">
                    ${tp("wigs.save.lattice_changed", changes.length, {
                        name: this._plan?.source_wig_name ?? "",
                    })}
                </div>
                <div class="lattice-list">
                    ${changes.map(
                        (change) => html`<span
                            class="cell-chip ${change.kind}"
                            >${change.label}</span
                        >`,
                    )}
                </div>
                <label class="fit-check propose">
                    <input
                        type="checkbox"
                        .checked=${this._proposeLattice}
                        @change=${this._toggleProposeLattice}
                    />
                    <span>${t("wigs.save.propose_lattice")}</span>
                </label>
                ${this._attestBlocked
                    ? html`<div class="lattice-gate">
                          ${t("wigs.save.lattice_blocks_attestation")}
                      </div>`
                    : ""}
            </div>
        `;
    }

    /**
     * The checklist. Second Fitting amendment v2: on SUCCESSION the
     * matched rows render first, exactly as an UPDATE would, then a
     * light divider introduces the delta -- additions (on the device,
     * not in the source wig) and removals (in the source wig, not on
     * the device) -- so the change is visible before anything is
     * signed. Matched rows and additions are both attestable; a
     * removal never is, because nobody can vouch for a command that is
     * not there. On CREATE and plain UPDATE there is no delta, so this
     * collapses back to the single list it always was.
     *
     * Bench addendum ruling (2026-08-05): `_renderFitting` now calls
     * this for any succession, armed or not. `readOnly` is what draws
     * the unarmed case -- every row disabled and unchecked, matched
     * and additions alike, because nothing here is being signed. It
     * reuses the row's existing "off" look rather than inventing a
     * second visual language: dimmed and struck reads as "not part of
     * what's being attested" whether the reason is a decline or an
     * unarmed preview.
     */
    private _renderList() {
        const rows = this._allRows;
        const succession = this._isSuccession;
        const matched = succession ? rows.filter((r) => r.matched) : rows;
        const additions = succession ? rows.filter((r) => !r.matched) : [];
        const removals = succession ? (this._plan?.missing_rows ?? []) : [];
        const readOnly = succession && !this._perfect;
        return html`
            <div class="fit-list">
                ${matched.map((row) =>
                    this._renderRow(row, false, readOnly),
                )}
                ${additions.length || removals.length
                    ? html`
                          <div class="changes-divider">
                              <span>${t("wigs.save.changes_title")}</span>
                          </div>
                          ${additions.map((row) =>
                              this._renderRow(row, true, readOnly),
                          )}
                          ${removals.map((row) =>
                              this._renderRemovalRow(row),
                          )}
                      `
                    : ""}
            </div>
            ${readOnly || this._isPerfectFit
                ? ""
                : html`<div class="downgrade">
                      ${t("wigs.save.downgrade", {
                          checked: String(this._checkedCount),
                          total: String(this._attestableRows.length),
                      })}
                  </div>`}
        `;
    }

    /** A matched row, or (SUCCESSION only) an addition: a command on
     * the device with no row in the source wig. An addition attests
     * exactly like a matched row -- it travels in the successor and
     * its claim binds there -- with a small leading "+" marking it as
     * new. The rename-propose line stays UPDATE only: a SUCCESSION
     * successor is authored from the device's current alias directly,
     * so there is no upstream file left to propose the rename onto.
     *
     * `readOnly` (bench addendum, 2026-08-05): an unarmed succession's
     * preview. The checkbox renders disabled and forced unchecked --
     * column rhythm holds, but nothing here is checkable, and the
     * reason picker never shows under a row nobody can decline. */
    private _renderRow(
        row: SavePlanRow,
        isAddition = false,
        readOnly = false,
    ) {
        const checked = readOnly ? false : this._checked.has(row.digest);
        return html`
            <div
                class="fit-row ${checked ? "" : "off"} ${isAddition
                    ? "addition"
                    : ""}"
            >
                <input
                    type="checkbox"
                    .checked=${checked}
                    ?disabled=${readOnly}
                    @change=${() => this._toggleRow(row.digest)}
                />
                <span class="fit-name">
                    ${isAddition
                        ? html`<span class="delta-mark add">+</span>`
                        : ""}
                    ${this._rowLabel(row)}
                    ${this._rowContext(row)
                        ? html`<span class="fit-context"
                              >${this._rowContext(row)}</span
                          >`
                        : ""}
                </span>
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
                    ${row.command_id || this._isCell(row)
                        ? html`<ir-test-button
                              .send=${() => this._sendRow(row)}
                              .disabledReason=${this.hasEmitter
                                  ? null
                                  : t("wigs.save.no_emitter")}
                          ></ir-test-button>`
                        : ""}
                </span>
            </div>
            ${checked || readOnly ? "" : this._renderReasons(row)}
            ${checked && row.renamed && this._isUpdate
                ? this._renderRename(row)
                : ""}
        `;
    }

    /** A wig row the device no longer covers (Second Fitting amendment
     * v2, owner ruling on missing rows, option 2): always a removal
     * now, never an exclusion candidate. Struck, a leading "-", and a
     * checkbox that renders for column rhythm but is DISABLED --
     * nobody can vouch for a command that is not there. No TEST:
     * there is nothing on the device left to send. */
    private _renderRemovalRow(row: SavePlanMissingRow) {
        return html`
            <div class="fit-row removal">
                <input type="checkbox" disabled />
                <span class="fit-name">
                    <span class="delta-mark remove">-</span>
                    ${row.alias}
                </span>
                <span></span>
                <span class="pill-slot"></span>
                <span class="test-slot"></span>
            </div>
            <div class="row-note">${t("wigs.save.row_leaves_wig")}</div>
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
        return html`
            <div class="dialog-actions">
                <span class="spacer"></span>
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    ${t("common.cancel")}
                </button>
                <button
                    class="action-btn save-wig-btn"
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
            /* GREEN IS THE GO BUTTON, in every state (owner ruling
               2026-08-03). It used to mark one thing -- a complete
               perfect fit about to be written -- with everything else
               oxblood, but the LABEL already carries that distinction
               ("Save Perfect Fit" against "Save Fitted Wig" against
               "Save"), so the colour was saying it a second time and
               worse. A lone red button in a green dialog reads as a
               warning about nothing. */
            .save-wig-btn {
                background: #3f8a4b;
                color: #fff;
                border-color: #3f8a4b;
            }
            .save-wig-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
            .saved-line {
                padding: 8px 0 4px;
                font-size: 13.5px;
                line-height: 1.5;
            }
            /* The content-change prompt. Above the attestation block
               on purpose: what the wig is about to BECOME has to be
               settled before anybody vouches for it. */
            .lattice-block {
                margin-top: 10px;
                padding: 8px 10px;
                border: 1px solid rgba(217, 164, 65, 0.45);
                border-radius: 6px;
                background: rgba(217, 164, 65, 0.06);
            }
            .lattice-head {
                font-size: 12px;
                line-height: 1.45;
            }
            .lattice-list {
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin: 7px 0;
            }
            .cell-chip {
                font-size: 11px;
                padding: 1px 7px;
                border-radius: 4px;
                border: 1px solid var(--divider-color);
                color: var(--secondary-text-color);
            }
            .cell-chip.changed {
                border-color: rgba(217, 164, 65, 0.6);
                color: #d9a441;
            }
            /* A deleted cell reads as gone, not as edited. */
            .cell-chip.deleted {
                text-decoration: line-through;
                opacity: 0.75;
            }
            .propose {
                font-size: 12.5px;
                margin-top: 2px;
            }
            .lattice-gate {
                font-size: 11.5px;
                color: #d9a441;
                line-height: 1.45;
                margin-top: 7px;
            }
            /* THE BOUNDARY between describing the wig and making a
               claim about it. Those are different acts and the dialog
               never said so: the one control that turns a save into a
               signed claim was a bare checkbox under a hairline rule,
               at the same weight as the form labels above it.

               DASHED at rest so it reads as an offer; SOLID the moment
               it is armed. Blue, not green: green is already carrying
               the row checks and the Save button, and a green frame
               here would compete with the thing it leads up to. Blue is
               the panel's informational colour already (the comb glyph,
               every link). */
            .fit-block {
                margin-top: 14px;
                padding: 13px 15px;
                border: 1.5px dashed rgba(100, 181, 246, 0.45);
                border-radius: 8px;
                background: rgba(100, 181, 246, 0.035);
                transition: border-color 180ms ease, background 180ms ease,
                    box-shadow 180ms ease;
            }
            .fit-block:hover {
                border-color: rgba(100, 181, 246, 0.7);
            }
            .fit-block.on {
                border-style: solid;
                border-color: #64b5f6;
                background: rgba(100, 181, 246, 0.09);
                box-shadow:
                    0 0 0 1px rgba(100, 181, 246, 0.18),
                    0 2px 14px rgba(100, 181, 246, 0.09);
            }
            /* Only the head is clickable. Generous enough that nobody
               hits a 15px checkbox, bounded so a stray click among the
               thirty ticks below cannot disarm the block and throw the
               work away. */
            .fit-head {
                cursor: pointer;
            }
            /* Why the tick is refused, next to the tick it refuses.
               It used to sit under the propose control, which is where
               the REMEDY is; the question it answers is asked here. */
            .fit-gate {
                font-size: 11.5px;
                color: #d9a441;
                line-height: 1.45;
                margin: 6px 0 0 24px;
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
            /* Two bordered objects should not touch. The explainer's own
               8px is enough when it is the last thing in the head, but
               the fittings door is a card, and a card butted straight
               against the checklist reads as one control. */
            .fit-head + .fit-list {
                margin-top: 11px;
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
                text-transform: capitalize;
            }
            /* The coordinates a checklist row holds constant. "Cool"
               alone does not say which cell was pressed, and a person
               attesting a lattice is entitled to know which one they
               are vouching for. */
            .fit-context {
                margin-left: 6px;
                font-size: 11px;
                color: var(--secondary-text-color);
                text-transform: none;
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
            /* The delta section (Second Fitting amendment v2): a light
               divider above the title, extending the existing checklist
               anatomy rather than inventing a new box. */
            .changes-divider {
                display: flex;
                align-items: center;
                margin: 10px 2px 6px;
                padding-top: 8px;
                border-top: 1px solid var(--divider-color);
                font-size: 10.5px;
                font-weight: 600;
                letter-spacing: 0.03em;
                text-transform: uppercase;
                color: var(--secondary-text-color);
            }
            /* The leading +/- on a delta row. Green for an addition, the
               same house colour every attestable check already wears;
               muted for a removal, which is leaving, not arriving. */
            .delta-mark {
                font-weight: 700;
                margin-right: 3px;
            }
            .delta-mark.add {
                color: #4f9e5a;
            }
            .delta-mark.remove {
                color: var(--secondary-text-color);
            }
            /* A removal (v0.9.7 Second Fitting, owner ruling on missing
               rows): struck like a declined claim, because it reads the
               same way -- nothing here binds a claim -- but dimmed a
               touch further since the checkbox itself is disabled, not
               merely unticked. */
            .fit-row.removal {
                opacity: 0.65;
            }
            .fit-row.removal .fit-name {
                text-decoration: line-through;
            }
            .row-note {
                font-size: 11px;
                color: var(--secondary-text-color);
                line-height: 1.4;
                padding: 5px 4px 7px 30px;
                border-top: 1px solid rgba(255, 255, 255, 0.04);
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
            /* You are joining a record, not starting one. Three
               renamed saves read as three lost wigs on the bench when
               they were one wig collecting three fittings. */
            /* A DOOR, not a footnote. The count was grey text under a
               grey paragraph and the people behind it were unreachable;
               it opens the ledger now. Sized and bordered so it reads
               as something you can press. */
            .joining {
                display: block;
                width: calc(100% - 24px);
                margin: 11px 0 0 24px;
                padding: 9px 12px;
                text-align: left;
                font-family: inherit;
                color: inherit;
                background: rgba(100, 181, 246, 0.05);
                border: 1px solid rgba(100, 181, 246, 0.28);
                border-radius: 7px;
                cursor: pointer;
                transition: background 150ms ease, border-color 150ms ease;
            }
            .joining:hover {
                background: rgba(100, 181, 246, 0.12);
                border-color: rgba(100, 181, 246, 0.55);
            }
            .joining .j-line {
                display: block;
                font-size: 13px;
                line-height: 1.5;
            }
            .joining .j-see {
                display: block;
                font-size: 11.5px;
                color: var(--secondary-text-color);
                margin-top: 4px;
            }
            .joining .j-see u {
                color: #64b5f6;
                text-decoration: underline dotted;
                text-underline-offset: 3px;
            }
            .rename-warn {
                font-size: 11.5px;
                color: #d9a441;
                line-height: 1.45;
                margin: 4px 0 0;
            }
            /* Footer labels never break mid-phrase. The wrap only
               showed up once something else competed for the row, but a
               button that can stack its own words is a button waiting
               to do it again in a longer language. */
            .dialog-actions .action-btn {
                white-space: nowrap;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-save-wig-dialog": IrSaveWigDialog;
    }
}
