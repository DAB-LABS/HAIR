/**
 * The comb report (Smart Perm phase 2, mockup LR1 as ruled 2026-07-31).
 *
 * Findings grouped by severity, worst class first, each group truncated to
 * a few rows with a Show all so a wig with one finding and a wig with nine
 * hundred open to the same height. Keys are rendered in the cell grammar
 * the fitting dialog uses, never the ledger's compact form.
 *
 * The footer line is load bearing rather than decoration: combing and
 * fitting are orthogonal, and "it passed a fitting" will otherwise be read
 * as "the codes are all good". The findings measured that -- the dimension
 * checklist caught one defective cell in 74.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { CombFinding, CombReport, WigInfo } from "./types.js";

export const COMB_PATH = "M367.808,240.512c-37.163-31.232-58.475-60.565-58.475-80.512c0-23.019,5.568-37.077,10.944-50.667 c5.099-12.885,10.389-26.24,10.389-45.333c0-43.669-23.723-64-74.667-64s-74.667,20.331-74.667,64 c0,19.093,5.291,32.448,10.389,45.355c5.376,13.589,10.944,27.648,10.944,50.667c0,19.925-21.312,49.259-58.475,80.512 c-17.067,14.357-26.859,35.264-26.859,57.344v203.456c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667 v-160H160v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160 c0,5.888,4.779,10.667,10.667,10.667S224,507.221,224,501.333v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667 s10.667-4.779,10.667-10.667v-160H288v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160 c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667 c5.888,0,10.667-4.779,10.667-10.667V297.856C394.667,275.776,384.875,254.891,367.808,240.512z M373.333,320H138.667v-22.123 c0-15.765,7.019-30.741,19.264-41.024C188.075,231.509,224,194.133,224,160c0-27.093-6.613-43.797-12.437-58.517 c-4.779-12.075-8.896-22.464-8.896-37.483c0-27.669,8.491-42.667,53.333-42.667S309.333,36.331,309.333,64 c0,15.019-4.117,25.408-8.896,37.483C294.613,116.203,288,132.885,288,160c0,34.133,35.925,71.509,66.069,96.853 c12.245,10.304,19.264,25.259,19.264,41.024V320z";

/** Worst first. Mirrors SEVERITY_ORDER in wig_comb.py; the backend already
 * sorts, and this is what groups them for display. */
const SEVERITY_ORDER = [
    "duplicated-neighbour",
    "malformed",
    "frame-shape",
    "missing-cell",
    "coordinate-collision",
    "stray-cell",
    "stray-burst",
    "duplicate-labels",
];

/** Rows shown per group before Show all. Enough to see the shape of the
 * problem without a 34-row wall. */
const PREVIEW_ROWS = 3;

@customElement("ir-comb-report")
export class IrCombReport extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public wig!: WigInfo;

    @state() private _report: CombReport | null = null;
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _expanded = new Set<string>();

    connectedCallback(): void {
        super.connectedCallback();
        void this._comb();
    }

    /** Always combs on open. The stored receipt may predate a Replace, and
     * a report that describes codes which no longer exist is worse than no
     * report at all. */
    private async _comb(): Promise<void> {
        this._busy = true;
        this._error = null;
        try {
            this._report = await this.api.wigsComb(this.wig.filename);
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
        this._busy = false;
        this.dispatchEvent(
            new CustomEvent("combed", { bubbles: true, composed: true }),
        );
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _grouped(): [string, CombFinding[]][] {
        const groups = new Map<string, CombFinding[]>();
        for (const f of this._report?.findings ?? []) {
            const list = groups.get(f.check);
            if (list) list.push(f);
            else groups.set(f.check, [f]);
        }
        return SEVERITY_ORDER.filter((c) => groups.has(c)).map(
            (c) => [c, groups.get(c)!] as [string, CombFinding[]],
        );
    }

    /** A finding's diagnosis, rendered from its localization key and
     * params. The backend never ships prebaked English. */
    private _diagnosis(f: CombFinding): string {
        return t(f.message, f.params ?? {});
    }

    render() {
        return html`
            <div class="overlay" @click=${this._close}>
                <div
                    class="dialog comb-dialog"
                    @click=${(e: Event) => e.stopPropagation()}
                >
                    <h3 class="heading">
                        ${t("comb.heading", { name: this.wig.name })}
                        <svg
                            class="combmark"
                            viewBox="0 0 512 512"
                            width="18"
                            height="18"
                            aria-hidden="true"
                        >
                            <path d=${COMB_PATH}></path>
                        </svg>
                    </h3>
                    ${this._renderBody()}
                    <div class="foot-note">${t("comb.footer")}</div>
                    <div class="dialog-actions comb-actions">
                        <button
                            class="action-btn again-btn"
                            ?disabled=${this._busy}
                            @click=${() => void this._comb()}
                        >
                            ${this._busy
                                ? t("comb.combing")
                                : t("comb.again")}
                        </button>
                        <span class="spacer"></span>
                        <button
                            class="action-btn cancel-btn"
                            @click=${this._close}
                        >
                            ${t("common.close")}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    private _renderBody() {
        if (this._error)
            return html`<div class="err">${this._error}</div>`;
        if (!this._report)
            return html`<div class="loading">
                ${t("common.loading_plain")}
            </div>`;
        const groups = this._grouped();
        return html`
            <div class="receipt">
                ${this._report.suspects > 0
                    ? html`<b
                          >${tp(
                              "comb.suspects",
                              this._report.suspects,
                          )}</b
                      > &middot; `
                    : nothing}
                ${t("comb.combed_on", { date: this._report.date ?? "" })}
            </div>
            ${groups.length === 0
                ? html`<div class="clean">
                      <span class="tick">&check;</span>
                      <span>${t("comb.clean")}</span>
                  </div>`
                : groups.map((g) => this._renderGroup(g[0], g[1]))}
            ${this._report.truncated
                ? html`<div class="more">
                      ${t("comb.truncated", {
                          count: String(this._report.truncated),
                      })}
                  </div>`
                : nothing}
        `;
    }

    private _renderGroup(check: string, findings: CombFinding[]) {
        const open = this._expanded.has(check);
        const shown = open ? findings : findings.slice(0, PREVIEW_ROWS);
        return html`
            <div class="grp sev-${check}">
                <div class="ghead">
                    <span class="glyph"
                        >${check === "duplicated-neighbour" ||
                        check === "stray-burst" ||
                        check === "stray-cell" ||
                        check === "duplicate-labels"
                            ? "\u25CF"
                            : "\u26A0"}</span
                    >
                    <span class="gname">${t(`comb.class.${check}`)}</span>
                    <span class="gcount">${findings.length}</span>
                    <span class="gwhat">${t(`comb.what.${check}`)}</span>
                </div>
                <div class="glist">
                    ${shown.map(
                        (f) => html`<div class="find">
                            <span class="key">${f.keys.join(" \u00b7 ")}</span>
                            <span class="diag">${this._diagnosis(f)}</span>
                        </div>`,
                    )}
                    ${findings.length > shown.length
                        ? html`<div class="more">
                              ${t("comb.showing", {
                                  shown: String(shown.length),
                                  total: String(findings.length),
                              })}
                              <button
                                  @click=${() => {
                                      const next = new Set(this._expanded);
                                      next.add(check);
                                      this._expanded = next;
                                  }}
                              >
                                  ${t("comb.show_all")}
                              </button>
                          </div>`
                        : nothing}
                </div>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            .comb-dialog {
                max-width: 620px;
            }
            .heading {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .combmark {
                fill: #64b5f6;
                flex: none;
            }
            .receipt {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                margin: -8px 0 14px;
            }
            .receipt b {
                color: var(--primary-text-color);
                font-weight: 500;
            }
            .grp {
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                margin-bottom: 10px;
            }
            .ghead {
                display: flex;
                align-items: baseline;
                gap: 9px;
                padding: 10px 12px;
            }
            .ghead .glyph {
                font-size: 12px;
                width: 14px;
                text-align: center;
                color: var(--secondary-text-color);
            }
            /* Red for the class the device answers while setting the wrong
               state; amber for everything the device simply ignores. */
            .sev-duplicated-neighbour .glyph {
                color: #ff5252;
            }
            .sev-malformed .glyph,
            .sev-frame-shape .glyph,
            .sev-missing-cell .glyph,
            .sev-coordinate-collision .glyph {
                color: #ffc107;
            }
            .ghead .gname {
                font-size: 12px;
                font-weight: 600;
            }
            .ghead .gcount {
                font-size: 11px;
                color: var(--secondary-text-color);
                font-variant-numeric: tabular-nums;
            }
            .ghead .gwhat {
                flex: 1;
                font-size: 11.5px;
                color: var(--secondary-text-color);
                text-align: right;
                opacity: 0.8;
            }
            .glist {
                border-top: 1px solid var(--divider-color);
                padding: 4px 0;
                max-height: 260px;
                overflow-y: auto;
            }
            .find {
                display: flex;
                gap: 12px;
                align-items: baseline;
                padding: 6px 12px 6px 26px;
                font-size: 12px;
                line-height: 1.5;
            }
            .find .key {
                font-family: ui-monospace, "SF Mono", Menlo, monospace;
                font-size: 11px;
                min-width: 140px;
                word-break: break-word;
            }
            .find .diag {
                color: var(--secondary-text-color);
            }
            .more {
                padding: 7px 12px 9px 26px;
                font-size: 11.5px;
                color: var(--secondary-text-color);
            }
            .more button {
                background: none;
                border: none;
                padding: 0;
                font: inherit;
                color: #64b5f6;
                cursor: pointer;
                text-decoration: underline dotted;
                text-underline-offset: 3px;
            }
            .clean {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 14px 4px;
                font-size: 13px;
                color: var(--secondary-text-color);
            }
            .clean .tick {
                color: #66bb6a;
                font-size: 16px;
            }
            .foot-note {
                margin-top: 14px;
                padding: 9px 12px;
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid var(--divider-color);
                font-size: 11.5px;
                color: var(--secondary-text-color);
                line-height: 1.5;
            }
            .comb-actions {
                margin-top: 14px;
            }
            .spacer {
                flex: 1;
            }
            .again-btn {
                color: #64b5f6;
                border-color: rgba(100, 181, 246, 0.35);
            }
            .err {
                font-size: 12px;
                color: var(--error-color, #c62828);
                margin-bottom: 8px;
            }
            .loading {
                padding: 16px;
                font-size: 12.5px;
                color: var(--secondary-text-color);
            }
        `,
    ];
}
