/**
 * Dialog for creating or editing an IR trigger.
 *
 * Create mode: pass signalFingerprint, protocol, code (read-only signal info).
 * Edit mode: pass an existing trigger object.
 *
 * Add Popups signpost 2 punch list item 8 (ruled 2026-08-10, scoped
 * 2026-08-17): a REMOTE picker now sits at the top of create mode --
 * HAIR Triggers (the drawer) preselected, every named TriggerRemote
 * listed below it, "+ New Remote" last (opens
 * ir-add-trigger-remote-dialog.ts, nested inside this one, in its
 * default Manual-tab state; its `remote-created` result becomes the
 * new picker selection). Edit mode shows the owning remote as a
 * FIXED, non-interactive label instead -- no picker, no moving a
 * trigger between remotes once created (the "no-moving" ruling).
 * Either way, the receiver picker further down renders only when the
 * effective target is the drawer; a named remote's own receiver_scope
 * covers its triggers instead (trigger_manager.py's
 * _effective_receiver_scope), the same rule that already governed
 * edit mode before this item, now driving create mode's picker too.
 *
 * Emits:
 *   trigger-saved  -- { detail: IRTrigger }
 *   closed         -- dialog dismissed
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-receiver-picker.js";
import "./ir-add-trigger-remote-dialog.js";
import type { HairApi } from "./api.js";
import type { IRTrigger, TriggerRemoteInfo } from "./types.js";

@customElement("ir-trigger-dialog")
export class IrTriggerDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;

    /** For create mode: signal details. */
    @property() public signalFingerprint = "";
    @property() public protocol: string | null = null;
    @property() public code: string | null = null;
    @property() public slPattern: string | null = null;
    /** Optional signal alias, shown instead of bare diamonds when set. */
    @property() public alias: string | null = null;
    /** Byte-level identity of the source signal (v0.5.8). Distinguishes
     * sub-threshold sibling buttons that share an S/L fingerprint. */
    @property() public byteHash: string | null = null;
    /** Decoded protocol identity of the source signal (v0.5.8 unified
     * identity). Jitter-immune tier-1 matching where a decoder exists. */
    @property() public decodedFingerprint: string | null = null;

    /** For create mode: optional source references. */
    @property() public sourceDeviceId: string | null = null;
    @property() public sourceCommandId: string | null = null;

    /** Create mode, signpost 4 Track M: where the REMOTE picker opens.
     * The three matrix doors already know which remote they belong to,
     * so the picker starts on it instead of on the drawer. It stays a
     * picker -- the user may retarget before saving, exactly as on any
     * other create door -- this only sets the starting selection. */
    @property() public remoteId: string | null = null;
    /** Create mode: which door minted this trigger. "matrix" is what
     * earns the row's STATE chip; null everywhere else, which is the
     * pre-Track-M behavior unchanged. */
    @property() public origin: string | null = null;
    /** Create mode: a name the door already knows, pre-filled and
     * still editable. */
    @property() public presetName: string | null = null;

    /** For edit mode: pass the existing trigger. */
    @property({ attribute: false }) public trigger: IRTrigger | null = null;

    // Set when opened from a Mirror row (v0.6.6): renders a one-line note
    // that the echo gate keeps the house's own sends from firing triggers.
    @property({ type: Boolean }) public mirrorContext = false;

    @state() private _name = "";
    @state() private _minHits = 1;
    @state() private _receiverIds: string[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    // Add Popups signpost 2 punch list item 8: REMOTE picker state.
    // null selection = the HAIR Triggers drawer, mirroring the
    // backend's own null-means-drawer convention on
    // IRTrigger.trigger_remote_id -- deliberately no separate
    // frontend sentinel id for "the drawer".
    @state() private _triggerRemotes: TriggerRemoteInfo[] = [];
    @state() private _drawerName: string | null = null;
    @state() private _selectedRemoteId: string | null = null;
    @state() private _showAddRemote = false;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.trigger) {
            this._name = this.trigger.name;
            this._minHits = this.trigger.min_hits;
            this._receiverIds = [...(this.trigger.receiver_entity_ids ?? [])];
        } else if (this.remoteId) {
            // Create mode opened from a door that already knows its
            // remote (signpost 4, Track M). Set before the list loads:
            // the picker renders the selection by id, so it lands
            // correctly whichever arrives first.
            this._selectedRemoteId = this.remoteId;
        }
        if (!this.trigger && this.presetName) {
            // A name the calling door already knows (the matrix doors
            // pass the cell's display name, "Cool 24 Auto"). Editable
            // like any other create-mode name. Deliberately NOT read
            // off ``alias``, which several existing doors already pass
            // for the diamond line and which has never seeded a name.
            this._name = this.presetName;
        }
        void this._loadTriggerRemotes();
    }

    /** Named remotes for the REMOTE picker (create mode) / the fixed
     *  owning-remote label (edit mode), plus the drawer's own live
     *  display name -- best-effort, same catch-and-empty shape
     *  ir-receiver-picker.ts uses for pre-2026.6 HA installs. */
    private async _loadTriggerRemotes(): Promise<void> {
        if (!this.api) return;
        try {
            this._triggerRemotes = await this.api.listTriggerRemotes();
        } catch {
            this._triggerRemotes = [];
        }
        try {
            this._drawerName = (await this.api.getTriggerDrawer()).name;
        } catch {
            this._drawerName = null;
        }
    }

    /** True when the currently-effective target (fixed in edit mode,
     *  picked in create mode) is the HAIR Triggers drawer -- the one
     *  case where a per-trigger receiver scope is meaningful. */
    private get _isDrawerTarget(): boolean {
        const id = this.trigger
            ? this.trigger.trigger_remote_id ?? null
            : this._selectedRemoteId;
        return id === null;
    }

    private _remoteName(id: string): string {
        return (
            this._triggerRemotes.find((r) => r.id === id)?.name ??
            t("common.kind_remote")
        );
    }

    private get _drawerLabel(): string {
        return this._drawerName ?? t("devlist.trigger_drawer_default_name");
    }

    private _pickRemote(id: string | null): void {
        if (this._busy) return;
        this._selectedRemoteId = id;
    }

    private _openAddRemote(): void {
        this._showAddRemote = true;
    }

    private _closeAddRemote(): void {
        this._showAddRemote = false;
    }

    /** ir-add-trigger-remote-dialog.ts's own success event, reused
     *  verbatim -- detail is a TriggerRemoteInfo (plus a client- or
     *  server-computed trigger_count riding along on the same
     *  interface), so no adapter is needed to feed it straight into
     *  the picker's own remote list. */
    private _onRemoteCreated(e: CustomEvent<TriggerRemoteInfo>): void {
        this._showAddRemote = false;
        if (e.detail) {
            this._triggerRemotes = [...this._triggerRemotes, e.detail];
            this._selectedRemoteId = e.detail.id;
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _save(): Promise<void> {
        const name = this._name.trim();
        if (!name) {
            this._error = t("common.name_required");
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            let saved: IRTrigger;
            if (this.trigger) {
                // Edit mode
                saved = await this.api.updateTrigger(this.trigger.id, {
                    name,
                    min_hits: this._minHits,
                    receiver_entity_ids: this._receiverIds,
                });
            } else {
                // Create mode -- signalFingerprint may be empty when
                // creating from a HAIR command; the backend computes it.
                const payload: Parameters<HairApi["createTrigger"]>[0] = {
                    name,
                    protocol: this.protocol,
                    code: this.code,
                    min_hits: this._minHits,
                    source_device_id: this.sourceDeviceId,
                    source_command_id: this.sourceCommandId,
                    receiver_entity_ids: this._receiverIds,
                    // Add Popups signpost 2 punch list item 8: the
                    // REMOTE picker's selection. Sent explicitly (not
                    // omitted for the drawer case) -- the picker
                    // always has a live selection, drawer or named.
                    trigger_remote_id: this._selectedRemoteId,
                };
                if (this.signalFingerprint) {
                    payload.signal_fingerprint = this.signalFingerprint;
                }
                if (this.byteHash) {
                    payload.byte_hash = this.byteHash;
                }
                if (this.decodedFingerprint) {
                    payload.decoded_fingerprint = this.decodedFingerprint;
                }
                // Signpost 4, Track M: the minting door's provenance.
                // Sent only when a door set it, so every pre-Track-M
                // caller keeps producing an origin-less trigger.
                if (this.origin) {
                    payload.origin = this.origin;
                }
                saved = await this.api.createTrigger(payload);
            }
            this.dispatchEvent(
                new CustomEvent("trigger-saved", {
                    detail: saved,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = (err as Error).message ?? t("trigger.save_failed");
        } finally {
            this._busy = false;
        }
    }

    private _emitDelete(): void {
        if (!this.trigger) return;
        this.dispatchEvent(
            new CustomEvent("trigger-delete", {
                detail: { triggerId: this.trigger.id },
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** Compute S/L boolean array from Pronto hex (mirrors backend logic). */
    private _prontoSlArray(hex: string): boolean[] | null {
        const words = hex.trim().split(/\s+/);
        if (words.length < 6) return null;
        const burst1 = parseInt(words[2], 16);
        const burst2 = parseInt(words[3], 16);
        const total = burst1 + burst2;
        const timings = words.slice(4);
        if (timings.length < total * 2) return null;
        const result: boolean[] = [];
        for (let i = 0; i < total * 2; i++) {
            const val = parseInt(timings[i], 16);
            result.push(val >= 0x30); // true = Long, false = Short
        }
        return result.length > 0 ? result : null;
    }

    /** Render diamonds from an S/L pattern string or Pronto hex code. */
    private _renderSignalInfo() {
        const isEdit = !!this.trigger;

        // Named signal: show the alias instead of bare diamonds so the
        // user recognizes which signal this trigger is for.
        if (!isEdit && this.alias) {
            return html`<span class="alias-inline"
                ><span class="alias-tag">${t("trigger.alias_tag")}</span
                ><span class="alias-name">${this.alias}</span></span
            >`;
        }

        // Try S/L pattern string first (from sniffer create mode).
        const patternStr = isEdit ? null : this.slPattern;
        if (patternStr) {
            return html`<span class="diamonds">${[...patternStr].map((ch) =>
                ch === "L"
                    ? html`<span class="diamond long">&#9670;</span>`
                    : html`<span class="diamond short">&#9671;</span>`
            )}</span>`;
        }

        // Try computing from Pronto hex code.
        const prontoCode = isEdit ? this.trigger!.code : this.code;
        const protocol = isEdit ? this.trigger!.protocol : this.protocol;
        if (protocol?.toUpperCase() === "PRONTO" && prontoCode) {
            const arr = this._prontoSlArray(prontoCode);
            if (arr) {
                return html`<span class="diamonds">${arr.map((isLong) =>
                    isLong
                        ? html`<span class="diamond long">&#9670;</span>`
                        : html`<span class="diamond short">&#9671;</span>`
                )}</span>`;
            }
        }

        // Fallback.
        return html`<span class="proto">${t("trigger.event")}</span>`;
    }

    render() {
        const isEdit = !!this.trigger;

        return html`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${(e: Event) => e.stopPropagation()}>
                    <h3 class="heading">
                        ${isEdit ? t("trigger.edit_heading") : t("trigger.create_heading")}
                    </h3>

                    <!-- Signal info (read-only) -->
                    <div class="signal-info">
                        ${this._renderSignalInfo()}
                    </div>

                    ${this.mirrorContext
                        ? html`<p class="field-hint scope-hint">
                              ${t("trigger.mirror_hint")}
                          </p>`
                        : ""}

                    <!-- REMOTE target (punch list item 8). Create mode:
                         a picker -- HAIR Triggers preselected, every
                         named remote below it, "+ New Remote" last.
                         Edit mode: a fixed, non-interactive label (no
                         moving a trigger between remotes once
                         created). Either way this decides whether the
                         receiver picker further down is inert (a
                         named remote owns its own receiver scope) or
                         live (the drawer's per-trigger scope). -->
                    <label class="field-label">${t("devlist.trigger_remotes_title")}</label>
                    ${isEdit
                        ? html`
                              <div class="remote-fixed">
                                  ${this._isDrawerTarget
                                      ? this._drawerLabel
                                      : this._remoteName(this.trigger!.trigger_remote_id!)}
                              </div>
                          `
                        : html`
                              <div class="remote-picker-list">
                                  <button
                                      type="button"
                                      class="remote-row ${this._selectedRemoteId === null ? "selected" : ""}"
                                      ?disabled=${this._busy}
                                      @click=${() => this._pickRemote(null)}
                                  >${this._drawerLabel}</button>
                                  ${this._triggerRemotes.map(
                                      (r) => html`
                                          <button
                                              type="button"
                                              class="remote-row ${this._selectedRemoteId === r.id ? "selected" : ""}"
                                              ?disabled=${this._busy}
                                              @click=${() => this._pickRemote(r.id)}
                                          >${r.name}</button>
                                      `,
                                  )}
                                  <button
                                      type="button"
                                      class="remote-row new-remote"
                                      ?disabled=${this._busy}
                                      @click=${this._openAddRemote}
                                  >${t("trigger.new_remote_option")}</button>
                              </div>
                          `}

                    <!-- Name -->
                    <label class="field-label">${t("trigger.name_label")}</label>
                    <input
                        class="field-input"
                        type="text"
                        placeholder=${t("trigger.name_placeholder")}
                        .value=${this._name}
                        @input=${(e: Event) => {
                            this._name = (e.target as HTMLInputElement).value;
                        }}
                        ?disabled=${this._busy}
                    />

                    <!-- Min Hits -->
                    <label class="field-label">
                        ${t("trigger.min_hits")}
                        <span class="field-hint">
                            ${t("trigger.min_hits_hint")}
                        </span>
                    </label>
                    <input
                        class="field-input hits-input"
                        type="number"
                        min="1"
                        max="10"
                        .value=${String(this._minHits)}
                        @input=${(e: Event) => {
                            const v = parseInt(
                                (e.target as HTMLInputElement).value,
                                10,
                            );
                            if (v >= 1 && v <= 10) this._minHits = v;
                        }}
                        ?disabled=${this._busy}
                    />

                    <!-- Receiver scope: a remote-owned trigger has no
                         per-trigger scope at all (trigger_manager.py's
                         _effective_receiver_scope resolves it entirely
                         from the owning TriggerRemote's receiver_scope,
                         Track 1B-B6) -- showing the picker here would be
                         inert and read as "no receiver set" when the
                         trigger is, in fact, scoped, just one level up.
                         Point at the remote's own view instead. Punch
                         list item 8 extends this same rule to create
                         mode: picking a named remote in the picker
                         above hides this section entirely, exactly
                         like it already does once a trigger is saved
                         onto one (_isDrawerTarget covers both). -->
                    ${this._isDrawerTarget
                        ? html`
                              <div class="receiver-field">
                                  <ir-receiver-picker
                                      .api=${this.api}
                                      .value=${this._receiverIds}
                                      ?disabled=${this._busy}
                                      @receivers-changed=${(e: CustomEvent) => {
                                          this._receiverIds = e.detail.value;
                                      }}
                                  ></ir-receiver-picker>
                                  <p class="field-hint scope-hint">
                                      ${t("trigger.scope_hint")}
                                  </p>
                              </div>
                          `
                        : html`
                              <p class="field-hint scope-hint">
                                  ${t("trigger.remote_scope_note")}
                              </p>
                          `}

                    ${this._error
                        ? html`<p class="error">${this._error}</p>`
                        : ""}

                    <div class="actions">
                        ${isEdit
                            ? html`<button
                                  class="btn delete-btn"
                                  @click=${this._emitDelete}
                                  ?disabled=${this._busy}
                              >${t("common.delete")}</button>`
                            : ""}
                        <span class="actions-spacer"></span>
                        <button
                            class="btn cancel"
                            @click=${this._close}
                            ?disabled=${this._busy}
                        >${t("common.cancel")}</button>
                        <button
                            class="btn save"
                            @click=${this._save}
                            ?disabled=${this._busy || !this._name.trim()}
                        >${this._busy
                            ? t("common.saving")
                            : isEdit
                              ? t("common.update")
                              : t("common.create")}</button>
                    </div>
                </div>
            </div>

            ${this._showAddRemote
                ? html`
                      <ir-add-trigger-remote-dialog
                          .api=${this.api}
                          @closed=${this._closeAddRemote}
                          @remote-created=${this._onRemoteCreated}
                      ></ir-add-trigger-remote-dialog>
                  `
                : ""}
        `;
    }

    static styles = [
        dialogStyles,
        css`
        .signal-info {
            padding: 8px 12px;
            background: var(--secondary-background-color);
            border-radius: 6px;
            margin-bottom: 16px;
            font-family: var(--code-font-family, monospace);
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .proto {
            text-transform: uppercase;
            font-weight: 500;
        }
        .alias-inline {
            display: inline-flex;
            align-items: baseline;
            gap: 7px;
        }
        .alias-tag {
            font-size: 0.6rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: #ba7517;
        }
        .alias-name {
            font-size: 0.9rem;
            color: var(--primary-color);
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .field-label {
            display: block;
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--primary-text-color);
            margin-bottom: 4px;
        }
        .field-hint {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.78rem;
            margin-left: 4px;
        }
        .field-input {
            display: block;
            width: 100%;
            box-sizing: border-box;
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            font-size: 0.9rem;
            font-family: inherit;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            margin-bottom: 14px;
            outline: none;
            transition: border-color 150ms ease;
        }
        .field-input:focus {
            border-color: var(--primary-color);
        }
        .field-input:disabled {
            opacity: 0.5;
        }
        .hits-input {
            width: 80px;
        }
        .remote-fixed {
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            font-size: 0.9rem;
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
            margin-bottom: 14px;
        }
        .remote-picker-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-bottom: 14px;
            max-height: 160px;
            overflow-y: auto;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 4px;
        }
        .remote-row {
            display: block;
            width: 100%;
            box-sizing: border-box;
            text-align: left;
            padding: 7px 10px;
            border: 1px solid transparent;
            border-radius: 5px;
            background: none;
            font-family: inherit;
            font-size: 0.85rem;
            color: var(--primary-text-color);
            cursor: pointer;
            transition: background 140ms ease, border-color 140ms ease;
        }
        .remote-row:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .remote-row:disabled {
            cursor: default;
            opacity: 0.55;
        }
        .remote-row.selected {
            border-color: #b89930;
            background: rgba(184, 153, 48, 0.12);
            font-weight: 500;
        }
        .remote-row.new-remote {
            color: var(--primary-color);
            border-top: 1px solid var(--divider-color);
            border-radius: 0 0 5px 5px;
            margin-top: 2px;
        }
        .receiver-field {
            margin-bottom: 14px;
        }
        .scope-hint {
            margin: 6px 0 0;
            margin-left: 0;
        }
        .error {
            color: #e65100;
            font-size: 0.85rem;
            margin: 0 0 12px;
        }
        .actions {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 4px;
        }
        .actions-spacer {
            flex: 1;
        }
        .btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .btn:hover {
            background: var(--secondary-background-color);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel {
            color: var(--secondary-text-color);
        }
        /* Create is ALWAYS green, across every create dialog (add-dialog
           form clarity ruling, 2026-08-16; punch list item 18). This
           button was the trigger family's one holdout in gold, which
           read as "gold means trigger" rather than "green means the
           thing this dialog makes". Gold keeps everything it actually
           owns -- the trigger chips, the "+ Trigger" doors on the
           matrix card and the LAST HEARD row -- and this one hex now
           matches ir-add-controlled-device-dialog.ts and
           ir-duplicate-device-dialog.ts exactly. Edit mode's Update
           rides the same class, which is correct: same button, same
           position, same primary meaning. */
        .save {
            color: #fff;
            background: #2e7d32;
            border-color: #2e7d32;
        }
        .save:hover:not(:disabled) {
            opacity: 0.9;
        }
        .delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.3);
        }
        .delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-trigger-dialog": IrTriggerDialog;
    }
}
