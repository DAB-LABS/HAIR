/**
 * Shared assigned-commands popover.
 *
 * Rendered when a signal row's Assign button is clicked and one or more
 * HAIR device commands already carry that signal's identity (the
 * zero-assignment case bypasses the popover and opens the Assign dialog
 * directly -- the exact mirror of the Trigger button's v0.5.7 flow).
 * Hosts the "+ new assignment" action plus one row per assignment, each
 * showing "<device> / <command>" with a chevron as the navigation cue.
 * Emits `create-new` and `open-assignment` (detail = the assignment) for
 * the parent to handle; open-assignment navigates to the device card.
 *
 * Read + navigate only: assignments are removed on the device card, not
 * here. The parent owns position (`top`/`left`) and dismiss-on-outside-
 * click / dismiss-on-scroll, mirroring ir-trigger-popover.
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "./decorators.js";
import { t } from "./localize.js";
import { popoverStyles } from "./ir-popover-styles.js";
import type { SignalAssignment } from "./types.js";

const ICON_CHEVRON = "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z";

@customElement("ir-assigned-popover")
export class IrAssignedPopover extends LitElement {
    @property({ attribute: false }) assignments: SignalAssignment[] = [];
    @property({ type: Number }) top = 0;
    @property({ type: Number }) left = 0;

    render() {
        return html`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">${t("popover.assigned_to")}</div>
                <button
                    class="popover-item accent"
                    @click=${() => this._emit("create-new")}
                >
                    <span>${t("popover.new_assignment")}</span>
                </button>
                <div class="popover-divider"></div>
                ${this.assignments.map(
                    (a) => html`
                        <button
                            class="popover-item"
                            title=${t("popover.open_in_devices", { name: a.device_name })}
                            @click=${() => this._emit("open-assignment", a)}
                        >
                            <span class="popover-name"
                                >${a.device_name} / ${a.command_name}</span
                            >
                            <ha-svg-icon
                                class="chevron"
                                .path=${ICON_CHEVRON}
                            ></ha-svg-icon>
                        </button>
                    `,
                )}
            </div>
        `;
    }

    private _emit(kind: string, assignment?: SignalAssignment): void {
        this.dispatchEvent(
            new CustomEvent(kind, {
                detail: assignment,
                bubbles: true,
                composed: true,
            }),
        );
    }

    static styles = [
        popoverStyles,
        css`
            :host {
                display: contents;
            }
            .chevron {
                --mdc-icon-size: 14px;
                color: var(--secondary-text-color);
                flex: none;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-assigned-popover": IrAssignedPopover;
    }
}
