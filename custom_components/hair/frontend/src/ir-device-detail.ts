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

/** Action-badge sizing constants (owner ruling, 2026-08-01).
 *  The cap is the width the badge is allowed to reserve before its label
 *  starts stepping down a font tier. 96px clears fan (90px) and
 *  media_player (93px) at full size, so the common device types never
 *  shrink at all; light is the one type that steps down. */
const ACTION_BADGE_CAP_PX = 96;
const ACTION_BADGE_FONT_LADDER = [10.5, 9.5, 9];
const ACTION_BADGE_WEIGHT = 500;
const ACTION_BADGE_TRACKING = 0.03; // letter-spacing, em
const ACTION_BADGE_CHROME_PX = 22; // 10px padding + 1px border, both sides
import "./ir-capture-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-save-perfect-dialog.js";
import "./ir-save-route-dialog.js";
import "./ir-save-new-dialog.js";
import "./ir-save-update-dialog.js";
import "./ir-emitter-picker.js";
import type { SaveRoute } from "./ir-save-route-dialog.js";
import "./ir-signal-editor.js";
import "./ir-trigger-dialog.js";
import "./ir-trigger-popover.js";
import { popoverStyles } from "./ir-popover-styles.js";
// The house wig, from images/wig.svg. Same glyph the closet wears,
// because this button is the door into it (FR5).
import { ICON_WIG } from "./ir-wigs.js";
import type { HairApi } from "./api.js";
import type {
    ActionOption,
    IRCommand,
    IRDevice,
    IRTrigger,
    DeviceTypeId,
    MatrixCellCoord,
    MatrixCells,
    ReceiverInfo,
    SavePlan,
} from "./types.js";
import { displayTemp, installUnit } from "./temperature.js";

// MDI: drag (six-dot grip)
const ICON_GRIP =
    "M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";

/** Debounce delay (ms) between drag end and WS save. */
const REORDER_DEBOUNCE_MS = 500;

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

    @state() private _busy = false;
    @state() private _captureName: string | null = null;
    @state() private _toast: string | null = null;
    @state() private _confirmDelete = false;
    /** Second Fitting v3: the decision window's own plan, fetched once
     * when SAVE TO CLOSET is clicked and handed straight into whatever
     * dialog the chosen route opens next -- neither the window nor the
     * dialog it routes to fetches a second copy. Null closes the
     * whole save flow; non-null with `_saveRoute` unset shows the
     * window itself. */
    @state() private _saveRoutePlan: SavePlan | null = null;
    /** Which route the window's own buttons chose. VALIDATE FOR
     * PERFECT FIT still opens the pre-v3 dialog until Commit 5 gives
     * it a stripped, purpose-built one of its own -- see the Commit 3
     * and 4 commit messages for the sequencing note. */
    @state() private _saveRoute: SaveRoute | null = null;
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

    // State-matrix cell browser (Cold Cuts second half, mockup CC3).
    // The lattice loads lazily the first time the card renders and is
    // cached per device id; a load failure leaves the card summary-only
    // rather than dead. Selection is one branch (mode, then fan/swing
    // as the branch offers them) plus one temperature tile.
    @state() private _matrixCells: MatrixCells | null = null;
    private _matrixCellsFor: string | null = null;
    @state() private _selMode: string | null = null;
    @state() private _selFan: string | null = null;
    @state() private _selSwing: string | null = null;
    @state() private _selTemp: number | null = null;

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

    private async _refresh() {
        this.device = await this.api.getDevice(this.device.id);
        this.dispatchEvent(
            new CustomEvent("device-changed", {
                bubbles: true,
                composed: true,
            }),
        );
    }

    private _flash(message: string) {
        this._toast = message;
        setTimeout(() => {
            this._toast = null;
        }, 2400);
    }

    /** Second Fitting v3: SAVE TO CLOSET opens the decision window
     * first, always -- fetching the plan once, up front, so its own
     * source line and delta summary are never a guess. A failed fetch
     * falls back to the old Perfect-Fit-route dialog directly, which
     * retries the same call and carries its own inline error banner. */
    private async _openSaveRoute(): Promise<void> {
        if (this._busy) return;
        try {
            this._saveRoutePlan = await this.api.wigsSavePlan(
                this.device.id,
            );
        } catch (err) {
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

    private _closeSaveFlow = (): void => {
        this._saveRoute = null;
        this._saveRoutePlan = null;
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
            this._flash(t("devdetail.emitters_updated"));
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
        // Lazy matrix load, once per device id: the card renders its
        // summary immediately and the cell browser fills in when the
        // lattice arrives.
        if (this.device.matrix && this._matrixCellsFor !== this.device.id) {
            this._matrixCellsFor = this.device.id;
            void this._loadMatrixCells();
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
     *  action can no longer grow the button and shove the buttons after it
     *  sideways. Measured once here rather than per render, and only to
     *  choose a font tier -- the actual width is settled in CSS by a hidden
     *  copy of the widest label, which stays correct in any language.
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
        // measureText knows nothing about letter-spacing, and the badge
        // carries 0.03em; the chrome is the 10px side padding plus 1px
        // border, doubled.
        const widthOf = (text: string, px: number): number => {
            ctx.font = `${ACTION_BADGE_WEIGHT} ${px}px ${family}`;
            return (
                ctx.measureText(text).width +
                text.length * px * ACTION_BADGE_TRACKING +
                ACTION_BADGE_CHROME_PX
            );
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

        // Position popover near the badge button using fixed viewport coords.
        const badge = (e.target as LitElement).shadowRoot?.querySelector(".badge-btn") as HTMLElement | null;
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

    private async _deleteDevice() {
        this._busy = true;
        try {
            await this.api.deleteDevice(this.device.id);
            this.dispatchEvent(
                new CustomEvent("device-deleted", {
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._flash(`Delete failed: ${(err as Error).message}`);
        } finally {
            this._busy = false;
            this._confirmDelete = false;
        }
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

    private async _loadMatrixCells(): Promise<void> {
        this._matrixCells = null;
        try {
            const cells = await this.api.matrixCells(this.device.id);
            this._matrixCells = cells;
            if (cells.modes.length > 0) {
                this._select(cells.modes[0], null, null, null);
            }
        } catch {
            // Summary-only card; the backend already logged why.
            this._matrixCells = null;
        }
    }

    /** Fan values the mode branch actually holds, in vocabulary order. */
    private _fansFor(mode: string): string[] {
        const mc = this._matrixCells!;
        const seen = new Set<string>();
        for (const c of mc.cells) {
            if (c.m === mode && c.f !== undefined) seen.add(c.f);
        }
        return mc.fan_modes.filter((f) => seen.has(f));
    }

    /** Swing values under (mode, fan), in vocabulary order. */
    private _swingsFor(mode: string, fan: string | null): string[] {
        const mc = this._matrixCells!;
        const seen = new Set<string>();
        for (const c of mc.cells) {
            if (
                c.m === mode &&
                (c.f ?? null) === fan &&
                c.s !== undefined
            ) {
                seen.add(c.s);
            }
        }
        return mc.swing_modes.filter((s) => seen.has(s));
    }

    /** Every cell of the selected branch (exact dimension match --
     * absent dimensions pair only with null, mirroring exact_cell). */
    private _branchCells(
        mode: string,
        fan: string | null,
        swing: string | null,
    ): MatrixCellCoord[] {
        return this._matrixCells!.cells.filter(
            (c) =>
                c.m === mode &&
                (c.f ?? null) === fan &&
                (c.s ?? null) === swing,
        );
    }

    /** Move the selection, re-resolving the deeper dimensions so the
     * result is always a branch the matrix actually has: a fan/swing
     * that vanished with the mode change falls to the branch's first,
     * a temperature falls to the nearest available (middle when the
     * branch is fresh -- the entity's resolve_cell default). */
    private _select(
        mode: string,
        fan: string | null,
        swing: string | null,
        temp: number | null,
    ): void {
        const fans = this._fansFor(mode);
        const useFan =
            fan !== null && fans.includes(fan) ? fan : (fans[0] ?? null);
        const swings = this._swingsFor(mode, useFan);
        const useSwing =
            swing !== null && swings.includes(swing)
                ? swing
                : (swings[0] ?? null);
        const temps = this._branchCells(mode, useFan, useSwing)
            .filter((c) => c.t !== undefined)
            .map((c) => c.t!)
            .sort((a, b) => a - b);
        let useTemp: number | null = null;
        if (temps.length > 0) {
            if (temp === null) {
                useTemp = temps[Math.floor(temps.length / 2)];
            } else if (temps.includes(temp)) {
                useTemp = temp;
            } else {
                useTemp = temps.reduce((best, x) =>
                    Math.abs(x - temp) < Math.abs(best - temp) ? x : best,
                );
            }
        }
        this._selMode = mode;
        this._selFan = useFan;
        this._selSwing = useSwing;
        this._selTemp = useTemp;
    }

    /** The exact cell the selection points at, or null mid-load. */
    private _selectedCell(): MatrixCellCoord | null {
        if (!this._matrixCells || this._selMode === null) return null;
        return (
            this._branchCells(
                this._selMode,
                this._selFan,
                this._selSwing,
            ).find((c) => (c.t ?? null) === this._selTemp) ?? null
        );
    }

    /** One matrix temperature as display text, converted to the
     * viewer's install unit when it differs from the matrix's native
     * unit (unit ruling 2026-07-29). Display-only: coordinates and
     * the absent-tile walk stay native. */
    private _displayTemp(temp: number): string {
        const mc = this._matrixCells;
        return displayTemp(
            temp,
            mc?.unit ?? "C",
            installUnit(this.hass),
            mc?.precision ?? 1,
        );
    }

    /** The CC4 display grammar, client-side: mode bare, fan and swing
     * labeled, temperature a bare number last. Must mirror
     * wig_climate.cell_display_name byte-for-byte -- the current-tile
     * glow compares this against the entity's matrix_cell attribute,
     * which the backend also converts to the install's unit at send
     * time, so the temperature part converts here too. */
    private _cellName(c: MatrixCellCoord): string {
        const parts = [c.m];
        if (c.f !== undefined) parts.push(`fan: ${c.f}`);
        if (c.s !== undefined) parts.push(`swing: ${c.s}`);
        if (c.t !== undefined) parts.push(this._displayTemp(c.t));
        return parts.join(" / ");
    }

    private async _matrixSend(): Promise<void> {
        const cell = this._selectedCell();
        if (!cell) return;
        this._busy = true;
        try {
            const result = await this.api.matrixSend(this.device.id, {
                mode: cell.m,
                fan: cell.f ?? null,
                swing: cell.s ?? null,
                temp: cell.t ?? null,
            });
            this._flash(t("devdetail.sent_cmd", { name: result.sent }));
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

    private async _matrixSaveCommand(): Promise<void> {
        const cell = this._selectedCell();
        if (!cell) return;
        this._busy = true;
        try {
            // The response IS the refreshed full device (the saved
            // state replaces by name, so the list never twins).
            this.device = await this.api.matrixCommand(this.device.id, {
                mode: cell.m,
                fan: cell.f ?? null,
                swing: cell.s ?? null,
                temp: cell.t ?? null,
            });
            this._flash(
                t("devdetail.saved", { name: this._cellName(cell) }),
            );
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

    /** One dimension chip row (Mode / Fan / Swing). */
    private _renderDimRow(
        label: string,
        values: string[],
        selected: string | null,
        pick: (value: string) => void,
    ) {
        return html`
            <div class="mx-dim-row">
                <span class="mx-dim-label">${label}</span>
                <span class="mx-chips">
                    ${values.map(
                        (v) => html`<button
                            class="mx-chip ${v === selected ? "on" : ""}"
                            @click=${() => pick(v)}
                        >
                            ${v}
                        </button>`,
                    )}
                </span>
            </div>
        `;
    }

    /** The temperature tiles of the selected branch: present tiles
     * show the number, absent positions (branch min to max stepping
     * precision) render dashed and inert, the selected tile fills
     * cold blue, and the tile matching the entity's current cell
     * wears the cold glow ring. Depth-limited branches (no
     * temperature dimension) render one bare tile for the branch. */
    private _renderMatrixGrid(currentName: string | null) {
        const mode = this._selMode!;
        const branch = this._branchCells(
            mode,
            this._selFan,
            this._selSwing,
        );
        const byTemp = new Map<number, MatrixCellCoord>();
        for (const c of branch) {
            if (c.t !== undefined) byTemp.set(c.t, c);
        }
        const temps = [...byTemp.keys()].sort((a, b) => a - b);
        if (temps.length === 0) {
            const bare = branch.find((c) => c.t === undefined) ?? null;
            if (!bare) return nothing;
            const isCurrent =
                currentName !== null &&
                this._cellName(bare) === currentName;
            return html`<div class="mx-grid">
                <button
                    class="mx-tile sel ${isCurrent ? "cur" : ""}"
                    @click=${() =>
                        this._select(
                            mode,
                            this._selFan,
                            this._selSwing,
                            null,
                        )}
                >
                    ${mode}
                </button>
            </div>`;
        }
        const step =
            this._matrixCells!.precision > 0
                ? this._matrixCells!.precision
                : 1;
        const positions: number[] = [];
        for (
            let x = temps[0];
            x <= temps[temps.length - 1] + step / 2;
            x += step
        ) {
            // Two-decimal rounding keeps 0.5-precision walks exact.
            positions.push(Math.round(x * 100) / 100);
        }
        return html`<div class="mx-grid">
            ${positions.map((pos) => {
                const cell = byTemp.get(pos);
                if (!cell) {
                    return html`<button
                        class="mx-tile absent"
                        disabled
                        title=${t("devices.matrix_absent")}
                    >
                        ${this._displayTemp(pos)}
                    </button>`;
                }
                const isCurrent =
                    currentName !== null &&
                    this._cellName(cell) === currentName;
                return html`<button
                    class="mx-tile ${pos === this._selTemp ? "sel" : ""} ${
                        isCurrent ? "cur" : ""
                    }"
                    @click=${() =>
                        this._select(
                            mode,
                            this._selFan,
                            this._selSwing,
                            pos,
                        )}
                >
                    ${this._displayTemp(pos)}
                </button>`;
            })}
        </div>`;
    }

    /** The STATE MATRIX card (mockups CC3/CC4): summary header, the
     * entity's current-cell readout, one-branch dimension chips, the
     * temperature tile grid, and the action bar (send the state, or
     * save it as a command). The lattice loads lazily; until it
     * arrives (or if it cannot), the card stays summary-only. */
    private _renderMatrixCard() {
        const m = this.device.matrix!;
        const current =
            this._climateState()?.attributes?.matrix_cell ?? null;
        const mc = this._matrixCells;
        // Summary range: converted to the viewer's unit with the unit
        // letter as suffix ("61 to 86 F"); when converted, the file's
        // native range rides in a title tooltip (chosen over parens:
        // the one-line summary is already five facts long). Precision
        // comes from the loaded lattice when available; summary-only
        // renders fall back to whole degrees, which corpus bounds are.
        const viewUnit = installUnit(this.hass);
        const converted = viewUnit !== m.unit;
        const rangeTitle = converted
            ? t("devices.matrix_native_range", {
                  min: String(m.min_temp),
                  max: String(m.max_temp),
                  unit: m.unit,
              })
            : "";
        const summaryText = t("devices.matrix_summary", {
            cells: String(m.cells),
            modes: String(m.modes.length),
            fans: String(m.fan_modes.length),
            min: displayTemp(
                m.min_temp,
                m.unit,
                viewUnit,
                mc?.precision ?? 1,
            ),
            max: displayTemp(
                m.max_temp,
                m.unit,
                viewUnit,
                mc?.precision ?? 1,
            ),
            unit: viewUnit,
        });
        const selected = this._selectedCell();
        const fans =
            mc && this._selMode !== null
                ? this._fansFor(this._selMode)
                : [];
        const swings =
            mc && this._selMode !== null
                ? this._swingsFor(this._selMode, this._selFan)
                : [];
        return html`
            <div class="matrix-card">
                <div class="mx-head">
                    <span class="mx-title">${t("devices.matrix_title")}</span>
                    <span class="mx-summary" title=${rangeTitle}>
                        ${summaryText}
                    </span>
                </div>
                ${current != null
                    ? html`<div class="matrix-current">
                          ${t("devices.matrix_current", { cell: current })}
                      </div>`
                    : nothing}
                ${mc && this._selMode !== null
                    ? html`
                          ${this._renderDimRow(
                              t("devices.matrix_dim_mode"),
                              mc.modes,
                              this._selMode,
                              (v) =>
                                  this._select(
                                      v,
                                      this._selFan,
                                      this._selSwing,
                                      this._selTemp,
                                  ),
                          )}
                          ${fans.length > 0
                              ? this._renderDimRow(
                                    t("devices.matrix_dim_fan"),
                                    fans,
                                    this._selFan,
                                    (v) =>
                                        this._select(
                                            this._selMode!,
                                            v,
                                            this._selSwing,
                                            this._selTemp,
                                        ),
                                )
                              : nothing}
                          ${swings.length > 0
                              ? this._renderDimRow(
                                    t("devices.matrix_dim_swing"),
                                    swings,
                                    this._selSwing,
                                    (v) =>
                                        this._select(
                                            this._selMode!,
                                            this._selFan,
                                            v,
                                            this._selTemp,
                                        ),
                                )
                              : nothing}
                          ${this._renderMatrixGrid(current)}
                          <div class="mx-actions">
                              <span class="mx-set">
                                  ${selected
                                      ? t("devices.matrix_set_state", {
                                            name: this._cellName(selected),
                                        })
                                      : nothing}
                              </span>
                              <button
                                  class="action-btn test-btn"
                                  ?disabled=${this._busy || !selected}
                                  @click=${this._matrixSend}
                              >
                                  ${t("fitting.send")}
                              </button>
                              <button
                                  class="action-btn mx-cmd-btn"
                                  ?disabled=${this._busy || !selected}
                                  @click=${this._matrixSaveCommand}
                              >
                                  ${t("devices.matrix_add_command")}
                              </button>
                          </div>
                      `
                    : nothing}
            </div>
        `;
    }

    // ---------------------------------------------------------------
    // Render
    // ---------------------------------------------------------------

    render() {
        const commands = this.device.commands;
        const badge = this._actionBadgeMetrics();
        const count = commands.length;

        return html`
            <!-- Header: editable name + delete -->
            <section class="header">
                <div class="header-left">
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
                </div>
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
                    @click=${() => this.dispatchEvent(new CustomEvent("collapse", { bubbles: true, composed: true }))}
                    title=${t("common.close")}
                >&#x2715;</button>
            </section>

            <!-- Device metadata: two columns, each label above its own
                 control (comp L1) -->
            <div class="device-meta">
                <div class="stack">
                    <span class="sl">${t("devdetail.type")}</span>
                    <select
                        .value=${this.device.device_type}
                        @change=${this._onTypeChanged}
                        ?disabled=${this._busy}
                    >
                        ${DEVICE_TYPES.map(
                            (dt) => html`
                                <option
                                    value=${dt.value}
                                    ?selected=${this.device.device_type === dt.value}
                                >
                                    ${t(`device_type.${dt.value}`)}
                                </option>
                            `,
                        )}
                    </select>
                </div>
                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this.device.emitter_entity_ids ?? []}
                    ?disabled=${this._busy}
                    @emitters-changed=${this._onEmittersChanged}
                ></ir-emitter-picker>
            </div>

            ${this.device.matrix ? this._renderMatrixCard() : nothing}

            <!-- Commands -->
            <div class="commands-section">
                <div class="commands-header">
                    <span>${t("devdetail.commands", { count })}</span>
                </div>
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
                                          @map-action=${this._onMapAction}
                                          @test=${this._onTest}
                                          @toggle-trigger=${this._onToggleTrigger}
                                          @toggle-tx-raw=${this._onToggleTxRaw}
                                          @edit-command=${this._onEditCommand}
                                          @rename-command=${this._onRenameCommand}
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
                    @click=${() => (this._confirmDelete = true)}
                    ?disabled=${this._busy}
                >${t("devdetail.delete_device")}</button>
            </div>

            <!-- Dialogs -->
            ${this._saveRoutePlan && !this._saveRoute
                ? html`<ir-save-route-dialog
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
                      @closed=${this._closeSaveFlow}
                  ></ir-save-new-dialog>`
                : ""}
            ${this._saveRoute === "update" && this._saveRoutePlan
                ? html`<ir-save-update-dialog
                      .api=${this.api}
                      sourceId=${this.device.id}
                      .plan=${this._saveRoutePlan}
                      @stale-replace=${this._onStaleReplace}
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
            ${this._confirmDelete
                ? html`
                      <ir-confirm-dialog
                          title=${t("devdetail.del_device_title", { name: this.device.name })}
                          message=${t("devdetail.del_device_msg")}
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._deleteDevice}
                          @closed=${() => (this._confirmDelete = false)}
                      ></ir-confirm-dialog>
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
            ${this._toast
                ? html`<div class="toast" role="status">${this._toast}</div>`
                : ""}
        `;
    }

    static styles = [
        actionChipStyles,
        popoverStyles,
        css`
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

        /* --- Header --- */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }
        .header-left {
            flex: 1;
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
            width: 100%;
            padding: 0 0 2px;
        }
        .header .action-btn.collapse-btn {
            flex-shrink: 0;
            align-self: center;
        }

        /* --- Metadata: two columns, no label gutter (comp L1) ---
           The old grid reserved a fixed 80px column for two words and
           left the controls floating in what remained, which is what
           made the row read as a form from 2004. Each label sits above
           its own control now, and each control gets the full width of
           its own column. TYPE is capped at 200px because a seven-item
           dropdown never needed 900; emitters take the rest and wrap. */
        .device-meta {
            display: grid;
            grid-template-columns: 200px minmax(0, 1fr);
            gap: 0 22px;
            align-items: start;
            margin: 16px 0 0;
        }
        .stack .sl {
            display: block;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--secondary-text-color);
            margin-bottom: 5px;
        }
        /* Below this, 200px plus a useful chip column stops fitting. */
        @media (max-width: 700px) {
            .device-meta {
                grid-template-columns: minmax(0, 1fr);
                gap: 12px 0;
            }
        }
        /* The STATE MATRIX card (Cold Cuts second half, mockup CC3):
           the cell browser in the cold-blue family (#58a6d8) -- the
           stateful signature the closet's fit-tick glow introduced.
           Everything in here is the card's own dialect; the action bar
           reuses the shared chip anatomy. */
        .matrix-card {
            margin-top: 12px;
            padding: 9px 12px 10px;
            border: 1px solid rgba(88, 166, 216, 0.45);
            border-radius: 8px;
            font-size: 0.85rem;
            color: var(--primary-text-color);
            line-height: 1.5;
        }
        .mx-head {
            display: flex;
            align-items: baseline;
            gap: 10px;
            flex-wrap: wrap;
        }
        .mx-title {
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #58a6d8;
        }
        .mx-summary {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
        }
        .matrix-current {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        .mx-dim-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 8px;
        }
        .mx-dim-label {
            flex: none;
            width: 44px;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: var(--secondary-text-color);
        }
        .mx-chips {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .mx-chip {
            font-size: 0.75rem;
            font-family: inherit;
            padding: 3px 10px;
            border-radius: 12px;
            border: 1px solid var(--divider-color);
            background: none;
            color: var(--primary-text-color);
            cursor: pointer;
            transition: background 150ms ease, border-color 150ms ease;
        }
        .mx-chip:hover {
            border-color: rgba(88, 166, 216, 0.6);
        }
        .mx-chip.on {
            background: #58a6d8;
            border-color: #58a6d8;
            color: #fff;
        }
        .mx-grid {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        .mx-tile {
            width: 52px;
            height: 38px;
            box-sizing: border-box;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            background: none;
            font-family: inherit;
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--primary-text-color);
            cursor: pointer;
            transition: background 150ms ease, border-color 150ms ease,
                        box-shadow 300ms ease;
        }
        .mx-tile:hover:not(:disabled):not(.sel) {
            border-color: rgba(88, 166, 216, 0.6);
        }
        /* Absent position: the matrix is sparse and says so -- dashed,
           inert, dimmed, with the tooltip carrying the sentence. */
        .mx-tile.absent {
            border-style: dashed;
            color: var(--secondary-text-color);
            opacity: 0.45;
            cursor: default;
        }
        .mx-tile.sel {
            background: #58a6d8;
            border-color: #58a6d8;
            color: #fff;
        }
        /* The entity's CURRENT cell wears the cold glow ring, whatever
           else it is -- same cue language as the closet's matrix tick. */
        .mx-tile.cur {
            box-shadow:
                0 0 0 2px rgba(88, 166, 216, 0.5),
                0 0 10px rgba(88, 166, 216, 0.55);
        }
        .mx-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid var(--divider-color);
        }
        .mx-set {
            flex: 1;
            min-width: 0;
            font-size: 0.8rem;
            color: var(--primary-text-color);
            font-family: var(--code-font-family, monospace);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        /* Save-state-as-command wears the Clipper's copper: it does the
           same kind of thing as Add Signal -- one more command row. */
        .action-btn.mx-cmd-btn {
            color: #b87333;
            border-color: rgba(184, 115, 51, 0.35);
        }
        .action-btn.mx-cmd-btn:hover:not(:disabled) {
            background: rgba(184, 115, 51, 0.08);
        }
        .stack select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
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
