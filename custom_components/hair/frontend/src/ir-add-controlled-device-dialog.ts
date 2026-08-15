/**
 * Add Controlled Device dialog (add-popups, signpost 2, Track 2).
 *
 * Replaces the two-tile Add Device chooser -- formally superseded,
 * owner-ruled 2026-08-13, and per the coding plan's own review pass
 * that chooser was never actually built/shipped in the first place.
 * The real retirement target, ir-add-device-dialog.ts (the old
 * + New Device dialog), was cut over to this dialog and deleted
 * outright in Track 4 -- not just unlinked, the class/tag no longer
 * exists in the built bundle at all.
 *
 * Three tabs, one create grammar (brief section 3): pick a source (or
 * none, on Manual), see a live preview line, confirm a name, Create.
 * The footer -- name field, emitter picker, Create -- is constant
 * across every tab including Manual.
 *
 *   Manual: rides the same `createDevice()` call verbatim that
 *     ir-add-device-dialog.ts used before its Track 4 retirement,
 *     Device Type restored (ruled IN,
 *     section 3 -- "the user needs to pick a device type when they
 *     add a device").
 *   Closet: rides the existing adopt-as-device machinery
 *     (`api.wigMakeDevice()`, the same call ir-promote-dialog.ts's
 *     Adopt Device flow uses), via the new ir-wig-picker.ts. Device
 *     Type is the same editable select, EXCEPT a matrix-backed wig
 *     locks it to `ac` and disables the select (owner's own exception,
 *     "unless, of course, it's a stateful air-conditioning" -- mirrors
 *     ir-promote-dialog.ts's `isMatrix` treatment exactly).
 *   Remote: inert shell (ir-remote-picker.ts), wiring lands signpost 3.
 *     Create stays disabled on this tab; the footer caption points at
 *     Manual/Closet instead.
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
 * Fires `device-created` with detail: IRDevice (Manual/Closet only --
 * Remote is inert and never fires it this signpost).
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles, dialogTabStyles } from "./ir-dialog-styles.js";
import { ORIGIN_COLORS } from "./ir-origin-colors.js";
import "./ir-emitter-picker.js";
import "./ir-wig-picker.js";
import "./ir-remote-picker.js";
import type { HairApi } from "./api.js";
import type { DeviceTypeId, IRDevice } from "./types.js";
import type { WigPickRow } from "./ir-wig-picker.js";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "media_player", label: "Media Player" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "light", label: "Light" },
    { value: "switch", label: "Switch" },
    { value: "screen", label: "Screen / Shade" },
    { value: "other", label: "Other" },
];

type Tab = "manual" | "closet" | "remote";

@customElement("ir-add-controlled-device-dialog")
export class IrAddControlledDeviceDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;

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

    private get _isMatrixSource(): boolean {
        return this._activeTab === "closet" && !!this._pickedWig?.wig?.matrix;
    }

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
        if (e.detail.row.wig?.matrix) {
            this._deviceType = "ac";
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
        if (this._activeTab === "closet" && !this._pickedWig) {
            this._error = t("adddc.pick_source_required");
            return;
        }

        this._busy = true;
        this._error = null;
        try {
            let created: IRDevice;
            if (this._activeTab === "closet" && this._pickedWig) {
                const source =
                    this._pickedWig.source === "local"
                        ? { filename: this._pickedWig.wig!.filename }
                        : {
                              codebookId: this._pickedWig.codebook!.id,
                          };
                created = await this.api.wigMakeDevice(
                    source,
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
        return tab === "remote" ? ORIGIN_COLORS.remote : ORIGIN_COLORS[tab];
    }

    render() {
        const color = this._tabColor(this._activeTab);
        return html`
            <ha-dialog
                open
                heading=${t("adddc.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <div class="dlg-tabs">
                    ${this._renderTab("manual", t("adddc.tab_manual"))}
                    ${this._renderTab("closet", t("adddc.tab_closet"))}
                    ${this._renderTab("remote", t("adddc.tab_remote"))}
                </div>

                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                ${this._activeTab === "manual" ? this._renderManualBody() : ""}
                ${this._activeTab === "closet" ? this._renderClosetBody() : ""}
                ${this._activeTab === "remote" ? this._renderRemoteBody() : ""}

                ${this._activeTab !== "remote"
                    ? html`
                          <div class="field">
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
                          </div>
                          <ir-emitter-picker
                              .hass=${this.hass}
                              .api=${this.api}
                              .value=${this._emitterIds}
                              ?disabled=${this._busy}
                              @emitters-changed=${(e: CustomEvent) =>
                                  (this._emitterIds = e.detail.value)}
                          ></ir-emitter-picker>
                      `
                    : html`<p class="dlg-empty-line">${t("adddc.remote_caption")}</p>`}

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

    private _renderManualBody() {
        return html`
            <div class="field">
                <label>${t("common.device_type")}</label>
                <select
                    .value=${this._deviceType}
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
            </div>
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

            <div class="field">
                <label>${t("common.device_type")}</label>
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
            .type-hint {
                font-size: 11px;
                color: var(--secondary-text-color);
                margin-top: 4px;
                line-height: 1.4;
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
        "ir-add-controlled-device-dialog": IrAddControlledDeviceDialog;
    }
}
