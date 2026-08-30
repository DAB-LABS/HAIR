/**
 * Validate for Perfect Fit (Second Fitting v3, coding plan Commit 5).
 *
 * The ceremony this whole family exists for, promoted to its own
 * dialog and its own route: prove every code, then sign it. Retired
 * out of `ir-save-wig-dialog` -- the one dialog that used to carry
 * every verb plus this ceremony beside them -- because the decision
 * window (Commit 3) already asks which route the person wants before
 * any dialog opens, so this one only ever does its own job now. Save
 * as New and Update Closet Wig (Commit 4) went the same way; this
 * commit retires the combined dialog they were all extracted from.
 *
 * The checklist, TEST, the "Changes with new fitting" section, the
 * signing and arming rules, the successor-rows denominator -- all of
 * it rides over from v2 UNCHANGED (spec section 4: "exactly as v2
 * section 1 specified"). What changes is what happens on SAVE and
 * after it:
 *
 * - SOURCED, DIVERGED. Owner ruling: "ALWAYS replaces." The save
 *   sends `replace: true` (Commit 2's server flag) in the SAME call
 *   that writes the successor, so the ancestor mints and retires in
 *   one step -- no post-save confirm, no Keep Both anywhere in this
 *   flow, because picking this route and signing the oath already
 *   was the decision. Second Fitting v3 punch list item 13 moved
 *   what retired (named fittings, the same graded weight the old
 *   self-supersede confirm gave it) and what would be lost to BEFORE
 *   the click instead -- see _gradedLine / _lostRowsLine -- because
 *   that is where the decision still is. The closing screen is now a
 *   pure one-line notification when this route replaced something;
 *   no top-up offer lives there anymore, since a device wanting the
 *   successor's new commands picks them up through the adopt path.
 * - SOURCED, MATCHING. Today's attested UPDATE: the bundle appends,
 *   nothing retires.
 * - FROM-SCRATCH. Today's attested CREATE: a wig is born signed,
 *   nothing to retire.
 *
 * THE TEST BUTTON IS STATELESS ABOUT PROOF, unchanged from v2: it
 * transmits through the device's own emitter routing and reports that
 * the code went over the air, never that the fan spun. "Heard" means
 * a receiver caught the signal, not a verdict -- that stays the
 * human's act.
 *
 * Bench fix (2026-08-07): the form and the receipt(s) used to be
 * separate <ha-dialog> elements, swapped on save. As of HA 2026.7,
 * <ha-dialog> opens a real native <dialog> (showModal()) under the
 * hood, and removing one mid-transition to open another raced the
 * outgoing close() against the incoming showModal() -- an uncaught
 * "InvalidStateError: Transition was aborted", reproduced live
 * against the test instance, that took the whole dialog off-screen
 * before the receipt ever painted (the save itself always succeeded;
 * only the confirmation was crashing invisibly). One <ha-dialog> now
 * stays open for the component's whole life; only the content inside
 * it swaps between the form and whichever receipt applies. The
 * sibling <ir-claims-ledger> below -- a genuinely separate native
 * <dialog>, opened only from the form -- is untouched.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { displayTemp, installUnit } from "./temperature.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import {
    renderMetadataFields,
    type MetadataFieldSetters,
    type MetadataFieldValues,
} from "./ir-save-metadata-fields.js";
import type { HairApi } from "./api.js";
import type {
    SavePlan,
    SavePlanMissingRow,
    SavePlanRow,
    SaveResult,
} from "./types.js";
import "./ir-protocol-chip.js";
import "./ir-test-button.js";
import "./ir-tx-knobs.js";
import "./ir-claims-ledger.js";
import { ICON_WIG } from "./ir-wigs.js";
import { ICON_COMB, COMB_VIEWBOX } from "./ir-icons.js";

type Verdict = "worked" | "not_on_device" | "wont_work";

/** Second Fitting v3 punch list item 13: splits the localized
 * replaced-receipt sentence on its own {old}/{new} placeholder
 * tokens so only the two wig names carry the bold+blue styling,
 * whatever order the sentence puts them in per language. */
const REPLACED_RECEIPT_SPLIT = /\{(old|new)\}/g;

@customElement("ir-save-perfect-dialog")
export class IrSavePerfectDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public sourceId = "";
    @property() public sourceName = "";
    /** True when the device has at least one emitter. TEST needs one. */
    @property({ type: Boolean }) public hasEmitter = true;
    /** Needed only to read the install's temperature unit, so a
     * checklist written in Celsius reads in whatever the person set. */
    @property({ attribute: false }) public hass: any;
    /** Pre-fetched by the decision window before this dialog opens.
     * When present, `firstUpdated` acts on it directly instead of
     * calling wigsSavePlan again -- the plan the person already saw
     * summarized is exactly the one this dialog acts on, never a
     * second, possibly-disagreeing copy. */
    @property({ attribute: false }) public plan: SavePlan | null = null;

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
    /** How many codes on this device are still open tangle rows (P4).
     *
     * Read once when the dialog opens. Zero is also what a failed read
     * leaves behind, deliberately: the door is on the BACKEND, which
     * refuses a fitting over an unclean listing whatever this dialog
     * believes. This is the face of that refusal, shown before the
     * click instead of after it, and a face that cannot be drawn is a
     * reason to let the person try, not to bar them on a guess. */
    @state() private _openTangles = 0;
    /** Digests currently checked. Nothing, until somebody checks one --
     * perfect-or-nothing (owner ruling 2026-08-07): the click IS the
     * attestation, so the default claim is nothing rather than
     * everything. */
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

    /** The device's commands have diverged from the source wig -- an
     * addition, a removal, or both -- so the save mints a successor
     * rather than appending to a row set the device has outgrown. */
    private get _isSuccession(): boolean {
        return this._plan?.variant === "succession";
    }

    /** Every row the attestation list draws. A wig row the device no
     * longer covers never merges in here (a missing row always
     * diverges the save to SUCCESSION instead of offering per-row
     * exclusion), so this is simply the device's own rows -- matched,
     * or, on SUCCESSION, newly added. */
    private get _allRows(): SavePlanRow[] {
        return this._plan?.rows ?? [];
    }

    /** Rows that can actually be attested: every row the plan carries.
     * An unmatched row is never excluded here -- under SUCCESSION it
     * is a normal addition that travels in the successor, so the
     * perfect-fit denominator is matched rows plus additions. A
     * removal (missing_rows) never reaches this list; nobody can vouch
     * for a command that is not there. */
    private get _attestableRows(): SavePlanRow[] {
        return this._allRows;
    }

    private get _checkedCount(): number {
        return this._attestableRows.filter((r) =>
            this._checked.has(this._rowKey(r)),
        ).length;
    }

    /** Perfect fit requires every attestable row checked. The dialog says
     * so rather than hiding the button (RULED). */
    private get _isPerfectFit(): boolean {
        const rows = this._attestableRows;
        return rows.length > 0 && this._checkedCount === rows.length;
    }

    /** Rows that carry SOME claim: checked, or (cells only) an
     * exclusion verdict. A flat row -- including a comb-flagged
     * porthole -- has no exclusion path at all, so for it this
     * collapses to "checked"; that is the whole comb-gate rule
     * (RULED 2026-08-08) without a second code path. */
    private get _attestedCount(): number {
        return this._attestableRows.filter((r) => {
            const key = this._rowKey(r);
            return (
                this._checked.has(key) ||
                (this._isCell(r) && this._reasons.has(key))
            );
        }).length;
    }

    /** Every attestable row carries a claim. Perfect-or-nothing (owner
     * ruling 2026-08-07): signing arms only here -- there is no
     * partial save. On a flat wig this degenerates to `_isPerfectFit`
     * exactly, since a flat row's only claim is a check. On a matrix
     * it also requires every comb-flagged cell checked, because a
     * flagged row has no exclusion path either (the comb gate,
     * RULED 2026-08-08). */
    private get _fullyAttested(): boolean {
        const rows = this._attestableRows;
        return rows.length > 0 && this._attestedCount === rows.length;
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

    private get _metadataValues(): MetadataFieldValues {
        return {
            name: this._name,
            brand: this._brand,
            model: this._model,
            notes: this._notes,
            fccId: this._fccId,
            upc: this._upc,
            asin: this._asin,
            oem: this._oem,
        };
    }

    private get _metadataSetters(): MetadataFieldSetters {
        return {
            setName: (v) => (this._name = v),
            setBrand: (v) => (this._brand = v),
            setModel: (v) => (this._model = v),
            setNotes: (v) => (this._notes = v),
            setFccId: (v) => (this._fccId = v),
            setUpc: (v) => (this._upc = v),
            setAsin: (v) => (this._asin = v),
            setOem: (v) => (this._oem = v),
        };
    }

    /** Typing a new name on an UPDATE renames the EXISTING wig. It does
     * not fork a new one, and the file keeps the name it was first
     * written under, because identity is the wig_id and renaming files
     * would strand anything that referenced them. */
    private get _renameWarning(): string | null {
        if (!this._isUpdate) return null;
        const before = (this._plan?.metadata.name ?? "").trim();
        if (!before || this._name.trim() === before) return null;
        // Second Fitting v3 punch list item 16: names the actual
        // file being renamed, terser than the old "this renames
        // {name} itself" copy.
        return t("wigs.save.rename_wig_warning", {
            filename: this._plan?.source_filename ?? "",
        });
    }

    /** A device with no codes and no lattice has nothing to vouch for.
     * Offering the box anyway produced "0 of 0 rows attested" over an
     * empty list -- an invitation to attest nothing. */
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

    /** A FITTING IS A CLAIM ABOUT CODES THAT WORK (P4).
     *
     * The comb doubts some of these and nobody has answered it yet.
     * Signing a perfect fit over that would put a person's name on
     * bytes the device itself is still asking about, and the shop
     * would carry it as proof. The rows are right there on the same
     * page with the buttons that settle them, so this is a door, not
     * a dead end: fix them, or keep them, and the door opens.
     *
     * A plain save is untouched. The wig can be written and updated
     * with open rows all day; it is the ATTESTATION that waits. */
    private get _tanglesBlock(): boolean {
        return this._openTangles > 0;
    }

    /** Second Fitting v3 punch list, item 3: choosing the route IS
     * the arming now -- there is no checkbox left to tick. Armed
     * whenever there is something to attest and nothing blocking it
     * (a diverged matrix lattice, until proposed; open tangle rows,
     * until they are settled). Replaces every read of the old
     * manually-ticked `_perfect` field. */
    private get _armed(): boolean {
        return (
            !this._attestBlocked &&
            !this._tanglesBlock &&
            !this._nothingToAttest
        );
    }

    private get _signed(): boolean {
        return this._armed && this._oath;
    }

    private get _canSave(): boolean {
        if (this._busy) return false;
        // No partial signing (perfect-or-nothing, owner ruling
        // 2026-08-07): armed but not every row attested refuses,
        // regardless of the oath. Checking every box is what arms the
        // save, not a separate gate on top of it.
        if (this._armed && !this._fullyAttested) return false;
        // An attestation is not signed until the oath is ticked, in
        // either verb. Prefill fills fields, it never pre-checks the
        // oath, and nothing signs without it.
        if (this._armed && !this._oath) return false;
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
        if (!this._armed) return t("common.save");
        if (this._isPerfectFit) return t("wigs.save.save_perfect");
        // A matrix, fully attested, but carrying an exclusion: a real
        // record, just not a PERFECT FIT (the carve-out). Not yet
        // fully attested: plain Save, disabled -- _canSave already
        // refuses it above.
        if (this._fullyAttested) return t("wigs.save.save_record");
        return t("common.save");
    }

    /** The graded line (Second Fitting v3 punch list item 13): on
     * SOURCED, DIVERGED, replacing the ancestor always retires its
     * fitting history -- named here, before the click, instead of on
     * the receipt after it, since the receipt is a pure notification
     * now and the decision already happened by the time it shows.
     * Same rule and copy ir-save-update-dialog.ts's own _gradedLine
     * uses; ported here because this dialog's original design left
     * grading entirely to the post-save closing screen, which item 13
     * retires as a decision point. The attesting person's own handle
     * is filtered from the credit list for the same reason the old
     * receipt-side version did: replacing a wig you yourself just
     * fitted needs no warning about yourself.
     *
     * Perfect-or-nothing (owner ruling 2026-08-07): ``grade.state`` can
     * no longer be "scoped" -- an incomplete ancestor grades as no
     * state at all now, which the guard above already returns null
     * for -- so this only ever has the amber PERFECT FIT line left to
     * give. */
    private get _gradedLine(): { amber: boolean; text: string } | null {
        if (!this._isSuccession) return null;
        const grade = this._plan?.old_fitting_grade;
        if (!grade || grade.state !== "perfect") return null;
        const mine = this._handle.trim().toLowerCase();
        const who = mine
            ? grade.handles.filter((h) => h.trim().toLowerCase() !== mine)
            : grade.handles;
        if (!who.length) return null;
        const name = this._plan?.source_wig_name ?? "";
        return {
            amber: true,
            text: t("supersede.fitted_perfect", { name, who: who.join(", ") }),
        };
    }

    /** The lost-rows line: rows the ancestor carries that the device
     * does not, named before the click for the same reason
     * _gradedLine moved here (item 13). Never shown on matching
     * content: there is nothing about to be discarded when nothing is
     * being replaced. */
    private get _lostRowsLine(): string | null {
        if (!this._isSuccession) return null;
        const missing = this._plan?.missing_rows ?? [];
        if (!missing.length) return null;
        return tp("supersede.lost", missing.length, {
            count: String(missing.length),
            names: missing.map((r) => r.alias).join(", "),
        });
    }

    async firstUpdated(): Promise<void> {
        this._loading = true;
        try {
            const plan =
                this.plan ?? (await this.api.wigsSavePlan(this.sourceId));
            this._plan = plan;
            // Asked once, here, rather than watched: the dialog is
            // modal, so nothing can settle a row while it is open.
            try {
                const listing = await this.api.tangles(this.sourceId);
                this._openTangles = listing.rows.length;
            } catch {
                this._openTangles = 0;
            }
            this._name = plan.metadata.name ?? this.sourceName;
            this._brand = plan.metadata.brand ?? "";
            this._model = plan.metadata.model ?? "";
            this._notes = plan.metadata.notes ?? "";
            this._fccId = plan.metadata.fcc_id ?? "";
            this._upc = plan.metadata.upc ?? "";
            this._asin = plan.metadata.asin ?? "";
            this._oem = plan.metadata.oem ?? "";
            // Second Fitting v3 punch list, item 3: the route
            // itself was the arming, so the checklist seeds its
            // defaults (everything checked) the moment the plan
            // says there is something to attest and nothing
            // blocking it -- no click required.
            if (this._armed) this._armChecklist();
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._loading = false;
        }
    }

    /** Bench fix (2026-08-07): one `<ha-dialog>` now stays open for
     * this component's whole life -- see the file header comment for
     * why the form/receipt swap this used to guard against (and the
     * stale, late `closed` event it could throw) is gone, not just
     * patched. Plain dispatch, no target to check. */
    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    /** Arming used to check everything by default; perfect-or-nothing
     * (owner ruling 2026-08-07) retired that. Every row now starts
     * GREY AND UNCHECKED -- the fitter physically checks each one,
     * because the click IS the attestation. This still runs wherever
     * arming happens (Second Fitting v3 punch list item 3: the route
     * itself is the arming, not a checkbox), it just seeds nothing
     * rather than everything, and still clears `_reasons` since both
     * call sites need that reset. */
    private _armChecklist(): void {
        this._checked = new Set<string>();
        this._reasons = new Map();
    }

    private _toggleProposeLattice(e: Event): void {
        this._proposeLattice = (e.target as HTMLInputElement).checked;
        // Proposing the fix lifts the block; arm (seed the
        // checklist) the instant it does, since item 3 removed the
        // checkbox that used to do this by hand.
        if (this._armed) this._armChecklist();
    }

    /** Takes `_rowKey(row)`, not `row.digest` -- see that helper for
     * why the two are not interchangeable. */
    private _toggleRow(key: string): void {
        const next = new Set(this._checked);
        if (next.has(key)) {
            next.delete(key);
        } else {
            next.add(key);
            const reasons = new Map(this._reasons);
            reasons.delete(key);
            this._reasons = reasons;
        }
        this._checked = next;
    }

    /** Takes `_rowKey(row)`, not `row.digest`. */
    private _setReason(key: string, verdict: Verdict | null): void {
        const next = new Map(this._reasons);
        if (verdict === null) next.delete(key);
        else next.set(key, verdict);
        this._reasons = next;
    }

    /** Takes `_rowKey(row)`, not `row.digest`. */
    private _toggleRename(key: string): void {
        const next = new Set(this._renames);
        if (next.has(key)) next.delete(key);
        else next.add(key);
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
        // climate entity does. Second Fitting v3 punch list item 14:
        // the cell send now rides the same Mirror echo hook a stored
        // command's TEST does, so it reports SENT . HEARD instead of
        // settling on SENT alone.
        const result = await this.api.matrixSend(
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
        return !!result?.heard;
    }

    /** A checklist row: no command behind it, but coordinates or a
     * power code that TEST can send. */
    private _isCell(row: SavePlanRow): boolean {
        return !!row.power || !!row.mode;
    }

    /** The checklist's own local identity for a row -- NOT `row.digest`.
     * Digest is a content hash, and the comb flags a row partly BECAUSE
     * it can be byte-identical to a neighbour (a duplicate, one of the
     * anomalies the comb looks for), so two distinct rows can carry the
     * same digest. Keying `_checked`/`_reasons`/`_renames` on digest
     * made checking one such row check both -- this is what those Set/
     * Map lookups use instead. A porthole row (comb-flagged or not)
     * always has its own `command_id`, which is unique per row; a plain
     * dimension-checklist sample has none (it addresses a cell by
     * coordinate, not by command), so it falls back to those
     * coordinates instead, which are just as unique per sampled cell.
     * The actual claim sent to the server still binds `row.digest` --
     * see `_claims()` -- since that is the correct wire contract; only
     * the widget's own toggle-tracking key changes. */
    private _rowKey(row: SavePlanRow): string {
        if (row.command_id) return `cmd:${row.command_id}`;
        return [
            "cell",
            row.power ?? "",
            row.section ?? "",
            row.mode ?? "",
            row.fan ?? "",
            row.swing ?? "",
            row.temp ?? "",
        ].join(":");
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
            row.temp != null ? `${this._displayTemp(row.temp)}°` : null,
        ].filter(Boolean);
        const context = parts.join(" · ");
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
            const key = this._rowKey(row);
            if (this._checked.has(key)) {
                out.push({ digest: row.digest, verdict: "worked" });
                continue;
            }
            const reason = this._reasons.get(key);
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
            .filter((r) => r.renamed && this._renames.has(this._rowKey(r)))
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
            // Confirm with the filename in place instead of vanishing --
            // the filename IS the receipt. A diverged, sourced save
            // already retired its ancestor inside the same write (see
            // `_saveDevice`); this screen only ever has to say so, no
            // second decision left to make.
            this._done = result as SaveResult;
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
        const attest = this._armed
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
            // Owner ruling: a diverged, sourced Perfect Fit save ALWAYS
            // replaces. Picking this route and signing the oath already
            // was the decision, so the mint and the retirement happen
            // in the same write (Commit 2's server flag) -- there is no
            // post-save confirm left to ask it again, and no Keep Both
            // anywhere in this flow.
            ...(this._isSuccession ? { replace: true } : {}),
            ...(this._isUpdate && this._proposeLattice
                ? { propose_lattice: true }
                : {}),
        });
    }

    // --- Rendering -----------------------------------------------------

    /** Bench fix, part 2 (2026-08-07): matches
     * ir-save-new-dialog.ts's own part-2 fix -- see that file's
     * header comment for the full story. The form and the done
     * screen both live in permanently-mounted wrapper <div>s here
     * too, toggled with `hidden` rather than swapped by Lit, so the
     * dialog's direct children never change identity or count. */
    render() {
        return html`
            <ha-dialog
                open
                heading=${t("wigs.route.validate_perfect_fit")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <div ?hidden=${!!this._done}>${this._renderForm()}</div>
                <div ?hidden=${!this._done}>${this._renderDone()}</div>
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

    private _renderForm() {
        const graded = this._gradedLine;
        const lost = this._lostRowsLine;
        return html`
            ${this._error
                ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                : ""}
            ${this._plan?.source_missing
                ? html`<div class="source-missing-info">
                      <ha-svg-icon .path=${ICON_WIG}></ha-svg-icon>
                      <span>${t("wigs.save.source_missing")}</span>
                  </div>`
                : ""}
            ${graded
                ? html`<div
                      class=${graded.amber
                          ? "fitted-callout"
                          : "fitted-line"}
                  >
                      ${graded.text}
                  </div>`
                : ""}
            ${lost
                ? html`<div class="lost-callout">${lost}</div>`
                : ""}
            ${renderMetadataFields(
                this._metadataValues,
                this._metadataSetters,
                this._renameWarning,
            )}
            ${this._renderFitting()} ${this._renderActions()}
        `;
    }

    /** Rendered even before there is anything to show (see the
     * bench fix part 2 comment on render()) -- stays behind `hidden`
     * until `_done` lands, so the dialog's children never change
     * count or identity when the save actually completes. */
    private _renderDone() {
        if (!this._done) return html``;
        const done = this._done;
        const replaced = done.replaced;
        // Second Fitting v3 punch list item 13 (supersedes round one
        // item 5's anatomy): a replace's receipt is a pure
        // notification now -- both names bold and blue, a single
        // CLOSE, nothing else. The retirement line, the top-up offer,
        // and the Save/Cancel pair that used to live here are gone;
        // the graded-fitting and lost-rows warnings this used to
        // report AFTER the write now render BEFORE it instead (see
        // _gradedLine / _lostRowsLine above), where the decision
        // actually is. Devices wanting the successor's new commands
        // pick them up through the adopt path, not this screen.
        if (replaced) {
            return html`
                <div class="saved-line">
                    ${this._renderReplacedLine(
                        replaced.old_name,
                        this._name.trim(),
                    )}
                </div>
                <div class="dialog-actions">
                    <span class="spacer"></span>
                    <button class="action-btn" @click=${this._close}>
                        ${t("common.close")}
                    </button>
                </div>
            `;
        }
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
                <span class="spacer"></span>
                <button class="action-btn" @click=${this._close}>
                    ${t("common.close")}
                </button>
            </div>
        `;
    }

    /** Second Fitting v3 punch list item 13: splitting the localized
     * sentence on its own {old}/{new} tokens -- rather than
     * substituting plain text into them -- keeps each language's own
     * word order while still letting just the two names carry the
     * style. Same technique ir-wigs.ts already uses for its drop
     * title and duplicate-receipt links. */
    private _renderReplacedLine(oldName: string, newName: string) {
        const segments = t("wigs.route.replaced_receipt").split(
            REPLACED_RECEIPT_SPLIT,
        );
        return html`${segments.map((seg) =>
            seg === "old"
                ? html`<b class="replaced-name">${oldName}</b>`
                : seg === "new"
                  ? html`<b class="replaced-name">${newName}</b>`
                  : html`${seg}`,
        )}`;
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
     * Cardinal, not ordinal: an ordinal template broke on 2, 4 and 21,
     * and several locales have no such construction at all. A cardinal
     * count is one ordinary plural key that translates everywhere.
     */
    private _renderJoining() {
        const n = this._plan?.existing_fittings ?? 0;
        if (!this._isUpdate || n < 1) return "";
        // Second Fitting v3 punch list, item 11 (round three, the
        // FINAL copy, superseding round two's first pass above): the
        // self case is a pure informational replace notice -- no
        // handle needed since it can only ever be your own -- and it
        // wears the house amber family (.fitted-callout /
        // .lost-callout / .rename-warn) instead of blue, the same
        // weight this codebase already gives "something will be
        // replaced" news. Fits by other keys keep the original blue
        // copy and styling, unchanged.
        const self = this._plan?.same_key_notice;
        const isSelf = !!(self && self.handle);
        const line = isSelf
            ? t("wigs.save.joining_self_notice", {
                  date: self!.date ?? "",
              })
            : tp("wigs.save.joining_proven", n);
        return html`
            <button
                class="joining ${isSelf ? "joining-self" : ""}"
                @click=${(e: Event) => {
                    e.stopPropagation();
                    this._ledgerOpen = true;
                }}
            >
                <span class="j-line">${line}</span>
                <span class="j-see"
                    ><u>${tp("wigs.save.joining_see", n)}</u> &rsaquo;</span
                >
            </button>
        `;
    }

    /** A succession save is never silent: the list renders on any
     * succession regardless of whether perfect fit is armed;
     * `_renderList` is what draws it read-only when it is not. The
     * attestation block (the oath, handle, github) stays perfect-fit
     * only -- nothing is signed unarmed, so nothing there has anything
     * to show. */
    private _renderFitting() {
        if (this._loading) {
            return html`<div class="ident-hint">${t("common.loading_plain")}</div>`;
        }
        if (!this._plan) return nothing;
        return html`
            ${this._tanglesBlock ? nothing : this._renderLatticeChanges()}
            <div class="fit-block ${this._armed ? "on" : ""}">
                <div class="fit-head">
                    ${this._tanglesBlock
                        ? // IN PLACE OF THE ACTION, NOT BESIDE IT
                          // (P4). A greyed-out Perfect Fit with a note
                          // under it still reads as an offer that
                          // failed. The HEAD is what swaps, and only
                          // the head: _armed is already false while
                          // rows are open, so the attestation block
                          // hides itself, and the list below keeps
                          // rendering for a succession. A succession
                          // save is never silent, and codes needing
                          // attention are not a reason to make one.
                          html`<div class="fit-blocked">
                              ${tp("tangles.fit_blocked", this._openTangles)}
                          </div>`
                        : html`
                              <div class="fit-check">
                                  <span>${t("wigs.save.perfect_label")}</span>
                              </div>
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
                                        ${t(
                                            "wigs.save.lattice_blocks_attestation",
                                        )}
                                    </div>`
                                  : ""}
                              ${this._renderJoining()}
                          `}
                </div>
                ${this._armed || this._isSuccession
                    ? this._renderList()
                    : ""}
                ${this._armed ? this._renderAttestation() : ""}
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
     *
     * NOT WHILE THE GATE IS UP (owner amendment 2026-08-30, from the
     * Komeco QA pass). The caller renders this only when the fitting
     * gate is clear. A yellow box with a checkbox and an explanation
     * of attesting, stacked above a red notice that says nothing can
     * be attested yet, is two prompts with the dead one on top. The
     * gate is the dialog's one message until the device combs clean.
     *
     * Nothing here changed. The propose flow returns exactly as it
     * was, on the other side of that one condition, the moment the
     * last row is settled.
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
     * The checklist. On SUCCESSION the matched rows render first,
     * exactly as an UPDATE would, then a light divider introduces the
     * delta -- additions (on the device, not in the source wig) and
     * removals (in the source wig, not on the device) -- so the change
     * is visible before anything is signed. Matched rows and additions
     * are both attestable; a removal never is, because nobody can
     * vouch for a command that is not there. On CREATE and plain
     * UPDATE there is no delta, so this collapses back to the single
     * list it always was.
     *
     * `readOnly` draws the unarmed succession case -- every row
     * disabled and unchecked, matched and additions alike, because
     * nothing here is being signed. It reuses the row's existing "off"
     * look rather than inventing a second visual language: dimmed and
     * struck reads as "not part of what's being attested" whether the
     * reason is a decline or an unarmed preview.
     */
    private _renderList() {
        const rows = this._allRows;
        const succession = this._isSuccession;
        const matched = succession ? rows.filter((r) => r.matched) : rows;
        const additions = succession ? rows.filter((r) => !r.matched) : [];
        const removals = succession ? (this._plan?.missing_rows ?? []) : [];
        const readOnly = succession && !this._armed;

        // The comb gate (RULED 2026-08-08): on a matrix, comb-flagged
        // portholes draw as their own group after the dimension
        // samples and the ordinary extras beside them -- coordinate-
        // named (already true of a porthole's own alias), checkbox
        // mandatory, no exclusion picker anywhere near them (the
        // `_isCell` gate on `_renderReasons` already keeps it off a
        // porthole regardless of grouping; this split is purely
        // visual, so the fitter can see which rows earned suspicion).
        // A flat wig has nothing to group -- every row must be
        // checked already -- so it stays one list and each
        // comb-flagged row just wears the mark in place.
        const isMatrix = !!this._plan?.matrix;
        const combRows = isMatrix
            ? matched.filter((r) => r.comb_suspect)
            : [];
        const mainRows = isMatrix
            ? matched.filter((r) => !r.comb_suspect)
            : matched;

        return html`
            <div class="fit-list">
                ${mainRows.map((row) =>
                    this._renderRow(row, false, readOnly),
                )}
                ${combRows.length
                    ? html`
                          <div class="changes-divider">
                              <span>${t("wigs.save.comb_group_title")}</span>
                          </div>
                          ${combRows.map((row) =>
                              this._renderRow(row, false, readOnly),
                          )}
                      `
                    : ""}
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
            ${readOnly
                ? ""
                : html`<div class="attest-progress">
                      ${t("wigs.save.attest_progress", {
                          checked: String(this._attestedCount),
                          total: String(this._attestableRows.length),
                      })}
                      ${this._reasons.size > 0
                          ? html`<div class="exclusion-note">
                                ${t("wigs.save.exclusion_note")}
                            </div>`
                          : ""}
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
     * `readOnly`: an unarmed succession's preview. The checkbox
     * renders disabled and forced unchecked -- column rhythm holds,
     * but nothing here is checkable, and the reason picker never shows
     * under a row nobody can decline. */
    private _renderRow(
        row: SavePlanRow,
        isAddition = false,
        readOnly = false,
    ) {
        const key = this._rowKey(row);
        const checked = readOnly ? false : this._checked.has(key);
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
                    @change=${() => this._toggleRow(key)}
                />
                <span class="fit-name">
                    ${this._rowLabel(row)}
                    ${this._rowContext(row)
                        ? html`<span class="fit-context"
                              >${this._rowContext(row)}</span
                          >`
                        : ""}
                    ${row.comb_suspect
                        ? html`<span
                              class="comb-mark"
                              title=${row.comb_finding ??
                              t("wigs.save.comb_flagged")}
                              ><ha-svg-icon
                                  .path=${ICON_COMB}
                                  .viewBox=${COMB_VIEWBOX}
                              ></ha-svg-icon
                          ></span>`
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
            ${checked || readOnly || !this._isCell(row)
                ? ""
                : this._renderReasons(row)}
            ${checked && row.renamed && this._isUpdate
                ? this._renderRename(row)
                : ""}
        `;
    }

    /** A wig row the device no longer covers: always a removal now,
     * never an exclusion candidate. Struck, a leading "-", and a
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
        const key = this._rowKey(row);
        const current = this._reasons.get(key) ?? null;
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
                                    key,
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
        const key = this._rowKey(row);
        const proposing = this._renames.has(key);
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
                    @click=${() => this._toggleRename(key)}
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
                        (v) => (this._github = v.replace(/^@+/, "")),
                        "",
                        "@",
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

    private _textField(
        label: string,
        value: string,
        set: (v: string) => void,
        placeholder = "",
        prefix = "",
    ) {
        const input = html`
            <input
                type="text"
                .value=${value}
                placeholder=${placeholder}
                @input=${(e: Event) =>
                    set((e.target as HTMLInputElement).value)}
            />
        `;
        return html`
            <div class="field">
                <label>${label}</label>
                ${prefix
                    ? html`
                          <div class="input-prefixed">
                              <span class="input-prefix">${prefix}</span>
                              ${input}
                          </div>
                      `
                    : input}
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
            .input-prefixed {
                display: flex;
                align-items: center;
                width: 100%;
                padding: 0 8px;
                border-radius: 4px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                box-sizing: border-box;
            }
            .input-prefixed:focus-within {
                border-color: #8e3b3b;
            }
            .input-prefix {
                color: var(--secondary-text-color);
                font-size: 0.95rem;
                padding-right: 2px;
                user-select: none;
            }
            .input-prefixed input[type="text"] {
                flex: 1;
                min-width: 0;
                border: none;
                background: transparent;
                padding: 8px 0;
                outline: none;
            }
            .ident-hint {
                font-size: 11px;
                color: var(--secondary-text-color);
                margin: -5px 0 10px;
                line-height: 1.4;
            }
            /* GREEN IS THE GO BUTTON, in every state (owner ruling
               2026-08-03). The label already carries the distinction
               ("Save Perfect Fit" against "Save Fitted Wig" against
               "Save"), so the colour need not say it a second time. */
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
            /* Amber, matching ir-supersede-dialog's own family exactly:
               a fitting retiring is the same weight of news wherever it
               renders. Second Fitting v3 punch list item 13: moved
               here from the receipt (where it used to render AFTER
               the save) to before the click instead, so the margin
               now separates it from what follows rather than what
               came before. */
            .fitted-callout,
            .lost-callout {
                margin: 0 0 12px;
                padding: 10px 12px;
                border-radius: 6px;
                border: 1px solid rgba(217, 164, 65, 0.45);
                background: rgba(217, 164, 65, 0.07);
                color: var(--primary-text-color);
                font-size: 0.85rem;
                line-height: 1.5;
            }
            /* Second Fitting v3 punch list item 18: green, not a
               warning -- creating a wig is information, not danger.
               Same geometry as the amber family above, house green
               (matching .save-wig-btn) instead. */
            .source-missing-info {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 0 0 12px;
                padding: 10px 12px;
                border-radius: 6px;
                border: 1px solid rgba(79, 158, 90, 0.45);
                background: rgba(79, 158, 90, 0.07);
                color: var(--primary-text-color);
                font-size: 0.85rem;
                line-height: 1.5;
            }
            .source-missing-info ha-svg-icon {
                --mdc-icon-size: 20px;
                color: #4f9e5a;
                flex-shrink: 0;
            }
            .fitted-line {
                margin: 0 0 12px;
                font-size: 0.9rem;
                line-height: 1.5;
                color: var(--primary-text-color);
            }
            /* Second Fitting v3 punch list item 13: the replace
               receipt's two names, bold and blue -- the same house
               blue .joining .j-see u already uses below. */
            .replaced-name {
                font-weight: 600;
                color: #64b5f6;
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
               claim about it. DASHED at rest so it reads as an offer;
               SOLID the moment it is armed. Blue, not green: green is
               already carrying the row checks and the Save button. */
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
            /* Bench feedback 2026-08-06: this .fit-check is a
               bare label (no checkbox glyph to skip past, unlike the
               propose/oath rows below), so the gate/explainer/joining
               box under it flush left to the label's own edge instead
               of carrying that indent along for no reason. */
            .fit-gate {
                font-size: 11.5px;
                color: #d9a441;
                line-height: 1.45;
                margin: 6px 0 0 0;
            }
            /* The panel's own ember, the one DELETE and every other
               refusal already wears. The lattice gate above it is
               amber because it is a caution about which bytes get
               bound; this one is a refusal, and it reads as one. */
            .fit-blocked {
                font-size: 12px;
                color: #e65100;
                line-height: 1.45;
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
                margin: 6px 0 8px 0;
            }
            .fit-list {
                max-height: 320px;
                overflow-y: auto;
                border: 1px solid var(--divider-color);
                border-radius: 6px;
                padding: 4px 6px;
            }
            .fit-head + .fit-list {
                margin-top: 11px;
            }
            /* COLUMN DISCIPLINE. The pill sits in a fixed slot sized to
               the widest protocol name and the value chips sit in fixed
               slots, so glyphs, pills and TEST buttons align straight
               down the list. */
            .fit-row {
                display: grid;
                grid-template-columns: auto 1fr auto 72px auto;
                align-items: center;
                gap: 8px;
                padding: 3px 2px;
            }
            /* Perfect-or-nothing (owner ruling 2026-08-07): unchecked
               is the default, ordinary state now -- not a decline --
               so it dims rather than strikes through. Strikethrough
               stays reserved for .removal, where a row really is
               gone. */
            .fit-row.off .fit-name {
                opacity: 0.55;
            }
            .fit-name {
                font-size: 13px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                text-transform: capitalize;
            }
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
            /* Perfect-or-nothing (owner ruling 2026-08-07): a neutral
               running count, not a warning -- attesting rows is the
               main road now, not a downgrade from it. */
            .attest-progress {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                margin: 8px 0 2px;
                line-height: 1.4;
            }
            /* Amber, matching the house family: a matrix carrying an
               exclusion is real news -- this fitting stays a closet
               record, not a PERFECT FIT. */
            .exclusion-note {
                color: #d9a441;
                margin-top: 3px;
            }
            /* The comb gate (RULED 2026-08-08): a small flag, not a
               verdict of its own -- the row's own check or repair is
               what resolves it. Trails the name rather than leading
               it, gray and dim rather than amber -- a diagnostic
               note, not a warning. Sized to ~90% of .fit-name's 13px:
               present without competing with the label. */
            .comb-mark {
                display: inline-flex;
                align-items: center;
                margin-left: 4px;
                color: var(--secondary-text-color);
                opacity: 0.6;
                cursor: help;
            }
            .comb-mark ha-svg-icon {
                --mdc-icon-size: 11.7px;
            }
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
            .delta-mark {
                font-weight: 700;
                margin-right: 3px;
            }
            .delta-mark.remove {
                color: var(--secondary-text-color);
            }
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
               (owner ruling 2026-08-03). */
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
            input[type="checkbox"] {
                accent-color: #4f9e5a;
                width: 15px;
                height: 15px;
                cursor: pointer;
            }
            .joining {
                display: block;
                width: 100%;
                margin: 11px 0 0 0;
                padding: 9px 12px;
                box-sizing: border-box;
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
            /* Second Fitting v3 punch list item 11 (round three): the
               self case reads as a replace notice, so it wears the
               house amber family instead of this blue -- declared
               after .joining so the cascade favors these values for
               the properties both rules set. */
            .joining-self {
                background: rgba(217, 164, 65, 0.07);
                border-color: rgba(217, 164, 65, 0.45);
            }
            .joining-self:hover {
                background: rgba(217, 164, 65, 0.14);
                border-color: rgba(217, 164, 65, 0.65);
            }
            /* Bench feedback 2026-08-07: one continuous line, not
               two -- "See the fitting it already carries" runs right
               after the notice sentence instead of underneath it.
               Both spans fall back to their default inline display
               so they wrap together as one paragraph; the template's
               own whitespace between the two tags supplies the gap. */
            .joining .j-line {
                font-size: 13px;
                line-height: 1.5;
            }
            .joining .j-see {
                font-size: 11.5px;
                color: var(--secondary-text-color);
            }
            .joining .j-see u {
                color: #64b5f6;
                text-decoration: underline dotted;
                text-underline-offset: 3px;
            }
            /* Amber, matching the house family (.fitted-callout /
               .lost-callout above): renaming the wig here is the same
               weight of news, right where it's being typed. */
            .rename-warn {
                margin: 6px 0 0;
                padding: 8px 10px;
                border-radius: 6px;
                border: 1px solid rgba(217, 164, 65, 0.45);
                background: rgba(217, 164, 65, 0.07);
                color: var(--primary-text-color);
                font-size: 0.85rem;
                line-height: 1.5;
            }
            .dialog-actions .action-btn {
                white-space: nowrap;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-save-perfect-dialog": IrSavePerfectDialog;
    }
}
