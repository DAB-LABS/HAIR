/**
 * A grouped command, opened (grouped-signals.md).
 *
 * The steps in order, each its own quiet block (the command rows'
 * radius, a shade lighter) with its number in a small circle, its device
 * and command, its protocol chip or band so IR and RF steps tell apart,
 * a grip to drag it, and an x to take it out of this group. The x is not
 * a trash can: the command itself stays, and the row's trash can, which
 * deletes a command for good, sits an inch away.
 *
 * THE DELAY IS A BAND under each step but the last: half a step's height,
 * full width, in the steps' own grey, so the list reads step, band, step.
 * A small clock sits in the grip's column (grip, clock, grip, clock down
 * the left edge), and beside it the value between a minus and a plus:
 * "- 1.5 s +", no word, no box. The keys have no fill of their own; the
 * glyphs carry them, with a hover and a focus ring. Each press moves the
 * delay 100 ms; - greys out at 300 ms, the floor, so nothing it can show
 * is refused, and + at the most. A new step starts at 300 ms. Holding a button repeats, and
 * speeds up after a moment. It counts from the end of the first step's
 * signal. A stored delay off the 100 ms grid shows rounded up, and saves
 * that way the next time it is changed. The change saves once, when the
 * button is let go.
 *
 * A missing step (its command was deleted) shows in amber with its last
 * names and "Pick again". "+ Add step" opens the picker. The run time and "No steps yet"
 * are said once, on the row's own line, so not again here.
 *
 * Changes save as they're made, as a rename or a reorder does: each one goes
 * to `hair/command/group/steps`, and the device as it now is goes up as
 * `device-updated`.
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
    GROUP_DELAY_MAX_MS,
    GROUP_DELAY_MIN_MS,
    GROUP_MAX_STEPS,
    delayOnGrid,
    delayText,
    stepDelay,
    moveStep,
    stepsForSave,
} from "./group-steps.js";
import { bandText } from "./ir-group-picker.js";
import "./ir-group-picker.js";
import "./ir-protocol-chip.js";

const CLOCK =
    "M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z";
const GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";

@customElement("ir-group-steps")
export class IrGroupSteps extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public deviceId!: string;
    @property({ attribute: false }) public command!: IRCommand;

    /** Delays being stepped and not yet saved, by step index. */
    @state() private _drafts = new Map<number, number>();
    /** The held stepper button's repeat. */
    private _repeat: ReturnType<typeof setTimeout> | null = null;
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
        this._stopRepeat();
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

    /** The picker's green button: every staged pick, in order, saved
     *  in one go. */
    private _onAdd(e: CustomEvent<{ picks: { device_id: string; command_id: string }[] }>): void {
        const picks = e.detail.picks;
        if (!picks.length) return;
        if (this._steps.length + picks.length > GROUP_MAX_STEPS) {
            this._error = t("group.refused_too_many_steps");
            return;
        }
        const steps = [
            ...this._steps.map((s) => ({ ...s })),
            ...picks.map((p) => ({ ...p, delay_ms: GROUP_DELAY_DEFAULT_MS }) as GroupStepView),
        ];
        void this._save(steps);
    }

    /** "Pick again" on a missing step: the one pick takes its place. */
    private _onPick(e: CustomEvent<{ device_id: string; command_id: string }>): void {
        const replace = this._picker?.replace ?? null;
        if (replace === null) return;
        const steps = this._steps.map((s) => ({ ...s }));
        steps[replace] = { ...steps[replace], ...e.detail };
        void this._save(steps);
    }

    /** The delay a step shows: its draft while stepping, else its
     *  stored delay on the grid. */
    private _delayOf(index: number): number {
        return this._drafts.get(index) ?? delayOnGrid(this._steps[index].delay_ms);
    }

    private _nudge(index: number, direction: 1 | -1): void {
        const next = new Map(this._drafts);
        next.set(index, stepDelay(this._delayOf(index), direction));
        this._drafts = next;
    }

    /** A pointer press: one step now, then repeats while held, faster
     *  after ten. Saved on release (``_endHold``). */
    private _startHold(e: PointerEvent, index: number, direction: 1 | -1): void {
        if (e.button !== 0) return;
        e.preventDefault();
        this._stopRepeat();
        this._nudge(index, direction);
        let count = 0;
        const tick = (): void => {
            this._nudge(index, direction);
            count += 1;
            this._repeat = setTimeout(tick, count < 10 ? 100 : 40);
        };
        this._repeat = setTimeout(tick, 400);
    }

    private _stopRepeat(): void {
        if (this._repeat !== null) clearTimeout(this._repeat);
        this._repeat = null;
    }

    private _endHold(index: number): void {
        if (this._repeat === null && !this._drafts.has(index)) return;
        this._stopRepeat();
        this._commitDelay(index);
    }

    /** A keyboard press (a click with no pointer): one step, saved. */
    private _keyStep(e: MouseEvent, index: number, direction: 1 | -1): void {
        if (e.detail !== 0) return;
        this._nudge(index, direction);
        this._commitDelay(index);
    }

    private _commitDelay(index: number): void {
        const draft = this._drafts.get(index);
        if (draft === undefined) return;
        if (draft === this._steps[index].delay_ms) {
            const next = new Map(this._drafts);
            next.delete(index);
            this._drafts = next;
            return;
        }
        const steps = this._steps.map((s, i) => (i === index ? { ...s, delay_ms: draft } : s));
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
        const delay = last ? 0 : this._delayOf(index);
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
                : html`<div class="wait" title=${t("group.delay_title")}>
                      <span class="num-space" aria-hidden="true"></span>
                      <svg class="clock" viewBox="0 0 24 24" role="img" aria-label=${t("group.delay_title")}>
                          <path d=${CLOCK}></path>
                      </svg>
                      <span class="stepper">
                          <button
                              aria-label=${t("group.delay_shorter")}
                              title=${t("group.delay_shorter")}
                              ?disabled=${this._busy || delay <= GROUP_DELAY_MIN_MS}
                              @pointerdown=${(e: PointerEvent) => this._startHold(e, index, -1)}
                              @pointerup=${() => this._endHold(index)}
                              @pointerleave=${() => this._endHold(index)}
                              @pointercancel=${() => this._endHold(index)}
                              @click=${(e: MouseEvent) => this._keyStep(e, index, -1)}
                          >
                              −
                          </button>
                          <span class="ms" aria-live="polite">${delayText(delay)}</span>
                          <button
                              aria-label=${t("group.delay_longer")}
                              title=${t("group.delay_longer")}
                              ?disabled=${this._busy || delay >= GROUP_DELAY_MAX_MS}
                              @pointerdown=${(e: PointerEvent) => this._startHold(e, index, 1)}
                              @pointerup=${() => this._endHold(index)}
                              @pointerleave=${() => this._endHold(index)}
                              @pointercancel=${() => this._endHold(index)}
                              @click=${(e: MouseEvent) => this._keyStep(e, index, 1)}
                          >
                              +
                          </button>
                      </span>
                  </div>`}
        </div>`;
    }

    render() {
        const steps = this._steps;
        return html`
            <div class="steps">
                ${steps.length
                    ? keyed(
                          this._version,
                          html`<div class="steps-list">
                              ${steps.map((s, i) => this._renderStep(s, i, i === steps.length - 1))}
                          </div>`,
                      )
                    : nothing}
                ${this._error ? html`<div class="err-line" role="alert">${this._error}</div>` : nothing}
                <div class="foot">
                    <button
                        class="add"
                        ?disabled=${this._busy || steps.length >= GROUP_MAX_STEPS}
                        @click=${() => (this._picker = { replace: null })}
                    >
                        ${t("group.add_step")}
                    </button>
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
                      @add=${this._onAdd}
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
        }
        /* Each step its own block: the command rows' radius, a shade
           lighter than the row it sits in. */
        .step {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 8px;
            border-radius: 4px;
            background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
        }
        /* The step's number in a small circle, tabular figures. */
        .num {
            box-sizing: border-box;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 1px solid var(--divider-color);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: var(--secondary-text-color);
            font-size: 0.7rem;
            font-variant-numeric: tabular-nums;
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
        /* Red on hover: it takes the step out, never the command. */
        .x:hover:not(:disabled) {
            background: color-mix(in srgb, var(--error-color, #db4437) 12%, transparent);
            color: var(--error-color, #db4437);
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
        /* The delay band between two steps: half a step's height, full
           width, the steps' own grey and radius, so the list reads step,
           band, step. Its columns line up with the step's: the number's
           width, then the clock under the grip, then the value under the
           name. */
        .wait {
            display: flex;
            align-items: center;
            gap: 10px;
            height: 20px;
            margin: 3px 0;
            padding: 0 8px;
            border-radius: 4px;
            background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
            color: var(--secondary-text-color);
            font-size: 0.75rem;
        }
        .num-space {
            width: 20px;
            flex: none;
        }
        /* The grip's colour and weight. */
        .clock {
            width: 16px;
            height: 16px;
            flex: none;
            fill: var(--secondary-text-color);
            opacity: 0.6;
        }
        /* - value +: no box, and keys with no fill of their own. */
        .stepper {
            display: inline-flex;
            align-items: center;
            gap: 2px;
        }
        .stepper button {
            width: 20px;
            height: 18px;
            padding: 0;
            border: none;
            border-radius: 3px;
            background: transparent;
            color: var(--primary-text-color);
            font: inherit;
            font-size: 0.9rem;
            line-height: 1;
            cursor: pointer;
            touch-action: manipulation;
            user-select: none;
        }
        .stepper button:hover:not(:disabled) {
            background: color-mix(in srgb, var(--primary-text-color) 12%, transparent);
        }
        .stepper button:focus-visible {
            outline: 2px solid var(--primary-color);
            outline-offset: 0;
        }
        .stepper button:disabled {
            opacity: 0.3;
            cursor: default;
        }
        .stepper .ms {
            min-width: 52px;
            text-align: center;
            color: var(--primary-text-color);
            font-variant-numeric: tabular-nums;
        }
        .err-line {
            color: var(--error-color, #db4437);
            font-size: 0.8rem;
            padding: 4px 0;
        }
        .foot {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            padding: 8px 0 2px;
        }
        button:disabled {
            opacity: 0.5;
            cursor: default;
        }
        @media (max-width: 450px) {
            .steps {
                margin-left: 0;
            }
            .step {
                gap: 8px;
                padding: 6px;
            }
            .wait {
                gap: 8px;
                padding: 0 6px;
            }
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-group-steps": IrGroupSteps;
    }
}
