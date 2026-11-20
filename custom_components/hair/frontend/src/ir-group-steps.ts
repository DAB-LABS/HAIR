/**
 * A grouped command, opened (grouped-signals.md).
 *
 * The steps in order. Each step shows its device and command, with its
 * protocol chip or band so IR and RF steps tell apart, a grip to drag
 * it, and an x to remove it. Between two steps sits the delay field:
 * counted from the end of the first step's signal, 300 ms or more, and
 * the field says why when it refuses less. A missing step (its command
 * was deleted) shows in amber with its last names and "Pick again".
 * "+ Add step" opens the picker.
 *
 * Changes save as they're made, as a rename or a reorder does: each one goes
 * to `hair/command/group/steps`, and the device as it now is goes up as
 * `device-updated`. A delay saves when the field is left or Enter is
 * pressed, and only when the field holds a delay the server would take.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { keyed } from "lit/directives/keyed.js";
import { t } from "./localize.js";
import Sortable from "sortablejs";
import type { HairApi } from "./api.js";
import type { GroupStepView, IRCommand } from "./types.js";
import {
    GROUP_DELAY_DEFAULT_MS,
    GROUP_DELAY_MIN_MS,
    GROUP_MAX_STEPS,
    aboutSeconds,
    delayProblem,
    moveStep,
    stepsForSave,
} from "./group-steps.js";
import { bandText } from "./ir-group-picker.js";
import "./ir-group-picker.js";
import "./ir-protocol-chip.js";

const GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";

@customElement("ir-group-steps")
export class IrGroupSteps extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public command!: IRCommand;

    /** Typed delays not yet saved, by step index. */
    @state() private _drafts = new Map<number, string>();
    @state() private _picker: { replace: number | null } | null = null;
    @state() private _busy = false;
    @state() private _error: string | null = null;
    /** Bumped after each save: the list is drawn fresh, because the
     *  drag moved its elements behind Lit's back. */
    @state() private _version = 0;

    private _sortable: Sortable | null = null;

    private get _steps(): GroupStepView[] {
        return this.command.group?.steps ?? [];
    }

    updated(): void {
        const list = this.renderRoot.querySelector<HTMLElement>(".steps-list");
        if (list && !this._sortable) {
            this._sortable = Sortable.create(list, {
                handle: ".grip",
                draggable: ".step-block",
                animation: 150,
                onEnd: (e) => {
                    if (e.oldIndex === undefined || e.newIndex === undefined || e.oldIndex === e.newIndex) {
                        return;
                    }
                    void this._save(moveStep(this._steps, e.oldIndex, e.newIndex));
                },
            });
        }
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._sortable?.destroy();
        this._sortable = null;
    }

    private async _save(
        steps: { device_id: string; command_id: string; delay_ms: number }[],
    ): Promise<void> {
        this._busy = true;
        this._error = null;
        try {
            const { device } = await this.api.groupSetSteps(
                this.deviceId,
                this.command.id,
                stepsForSave(steps),
            );
            this._drafts = new Map();
            this.dispatchEvent(
                new CustomEvent("device-updated", { detail: { device }, bubbles: true, composed: true }),
            );
        } catch (err) {
            this._error = this._refusal(err);
        } finally {
            this._busy = false;
            // Sortable moved the DOM; let Lit draw the order it was given.
            this._sortable?.destroy();
            this._sortable = null;
            this._version++;
        }
    }

    private _refusal(err: unknown): string {
        const code = (err as { code?: string })?.code ?? "";
        const key = `group.refused_${code}`;
        const said = t(key);
        return said !== key ? said : (err as Error)?.message ?? String(err);
    }

    private _remove(index: number): void {
        const steps = this._steps.slice();
        steps.splice(index, 1);
        void this._save(steps);
    }

    private _onPick(e: CustomEvent<{ device_id: string; command_id: string }>): void {
        const replace = this._picker?.replace ?? null;
        const steps = this._steps.map((s) => ({ ...s }));
        if (replace !== null) {
            steps[replace] = { ...steps[replace], ...e.detail };
        } else {
            if (steps.length >= GROUP_MAX_STEPS) {
                this._error = t("group.refused_too_many_steps");
                return;
            }
            steps.push({ ...e.detail, delay_ms: GROUP_DELAY_DEFAULT_MS } as GroupStepView);
        }
        void this._save(steps);
    }

    private _onDelayInput(index: number, value: string): void {
        const next = new Map(this._drafts);
        next.set(index, value);
        this._drafts = next;
    }

    private _commitDelay(index: number): void {
        const draft = this._drafts.get(index);
        if (draft === undefined || delayProblem(draft)) return;
        if (Number(draft) === this._steps[index].delay_ms) {
            const next = new Map(this._drafts);
            next.delete(index);
            this._drafts = next;
            return;
        }
        const steps = this._steps.map((s, i) => (i === index ? { ...s, delay_ms: Number(draft) } : s));
        void this._save(steps);
    }

    private _renderTag(step: GroupStepView) {
        if (step.medium === "rf") {
            return html`<span class="band">${bandText(step)}</span>`;
        }
        return step.protocol
            ? html`<ir-protocol-chip .protocol=${step.protocol}></ir-protocol-chip>`
            : nothing;
    }

    private _renderStep(step: GroupStepView, index: number, last: boolean) {
        const draft = this._drafts.get(index);
        const shown = draft ?? String(step.delay_ms);
        const problem = draft !== undefined ? delayProblem(draft) : null;
        return html`<div class="step-block">
            <div class="step ${step.missing ? "missing" : ""}">
                <span class="num">${index + 1}</span>
                <svg class="grip" viewBox="0 0 24 24" aria-label=${t("devdetail.drag")}>
                    <path d=${GRIP}></path>
                </svg>
                <span class="what">
                    ${step.missing
                        ? t("group.step_missing", { command: step.command_name, device: step.device_name })
                        : html`<span class="dev">${step.device_name}</span><span class="sep">/</span><span
                                  >${step.command_name}</span
                              >`}
                </span>
                ${step.missing
                    ? html`<button
                          class="pick"
                          ?disabled=${this._busy}
                          @click=${() => (this._picker = { replace: index })}
                      >
                          ${t("group.pick_again")}
                      </button>`
                    : this._renderTag(step)}
                <button
                    class="x"
                    title=${t("group.remove_step")}
                    aria-label=${t("group.remove_step")}
                    ?disabled=${this._busy}
                    @click=${() => this._remove(index)}
                >
                    ×
                </button>
            </div>
            ${last
                ? nothing
                : html`<div class="wait ${problem ? "bad" : ""}">
                      <span>${t("group.then_wait")}</span>
                      <input
                          type="text"
                          inputmode="numeric"
                          aria-label=${t("group.delay_label")}
                          .value=${shown}
                          ?disabled=${this._busy}
                          @input=${(e: Event) => this._onDelayInput(index, (e.target as HTMLInputElement).value)}
                          @change=${() => this._commitDelay(index)}
                          @keydown=${(e: KeyboardEvent) => {
                              if (e.key === "Enter") this._commitDelay(index);
                          }}
                      />
                      <span>ms</span>
                      <span class="floor">${t("group.floor_hint", { ms: String(GROUP_DELAY_MIN_MS) })}</span>
                      ${problem
                          ? html`<span class="err" role="alert">${t(`group.delay_${problem}`, {
                                ms: String(GROUP_DELAY_MIN_MS),
                            })}</span>`
                          : nothing}
                  </div>`}
        </div>`;
    }

    render() {
        const steps = this._steps;
        const runMs = this.command.group?.run_ms ?? 0;
        return html`
            <div class="steps">
                ${steps.length
                    ? keyed(
                          this._version,
                          html`<div class="steps-list">
                              ${steps.map((s, i) => this._renderStep(s, i, i === steps.length - 1))}
                          </div>`,
                      )
                    : html`<div class="empty">${t("group.no_steps")}</div>`}
                ${this._error ? html`<div class="err-line" role="alert">${this._error}</div>` : nothing}
                <div class="foot">
                    <button
                        class="add"
                        ?disabled=${this._busy || steps.length >= GROUP_MAX_STEPS}
                        @click=${() => (this._picker = { replace: null })}
                    >
                        ${t("group.add_step")}
                    </button>
                    ${steps.length
                        ? html`<span class="total">
                              ${t(this.command.group?.missing ? "group.runs_about_skipping" : "group.runs_about", {
                                  time: aboutSeconds(runMs),
                              })}
                          </span>`
                        : nothing}
                </div>
            </div>
            ${this._picker
                ? html`<ir-group-picker
                      .api=${this.api}
                      .deviceId=${this.deviceId}
                      .groupName=${this.command.name}
                      .steps=${steps}
                      ?replace=${this._picker.replace !== null}
                      @pick=${this._onPick}
                      @closed=${() => (this._picker = null)}
                  ></ir-group-picker>`
                : nothing}
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        .steps {
            margin: 6px 0 4px 44px;
            border-left: 2px solid var(--divider-color);
            padding-left: 12px;
        }
        .step {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 5px 0;
        }
        .num {
            width: 18px;
            text-align: right;
            color: var(--secondary-text-color);
            font-size: 0.75rem;
            flex: none;
        }
        .grip {
            width: 16px;
            height: 16px;
            fill: var(--secondary-text-color);
            opacity: 0.6;
            cursor: grab;
            flex: none;
        }
        .what {
            flex: 1 1 0;
            min-width: 0;
            overflow-wrap: anywhere;
        }
        .dev {
            color: var(--secondary-text-color);
        }
        .sep {
            color: var(--secondary-text-color);
            opacity: 0.5;
            margin: 0 4px;
        }
        .missing .what {
            color: var(--warning-color, #d9a441);
        }
        .band {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            flex: none;
        }
        ir-protocol-chip {
            flex: none;
        }
        .x {
            background: none;
            border: none;
            color: var(--secondary-text-color);
            font-size: 1rem;
            width: 28px;
            height: 26px;
            border-radius: 4px;
            cursor: pointer;
            flex: none;
        }
        .x:hover:not(:disabled) {
            background: var(--secondary-background-color);
            color: var(--primary-text-color);
        }
        .pick,
        .add {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            color: var(--primary-color);
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            flex: none;
        }
        .wait {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            padding: 2px 0 2px 28px;
            color: var(--secondary-text-color);
            font-size: 0.8rem;
        }
        .wait input {
            width: 78px;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 6px;
            font: inherit;
            text-align: right;
        }
        .wait input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .wait.bad input {
            border-color: var(--error-color, #db4437);
        }
        .floor {
            opacity: 0.8;
        }
        .err {
            flex-basis: 100%;
            color: var(--error-color, #db4437);
        }
        .err-line {
            color: var(--error-color, #db4437);
            font-size: 0.8rem;
            padding: 4px 0;
        }
        .empty {
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 6px 0;
        }
        .foot {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            padding: 8px 0 2px;
        }
        .total {
            margin-left: auto;
            color: var(--secondary-text-color);
            font-size: 0.8rem;
        }
        button:disabled {
            opacity: 0.5;
            cursor: default;
        }
        @media (max-width: 450px) {
            .steps {
                margin-left: 6px;
                padding-left: 8px;
            }
            .wait {
                padding-left: 22px;
            }
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-group-steps": IrGroupSteps;
    }
}
