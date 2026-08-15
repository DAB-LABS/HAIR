/**
 * Add Trigger Remote dialog (add-popups, signpost 2, Track 3).
 *
 * GATED on Track 1B's bench gate (create a named remote, see it as a
 * targetable device, add+fire a trigger, rename, delete-takes-its-
 * triggers, drawer untouched) -- confirmed passing before this track
 * started. Every creation path below writes into that model.
 *
 * Four tabs, same create grammar Track 2 established (brief section 3):
 * pick a source or none, see a live preview, confirm a name, Create.
 * The footer -- name field, ir-receiver-picker -- is constant across
 * every tab including Manual, mirroring ir-add-controlled-device-dialog.ts,
 * except the picker is receivers (this dialog's hardware), not emitters.
 *
 *   Manual: a blank named remote. No Device Type analog -- TriggerRemote
 *     has no such field, unlike IRDevice.
 *   Closet: ir-wig-picker.ts (Track 1) supplies the source row, same
 *     component and same matrix-row-disabled behavior Track 2's Closet
 *     tab already has -- a matrix wig can never actually be picked here
 *     either, so there is no separate matrix case to handle in the
 *     seeding loop below.
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
 *   Remote: inert shell (ir-remote-picker.ts), same treatment as Track 2
 *     step 10 -- Create stays disabled, footer caption points elsewhere.
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
 * created them.
 *
 * Fires `remote-created` with detail: TriggerRemoteInfo & { trigger_count }
 * (Manual/Closet/Device only -- Remote is inert and never fires it this
 * signpost).
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles, dialogTabStyles } from "./ir-dialog-styles.js";
import { ORIGIN_COLORS } from "./ir-origin-colors.js";
import "./ir-receiver-picker.js";
import "./ir-wig-picker.js";
import "./ir-device-picker.js";
import "./ir-remote-picker.js";
import type { HairApi } from "./api.js";
import type { DeviceSummary, TriggerRemoteInfo } from "./types.js";
import type { WigPickRow } from "./ir-wig-picker.js";

type Tab = "manual" | "closet" | "device" | "remote";

@customElement("ir-add-trigger-remote-dialog")
export class IrAddTriggerRemoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;

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

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _setTab(tab: Tab): void {
        this._activeTab = tab;
        this._error = null;
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

    /** The tab IS the creation-door discriminator (provenance ruling). */
    private _origin(): "manual" | "closet" | "device" {
        if (this._activeTab === "closet") return "closet";
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
        if (this._activeTab === "closet" && !this._pickedWig) {
            this._error = t("addtr.pick_source_required");
            return;
        }
        if (this._activeTab === "device" && !this._pickedDevice) {
            this._error = t("addtr.pick_device_required");
            return;
        }

        this._busy = true;
        this._error = null;
        let createdRemote: TriggerRemoteInfo | null = null;
        try {
            createdRemote = await this.api.createTriggerRemote({
                name,
                receiver_scope: this._receiverIds,
                origin: this._origin(),
            });

            let seeded = 0;
            if (this._activeTab === "closet" && this._pickedWig) {
                seeded = await this._seedFromWig(createdRemote.id, this._pickedWig);
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
        return ORIGIN_COLORS[tab];
    }

    render() {
        const color = this._tabColor(this._activeTab);
        return html`
            <ha-dialog
                open
                heading=${t("addtr.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <div class="dlg-tabs">
                    ${this._renderTab("manual", t("addtr.tab_manual"))}
                    ${this._renderTab("closet", t("addtr.tab_closet"))}
                    ${this._renderTab("device", t("addtr.tab_device"))}
                    ${this._renderTab("remote", t("addtr.tab_remote"))}
                </div>

                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                ${this._activeTab === "closet" ? this._renderClosetBody() : ""}
                ${this._activeTab === "device" ? this._renderDeviceBody() : ""}
                ${this._activeTab === "remote" ? this._renderRemoteBody() : ""}

                ${this._activeTab !== "remote"
                    ? html`
                          <div class="field">
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
                          </div>
                          <ir-receiver-picker
                              .api=${this.api}
                              .value=${this._receiverIds}
                              ?disabled=${this._busy}
                              @receivers-changed=${(e: CustomEvent) =>
                                  (this._receiverIds = e.detail.value)}
                          ></ir-receiver-picker>
                      `
                    : html`<p class="dlg-empty-line">${t("addtr.remote_caption")}</p>`}

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
                        style="background:${color};border-color:${color};"
                        @click=${this._create}
                        ?disabled=${this._busy || this._activeTab === "remote"}
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

    private _renderClosetBody() {
        return html`
            <ir-wig-picker
                .api=${this.api}
                .value=${this._pickedWig?.id ?? null}
                ?disabled=${this._busy}
                @wig-picked=${this._onWigPicked}
            ></ir-wig-picker>

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
            <ir-device-picker
                .api=${this.api}
                .value=${this._pickedDevice?.id ?? null}
                ?disabled=${this._busy}
                @device-picked=${this._onDevicePicked}
            ></ir-device-picker>

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

    private _renderRemoteBody() {
        return html`
            <ir-remote-picker .groups=${[]} .pluckerConfigured=${false}></ir-remote-picker>
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
            .create-btn {
                color: #fff;
            }
            .create-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
            .create-btn:disabled {
                background: none !important;
                border-color: var(--divider-color) !important;
                color: var(--secondary-text-color);
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
