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
 * SELECTION ON THE PILL, HEALTH ON THE DOT (ember, 2026-10-19). HA
 * already knows which emitters are unreachable, and device_manager
 * skips `unavailable` ones at send time. This picker once read the
 * very same state object for the friendly name and threw the rest
 * away; then it showed health only for an assigned emitter, in amber,
 * which read as "attention" rather than "down". Now every chip shows
 * both, selected or not (entity-health.ts decides online):
 *
 *   not assigned, online   -> grey pill, green dot
 *   not assigned, offline  -> grey pill, hollow ember ring
 *   assigned, online       -> green pill, green dot, glow
 *   assigned, offline      -> ember edge and wash, ember ring, no glow
 *
 * The shared healthDotStyles (ir-header-chip-styles.ts) draws the dot
 * and the alarm, so the picker, the header chips, the Listen chip and
 * the Devices tab cards cannot drift apart. An offline emitter stays
 * listed and can still be assigned or removed.
 *
 * The state word is not printed beside the name. The dot is the state,
 * which is what keeps a row of three emitters reading as three things
 * rather than six. The word still reaches anyone who needs it, through
 * the tooltip and the accessible name: "{name}, online, selected".
 * Where it is spoken it is "selected" and not "sending": a chip saying
 * sending on an idle emitter claims a transmission that is not
 * happening.
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
 *
 * It has since moved again, to emitter-options.ts, so it can run under
 * node in tests; it is re-exported here. Each option carries two
 * names: `name`, with a doubled device name said once, is what the
 * chip says, and `fullName`, HA's friendly name as composed, stays in
 * the tooltip.
 *
 * RADIO (RF send round, T2). Radio frequency transmitters are emitters
 * too, and a device may hold both kinds: each command goes only to its
 * own kind. `media` says which kinds the target can use (a radio code:
 * radio only; a new device: both), and with both shown the chips split
 * into an Infrared and a Radio group. With `rfFrequencyHz`, each
 * transmitter is checked against that frequency by the send path's own
 * rule (`hair/rf/transmitters`): one that cannot send it is greyed with
 * the reason and cannot be turned on, though it can still be turned off.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { HairApi } from "./api.js";
import { emitterGroups, getEmitterOptions, type EmitterInfo } from "./emitter-options.js";
import { bandNumber } from "./ir-listen-state.js";
import type { Medium, RfFit } from "./types.js";
import { healthChipClass, healthDotClass, healthPhrase } from "./entity-health.js";
import { healthDotStyles } from "./ir-header-chip-styles.js";

export { emitterGroups, getEmitterOptions, type EmitterInfo };

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

    /** Which kinds of emitter the target can use; null for both. */
    @property({ attribute: false }) public media: Medium[] | null = null;

    /** A radio code's frequency, to check each transmitter against. */
    @property({ attribute: false }) public rfFrequencyHz: number | null = null;

    @state() private _fits = new Map<string, RfFit>();
    private _fitsFor: number | null | undefined = undefined;

    @state() private _didAutoSelect = false;
    @state() private _receiverIds = new Set<string>();
    private _receiversLoaded = false;

    updated(changed: Map<string, unknown>): void {
        super.updated(changed);

        if (changed.has("api") && this.api && !this._receiversLoaded) {
            this._receiversLoaded = true;
            void this._loadReceivers();
        }
        if (this.api && this._fitsFor !== this.rfFrequencyHz) {
            this._fitsFor = this.rfFrequencyHz;
            void this._loadFits();
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

    private async _loadFits(): Promise<void> {
        const asked = this.rfFrequencyHz;
        if (!this.api || !asked) {
            this._fits = new Map();
            return;
        }
        try {
            const items = await this.api.rfTransmitters(asked);
            if (asked !== this.rfFrequencyHz) return;
            this._fits = new Map(
                items.filter((it) => it.fit).map((it) => [it.entity_id, it.fit as RfFit]),
            );
        } catch {
            this._fits = new Map();
        }
    }

    /** The emitters the target can use, of the media it takes. */
    private _getEmitters(): EmitterInfo[] {
        return emitterGroups(
            getEmitterOptions(this.hass, this._receiverIds, this.excludeEntityIds),
            this.media,
        ).flatMap((group) => group.items);
    }

    /** Why a transmitter cannot send the code's frequency, or how it
     *  will; empty when it simply can. */
    private _fitNote(em: EmitterInfo): { blocked: boolean; note: string } {
        const fit = em.medium === "rf" ? this._fits.get(em.entity_id) : undefined;
        if (!fit || !this.rfFrequencyHz) return { blocked: false, note: "" };
        if (fit.ok) {
            return fit.substituted && fit.send_hz
                ? { blocked: false, note: t("picker.fit_substituted", { band: bandNumber(fit.send_hz) }) }
                : { blocked: false, note: "" };
        }
        if (fit.code === "no_ranges") return { blocked: true, note: t("picker.fit_no_ranges") };
        return { blocked: true, note: t("picker.fit_unsupported", { band: bandNumber(this.rfFrequencyHz) }) };
    }

    /**
     * One control where there were two. Adding used to mean choosing
     * from a dropdown and removing used to mean hitting an x on a chip;
     * both were the same question asked of the same list.
     */
    private _toggle(entityId: string, blocked = false): void {
        if (this.disabled) return;
        // A transmitter that cannot send the code is never turned on; one
        // already chosen can still be turned off.
        if (blocked && !this.value.includes(entityId)) return;
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
        const groups = emitterGroups(
            getEmitterOptions(this.hass, this._receiverIds, this.excludeEntityIds),
            this.media,
        );
        const onlyRf = this.media?.length === 1 && this.media[0] === "rf";
        const label = onlyRf
            ? t("picker.transmitters_label")
            : this.media?.length === 1 || !groups.some((g) => g.medium === "rf")
              ? t("picker.emitters_label")
              : t("picker.both_label");
        if (groups.length === 0) {
            return html`<label>${label}</label>
                <div class="chips">
                    <span class="no-emitters"
                        >${onlyRf ? t("picker.no_transmitters") : t("picker.no_emitters")}</span
                    >
                </div>`;
        }
        // One medium: one row of chips, as before. Both: a small heading
        // over each group.
        return html`
            <label>${label}</label>
            ${groups.length === 1
                ? html`<div class="chips">${groups[0].items.map((em) => this._renderChip(em))}</div>`
                : groups.map(
                      (group) => html`<div class="group">
                          <span class="group-name"
                              >${t(group.medium === "rf" ? "picker.group_rf" : "picker.group_ir")}</span
                          >
                          <div class="chips">${group.items.map((em) => this._renderChip(em))}</div>
                      </div>`,
                  )}
        `;
    }

    private _renderChip(em: EmitterInfo) {
        const on = this.value.includes(em.entity_id);
        const cls = healthChipClass(on, em.available);
        const word = healthPhrase(em.available, on, t);
        const { blocked, note } = this._fitNote(em);
        const said = note ? `${word}, ${note}` : word;
        // The dot carries the state and the name carries itself. A word
        // spelled out beside every chip turned a row of three into a row
        // of six things to read, which is the opposite of what the
        // chip row is for. The word still reaches anyone who needs it:
        // the tooltip and the accessible name both say it.
        // The chip says the name once (entity-names.ts); the tooltip
        // keeps HA's full friendly name, then the entity id:
        // "{full name}, online, selected · {entity id}".
        return html`
            <button
                class="em ${cls} ${blocked ? "nofit" : ""}"
                role="switch"
                aria-checked=${on ? "true" : "false"}
                aria-disabled=${blocked && !on ? "true" : "false"}
                aria-label="${em.name}, ${said}"
                ?disabled=${this.disabled}
                title="${em.fullName}, ${said}${em.fullName === em.entity_id ? "" : ` · ${em.entity_id}`}"
                @click=${() => this._toggle(em.entity_id, blocked)}
            >
                <span class="dot ${healthDotClass(em.available)}"></span>
                <span class="em-name">${em.name}</span>
            </button>
        `;
    }

    static styles = [css`
        :host {
            display: block;
            /* The offline ring, one pixel wider than this picker's
               7px dot (healthDotStyles). */
            --hair-ring: 8px;
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
        /* SELECTED. The pill takes the green; the dot is health and
           comes from healthDotStyles, loaded after this block. */
        .em.on {
            border-color: rgba(79, 158, 90, 0.5);
            background: rgba(79, 158, 90, 0.12);
            color: var(--primary-text-color);
        }
        /* Both kinds shown: a quiet heading over each group. */
        .group + .group {
            margin-top: 8px;
        }
        .group-name {
            display: block;
            font-size: 0.66rem;
            color: var(--secondary-text-color);
            margin-bottom: 3px;
        }
        /* A transmitter that cannot send this code's frequency. */
        .em.nofit:not(.on) {
            opacity: 0.45;
            cursor: not-allowed;
            border-style: dashed;
        }
        .no-emitters {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `, healthDotStyles];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-emitter-picker": IrEmitterPicker;
    }
}
