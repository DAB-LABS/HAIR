/**
 * Device detail view: editable header (name, type, emitter),
 * read-only hardware cards (TX / RX), flat command list.
 */
import { LitElement, html, css, nothing } from "lit";
import { actionChipStyles } from "./ir-action-chip-styles";
import { customElement, property, state } from "./decorators.js";
import { t, tv } from "./localize.js";
import { keyed } from "lit/directives/keyed.js";
import { repeat } from "lit/directives/repeat.js";
import Sortable from "sortablejs";
import "./ir-command-row.js";

/** Action-badge sizing constants (owner ruling, 2026-08-01; box model
 *  REWORKED 2026-08-11, fourth bench pass -- the fixed-width reservation
 *  these drive was reinstated in ir-command-row.ts after commit 2 dropped
 *  it along with the old bordered .badge-btn. See _measureActionBadges
 *  for what changed: the new link-A label has no padding or border to
 *  account for, and no letter-spacing, but DOES have an arrow glyph
 *  ("-> ") that the old plain-text badge never rendered.
 *  The cap is the width the badge is allowed to reserve before its label
 *  starts stepping down a font tier. 96px clears fan (90px) and
 *  media_player (93px) at full size, so the common device types never
 *  shrink at all; light is the one type that steps down. */
const ACTION_BADGE_CAP_PX = 96;
const ACTION_BADGE_FONT_LADDER = [10.5, 9.5, 9];
const ACTION_BADGE_WEIGHT = 500;
const ACTION_BADGE_TRACKING = 0; // the link-A label carries no letter-spacing, unlike the old uppercase badge button's 0.03em
const ACTION_ARROW_CHAR = "→"; // matches .map-arrow's glyph in ir-command-row.ts
const ACTION_ARROW_GAP_PX = 3; // matches .action-visible/.action-sizer's flex gap there
import "./ir-capture-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-save-perfect-dialog.js";
import "./ir-save-route-dialog.js";
import "./ir-save-new-dialog.js";
import "./ir-save-update-dialog.js";
import { getEmitterOptions } from "./ir-emitter-picker.js";
import "./ir-header-chip-group.js";
import type { HeaderChipRow } from "./ir-header-chip-group.js";
import { GREEN_PEAK, ORIGIN_COLORS } from "./ir-origin-colors.js";
import { PINNING_UI_ENABLED } from "./ir-pin-flag.js";
import type { SaveRoute } from "./ir-save-route-dialog.js";
import "./ir-matrix-card.js";
import type { MatrixCardPick } from "./ir-matrix-card.js";
import "./ir-signal-editor.js";
import "./ir-trigger-dialog.js";
import "./ir-trigger-popover.js";
import { popoverStyles } from "./ir-popover-styles.js";
// The house wig, from images/wig.svg. Same glyph the closet wears,
// because this button is the door into it (FR5).
import { ICON_WIG } from "./ir-wigs.js";
// Device Settings (0.9.8): the mustache gear settings button, from
// images/mustache-gear.svg -- see ir-icons.ts for the full ruling on
// why it renders as an inline <svg> rather than through <ha-svg-icon>.
import {
    ICON_SETTINGS,
    SETTINGS_VIEWBOX,
    settingsButtonStyles,
    exitToEntityButtonStyles,
    renderExitToEntityBtn,
} from "./ir-icons.js";
import "./ir-device-settings-dialog.js";
import type { HairApi } from "./api.js";
import "./ir-tangle-section.js";
import type {
    ActionOption,
    IRCommand,
    IRDevice,
    IRTrigger,
    DeviceTypeId,
    ReceiverInfo,
    SavePlan,
    TriggerRemoteInfo,
} from "./types.js";

// MDI: drag (six-dot grip)
const ICON_GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";

/** Debounce delay (ms) between drag end and WS save. */
const REORDER_DEBOUNCE_MS = 500;

/**
 * Width of the Device detail header's label column, in px (punch list
 * item 9, `header-pin-layout-handoff.md`). Both rows on this header pass
 * the same value to ir-header-chip-group, which is what puts
 * "EMITTERS:" and "PINNED:" on one colon line and keeps a wrapped row of
 * chips under the chips column instead of back under the label.
 *
 * DERIVED, not arbitrary: sized to "EMITTERS:", 9 characters, the
 * longest label this column carries in any state. It is narrower than
 * the Remote header's 80px because that header's own longest label is
 * "RECEIVERS:" -- the two numbers are measured per surface, not shared.
 * Re-measure before adding a longer label here.
 */
const DEVICE_HDR_LABEL_W = 76;

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "media_player", label: "Media Player" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "light", label: "Light" },
    { value: "switch", label: "Switch" },
    { value: "screen", label: "Screen / Shade" },
    { value: "other", label: "Other" },
];

@customElement("ir-device-detail")
export class IrDeviceDetail extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public device!: IRDevice;
    /** ir-device-list.ts's own already-loaded receivers list, reused
     *  so the header Emitters group can exclude RX-only entities the
     *  same way ir-emitter-picker.ts's .api-driven fetch does, without
     *  a second network call (signpost 3, Track 1 item 5). */
    @property({ attribute: false }) public receivers: ReceiverInfo[] = [];
    /** Candidate list for the gated Pin: group -- existing Trigger
     *  Remotes, pinned items on a Device ARE Remotes. Unused while
     *  PINNING_UI_ENABLED is false. */
    @property({ attribute: false }) public triggerRemotes: TriggerRemoteInfo[] = [];

    @state() private _busy = false;
    @state() private _captureName: string | null = null;
    @state() private _toast: string | null = null;
    /** Second Fitting v3 punch list item 6: the window itself opens on
     * this alone, synchronously, the moment SAVE TO CLOSET is clicked
     * -- it no longer waits on the plan fetch below. False closes the
     * whole save flow. */
    @state() private _saveRouteOpen = false;
    /** Second Fitting v3: the decision window's own plan, fetched once
     * when SAVE TO CLOSET is clicked and handed straight into whatever
     * dialog the chosen route opens next -- neither the window nor the
     * dialog it routes to fetches a second copy. Streams in after the
     * window is already open (item 6); null until it lands. */
    @state() private _saveRoutePlan: SavePlan | null = null;
    /** Which route the window's own buttons chose. VALIDATE FOR
     * PERFECT FIT still opens the pre-v3 dialog until Commit 5 gives
     * it a stripped, purpose-built one of its own -- see the Commit 3
     * and 4 commit messages for the sequencing note. */
    @state() private _saveRoute: SaveRoute | null = null;
    /** Bench fix (2026-08-07): set by _onWigSaved, consumed by
     * _closeSaveFlow -- see either for the full story. */
    @state() private _pendingWigSaved = false;
    @state() private _commandToDelete: IRCommand | null = null;
    @state() private _editCommand: IRCommand | null = null;

    // Action mapping
    @state() private _actionOptions: ActionOption[] = [];
    /** Reserved-width sizing for the action badge. Derived, not state:
     *  recomputed during render whenever the set of labels in play changes,
     *  and memoized on that set. See _actionBadgeMetrics. */
    private _actionBadge: {
        sizerLabel: string;
        sizerFontPx: number;
        fontFor: Record<string, number>;
    } | null = null;
    private _actionBadgeKey = "";
    @state() private _mappingCommandName: string | null = null;
    @state() private _popoverTop = 0;
    @state() private _popoverLeft = 0;
    // Custom action entry (owner ruling, GH bench 2026-07-19): free-form
    // action key typed into the popover -- the update-mapping endpoint
    // accepts any string, and the thermostat consumes any temp_N key, so
    // changing "temp_28" to "temp_30" no longer requires delete+reimport.
    // A key outside the known vocabulary stores but drives no entity;
    // the ACTIONS badge renders it as typed, so a typo stays visible.
    @state() private _customActionOpen = false;
    @state() private _customActionValue = "";
    private _dismissHandler: ((e: MouseEvent) => void) | null = null;

    // Inline name editing
    @state() private _editingName = false;
    @state() private _draftName = "";

    // Device Settings (0.9.8): the settings button in the meta row.
    // Universal across every device type (Track 1 item 6, coding plan
    // item 0.2) -- settingsSections(device) still decides which
    // power/climate sections show INSIDE the dialog, but no longer
    // gates the button's own visibility; the dialog always has the
    // convert/Duplicate/Delete rows even when both sections are empty.
    @state() private _settingsOpen = false;

    // Triggers
    @state() private _triggers: IRTrigger[] = [];
    @state() private _triggerCommand: IRCommand | null = null;
    @state() private _triggerEdit: IRTrigger | null = null;
    @state() private _confirmDeleteTriggerId: string | null = null;
    // Trigger picker popover (v0.5.7): shown when a command already has 1+
    // triggers; zero-trigger click opens the Create dialog directly.
    @state() private _triggerPopover: {
        command: IRCommand;
        top: number;
        left: number;
    } | null = null;
    @state() private _receivers: ReceiverInfo[] = [];

    // Command reorder (SortableJS lifecycle)
    private _sortable: Sortable | null = null;
    private _pendingReorderTimeout: number | null = null;
    // Incremented after each drop to force a fresh repeat() instance via
    // the keyed() directive. SortableJS's mid-drag DOM mutations corrupt
    // repeat()'s internal positional cache; reverting the DOM and
    // reassigning the array isn't enough to recover. A keyed rebuild
    // gives Lit a clean cache so the new commands order renders correctly.
    @state() private _commandsListVersion = 0;

    // ---------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------

    /** Resolve emitter entity to friendly name, falling back to entity_id. */
    private _emitterName(entityId: string): string {
        const stateObj = this.hass?.states?.[entityId];
        return stateObj?.attributes?.friendly_name ?? entityId;
    }

    /** Resolve a device-registry ID to its display name. */
    private _deviceRegistryName(deviceId: string): string {
        const deviceEntry = this.hass?.devices?.[deviceId];
        return deviceEntry?.name_by_user ?? deviceEntry?.name ?? deviceId;
    }

    /** Get the config_entry_id for a device-registry device. */
    private _deviceConfigEntryId(deviceId: string): string | null {
        const deviceEntry = this.hass?.devices?.[deviceId];
        if (!deviceEntry) return null;
        const entries: string[] = deviceEntry.config_entries ?? [];
        return entries[0] ?? null;
    }

    /** Get the integration domain for a config entry. */
    private _configEntryDomain(configEntryId: string): string | null {
        const entry = this.hass?.config_entries?.entries?.[configEntryId];
        return entry?.domain ?? null;
    }

    /** Build integration page URL for a config entry. */
    private _integrationUrl(configEntryId: string | null): string | null {
        if (!configEntryId) return null;
        const domain = this._configEntryDomain(configEntryId);
        if (domain) {
            return `/config/integrations/integration/${domain}`;
        }
        return null;
    }

    /** Build integration page URL for an entity. */
    private _entityIntegrationUrl(entityId: string): string | null {
        // Entity domain is the part before the first dot
        const domain = entityId.split(".")[0];
        // Try to find the config entry via the entity registry
        const entityReg = this.hass?.entities?.[entityId];
        if (entityReg?.config_entry_id) {
            return this._integrationUrl(entityReg.config_entry_id);
        }
        // Fallback: use the entity's platform domain
        if (entityReg?.platform) {
            return `/config/integrations/integration/${entityReg.platform}`;
        }
        return `/config/integrations/integration/${domain}`;
    }

    // ---------------------------------------------------------------
    // Data
    // ---------------------------------------------------------------

    /** Refetches the device and tells the world it changed.
     * Called directly by every other mutating action in this file;
     * the "wig-saved" handler below no longer calls this immediately
     * -- see _onWigSaved and _closeSaveFlow for why. */
    private async _refresh() {
        this.device = await this.api.getDevice(this.device.id);
        this.dispatchEvent(
            new CustomEvent("device-changed", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** Bench fix (2026-08-07): the "wig-saved" handler for all three
     * save dialogs used to call _refresh() straight away. That
     * dispatched "device-changed" the instant the server save
     * resolved -- before the receipt ever painted -- which bubbles up
     * to ir-device-list and rebuilds this element (and the open save
     * dialog inside it, receipt and all) out from under the save
     * flow. No close() call, no "closed" event, nothing crashes: the
     * whole host is replaced, so the receipt never gets a chance to
     * paint. This handler only records that a refresh is owed;
     * _closeSaveFlow runs it once the flow is actually done. */
    private _onWigSaved = (): void => {
        this._pendingWigSaved = true;
    };

    private _flash(message: string) {
        this._toast = message;
        setTimeout(() => {
            this._toast = null;
        }, 2400);
    }

    /** Second Fitting v3: SAVE TO CLOSET opens the decision window
     * first, always. Punch list item 6: the window itself opens
     * immediately, synchronously, on `hasSource` alone -- the plan
     * fetch is no longer awaited before anything shows; its source
     * line and delta summary stream in once the fetch resolves. A
     * failed fetch closes the just-opened window and falls back to
     * the old Perfect-Fit-route dialog directly, which retries the
     * same call and carries its own inline error banner. */
    private async _openSaveRoute(): Promise<void> {
        if (this._busy) return;
        this._saveRouteOpen = true;
        try {
            this._saveRoutePlan = await this.api.wigsSavePlan(
                this.device.id,
            );
        } catch (err) {
            this._saveRouteOpen = false;
            this._flash((err as Error).message);
            this._saveRoute = "perfect";
        }
    }

    /** Second Fitting v3, Commit 4: SAVE AS NEW and UPDATE CLOSET WIG
     * open their own stripped dialogs now. VALIDATE FOR PERFECT FIT
     * still opens the pre-v3 dialog until Commit 5 gives it one of its
     * own -- see the Commit 3 and 4 commit messages. The plan fetched
     * for the window rides straight into whichever dialog opens, so
     * nothing downstream refetches it. */
    private _onSaveRoute = (e: CustomEvent<{ route: SaveRoute }>): void => {
        this._saveRoute = e.detail.route;
    };

    /** Coding plan Commit 4: the Update dialog's stale-replace refusal
     * (Commit 2's `not_diverged`) surfaces as a plain re-open of the
     * decision window with a fresh plan, not a dead end the person has
     * to back out of by hand. */
    private _onStaleReplace = async (): Promise<void> => {
        this._saveRoute = null;
        await this._openSaveRoute();
    };

    /** Clears the route state as always, then -- if a save
     * dialog left a refresh owed (see _onWigSaved) -- runs it now
     * that the flow is actually closed. Still lands strictly before
     * the next Save to Closet open (the route window can't open
     * while a save dialog is up), which is all 697923c's fix ever
     * needed -- it just doesn't run while the receipt is on screen. */
    private _closeSaveFlow = (): void => {
        this._saveRouteOpen = false;
        this._saveRoute = null;
        this._saveRoutePlan = null;
        if (this._pendingWigSaved) {
            this._pendingWigSaved = false;
            void this._refresh();
        }
    };

    // ---------------------------------------------------------------
    // Inline name editing
    // ---------------------------------------------------------------

    private _startEditName() {
        this._draftName = this.device.name;
        this._editingName = true;
        this.updateComplete.then(() => {
            const input = this.shadowRoot?.querySelector<HTMLInputElement>(".name-input");
            input?.focus();
            input?.select();
        });
    }

    private async _saveName() {
        const name = this._draftName.trim();
        if (!name || name === this.device.name) {
            this._editingName = false;
            return;
        }
        this._busy = true;
        try {
            this.device = await this.api.updateDevice(this.device.id, { name });
            this._flash(t("devdetail.name_updated"));
            this.dispatchEvent(
                new CustomEvent("device-changed", { bubbles: true, composed: true }),
            );
        } catch (err) {
            this._flash(`Update failed: ${(err as Error).message}`);
        } finally {
            this._busy = false;
            this._editingName = false;
        }
    }

    private _onNameKeyDown(e: KeyboardEvent) {
        if (e.key === "Enter") {
            e.preventDefault();
            void this._saveName();
        } else if (e.key === "Escape") {
            this._editingName = false;
        }
    }

    // ---------------------------------------------------------------
    // Device type / emitter changes
    // ---------------------------------------------------------------

    private async _onTypeChanged(e: Event) {
        const newType = (e.target as HTMLSelectElement).value;
        if (newType === this.device.device_type) return;
        this._busy = true;
        try {
            this.device = await this.api.updateDevice(this.device.id, {
                device_type: newType,
            });
            this._flash(t("devdetail.type_updated"));
            this.dispatchEvent(
                new CustomEvent("device-changed", { bubbles: true, composed: true }),
            );
        } catch (err) {
            this._flash(`Update failed: ${(err as Error).message}`);
        } finally {
            this._busy = false;
        }
    }

    /** Every assignable emitter (getEmitterOptions -- the same
     *  infrared.* / receiver-exclusion / hair_observer filter
     *  ir-emitter-picker.ts itself uses), mapped to header-chip-group's
     *  row shape. `down` mirrors that component's own three-state
     *  logic: assigned but HA reports it unreachable. */
    private _emitterRows(): HeaderChipRow[] {
        const receiverIds = new Set(this.receivers.map((r) => r.entity_id));
        const value = this.device.emitter_entity_ids ?? [];
        return getEmitterOptions(this.hass, receiverIds).map((em) => ({
            id: em.entity_id,
            name: em.name,
            on: value.includes(em.entity_id),
            down: value.includes(em.entity_id) && !em.available,
        }));
    }

    /** Rows for the Device detail's Pin: group -- candidates are
     *  Remotes, and `on` is read from stored state (signpost 4, Track
     *  4). The pin lives on the remote, so "is this device pinned to
     *  that remote" is answered by looking in the remote's own list;
     *  the device side deliberately stores nothing of its own. */
    private _pinRows(): HeaderChipRow[] {
        return this.triggerRemotes.map((r) => ({
            id: r.id,
            name: r.name,
            on: (r.pinned_device_ids ?? []).includes(this.device.id),
        }));
    }

    /** Pin or unpin this device against whichever Remote's chip moved.
     *
     * The group reports the full new list of "on" ids, so the delta
     * against current state names the one remote that changed. Both
     * directions are one call; the parent refetches remotes afterwards
     * so the chips reflect what the backend actually stored rather
     * than what we hoped it stored. */
    private async _onPinsChanged(e: CustomEvent<{ value: string[] }>) {
        const next = new Set(e.detail.value);
        const before = new Set(
            this._pinRows().filter((r) => r.on).map((r) => r.id),
        );
        const added = [...next].filter((id) => !before.has(id));
        const removed = [...before].filter((id) => !next.has(id));
        this._busy = true;
        try {
            for (const remoteId of added) {
                await this.api.pinTriggerRemoteDevice(remoteId, this.device.id);
            }
            for (const remoteId of removed) {
                await this.api.unpinTriggerRemoteDevice(
                    remoteId,
                    this.device.id,
                );
            }
            this.dispatchEvent(
                new CustomEvent("remote-pins-changed", {
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._toast = String(err);
        } finally {
            this._busy = false;
        }
    }

    private async _onEmittersChanged(e: CustomEvent) {
        const newIds: string[] = e.detail.value;
        const previousIds = [...this.device.emitter_entity_ids];

        // Optimistic local update -- otherwise the ``_busy = true`` line
        // below triggers a parent re-render that passes the still-saved
        // ``emitter_entity_ids`` back into the picker, briefly snapping
        // the just-removed chip back. The picker re-renders with the
        // new (empty) value as soon as Lit processes this assignment.
        this.device = { ...this.device, emitter_entity_ids: newIds };
        this._busy = true;
        try {
            this.device = await this.api.updateDevice(this.device.id, {
                emitter_entity_ids: newIds,
            });
            // Signpost 3 follow-up (2026-08-15): no success flash here --
            // the picker's own chips turning green already signal the
            // update, matching the (already flash-less) receiver picker
            // on the remote side. The failure flash below is unchanged.
            this.dispatchEvent(
                new CustomEvent("device-changed", { bubbles: true, composed: true }),
            );
        } catch (err) {
            // Revert the optimistic update so the picker reflects what
            // actually persisted server-side.
            this.device = { ...this.device, emitter_entity_ids: previousIds };
            this._flash(`Update failed: ${(err as Error).message}`);
        } finally {
            this._busy = false;
        }
    }

    // ---------------------------------------------------------------
    // Action mapping
    // ---------------------------------------------------------------

    connectedCallback(): void {
        super.connectedCallback();
        void this._loadActionOptions();
        void this._loadTriggers();
        // Best-effort: receiver names for the trigger popover's scope labels.
        this.api
            .listReceivers()
            .then((r) => {
                this._receivers = r;
            })
            .catch(() => {
                this._receivers = [];
            });
    }

    updated(changed: Map<string, unknown>): void {
        if (changed.has("device")) {
            void this._loadActionOptions();
            void this._loadTriggers();
        }
        // After a keyed rebuild of the commands-list, Sortable needs to
        // be re-attached to the freshly-created container.
        if (changed.has("_commandsListVersion") && !this._sortable) {
            this._attachSortable();
        }
    }

    private async _loadActionOptions() {
        try {
            this._actionOptions = await this.api.getActionOptions(this.device.device_type);
        } catch {
            this._actionOptions = [];
        }
    }

    /** Every label the badge can actually render for THIS device.
     *
     *  Not just the option list. _getActionLabel falls back to the raw
     *  mapping key when a mapped key is absent from the device type's
     *  options, which happens when a device carries a mapping from a type
     *  it no longer is -- an AC on the bench still holds media_player keys
     *  and renders POWER_TOGGLE, NAVIGATE_RIGHT and friends. Those escaped
     *  the first version of this sizing, so the reservation came out too
     *  narrow and the badges went ragged again. Measuring what is really
     *  on screen closes that whole class of gap rather than the one case. */
    private _badgeLabels(): string[] {
        const labels = new Set<string>([t("cmdrow.actions")]);
        for (const opt of this._actionOptions) labels.add(tv(opt.label));
        for (const cmd of this.device?.commands ?? []) {
            const label = this._getActionLabel(cmd.name);
            if (label) labels.add(label);
        }
        return [...labels];
    }

    /** Memoized badge metrics, keyed on the label set itself so a mapping
     *  change or a device switch recomputes and nothing else does. */
    private _actionBadgeMetrics() {
        const labels = this._badgeLabels();
        // The escaped form, not a literal NUL. A raw one made git and
        // grep treat this whole file as binary, so it never showed a
        // diff and never matched a search. Identical at runtime.
        const key = labels.join("\u0000");
        if (key !== this._actionBadgeKey) {
            this._actionBadgeKey = key;
            this._actionBadge = this._measureActionBadges(labels);
        }
        return this._actionBadge;
    }

    /** Size the action badge once per device type (owner ruling,
     *  2026-08-01).
     *
     *  Every command row in one device detail draws from the same option
     *  list, so one reserved width makes the whole list rigid: mapping an
     *  action can no longer grow the label and shove the buttons after it
     *  sideways. Measured once here rather than per render, and only to
     *  choose a font tier -- the actual width is settled in CSS by a hidden
     *  copy of the widest label, stacked in the same grid cell as the
     *  visible one (ir-command-row.ts's .action-sizer), which stays
     *  correct in any language.
     *
     *  Labels that do not fit the cap step down a tier rather than being
     *  truncated: the two long ones are Color Temp Warmer / Cooler, and
     *  clipping them to "Color Temp Warm..." would destroy the only word
     *  that tells them apart. A device type whose longest label misses even
     *  the smallest tier keeps that tier and widens past the cap, which is
     *  a deliberate graceful failure rather than unreadable text. */
    private _measureActionBadges(labels: string[]) {
        const ctx = document.createElement("canvas").getContext("2d");
        if (!ctx) return null;
        const family = getComputedStyle(this).fontFamily || "sans-serif";
        // The reservation has to cover the MAPPED rendering (arrow +
        // label), the wider of the two states a row can show, since an
        // unmapped row can be mapped later without ever changing width.
        // The arrow renders at 0.8em relative to whichever font tier the
        // label itself lands on (.map-arrow, ir-command-row.ts), so it's
        // measured here at that same relative size rather than a fixed
        // px guess. No padding or border to add on top of that -- the
        // link-A label has neither, unlike the old bordered badge button
        // this replaced.
        const widthOf = (text: string, px: number): number => {
            ctx.font = `${ACTION_BADGE_WEIGHT} ${px}px ${family}`;
            const textWidth =
                ctx.measureText(text).width +
                text.length * px * ACTION_BADGE_TRACKING;
            ctx.font = `${px * 0.8}px ${family}`;
            const arrowWidth = ctx.measureText(ACTION_ARROW_CHAR).width;
            return textWidth + arrowWidth + ACTION_ARROW_GAP_PX;
        };
        const tierFor = (text: string): number =>
            ACTION_BADGE_FONT_LADDER.find(
                (px) => widthOf(text, px) <= ACTION_BADGE_CAP_PX,
            ) ?? ACTION_BADGE_FONT_LADDER[ACTION_BADGE_FONT_LADDER.length - 1];

        let sizerLabel = t("cmdrow.actions");
        let sizerFontPx = ACTION_BADGE_FONT_LADDER[0];
        let widest = 0;
        const fontFor: Record<string, number> = {};
        for (const label of labels) {
            const px = tierFor(label);
            fontFor[label] = px;
            const w = widthOf(label, px);
            if (w > widest) {
                widest = w;
                sizerLabel = label;
                sizerFontPx = px;
            }
        }
        return { sizerLabel, sizerFontPx, fontFor };
    }

    private async _loadTriggers() {
        try {
            this._triggers = await this.api.listTriggers();
        } catch {
            this._triggers = [];
        }
    }

    /** Check if a command has an associated trigger (by matching its signal fingerprint). */
    private _commandHasTrigger(cmd: IRCommand): boolean {
        // A trigger's source_command_id links it back to the command.
        return this._triggers.some((t) => t.source_command_id === cmd.id);
    }

    /** Count triggers bound to a command (yellow dot; multiple legal in v0.5.7). */
    private _commandTriggerCount(cmd: IRCommand): number {
        return this._triggers.filter((t) => t.source_command_id === cmd.id).length;
    }

    private _onToggleTrigger(ev: CustomEvent): void {
        const cmd = ev.detail?.command as IRCommand | null;
        if (!cmd) return;

        const matches = this._triggers.filter(
            (t) => t.source_command_id === cmd.id,
        );
        // Zero triggers: open the Create dialog directly (no popover).
        if (matches.length === 0) {
            this._triggerCommand = cmd;
            return;
        }
        // 1+ triggers: show the picker popover near the command's Trigger button.
        const rect = ev.detail?.buttonRect as DOMRect | null;
        this._triggerPopover = {
            command: cmd,
            top: rect ? rect.bottom + 4 : 120,
            left: rect ? Math.max(8, rect.right - 220) : 120,
        };
        this._installTriggerPopoverDismiss();
    }

    private _triggersForCommand(cmd: IRCommand): IRTrigger[] {
        return this._triggers.filter((t) => t.source_command_id === cmd.id);
    }

    private _closeTriggerPopover(): void {
        this._triggerPopover = null;
        this._removeTriggerPopoverDismiss();
    }

    private _onTriggerPopoverCreateNew(): void {
        const p = this._triggerPopover;
        this._closeTriggerPopover();
        if (p) this._triggerCommand = p.command;
    }

    private _onTriggerPopoverEdit(ev: CustomEvent): void {
        const t = ev.detail as IRTrigger | undefined;
        this._closeTriggerPopover();
        if (t) this._triggerEdit = t;
    }

    private _onDocClickForTriggerPopover = (ev: Event): void => {
        const pop = this.shadowRoot?.querySelector("ir-trigger-popover");
        if (pop && ev.composedPath().includes(pop)) return;
        this._closeTriggerPopover();
    };

    private _onScrollForTriggerPopover = (): void => {
        this._closeTriggerPopover();
    };

    private _installTriggerPopoverDismiss(): void {
        setTimeout(() => {
            document.addEventListener(
                "click",
                this._onDocClickForTriggerPopover,
                true,
            );
            window.addEventListener(
                "scroll",
                this._onScrollForTriggerPopover,
                true,
            );
        }, 0);
    }

    private _removeTriggerPopoverDismiss(): void {
        document.removeEventListener(
            "click",
            this._onDocClickForTriggerPopover,
            true,
        );
        window.removeEventListener("scroll", this._onScrollForTriggerPopover, true);
    }

    private _closeTriggerDialog(): void {
        this._triggerCommand = null;
        this._triggerEdit = null;
    }

    private async _onTriggerSaved(): Promise<void> {
        this._triggerCommand = null;
        this._triggerEdit = null;
        await this._loadTriggers();
        // Tell the parent (ir-device-list) to refresh its own _triggers
        // state so the new trigger card appears in the panel's Triggers
        // section immediately. Without this, the trigger is created on
        // the backend and the device-detail's local list reflects it,
        // but the panel's separate trigger list stays stale until the
        // user reloads the page.
        this.dispatchEvent(
            new CustomEvent("trigger-changed", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _requestDeleteTrigger(triggerId: string): void {
        this._confirmDeleteTriggerId = triggerId;
    }

    private async _doDeleteTrigger(): Promise<void> {
        if (!this._confirmDeleteTriggerId) return;
        const id = this._confirmDeleteTriggerId;
        this._confirmDeleteTriggerId = null;
        this._triggerEdit = null;
        try {
            await this.api.deleteTrigger(id);
            await this._loadTriggers();
            // Notify the parent so its Triggers section drops the deleted
            // card without requiring a reload. Same rationale as
            // _onTriggerSaved -- the device-detail and the device-list
            // each maintain their own trigger state.
            this.dispatchEvent(
                new CustomEvent("trigger-changed", {
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch {
            // Non-fatal.
        }
    }

    /** Look up the human label for the action mapped to a command. */
    private _getActionLabel(commandName: string): string | null {
        const mapping = this.device.entity_config?.command_mapping ?? {};
        for (const [key, val] of Object.entries(mapping)) {
            if (val.toLowerCase() === commandName.toLowerCase()) {
                const opt = this._actionOptions.find((o) => o.key === key);
                return opt ? tv(opt.label) : key;
            }
        }
        return null;
    }

    private _onMapAction(e: CustomEvent) {
        const { command } = e.detail as { command: IRCommand };
        if (!command) return;

        // Position popover near the row's action-mapping label, using fixed
        // viewport coords (.action-popover is position: fixed, per
        // ir-popover-styles.ts). BUG FIX (owner report 2026-08-11, third
        // bench look): this selector still said ".badge-btn", the OLD
        // ACTIONS button class from before mobile-polish.md 2.2's link-A
        // swap (commit 2) renamed it to ".map-action-label" -- so this
        // query always missed, top/left stayed at their 0/0 default, and
        // the popover rendered pinned to the page's top-left corner
        // instead of near the label that opened it.
        const badge = (e.target as LitElement).shadowRoot?.querySelector(".map-action-label") as HTMLElement | null;
        if (badge) {
            const rect = badge.getBoundingClientRect();
            this._popoverTop = rect.bottom + 4;
            this._popoverLeft = Math.max(8, rect.right - 220);
        }

        this._mappingCommandName = command.name;

        // Dismiss on outside click (next tick so this click doesn't immediately close).
        requestAnimationFrame(() => {
            this._dismissHandler = (ev: MouseEvent) => {
                const path = ev.composedPath();
                const popover = this.shadowRoot?.querySelector(".action-popover");
                if (popover && !path.includes(popover)) {
                    this._closePopover();
                }
            };
            document.addEventListener("click", this._dismissHandler, true);
        });
    }

    private _closePopover() {
        this._mappingCommandName = null;
        this._customActionOpen = false;
        this._customActionValue = "";
        if (this._dismissHandler) {
            document.removeEventListener("click", this._dismissHandler, true);
            this._dismissHandler = null;
        }
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        if (this._dismissHandler) {
            document.removeEventListener("click", this._dismissHandler, true);
            this._dismissHandler = null;
        }
        this._removeTriggerPopoverDismiss();
        this._sortable?.destroy();
        this._sortable = null;
        this._cancelPendingReorderSave();
    }

    firstUpdated(): void {
        this._attachSortable();
    }

    /** Wire SortableJS to the commands list container. Idempotent. */
    private _attachSortable(): void {
        if (this._sortable) return;
        const container = this.renderRoot.querySelector(
            ".commands-list",
        ) as HTMLElement | null;
        if (!container) return;
        // Command row restructure (command-row-restructure.md, commit
        // 2 of 2): checked whether this selector needed to change for
        // the grip's new position and it doesn't. .grip-handle is a
        // light-DOM child of <ir-command-row> (slotted in below, via
        // slot="status") -- ir-command-row's restructure only moved
        // .status around inside ITS OWN shadow DOM (nesting it in
        // .top-line instead of a grid column), which never touches
        // .grip-handle's actual position in the light DOM tree that
        // Sortable's handle matching (closest()) walks. Confirmed by
        // DOM/selector inspection post-deploy; native HTML5
        // drag-and-drop isn't mechanically triggerable through this
        // project's browser-automation tooling, so the actual drag
        // gesture still wants a manual once-over.
        this._sortable = Sortable.create(container, {
            handle: ".grip-handle",
            animation: 150,
            ghostClass: "sortable-ghost",
            onEnd: (e) => {
                const oldIndex = e.oldIndex;
                const newIndex = e.newIndex;
                if (
                    oldIndex === undefined ||
                    newIndex === undefined ||
                    oldIndex === newIndex
                ) {
                    return;
                }

                // Compute the new commands order from the drag indices.
                // We trust SortableJS for the DOM (no manual revert) and
                // force a keyed rebuild below so Lit gets a fresh repeat()
                // cache instead of trying to reconcile a stale one.
                const commands = [...this.device.commands];
                const [moved] = commands.splice(oldIndex, 1);
                commands.splice(newIndex, 0, moved);
                this.device = { ...this.device, commands };

                // Bubble the new order to the parent so its cached
                // ``_expandedDevice`` stays in sync. Without this, the
                // parent's next re-render would pass its still-original
                // device back down and Lit would overwrite our local
                // ``this.device``. The custom event is intentionally
                // lightweight -- the parent updates its cache without
                // refetching, so the heavy ``device-changed`` cascade
                // (round-trip, action-options reload, triggers reload)
                // is avoided.
                this.dispatchEvent(
                    new CustomEvent("commands-reordered", {
                        detail: { commands },
                        bubbles: true,
                        composed: true,
                    }),
                );

                // Tear down the SortableJS instance bound to the old
                // container and increment the version so ``keyed()``
                // gives us a fresh ``.commands-list`` DOM tree. The
                // ``updated()`` lifecycle re-attaches Sortable to the
                // new container once Lit has rendered it.
                this._sortable?.destroy();
                this._sortable = null;

                // SortableJS sometimes leaves the dragged element
                // positioned after Lit's end-of-content marker, which
                // puts it outside keyed()'s managed range. Lit can't
                // clean it up there and it shows as a visual duplicate
                // after the rebuild. Explicit pre-rebuild cleanup
                // guarantees no orphans -- keyed() then rebuilds from
                // a known-empty state.
                const container = this.renderRoot.querySelector(
                    ".commands-list",
                );
                if (container) {
                    for (const row of Array.from(
                        container.querySelectorAll("ir-command-row"),
                    )) {
                        row.remove();
                    }
                }

                this._commandsListVersion++;

                this._scheduleReorderSave(commands.map((c) => c.id));
            },
        });
    }

    /** Debounce a reorder save to ride out rapid sequential drags. */
    private _scheduleReorderSave(commandIds: string[]): void {
        this._cancelPendingReorderSave();
        this._pendingReorderTimeout = window.setTimeout(async () => {
            this._pendingReorderTimeout = null;
            try {
                await this.api.reorderCommands(this.device.id, commandIds);
                // Silent on success. Local ``this.device.commands`` already
                // holds the canonical order (the server accepted exactly
                // what we sent), so re-assigning would trigger an
                // unnecessary re-render chain: child re-render, parent
                // ``device-changed`` listener, ``_loadExpandedDevice``
                // round-trip, ``updated()`` lifecycle, ``_loadActionOptions``
                // + ``_loadTriggers`` re-fires. That cascade is what made
                // the card visibly flash 500 ms after each drop.
            } catch (err) {
                // Backend rejected (eg. stale command set after a parallel
                // add/delete). Surface the error and resync from server.
                this._flash(t("devdetail.reorder_failed", { message: (err as Error).message }));
                await this._refresh();
            }
        }, REORDER_DEBOUNCE_MS);
    }

    /** Drop any pending debounced reorder save (called before add/delete). */
    private _cancelPendingReorderSave(): void {
        if (this._pendingReorderTimeout !== null) {
            clearTimeout(this._pendingReorderTimeout);
            this._pendingReorderTimeout = null;
        }
    }

    /** Get the command name currently mapped to a given action key. */
    private _getCommandForAction(actionKey: string): string | null {
        const mapping = this.device.entity_config?.command_mapping ?? {};
        return mapping[actionKey] ?? null;
    }

    private async _selectAction(commandName: string, actionKey: string | null) {
        this._closePopover();
        this._busy = true;
        try {
            const result = await this.api.updateMapping(
                this.device.id,
                commandName,
                actionKey,
            );
            this.device = {
                ...this.device,
                entity_config: {
                    ...this.device.entity_config,
                    command_mapping: result.mapping,
                },
            };
            this._flash(actionKey ? t("devdetail.mapped_to", { action: actionKey }) : t("devdetail.mapping_cleared"));
            this.dispatchEvent(
                new CustomEvent("device-changed", { bubbles: true, composed: true }),
            );
        } catch (err) {
            this._flash(t("devdetail.mapping_failed", { message: (err as Error).message }));
        } finally {
            this._busy = false;
        }
    }

    /** Find the action key currently mapped to a command name. */
    private _getCurrentActionKey(commandName: string): string {
        const mapping = this.device.entity_config?.command_mapping ?? {};
        for (const [key, val] of Object.entries(mapping)) {
            if (val.toLowerCase() === commandName.toLowerCase()) {
                return key;
            }
        }
        return "";
    }

    // ---------------------------------------------------------------
    // Command actions
    // ---------------------------------------------------------------

    private async _onTest(e: CustomEvent) {
        const { command } = e.detail as { command: IRCommand };
        if (!command) return;
        this._busy = true;
        try {
            await this.api.sendCommand(this.device.id, command.id);
            this._flash(t("devdetail.sent_cmd", { name: command.name }));
        } catch (err) {
            this._flash(t("devdetail.send_failed", { message: (err as Error).message }));
        } finally {
            this._busy = false;
        }
    }

    /** Whether a command is currently a climate preset on this device.
     *  Case-insensitive to match the backend's own name comparisons,
     *  which is what the rename cascade and the delete prune use. */
    private _isStarred(name: string): boolean {
        const starred = this.device.entity_config?.starred ?? [];
        const target = name.toLowerCase();
        return starred.some((entry) => entry.toLowerCase() === target);
    }

    /** Climate presets: the star (climate-presets-star.md). One click,
     *  no dialog -- toggle, take the authoritative list back, repaint.
     *  The device's own payload is patched rather than refetched: the
     *  handler returns the full starred list, so a round trip would
     *  only re-read what is already in hand. */
    private async _onStarToggle(e: CustomEvent) {
        const { command } = e.detail as { command: IRCommand };
        if (!command) return;
        const next = !this._isStarred(command.name);
        this._busy = true;
        try {
            const result = await this.api.starCommand(
                this.device.id,
                command.name,
                next,
            );
            this.device = {
                ...this.device,
                entity_config: {
                    ...this.device.entity_config,
                    starred: result.starred,
                },
            };
            // No success flash on purpose: the glyph filling in IS the
            // feedback, and the feature's whole shape is "no dialog, no
            // picker, no vocabulary". Only the failure path needs
            // words, and it borrows the page's existing generic one
            // rather than minting copy the handoff did not ask for
            // (which specifies exactly two new locale keys, both
            // titles).
            this.dispatchEvent(
                new CustomEvent("device-changed", {
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._flash(
                t("devdetail.update_failed", {
                    message: (err as Error).message,
                }),
            );
        } finally {
            this._busy = false;
        }
    }

    private async _onToggleTxRaw(e: CustomEvent) {
        const { command } = e.detail as { command: IRCommand };
        if (!command) return;
        const next = !command.tx_force_raw;
        this._busy = true;
        try {
            await this.api.setCommandTxForceRaw(this.device.id, command.id, next);
            command.tx_force_raw = next;
            this.requestUpdate();
            this._flash(
                next
                    ? `"${command.name}" will transmit the captured timings`
                    : `"${command.name}" will transmit clean decoded timings`,
            );
        } catch (err) {
            this._flash(`Update failed: ${(err as Error).message}`);
        } finally {
            this._busy = false;
        }
    }

    private _onDelete(e: CustomEvent) {
        const { command } = e.detail as { command: IRCommand };
        if (!command) return;
        this._commandToDelete = command;
    }

    private _onEditCommand(e: CustomEvent) {
        const { command } = e.detail as { command: IRCommand };
        if (!command) return;
        this._editCommand = command;
    }

    private async _onCommandEdited(e: CustomEvent): Promise<void> {
        const detail = e.detail as {
            triggers?: { rewired: string[]; skipped: string[] };
        };
        this._editCommand = null;
        await this._refresh();
        const rewired = detail.triggers?.rewired ?? [];
        if (rewired.length) {
            const names = rewired.map((n) => `"${n}"`).join(", ");
            this._flash(t("devdetail.cmd_updated_repointed", { names }));
        } else {
            this._flash(t("devdetail.cmd_updated"));
        }
        // A code edit can change the trigger's identity; refresh the panel's
        // trigger list too.
        this.dispatchEvent(
            new CustomEvent("trigger-changed", { bubbles: true, composed: true }),
        );
    }

    private async _onRenameCommand(e: CustomEvent): Promise<void> {
        const { command, name } = e.detail as { command: IRCommand; name: string };
        this._busy = true;
        try {
            const result = await this.api.updateCommand({
                device_id: this.device.id,
                command_id: command.id,
                name,
            });
            await this._refresh();
            const n = result.mappings_updated;
            this._flash(
                n > 0
                    ? `Renamed (updated ${n} action mapping${n === 1 ? "" : "s"})`
                    : "Renamed",
            );
            this.dispatchEvent(
                new CustomEvent("device-changed", { bubbles: true, composed: true }),
            );
        } catch (err) {
            this._flash(t("devdetail.rename_failed", { message: (err as Error).message }));
        } finally {
            this._busy = false;
        }
    }

    private async _confirmCommandDelete(): Promise<void> {
        const command = this._commandToDelete;
        if (!command) return;
        this._commandToDelete = null;
        this._cancelPendingReorderSave();
        this._busy = true;
        try {
            await this.api.deleteCommand(this.device.id, command.id);
            await this._refresh();
            this._flash(t("devdetail.removed", { name: command.name }));
        } catch (err) {
            this._flash(`Delete failed: ${(err as Error).message}`);
        } finally {
            this._busy = false;
        }
    }

    // ---------------------------------------------------------------
    // Capture dialog
    // ---------------------------------------------------------------

    private _onCaptureClosed() {
        this._captureName = null;
    }

    private async _onCommandSaved(e: CustomEvent) {
        const { commandName } = e.detail as { commandName: string };
        this._cancelPendingReorderSave();
        await this._refresh();
        this._flash(t("devdetail.saved", { name: commandName }));
        this._captureName = null;
    }

    // ---------------------------------------------------------------
    // Navigation / device delete
    // ---------------------------------------------------------------

    private _goToSniffer() {
        this.dispatchEvent(
            new CustomEvent("navigate-sniffer", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _goToClips() {
        this.dispatchEvent(
            new CustomEvent("navigate-clips", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _goToMirror() {
        this.dispatchEvent(
            new CustomEvent("navigate-mirror", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** Dispatched by both the footer's "Delete Device" button below
     *  and (bubbling straight through, composed, from the nested
     *  <ir-device-settings-dialog>) its Settings-dialog Delete button.
     *  ir-device-list.ts's <ir-device-detail> instantiation catches
     *  this and reuses its own already-tested _confirmDeleteDevice /
     *  _doDeleteDevice flow -- the same one the card's hover-trash
     *  icon triggers -- rather than this file keeping a second,
     *  separate delete implementation of its own (Track 1 item 6,
     *  "not two flows"). */
    private _requestDelete(): void {
        this.dispatchEvent(
            new CustomEvent("request-delete", { bubbles: true, composed: true }),
        );
    }

    private _navigateIntegration(url: string | null) {
        if (!url) return;
        window.history.pushState(null, "", url);
        window.dispatchEvent(new PopStateEvent("popstate"));
    }

    // ---------------------------------------------------------------
    // State matrix (Cold Cuts, v0.8.8)
    // ---------------------------------------------------------------

    /** The device's HAIR climate state object, resolved through the
     * HA registries: device by its (hair, id) identifier, then that
     * device's climate entity. Registry-first because the HAIR device
     * id is not the HA device id and the entity_id is user-renamable;
     * null (no card readout) while the registries have not caught up. */
    private _climateState(): any | null {
        const devices = (this.hass?.devices ?? {}) as Record<string, any>;
        let haDeviceId: string | null = null;
        for (const dev of Object.values(devices)) {
            const idents = (dev?.identifiers ?? []) as [string, string][];
            if (
                idents.some(
                    (pair) =>
                        pair[0] === "hair" && pair[1] === this.device.id,
                )
            ) {
                haDeviceId = dev.id;
                break;
            }
        }
        if (!haDeviceId) return null;
        const entities = (this.hass?.entities ?? {}) as Record<
            string,
            any
        >;
        for (const [entityId, entry] of Object.entries(entities)) {
            if (
                entry?.device_id === haDeviceId &&
                entityId.startsWith("climate.")
            ) {
                return this.hass?.states?.[entityId] ?? null;
            }
        }
        return null;
    }

    /** SEND from the card: transmit the picked state now.
     *
     * The card resolved the coordinates and the display name before it
     * fired; this only has to choose which shape of request they make
     * (a power code, or a cell) and report what came back. Power wins
     * when set, the same precedence the card itself applies. */
    /** The climate entity's current cell, which the card rings cold.
     * matrix-power-row.md item 3 (optional polish): matrix_cell is
     * absent while the climate entity is off, so the readout used to
     * go blank instead of saying so. Cheap to add -- the state object
     * is already fetched for the cell attribute, this just also reads
     * .state -- so no plumbing skip needed here. */
    private _matrixCurrentName(): string | null {
        const climateState = this._climateState();
        return (
            climateState?.attributes?.matrix_cell ??
            (climateState?.state === "off" ? t("fitting.row_off") : null)
        );
    }

    private async _matrixSend(e: CustomEvent<MatrixCardPick>): Promise<void> {
        const pick = e.detail;
        this._busy = true;
        try {
            const result = await this.api.matrixSend(
                this.device.id,
                pick.power !== null
                    ? { power: pick.power }
                    : {
                          mode: pick.mode!,
                          fan: pick.fan,
                          swing: pick.swing,
                          temp: pick.temp,
                      },
            );
            // Second Fitting v3 punch list item 14: the cell TEST now
            // carries the same SENT . HEARD reading a stored command's
            // TEST does. Reuses testbtn.heard rather than minting a
            // new locale key for one word.
            const sentMsg = t("devdetail.sent_cmd", { name: result.sent });
            this._flash(
                result.heard
                    ? `${sentMsg} \u00b7 ${t("testbtn.heard")}`
                    : sentMsg,
            );
        } catch (err) {
            this._flash(
                t("devdetail.send_failed", {
                    message: (err as Error).message,
                }),
            );
        } finally {
            this._busy = false;
        }
    }

    /** + COMMAND from the card: keep the picked state as a row. */
    private async _matrixSaveCommand(
        e: CustomEvent<MatrixCardPick>,
    ): Promise<void> {
        const pick = e.detail;
        this._busy = true;
        try {
            // The response IS the refreshed full device (the saved
            // state replaces by name, so the list never twins).
            this.device = await this.api.matrixCommand(
                this.device.id,
                pick.power !== null
                    ? { power: pick.power }
                    : {
                          mode: pick.mode!,
                          fan: pick.fan,
                          swing: pick.swing,
                          temp: pick.temp,
                      },
            );
            this._flash(t("devdetail.saved", { name: pick.name }));
            this.dispatchEvent(
                new CustomEvent("device-changed", {
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._flash(
                t("devdetail.update_failed", {
                    message: (err as Error).message,
                }),
            );
        } finally {
            this._busy = false;
        }
    }

    // ---------------------------------------------------------------
    // Render
    // ---------------------------------------------------------------

    render() {
        const commands = this.device.commands;
        const badge = this._actionBadgeMetrics();
        const count = commands.length;

        return html`
            <!-- Header (punch list item 9, header-pin-layout-handoff.md):
                 one block now, not a header row plus a separate
                 .device-meta grid below it. Left to right: the title
                 block (name, then Type directly under it), the
                 full-height divider, the colon-aligned Emitters/Pinned
                 rows, and the actions column that anchors Save to
                 Closet + X to the top edge and the gear to the bottom. -->
            <section class="header rdetail-top">
                <div class="rtitle-block">
                    <div class="name-row">
                        ${this._editingName
                            ? html`
                                  <input
                                      class="name-input"
                                      type="text"
                                      .value=${this._draftName}
                                      @input=${(e: Event) =>
                                          (this._draftName = (e.target as HTMLInputElement).value)}
                                      @blur=${this._saveName}
                                      @keydown=${this._onNameKeyDown}
                                      ?disabled=${this._busy}
                                  />
                              `
                            : html`
                                  <h1
                                      class="editable-name"
                                      @click=${this._startEditName}
                                      title=${t("cmdrow.rename")}
                                  >
                                      ${this.device.name}
                                      <span class="edit-icon">&#9998;</span>
                                  </h1>
                              `}
                        ${this.device.ha_device_id
                            ? renderExitToEntityBtn(
                                  `/config/devices/device/${this.device.ha_device_id}`,
                                  t("devices.open_in_ha"),
                              )
                            : nothing}
                    </div>
                    <div class="stack">
                        <span class="sl">${t("devdetail.type")}</span>
                        ${this.device.matrix
                        ? html`<span
                              class="type-locked"
                              title=${t("devdetail.type_locked_tooltip")}
                              >${t("device_type.ac")} ·
                              ${t("devices.matrix_title")}</span
                          >`
                        : html`<select
                              .value=${this.device.device_type}
                              @change=${this._onTypeChanged}
                              ?disabled=${this._busy}
                          >
                              ${DEVICE_TYPES.map(
                                  (dt) => html`
                                      <option
                                          value=${dt.value}
                                          ?selected=${this.device
                                              .device_type === dt.value}
                                      >
                                          ${t(`device_type.${dt.value}`)}
                                      </option>
                                  `,
                              )}
                          </select>`}
                    </div>
                </div>
                <div class="rdetail-divider"></div>
                <div class="hdr-rows">
                    <ir-header-chip-group
                        label=${t("hdrchips.emitters_label")}
                        .labelWidth=${DEVICE_HDR_LABEL_W}
                        .rows=${this._emitterRows()}
                        .tone=${GREEN_PEAK}
                        ?disabled=${this._busy}
                        @chips-changed=${this._onEmittersChanged}
                    ></ir-header-chip-group>
                    ${PINNING_UI_ENABLED
                        ? html`
                              <ir-header-chip-group
                                  label=${t("hdrchips.pin_label_full")}
                                  labelEmpty=${t("hdrchips.pin_label_empty")}
                                  .labelWidth=${DEVICE_HDR_LABEL_W}
                                  .rows=${this._pinRows()}
                                  .tone=${ORIGIN_COLORS.remote}
                                  ?disabled=${this._busy}
                                  @chips-changed=${this._onPinsChanged}
                              ></ir-header-chip-group>
                          `
                        : nothing}
                </div>
                <div class="rdetail-actions">
                    <div class="actions-top">
                        <button
                            class="stc-btn"
                            @click=${this._openSaveRoute}
                            ?disabled=${this._busy}
                            title=${t("wigs.save_as_wig")}
                        >
                            <ha-svg-icon
                                class="stc-wig"
                                .path=${ICON_WIG}
                            ></ha-svg-icon>
                            ${t("wigs.save_as_wig")}
                        </button>
                        <button
                            class="action-btn collapse-btn"
                            @click=${() =>
                                this.dispatchEvent(
                                    new CustomEvent("collapse", { bubbles: true, composed: true }),
                                )}
                            title=${t("common.close")}
                        >&#x2715;</button>
                    </div>
                    <button
                        class="settings-btn"
                        title=${t("devsettings.title")}
                        ?disabled=${this._busy}
                        @click=${() => (this._settingsOpen = true)}
                    >
                        <svg
                            class="settings-icon"
                            viewBox=${SETTINGS_VIEWBOX}
                        >
                            <path
                                d=${ICON_SETTINGS}
                                fill="currentColor"
                            ></path>
                        </svg>
                    </button>
                </div>
            </section>

            ${this.device.matrix
                ? html`<ir-matrix-card
                      .hass=${this.hass}
                      mode="send"
                      .summary=${this.device.matrix}
                      .cellsKey=${this.device.id}
                      .cellsLoader=${() => this.api.matrixCells(this.device.id)}
                      .currentName=${this._matrixCurrentName()}
                      ?busy=${this._busy}
                      @matrix-send=${this._matrixSend}
                      @matrix-save-command=${this._matrixSaveCommand}
                  ></ir-matrix-card>`
                : nothing}

            <!-- Commands -->
            <div class="commands-section">
                <div class="commands-header">
                    <span>${t("devdetail.commands", { count })}</span>
                </div>
                <!-- The detangle rows sit ABOVE the command rows
                     (owner ruling 2026-08-29), inside Commands and in
                     the same visual language, so the two read as one
                     list with the work that needs attention first. -->
                <ir-tangle-section
                    .hass=${this.hass}
                    .api=${this.api}
                    .deviceId=${this.device.id}
                    .matrixUnit=${this.device.matrix?.unit ?? "C"}
                ></ir-tangle-section>
                <div class="commands-list">
                    ${keyed(
                        this._commandsListVersion,
                        commands.length > 0
                            ? repeat(
                                  commands,
                                  (cmd) => cmd.id,
                                  (cmd) => html`
                                      <ir-command-row
                                          data-id=${cmd.id}
                                          .templateName=${cmd.name}
                                          .command=${cmd}
                                          .busy=${this._busy}
                                          .actionLabel=${this._getActionLabel(cmd.name)}
                                          .actionBadgeLabel=${badge?.sizerLabel ??
                                          null}
                                          .actionBadgeFontPx=${badge?.sizerFontPx ??
                                          null}
                                          .actionFontPx=${badge?.fontFor[
                                              this._getActionLabel(cmd.name) ??
                                                  t("cmdrow.actions")
                                          ] ?? null}
                                          .hasTrigger=${this._commandHasTrigger(cmd)}
                                          .triggerCount=${this._commandTriggerCount(cmd)}
                                          .showActionMapping=${this.device.device_type !== "other" &&
                                          !this.device.matrix}
                                          .showStar=${this.device
                                              .device_type === "ac" &&
                                          !cmd.matrix_cell}
                                          .starred=${this._isStarred(cmd.name)}
                                          @map-action=${this._onMapAction}
                                          @test=${this._onTest}
                                          @toggle-trigger=${this._onToggleTrigger}
                                          @toggle-tx-raw=${this._onToggleTxRaw}
                                          @edit-command=${this._onEditCommand}
                                          @rename-command=${this._onRenameCommand}
                                          @star-toggle=${this._onStarToggle}
                                          @delete=${this._onDelete}
                                      >
                                          <ha-svg-icon
                                              slot="status"
                                              class="grip-handle"
                                              .path=${ICON_GRIP}
                                              title=${t("devdetail.drag")}
                                          ></ha-svg-icon>
                                      </ir-command-row>
                                  `,
                              )
                            : html`<div class="empty">${t("devdetail.no_commands")}</div>`,
                    )}

                    ${this._mappingCommandName
                        ? html`
                              <div
                                  class="action-popover"
                                  style="top:${this._popoverTop}px; left:${this._popoverLeft}px"
                              >
                                  <div class="popover-header">${t("devdetail.map_action")}</div>
                                  ${this._getCurrentActionKey(this._mappingCommandName)
                                      ? html`
                                            <button
                                                class="popover-item clear"
                                                @click=${() => this._selectAction(this._mappingCommandName!, null)}
                                            >
                                                <span class="popover-label">${t("devdetail.none_clear")}</span>
                                            </button>
                                        `
                                      : ""}
                                  ${this._actionOptions.map((opt) => {
                                      const current = this._getCurrentActionKey(this._mappingCommandName!);
                                      const isCurrent = current === opt.key;
                                      const existing = this._getCommandForAction(opt.key);
                                      const isOther = existing && existing.toLowerCase() !== this._mappingCommandName!.toLowerCase();
                                      return html`
                                          <button
                                              class="popover-item ${isCurrent ? "active" : ""}"
                                              @click=${() => this._selectAction(this._mappingCommandName!, opt.key)}
                                          >
                                              <span class="popover-label">${tv(opt.label)}</span>
                                              ${isCurrent
                                                  ? html`<span class="popover-check">&#10003;</span>`
                                                  : isOther
                                                    ? html`<span class="popover-existing">${existing}</span>`
                                                    : ""}
                                          </button>
                                      `;
                                  })}
                                  ${this._customActionOpen
                                      ? html`
                                            <div class="custom-action-row">
                                                <input
                                                    class="custom-action-input"
                                                    type="text"
                                                    placeholder=${t("devdetail.custom_action_placeholder")}
                                                    .value=${this._customActionValue}
                                                    @input=${(e: Event) =>
                                                        (this._customActionValue = (
                                                            e.target as HTMLInputElement
                                                        ).value)}
                                                    @keydown=${(e: KeyboardEvent) => {
                                                        if (
                                                            e.key === "Enter" &&
                                                            this._customActionValue.trim()
                                                        ) {
                                                            void this._selectAction(
                                                                this._mappingCommandName!,
                                                                this._customActionValue.trim(),
                                                            );
                                                        }
                                                    }}
                                                />
                                                <button
                                                    class="custom-action-set"
                                                    ?disabled=${!this._customActionValue.trim()}
                                                    @click=${() =>
                                                        this._selectAction(
                                                            this._mappingCommandName!,
                                                            this._customActionValue.trim(),
                                                        )}
                                                >
                                                    ${t("devdetail.set")}
                                                </button>
                                            </div>
                                        `
                                      : html`
                                            <button
                                                class="popover-item custom-action-open"
                                                @click=${(e: Event) => {
                                                    e.stopPropagation();
                                                    this._customActionOpen = true;
                                                    this.updateComplete.then(() => {
                                                        this.shadowRoot
                                                            ?.querySelector<HTMLInputElement>(
                                                                ".custom-action-input",
                                                            )
                                                            ?.focus();
                                                    });
                                                }}
                                            >
                                                <span class="popover-label"
                                                    >${t("devdetail.custom_action")}</span
                                                >
                                            </button>
                                        `}
                              </div>
                          `
                        : ""}
                </div>
            </div>


            <div class="footer-actions">
                <div class="add-group">
                    <button
                        class="action-btn"
                        title=${t("devdetail.sniff_title")}
                        @click=${this._goToSniffer}
                        ?disabled=${this._busy}
                    >${t("devdetail.sniffed")}</button>
                    <button
                        class="action-btn"
                        title=${t("devdetail.clip_title")}
                        @click=${this._goToClips}
                        ?disabled=${this._busy}
                    >${t("devdetail.clipped")}</button>
                    <button
                        class="action-btn"
                        title=${t("devdetail.mirror_title")}
                        @click=${this._goToMirror}
                        ?disabled=${this._busy}
                    >${t("devdetail.mirrored")}</button>
                </div>
                <button
                    class="action-btn delete-btn"
                    @click=${this._requestDelete}
                    ?disabled=${this._busy}
                >${t("devdetail.delete_device")}</button>
            </div>

            <!-- Dialogs -->
            ${this._saveRouteOpen && !this._saveRoute
                ? html`<ir-save-route-dialog
                      ?hasSource=${!!this.device.source_wig_id}
                      .plan=${this._saveRoutePlan}
                      @route=${this._onSaveRoute}
                      @closed=${this._closeSaveFlow}
                  ></ir-save-route-dialog>`
                : ""}
            ${this._saveRoute === "new" && this._saveRoutePlan
                ? html`<ir-save-new-dialog
                      .api=${this.api}
                      sourceId=${this.device.id}
                      .plan=${this._saveRoutePlan}
                      @wig-saved=${this._onWigSaved}
                      @closed=${this._closeSaveFlow}
                  ></ir-save-new-dialog>`
                : ""}
            ${this._saveRoute === "update" && this._saveRoutePlan
                ? html`<ir-save-update-dialog
                      .api=${this.api}
                      sourceId=${this.device.id}
                      .plan=${this._saveRoutePlan}
                      @stale-replace=${this._onStaleReplace}
                      @wig-saved=${this._onWigSaved}
                      @closed=${this._closeSaveFlow}
                  ></ir-save-update-dialog>`
                : ""}
            ${this._saveRoute === "perfect"
                ? html`<ir-save-perfect-dialog
                      .api=${this.api}
                      source="device"
                      sourceId=${this.device.id}
                      sourceName=${this.device.name}
                      ?hasEmitter=${(this.device.emitter_entity_ids ?? [])
                          .length > 0}
                      .hass=${this.hass}
                      .plan=${this._saveRoutePlan}
                      @wig-saved=${this._onWigSaved}
                      @closed=${this._closeSaveFlow}
                  ></ir-save-perfect-dialog>`
                : ""}
            ${this._captureName
                ? html`
                      <ir-capture-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .device=${this.device}
                          .commandName=${this._captureName}
                          @closed=${this._onCaptureClosed}
                          @command-saved=${this._onCommandSaved}
                      ></ir-capture-dialog>
                  `
                : ""}
            ${this._commandToDelete
                ? html`
                      <ir-confirm-dialog
                          title=${this._commandToDelete.matrix_cell
                              ? t("devdetail.del_cell_title")
                              : t("devdetail.del_cmd_title")}
                          message=${this._commandToDelete.matrix_cell
                              ? t("devdetail.del_cell_msg", {
                                    name: this._commandToDelete.name,
                                })
                              : t("devdetail.del_cmd_msg", {
                                    name: this._commandToDelete.name,
                                })}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._confirmCommandDelete}
                          @closed=${() => (this._commandToDelete = null)}
                      ></ir-confirm-dialog>
                  `
                : ""}
            ${this._editCommand
                ? html`
                      <ir-signal-editor
                          .api=${this.api}
                          .deviceId=${this.device.id}
                          .commandId=${this._editCommand.id}
                          .initialPronto=${this._editCommand.code ?? ""}
                          .initialAlias=${this._editCommand.name}
                          .initialSendCount=${this._editCommand.send_count ?? 1}
                          .initialDitto=${this._editCommand.repeat_count ?? 1}
                          .initialTxForceRaw=${this._editCommand.tx_force_raw ?? false}
                          .initialDecodedProtocol=${this._editCommand
                              .decoded_protocol ?? null}
                          .hasTrigger=${this._commandHasTrigger(this._editCommand)}
                          @command-edited=${this._onCommandEdited}
                          @closed=${() => (this._editCommand = null)}
                      ></ir-signal-editor>
                  `
                : ""}
            ${this._triggerPopover
                ? html`
                      <ir-trigger-popover
                          .triggers=${this._triggersForCommand(
                              this._triggerPopover.command,
                          )}
                          .receivers=${this._receivers}
                          .top=${this._triggerPopover.top}
                          .left=${this._triggerPopover.left}
                          @create-new=${this._onTriggerPopoverCreateNew}
                          @edit-trigger=${this._onTriggerPopoverEdit}
                      ></ir-trigger-popover>
                  `
                : ""}
            ${this._triggerCommand
                ? html`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .protocol=${this._triggerCommand.protocol}
                          .code=${this._triggerCommand.code}
                          .byteHash=${this._triggerCommand.byte_hash ?? null}
                          .decodedFingerprint=${this._triggerCommand.decoded_fingerprint ?? null}
                          .sourceDeviceId=${this.device.id}
                          .sourceCommandId=${this._triggerCommand.id}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                      ></ir-trigger-dialog>
                  `
                : ""}
            ${this._triggerEdit
                ? html`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEdit}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${(e: CustomEvent) =>
                              this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `
                : ""}
            ${this._confirmDeleteTriggerId
                ? html`
                      <ir-confirm-dialog
                          title=${t("mirror.del_trigger_title")}
                          message=${t("devdetail.del_trigger_msg")}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${() => (this._confirmDeleteTriggerId = null)}
                      ></ir-confirm-dialog>
                  `
                : ""}
            ${this._settingsOpen
                ? html`
                      <ir-device-settings-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .device=${this.device}
                          @device-changed=${() => {
                              this._settingsOpen = false;
                              this.dispatchEvent(
                                  new CustomEvent("device-changed", {
                                      bubbles: true,
                                      composed: true,
                                  }),
                              );
                          }}
                          @closed=${() => (this._settingsOpen = false)}
                      ></ir-device-settings-dialog>
                  `
                : ""}
            ${this._toast
                ? html`<div class="toast" role="status">${this._toast}</div>`
                : ""}
        `;
    }

    static styles = [
        actionChipStyles,
        popoverStyles,
        settingsButtonStyles,
        exitToEntityButtonStyles,
        css`
        /* The 0.9.8 top-nudge and the 2026-08-15 10px right inset on
           .device-meta .settings-btn both retired
           with .device-meta itself (punch list item 9). The gear no
           longer floats in a grid row of its own where it needed
           nudging toward the command rows' trash column -- it is the
           bottom child of the header's anchored actions column now, and
           its right edge is meant to line up with the X directly above
           it. A 10px inset here would break exactly the alignment the
           handoff asks for. */
        /* SAVE TO CLOSET, in the header (RULED, mockup FR5 variant V2).
           It used to sit stacked under DELETE DEVICE in the bottom
           right, which put the door into the closet next to the button
           that destroys the device -- and buried the one action that
           ends the workflow. It now sits hard right of the device name,
           left of the X, matching the 0.8.8 card-header convention.

           GRAYS AND WHITE ONLY AT REST: no blues, no accents. The
           oxblood appears exclusively on hover, which keeps the
           closet's colour tied to intent rather than decoration. Hover
           also lifts the house gray background, the same 0.06 white
           every other button in the panel uses, so it reads as a
           button first and a closet second. */
        .stc-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            flex: none;
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            color: var(--secondary-text-color);
            font-size: 10.5px;
            font-weight: 500;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            font-family: inherit;
            padding: 4px 10px;
            cursor: pointer;
        }
        .stc-btn .stc-wig {
            --mdc-icon-size: 15px;
        }
        .stc-btn:hover:not(:disabled) {
            color: var(--primary-text-color);
            border-color: #8e3b3b;
            background: rgba(255, 255, 255, 0.06);
        }
        .stc-btn:hover:not(:disabled) .stc-wig {
            color: #b05050;
        }
        .stc-btn:disabled {
            opacity: 0.4;
            cursor: default;
        }
        /* DELETE DEVICE, hard right of the add-signal row (owner ruling
           2026-08-03). It used to sit on its own full-width line below,
           which was correct when SAVE TO CLOSET was stacked above it and
           the pair needed their own company; SAVE moved to the header
           (FR5) and left one button alone under a mostly empty row.

           PINNED WITH margin-left:auto, NOT the container's
           justify-content. space-between distributes per WRAPPED LINE,
           so on a card narrow enough to break the four buttons 2-and-2
           it would spread the second line to both edges with a hole in
           the middle. margin-left:auto puts the button at the right of
           whatever line it lands on, which is the same result on a wide
           card and the correct one on a phone. */
        .footer-actions > .delete-btn {
            margin-left: auto;
        }

        :host {
            display: block;
        }

        /* --- Header (punch list item 9, header-pin-layout-handoff.md,
           owner-approved 2026-08-16) ------------------------------
           The same structural pattern the Remote detail header uses, so
           the two read as one family: title block, full-height divider,
           colon-aligned chip rows, anchored actions column. What was
           two separate blocks (a .header row plus a .device-meta grid)
           is one flex row now.

           align-items: stretch is load-bearing -- it is what lets the
           actions column span the full header height, which is what the
           X/gear anchoring below depends on. */
        .header {
            display: flex;
            align-items: stretch;
            gap: 16px;
        }
        /* Title block is a column now: the name row, then Type directly
           under it. Type is a property of the device itself, so it
           belongs with the name rather than sitting in a hardware-picker
           row beside Emitters and Pinned. */
        .rtitle-block {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 6px;
            flex-shrink: 0;
            min-width: 0;
        }
        /* New here -- today's shipped Device header has no divider at
           all; the Remote header's was a short stub. Full height on
           both now. */
        .rdetail-divider {
            width: 1px;
            align-self: stretch;
            background: var(--divider-color);
            flex-shrink: 0;
        }
        .hdr-rows {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 11px;
            flex: 1;
            min-width: 0;
        }
        /* THE ANCHORING (owner: "right now it seems to move"). Stretched
           column + space-between pins the first child to the top edge
           and the last to the bottom edge regardless of how tall the
           chip rows grow. Structural, not a pixel offset -- and
           deliberately NOT position: absolute, which would break the
           moment the card's content-driven height changes.

           Device-specific: the first child is a ROW of two buttons
           (Save to Closet, then X) rather than a single button, so that
           whole cluster anchors to the top as a unit. The gear stays
           alone at the bottom. */
        .rdetail-actions {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-self: stretch;
            flex-shrink: 0;
        }
        .rdetail-actions .actions-top {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .rdetail-actions .settings-btn {
            align-self: flex-end;
        }
        .name-row {
            display: flex;
            align-items: center;
            gap: 6px;
            min-width: 0;
        }
        h1 {
            font-size: 1.5rem;
            margin: 0;
        }
        .editable-name {
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .edit-icon {
            font-size: 0.75rem;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .editable-name:hover .edit-icon {
            opacity: 1;
        }
        .name-input {
            font-size: 1.5rem;
            font-family: inherit;
            font-weight: bold;
            border: none;
            border-bottom: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-text-color);
            outline: none;
            flex: 1;
            min-width: 0;
            padding: 0 0 2px;
        }
        .header .action-btn.collapse-btn {
            flex-shrink: 0;
            align-self: center;
        }
        /* Punch list item 23: ONE fixed square box for both actions.
           Item 17 aligned the button EDGES and they do align -- but a
           box's edge is not what the eye reads, its glyph is, and the
           two glyphs sat at different insets because the two buttons
           carried different padding (this X had 2px 8px, the Remote
           header's had 4px, the shared gear has 5px around a 29px
           icon). Right-aligning boxes of different widths lines up the
           right edges and nothing else.

           Equal squares fix it by construction rather than by
           arithmetic: each glyph is centered in its own box, the boxes
           are the same size, and their right edges already coincide,
           so the glyph centers coincide too -- on this header and on
           the Remote's, which carries the identical rule. Nothing here
           needs to be re-derived if a glyph or a font size changes
           later. */
        .rdetail-actions .action-btn.collapse-btn,
        .rdetail-actions .settings-btn {
            width: 32px;
            height: 32px;
            min-width: 32px;
            padding: 0;
            box-sizing: border-box;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        /* .device-meta RETIRED (punch list item 9). It was a three-column
           grid holding Type, the chip groups and the gear on a row of
           its own below the header. All four moved into the single
           header block above: Type into the title block, the chip groups
           into .hdr-rows, the gear into the anchored actions column. The
           grid's sizing comments went with it -- the Type column no
           longer competes with a chip column for width, since it now
           sits under the name. */

        /* TYPE one-line (owner ruling 2026-08-15, still true): label
           beside the control instead of stacked above it, matching how
           ir-header-chip-group.ts's own row label sits beside its chips
           -- same bold/uppercase/colon treatment, colon baked into the
           devdetail.type locale string the same way
           hdrchips.emitters_label already carries its own. */
        .stack {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .stack .sl {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        /* Below this the title block, a useful chip column and the
           actions column stop fitting on one line. The header wraps to
           a column: title block first, then the chip rows full width,
           with the actions column riding along the top on its own line.
           The divider has nothing to divide once they stack, so it goes.

           The anchoring rule is unaffected -- it governs the actions
           column's own two edges, which still hold whenever the header
           is a row. */
        @media (max-width: 700px) {
            .header {
                flex-wrap: wrap;
                align-items: flex-start;
                gap: 12px;
            }
            .rtitle-block {
                flex: 1;
            }
            .rdetail-divider {
                display: none;
            }
            .hdr-rows {
                flex-basis: 100%;
                order: 3;
            }
            .rdetail-actions {
                align-self: flex-start;
            }
        }
        .stack select {
            box-sizing: border-box;
            padding: 3px 10px 3px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 11.5px;
        }
        /* Type lock (matrix-power-row.md item 4): a matrix device's
           type control is a static label, not a dropdown -- sized to
           match .stack select so swapping the two doesn't jump the
           row, but unclickable and dimmed just enough to read as
           fixed rather than editable. */
        .type-locked {
            display: block;
            box-sizing: border-box;
            padding: 3px 10px 3px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--secondary-text-color);
            font-family: inherit;
            font-size: 11.5px;
            cursor: default;
        }

        /* --- Buttons --- */
        .action-btn.collapse-btn {
            font-size: 1rem;
            padding: 2px 8px;
            color: var(--secondary-text-color);
            border-color: transparent;
        }
        .action-btn.collapse-btn:hover {
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
        }

        /* --- Commands section (Sniffer-style) --- */
        /* The margin, the rule and the padding used to stack to nearly
           30px of dead air between the emitters row and the word
           "Commands" -- against a 4px rhythm inside the list itself.
           That contrast is what read as loose; the rule alone already
           separates the two blocks (owner ruling 2026-08-03). */
        .commands-section {
            margin: 12px 0;
            border-top: 1px solid var(--divider-color);
            padding-top: 9px;
        }
        .commands-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--primary-text-color);
        }
        .commands-list {
            display: flex;
            flex-direction: column;
        }
        /* --- Drag handle (slotted into ir-command-row's status column) --- */
        .grip-handle {
            --mdc-icon-size: 18px;
            color: var(--secondary-text-color);
            opacity: 0.6;
            cursor: grab;
            transition: opacity 120ms ease;
        }
        .grip-handle:hover {
            opacity: 1;
        }
        .grip-handle:active {
            cursor: grabbing;
        }
        /* SortableJS applies this class to the element being dragged. */
        ir-command-row.sortable-ghost {
            opacity: 0.4;
        }
        /* Action-popover styles live in the shared ir-popover-styles module
           (spread into static styles below) so ir-trigger-popover reuses the
           exact same treatment. */
        .empty {
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 12px 0;
        }
        /* No justify-content: it was space-between and had been inert
           for as long as .delete-row forced its own line, since one item
           per flex line has no free space to distribute. Leaving it
           would read as the thing pinning DELETE right, and it is not
           -- see .footer-actions > .delete-btn above.
           Bottom margin is 0: the card's own 16px padding is the gap,
           and doubling it left 32px of nothing under the row. */
        .footer-actions {
            display: flex;
            align-items: center;
            margin: 11px 0 0;
            flex-wrap: wrap;
            gap: 8px;
        }
        .add-group {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            /* Align with the command NAME column above: 10px row
               padding + 32px grip column + 12px grid gap (owner
               layout, 2026-07-20 -- the eye line runs straight down
               from the signal names into these buttons). */
            margin-left: 54px;
        }

        /* --- Toast --- */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--primary-color);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            z-index: 100;
        }

        /* Custom action entry (free-form key) inside the Map action
           popover. Input + Set on one row, matching popover chrome. */
        .custom-action-row {
            display: flex;
            gap: 6px;
            padding: 6px 10px 8px;
            align-items: center;
        }
        .custom-action-input {
            flex: 1;
            min-width: 0;
            padding: 5px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.8rem;
            font-family: var(--code-font-family, monospace);
            box-sizing: border-box;
        }
        .custom-action-input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .custom-action-set {
            border: 1px solid var(--divider-color);
            background: none;
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            color: var(--primary-text-color);
        }
        .custom-action-set:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .custom-action-set:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-detail": IrDeviceDetail;
    }
}
