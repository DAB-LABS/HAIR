/**
 * Add Trigger Remote dialog (add-popups, signpost 2, Track 3; drop
 * mode added signpost 3, Track 1 item 3; per-kind source tabs added
 * signpost 3, Track 1 item 4).
 *
 * GATED on Track 1B's bench gate (create a named remote, see it as a
 * targetable device, add+fire a trigger, rename, delete-takes-its-
 * triggers, drawer untouched) -- confirmed passing before this track
 * started. Every creation path below writes into that model.
 *
 * Six tabs, same create grammar Track 2 established (brief section 3):
 * pick a source or none, see a live preview, confirm a name, Create.
 * The footer -- name field, ir-receiver-picker -- is constant across
 * all six tabs now (signpost 3, Track 4 bench-gate fix, 2026-08-17 --
 * see signpost-3-coding-plan.md section 3a), mirroring
 * ir-add-controlled-device-dialog.ts, except the picker is receivers
 * (this dialog's hardware), not emitters. The three Sniffer/Clipper/
 * Plucker tabs below used to stay inert pending a backend contract
 * Track 2 item 2 had, in fact, already built; they call it directly
 * now.
 *
 *   Manual: a blank named remote. No Device Type analog -- TriggerRemote
 *     has no such field, unlike IRDevice.
 *   Closet: ir-wig-picker.ts (Track 1) supplies the source row, same
 *     component and same matrix-row-disabled behavior Track 2's Closet
 *     tab already has -- a matrix wig can never actually be picked here
 *     either through a manual click (see the drop-mode note below for
 *     the one path that changes that), so there is no separate matrix
 *     case to handle in the seeding loop below.
 *   Device: ir-device-picker.ts (Track 1) supplies the source row.
 *     Known gap carried from Track 1 (see that file's header): the list-
 *     level DeviceSummary has no matrix field, so a matrix-backed device
 *     IS pickable here unlike a matrix wig. No special-casing needed
 *     regardless -- IRDevice.commands is already the discrete-only list
 *     (matrix cells live in their own hair/matrices/ file), so seeding
 *     from it naturally yields "the discrete-press subset only" the
 *     matrix rule calls for. A pure-matrix device legitimately seeds
 *     zero triggers; the preview line says that plainly rather than
 *     implying a bug.
 *   Sniffer / Clipper / Plucker (signpost 3, Track 1 item 4): each its
 *     own kind-colored tab now, REPLACING the single grouped-with-
 *     chips "Remote" tab shell from signpost 2 (ir-remote-picker.ts,
 *     retired outright -- see ir-source-picker.ts's header for why).
 *     Plucker renders only when something can actually be plucked
 *     right now (`anyPluckReadyNow`, shared with the other dialog):
 *     this is an action picker, and an action picker offers what can
 *     act. The Plucker TAB is the opposite case and renders always.
 *     Rows are REAL, live-fetched via the already-standalone-callable
 *     `api.getUnknownDevices({source})` (one call per kind, lazily on
 *     first tab visit, cached per dialog instance). LIVE (Track 4
 *     bench-gate fix): picking a row calls `api.createTriggerRemote()`
 *     with `promoted_from_unknown_id` set to that row's id --
 *     ws_create_trigger_remote's existing promote branch (Track 2 item
 *     2, "USE-as-Remote creation from every source: Sniffer promote...
 *     Clipper and Plucker remotes the same way") copies every signal
 *     on the source into named triggers itself, the same path Track
 *     3.1 already wired for the four catalog surfaces' USE fork. This
 *     dialog just calls it from a second door -- and, unlike the
 *     Closet/Device tabs below, needs no seed loop of its own: the one
 *     call does the whole job server-side.
 *
 * Seeding design (this round's steer, in place of a bespoke atomic bulk-
 * create endpoint): create the remote first via createTriggerRemote(),
 * then loop the EXISTING hair/trigger/create call once per discrete
 * signal, now carrying two fields it gained for exactly this
 * (trigger_remote_id, origin) -- see websocket_api.py's docstring. A wig
 * source's per-signal identity (fingerprint/byte_hash/decoded_fingerprint)
 * comes from the new read-only hair/wigs/signals call, since there is no
 * Pronto decoder on the frontend to derive it locally; a device source
 * reuses hair/trigger/create's existing source_device_id +
 * source_command_id resolution verbatim -- that path already existed for
 * the drawer's own dialog.
 *
 * This is N+1 websocket round trips, not one backend transaction, so a
 * failure partway through the loop is handled with a best-effort
 * rollback (delete the just-created remote, which takes its already-
 * seeded triggers with it) rather than leaving a half-seeded remote
 * behind -- see _create()'s catch block.
 *
 * Origin lands on every path in this track, per the provenance ruling --
 * it is this dialog's whole reason for existing. Both the remote's own
 * origin and each seeded trigger's origin are set to the tab that
 * created them (drop mode records "closet", matching where the dropped
 * wig actually landed).
 *
 * DROP MODE (signpost 3, Track 1 item 3): set `.dropSource` to a
 * WigPickRow and the dialog renders as s11's "Drop mode" frame -- tab
 * row and source picker both suppressed, a synopsis line in their place
 * (`addtr.preview_creates`, plus a MATRIX tag when the wig is matrix-
 * shaped), name prefilled from the wig's label, and the hardware footer
 * (receiver picker, ALL-OFF by default -- `_receiverIds` already starts
 * empty, so drop mode gets this for free) always expanded, no escape
 * hatch back to a source picker. Seeding rides the same `_seedFromWig()`
 * path the Closet tab uses. As with the Device dialog, this is the one
 * path that can carry a matrix wig at all: ir-wig-picker's own `_pick()`
 * refuses matrix rows, so `dropSource` (assigned programmatically by the
 * caller, not by a picker click) is what makes `_isMatrixSource` a live
 * case here instead of dead defensive code. A matrix wig legitimately
 * seeds zero triggers via `_seedFromWig()` (matrix cells aren't discrete
 * signals) -- the preview line says so plainly, matching the Device
 * dialog's pure-matrix-device case above.
 *
 * Actually catching a file drop, running it through the funnel, and
 * opening this dialog with `.dropSource` set is Track 2 item 3 / Track
 * 3 item 3's job (subject to the Track 0 funnel-callability finding,
 * confirmed callable) -- this component only knows how to render and
 * seed once a source is already in hand.
 *
 * Fires `remote-created` with detail: TriggerRemoteInfo & { trigger_count }
 * on Manual/Closet/Device (client-computed seed count); on Sniffer/
 * Clipper/Plucker the detail is the bare TriggerRemoteInfo the
 * promoted create call returns, whose own `trigger_count` field the
 * backend already filled in (Track 4 bench-gate fix retired the
 * "stay inert" exception for these three).
 *
 * SOURCE / REMOTE / RECEIVERS sections (punch list item 6,
 * owner-approved 2026-08-16): the per-tab source body, the Name field,
 * and the receiver picker each now render inside their own
 * `.dlg-section` with a `.dlg-section-head` label -- REMOTE (the
 * hoisted Name field) and RECEIVERS render identically and
 * unconditionally on every tab; SOURCE is absent on Manual and
 * collapses to a header + synopsis line (no picker) in drop mode.
 * Only the SOURCE header's text picks up the active tab's origin
 * color; the Create button lost its per-tab fill and is static green
 * to match ir-duplicate-device-dialog.ts. See `_renderSourceSection()`
 * / `_renderRemoteSection()` / `_renderReceiversSection()` below.
 */
import { LitElement, html, css, type PropertyValues } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles, dialogTabStyles } from "./ir-dialog-styles.js";
import { ORIGIN_COLORS, REMOTE_KIND_COLORS } from "./ir-origin-colors.js";
import "./ir-receiver-picker.js";
import "./ir-wig-picker.js";
import "./ir-device-picker.js";
import "./ir-source-picker.js";
import { anyPluckReadyNow } from "./api.js";
import type { HairApi } from "./api.js";
import type {
    DeviceSummary,
    PluckSource,
    SignalSourceId,
    TriggerRemoteInfo,
} from "./types.js";
import type { WigPickRow } from "./ir-wig-picker.js";
import type { SourcePickRow } from "./ir-source-picker.js";

/** Kind tabs backed by hair/unknown/devices -- Sniffer/Clipper/Plucker
 *  share one list call, discriminated by `source`. */
type SourceKind = "sniffer" | "clipper" | "plucker";
const UNKNOWN_SOURCE: Record<SourceKind, SignalSourceId> = {
    sniffer: "sniffed",
    clipper: "manual",
    plucker: "plucked",
};
/** Tab labels for these three stay hardcoded English on purpose --
 *  matching ha-panel-ir-devices.ts's own main nav bar (literal strings,
 *  never through t() -- brand names, not common nouns). */
const SOURCE_KIND_LABEL: Record<SourceKind, string> = {
    sniffer: "Sniffer",
    clipper: "Clipper",
    plucker: "Plucker",
};

type Tab = "manual" | "closet" | "device" | SourceKind;

@customElement("ir-add-trigger-remote-dialog")
export class IrAddTriggerRemoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;

    /** Set to render in drop mode -- see the file header. The caller
     *  has already run the drop through the funnel and landed a wig in
     *  the Closet; this is that wig's picker row. */
    @property({ attribute: false }) public dropSource: WigPickRow | null = null;

    /** The pluckable source roll, straight from the panel.
     *
     *  Read through `anyPluckReadyNow()` rather than by hand, and NOT
     *  the rule the main nav uses any more: the nav's Plucker tab
     *  renders unconditionally now (discovery surfaces always show),
     *  while this dialog is an action picker and shows what works now.
     *  One helper, so the rule cannot drift between the sites. */
    @property({ attribute: false }) public pluckSources: PluckSource[] = [];

    @state() private _activeTab: Tab = "manual";
    @state() private _name = "";
    private _nameEdited = false;
    @state() private _receiverIds: string[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    /** Closet tab's current pick, if any. */
    @state() private _pickedWig: WigPickRow | null = null;
    /** Device tab's current pick, if any. */
    @state() private _pickedDevice: DeviceSummary | null = null;
    /** Sniffer/Clipper/Plucker tab's current pick, if any (Track 4
     *  bench-gate fix) -- one field covers all three since only one
     *  is ever the active tab at a time. Cleared on tab switch. */
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
    }

    private _onDevicePicked(
        e: CustomEvent<{ value: string; device: DeviceSummary }>,
    ): void {
        this._pickedDevice = e.detail.device;
        if (!this._nameEdited) {
            this._name = e.detail.device.name;
        }
    }

    /** Sniffer/Clipper/Plucker tab pick (Track 4 bench-gate fix) --
     *  same shape _onWigPicked / _onDevicePicked already handle. */
    private _onSourceRowPicked(
        e: CustomEvent<{ value: string; row: SourcePickRow }>,
    ): void {
        this._pickedSourceRow = e.detail.row;
        if (!this._nameEdited) {
            this._name = e.detail.row.name;
        }
    }

    /** The tab IS the creation-door discriminator (provenance ruling).
     *  Drop mode always resolves through the Closet (the dropped file
     *  lands as a wig there first), so it records "closet" too. */
    private _origin(): "manual" | "closet" | "device" {
        if (this._dropMode || this._activeTab === "closet") return "closet";
        if (this._activeTab === "device") return "device";
        return "manual";
    }

    private async _seedFromWig(remoteId: string, row: WigPickRow): Promise<number> {
        const source =
            row.source === "local"
                ? { filename: row.wig!.filename }
                : { codebookId: row.codebook!.id };
        const { signals } = await this.api.wigSignals(source);
        for (const sig of signals) {
            await this.api.createTrigger({
                name: sig.name,
                signal_fingerprint: sig.signal_fingerprint,
                code: sig.code,
                byte_hash: sig.byte_hash,
                decoded_fingerprint: sig.decoded_fingerprint,
                trigger_remote_id: remoteId,
                origin: "closet",
            });
        }
        return signals.length;
    }

    private async _seedFromDevice(
        remoteId: string,
        device: DeviceSummary,
    ): Promise<number> {
        const full = await this.api.getDevice(device.id);
        for (const cmd of full.commands) {
            await this.api.createTrigger({
                name: cmd.name,
                source_device_id: device.id,
                source_command_id: cmd.id,
                trigger_remote_id: remoteId,
                origin: "device",
            });
        }
        return full.commands.length;
    }

    private async _create(): Promise<void> {
        const name = this._name.trim();
        if (!name) {
            this._error = t("common.name_required");
            return;
        }
        const wig = this._effectiveWig;
        if (!this._dropMode && this._activeTab === "closet" && !wig) {
            this._error = t("addtr.pick_source_required");
            return;
        }
        if (this._activeTab === "device" && !this._pickedDevice) {
            this._error = t("addtr.pick_device_required");
            return;
        }
        if (
            !this._dropMode &&
            (this._activeTab === "sniffer" ||
                this._activeTab === "clipper" ||
                this._activeTab === "plucker") &&
            !this._pickedSourceRow
        ) {
            this._error = t("common.pick_row_required");
            return;
        }

        this._busy = true;
        this._error = null;
        let createdRemote: TriggerRemoteInfo | null = null;
        try {
            if (
                !this._dropMode &&
                (this._activeTab === "sniffer" ||
                    this._activeTab === "clipper" ||
                    this._activeTab === "plucker")
            ) {
                // Sniffer/Clipper/Plucker promote (Track 4 bench-gate
                // fix): one call -- ws_create_trigger_remote's
                // promoted_from_unknown_id branch (Track 2 item 2)
                // copies every signal on the source catalog remote
                // into named triggers server-side, unlike the Closet/
                // Device doors below which seed client-side in a loop.
                createdRemote = await this.api.createTriggerRemote({
                    name,
                    receiver_scope: this._receiverIds,
                    promoted_from_unknown_id: this._pickedSourceRow!.id,
                });
                this.dispatchEvent(
                    new CustomEvent("remote-created", {
                        detail: createdRemote,
                        bubbles: true,
                        composed: true,
                    }),
                );
                return;
            }

            createdRemote = await this.api.createTriggerRemote({
                name,
                receiver_scope: this._receiverIds,
                origin: this._origin(),
            });

            let seeded = 0;
            if ((this._dropMode || this._activeTab === "closet") && wig) {
                seeded = await this._seedFromWig(createdRemote.id, wig);
            } else if (this._activeTab === "device" && this._pickedDevice) {
                seeded = await this._seedFromDevice(createdRemote.id, this._pickedDevice);
            }

            this.dispatchEvent(
                new CustomEvent("remote-created", {
                    detail: { ...createdRemote, trigger_count: seeded },
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            // Seeding is a loop of independent websocket calls, not one
            // backend transaction (this round's steer, in place of a
            // bespoke bulk-create endpoint) -- see the module doc. A
            // failure partway through would otherwise leave an orphaned,
            // partially-seeded remote in the list. Best-effort roll it
            // back so a retry starts clean; the rollback failing is
            // secondary to the original error and must not mask it.
            if (createdRemote) {
                try {
                    await this.api.deleteTriggerRemote(createdRemote.id);
                } catch {
                    // Nothing more to do -- surface the original error below.
                }
            }
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private _tabColor(tab: Tab): string {
        if (tab === "manual" || tab === "closet" || tab === "device") {
            return ORIGIN_COLORS[tab];
        }
        return REMOTE_KIND_COLORS[tab];
    }

    render() {
        const sourceColor = this._dropMode
            ? ORIGIN_COLORS.closet
            : this._tabColor(this._activeTab);
        return html`
            <ha-dialog
                open
                heading=${t("addtr.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._dropMode
                    ? ""
                    : html`
                          <div class="dlg-tabs">
                              ${this._renderTab("manual", t("addtr.tab_manual"))}
                              ${this._renderTab("closet", t("addtr.tab_closet"))}
                              ${this._renderTab("device", t("addtr.tab_device"))}
                              ${this._renderTab("sniffer", SOURCE_KIND_LABEL.sniffer)}
                              ${this._renderTab("clipper", SOURCE_KIND_LABEL.clipper)}
                              ${anyPluckReadyNow(this.pluckSources)
                                  ? this._renderTab("plucker", SOURCE_KIND_LABEL.plucker)
                                  : ""}
                          </div>
                      `}

                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                ${this._renderSourceSection(sourceColor)}
                ${this._renderRemoteSection()}
                ${this._renderReceiversSection()}

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
     *  (dialog opens straight into REMOTE), a header + synopsis-only
     *  line in drop mode (no picker -- s11's "Drop mode" frame), a
     *  header + picker + preview line on every other tab. `color` is
     *  the active tab's origin/kind color (`_tabColor()`, same lookup
     *  the tab pills use) -- tints the header TEXT only. */
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
        if (this._activeTab === "device") {
            return this._renderSourceSectionShell(color, this._renderDeviceBody());
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
                    <h5 style="color:${color}">${t("addtr.section_source")}</h5>
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
                    ? html`${t("addtr.preview_creates", {
                          count: String(this._pickedWig.signalCount),
                          name: this._pickedWig.label,
                      })}`
                    : t("addtr.preview_select_source")}
            </div>
        `;
    }

    private _renderDeviceBody() {
        return html`
            <div class="dlg-source-picker-wrap">
                <ir-device-picker
                    .api=${this.api}
                    .value=${this._pickedDevice?.id ?? null}
                    ?disabled=${this._busy}
                    @device-picked=${this._onDevicePicked}
                ></ir-device-picker>
            </div>

            <div class="dlg-preview-line ${this._pickedDevice ? "" : "none"}">
                ${this._pickedDevice
                    ? html`${t("addtr.preview_creates", {
                          count: String(this._pickedDevice.command_count),
                          name: this._pickedDevice.name,
                      })}`
                    : t("addtr.preview_select_source")}
            </div>
        `;
    }

    /** Sniffer/Clipper/Plucker: fixed-height wrap + 3-row skeleton
     *  shimmer while `_sourceLoading === kind`, in place of
     *  `<ir-source-picker>`'s own plain-text "Loading..." row for this
     *  call site (punch list item 6 -- no second height jump when real
     *  rows land). Preview line's space stays reserved via
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
                    ? html`${t("addtr.preview_creates", {
                          count: String(this._pickedSourceRow.count ?? 0),
                          name: this._pickedSourceRow.name,
                      })}`
                    : t("addtr.preview_select_source")}
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

    /** Drop mode's SOURCE content: synopsis line (+ MATRIX tag) only --
     *  no Device Type analog here (TriggerRemote has none), no tab row,
     *  no picker, per s11's "Drop mode" frame. The header wrapping this
     *  now comes from `_renderSourceSectionShell()`, punch list item 6
     *  -- previously this was the section's whole (headerless) body. */
    private _renderDropSourceBody() {
        const wig = this._effectiveWig;
        return html`
            <div class="dlg-preview-line">
                ${wig
                    ? html`${t("addtr.preview_creates", {
                          count: String(wig.signalCount),
                          name: wig.label,
                      })}`
                    : ""}
                ${this._isMatrixSource
                    ? html`<span class="reduced-note">${t("common.matrix_tag")}</span>`
                    : ""}
            </div>
        `;
    }

    /** REMOTE section (punch list item 6): the hoisted Name field,
     *  always present, identical on every tab including Manual and
     *  drop mode -- no Device Type analog (TriggerRemote has none).
     *  Live "Required" attention: `input`-bound (not blur/change), so
     *  it fires the instant the field goes empty and clears the
     *  instant a keystroke lands, both off one derived boolean with no
     *  intermediate state. Independent of, and does not touch, the
     *  submit-time `<ha-alert>` path in `_create()`. */
    private _renderRemoteSection() {
        const nameEmpty = this._name.trim().length === 0;
        return html`
            <div class="dlg-section">
                <div class="dlg-section-head"><h5>${t("common.kind_remote")}</h5></div>
                <div class="field ${nameEmpty ? "req-empty" : ""}" style="margin:0;">
                    <label>${t("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${t("addtr.name_placeholder")}
                        ?disabled=${this._busy}
                        @input=${(e: Event) => {
                            this._name = (e.target as HTMLInputElement).value;
                            this._nameEdited = true;
                        }}
                    />
                    ${nameEmpty
                        ? html`<div class="field-req-caption">
                              ${t("addtr.name_required_caption")}
                          </div>`
                        : ""}
                </div>
            </div>
        `;
    }

    /** RECEIVERS section (punch list item 6): the hoisted receiver
     *  picker, always present, identical on every tab. Reuses the
     *  already-shipped `devlist.receivers` ("Receivers") label rather
     *  than minting a duplicate string. */
    private _renderReceiversSection() {
        return html`
            <div class="dlg-section">
                <div class="dlg-section-head"><h5>${t("devlist.receivers")}</h5></div>
                <ir-receiver-picker
                    .api=${this.api}
                    .value=${this._receiverIds}
                    ?disabled=${this._busy}
                    @receivers-changed=${(e: CustomEvent) =>
                        (this._receiverIds = e.detail.value)}
                ></ir-receiver-picker>
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

            /* --- SOURCE / REMOTE / RECEIVERS section shell (punch
               list item 6) -- CSS recipe lifted verbatim from
               ir-device-list.ts's own shipped .section-header, sized
               down slightly (0.7rem vs 0.82rem) to read as a dialog
               sub-label rather than a full page section. */
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
               exactly (#2e7d32); no longer tinted by the active tab's
               origin color (the tab pill, the picker's selected-row
               highlight, and the preview line all keep that tint). */
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

            /* --- Source picker fixed geometry + skeleton loading
               (punch list item 6) -- a fixed max-height so picking a
               tab with more/fewer rows doesn't reflow the dialog's
               vertical anchor, and a 3-row shimmer placeholder for the
               Sniffer/Clipper/Plucker fetch window so real rows
               landing doesn't cause a second height jump. --- */
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
               list item 6). ha-dialog's internals aren't vendored in
               this repo to confirm the exact custom-property names
               against real HA frontend source -- --vertical-align-
               dialog is the documented HA token for top-aligning a
               dialog instead of vertically centering it; the fixed
               top margin is this file's own best-effort fallback.
               Flag for visual QA once this actually builds against a
               real HA frontend. --- */
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
        "ir-add-trigger-remote-dialog": IrAddTriggerRemoteDialog;
    }
}
