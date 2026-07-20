/**
 * Pluck Signal dialog.
 *
 * Two-state flow:
 *   1. The user types the command name they gave the code in the vendor app
 *      and clicks Pluck. HAIR fires the vendor send service at the HAIR
 *      Tweezer and captures the resulting code(s).
 *   2. On success the captured Pronto preview(s) render with an alias field;
 *      Create persists each onto the plucked blaster. A multi-code pluck
 *      shows all captures stacked, each removable.
 *
 * Inline errors (vendor_error / no_response / unknown) render under the Pluck
 * button. No IR is broadcast: the Tweezer absorbs the command.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type {
    PluckedSignalPreview,
    ProntoValidation,
    UnknownDevice,
} from "./types.js";

// mdi:check
const ICON_CHECK = "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z";
// mdi:alert-circle-outline
const ICON_ALERT =
    "M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z";

@customElement("ir-pluck-signal-dialog")
export class IrPluckSignalDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public blaster!: UnknownDevice;
    @property() public integration = "";

    @state() private _commandName = "";
    @state() private _busy = false;
    @state() private _creating = false;
    @state() private _error: string | null = null;
    @state() private _captures: PluckedSignalPreview[] | null = null;
    @state() private _aliases: string[] = [];
    @state() private _validations: (ProntoValidation | null)[] = [];

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _pluck(): Promise<void> {
        const command = this._commandName.trim();
        if (!command) {
            this._error = t("assign.command_required");
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const result = await this.api.runPluck({
                integration: this.integration,
                vendor_entity_id: this.blaster.vendor_entity_id ?? "",
                appliance: this.blaster.appliance ?? "",
                command_name: command,
            });
            if (result.error) {
                this._error = result.message ?? t("pluckdlg.pluck_failed");
            } else if (result.signals && result.signals.length > 0) {
                this._captures = result.signals;
                this._aliases = result.signals.map((s) => s.suggested_alias);
                this._validations = await Promise.all(
                    result.signals.map((s) =>
                        this.api.validatePronto(s.code ?? "").catch(() => null),
                    ),
                );
            } else {
                this._error = t("pluckdlg.no_response");
            }
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    private _removeCapture(i: number): void {
        if (!this._captures) return;
        this._captures = this._captures.filter((_, idx) => idx !== i);
        this._aliases = this._aliases.filter((_, idx) => idx !== i);
        this._validations = this._validations.filter((_, idx) => idx !== i);
        if (this._captures.length === 0) {
            // Nothing kept -- go back to the command-name state.
            this._captures = null;
        }
    }

    private async _create(): Promise<void> {
        if (!this._captures || this._captures.length === 0) return;
        this._creating = true;
        this._error = null;
        try {
            const created = [];
            for (let i = 0; i < this._captures.length; i++) {
                const cap = this._captures[i];
                const sig = await this.api.createPluckedSignal({
                    device_id: this.blaster.id,
                    pronto: cap.code ?? "",
                    command_name: cap.plucked_command_name,
                    alias: this._aliases[i].trim(),
                });
                created.push(sig);
            }
            this.dispatchEvent(
                new CustomEvent("signals-created", {
                    detail: created,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._creating = false;
        }
    }

    private _renderValid(cap: PluckedSignalPreview, i: number) {
        const v = this._validations[i] ?? null;
        const recognized = v?.recognized_protocol ?? cap.decoded_protocol ?? null;
        const khz =
            v?.frequency_khz != null
                ? v.frequency_khz.toFixed(1)
                : (cap.frequency / 1000).toFixed(1);
        const pairs = v?.burst_pair_count ?? null;
        return html`
            <div class="valid-box">
                <div class="valid-head">
                    <ha-svg-icon .path=${ICON_CHECK}></ha-svg-icon>
                    ${recognized
                        ? t("pluckdlg.recognized_as", { protocol: recognized })
                        : t("pluckdlg.valid_pronto")}
                </div>
                <div class="valid-sub">
                    ${khz} kHz${pairs != null ? ` · ${pairs} burst pairs` : ""}
                </div>
            </div>
        `;
    }

    private _renderError() {
        if (!this._error) return "";
        return html`
            <div class="pluck-error">
                <ha-svg-icon .path=${ICON_ALERT}></ha-svg-icon>
                <span>${this._error}</span>
            </div>
        `;
    }

    private _renderCommandState() {
        return html`
            <div class="field">
                <label>${t("assign.command_name")}</label>
                <input
                    type="text"
                    .value=${this._commandName}
                    placeholder=${t("pluckdlg.command_placeholder")}
                    autofocus
                    @input=${(e: Event) =>
                        (this._commandName = (e.target as HTMLInputElement).value)}
                    @keydown=${(e: KeyboardEvent) => {
                        if (e.key === "Enter") void this._pluck();
                    }}
                />
                <div class="help">
                    ${t("pluckdlg.command_help")}
                </div>
            </div>
            ${this._renderError()}
            <div class="dialog-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    ${t("common.cancel")}
                </button>
                <button
                    class="action-btn pluck-btn"
                    @click=${this._pluck}
                    ?disabled=${this._busy}
                >
                    ${this._busy ? t("pluckdlg.plucking") : t("pluckdlg.pluck")}
                </button>
            </div>
        `;
    }

    private _renderCaptures(captures: PluckedSignalPreview[]) {
        const multi = captures.length > 1;
        return html`
            ${this._renderError()}
            <div class="captured-label">
                ${t("pluckdlg.captured")} ${multi ? `(${captures.length})` : ""}
            </div>
            ${captures.map(
                (cap, i) => html`
                    <div class="capture">
                        ${multi
                            ? html`<button
                                  class="remove-btn"
                                  title=${t("pluckdlg.remove_capture")}
                                  @click=${() => this._removeCapture(i)}
                              >
                                  &times;
                              </button>`
                            : ""}
                        <div class="pronto">${cap.code}</div>
                        ${this._renderValid(cap, i)}
                        <div class="field">
                            <label>${t("pluckdlg.alias")}</label>
                            <input
                                type="text"
                                .value=${this._aliases[i] ?? ""}
                                @input=${(e: Event) => {
                                    const v = (e.target as HTMLInputElement).value;
                                    const next = [...this._aliases];
                                    next[i] = v;
                                    this._aliases = next;
                                }}
                            />
                        </div>
                    </div>
                `,
            )}
            <div class="dialog-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._creating}
                >
                    ${t("common.cancel")}
                </button>
                <button
                    class="action-btn create-btn"
                    @click=${this._create}
                    ?disabled=${this._creating}
                >
                    ${this._creating ? t("common.saving") : t("common.create")}
                </button>
            </div>
        `;
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${t("pluckdlg.signal_heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._captures
                    ? this._renderCaptures(this._captures)
                    : this._renderCommandState()}
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
        .help {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        /* Tab-accent focus, overriding the shared primary-blue. */
        input[type="text"]:focus {
            outline: none;
            border-color: #455a64;
        }
        .pluck-error {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 12px 0;
            padding: 8px 12px;
            border-radius: 6px;
            background: rgba(255, 152, 0, 0.1);
            border-left: 3px solid var(--warning-color, #ff9800);
            color: var(--primary-text-color);
            font-size: 0.85rem;
            line-height: 1.3;
        }
        .pluck-error ha-svg-icon {
            --mdc-icon-size: 18px;
            color: var(--warning-color, #ff9800);
            flex-shrink: 0;
        }
        .captured-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--secondary-text-color);
            margin: 12px 0 6px;
        }
        .capture {
            position: relative;
            margin-bottom: 12px;
        }
        .capture + .capture {
            border-top: 1px solid var(--divider-color);
            padding-top: 12px;
        }
        .remove-btn {
            position: absolute;
            top: 6px;
            right: 6px;
            border: none;
            background: none;
            color: var(--secondary-text-color);
            font-size: 1.1rem;
            line-height: 1;
            cursor: pointer;
            padding: 2px 6px;
        }
        .remove-btn:hover {
            color: var(--error-color, #c62828);
        }
        .pronto {
            font-family: var(--code-font-family, monospace);
            font-size: 0.72rem;
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 8px;
            max-height: 96px;
            overflow: auto;
            word-break: break-all;
        }
        .valid-box {
            margin-top: 8px;
            background: var(--secondary-background-color);
            border-radius: 6px;
            padding: 8px 10px;
        }
        .valid-head {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            color: #2e7d32;
        }
        .valid-head ha-svg-icon {
            --mdc-icon-size: 16px;
        }
        .valid-sub {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        .pluck-btn,
        .create-btn {
            background: #455a64;
            color: #fff;
            border-color: #455a64;
        }
        .pluck-btn:hover:not(:disabled),
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-pluck-signal-dialog": IrPluckSignalDialog;
    }
}
