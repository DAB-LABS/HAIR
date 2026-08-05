/**
 * The decision window (Second Fitting v3, "the Add to Closet fork").
 *
 * v2 ruled "the user never picks a verb": SAVE TO CLOSET derived
 * UPDATE or SUCCESSION silently and asked the replace question AFTER
 * the save, in a confirm that arrived late (and, before the bench
 * addendum's lifecycle fix, could die young). The owner's bench walk
 * showed why that fails -- the decision moves to the FRONT instead.
 * SAVE TO CLOSET now opens this small window first, always, where the
 * person declares intent one of three ways:
 *
 * - SAVE AS NEW -- a new wig file; the existing wig untouched.
 * - UPDATE CLOSET WIG -- bring the existing wig up to match the
 *   device. Offered only when the device HAS a source wig (owner:
 *   "if somebody created a device that doesn't have a wig, there is
 *   nothing to update").
 * - VALIDATE FOR PERFECT FIT -- the ceremony: prove every code and
 *   sign it.
 *
 * Each route opens its OWN dialog (owner: "each of those dialogs is
 * their own" -- no morphing between them, unlike v2's single dialog
 * that silently became one verb or another). This component owns
 * none of them; it only reads the plan the host already fetched and
 * fires a `route` event naming the choice, so the host decides what
 * opens next and never refetches the plan to do it.
 *
 * The source line and delta summary read straight off the save plan's
 * own digest comparison -- the same derivation that has always decided
 * CREATE / UPDATE / SUCCESSION server-side. This absorbs the bench
 * addendum's ruling that no doorway to a succession is ever silent:
 * the summary line IS the warning, and it costs one line, up front,
 * before any route is even chosen.
 */
import { LitElement, css, html } from "lit";
import { customElement, property } from "./decorators.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import { t, tp } from "./localize.js";
import type { SavePlan } from "./types.js";

export type SaveRoute = "new" | "update" | "perfect";

@customElement("ir-save-route-dialog")
export class IrSaveRouteDialog extends LitElement {
    /** Already fetched by the host (hair/wigs/save_plan) before this
     * dialog opens -- the whole point of routing through here is that
     * the dialog the person lands on next never refetches it. */
    @property({ attribute: false }) public plan!: SavePlan;

    private get _hasSource(): boolean {
        return !!this.plan?.source_wig_id;
    }

    private get _sourceLine(): string {
        return this._hasSource
            ? t("wigs.route.source_from", {
                  name: this.plan.source_wig_name ?? "",
              })
            : t("wigs.route.source_none");
    }

    /** The one-line delta summary, or null when there is no source to
     * compare against (a from-scratch device has nothing to diverge
     * from). Diverged content names what changed rather than just
     * warning that it did -- the same rows the plan already carries
     * for the checklist below, counted here instead of listed. */
    private get _summaryLine(): string | null {
        if (!this._hasSource) return null;
        if (this.plan.variant !== "succession") {
            return t("wigs.route.summary_matches");
        }
        const added = this.plan.rows.filter((r) => !r.matched).length;
        const removed = this.plan.missing_rows.length;
        const parts: string[] = [];
        if (added) {
            parts.push(
                tp("wigs.route.added", added, { count: String(added) }),
            );
        }
        if (removed) {
            parts.push(
                tp("wigs.route.removed", removed, { count: String(removed) }),
            );
        }
        return t("wigs.route.summary_diverged", { parts: parts.join(", ") });
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _choose(route: SaveRoute): void {
        this.dispatchEvent(
            new CustomEvent("route", {
                detail: { route },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        if (!this.plan) return html``;
        const summary = this._summaryLine;
        return html`
            <div class="overlay" @click=${this._close}>
                <div
                    class="dialog"
                    @click=${(e: Event) => e.stopPropagation()}
                >
                    <h3 class="heading">${t("wigs.export.heading")}</h3>
                    <p class="source-line">${this._sourceLine}</p>
                    ${summary
                        ? html`<p class="summary-line">${summary}</p>`
                        : ""}
                    <div class="route-list">
                        <button
                            class="route-btn"
                            @click=${() => this._choose("new")}
                        >
                            ${t("wigs.route.save_as_new")}
                        </button>
                        ${this._hasSource
                            ? html`<button
                                  class="route-btn"
                                  @click=${() => this._choose("update")}
                              >
                                  ${t("wigs.route.update_closet_wig")}
                              </button>`
                            : ""}
                        <button
                            class="route-btn"
                            @click=${() => this._choose("perfect")}
                        >
                            ${t("wigs.route.validate_perfect_fit")}
                        </button>
                    </div>
                    <div class="dialog-actions">
                        <button
                            class="action-btn cancel-btn"
                            @click=${this._close}
                        >
                            ${t("common.cancel")}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            .source-line {
                margin: 0 0 4px;
                font-size: 0.9rem;
                color: var(--primary-text-color);
            }
            .summary-line {
                margin: 0 0 16px;
                font-size: 0.85rem;
                color: var(--secondary-text-color);
            }
            .route-list {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .route-btn {
                background: none;
                border: 1px solid var(--divider-color);
                border-radius: 6px;
                padding: 12px 14px;
                font-size: 0.95rem;
                font-weight: 500;
                font-family: inherit;
                color: var(--primary-text-color);
                text-align: left;
                cursor: pointer;
                transition:
                    background 150ms ease,
                    border-color 150ms ease;
            }
            .route-btn:hover {
                border-color: #43a047;
                background: rgba(67, 160, 71, 0.06);
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-save-route-dialog": IrSaveRouteDialog;
    }
}
