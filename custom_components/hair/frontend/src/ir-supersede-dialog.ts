/**
 * The supersede dialog (v0.9.7 "Second Fitting", amended).
 *
 * Fires at the drop bar (ir-wigs, an arriving Wig whose ancestry matches
 * a local one) -- its sole caller since Second Fitting v3 Commit 5
 * retired the self-supersession confirm Save as new used to open: a
 * diverged, sourced Perfect Fit save now mints its successor and
 * retires the ancestor in the same write (replace: true), so there is
 * no second decision dialog left to open there. Commit 6 removed the
 * self/viewerHandle scaffolding that caller needed; this component now
 * describes the drop bar only.
 *
 * Two states off one block:
 *  - friendly (lost_digests empty): every row of the local copy carries
 *    forward, so the dialog reads as an invitation.
 *  - guarded (lost_digests non-empty): the local copy has a row the
 *    successor lacks; an amber callout names it. REPLACE stays the primary
 *    (owner ruling: unfilled rather than demoted out of the slot), because
 *    the guard informs, it does not block.
 *
 * Amendment v2 section 2 adds the graded ceremony (the ancestor's own
 * fitting history, credited and graded before anything is replaced) and
 * a third action, CANCEL: it undoes the import outright, deleting the
 * file that just arrived.
 *
 * It owns no network: REPLACE, KEEP BOTH and CANCEL are events the host
 * acts on.
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

    /** Per-device top-up choices, on by default. */
    @state() private _topup = new Set<string>();
    @state() private _busy = false;
    private _seeded = false;

    private get _guarded(): boolean {
        return (this.block?.lost_digests?.length ?? 0) > 0;
    }

    /** The graded ceremony line, or null when there is nothing to grade
     * (amendment v2 section 2: "no claims" is the light state -- the
     * body stands on its own): an anonymous fitting with no handle at
     * all leaves nobody to credit. */
    private get _fitted(): {
        state: "perfect" | "scoped";
        count: number;
        who: string[];
    } | null {
        const of = this.block?.old_fittings;
        if (!of || !of.state) return null;
        const who = of.handles;
        if (!who.length) return null;
        return { state: of.state, count: of.count, who };
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

    /** Owner ruling: "Cancel means undo this import" -- the host deletes
     * the file that just arrived and receipts it. */
    private _cancel(): void {
        if (this._busy) return;
        this._busy = true;
        this.dispatchEvent(
            new CustomEvent("cancel-import", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** Names, not counts (amendment v2 section 2): "Timer and Breeze
     * Mode", truncating past four so a device missing a dozen commands
     * does not turn the confirm into a wall of text. */
    private _formatNames(names: string[]): string {
        const MAX = 4;
        if (names.length <= 1) return names[0] ?? "";
        const and = t("supersede.list_and");
        if (names.length <= MAX) {
            return `${names.slice(0, -1).join(", ")} ${and} ${
                names[names.length - 1]
            }`;
        }
        const more = names.length - MAX;
        return `${names.slice(0, MAX).join(", ")} ${and} ${tp(
            "supersede.topup_more",
            more,
            { count: String(more) },
        )}`;
    }

    render() {
        const b = this.block;
        if (!b) return html``;
        const carried = b.old_signals - b.lost_digests.length;
        const firstDevice = b.devices[0]?.name ?? "";
        const fitted = this._fitted;
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
                    ${fitted
                        ? fitted.state === "perfect"
                            ? html`<div class="fitted-callout">
                                  ${t("supersede.fitted_perfect", {
                                      name: b.old_name,
                                      who: fitted.who.join(", "),
                                  })}
                              </div>`
                            : html`<p class="fitted-line">
                                  ${tp(
                                      "supersede.fitted_scoped",
                                      fitted.count,
                                      {
                                          count: String(fitted.count),
                                          name: b.old_name,
                                          who: fitted.who.join(", "),
                                      },
                                  )}
                              </p>`
                        : ""}
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
                    <p class="refit-note">${t("supersede.refit_note")}</p>
                    ${b.devices.map(
                        (d) => html`
                            <label class="topup-row">
                                <input
                                    type="checkbox"
                                    .checked=${this._topup.has(d.id)}
                                    @change=${() => this._toggleTopup(d.id)}
                                />
                                <span>
                                    ${d.missing_aliases.length
                                        ? t("supersede.topup_names", {
                                              names: this._formatNames(
                                                  d.missing_aliases,
                                              ),
                                              name: d.name,
                                          })
                                        : t("supersede.topup_none", {
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
                            ?disabled=${this._busy}
                            @click=${this._cancel}
                        >
                            ${t("common.cancel")}
                        </button>
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
            /* Amber: the register for "something proven is going away".
               The guarded state's lost row wears it here; the graded
               ceremony's PERFECT FIT retirement wears the same family
               below (.fitted-callout), because losing a row and
               retiring a signed perfect fit are the same weight of
               news. */
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
            /* A scoped fitting is informational, the same weight as
               .follows -- somebody tried, nobody finished, so there is
               nothing heavy to warn about. */
            .fitted-line {
                margin: 8px 0 0;
                font-size: 0.9rem;
                line-height: 1.5;
                color: var(--primary-text-color);
            }
            /* A PERFECT FIT retiring gets the amber-family treatment
               .lost-callout wears, for the reason noted above it. */
            .fitted-callout {
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
