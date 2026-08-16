/**
 * Add Controlled Device dialog (add-popups, signpost 2, Track 2; drop
 * mode added signpost 3, Track 1 item 3; per-kind source tabs added
 * signpost 3, Track 1 item 4).
 *
 * Replaces the two-tile Add Device chooser -- formally superseded,
 * owner-ruled 2026-08-13, and per the coding plan's own review pass
 * that chooser was never actually built/shipped in the first place.
 * The real retirement target, ir-add-device-dialog.ts (the old
 * + New Device dialog), was cut over to this dialog and deleted
 * outright in Track 4 -- not just unlinked, the class/tag no longer
 * exists in the built bundle at all.
 *
 * Six tabs, one create grammar (brief section 3): pick a source (or
 * none, on Manual), see a live preview line, confirm a name, Create.
 * The footer -- name field, Device Type, emitter picker, Create -- is
 * now constant across all six tabs (signpost 3, Track 4 bench-gate
 * fix, 2026-08-17 -- see signpost-3-coding-plan.md section 3a): the
 * four newer tabs below used to stay inert pending a backend contract
 * that Track 2 item 2 had, in fact, already built (promoted_from_
 * unknown_id on hair/device/create) -- they call it directly now.
 *
 *   Manual: rides the same `createDevice()` call verbatim that
 *     ir-add-device-dialog.ts used before its Track 4 retirement,
 *     Device Type restored (ruled IN,
 *     section 3 -- "the user needs to pick a device type when they
 *     add a device").
 *   Closet: rides the existing adopt-as-device machinery
 *     (`api.wigMakeDevice()`, the same call ir-promote-dialog.ts's
 *     Adopt Device flow uses), via ir-wig-picker.ts. Device Type is
 *     the same editable select, EXCEPT a matrix-backed wig locks it to
 *     `ac` and disables the select (owner's own exception, "unless,
 *     of course, it's a stateful air-conditioning" -- mirrors
 *     ir-promote-dialog.ts's `isMatrix` treatment exactly).
 *   Sniffer / Clipper / Plucker (signpost 3, Track 1 item 4): each its
 *     own kind-colored tab now, REPLACING the single grouped-with-
 *     chips "Remote" tab shell from signpost 2 (ir-remote-picker.ts,
 *     retired outright -- see ir-source-picker.ts's header for why).
 *     Plucker renders only when `.pluckerConfigured` is true. Rows are
 *     REAL, live-fetched via the already-standalone-callable
 *     `api.getUnknownDevices({source})` (one call per kind, lazily on
 *     first tab visit, cached per dialog instance) -- a genuine
 *     improvement over the old always-empty placeholder. LIVE
 *     (Track 4 bench-gate fix): picking a row calls
 *     `api.createDevice()` with `promoted_from_unknown_id` set to
 *     that row's id -- ws_create_device's existing promote branch
 *     (Track 2 item 2) copies the source's signals into commands and
 *     auto-maps them server-side, the same path Track 3.1 already
 *     wired for the four catalog surfaces' USE fork. This dialog just
 *     calls it from a second door.
 *   Remotes (signpost 3, Track 1 item 4, NEW -- the device-from-remote
 *     mirror door): pick an existing named Remote, gold like every
 *     other `trigger`-kind surface. Rows come from `.triggerRemotes`,
 *     a prop rather than a fresh fetch -- `ha-panel-ir-devices.ts`
 *     already hoists and keeps this list fresh
 *     (`_refreshTriggerRemotes()`), so this dialog reuses it instead
 *     of duplicating the call. LIVE (Track 4 bench-gate fix): picking
 *     a row calls `api.remoteMakeDevice()`
 *     (hair/trigger-remote/make-device) -- the same mirror-door call
 *     the settings dialog's "Make a Device" row already uses (Track 2
 *     item 7), reached from a second door here.
 *
 * No `origin` field on the create payload: the backend has no such
 * field on devices yet (Track 1B only added it to the trigger-remote
 * side), and the coding plan scopes origin-field wiring to Track 3
 * ("it's this dialog's whole reason for existing") -- Track 2's own
 * item list (7-11) never mentions it. Sending an unrecognized key on
 * a voluptuous-validated websocket command would just error, so this
 * dialog omits it rather than guess a backend contract that isn't
 * built.
 *
 * DROP MODE (signpost 3, Track 1 item 3): set `.dropSource` to a
 * WigPickRow and the dialog renders as s11's "Drop mode" frame --
 * tab row and source picker both suppressed, a synopsis line in their
 * place (`adddc.preview_creates`, plus a MATRIX tag when the wig is
 * matrix-shaped), name prefilled from the wig's label, and the
 * hardware footer (Device Type + emitter picker) always expanded, no
 * escape hatch back to a source picker. Creation rides the same
 * `wigMakeDevice()` path the Closet tab uses -- a drop always lands
 * as a wig in the Closet first (per the mockup note), so by the time
 * this dialog opens in drop mode the source is already resolved to a
 * real WigPickRow, not a raw File.
 *
 * Note this dialog's `_isMatrixSource` gate now covers a real case:
 * ir-wig-picker.ts's own `_pick()` refuses to select a matrix row
 * (matrix wigs are Adopt-only, never Closet-tab-pickable), so before
 * drop mode existed the Closet tab could never actually reach a
 * matrix `_pickedWig` -- this getter's `_activeTab === "closet"` half
 * was future-proofing with no live path to it. Drop mode is that
 * path: `dropSource` is assigned programmatically (the caller already
 * resolved the wig via the funnel), bypassing the picker's own click
 * restriction, so a matrix wig CAN arrive here now.
 *
 * Actually catching a file drop, running it through the funnel, and
 * opening this dialog with `.dropSource` set is Track 2 item 3 / Track
 * 3 item 3's job (subject to the Track 0 funnel-callability finding,
 * confirmed callable) -- this component only knows how to render and
 * create once a source is already in hand.
 *
 * Fires `device-created` with detail: IRDevice, from every tab now
 * (Track 4 bench-gate fix retired the Sniffer/Clipper/Plucker/Remotes
 * exception).
 *
 * SOURCE / DEVICE / EMITTERS sections (punch list item 6,
 * owner-approved 2026-08-16): the per-tab source body, the (now-
 * hoisted) Type select + Name field, and the emitter picker each now
 * render inside their own `.dlg-section` with a `.dlg-section-head`
 * label -- DEVICE and EMITTERS render identically and unconditionally
 * on every tab; SOURCE is absent on Manual and collapses to a header +
 * synopsis line (no picker) in drop mode. Only the SOURCE header's
 * text picks up the active tab's origin color; the Create button lost
 * its per-tab fill and is static green to match
 * ir-duplicate-device-dialog.ts. Mirrors the identical rework landing
 * in parallel on this file's sibling, ir-add-trigger-remote-dialog.ts
 * (SOURCE/REMOTE/RECEIVERS there vs SOURCE/DEVICE/EMITTERS here) --
 * NOT touched by this file's own patch. See _renderSourceSection() /
 * _renderDeviceSection() / _renderEmittersSection() below.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles, dialogTabStyles } from "./ir-dialog-styles.js";
import { ORIGIN_COLORS, REMOTE_KIND_COLORS } from "./ir-origin-colors.js";
import "./ir-emitter-picker.js";
import "./ir-wig-picker.js";
import "./ir-source-picker.js";
import type { HairApi } from "./api.js";
import type {
    DeviceTypeId,
    IRDevice,
    SignalSourceId,
    TriggerRemoteInfo,
} from "./types.js";
import type { WigPickRow } from "./ir-wig-picker.js";
import type { SourcePickRow } from "./ir-source-picker.js";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "media_player", label: "Media Player" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "light", label: "Light" },
    { value: "switch", label: "Switch" },
    { value: "screen", label: "Screen / Shade" },
    { value: "other", label: "Other" },
];

/** Kind tabs backed by hair/unknown/devices -- Sniffer/Clipper/Plucker
 *  share one list call, discriminated by `source`. "Remotes" isn't in
 *  this set: it rides `.triggerRemotes` instead, not an unknown-device
 *  fetch -- see the file header. */
type SourceKind = "sniffer" | "clipper" | "plucker";
const UNKNOWN_SOURCE: Record<SourceKind, SignalSourceId> = {
    sniffer: "sniffed",
    clipper: "manual",
    plucker: "plucked",
};
/** Tab labels for these three stay hardcoded English on purpose --
 *  matching ha-panel-ir-devices.ts's own main nav bar, which renders
 *  "Sniffer" / "Clipper" / "Plucker" as literal strings rather than
 *  through t() (brand names for this app's acquisition doors, not
 *  common nouns). */
const SOURCE_KIND_LABEL: Record<SourceKind, string> = {
    sniffer: "Sniffer",
    clipper: "Clipper",
    plucker: "Plucker",
};

type Tab = "manual" | "closet" | SourceKind | "remotes";

@customElement("ir-add-controlled-device-dialog")
export class IrAddControlledDeviceDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;

    /** Set to render in drop mode -- see the file header. The caller
     *  has already run the drop through the funnel and landed a wig in
     *  the Closet; this is that wig's picker row. */
    @property({ attribute: false }) public dropSource: WigPickRow | null = null;

    /** Whether this install has a Plucker source configured at all --
     *  gates the Plucker tab entirely, same rule ir-remote-picker.ts
     *  (and the main nav's own Plucker tab) used. */
    @property({ type: Boolean }) public pluckerConfigured = false;

    /** Existing named Remotes, for the Remotes tab. A prop, not a
     *  fetch -- see the file header on why this dialog doesn't
     *  duplicate ha-panel-ir-devices.ts's own list call. */
    @property({ attribute: false }) public triggerRemotes: TriggerRemoteInfo[] = [];

    @state() private _activeTab: Tab = "manual";
    @state() private _name = "";
    private _nameEdited = false;
    @state() private _deviceType: DeviceTypeId = "media_player";
    @state() private _emitterIds: string[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    /** Closet tab's current pick, if any. Cleared on tab switch away
     *  from Closet so a stale pick can't leak into a Manual create. */
    @state() private _pickedWig: WigPickRow | null = null;

    /** Sniffer/Clipper/Plucker/Remotes tab's current pick, if any
     *  (Track 4 bench-gate fix) -- one field covers all four since
     *  only one of them is ever the active tab at a time, and
     *  ir-source-picker.ts emits the same SourcePickRow shape
     *  regardless of kind. Cleared on tab switch. */
    @state() private _pickedSourceRow: SourcePickRow | null = null;

    /** Sniffer/Clipper/Plucker rows, fetched lazily per kind on first
     *  tab visit and cached for the life of this dialog instance.
     *  Absent key = not yet fetched; present (possibly empty) = done. */
    @state() private _sourceRows: Partial<Record<SourceKind, SourcePickRow[]>> = {};
    @state() private _sourceLoading: SourceKind | null = null;

    private get _dropMode(): boolean {
        return !!this.dropSource;
    }

    /** The wig this create should ride, whichever door supplied it. */
    private get _effectiveWig(): WigPickRow | null {
        return this.dropSource ?? this._pickedWig;
    }

    private get _isMatrixSource(): boolean {
        return (
            (this._dropMode || this._activeTab === "closet") &&
            !!this._effectiveWig?.wig?.matrix
        );
    }

    protected willUpdate(changed: PropertyValues): void {
        if (changed.has("dropSource") && this.dropSource) {
            if (!this._nameEdited) {
                this._name = this.dropSource.label;
            }
            if (this.dropSource.wig?.matrix) {
                this._deviceType = "ac";
            }
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _setTab(tab: Tab): void {
        if (tab === this._activeTab) return;
        this._activeTab = tab;
        this._error = null;
        this._pickedSourceRow = null;
        if (tab === "sniffer" || tab === "clipper" || tab === "plucker") {
            void this._ensureSourceRows(tab);
        }
    }

    private async _ensureSourceRows(kind: SourceKind): Promise<void> {
        if (this._sourceRows[kind] || this._sourceLoading === kind) return;
        this._sourceLoading = kind;
        try {
            const list = await this.api.getUnknownDevices({
                source: UNKNOWN_SOURCE[kind],
            });
            this._sourceRows = {
                ...this._sourceRows,
                [kind]: list.map(
                    (d): SourcePickRow => ({
                        id: d.id,
                        name: d.label ?? d.protocol ?? t("common.raw"),
                        sub: tp("mirror.signals", d.signal_count),
                        count: d.signal_count,
                    }),
                ),
            };
        } catch {
            // Fail quiet -- Create is disabled on this tab regardless
            // (see the file header); an empty preview is honest enough
            // and matches how a genuinely-empty source would render.
            this._sourceRows = { ...this._sourceRows, [kind]: [] };
        } finally {
            if (this._sourceLoading === kind) this._sourceLoading = null;
        }
    }

    private _onWigPicked(e: CustomEvent<{ value: string; row: WigPickRow }>): void {
        this._pickedWig = e.detail.row;
        if (!this._nameEdited) {
            this._name = e.detail.row.label;
        }
        if (e.detail.row.wig?.matrix) {
            this._deviceType = "ac";
        }
    }

    /** Sniffer/Clipper/Plucker/Remotes tab pick (Track 4 bench-gate
     *  fix) -- same shape _onWigPicked already handles for Closet. */
    private _onSourceRowPicked(
        e: CustomEvent<{ value: string; row: SourcePickRow }>,
    ): void {
        this._pickedSourceRow = e.detail.row;
        if (!this._nameEdited) {
            this._name = e.detail.row.name;
        }
    }

    private async _create(): Promise<void> {
        const name = this._name.trim();
        if (!name) {
            this._error = t("common.name_required");
            return;
        }
        if (this._emitterIds.length === 0) {
            this._error = t("adddev.emitter_required");
            return;
        }
        const wig = this._effectiveWig;
        if (!this._dropMode && this._activeTab === "closet" && !wig) {
            this._error = t("adddc.pick_source_required");
            return;
        }
        if (
            !this._dropMode &&
            (this._activeTab === "sniffer" ||
                this._activeTab === "clipper" ||
                this._activeTab === "plucker" ||
                this._activeTab === "remotes") &&
            !this._pickedSourceRow
        ) {
            this._error = t("common.pick_row_required");
            return;
        }

        this._busy = true;
        this._error = null;
        try {
            let created: IRDevice;
            if ((this._dropMode || this._activeTab === "closet") && wig) {
                const source =
                    wig.source === "local"
                        ? { filename: wig.wig!.filename }
                        : {
                              codebookId: wig.codebook!.id,
                          };
                created = await this.api.wigMakeDevice(
                    source,
                    name,
                    this._deviceType,
                    this._emitterIds,
                );
            } else if (
                this._activeTab === "sniffer" ||
                this._activeTab === "clipper" ||
                this._activeTab === "plucker"
            ) {
                // Sniffer/Clipper/Plucker promote (Track 4 bench-gate
                // fix): one call -- ws_create_device's
                // promoted_from_unknown_id branch (Track 2 item 2)
                // copies the source's signals into commands and
                // auto-maps them server-side.
                created = await this.api.createDevice({
                    name,
                    device_type: this._deviceType,
                    emitter_entity_ids: this._emitterIds,
                    capture_device_id: null,
                    capture_provider_type: "esphome",
                    promoted_from_unknown_id: this._pickedSourceRow!.id,
                });
            } else if (this._activeTab === "remotes") {
                // Remotes tab (Track 4 bench-gate fix): the device-
                // from-remote mirror door, same trigger-remote/
                // make-device call the "Make a Device" settings-dialog
                // row already uses (Track 2 item 7).
                created = await this.api.remoteMakeDevice(
                    this._pickedSourceRow!.id,
                    name,
                    this._deviceType,
                    this._emitterIds,
                );
            } else {
                created = await this.api.createDevice({
                    name,
                    device_type: this._deviceType,
                    emitter_entity_ids: this._emitterIds,
                    capture_device_id: null,
                    capture_provider_type: "esphome",
                });
            }
            this.dispatchEvent(
                new CustomEvent("device-created", {
                    detail: created,
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

    private _tabColor(tab: Tab): string {
        if (tab === "manual" || tab === "closet") return ORIGIN_COLORS[tab];
        if (tab === "remotes") return REMOTE_KIND_COLORS.trigger;
        return REMOTE_KIND_COLORS[tab];
    }

    render() {
        const sourceColor = this._dropMode
            ? ORIGIN_COLORS.closet
            : this._tabColor(this._activeTab);
        return html`
            <ha-dialog
                open
                heading=${t("adddc.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._dropMode
                    ? ""
                    : html`
                          <div class="dlg-tabs">
                              ${this._renderTab("manual", t("adddc.tab_manual"))}
                              ${this._renderTab("closet", t("adddc.tab_closet"))}
                              ${this._renderTab("sniffer", SOURCE_KIND_LABEL.sniffer)}
                              ${this._renderTab("clipper", SOURCE_KIND_LABEL.clipper)}
                              ${this.pluckerConfigured
                                  ? this._renderTab("plucker", SOURCE_KIND_LABEL.plucker)
                                  : ""}
                              ${this._renderTab("remotes", t("adddc.tab_remotes"))}
                          </div>
                      `}

                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                ${this._renderSourceSection(sourceColor)}
                ${this._renderDeviceSection()}
                ${this._renderEmittersSection()}

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${t("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy ? t("common.creating") : t("adddev.create")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    private _renderTab(tab: Tab, label: string) {
        const active = this._activeTab === tab;
        const color = this._tabColor(tab);
        return html`
            <button
                class="dlg-tab ${active ? "active" : ""}"
                style=${active ? `color:${color};border-bottom-color:${color};` : ""}
                @click=${() => this._setTab(tab)}
            >
                ${label}
            </button>
        `;
    }

    /** SOURCE section dispatcher (punch list item 6): absent on Manual
     *  (dialog opens straight into DEVICE), a header + synopsis-only
     *  line in drop mode (no picker -- s11's "Drop mode" frame), a
     *  header + picker + preview line on every other tab. `color` is
     *  the active tab's origin/kind color (`_tabColor()`, same lookup
     *  the tab pills and picker highlight already use) -- tints the
     *  header TEXT only; DEVICE, EMITTERS, and the Create button never
     *  see it. */
    private _renderSourceSection(color: string) {
        if (this._dropMode) {
            return this._renderSourceSectionShell(color, this._renderDropSourceBody());
        }
        if (this._activeTab === "manual") {
            return "";
        }
        if (this._activeTab === "closet") {
            return this._renderSourceSectionShell(color, this._renderClosetBody());
        }
        if (this._activeTab === "remotes") {
            return this._renderSourceSectionShell(color, this._renderRemotesBody());
        }
        return this._renderSourceSectionShell(
            color,
            this._renderSourceBody(this._activeTab as SourceKind),
        );
    }

    private _renderSourceSectionShell(color: string, body: unknown) {
        return html`
            <div class="dlg-section">
                <div class="dlg-section-head">
                    <h5 style="color:${color}">${t("adddc.section_source")}</h5>
                </div>
                ${body}
            </div>
        `;
    }

    private _renderClosetBody() {
        return html`
            <div class="dlg-source-picker-wrap">
                <ir-wig-picker
                    .api=${this.api}
                    .value=${this._pickedWig?.id ?? null}
                    ?disabled=${this._busy}
                    @wig-picked=${this._onWigPicked}
                ></ir-wig-picker>
            </div>

            <div class="dlg-preview-line ${this._pickedWig ? "" : "none"}">
                ${this._pickedWig
                    ? html`${t("adddc.preview_creates", {
                          count: String(this._pickedWig.signalCount),
                          name: this._pickedWig.label,
                      })}`
                    : t("adddc.preview_select_source")}
            </div>
        `;
    }

    /** Sniffer/Clipper/Plucker: fixed-height wrap + 3-row skeleton
     *  shimmer while `_sourceLoading === kind`, in place of
     *  `<ir-source-picker>`'s own plain-text "Loading..." row for this
     *  call site (punch list item 6 -- no second height jump when real
     *  rows land). Preview line's own space stays reserved via
     *  `visibility:hidden`, not `display:none`, during that window. */
    private _renderSourceBody(kind: SourceKind) {
        const loading = this._sourceLoading === kind;
        return html`
            <div class="dlg-source-picker-wrap">
                ${loading
                    ? this._renderSourceSkeleton()
                    : html`
                          <ir-source-picker
                              .kind=${kind}
                              .rows=${this._sourceRows[kind] ?? []}
                              .selectedId=${this._pickedSourceRow?.id ?? null}
                              ?disabled=${this._busy}
                              @row-picked=${this._onSourceRowPicked}
                          ></ir-source-picker>
                      `}
            </div>

            <div
                class="dlg-preview-line ${this._pickedSourceRow ? "" : "none"}"
                style=${loading ? "visibility:hidden" : ""}
            >
                ${this._pickedSourceRow
                    ? html`${t("adddc.preview_creates", {
                          count: String(this._pickedSourceRow.count ?? 0),
                          name: this._pickedSourceRow.name,
                      })}`
                    : t("adddc.preview_select_source")}
            </div>
        `;
    }

    private _renderSourceSkeleton() {
        return html`
            <div class="dlg-skeleton-row"></div>
            <div class="dlg-skeleton-row"></div>
            <div class="dlg-skeleton-row"></div>
        `;
    }

    private _renderRemotesBody() {
        const rows: SourcePickRow[] = this.triggerRemotes.map((r) => ({
            id: r.id,
            name: r.name,
            sub: tp("trow.header_count", r.trigger_count),
            count: r.trigger_count,
        }));
        return html`
            <div class="dlg-source-picker-wrap">
                <ir-source-picker
                    kind="trigger"
                    .rows=${rows}
                    .selectedId=${this._pickedSourceRow?.id ?? null}
                    ?disabled=${this._busy}
                    @row-picked=${this._onSourceRowPicked}
                ></ir-source-picker>
            </div>

            <div class="dlg-preview-line ${this._pickedSourceRow ? "" : "none"}">
                ${this._pickedSourceRow
                    ? html`${t("adddc.preview_creates", {
                          count: String(this._pickedSourceRow.count ?? 0),
                          name: this._pickedSourceRow.name,
                      })}`
                    : t("adddc.preview_select_source")}
            </div>
        `;
    }

    /** Drop mode's SOURCE content (punch list item 6): a single
     *  dlg-preview-line synopsis using the new `adddc.preview_dropped`
     *  pattern ("Dropped X -- creates a device with N commands") instead
     *  of the generic `adddc.preview_creates` every picker tab uses --
     *  drop mode's source was never a row the user picked from a list,
     *  so it reads better named as what it is. The wig's own label gets
     *  wrapped in <b> wherever the translated string actually places
     *  it, so word order still varies safely per locale. No tab row, no
     *  picker; the header wrapping this now comes from
     *  _renderSourceSectionShell(), not this method. */
    private _renderDropSourceBody() {
        const wig = this._effectiveWig;
        if (!wig) return html``;
        const text = t("adddc.preview_dropped", {
            name: wig.label,
            count: String(wig.signalCount),
        });
        const idx = text.indexOf(wig.label);
        return html`
            <div class="dlg-preview-line">
                ${idx >= 0
                    ? html`${text.slice(0, idx)}<b>${wig.label}</b>${text.slice(
                          idx + wig.label.length,
                      )}`
                    : text}
                ${this._isMatrixSource
                    ? html`<span class="reduced-note">${t("common.matrix_tag")}</span>`
                    : ""}
            </div>
        `;
    }

    /** DEVICE section (punch list item 6): the Type select, hoisted out
     *  of every per-tab body above so it renders identically no matter
     *  which tab is active -- position (first, above Name) and behavior
     *  (disabled + hint line for a matrix-backed wig, via the existing
     *  `_isMatrixSource` getter) are unchanged, only the label moved
     *  from "Device type" (`common.device_type`, still used by
     *  ir-assign-signal-dialog.ts and ir-promote-dialog.ts, left alone)
     *  to "Type" (`adddc.type_label`, new). The Name field is hoisted
     *  here too, now carrying its own live "Required" attention: an
     *  `input`-bound (not blur/change) border tint + caption that fires
     *  the instant the field is empty and clears the instant a
     *  character lands, off one derived boolean with no intermediate
     *  state. Deliberately separate from `_error`'s submit-time
     *  <ha-alert> above -- that stays --error-color red and only
     *  `_create()` sets it; this is pre-submit guidance in
     *  --primary-color blue. */
    private _renderDeviceSection() {
        const nameEmpty = this._name.trim().length === 0;
        return html`
            <div class="dlg-section">
                <div class="dlg-section-head"><h5>${t("common.kind_device")}</h5></div>

                <div class="field">
                    <label>${t("adddc.type_label")}</label>
                    <select
                        .value=${this._deviceType}
                        ?disabled=${this._isMatrixSource}
                        @change=${(e: Event) =>
                            (this._deviceType = (e.target as HTMLSelectElement)
                                .value as DeviceTypeId)}
                    >
                        ${DEVICE_TYPES.map(
                            (dt) => html`
                                <option value=${dt.value} ?selected=${this._deviceType === dt.value}>
                                    ${t(`device_type.${dt.value}`)}
                                </option>
                            `,
                        )}
                    </select>
                    ${this._isMatrixSource
                        ? html`<div class="type-hint">${t("promote.matrix_type_hint")}</div>`
                        : ""}
                </div>

                <div class="field ${nameEmpty ? "req-empty" : ""}">
                    <label>${t("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${t("common.device_name_placeholder")}
                        ?disabled=${this._busy}
                        @input=${(e: Event) => {
                            this._name = (e.target as HTMLInputElement).value;
                            this._nameEdited = true;
                        }}
                    />
                    ${nameEmpty
                        ? html`<div class="field-req-caption">
                              ${t("adddc.name_required_caption")}
                          </div>`
                        : ""}
                </div>
            </div>
        `;
    }

    /** EMITTERS section (punch list item 6): the hoisted emitter
     *  picker, always present, identical on every tab -- content
     *  unchanged, reuses the already-shipped `devlist.emitters`
     *  ("Emitters") label rather than minting a duplicate string. */
    private _renderEmittersSection() {
        return html`
            <div class="dlg-section">
                <div class="dlg-section-head"><h5>${t("devlist.emitters")}</h5></div>
                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${(e: CustomEvent) =>
                        (this._emitterIds = e.detail.value)}
                ></ir-emitter-picker>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        dialogTabStyles,
        css`
            ha-alert {
                display: block;
                margin: 8px 0;
            }
            .field {
                margin: 12px 0;
            }
            .type-hint {
                font-size: 11px;
                color: var(--secondary-text-color);
                margin-top: 4px;
                line-height: 1.4;
            }

            /* --- SOURCE / DEVICE / EMITTERS section shell (punch list
               item 6) -- CSS recipe lifted verbatim from
               ir-device-list.ts's own shipped .section-header, sized
               down slightly (0.7rem vs 0.82rem) to read as a dialog
               sub-label rather than a full page section. --- */
            .dlg-section-head {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 0 0 10px;
                padding-top: 12px;
                border-top: 2px solid var(--divider-color);
            }
            .dlg-section:first-child .dlg-section-head {
                padding-top: 0;
                border-top: none;
                margin-top: 0;
            }
            .dlg-section-head h5 {
                margin: 0;
                font-size: 0.7rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-weight: 700;
                color: var(--secondary-text-color);
            }

            /* --- Name field's live "Required" attention (punch list
               item 6) -- instant, input-bound, one boolean drives both
               halves together. Separate from the submit-time
               <ha-alert> path in _create(). --- */
            .field.req-empty input[type="text"] {
                border-color: rgba(77, 171, 247, 0.55);
                box-shadow: 0 0 0 3px rgba(77, 171, 247, 0.12);
            }
            .field-req-caption {
                font-size: 0.68rem;
                color: var(--primary-color);
                margin-top: 5px;
                display: flex;
                align-items: center;
                gap: 5px;
            }
            .field-req-caption::before {
                content: "";
                width: 5px;
                height: 5px;
                border-radius: 50%;
                background: var(--primary-color);
                flex-shrink: 0;
            }

            /* --- Create button: static green (punch list item 6) --
               matches ir-duplicate-device-dialog.ts's own create-btn
               exactly (#2e7d32, the same hex ir-origin-colors.ts's own
               ORIGIN_COLORS.device comment already earmarks for this
               button); no longer tinted by the active tab's origin
               color -- the tab pill, the picker's selected-row
               highlight, and the SOURCE header text all keep that
               tint. --- */
            .create-btn {
                background: #2e7d32;
                color: #fff;
                border: none;
            }
            .create-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
            .create-btn:disabled {
                background: none !important;
                border-color: var(--divider-color) !important;
                color: var(--secondary-text-color);
            }

            /* --- SOURCE picker fixed geometry + skeleton loading
               (punch list item 6) -- a fixed max-height so switching to
               a tab with more/fewer rows doesn't reflow the dialog's
               vertical anchor, and a 3-row shimmer placeholder for the
               Sniffer/Clipper/Plucker fetch window so the real rows
               landing doesn't cause a second height jump. Closet and
               Remotes get the same wrap for visual consistency, no
               skeleton overlay -- ir-wig-picker.ts owns its own loading
               state internally and isn't touched by this pass; the
               Remotes tab's rows are a prop, never actually async here.
               --- */
            .dlg-source-picker-wrap {
                /* No max-height/overflow here: ir-source-picker.ts and
                   ir-wig-picker.ts already cap and scroll their own
                   internal .list at 320px. A second scroll region on
                   this wrap produced a visible double scrollbar (bench
                   catch, 2026-08-16) since 220px is smaller than the
                   inner list can grow to. */
            }
            .dlg-skeleton-row {
                height: 46px;
                border-radius: 6px;
                margin-bottom: 6px;
                background: linear-gradient(
                    90deg,
                    var(--secondary-background-color) 25%,
                    var(--divider-color) 37%,
                    var(--secondary-background-color) 63%
                );
                background-size: 400% 100%;
                animation: dlg-skeleton-sheen 1.4s ease infinite;
            }
            .dlg-skeleton-row:last-child {
                margin-bottom: 0;
            }
            @keyframes dlg-skeleton-sheen {
                0% {
                    background-position: 100% 50%;
                }
                100% {
                    background-position: 0 50%;
                }
            }

            /* --- Fixed geometry: top-anchored, grows down only (punch
               list item 6). --vertical-align-dialog is the documented
               HA 'ha-dialog' token for top-aligning the surface instead
               of vertically centering (and re-centering on every
               content-height change, which is the default mwc-dialog
               behavior this override exists to defeat); the fixed top
               margin is this file's own best-effort companion,
               mirrored from the identical override landing in this
               dialog's sibling, ir-add-trigger-remote-dialog.ts (same
               punch list item, same day). ha-dialog's internals aren't
               vendored in this repo to confirm either token against
               real HA frontend source -- flag for visual QA once this
               actually builds. --- */
            ha-dialog {
                --vertical-align-dialog: flex-start;
                --dialog-surface-margin-top: 40px;
            }

            @media (max-width: 768px) {
                .dlg-tabs {
                    gap: 0;
                }
                .dlg-tab {
                    font-size: 0.78rem;
                    padding: 8px 4px;
                }
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-add-controlled-device-dialog": IrAddControlledDeviceDialog;
    }
}
