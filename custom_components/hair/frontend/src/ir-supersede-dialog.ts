/**
 * The supersede dialog (v0.9.7 "Second Fitting").
 *
 * Fires wherever a successor meets its ancestor: from the drop bar
 * (ir-wigs, an arriving Wig whose ancestry matches a local one) and from
 * Save as new (ir-save-wig-dialog, the self-supersession case). Both hand
 * it the same server-computed block, so this one component draws both
 * doorways.
 *
 * Two states off one block:
 *  - friendly (lost_digests empty): every row of the local copy carries
 *    forward, so the dialog reads as an invitation.
 *  - guarded (lost_digests non-empty): the local copy has a row the
 *    successor lacks; an amber callout names it. REPLACE stays the primary
 *    (owner ruling: unfilled rather than demoted out of the slot), because
 *    the guard informs, it does not block.
 *
 * It owns no network: REPLACE and KEEP BOTH are events the host acts on,
 * so the same dialog serves a host that uploaded and a host that saved.
 */
import { LitElement, css, html } from "lit";
import { customElement, property, state } from "./decorators.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import { t, tp } from "./localize.js";
import type { SupersessionBlock } from "./types.js";

@customElement("ir-supersede-dialog")
export class IrSupersedeDialog extends LitElement {
    @property({ attribute: false }) public block!: SupersessionBlock;
    @property() public newFilename = "";
    /** Self-supersession (opened from Save as new). The refit note falls
     * away: they just attested the successor, so there is nothing to warn
     * them off. */
    @property({ type: Boolean }) public self = false;

    /** Per-device top-up choices, on by default. */
    @state() private _topup = new Set<string>();
    @state() private _busy = false;
    private _seeded = false;

    private get _guarded(): boolean {
        return (this.block?.lost_digests?.length ?? 0) > 0;
    }

    updated(): void {
        if (!this._seeded && this.block) {
            this._seeded = true;
            this._topup = new Set(this.block.devices.map((d) => d.id));
        }
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _keepBoth(): void {
        this.dispatchEvent(
            new CustomEvent("keep-both", { bubbles: true, composed: true }),
        );
    }

    private _replace(): void {
        if (this._busy) return;
        // Disabled until the host's supersede call returns; the host is
        // the one that re-verifies the pair, so REPLACE waits on it.
        this._busy = true;
        this.dispatchEvent(
            new CustomEvent("replace", {
                detail: {
                    newFilename: this.newFilename,
                    oldFilename: this.block.old_filename,
                    relink: true,
                    topupDeviceIds: [...this._topup],
                },
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _toggleTopup(id: string): void {
        const next = new Set(this._topup);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        this._topup = next;
    }

    render() {
        const b = this.block;
        if (!b) return html``;
        const carried = b.old_signals - b.lost_digests.length;
        const firstDevice = b.devices[0]?.name ?? "";
        return html`
            <div class="overlay" @click=${this._close}>
                <div
                    class="dialog"
                    @click=${(e: Event) => e.stopPropagation()}
                >
                    <h3 class="heading">${t("supersede.title")}</h3>
                    <p class="body">
                        ${t("supersede.body", {
                            new: String(b.new_signals),
                            old: String(b.old_signals),
                            name: b.old_name,
                        })}
                    </p>
                    ${this._guarded
                        ? html`<div class="lost-callout">
                              ${tp("supersede.lost", b.lost_digests.length, {
                                  count: String(b.lost_digests.length),
                                  names: b.lost_aliases.join(", "),
                              })}
                          </div>`
                        : html`<p class="carried">
                              ${t("supersede.carried_all", {
                                  count: String(carried),
                              })}
                          </p>`}
                    ${b.devices.length
                        ? html`<p class="follows">
                              ${tp(
                                  "supersede.device_follows",
                                  b.devices.length,
                                  {
                                      count: String(b.devices.length),
                                      name: firstDevice,
                                  },
                              )}
                          </p>`
                        : ""}
                    ${this.self
                        ? ""
                        : html`<p class="refit-note">
                              ${t("supersede.refit_note")}
                          </p>`}
                    ${b.devices.map(
                        (d) => html`
                            <label class="topup-row">
                                <input
                                    type="checkbox"
                                    .checked=${this._topup.has(d.id)}
                                    @change=${() => this._toggleTopup(d.id)}
                                />
                                <span>
                                    ${tp("supersede.topup", d.missing_commands, {
                                        count: String(d.missing_commands),
                                        name: d.name,
                                    })}
                                </span>
                            </label>
                        `,
                    )}
                    ${this._guarded
                        ? html`<p class="reanchor">${t("supersede.title")}</p>`
                        : ""}
                    <div class="dialog-actions">
                        <button
                            class="action-btn cancel-btn"
                            @click=${this._keepBoth}
                        >
                            ${t("supersede.keep_both")}
                        </button>
                        <button
                            class="action-btn wide replace ${this._guarded
                                ? "guarded"
                                : ""}"
                            ?disabled=${this._busy}
                            @click=${this._replace}
                        >
                            ${t("supersede.replace")}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            .body {
                margin: 0 0 6px;
                font-size: 0.95rem;
                line-height: 1.55;
                color: var(--primary-text-color);
            }
            .carried {
                margin: 0 0 6px;
                font-size: 0.9rem;
                color: var(--secondary-text-color);
            }
            .follows {
                margin: 8px 0 0;
                font-size: 0.9rem;
                line-height: 1.5;
                color: var(--primary-text-color);
            }
            .refit-note {
                margin: 10px 0 0;
                font-size: 0.82rem;
                line-height: 1.5;
                color: var(--secondary-text-color);
            }
            /* Amber, and only here: the one place something is lost. */
            .lost-callout {
                margin: 12px 0;
                padding: 10px 12px;
                border-radius: 6px;
                border: 1px solid rgba(217, 164, 65, 0.45);
                background: rgba(217, 164, 65, 0.07);
                color: var(--primary-text-color);
                font-size: 0.85rem;
                line-height: 1.5;
            }
            .topup-row {
                display: flex;
                align-items: flex-start;
                gap: 9px;
                margin-top: 10px;
                font-size: 0.9rem;
                line-height: 1.45;
                color: var(--primary-text-color);
                cursor: pointer;
            }
            .topup-row input {
                margin-top: 2px;
                accent-color: #43a047;
                width: 15px;
                height: 15px;
                cursor: pointer;
            }
            .reanchor {
                margin: 14px 0 0;
                font-size: 0.82rem;
                color: var(--secondary-text-color);
            }
            .cancel-btn {
                border: 1px solid var(--divider-color);
            }
            /* REPLACE: house green, the confirm-forward primary. Filled in
               the friendly state; unfilled in the guarded one -- same hue,
               less weight -- because the warning already lives in the amber
               callout and the button need not repeat it (owner ruling). */
            .replace {
                background: #43a047;
                color: #fff;
            }
            .replace:hover:not(:disabled) {
                opacity: 0.9;
            }
            .replace.guarded {
                background: none;
                color: #4f9e5a;
                border: 1px solid rgba(79, 158, 90, 0.55);
            }
            .replace.guarded:hover:not(:disabled) {
                background: rgba(79, 158, 90, 0.12);
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-supersede-dialog": IrSupersedeDialog;
    }
}
