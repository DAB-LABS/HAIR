/**
 * Reusable multi-emitter picker: a label and a row of toggle chips.
 *
 * THE CHIPS ARE NOT A SELECTION. Every assigned emitter fires on every
 * send -- device_manager.async_send_command broadcasts to all of them,
 * staggered by tx_gate, and succeeds if at least one lands. They are
 * redundancy, not a choice between blasters. The old dropdown-plus-
 * removable-chips shape said the opposite: it read as "pick one, then
 * maybe another", and it spent a chip to announce what it had just
 * added. Every emitter renders now, and being assigned is simply the
 * chip's on state.
 *
 * THREE STATES, and the third is the point. HA already knows which
 * emitters are unreachable, and device_manager skips `unavailable` and
 * `unknown` ones at send time. This picker was reading the very same
 * state object for the friendly name and throwing the rest away, so a
 * device could sit there listing a blaster that had been unplugged for
 * a week with nothing to show for it.
 *
 *   assigned + reachable  -> green border, lit dot,  "On"
 *   not assigned          -> divider border, dead dot, "Off"
 *   assigned + unreachable-> amber border, flat dot, "Unavailable"
 *
 * The state word is not printed beside the name. The dot is the state,
 * which is what keeps a row of three emitters reading as three things
 * rather than six. The word still reaches anyone who needs it, through
 * the tooltip and the accessible name. Where it is spoken it is "On"
 * and not "Sending": a chip reading Sending on an idle emitter claims
 * a transmission that is not happening.
 *
 * Usage:
 *   <ir-emitter-picker
 *       .hass=${this.hass}
 *       .value=${["infrared.living_room"]}
 *       @emitters-changed=${(e) => this._ids = e.detail.value}
 *   ></ir-emitter-picker>
 *
 * Fires `emitters-changed` with detail: { value: string[] }. The
 * contract is unchanged from the dropdown era, which is why
 * ir-assign-signal-dialog, ir-promote-dialog, and (add-popups
 * signpost 2) ir-add-controlled-device-dialog inherited this for
 * free.
 *
 * `getEmitterOptions()` (signpost 3, Track 1 item 5): the entity-
 * discovery half of `_getEmitters()` below, pulled out to a standalone
 * exported function so ir-device-detail.ts's new header chip group
 * (ir-header-chip-group.ts) can build the SAME on/down/off-eligible
 * emitter list this component shows, without a second, drifting copy
 * of the `infrared.*` / receiver-exclusion / `hair_observer` filter.
 * The class method below is now a thin delegate to it -- behavior is
 * unchanged, only where the logic lives moved.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { HairApi } from "./api.js";

export interface EmitterInfo {
    entity_id: string;
    name: string;
    /** HA's own verdict. device_manager.py skips these at send time and
     * the panel never used to say so. */
    available: boolean;
}

/** The one state that means "this entity is not answering".
 * "unknown" is deliberately NOT here: an emitter's state is its
 * last-send timestamp, unknown until the first send, so a brand-new
 * blaster in "unknown" is unproven, not down -- painting it amber
 * told every fresh install its hardware was broken (GH #83). */
const DEAD_STATES = new Set(["unavailable"]);

/** Every `infrared.*` entity that can be assigned as an emitter: not a
 *  known receiver, not flagged `hair_observer`, not in `excludeIds`.
 *  `receiverIds` is the caller's job to supply (this function does no
 *  fetching of its own -- ir-emitter-picker.ts loads its own via
 *  `api.listReceivers()`; ir-device-detail.ts reuses ir-device-list.ts's
 *  already-loaded receivers list instead of a second fetch). */
export function getEmitterOptions(
    hass: any,
    receiverIds: Set<string>,
    excludeEntityIds: string[] = [],
): EmitterInfo[] {
    const states = (hass?.states ?? {}) as Record<
        string,
        {
            entity_id: string;
            state?: string;
            attributes: { friendly_name?: string; hair_observer?: boolean };
        }
    >;
    const excludeSet = new Set(excludeEntityIds);
    const emitters: EmitterInfo[] = [];
    for (const [entityId, st] of Object.entries(states)) {
        if (
            entityId.startsWith("infrared.") &&
            !excludeSet.has(entityId) &&
            !receiverIds.has(entityId) &&
            !st.attributes.hair_observer
        ) {
            emitters.push({
                entity_id: entityId,
                name: st.attributes.friendly_name ?? entityId,
                available: !DEAD_STATES.has(st.state ?? ""),
            });
        }
    }
    return emitters;
}

@customElement("ir-emitter-picker")
export class IrEmitterPicker extends LitElement {
    @property({ attribute: false }) public hass?: any;

    /**
     * HAIR API client. When provided, the picker fetches the list of
     * native ``InfraredReceiverEntity`` instances and excludes them from
     * the chips -- so RX-only entities can't be picked as an emitter
     * by mistake. Optional for backward compatibility.
     */
    @property({ attribute: false }) public api?: HairApi;

    /** Currently selected emitter entity IDs. */
    @property({ attribute: false }) public value: string[] = [];

    /** Disable all interactions. */
    @property({ type: Boolean }) public disabled = false;

    /** Entity IDs to exclude entirely (e.g. extra hand-picked exclusions). */
    @property({ attribute: false }) public excludeEntityIds: string[] = [];

    @state() private _didAutoSelect = false;
    @state() private _receiverIds = new Set<string>();
    private _receiversLoaded = false;

    updated(changed: Map<string, unknown>): void {
        super.updated(changed);

        if (changed.has("api") && this.api && !this._receiversLoaded) {
            this._receiversLoaded = true;
            void this._loadReceivers();
        }

        // First-render decision. Two cases:
        //   1. ``value`` is already non-empty (a pre-saved device was passed
        //      in) -- treat that as "the user has already made a choice"
        //      and never auto-fill again.
        //   2. ``value`` is empty and exactly one emitter is available --
        //      auto-pick it as a convenience for first-time setup.
        // Either way, once ``_didAutoSelect`` flips true, we leave the
        // picker alone. Turning the last chip off then leaves the field
        // empty, instead of the auto-fill snapping it back to the only
        // option (the bug this guard fixes).
        if (!this._didAutoSelect) {
            if (this.value.length > 0) {
                this._didAutoSelect = true;
            } else {
                const emitters = this._getEmitters();
                if (emitters.length === 1) {
                    this._didAutoSelect = true;
                    this._fireChange([emitters[0].entity_id]);
                }
            }
        }
    }

    private async _loadReceivers(): Promise<void> {
        if (!this.api) return;
        try {
            const receivers = await this.api.listReceivers();
            this._receiverIds = new Set(receivers.map((r) => r.entity_id));
        } catch {
            // Pre-2026.6 HA versions don't expose receivers; treat as empty.
            this._receiverIds = new Set();
        }
    }

    private _getEmitters(): EmitterInfo[] {
        return getEmitterOptions(this.hass, this._receiverIds, this.excludeEntityIds);
    }

    /**
     * One control where there were two. Adding used to mean choosing
     * from a dropdown and removing used to mean hitting an x on a chip;
     * both were the same question asked of the same list.
     */
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
            new CustomEvent("emitters-changed", {
                detail: { value: newValue },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const emitters = this._getEmitters();
        return html`
            <label>${t("picker.emitters_label")}</label>
            <div class="chips">
                ${emitters.length === 0
                    ? html`<span class="no-emitters"
                          >${t("picker.no_emitters")}</span
                      >`
                    : emitters.map((em) => this._renderChip(em))}
            </div>
        `;
    }

    private _renderChip(em: EmitterInfo) {
        const on = this.value.includes(em.entity_id);
        // Only an emitter being ASKED to send has anything to say about
        // being unreachable. An unassigned one that happens to be down
        // is simply off, because nothing is expected of it.
        const down = on && !em.available;
        const cls = down ? "down" : on ? "on" : "";
        const word = down
            ? t("picker.state_unavailable")
            : on
              ? t("picker.state_on")
              : t("picker.state_off");
        // The dot carries the state and the name carries itself. A word
        // spelled out beside every chip turned a row of three into a row
        // of six things to read, which is the opposite of what the
        // chip row is for. The word still reaches anyone who needs it:
        // the tooltip and the accessible name both say it.
        return html`
            <button
                class="em ${cls}"
                role="switch"
                aria-checked=${on ? "true" : "false"}
                aria-label="${em.name}, ${word}"
                ?disabled=${this.disabled}
                title="${em.entity_id} · ${word}"
                @click=${() => this._toggle(em.entity_id)}
            >
                <span class="dot"></span>
                <span class="em-name">${em.name}</span>
            </button>
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        /* Comp L1: the label sits ABOVE its control rather than in a
           fixed gutter beside it. Small, quiet and out of the way, so
           the chips are what the row is made of. */
        label {
            display: var(--picker-label-display, block);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--secondary-text-color);
            margin-bottom: 5px;
        }
        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            padding-top: 2px;
        }
        .em {
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
        .em:hover:not(:disabled) {
            border-color: var(--secondary-text-color);
        }
        .em:disabled {
            cursor: default;
            opacity: 0.55;
        }
        .em-name {
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
        /* ON. Green, and the dot glows, because this one is live. */
        .em.on {
            border-color: rgba(79, 158, 90, 0.5);
            background: rgba(79, 158, 90, 0.12);
            color: var(--primary-text-color);
        }
        .em.on .dot {
            background: #6cbf78;
            box-shadow: 0 0 5px rgba(108, 191, 120, 0.6);
        }
        /* ASSIGNED BUT DOWN. Amber edge and a warm name, and the dot
           does NOT glow: the glow is the panel's mark for something
           that is working, and this is the one case where the device is
           asking an emitter to fire and HA will skip it. */
        .em.down {
            border-color: rgba(217, 164, 65, 0.45);
            color: #e8dcc2;
        }
        .em.down .dot {
            background: #d9a441;
            box-shadow: none;
        }
        .no-emitters {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-emitter-picker": IrEmitterPicker;
    }
}
