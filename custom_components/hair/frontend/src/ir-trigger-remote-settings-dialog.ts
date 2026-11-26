/**
 * Remote settings dialog: the Remote-detail sibling of
 * ir-device-settings-dialog.ts, opened from the gear in the Remote
 * detail header (ir-device-list.ts). A separate, smaller component
 * rather than a "kind" prop on the Device dialog. The Remote's name and
 * receivers live in its header, not here.
 *
 * Its sections are cards (settings-section-styles.ts), as the Device
 * dialog's are:
 *   - Power, for a typed Remote whose type has power (a media player,
 *     fan, light or switch): the Device's own fields
 *     (ir-power-source-section.ts), so a state source corrects the
 *     Remote's entity as it corrects a Device's. It is never copied to
 *     or from a Device; each is set on its own.
 *   - Cover, for a Remote typed as a screen: its kind of cover (GH
 *     #313), the Device dialog's menu (ir-cover-class-field.ts). Made
 *     from a Device, a Remote starts with the Device's kind.
 *   - Make a Device, a card with its button: this dialog only asks for
 *     the mint (request-make-device) and ir-device-list.ts's
 *     <ir-promote-dialog> makes it.
 *
 * The footer is the Device dialog's: Delete on the left; Duplicate and,
 * with the Power or the Cover card, Save on the right. A Remote with nothing to
 * save here gets no Save. Delete and Duplicate dispatch request-delete
 * and request-duplicate, so the Remote card's own flows do the work.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { CoverDeviceClass, TriggerRemoteInfo } from "./types.js";
import {
    coverClassForSave,
    coverClassLabelKey,
    coverClassShown,
} from "./cover-class.js";
import { renderCoverClassField } from "./ir-cover-class-field.js";
import {
    sectionAccentHost,
    settingsSectionStyles,
} from "./settings-section-styles.js";
import type { IrPowerSourceSection } from "./ir-power-source-section.js";
import "./ir-power-source-section.js";

@customElement("ir-trigger-remote-settings-dialog")
export class IrTriggerRemoteSettingsDialog extends LitElement {
    @property({ attribute: false }) public api?: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public remote!: TriggerRemoteInfo;

    @state() private _busy = false;
    @state() private _error: string | null = null;
    /** The Power and Cover cards start open. A Remote gets one of them
     * at most: a screen has no power. */
    @state() private _powerOpen = true;
    @state() private _coverOpen = true;
    @state() private _coverClass: CoverDeviceClass = "shade";

    firstUpdated(): void {
        this._coverClass = coverClassShown(this.remote.cover_device_class);
    }

    updated(): void {
        this.toggleAttribute("dark", Boolean(this.hass?.themes?.darkMode));
    }

    /** A typed Remote whose type has power gets the Power card, and Save
     * with it. */
    private get _hasPower(): boolean {
        return this.remote.power_eligible === true;
    }

    /** A Remote typed as a screen gets the Cover card, and Save with
     * it. */
    private get _hasCover(): boolean {
        return this.remote.device_type === "screen";
    }

    /** Whether there is anything here to save. */
    private get _saves(): boolean {
        return this._hasPower || this._hasCover;
    }

    private get _power(): IrPowerSourceSection | null {
        return this.renderRoot?.querySelector("ir-power-source-section") ?? null;
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _requestDuplicate(): void {
        this.dispatchEvent(
            new CustomEvent("request-duplicate", { bubbles: true, composed: true }),
        );
        this._close();
    }

    private _requestDelete(): void {
        this.dispatchEvent(
            new CustomEvent("request-delete", { bubbles: true, composed: true }),
        );
        this._close();
    }

    /** "Make a Device": this dialog does not mint anything itself,
     *  ir-device-list.ts's <ir-promote-dialog> (sourceRemoteId mode)
     *  does, the same ask-and-get-out-of-the-way shape as Duplicate and
     *  Delete. */
    private _requestMakeDevice(): void {
        this.dispatchEvent(
            new CustomEvent("request-make-device", { bubbles: true, composed: true }),
        );
        this._close();
    }

    private async _save(): Promise<void> {
        if (this._busy || !this.api) return;
        const power = this._hasPower ? this._power : null;
        if (this._hasPower && !power) return;
        const validation = power?.validationError;
        if (validation) {
            this._error = validation;
            this._powerOpen = true;
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            if (power) {
                await this.api.setTriggerRemotePower(this.remote.id, power.patch());
                this.dispatchEvent(
                    new CustomEvent("remote-power-changed", {
                        bubbles: true,
                        composed: true,
                    }),
                );
            }
            if (this._hasCover) {
                await this.api.setTriggerRemoteCoverClass(
                    this.remote.id,
                    coverClassForSave(this._coverClass),
                );
                this.dispatchEvent(
                    new CustomEvent("remote-cover-changed", {
                        bubbles: true,
                        composed: true,
                    }),
                );
            }
            this._close();
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    render() {
        const power = this._power;
        const problem = power?.validationError ?? null;
        return html`
            <ha-dialog
                open
                heading=${t("devsettings.remote_title")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <div ?hidden=${!this._error}>
                    <ha-alert alert-type="error">${this._error}</ha-alert>
                </div>
                <div
                    class="card card-power ${this._powerOpen ? "open" : ""}"
                    ?hidden=${!this._hasPower}
                >
                    <h3 class="card-heading">
                        <button
                            type="button"
                            class="card-head"
                            aria-expanded=${this._powerOpen ? "true" : "false"}
                            aria-controls="card-body-power"
                            @click=${() => (this._powerOpen = !this._powerOpen)}
                        >
                            <span class="card-text">
                                <span class="card-title"
                                    >${t("devsettings.power_title")}</span
                                >
                                <span class="card-sum"
                                    >${problem ?? power?.summary ?? ""}</span
                                >
                            </span>
                            <span class="card-fold" aria-hidden="true"></span>
                        </button>
                    </h3>
                    <div
                        class="card-body"
                        id="card-body-power"
                        ?hidden=${!this._powerOpen}
                    >
                        ${this._hasPower
                            ? html`<ir-power-source-section
                                  .hass=${this.hass}
                                  .source=${this.remote}
                                  .busy=${this._busy}
                                  forRemote
                                  @power-source-change=${() => this.requestUpdate()}
                              ></ir-power-source-section>`
                            : ""}
                    </div>
                </div>
                <div
                    class="card card-cover ${this._coverOpen ? "open" : ""}"
                    ?hidden=${!this._hasCover}
                >
                    <h3 class="card-heading">
                        <button
                            type="button"
                            class="card-head"
                            aria-expanded=${this._coverOpen ? "true" : "false"}
                            aria-controls="card-body-cover"
                            @click=${() => (this._coverOpen = !this._coverOpen)}
                        >
                            <span class="card-text">
                                <span class="card-title"
                                    >${t("devsettings.cover_title")}</span
                                >
                                <span class="card-sum"
                                    >${t(coverClassLabelKey(this._coverClass))}</span
                                >
                            </span>
                            <span class="card-fold" aria-hidden="true"></span>
                        </button>
                    </h3>
                    <div
                        class="card-body"
                        id="card-body-cover"
                        ?hidden=${!this._coverOpen}
                    >
                        ${this._hasCover
                            ? renderCoverClassField(
                                  this._coverClass,
                                  this._busy,
                                  (kind) => (this._coverClass = kind),
                              )
                            : ""}
                    </div>
                </div>
                <div class="card card-action section-convert">
                    <div class="card-row">
                        <div class="card-text">
                            <h3 class="card-heading card-title">
                                ${t("devsettings.make_device_title")}
                            </h3>
                            <span class="card-sum">
                                ${t("devsettings.make_device_desc")}
                            </span>
                        </div>
                        <button
                            class="action-btn convert-btn card-action-btn"
                            @click=${this._requestMakeDevice}
                        >
                            ${t("devsettings.make_device_btn")}
                        </button>
                    </div>
                </div>
                <div class="dialog-actions">
                    <button
                        class="action-btn delete-btn"
                        @click=${this._requestDelete}
                        ?disabled=${this._busy}
                    >
                        ${t("devsettings.delete")}
                    </button>
                    <span class="actions-spacer"></span>
                    <button
                        class="action-btn duplicate-btn"
                        @click=${this._requestDuplicate}
                        ?disabled=${this._busy}
                    >
                        ${t("devsettings.duplicate")}
                    </button>
                    ${this._saves
                        ? html`<button
                              class="action-btn save-btn"
                              @click=${this._save}
                              ?disabled=${this._busy || !!problem}
                          >
                              ${this._busy ? t("common.saving") : t("common.save")}
                          </button>`
                        : ""}
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
            /* The same footer as the Device settings dialog, so the two
             * read as one family: Delete alone on the left, the
             * constructive side on the right. Save shows only with the
             * Power or the Cover card; the shape is the rule, not the
             * button count. */
            .duplicate-btn {
                background: none;
                border-color: #43a047;
                color: #43a047;
            }
            .duplicate-btn:hover:not(:disabled) {
                background: rgba(67, 160, 71, 0.14);
            }
            .delete-btn {
                background: none;
                border-color: #e65100;
                color: #e65100;
            }
            .delete-btn:hover:not(:disabled) {
                background: rgba(230, 81, 0, 0.14);
            }
            .save-btn {
                background: #3f8a4b;
                color: #fff;
                border-color: #3f8a4b;
            }
            .save-btn:hover:not(:disabled) {
                opacity: 0.9;
            }
        `,
        sectionAccentHost,
        settingsSectionStyles,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-trigger-remote-settings-dialog": IrTriggerRemoteSettingsDialog;
    }
}
