/**
 * The fitting dialog (Perfect Fit) -- proving a wig on real hardware.
 *
 * Owner rulings baked in (fitting-flow.md Sections 12, 13, 15):
 * - The row's Fit button opens STRAIGHT into the session; there is no
 *   editor detour and no Resume button -- reopening IS resuming,
 *   because marks persist in the wig file as you go.
 * - No auto-advance: after a verdict the list stays put. Untested
 *   signals sort first ON OPEN only; the order never shuffles
 *   mid-session.
 * - SEND stays after sending; the machine facts (sent count, heard
 *   back) update per send.
 * - Actions are CLOSE / DISCARD / FINISH -- no "fitting" in the
 *   labels. Close keeps everything; Discard is the explicit
 *   throw-away, confirmed inline.
 * - The green moment: every signal marked worked flips the progress
 *   line and fills FINISH solid green. "Perfect Fit" appears in the
 *   signing sentence (State C), never on a button.
 * - Standard dialog size at every signal count; the list scrolls.
 *
 * Two views in one dialog: the session (State B) and the signing
 * confirm (State C). Dispatches ``closed`` always, plus ``recorded``
 * with the finish result so the closet can refresh its check marks.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type { FittingRow, FittingState, WigInfo } from "./types.js";
import { displayTemp, installUnit } from "./temperature.js";

// Curated kind suggestions; the input accepts anything (custom kinds
// welcome) and the server squashes to lowercase alphanumerics.
const KIND_SUGGESTIONS = [
    "tv", "soundbar", "receiver", "settopbox", "projector",
    "fan", "light", "candles", "ac", "heater", "blinds",
];

interface RowFacts {
    sent: number;
    heard: boolean;
    busy: boolean;
}

/** Display cleanup for a prefilled GitHub handle: strip a profile URL
 * down to its account (everything up to the first remaining slash, so
 * a copied repo URL yields the owner, not owner/repo), drop a typed @.
 * Prefill only; the backend normalizes again at record time. */
function _cleanGithubHandle(value: string): string {
    let v = value.trim();
    v = v.replace(/^https?:\/\/(www\.)?github\.com\//i, "");
    v = v.replace(/^@+/, "");
    const slash = v.indexOf("/");
    if (slash !== -1) v = v.slice(0, slash);
    return v.trim();
}

@customElement("ir-fitting-dialog")
export class IrFittingDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public wig!: WigInfo;

    @state() private _fit: FittingState | null = null;
    @state() private _order: number[] = [];
    @state() private _verdicts = new Map<number, "worked" | "failed">();
    @state() private _facts = new Map<number, RowFacts>();
    @state() private _emitter = "";
    // Session send-times control (fine-tuned-fittings). Every fresh
    // session starts at 1; NEVER carried between wigs, because a
    // remembered 3 quietly inflates every later wig's claim. Restored
    // from the state payload on open so a resumed session shows what
    // was used rather than snapping back to 1.
    @state() private _sendTimes = 1;
    @state() private _receiverIds = new Set<string>();
    @state() private _view: "session" | "sign" | "ledger" = "session";
    @state() private _confirmDiscard = false;
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _handle = "";
    @state() private _github = "";
    @state() private _note = "";
    @state() private _kind = "";

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
    }

    private async _load(): Promise<void> {
        try {
            const [fit, receivers] = await Promise.all([
                this.api.fittingState(this.wig.filename),
                this.api.listReceivers().catch(() => []),
            ]);
            this._receiverIds = new Set(receivers.map((r) => r.entity_id));
            this._fit = fit;
            this._handle = fit.username;
            this._kind = fit.kind ?? "";
            if (fit.send_times)
                this._sendTimes = Math.max(
                    1,
                    Math.min(fit.send_times, 10),
                );
            // Prefill the GitHub handle from the user's previous
            // fitting on this install ("remembered per install").
            const mine = fit.ledger.find(
                (row) =>
                    row.github &&
                    row.handle.toLowerCase() ===
                        fit.username.toLowerCase(),
            );
            // Normalized on prefill: a previous fitting may carry an
            // imported wig's dirty value (URL, @-prefixed), and a URL
            // sitting behind the field's decorative @ reads as a bug.
            // The backend cleans again on record either way.
            this._github = _cleanGithubHandle(mine?.github ?? "");
            const verdicts = new Map<number, "worked" | "failed">();
            fit.signals.forEach((alias, i) => {
                if (fit.draft?.failed.includes(alias))
                    verdicts.set(i, "failed");
                else if (fit.draft?.confirmed.includes(alias))
                    verdicts.set(i, "worked");
            });
            this._verdicts = verdicts;
            // Untested first, on open only; stable within each half.
            // Matrix sessions keep checklist order instead (mockup
            // CC1): the sectioned walk start / modes / fan / swing /
            // temp / wrap IS the session's shape, and resorting by
            // verdict would scatter rows across their headers.
            const idx = fit.signals.map((_, i) => i);
            this._order = fit.matrix
                ? idx
                : [
                      ...idx.filter((i) => !verdicts.has(i)),
                      ...idx.filter((i) => verdicts.has(i)),
                  ];
            const emitters = this._emitters();
            if (emitters.length === 1) this._emitter = emitters[0].id;
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
    }

    private _emitters(): { id: string; name: string }[] {
        const states = (this.hass?.states ?? {}) as Record<string, any>;
        const out: { id: string; name: string }[] = [];
        for (const [id, st] of Object.entries(states)) {
            if (
                id.startsWith("infrared.") &&
                !this._receiverIds.has(id) &&
                !st.attributes?.hair_observer
            ) {
                out.push({
                    id,
                    name: st.attributes?.friendly_name ?? id,
                });
            }
        }
        return out;
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private _onSendTimesInput(e: Event): void {
        const raw = Number((e.target as HTMLInputElement).value);
        if (!Number.isFinite(raw)) return;
        this._sendTimes = Math.max(1, Math.min(Math.round(raw), 10));
    }

    private async _send(i: number): Promise<void> {
        if (!this._emitter || !this._fit) return;
        const facts = this._facts.get(i) ?? {
            sent: 0,
            heard: false,
            busy: false,
        };
        if (facts.busy) return;
        this._facts = new Map(this._facts).set(i, {
            ...facts,
            busy: true,
        });
        try {
            const res = await this.api.fittingSend(
                this.wig.filename,
                i,
                this._emitter,
                this._sendTimes,
            );
            this._facts = new Map(this._facts).set(i, {
                sent: facts.sent + 1,
                heard: facts.heard || res.heard,
                busy: false,
            });
        } catch (err: any) {
            this._facts = new Map(this._facts).set(i, {
                ...facts,
                busy: false,
            });
            this._error = err?.message ?? String(err);
        }
    }

    private async _mark(
        i: number,
        verdict: "worked" | "failed",
    ): Promise<void> {
        const current = this._verdicts.get(i);
        const next = current === verdict ? "untested" : verdict;
        const verdicts = new Map(this._verdicts);
        if (next === "untested") verdicts.delete(i);
        else verdicts.set(i, next);
        this._verdicts = verdicts;
        try {
            await this.api.fittingMark(this.wig.filename, i, next);
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
    }

    private async _discard(): Promise<void> {
        this._busy = true;
        try {
            await this.api.fittingDiscard(this.wig.filename);
        } catch {
            // No draft to discard is fine -- nothing was marked yet.
        }
        this._busy = false;
        this._recordedRefresh();
        this._close();
    }

    private async _record(): Promise<void> {
        this._busy = true;
        this._error = null;
        try {
            const result = await this.api.fittingFinish(
                this.wig.filename,
                {
                    ...(this._handle.trim()
                        ? { handle: this._handle.trim() }
                        : {}),
                    ...(this._github.trim()
                        ? { github: this._github.trim() }
                        : {}),
                    ...(this._note.trim()
                        ? { note: this._note.trim() }
                        : {}),
                    ...(this._kind.trim() && !this._fit?.kind
                        ? { kind: this._kind.trim() }
                        : {}),
                },
            );
            this.dispatchEvent(
                new CustomEvent("recorded", {
                    detail: result,
                    bubbles: true,
                    composed: true,
                }),
            );
            this._close();
        } catch (err: any) {
            this._error = err?.message ?? String(err);
        }
        this._busy = false;
    }

    private _recordedRefresh(): void {
        this.dispatchEvent(
            new CustomEvent("recorded", {
                detail: null,
                bubbles: true,
                composed: true,
            }),
        );
    }

    private get _counts() {
        let worked = 0;
        let failed = 0;
        for (const v of this._verdicts.values()) {
            if (v === "worked") worked += 1;
            else failed += 1;
        }
        const total = this._fit?.signals.length ?? 0;
        return {
            worked,
            failed,
            tested: worked + failed,
            total,
            perfect: total > 0 && worked === total,
        };
    }

    render() {
        return html`
            <div class="overlay" @click=${this._close}>
                <div
                    class="dialog fit-dialog"
                    @click=${(e: Event) => e.stopPropagation()}
                >
                    ${this._view === "sign"
                        ? this._renderSign()
                        : this._view === "ledger"
                          ? this._renderLedger()
                          : this._renderSession()}
                </div>
            </div>
        `;
    }

    /** The user's own ledger row (valid hash), and everyone else's. */
    private _ledgerSplit() {
        const me = (this._fit?.username ?? "").trim().toLowerCase();
        const rows = this._fit?.ledger ?? [];
        const mine = rows.find(
            (r) => r.valid && r.handle.trim().toLowerCase() === me,
        );
        const others = rows.filter((r) => r !== mine);
        return { mine, others };
    }

    private _chipDate(date: string | null): string {
        if (!date) return "";
        const parsed = new Date(`${date}T00:00:00`);
        if (Number.isNaN(parsed.getTime())) return date;
        return parsed.toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
        });
    }

    /** Fitted-status chips (owner rulings 2026-07-27): your fitting
     * leads, everyone else folds into one quiet chip, and both open
     * the ledger -- which is where the ledger lives. Unfitted wigs
     * render nothing, so first-time fitting looks unchanged. */
    private _renderFitChips() {
        const { mine, others } = this._ledgerSplit();
        if (!mine && others.length === 0) return nothing;
        const total = this._fit?.signals.length ?? 0;
        return html`
            <div class="fitrow">
                ${mine
                    ? html`<button
                          class="fstat you ${mine.complete
                              ? ""
                              : "partial"}"
                          @click=${() => (this._view = "ledger")}
                      >
                          <span class="tick">&check;</span>
                          ${mine.complete
                              ? t("fitting.chip_you", {
                                    date: this._chipDate(mine.date),
                                })
                              : t("fitting.chip_you_partial", {
                                    confirmed: String(mine.confirmed),
                                    total: String(total),
                                })}
                      </button>`
                    : nothing}
                ${others.length
                    ? html`<button
                          class="fstat others"
                          @click=${() => (this._view = "ledger")}
                      >
                          ${tp("fitting.chip_others", others.length)}
                      </button>`
                    : nothing}
            </div>
        `;
    }

    private _renderSession() {
        const c = this._counts;
        return html`
            <h3 class="heading">${this.wig.name}</h3>
            ${this._fit?.matrix
                ? html`<div class="matrix-claim">
                      ${t("fitting.matrix_claim", {
                          sends: String(this._fit.rows.length),
                          cells: String(
                              this.wig.matrix?.cells ??
                                  this._fit.rows.length,
                          ),
                      })}
                  </div>`
                : nothing}
            <div class="sess-head">${t("fitting.header")}</div>
            ${this._renderFitChips()}
            ${this._error
                ? html`<div class="err">${this._error}</div>`
                : nothing}
            <div class="field">
                <label>${t("fitting.emitter")}</label>
                <select
                    .value=${this._emitter}
                    @change=${(e: Event) =>
                        (this._emitter = (
                            e.target as HTMLSelectElement
                        ).value)}
                >
                    <option value="" ?selected=${!this._emitter}>
                        ${t("fitting.pick_emitter")}
                    </option>
                    ${this._emitters().map(
                        (em) => html`<option
                            value=${em.id}
                            ?selected=${em.id === this._emitter}
                        >
                            ${em.name}
                        </option>`,
                    )}
                </select>
            </div>
            <div class="field">
                <label>${t("fitting.send_times")}</label>
                <input
                    class="send-count"
                    type="number"
                    min="1"
                    max="10"
                    .value=${String(this._sendTimes)}
                    @input=${this._onSendTimesInput}
                />
                <div class="hint">${t("fitting.send_times_hint")}</div>
            </div>
            <div class="sig-list">
                ${this._fit
                    ? this._fit.matrix
                        ? this._renderMatrixList()
                        : this._order.map((i) => this._renderRow(i))
                    : html`<div class="loading">
                          ${t("common.loading_plain")}
                      </div>`}
            </div>
            <div class="progress-line ${c.perfect ? "perfect" : ""}">
                <span>
                    ${c.perfect
                        ? t("fitting.all_worked", {
                              count: String(c.total),
                          })
                        : html`${t("fitting.progress", {
                              tested: String(c.tested),
                              total: String(c.total),
                          })}${c.failed > 0
                              ? html` &middot;
                                    <span class="fail-note"
                                        >${tp(
                                            "fitting.failed",
                                            c.failed,
                                        )}</span
                                    >`
                              : nothing}`}
                </span>
                <span class="bar"
                    ><i
                        style="width:${c.total
                            ? Math.round((c.tested / c.total) * 100)
                            : 0}%"
                    ></i
                ></span>
            </div>
            <div class="dialog-actions fit-actions">
                ${this._confirmDiscard
                    ? html`
                          <span class="discard-q"
                              >${t("fitting.discard_confirm")}</span
                          >
                          <span class="spacer"></span>
                          <button
                              class="action-btn cancel-btn"
                              @click=${() =>
                                  (this._confirmDiscard = false)}
                          >
                              ${t("fitting.keep")}
                          </button>
                          <button
                              class="action-btn discard-yes"
                              ?disabled=${this._busy}
                              @click=${this._discard}
                          >
                              ${t("fitting.discard")}
                          </button>
                      `
                    : html`
                          <button
                              class="action-btn cancel-btn"
                              @click=${this._close}
                          >
                              ${t("common.close")}
                          </button>
                          <span class="spacer"></span>
                          <button
                              class="action-btn discard-btn"
                              ?disabled=${c.tested === 0}
                              @click=${() =>
                                  (this._confirmDiscard = true)}
                          >
                              ${t("fitting.discard")}
                          </button>
                          <button
                              class="action-btn finish-btn ${c.perfect
                                  ? "green"
                                  : ""}"
                              ?disabled=${c.tested === 0}
                              @click=${() => (this._view = "sign")}
                          >
                              ${t("fitting.finish")}
                          </button>
                      `}
            </div>
            <div class="hint">${t("fitting.close_hint")}</div>
        `;
    }

    private _renderRow(i: number) {
        const alias = this._fit!.signals[i];
        return html`
            <div class="sig-row">
                <span class="sig-alias" title=${alias}>${alias}</span>
                ${this._renderRowControls(i)}
            </div>
        `;
    }

    /** The row anatomy every session row shares (Cold Cuts): machine
     * facts, SEND, WORKED, DID NOT. Extracted verbatim from the signal
     * row so the matrix rows carry the identical controls -- only the
     * label anatomy differs between the two wig kinds. */
    private _renderRowControls(i: number) {
        const verdict = this._verdicts.get(i);
        const facts = this._facts.get(i);
        return html`${facts?.sent
                ? html`<span class="facts">
                      ${facts.sent > 1
                          ? t("fitting.sent_n", {
                                count: String(facts.sent),
                            })
                          : t("fitting.sent")}${facts.heard
                          ? html` &middot;
                                <span class="heard"
                                    >${t("fitting.heard")}</span
                                >`
                          : nothing}
                  </span>`
                : nothing}
            <button
                class="send-btn"
                ?disabled=${!this._emitter || facts?.busy}
                title=${this._emitter
                    ? ""
                    : t("fitting.pick_emitter")}
                @click=${() => void this._send(i)}
            >
                ${t("fitting.send")}
            </button>
            <button
                class="vbtn ${verdict === "worked" ? "worked-on" : ""}"
                @click=${() => void this._mark(i, "worked")}
            >
                ${t("fitting.worked")}
            </button>
            <button
                class="vbtn ${verdict === "failed" ? "failed-on" : ""}"
                @click=${() => void this._mark(i, "failed")}
            >
                ${t("fitting.did_not")}
            </button>`;
    }

    /** The dimension-check list (mockup CC1): the same scrolling list,
     * grouped under uppercase section headers with a thin rule. Rows
     * keep their session index, so marks and sends address the backend
     * exactly as the signal flow does. */
    private _renderMatrixList() {
        const rows = this._fit!.rows;
        const out: unknown[] = [];
        let section: string | null = null;
        rows.forEach((row, i) => {
            if (row.section !== section) {
                section = row.section;
                out.push(this._renderSectionHead(row));
            }
            out.push(this._renderMatrixRow(i));
        });
        return out;
    }

    /** One matrix temperature as display text, converted to the
     * viewer's install unit when it differs from the wig's native
     * unit (unit ruling 2026-07-29). Labels only -- row KEYS and the
     * mark/send indexing stay native and untouched. */
    private _displayTemp(temp: number): string {
        return displayTemp(
            temp,
            this._fit?.unit ?? "C",
            installUnit(this.hass),
            this._fit?.precision ?? 1,
        );
    }

    /** The section's dim context note: what stays constant while this
     * section's rows walk one dimension, read off the section's FIRST
     * row (owner ruling 2026-07-28, e.g. "in cool 23, fan auto"). */
    private _sectionNote(row: FittingRow): string {
        if (row.section === "modes") return t("fitting.sec_modes_note");
        if (
            row.section !== "fan" &&
            row.section !== "swing" &&
            row.section !== "temp"
        ) {
            return "";
        }
        const parts: string[] = [];
        if (row.mode) {
            const temp = row.section === "temp" ? null : row.temp;
            parts.push(
                temp != null
                    ? `${row.mode} ${this._displayTemp(temp)}`
                    : row.mode,
            );
        }
        if (row.section !== "fan" && row.fan != null) {
            parts.push(t("fitting.ctx_fan", { fan: row.fan }));
        }
        if (row.section !== "swing" && row.swing != null) {
            parts.push(t("fitting.ctx_swing", { swing: row.swing }));
        }
        if (parts.length === 0) return "";
        return t("fitting.sec_in", { context: parts.join(", ") });
    }

    private _renderSectionHead(row: FittingRow) {
        const note = this._sectionNote(row);
        return html`
            <div class="sec-head">
                <span>${t(`fitting.sec_${row.section}`)}</span>
                ${note
                    ? html`<span class="sec-note">${note}</span>`
                    : nothing}
            </div>
        `;
    }

    private _renderMatrixRow(i: number) {
        const row = this._fit!.rows[i];
        let label: string = row.key;
        let caps = false;
        let dim = "";
        if (row.section === "start") {
            label = t("fitting.row_on");
            caps = true;
        } else if (row.section === "wrap") {
            label = t("fitting.row_off");
            caps = true;
        } else if (row.section === "modes") {
            label = row.mode ?? row.key;
            caps = true;
            dim = [
                row.fan,
                row.temp != null
                    ? `${this._displayTemp(row.temp)}\u00b0`
                    : null,
            ]
                .filter(Boolean)
                .join(" \u00b7 ");
            if (row.temp_less) {
                dim = [dim, t("fitting.no_temp_note")]
                    .filter(Boolean)
                    .join(" ");
            }
        } else if (row.section === "fan") {
            label = row.fan ?? row.key;
        } else if (row.section === "swing") {
            label = row.swing ?? row.key;
        } else if (row.section === "temp") {
            label = t(
                row.temp_role === "min"
                    ? "fitting.temp_min"
                    : "fitting.temp_max",
                { temp: row.temp != null ? this._displayTemp(row.temp) : "" },
            );
        }
        return html`
            <div class="sig-row">
                <span
                    class="sig-alias ${caps ? "caps" : ""}"
                    title=${row.key}
                    >${label}${dim
                        ? html` <span class="row-dim">${dim}</span>`
                        : nothing}</span
                >
                ${this._renderRowControls(i)}
            </div>
        `;
    }

    /** The fittings ledger (placement ruled 2026-07-27: it lives here,
     * behind the status chips). Each row: handle, signature state,
     * date, then the evidence line. A bad signature discredits the
     * attribution, not the data, and the wording says which. */
    private _renderLedger() {
        const rows = this._fit?.ledger ?? [];
        const total = this._fit?.signals.length ?? 0;
        return html`
            <h3 class="heading">${t("fitting.ledger_heading")}</h3>
            <div class="ledger">
                ${rows.map((r) => {
                    const evidence: string[] = [];
                    if (r.hair_version)
                        evidence.push(`HAIR ${r.hair_version}`);
                    if (r.emitter)
                        evidence.push(
                            r.receiver
                                ? `${r.emitter} → ${r.receiver}`
                                : r.emitter,
                        );
                    evidence.push(
                        t("fitting.ledger_coverage", {
                            confirmed: String(r.confirmed),
                            total: String(total),
                        }),
                    );
                    if (r.failed)
                        evidence.push(
                            tp("fitting.failed", r.failed),
                        );
                    if (r.signals_heard)
                        evidence.push(
                            t("fitting.ledger_heard", {
                                count: String(r.signals_heard),
                            }),
                        );
                    if (r.send_times_used)
                        // Absent renders nothing: unknown is not 1.
                        evidence.push(
                            t("fitting.ledger_send_times", {
                                count: String(r.send_times_used),
                            }),
                        );
                    if (r.key_fingerprint)
                        evidence.push(`key ${r.key_fingerprint}`);
                    return html`
                        <div class="led-row">
                            <div class="led-head">
                                <span class="led-handle"
                                    >${r.handle}</span
                                >
                                ${r.github
                                    ? html`<span class="led-gh"
                                          >@${r.github.replace(
                                              /^@/,
                                              "",
                                          )}</span
                                      >`
                                    : nothing}
                                ${r.draft
                                    ? html`<span
                                          class="led-sig unsigned"
                                          >${t(
                                              "fitting.ledger_in_progress",
                                          )}</span
                                      >`
                                    : r.signed === "valid"
                                      ? html`<span
                                            class="led-sig valid"
                                            >&check;
                                            ${t(
                                                "fitting.ledger_signed",
                                            )}</span
                                        >`
                                      : r.signed === "invalid"
                                        ? html`<span
                                              class="led-sig bad"
                                              >${t(
                                                  "fitting.ledger_bad_sig",
                                              )}</span
                                          >`
                                        : html`<span
                                              class="led-sig unsigned"
                                              >${t(
                                                  "fitting.ledger_unsigned",
                                              )}</span
                                          >`}
                                <span class="led-date"
                                    >${r.date ?? ""}</span
                                >
                            </div>
                            <div class="led-evidence">
                                ${evidence.join(" · ")}
                            </div>
                            ${!r.valid
                                ? html`<div class="led-invalid">
                                      ${t("fitting.ledger_invalid")}
                                  </div>`
                                : nothing}
                            ${r.note
                                ? html`<div class="led-note">
                                      “${r.note}”
                                  </div>`
                                : nothing}
                        </div>
                    `;
                })}
            </div>
            <div class="dialog-actions fit-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${() => (this._view = "session")}
                >
                    ${t("common.back")}
                </button>
            </div>
        `;
    }

    private _renderSign() {
        const c = this._counts;
        const emitterName =
            this._emitters().find((em) => em.id === this._emitter)
                ?.name ?? t("fitting.your_emitter");
        return html`
            <h3 class="heading">${t("fitting.sign_heading")}</h3>
            <div class="sign-line ${c.perfect ? "perfect" : ""}">
                ${c.perfect
                    ? t("fitting.sign_perfect", {
                          count: String(c.total),
                          emitter: emitterName,
                      })
                    : t("fitting.sign_partial", {
                          worked: String(c.worked),
                          failed: String(c.failed),
                          total: String(c.total),
                          emitter: emitterName,
                      })}
            </div>
            ${this._error
                ? html`<div class="err">${this._error}</div>`
                : nothing}
            <div class="field">
                <label>${t("fitting.handle")}</label>
                <input
                    .value=${this._handle}
                    @input=${(e: Event) =>
                        (this._handle = (
                            e.target as HTMLInputElement
                        ).value)}
                />
            </div>
            <div class="field">
                <label>${t("fitting.github")}</label>
                <!-- Decorative @ (roadmap, 2026-07-30): the format is
                     visible without being typed. Never enters _github;
                     the record payload is unchanged. Placeholder stays
                     "octocat" on purpose -- "@octocat" would suggest
                     typing the symbol, the opposite of the point. -->
                <div class="gh-wrap">
                    <span class="gh-at" aria-hidden="true">@</span>
                    <input
                        .value=${this._github}
                        placeholder="octocat"
                        @input=${(e: Event) =>
                            (this._github = (
                                e.target as HTMLInputElement
                            ).value)}
                    />
                </div>
                <div class="hint">${t("fitting.github_hint")}</div>
            </div>
            ${!this._fit?.kind
                ? html`<div class="field">
                      <label>${t("fitting.kind")}</label>
                      <input
                          list="kind-suggestions"
                          .value=${this._kind}
                          placeholder=${t("fitting.kind_placeholder")}
                          @input=${(e: Event) =>
                              (this._kind = (
                                  e.target as HTMLInputElement
                              ).value)}
                      />
                      <datalist id="kind-suggestions">
                          ${KIND_SUGGESTIONS.map(
                              (k) => html`<option value=${k}></option>`,
                          )}
                      </datalist>
                      <div class="hint">${t("fitting.kind_hint")}</div>
                  </div>`
                : nothing}
            <div class="field">
                <label>${t("fitting.note")}</label>
                <input
                    .value=${this._note}
                    placeholder=${t("fitting.note_placeholder")}
                    @input=${(e: Event) =>
                        (this._note = (
                            e.target as HTMLInputElement
                        ).value)}
                />
            </div>
            <div class="hint">${t("fitting.signed_hint")}</div>
            <div class="dialog-actions fit-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${() => (this._view = "session")}
                >
                    ${t("common.back")}
                </button>
                <span class="spacer"></span>
                <button
                    class="action-btn record-btn"
                    ?disabled=${this._busy}
                    @click=${this._record}
                >
                    ${t("fitting.record")}
                </button>
            </div>
        `;
    }

    static styles = [
        dialogStyles,
        css`
            .fit-dialog {
                max-width: 440px;
            }
            /* Decorative @ inside the GitHub field's left edge. */
            .gh-wrap {
                position: relative;
            }
            .gh-wrap .gh-at {
                position: absolute;
                left: 10px;
                top: 50%;
                transform: translateY(-50%);
                color: var(--secondary-text-color);
                pointer-events: none;
            }
            .gh-wrap input {
                width: 100%;
                box-sizing: border-box;
                padding-left: 24px;
            }
            .sess-head {
                font-size: 12.5px;
                color: var(--secondary-text-color);
                line-height: 1.5;
                margin-bottom: 12px;
            }
            /* The dimension-check claim (mockup CC1): sits under the
               title and says exactly what the 12-20 sends stand for. */
            .matrix-claim {
                font-size: 12.5px;
                color: var(--primary-text-color);
                line-height: 1.5;
                margin-bottom: 8px;
            }
            /* Sectioned list anatomy (matrix sessions only): uppercase
               header over a thin rule, dim context note alongside. */
            .sec-head {
                display: flex;
                align-items: baseline;
                gap: 8px;
                padding: 9px 12px 4px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--secondary-text-color);
                border-bottom: 1px solid var(--divider-color);
            }
            .sec-note {
                font-weight: 400;
                letter-spacing: normal;
                text-transform: none;
                font-size: 10.5px;
                opacity: 0.8;
            }
            .sig-alias.caps {
                text-transform: uppercase;
            }
            .row-dim {
                font-weight: 400;
                font-size: 11px;
                color: var(--secondary-text-color);
                text-transform: none;
            }
            .fitrow {
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
                margin: -4px 0 12px;
            }
            .fstat {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-size: 11px;
                font-weight: 500;
                padding: 3px 9px;
                border-radius: 12px;
                letter-spacing: 0.02em;
                font-family: inherit;
                cursor: pointer;
                background: none;
            }
            .fstat .tick {
                font-weight: 700;
            }
            .fstat.you {
                color: #66bb6a;
                background: rgba(76, 175, 80, 0.12);
                border: 1px solid rgba(76, 175, 80, 0.3);
            }
            .fstat.you.partial {
                color: #ffb300;
                background: rgba(255, 179, 0, 0.1);
                border-color: rgba(255, 179, 0, 0.35);
            }
            .fstat.others {
                color: var(--secondary-text-color);
                border: 1px solid var(--divider-color);
            }
            .fstat:hover {
                filter: brightness(1.2);
            }
            .ledger {
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                max-height: 340px;
                overflow-y: auto;
            }
            .led-row {
                padding: 9px 12px;
                border-bottom: 1px solid var(--divider-color);
                font-size: 12.5px;
                line-height: 1.5;
            }
            .led-row:last-child {
                border-bottom: none;
            }
            .led-head {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            .led-handle {
                font-weight: 600;
            }
            .led-gh {
                color: #78909c;
                font-size: 11.5px;
            }
            .led-date {
                color: var(--secondary-text-color);
                margin-left: auto;
                font-size: 11.5px;
            }
            .led-sig {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                border-radius: 3px;
                padding: 1px 6px;
            }
            .led-sig.valid {
                color: #66bb6a;
                background: rgba(76, 175, 80, 0.12);
                border: 1px solid rgba(76, 175, 80, 0.3);
            }
            .led-sig.bad {
                color: #e57373;
                background: rgba(198, 40, 40, 0.12);
                border: 1px solid rgba(198, 40, 40, 0.45);
            }
            .led-sig.unsigned {
                color: var(--secondary-text-color);
                border: 1px solid var(--divider-color);
            }
            .led-evidence {
                color: var(--secondary-text-color);
                font-size: 11.5px;
                margin-top: 2px;
            }
            .led-invalid {
                color: #e57373;
                font-size: 11.5px;
                margin-top: 2px;
            }
            .led-note {
                color: var(--primary-text-color);
                font-size: 11.5px;
                margin-top: 2px;
                font-style: italic;
            }
            .err {
                font-size: 12px;
                color: var(--error-color, #c62828);
                margin-bottom: 8px;
            }
            .field label {
                font-size: 11px;
                letter-spacing: 0.4px;
                text-transform: uppercase;
            }
            .field select {
                width: 100%;
                border: 1px solid var(--divider-color);
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
                font-family: inherit;
                background: var(--card-background-color);
                color: var(--primary-text-color);
            }
            .sig-list {
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                max-height: 300px;
                overflow-y: auto;
                margin-top: 4px;
            }
            .loading {
                padding: 16px;
                font-size: 12.5px;
                color: var(--secondary-text-color);
            }
            .sig-row {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 7px 12px;
                border-bottom: 1px solid var(--divider-color);
                font-size: 13px;
                min-height: 40px;
                box-sizing: border-box;
            }
            .sig-row:last-child {
                border-bottom: none;
            }
            .sig-alias {
                font-weight: 500;
                flex: 1;
                min-width: 0;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .facts {
                font-size: 11px;
                color: var(--secondary-text-color);
                flex: none;
                white-space: nowrap;
            }
            .facts .heard {
                color: #66bb6a;
            }
            .send-btn {
                background: none;
                border: 1px solid var(--divider-color);
                color: var(--primary-text-color);
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11.5px;
                font-weight: 500;
                text-transform: uppercase;
                cursor: pointer;
                font-family: inherit;
                flex: none;
            }
            .send-btn:hover:not(:disabled) {
                border-color: var(--secondary-text-color);
            }
            .send-btn:disabled {
                opacity: 0.45;
                cursor: default;
            }
            .vbtn {
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                cursor: pointer;
                font-family: inherit;
                flex: none;
                background: none;
                border: 1px solid var(--divider-color);
                color: var(--secondary-text-color);
            }
            .vbtn.worked-on {
                background: rgba(76, 175, 80, 0.12);
                border-color: rgba(76, 175, 80, 0.45);
                color: #66bb6a;
            }
            .vbtn.failed-on {
                background: rgba(198, 40, 40, 0.14);
                border-color: rgba(198, 40, 40, 0.5);
                color: #e57373;
            }
            .progress-line {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 12.5px;
                color: var(--secondary-text-color);
                padding: 10px 2px 0;
            }
            .progress-line.perfect {
                color: #66bb6a;
            }
            .progress-line .bar {
                flex: 1;
                height: 4px;
                border-radius: 2px;
                background: var(--divider-color);
                overflow: hidden;
            }
            .progress-line .bar i {
                display: block;
                height: 100%;
                background: #66bb6a;
            }
            .fail-note {
                color: #e57373;
            }
            .fit-actions {
                margin-top: 14px;
            }
            .spacer {
                flex: 1;
            }
            .discard-q {
                font-size: 12.5px;
                color: var(--primary-text-color);
            }
            .discard-btn {
                color: var(--secondary-text-color);
            }
            .discard-yes {
                color: var(--error-color, #c62828);
                border-color: var(--error-color, #c62828);
            }
            .finish-btn {
                color: #66bb6a;
                border-color: rgba(76, 175, 80, 0.45);
            }
            .finish-btn.green {
                background: #2e7d32;
                border-color: #2e7d32;
                color: #fff;
            }
            .record-btn {
                background: #2e7d32;
                border-color: #2e7d32;
                color: #fff;
            }
            .sign-line {
                border-radius: 8px;
                padding: 9px 12px;
                font-size: 12.5px;
                line-height: 1.45;
                margin-bottom: 12px;
                background: rgba(255, 160, 0, 0.1);
                border: 1px solid rgba(255, 160, 0, 0.4);
            }
            .sign-line.perfect {
                background: rgba(76, 175, 80, 0.12);
                border-color: rgba(76, 175, 80, 0.45);
            }
            .hint {
                font-size: 11.5px;
                color: var(--secondary-text-color);
                margin-top: 6px;
                line-height: 1.4;
            }
        `,
    ];
}
