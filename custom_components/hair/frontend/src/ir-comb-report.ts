/**
 * The comb report: what is wrong, ordered by what it DOES to you.
 *
 * The first draft grouped by check class and gave every class an
 * identical card. That is the backend's ordering rendered faithfully,
 * and it made a wig with nine cosmetic artefacts look exactly as
 * alarming as one with a code that answers a press and sets the wrong
 * state. The severity ranking existed; it just was not visible in the
 * first two seconds, which is the only part most people read.
 *
 * So the report leads with CONSEQUENCE. Three buckets, worst present
 * first, and an empty bucket does not render at all -- a card reading
 * "0 will do the wrong thing" is reassurance wearing the costume of a
 * warning.
 *
 * The tally carries a DENOMINATOR. Forty-eight findings is
 * catastrophic on a seven-button remote and unremarkable on a 288-cell
 * lattice, and it is the same number either way.
 *
 * Inside a bucket, one row per check class, opening on a chevron into
 * the findings GROUPED BY DIAGNOSIS. Frame shape on the Samsung has
 * twenty-two findings and two facts in it: nineteen codes send one
 * burst pair too many, three send two too many. Printing the same
 * sentence nineteen times was never nineteen facts.
 *
 * The footer line is load bearing rather than decoration: combing and
 * fitting are orthogonal, and "it passed a fitting" will otherwise be
 * read as "the codes are all good". The findings measured that -- the
 * dimension checklist caught one defective cell in 74.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { CombFinding, CombReport, WigInfo } from "./types.js";

export const COMB_PATH = "M367.808,240.512c-37.163-31.232-58.475-60.565-58.475-80.512c0-23.019,5.568-37.077,10.944-50.667 c5.099-12.885,10.389-26.24,10.389-45.333c0-43.669-23.723-64-74.667-64s-74.667,20.331-74.667,64 c0,19.093,5.291,32.448,10.389,45.355c5.376,13.589,10.944,27.648,10.944,50.667c0,19.925-21.312,49.259-58.475,80.512 c-17.067,14.357-26.859,35.264-26.859,57.344v203.456c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667 v-160H160v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160 c0,5.888,4.779,10.667,10.667,10.667S224,507.221,224,501.333v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667 s10.667-4.779,10.667-10.667v-160H288v160c0,5.888,4.779,10.667,10.667,10.667s10.667-4.779,10.667-10.667v-160h21.333v160 c0,5.888,4.779,10.667,10.667,10.667c5.888,0,10.667-4.779,10.667-10.667v-160h21.333v160c0,5.888,4.779,10.667,10.667,10.667 c5.888,0,10.667-4.779,10.667-10.667V297.856C394.667,275.776,384.875,254.891,367.808,240.512z M373.333,320H138.667v-22.123 c0-15.765,7.019-30.741,19.264-41.024C188.075,231.509,224,194.133,224,160c0-27.093-6.613-43.797-12.437-58.517 c-4.779-12.075-8.896-22.464-8.896-37.483c0-27.669,8.491-42.667,53.333-42.667S309.333,36.331,309.333,64 c0,15.019-4.117,25.408-8.896,37.483C294.613,116.203,288,132.885,288,160c0,34.133,35.925,71.509,66.069,96.853 c12.245,10.304,19.264,25.259,19.264,41.024V320z";

/** Worst first. Mirrors SEVERITY_ORDER in wig_comb.py; the backend
 * already sorts, and this is what orders the classes INSIDE a bucket,
 * so that ordering is still doing work. */
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

/**
 * What each finding DOES to a device (ruled 2026-08-03).
 *
 * The comb has only ever committed to an ordering, which is a weaker
 * claim than this one. Two classes needed a call, and the shipped
 * display strings had already made it. coordinate-collision reads "one
 * state, two codes", so HAIR sends one and the other is unreachable: a
 * dead code, not a wrong action. duplicate-labels reads "often
 * legitimate; reported, never changed", so the product already
 * declines to act on it and cannot then call it dangerous.
 *
 * This lives here and not in wig_comb.py deliberately. It is a
 * judgment about phrasing, the backend already ships localization keys
 * rather than English, and moving it server-side would make a receipt
 * format change out of a display concern.
 */
const CONSEQUENCE: Record<string, string> = {
    "duplicated-neighbour": "wrong",
    malformed: "ignored",
    "frame-shape": "ignored",
    "missing-cell": "ignored",
    "coordinate-collision": "ignored",
    "stray-burst": "cosmetic",
    "stray-cell": "cosmetic",
    "duplicate-labels": "cosmetic",
};

/** Worst first, and an empty one is omitted rather than shown at zero. */
const BUCKETS = ["wrong", "ignored", "cosmetic"];

/** Coordinate chips shown per diagnosis before Show all. A lattice
 * fault can name ninety rows, and the point of the group heading is
 * that you do not have to read all of them to know what happened. */
const PREVIEW_KEYS = 12;

@customElement("ir-comb-report")
export class IrCombReport extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public wig!: WigInfo;

    @state() private _report: CombReport | null = null;
    @state() private _busy = false;
    @state() private _error: string | null = null;
    /** Which check classes are open. Several at once, deliberately:
     * they are short, they scroll internally, and comparing frame
     * shape against malformed frame should not mean shutting one. */
    @state() private _expanded = new Set<string>();
    /** Diagnosis groups whose coordinate list has had its cap lifted,
     * keyed "<check>#<index>". */
    @state() private _allKeys = new Set<string>();

    connectedCallback(): void {
        super.connectedCallback();
        void this._comb();
    }

    /** Always combs on open. The stored receipt may predate a Replace,
     * and a report describing codes which no longer exist is worse
     * than no report at all. */
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

    /**
     * Every code the comb walked. A matrix wig carries its lattice
     * cells plus whatever flat rows it has (power, usually), and both
     * go past the checks, so both belong under the line.
     */
    private get _total(): number {
        return (this.wig.matrix?.cells ?? 0) + (this.wig.signal_count ?? 0);
    }

    /** Findings by check class. Counts come from the receipt rather
     * than from here, because the receipt is authoritative even when
     * the findings list was truncated. */
    private _findingsByCheck(): Map<string, CombFinding[]> {
        const out = new Map<string, CombFinding[]>();
        for (const f of this._report?.findings ?? []) {
            const list = out.get(f.check);
            if (list) list.push(f);
            else out.set(f.check, [f]);
        }
        return out;
    }

    /** [bucket, classes] worst first, empties dropped. */
    private _buckets(): [string, string[]][] {
        const counts = this._report?.counts ?? {};
        const out: [string, string[]][] = [];
        for (const bucket of BUCKETS) {
            const classes = SEVERITY_ORDER.filter(
                (c) => (counts[c] ?? 0) > 0 && CONSEQUENCE[c] === bucket,
            );
            if (classes.length) out.push([bucket, classes]);
        }
        return out;
    }

    private _bucketCount(classes: string[]): number {
        const counts = this._report?.counts ?? {};
        return classes.reduce((n, c) => n + (counts[c] ?? 0), 0);
    }

    /**
     * THE NUMBER OVER THE LINE IS WHAT THE BUCKETS ADD UP TO, and it is
     * deliberately not report.suspects.
     *
     * The two differ. duplicate-labels is ADVISORY server-side, so it
     * never counts toward suspects and never lights the closet chip --
     * a correct call, since the product already declines to act on it.
     * It still gets a cosmetic bucket here, because a report that lists
     * a finding and leaves it out of its own total is arguing with
     * itself in front of the reader.
     *
     * suspects keeps its own meaning everywhere else. This is the count
     * of what THIS DIALOG is showing you.
     */
    private _flagged(buckets: [string, string[]][]): number {
        return buckets.reduce((n, b) => n + this._bucketCount(b[1]), 0);
    }

    /** A finding's diagnosis, from its localization key and params.
     * The backend never ships prebaked English. */
    private _diagnosis(f: CombFinding): string {
        return t(f.message, f.params ?? {});
    }

    /**
     * Two findings are the SAME FACT when their message key and their
     * params are identical. A dictionary comparison, not a heuristic.
     *
     * Where every finding genuinely differs, as with
     * duplicated-neighbour, each gets its own heading and this
     * degrades gracefully into a flat list.
     */
    private _byDiagnosis(findings: CombFinding[]): CombFinding[][] {
        const groups = new Map<string, CombFinding[]>();
        for (const f of findings) {
            // An ARRAY key, not a concatenation. Joining the message
            // key and the params with a separator means picking a
            // character that cannot appear in either, and getting that
            // wrong silently merges two different facts into one
            // heading. Param keys are sorted because JSON.stringify
            // follows insertion order, and two findings carrying the
            // same params in a different order are the same fact.
            const params = f.params ?? {};
            const sorted = Object.keys(params)
                .sort()
                .map((k) => [k, params[k]]);
            const key = JSON.stringify([f.message, sorted]);
            const bucket = groups.get(key);
            if (bucket) bucket.push(f);
            else groups.set(key, [f]);
        }
        return [...groups.values()];
    }

    private _toggle(set: Set<string>, id: string): Set<string> {
        const next = new Set(set);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
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
                    </h3>
                    ${this._renderExplainer()} ${this._renderBody()}
                    ${this._renderSkipped()}
                    <div class="foot-note">${t("comb.footer")}</div>
                    ${this._renderHandoff()}
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

    /**
     * What combing IS, before any number about it.
     *
     * The glyph lives here and nowhere else in the dialog. It used to
     * sit beside the heading, where it decorated a title that already
     * says "Combing"; here it is the illustration for the sentence
     * that explains the word.
     */
    private _renderExplainer() {
        const lead = t("comb.explain_lead");
        const [before, after] = lead.split("{lint}");
        return html`
            <div class="explain">
                <svg
                    class="comb"
                    viewBox="0 0 512 512"
                    width="28"
                    height="28"
                    aria-hidden="true"
                >
                    <path d=${COMB_PATH}></path>
                </svg>
                <div>
                    <div class="lead">
                        ${before}<b>${t("comb.explain_lint")}</b>${after ?? ""}
                    </div>
                    <div class="frag">
                        <span>${t("comb.frag_frames")}</span><i></i>
                        <span>${t("comb.frag_repeats")}</span><i></i>
                        <span>${t("comb.frag_timings")}</span>
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
        const buckets = this._buckets();
        if (!buckets.length)
            return html`<div class="clean">
                <span class="tick">&check;</span>
                <span>${t("comb.clean")}</span>
            </div>`;
        const findings = this._findingsByCheck();
        return html`
            ${this._renderTally(buckets)}
            ${buckets.map((b) => this._renderBucket(b[0], b[1], findings))}
            ${this._report.truncated
                ? html`<div class="trunc">
                      ${t("comb.truncated", {
                          count: String(this._report.truncated),
                      })}
                  </div>`
                : nothing}
        `;
    }

    /** The count, its denominator, and the same split drawn as a bar.
     * Forty-eight of 288 and forty-eight of 60 are different reports. */
    private _renderTally(buckets: [string, string[]][]) {
        const total = this._flagged(buckets);
        const parts = buckets.map(
            (b) => [b[0], this._bucketCount(b[1])] as [string, number],
        );
        return html`
            <div class="tally">
                <div class="n">${total}</div>
                <div class="t">
                    ${this._total > 0
                        ? t("comb.tally", { total: String(this._total) })
                        : t("comb.tally_plain")}<br />
                    ${t("comb.combed_on", {
                        date: this._report?.date ?? "",
                    })}
                </div>
            </div>
            <div class="sevbar">
                ${parts.map(
                    (p) => html`<i
                        class="sev-${p[0]}"
                        style="width:${total ? (p[1] / total) * 100 : 0}%"
                    ></i>`,
                )}
            </div>
            <div class="sevkey">
                ${parts.map(
                    (p) => html`<span
                        ><i class="sev-${p[0]}"></i>${p[1]}
                        ${t(`comb.sev_${p[0]}`)}</span
                    >`,
                )}
            </div>
        `;
    }

    private _renderBucket(
        bucket: string,
        classes: string[],
        findings: Map<string, CombFinding[]>,
    ) {
        return html`
            <div class="bkt ${bucket}">
                <div class="bh">
                    <span class="n">${this._bucketCount(classes)}</span>
                    <span>
                        <div class="tt">${t(`comb.bucket_${bucket}`)}</div>
                        <div class="ts">
                            ${t(`comb.bucket_${bucket}_body`)}
                        </div>
                    </span>
                </div>
                <div class="bb">
                    ${classes.map((c) =>
                        this._renderClass(c, findings.get(c) ?? []),
                    )}
                </div>
            </div>
        `;
    }

    private _renderClass(check: string, findings: CombFinding[]) {
        const count = this._report?.counts?.[check] ?? findings.length;
        // A class with one finding gets NO chevron: its summary line
        // already is the finding, and there is nothing behind it.
        const openable = findings.length > 1;
        const open = openable && this._expanded.has(check);
        return html`
            <div class="sub">
                <div
                    class="srow ${openable ? "can" : ""}"
                    role=${openable ? "button" : "presentation"}
                    aria-expanded=${openable ? String(open) : nothing}
                    @click=${() => {
                        if (openable)
                            this._expanded = this._toggle(
                                this._expanded,
                                check,
                            );
                    }}
                >
                    <div class="txt">
                        <div class="sn">
                            ${t(`comb.class.${check}`)}
                            <span class="c">${count}</span>
                        </div>
                        <div class="sk">${this._summary(findings)}</div>
                    </div>
                    ${openable
                        ? html`<svg
                              class="chev ${open ? "open" : ""}"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              stroke-width="2.2"
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              aria-hidden="true"
                          >
                              <path d="M9 6l6 6-6 6"></path>
                          </svg>`
                        : nothing}
                </div>
                ${open ? this._renderDiagnoses(check, findings) : nothing}
            </div>
        `;
    }

    /** One sentence naming the first offender, so the closed row still
     * says something specific rather than only how many. */
    private _summary(findings: CombFinding[]) {
        if (!findings.length) return t("comb.summary_truncated");
        const first = findings[0];
        const key = first.keys[0] ?? "";
        const rest = findings.length - 1;
        return html`${rest > 0
            ? tp("comb.summary_lead", rest, { key })
            : key}${key ? " " : ""}${this._diagnosis(first)}`;
    }

    /** Treatment A: the diagnosis once as a heading with its count,
     * then its coordinates as chips beneath it. */
    private _renderDiagnoses(check: string, findings: CombFinding[]) {
        return html`
            <div class="grp">
                ${this._byDiagnosis(findings).map((group, i) => {
                    const id = `${check}#${i}`;
                    const keys = group.flatMap((f) => f.keys);
                    const all = this._allKeys.has(id);
                    const shown = all ? keys : keys.slice(0, PREVIEW_KEYS);
                    return html`
                        <div class="dg">
                            <div class="dh">
                                <span>${this._diagnosis(group[0])}</span>
                                <span class="cn"
                                    >${tp("comb.diag_count", keys.length)}</span
                                >
                            </div>
                            <div class="keys">
                                ${shown.map((k) => html`<span>${k}</span>`)}
                            </div>
                            ${keys.length > shown.length
                                ? html`<button
                                      class="morekeys"
                                      @click=${() =>
                                          (this._allKeys = this._toggle(
                                              this._allKeys,
                                              id,
                                          ))}
                                  >
                                      ${tp(
                                          "comb.more_keys",
                                          keys.length - shown.length,
                                      )}
                                  </button>`
                                : nothing}
                        </div>
                    `;
                })}
            </div>
        `;
    }

    /**
     * Where the flagged codes actually live, and how to get there.
     *
     * The footer says only a fitting proves them on the device; this is
     * the way to the device, so the two read as one thought. It is also
     * the only place the panel states that a comb suspect surfaces as
     * an ordinary command row wearing a comb glyph, which is the thing
     * nobody would guess.
     *
     * Nothing renders on a clean comb. There is nothing to go and fix.
     */
    private _renderHandoff() {
        if (!this._report || !this._buckets().length) return nothing;
        const linked = this.wig.linked_devices ?? [];
        const suspects = this._flagged(this._buckets());
        if (!linked.length) {
            // A library codebook has no file to adopt from, so the
            // offer would be a dead end.
            if (!this.wig.filename) return nothing;
            return html`
                <div class="hand green">
                    <span class="ic">
                        <svg
                            width="19"
                            height="19"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            aria-hidden="true"
                        >
                            <path d="M12 5v14M5 12h14"></path>
                        </svg>
                    </span>
                    <span class="tx">
                        <b>${t("comb.handoff_adopt")}</b>
                        <span>${t("comb.handoff_adopt_body")}</span>
                    </span>
                    <button
                        class="action-btn go adopt-go"
                        @click=${() =>
                            this.dispatchEvent(
                                new CustomEvent("adopt-wig", {
                                    detail: this.wig,
                                    bubbles: true,
                                    composed: true,
                                }),
                            )}
                    >
                        ${t("wigs.adopt")}
                    </button>
                </div>
            `;
        }
        const device = linked[0];
        return html`
            <div class="hand">
                <span class="ic">
                    <svg
                        viewBox="0 0 512 512"
                        width="19"
                        height="19"
                        fill="currentColor"
                        aria-hidden="true"
                    >
                        <path d=${COMB_PATH}></path>
                    </svg>
                </span>
                <span class="tx">
                    <b
                        >${tp("comb.handoff_open", suspects, {
                            device: device.device_name,
                        })}</b
                    >
                    <span>${t("comb.handoff_open_body")}</span>
                </span>
                <button
                    class="action-btn go open-go"
                    @click=${() =>
                        this.dispatchEvent(
                            new CustomEvent("navigate-device", {
                                detail: device.device_id,
                                bubbles: true,
                                composed: true,
                            }),
                        )}
                >
                    ${t("comb.open_device")}
                </button>
            </div>
        `;
    }

    /** The rows the comb deliberately did not check.
     *
     * Quiet, and below the findings, because it is not a finding: a
     * pinned code is a decision somebody made, not a defect. But a
     * report that lists two findings and says nothing about the two
     * rows it skipped is claiming a completeness it does not have.
     */
    private _renderSkipped() {
        const keys = this._report?.skipped ?? [];
        if (!keys.length) return nothing;
        return html`<div class="skipline">
            <span>${t("comb.skipped_label")}</span>
            <span class="skipkeys">${keys.join(", ")}</span>
        </div>`;
    }

    static styles = [
        dialogStyles,
        css`
            /* TOP-ANCHORED, not centred, for two reasons.
               The report arrives in two paints: a short "combing..."
               box, then the full thing once the comb returns, which on
               a 750-cell lattice is a couple of hundred milliseconds.
               Centred, that reads as one window appearing and a second
               one landing on top of it (bench 2026-08-03). Anchored,
               it simply grows downward from a fixed top edge.
               It also stops a tall report being clipped: the buckets on
               a big matrix run past a laptop viewport, and a centred
               flex child with nowhere to scroll loses both ends. */
            .overlay {
                align-items: flex-start;
                overflow-y: auto;
                padding: 5vh 0;
            }
            .comb-dialog {
                max-width: 700px;
                /* Holds the first paint's height so the box does not
                   visibly jump when the findings arrive. */
                min-height: 330px;
            }
            /* THE EXPLAINER. The glyph appears once in the dialog and
               this is it: illustrating the sentence that explains the
               word, rather than decorating a heading that already
               says "Combing". */
            .explain {
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 12px 15px;
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid var(--divider-color);
                margin-bottom: 15px;
            }
            .explain .comb {
                flex: none;
                fill: #64b5f6;
                opacity: 0.85;
            }
            .explain .lead {
                font-size: 13.5px;
                line-height: 1.45;
            }
            .explain .lead b {
                font-weight: 600;
            }
            .explain .frag {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                display: flex;
                gap: 9px;
                flex-wrap: wrap;
                align-items: center;
                margin-top: 4px;
            }
            .explain .frag i {
                width: 3px;
                height: 3px;
                border-radius: 50%;
                background: #4b5157;
                display: block;
                flex: none;
            }
            /* THE DENOMINATOR. 48 findings is catastrophic on a
               seven-button remote and unremarkable on a 288-cell
               lattice, and it is the same 48. */
            .tally {
                display: flex;
                align-items: flex-end;
                gap: 13px;
                margin-bottom: 9px;
            }
            .tally .n {
                font-size: 26px;
                font-weight: 600;
                line-height: 1;
                font-variant-numeric: tabular-nums;
            }
            .tally .t {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                line-height: 1.5;
                padding-bottom: 2px;
            }
            .sevbar {
                display: flex;
                height: 6px;
                border-radius: 3px;
                overflow: hidden;
                margin-bottom: 5px;
                background: #26292c;
            }
            .sevbar i {
                display: block;
                height: 100%;
            }
            .sev-wrong {
                background: #ef5350;
            }
            .sev-ignored {
                background: #ffc107;
            }
            .sev-cosmetic {
                background: #5b6167;
            }
            .sevkey {
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
                font-size: 10.5px;
                color: var(--secondary-text-color);
                margin-bottom: 16px;
            }
            .sevkey span {
                display: flex;
                align-items: center;
                gap: 5px;
            }
            .sevkey i {
                width: 7px;
                height: 7px;
                border-radius: 2px;
                display: block;
            }
            .bkt {
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                margin-bottom: 10px;
                overflow: hidden;
            }
            .bkt .bh {
                padding: 11px 14px;
                display: flex;
                align-items: flex-start;
                gap: 12px;
            }
            .bkt .bh .n {
                font-size: 23px;
                font-weight: 600;
                line-height: 1;
                font-variant-numeric: tabular-nums;
                min-width: 30px;
                text-align: right;
                color: var(--secondary-text-color);
            }
            .bkt.wrong .bh .n {
                color: #ef5350;
            }
            .bkt.ignored .bh .n {
                color: #ffc107;
            }
            .bkt .bh .tt {
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 2px;
            }
            .bkt .bh .ts {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                line-height: 1.5;
            }
            .bkt .bb {
                border-top: 1px solid var(--divider-color);
                background: rgba(255, 255, 255, 0.018);
            }
            .sub {
                border-bottom: 1px solid rgba(127, 127, 127, 0.12);
            }
            .sub:last-child {
                border-bottom: none;
            }
            /* THE WHOLE ROW IS THE TARGET, not the 16px chevron beside
               500px of text that looks just as pressable. */
            .srow {
                padding: 9px 14px 9px 56px;
                display: flex;
                align-items: flex-start;
                gap: 10px;
            }
            .srow.can {
                cursor: pointer;
            }
            .srow.can:hover {
                background: rgba(255, 255, 255, 0.028);
            }
            .srow .txt {
                flex: 1;
                min-width: 0;
            }
            .sn {
                font-size: 12px;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .sn .c {
                font-size: 10.5px;
                color: var(--secondary-text-color);
                font-variant-numeric: tabular-nums;
                font-weight: 400;
            }
            .sk {
                font-family: ui-monospace, "SF Mono", Menlo, monospace;
                font-size: 10px;
                color: var(--secondary-text-color);
                margin-top: 4px;
                line-height: 1.6;
            }
            .chev {
                flex: none;
                width: 16px;
                height: 16px;
                margin-top: 1px;
                color: #5f666d;
                transition: transform 180ms ease, color 180ms ease;
            }
            .srow.can:hover .chev,
            .chev.open {
                color: #64b5f6;
            }
            .chev.open {
                transform: rotate(90deg);
            }
            /* GROUPED BY DIAGNOSIS. Frame shape has 22 findings and two
               facts in it; the same sentence nineteen times was never
               nineteen facts. */
            .grp {
                padding: 4px 12px 11px 56px;
                max-height: 250px;
                overflow-y: auto;
            }
            .dg {
                margin-bottom: 11px;
            }
            .dg:last-child {
                margin-bottom: 2px;
            }
            .dh {
                display: flex;
                align-items: baseline;
                gap: 9px;
                font-size: 11px;
                color: var(--secondary-text-color);
                padding-bottom: 5px;
                border-bottom: 1px solid rgba(127, 127, 127, 0.14);
                margin-bottom: 6px;
            }
            .dh .cn {
                margin-left: auto;
                font-size: 10px;
                font-variant-numeric: tabular-nums;
                white-space: nowrap;
                opacity: 0.75;
            }
            .keys {
                display: flex;
                flex-wrap: wrap;
                gap: 4px 7px;
            }
            .keys span {
                font-family: ui-monospace, "SF Mono", Menlo, monospace;
                font-size: 10.5px;
                color: var(--secondary-text-color);
                background: rgba(127, 127, 127, 0.1);
                border-radius: 3px;
                padding: 2px 6px;
            }
            .morekeys {
                margin-top: 6px;
                background: none;
                border: none;
                padding: 0;
                font: inherit;
                font-size: 10.5px;
                color: #64b5f6;
                cursor: pointer;
                text-decoration: underline dotted;
                text-underline-offset: 3px;
            }
            /* THE HANDOFF. Reads as one thought with the footer above
               it: "only a fitting proves them on the device", then the
               way to the device. */
            .hand {
                margin-top: 10px;
                padding: 11px 14px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                gap: 13px;
                border: 1px solid rgba(100, 181, 246, 0.3);
                background: rgba(100, 181, 246, 0.06);
            }
            .hand .ic {
                flex: none;
                color: #64b5f6;
                display: flex;
            }
            .hand .tx {
                flex: 1;
                font-size: 12px;
                line-height: 1.5;
            }
            .hand .tx b {
                color: var(--primary-text-color);
                font-weight: 600;
            }
            .hand .tx span {
                color: var(--secondary-text-color);
            }
            .hand .go {
                flex: none;
                padding: 5px 12px;
                font-size: 0.78rem;
            }
            .hand.green {
                border-color: rgba(79, 158, 90, 0.35);
                background: rgba(79, 158, 90, 0.07);
            }
            .hand.green .ic {
                color: #6cbf78;
            }
            .adopt-go {
                color: #6cbf78;
                border-color: rgba(79, 158, 90, 0.4);
            }
            .open-go {
                color: #64b5f6;
                border-color: rgba(100, 181, 246, 0.35);
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
            .trunc {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                padding: 2px 0 4px;
            }
            .skipline {
                display: flex;
                gap: 10px;
                align-items: baseline;
                margin-top: 12px;
                padding-top: 10px;
                border-top: 1px solid var(--divider-color);
                font-size: 12px;
                color: var(--secondary-text-color);
            }
            .skipkeys {
                color: var(--primary-text-color);
                opacity: 0.8;
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
            /* Narrow: the deep left indent that lines detail up under
               the bucket count stops paying for itself. */
            @media (max-width: 620px) {
                .srow {
                    padding-left: 14px;
                }
                .grp {
                    padding-left: 14px;
                }
            }
        `,
    ];
}
