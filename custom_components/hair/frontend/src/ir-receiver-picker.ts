/**
 * Reusable multi-receiver picker: a label and a row of toggle chips.
 *
 * Converted in place to the ir-emitter-picker.ts toggle-chip pattern
 * (add-popups-signpost-2-coding-plan.md section 2, ruled 2026-08-13
 * then reversed to in-place-everywhere in section 10 -- "We are going
 * to replace the receiver picker in all the places, including its
 * current place... replace the existing one in place and then use it
 * everywhere"). Every consumer inherits the new rendering automatically
 * since the public contract (`.api`, `.value`, `disabled`, the
 * `receivers-changed` event with `detail: { value: string[] }`) is
 * unchanged -- as of this conversion that's exactly one consumer,
 * ir-trigger-dialog.ts (Track 0's 2026-08-13 consumer sweep), plus the
 * new Add Trigger Remote dialog's footer landing in Track 3.
 *
 * Replaces the old ADD-via-dropdown / REMOVE-via-chip-x model (selected
 * receivers shown as chips, unselected ones in a <select>) with the
 * emitter picker's own: every known receiver always renders as a
 * toggle chip, default OFF/grey, click to turn ON/green. No dropdown,
 * no add/remove-x, no "Default all receivers" copy -- the empty,
 * all-grey state IS the explanation, same as an emitter picker with
 * nothing lit needs no caption.
 *
 * Deliberately does NOT reuse ir-emitter-picker's three-state
 * (on/down/off) treatment: the ruling only ever describes ON/OFF for
 * receivers, and ReceiverInfo carries no availability flag to key a
 * third state on (unlike emitters, whose availability comes off
 * `hass.states`). Two states, not three.
 *
 * Stored semantics are unchanged: zero chips selected still serializes
 * as empty/unscoped ("any receiver"), so a remote created with nothing
 * clicked on keeps hearing new receivers added later, same as before.
 * Unlike the emitter picker there is still NO auto-select -- leaving
 * the field empty is the meaningful default, not a first-render
 * convenience fill.
 *
 * Usage:
 *   <ir-receiver-picker
 *       .api=${this.api}
 *       .value=${["infrared.garage_receiver"]}
 *       @receivers-changed=${(e) => this._ids = e.detail.value}
 *   ></ir-receiver-picker>
 *
 * Fires `receivers-changed` with detail: { value: string[] }
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { HairApi } from "./api.js";
import type { ReceiverInfo } from "./types.js";

@customElement("ir-receiver-picker")
export class IrReceiverPicker extends LitElement {
    /** HAIR API client. Required -- the receiver list comes from it. */
    @property({ attribute: false }) public api?: HairApi;

    /** Currently selected receiver entity IDs. */
    @property({ attribute: false }) public value: string[] = [];

    /** Disable all interactions. */
    @property({ type: Boolean }) public disabled = false;

    @state() private _receivers: ReceiverInfo[] = [];
    private _receiversLoaded = false;

    updated(changed: Map<string, unknown>): void {
        super.updated(changed);
        if (changed.has("api") && this.api && !this._receiversLoaded) {
            this._receiversLoaded = true;
            void this._loadReceivers();
        }
    }

    private async _loadReceivers(): Promise<void> {
        if (!this.api) return;
        try {
            this._receivers = await this.api.listReceivers();
        } catch {
            // Pre-2026.6 HA versions don't expose receivers; treat as empty.
            this._receivers = [];
        }
    }

    /** One control where there were two (mirrors ir-emitter-picker.ts's
     *  own note): a chip's on state IS the selection, there is no
     *  separate add-then-remove gesture anymore. */
    private _toggle(entityId: string): void {
        if (this.disabled) return;
        this._fireChange(
            this.value.includes(entityId)
                ? this.value.filter((id) => id !== entityId)
                : [...this.value, entityId],
        );
    }

    private _fireChange(newValue: string[]): void {
        this.value = newValue;
        this.dispatchEvent(
            new CustomEvent("receivers-changed", {
                detail: { value: newValue },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        return html`
            <label>${t("picker.receivers_label")}</label>
            <div class="chips">
                ${this._receivers.length === 0
                    ? html`<span class="no-receivers"
                          >${t("picker.no_receivers")}</span
                      >`
                    : this._receivers.map((r) => this._renderChip(r))}
            </div>
        `;
    }

    private _renderChip(r: ReceiverInfo) {
        const on = this.value.includes(r.entity_id);
        const word = on ? t("picker.state_on") : t("picker.state_off");
        return html`
            <button
                class="rx ${on ? "on" : ""}"
                role="switch"
                aria-checked=${on ? "true" : "false"}
                aria-label="${r.name}, ${word}"
                ?disabled=${this.disabled}
                title="${r.entity_id} · ${word}"
                @click=${() => this._toggle(r.entity_id)}
            >
                <span class="dot"></span>
                <span class="rx-name">${r.name}</span>
            </button>
        `;
    }

    static styles = css`
        :host {
            display: var(--picker-host-display, block);
            align-items: var(--picker-host-align, flex-start);
            gap: var(--picker-host-gap, 0);
        }
        label {
            display: var(--picker-label-display, block);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--secondary-text-color);
            margin-bottom: var(--picker-label-margin-bottom, 5px);
            flex-shrink: 0;
        }
        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            padding-top: 2px;
            flex: 1 1 auto;
            min-width: 0;
        }
        .rx {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 4px 11px 4px 9px;
            border: 1px solid var(--divider-color);
            border-radius: 14px;
            background: none;
            font-family: inherit;
            font-size: 12px;
            color: var(--secondary-text-color);
            cursor: pointer;
            transition: border-color 140ms ease, background 140ms ease,
                color 140ms ease;
        }
        .rx:hover:not(:disabled) {
            border-color: var(--secondary-text-color);
        }
        .rx:disabled {
            cursor: default;
            opacity: 0.55;
        }
        .rx-name {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }
        .dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #4d5359;
            flex: none;
        }
        .rx.on {
            border-color: rgba(79, 158, 90, 0.5);
            background: rgba(79, 158, 90, 0.12);
            color: var(--primary-text-color);
        }
        .rx.on .dot {
            background: #6cbf78;
            box-shadow: 0 0 5px rgba(108, 191, 120, 0.6);
        }
        .no-receivers {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-receiver-picker": IrReceiverPicker;
    }
}
