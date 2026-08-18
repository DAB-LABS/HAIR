/**
 * Dialog for promoting an unknown Sniffer device to a full HAIR device
 * -- or, since signpost 3 Track 3.5 (owner-directed 2026-08-15), for
 * the reverse mirror-door mint: creating a HAIR device straight from
 * a live Trigger Remote's own triggers when `sourceRemoteId` is set
 * (ir-trigger-remote-settings-dialog.ts's convert section, "Make a
 * Device"; hair/trigger-remote/make-device). That door carries no
 * matrix concept -- a Remote's triggers are always flat -- so
 * isMatrix and the type lock below never apply to it.
 *
 * Creates the device only -- signal assignment happens separately via
 * the assign-signal dialog.
 *
 * Fires `device-created` on success (bubbles/composed, detail is the
 * minted IRDevice -- every door, not just the mirror-door one, per
 * signpost 3 Track 3 item 5's USE-fork pin-prompt trigger), `closed`
 * on cancel / close.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-emitter-picker.js";
import type { HairApi } from "./api.js";
import type { DeviceTypeId } from "./types.js";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "media_player", label: "Media Player" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "light", label: "Light" },
    { value: "switch", label: "Switch" },
    { value: "screen", label: "Screen / Shade" },
    { value: "other", label: "Other" },
];

@customElement("ir-promote-dialog")
export class IrPromoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    /** Pre-filled device name from the unknown device label. */
    @property() public suggestedName = "";
    @property() public sourceUnknownId = "";
    /** Adopt Device (v0.8.1): when set, create FROM THIS WIG via the
     * direct-copy path instead of a catalog promote. */
    @property() public wigFilename = "";
    /** Library rows (v0.8.1): when set, adopt straight from this
     * codebook -- the backend renders a transient wig, nothing is
     * written to the closet. Mutually exclusive with wigFilename. */
    @property() public codebookId = "";
    /** Live Trigger Remote door (signpost 3, Track 3.5): mutually
     *  exclusive with every door above -- the "Make a Device"
     *  mirror-door mint, sourced from this remote's own triggers
     *  rather than a wig or a Sniffer catalog row. */
    @property() public sourceRemoteId = "";
    /** Seed the type dropdown (from the wig's kind); user can change. */
    @property() public suggestedType: DeviceTypeId | "" = "";
    /** Cold Cuts (v0.8.8): adopting a matrix wig locks the type to
     * Air Conditioner. The backend refuses anything else, so the lock
     * is honest UI, not a suggestion (owner ruling 2026-07-28). */
    @property({ type: Boolean }) public isMatrix = false;

    @state() private _name = "";
    @state() private _type: DeviceTypeId = "other";
    @state() private _emitterIds: string[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        if (this.suggestedName && !this._name) {
            this._name = this.suggestedName;
        }
        if (this.suggestedType) {
            this._type = this.suggestedType;
        }
        if (this.isMatrix) {
            this._type = "ac";
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
            this._error = t("promote.device_name_required");
            return;
        }
        if (this._emitterIds.length === 0) {
            this._error = t("promote.emitter_required");
            return;
        }

        this._busy = true;
        this._error = null;

        try {
            // Every door's minted object rides as the event's detail
            // (signpost 3, Track 3 item 5, owner-directed
            // 2026-08-15): the USE fork's already-linked pin-prompt
            // trigger needs the new device's id/name on all four
            // catalog surfaces, not just the Track 3.5 mirror door
            // this shape originally shipped for.
            let minted: Awaited<ReturnType<typeof this.api.createDevice>>;
            if (this.sourceRemoteId) {
                minted = await this.api.remoteMakeDevice(
                    this.sourceRemoteId,
                    name,
                    this._type,
                    this._emitterIds,
                );
            } else if (this.wigFilename || this.codebookId) {
                minted = await this.api.wigMakeDevice(
                    this.wigFilename
                        ? { filename: this.wigFilename }
                        : { codebookId: this.codebookId },
                    name,
                    this._type,
                    this._emitterIds,
                );
            } else {
                minted = await this.api.createDevice({
                    name,
                    device_type: this._type,
                    emitter_entity_ids: this._emitterIds,
                    promoted_from_unknown_id: this.sourceUnknownId || null,
                });
            }
            this.dispatchEvent(
                new CustomEvent("device-created", {
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
                heading=${t("promote.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <p class="description">${t("promote.description")}</p>

                <div class="field">
                    <label>${t("promote.device_name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${t("common.device_name_placeholder")}
                        required
                        autofocus
                        @input=${(e: Event) =>
                            (this._name = (e.target as HTMLInputElement)
                                .value)}
                        @keydown=${(e: KeyboardEvent) => {
                            if (e.key === "Enter") void this._create();
                        }}
                    />
                </div>

                <div class="field">
                    <label>${t("common.device_type")}</label>
                    <select
                        .value=${this._type}
                        ?disabled=${this.isMatrix}
                        @change=${(e: Event) =>
                            (this._type = (e.target as HTMLSelectElement)
                                .value as DeviceTypeId)}
                    >
                        ${DEVICE_TYPES.map(
                            (dt) => html`
                                <option
                                    value=${dt.value}
                                    ?selected=${this._type === dt.value}
                                >
                                    ${t(`device_type.${dt.value}`)}
                                </option>
                            `,
                        )}
                    </select>
                    ${this.isMatrix
                        ? html`<div class="type-hint">
                              ${t("promote.matrix_type_hint")}
                          </div>`
                        : ""}
                </div>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${(e: CustomEvent) =>
                        (this._emitterIds = e.detail.value)}
                ></ir-emitter-picker>

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
                        ${this._busy ? t("common.creating") : t("promote.create_device")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
        /* NOTE: no ha-textfield here anymore. This dialog was the
           panel's last ha-textfield user; the element is lazy-loaded by
           the HA frontend and is not reliably defined inside a custom
           panel, so it rendered as an empty, unfocusable shell (shampoo
           bench). The name box is now the shared .field + plain input,
           the same proven pattern as every other dialog. */
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .description {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 0 0 8px;
        }
        /* Why the type select is locked (matrix adopts): one dim line,
           same voice as the editor's field hints. */
        .type-hint {
            font-size: 11px;
            color: var(--secondary-text-color);
            margin-top: 4px;
            line-height: 1.4;
        }
        .create-btn {
            background: #2e7d32;
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
        "ir-promote-dialog": IrPromoteDialog;
    }
}
