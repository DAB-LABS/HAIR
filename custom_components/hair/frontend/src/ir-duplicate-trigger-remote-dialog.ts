/**
 * Dialog that clones a named trigger remote under a new name. Add
 * Popups signpost 2, Track 5.
 *
 * Unlike ir-duplicate-device-dialog.ts (which explicitly excludes
 * triggers -- see that file's own header), this ALSO copies every
 * trigger the source remote owns, including each one's on/off state
 * (owner ruling 2026-08-14). That is a deliberate divergence from the
 * device precedent: a trigger remote's triggers are its entire
 * content, so an empty duplicate would just be a second empty shell
 * (ir-add-trigger-remote-dialog.ts's Manual tab already covers that).
 * The trade-off it accepts: if the source remote is still receiving
 * real signals, both it and the copy fire until the user turns off or
 * deletes the triggers they do not want live -- ``duptr.hint_body``
 * says this plainly rather than leaving it a surprise.
 *
 * Dispatches:
 *   - ``remote-duplicated`` with detail ``{ remote: TriggerRemoteInfo }``
 *     on success
 *   - ``closed`` on Cancel or after the parent drives a close
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import "./ir-receiver-picker.js";
import type { HairApi } from "./api.js";
import type { TriggerRemoteInfo } from "./types.js";

@customElement("ir-duplicate-trigger-remote-dialog")
export class IrDuplicateTriggerRemoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;

    /** Id of the trigger remote being duplicated. */
    @property({ attribute: false }) public sourceId = "";

    /** Name of the source remote (for the hint text and default name). */
    @property({ attribute: false }) public sourceName = "";

    /** The source remote's own receiver_scope (Track 2 item 6): the
     *  footer picker's starting selection, overridable before Create.
     *  Stored semantics unchanged -- this is just what the picker
     *  shows lit on open. */
    @property({ attribute: false }) public sourceReceiverScope: string[] = [];

    @state() private _name = "";
    @state() private _receiverIds: string[] = [];
    @state() private _busy = false;
    @state() private _error: string | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        this._name = `${this.sourceName} (Copy)`;
        this._receiverIds = [...this.sourceReceiverScope];
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _duplicate(): Promise<void> {
        const name = this._name.trim();
        if (!name) {
            this._error = t("common.name_required");
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const created = await this.api.duplicateTriggerRemote(
                this.sourceId,
                name,
                this._receiverIds,
            );
            this.dispatchEvent(
                new CustomEvent<TriggerRemoteInfo>("remote-duplicated", {
                    detail: created,
                    bubbles: true,
                    composed: true,
                }),
            );
            this._close();
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private _onKeyDown(e: KeyboardEvent): void {
        if (e.key === "Enter") {
            e.preventDefault();
            void this._duplicate();
        }
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${t("duptr.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <p class="hint">
                    ${t("dup.hint_duplicating").split("{name}")[0]}<strong
                        >${this.sourceName}</strong
                    >${t("dup.hint_duplicating").split("{name}")[1] ?? ""}
                    ${t("duptr.hint_body")}
                </p>

                <div class="field">
                    <label>${t("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        autofocus
                        required
                        @input=${(e: Event) =>
                            (this._name = (e.target as HTMLInputElement).value)}
                        @keydown=${this._onKeyDown}
                        @focus=${(e: Event) =>
                            (e.target as HTMLInputElement).select()}
                    />
                </div>

                <ir-receiver-picker
                    .api=${this.api}
                    .value=${this._receiverIds}
                    ?disabled=${this._busy}
                    @receivers-changed=${(e: CustomEvent) =>
                        (this._receiverIds = e.detail.value)}
                ></ir-receiver-picker>

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
                        @click=${this._duplicate}
                        ?disabled=${this._busy || !this._name.trim()}
                    >
                        ${this._busy ? t("dup.duplicating") : t("dup.duplicate")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
        .hint {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 8px 0 16px;
        }
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 4px;
        }
        .field input {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        .field input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        /* Slimmer actions row than the shared one; ships this way. */
        .dialog-actions {
            margin-top: 16px;
            padding-top: 0;
            border-top: none;
        }
        /* Opacity in the transition so the Duplicate hover fades, not snaps. */
        .action-btn {
            transition: background 150ms ease, opacity 150ms ease;
        }
        /* Brighter cancel than the shared secondary; ships this way. */
        .cancel-btn {
            color: var(--primary-text-color);
        }
        /* Gold, matching the Trigger Remotes section's own palette
           (ir-device-list.ts's .trigger-icon / .trigger-drawer-card.expanded)
           -- not the device green ir-duplicate-device-dialog.ts uses. */
        .create-btn {
            background: #d4a017;
            color: #fff;
            border-color: #d4a017;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-duplicate-trigger-remote-dialog": IrDuplicateTriggerRemoteDialog;
    }
}
