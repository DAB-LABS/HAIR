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
import type { FittingState, WigInfo } from "./types.js";

interface RowFacts {
    sent: number;
    heard: boolean;
    busy: boolean;
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
    @state() private _receiverIds = new Set<string>();
    @state() private _view: "session" | "sign" | "ledger" = "session";
    @state() private _confirmDiscard = false;
    @state() private _busy = false;
    @state() private _error: string | null = null;
    @state() private _handle = "";
    @state() private _github = "";
    @state() private _note = "";

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
            // Prefill the GitHub handle from the user's previous
            // fitting on this install ("remembered per install").
            const mine = fit.ledger.find(
                (row) =>
                    row.github &&
                    row.handle.toLowerCase() ===
                        fit.username.toLowerCase(),
            );
            this._github = mine?.github ?? "";
            const verdicts = new Map<number, "worked" | "failed">();
            fit.signals.forEach((alias, i) => {
                if (fit.draft?.failed.includes(alias))
                    verdicts.set(i, "failed");
                else if (fit.draft?.confirmed.includes(alias))
                    verdicts.set(i, "worked");
            });
            this._verdicts = verdicts;
            // Untested first, on open only; stable within each half.
            const idx = fit.signals.map((_, i) => i);
            this._order = [
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
            <div class="sig-list">
                ${this._fit
                    ? this._order.map((i) => this._renderRow(i))
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
        const verdict = this._verdicts.get(i);
        const facts = this._facts.get(i);
        return html`
            <div class="sig-row">
                <span class="sig-alias" title=${alias}>${alias}</span>
                ${facts?.sent
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
                </button>
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
                <input
                    .value=${this._github}
                    placeholder="octocat"
                    @input=${(e: Event) =>
                        (this._github = (
                            e.target as HTMLInputElement
                        ).value)}
                />
                <div class="hint">${t("fitting.github_hint")}</div>
            </div>
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
            .sess-head {
                font-size: 12.5px;
                color: var(--secondary-text-color);
                line-height: 1.5;
                margin-bottom: 12px;
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
