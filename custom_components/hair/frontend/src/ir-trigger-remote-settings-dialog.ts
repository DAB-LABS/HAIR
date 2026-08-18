/**
 * Remote settings dialog (Add Popups signpost 3, Track 1 item 6, s10
 * "Settings + header pin management").
 *
 * The Remote-detail sibling of ir-device-settings-dialog.ts, opened
 * from the new universal gear button in ir-device-list.ts's inline
 * Remote detail header (.trh-header). A separate, smaller component
 * rather than a generalized "kind" prop bolted onto the Device
 * dialog: a Remote has no power/climate sections (those are strictly
 * Device-only, gated by settingsSections()) and, per s10, no Save
 * button either -- there is nothing left for a Remote to save through
 * Settings once name (the header's own inline rename) and receiver
 * scope (the header's Receivers: chip group, Track 1 item 5) both
 * already live outside this dialog. s10's own frame still draws a
 * Save button on the Remote settings popup, but nothing in that frame
 * is actually editable through it -- shipping a Save button with
 * nothing behind it would be exactly the "control that visibly does
 * nothing" this arc's PINNING_UI_ENABLED gate exists to avoid
 * elsewhere (ir-pin-flag.ts), so it's omitted here rather than copied
 * for pixel parity with the mockup. Flag at the bench checkpoint if
 * the owner wants it back for visual symmetry with the Device dialog.
 *
 * Holds, per s10:
 *   - the "Make a Device" mirror-door row (description + fixed-width
 *     button cell) -- wired since signpost 3 Track 3.5 (owner-directed
 *     2026-08-15) to hair/trigger-remote/make-device via
 *     ir-device-list.ts's <ir-promote-dialog> (sourceRemoteId mode).
 *     The gap flagged at the Track 3.4 checkpoint (Track 2.2 covered
 *     Sniffer/Clipper/Plucker/Closet-wig sources but never a live
 *     Remote's own triggers) is now closed; this dialog only asks for
 *     the mint (_requestMakeDevice) and gets out of the way, same as
 *     Duplicate/Delete below.
 *   - Duplicate (outlined GREEN_PEAK #43a047) and Delete (outlined
 *     ember #e65100) -- both dual-entry with the Remote card's own
 *     existing corner actions (_openDuplicateRemoteDialog /
 *     _requestDeleteRemote in ir-device-list.ts). This dialog
 *     implements neither itself; it dispatches request-duplicate /
 *     request-delete (composed, bubbling straight up since this
 *     component -- unlike ir-device-settings-dialog.ts -- is
 *     instantiated directly in ir-device-list.ts's own template, no
 *     intermediate host to pass through) and lets ir-device-list.ts's
 *     already-tested dialogs and confirm flow do the actual work --
 *     the same "one flow, two doors" pattern s10's callout calls for.
 *   - Close, quiet/grey, same anatomy as the Device dialog.
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { TriggerRemoteInfo } from "./types.js";

@customElement("ir-trigger-remote-settings-dialog")
export class IrTriggerRemoteSettingsDialog extends LitElement {
    @property({ attribute: false }) public remote!: TriggerRemoteInfo;

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

    /** "Make a Device" mirror-door mint (signpost 3, Track 3.5,
     *  owner-directed 2026-08-15). Same ask-and-get-out-of-the-way
     *  shape as _requestDuplicate/_requestDelete above -- this dialog
     *  does not mint anything itself, ir-device-list.ts's
     *  <ir-promote-dialog> (sourceRemoteId mode) does. */
    private _requestMakeDevice(): void {
        this.dispatchEvent(
            new CustomEvent("request-make-device", { bubbles: true, composed: true }),
        );
        this._close();
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${t("devsettings.remote_title")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <section class="settings-section section-convert">
                    <div class="convert-row">
                        <div class="convert-text">
                            <h3 class="section-label convert-label">
                                ${t("devsettings.make_device_title")}
                            </h3>
                            <p class="section-explainer convert-desc">
                                ${t("devsettings.make_device_desc")}
                            </p>
                        </div>
                        <div class="convert-btn-cell">
                            <button
                                class="action-btn convert-btn"
                                @click=${this._requestMakeDevice}
                            >
                                ${t("devsettings.make_device_btn")}
                            </button>
                        </div>
                    </div>
                </section>
                <div class="dialog-actions">
                    <button
                        class="action-btn delete-btn"
                        @click=${this._requestDelete}
                    >
                        ${t("devsettings.delete")}
                    </button>
                    <span class="actions-spacer"></span>
                    <button
                        class="action-btn duplicate-btn"
                        @click=${this._requestDuplicate}
                    >
                        ${t("devsettings.duplicate")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            .settings-section {
                margin: 16px 0;
            }
            .section-label {
                margin: 0 0 4px;
                font-size: 0.95rem;
                font-weight: 500;
            }
            .convert-label {
                color: var(--primary-color);
            }
            .section-explainer {
                margin: 0;
                padding-left: 8px;
                font-size: 0.8rem;
                color: var(--secondary-text-color);
            }
            .convert-row {
                display: flex;
                align-items: center;
                gap: 14px;
            }
            .convert-text {
                flex: 1;
            }
            .convert-btn-cell {
                flex: 0 0 116px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .convert-btn {
                width: 100%;
            }
            /* The same footer as the Device settings dialog (punch
             * list item 20), so the two popups read as one family:
             * Delete alone on the left, the constructive side on the
             * right, the grey Close gone. This dialog has no Save
             * (see the file header -- a Remote has nothing to save
             * through here), so the right side is Duplicate by
             * itself; the shape is the rule, not the button count.
             * The spacer does the work, so no justify-content
             * override is needed. */
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
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-trigger-remote-settings-dialog": IrTriggerRemoteSettingsDialog;
    }
}
