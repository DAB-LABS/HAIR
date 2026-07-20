/**
 * Shared trigger-picker popover.
 *
 * Rendered when a signal row's Trigger button is clicked and one or more
 * triggers already bind that signal's fingerprint (the zero-trigger case
 * bypasses the popover and opens the Create dialog directly). Hosts the
 * "+ new trigger" action plus one row per existing trigger, each showing its
 * receiver scope. Emits `create-new` and `edit-trigger` (detail = the
 * trigger) for the parent to handle.
 *
 * The parent owns position (`top`/`left`) and dismiss-on-outside-click /
 * dismiss-on-scroll, mirroring the action-popover pattern in
 * ir-device-detail.ts.
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "./decorators.js";
import { t } from "./localize.js";
import { popoverStyles } from "./ir-popover-styles.js";
import type { IRTrigger, ReceiverInfo } from "./types.js";

@customElement("ir-trigger-popover")
export class IrTriggerPopover extends LitElement {
    @property({ attribute: false }) triggers: IRTrigger[] = [];
    @property({ attribute: false }) receivers: ReceiverInfo[] = [];
    @property({ type: Number }) top = 0;
    @property({ type: Number }) left = 0;

    render() {
        return html`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">${t("popover.triggers")}</div>
                <button
                    class="popover-item accent"
                    @click=${() => this._emit("create-new")}
                >
                    <span>${t("popover.new_trigger")}</span>
                </button>
                <div class="popover-divider"></div>
                ${this.triggers.map(
                    (trig) => html`
                        <button
                            class="popover-item"
                            @click=${() => this._emit("edit-trigger", trig)}
                        >
                            <span class="popover-row">
                                <span class="popover-name">${trig.name}</span>
                                <span class="popover-scope"
                                    >${this._renderScope(trig)}</span
                                >
                            </span>
                        </button>
                    `,
                )}
            </div>
        `;
    }

    private _renderScope(trig: IRTrigger): string {
        const ids = trig.receiver_entity_ids ?? [];
        if (ids.length === 0) return t("popover.any_receiver");
        if (ids.length === 1) return this._friendly(ids[0]);
        return t("popover.n_more", {
            name: this._friendly(ids[0]),
            count: ids.length - 1,
        });
    }

    private _friendly(entityId: string): string {
        const match = this.receivers.find((r) => r.entity_id === entityId);
        return match?.name ?? entityId;
    }

    private _emit(kind: string, trigger?: IRTrigger): void {
        this.dispatchEvent(
            new CustomEvent(kind, {
                detail: trigger,
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
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-trigger-popover": IrTriggerPopover;
    }
}
