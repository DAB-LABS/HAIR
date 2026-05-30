/**
 * Device detail view: editable header (name, type, emitter),
 * read-only hardware cards (TX / RX), flat command list.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import Sortable from "sortablejs";
import "./ir-command-row.js";
import "./ir-capture-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-emitter-picker.js";
import "./ir-trigger-dialog.js";
import type { HairApi } from "./api.js";
import type { ActionOption, IRCommand, IRDevice, IRTrigger, DeviceTypeId } from "./types.js";

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
    @state() private _commandToDelete: IRCommand | null = null;

    // Action mapping
    @state() private _actionOptions: ActionOption[] = [];
    @state() private _mappingCommandName: string | null = null;
    @state() private _popoverTop = 0;
    @state() private _popoverLeft = 0;
    private _dismissHandler: ((e: MouseEvent) => void) | null = null;

    // Inline name editing
    @state() private _editingName = false;
    @state() private _draftName = "";

    // Triggers
    @state() private _triggers: IRTrigger[] = [];
    @state() private _triggerCommand: IRCommand | null = null;
    @state() private _triggerEdit: IRTrigger | null = null;
    @state() private _confirmDeleteTriggerId: string | null = null;

    // Command reorder (SortableJS lifecycle)
    private _sortable: Sortable | null = null;
    private _sortableBefore: Element | null = null;
    private _pendingReorderTimeout: number | null = null;

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
            this._flash("Name updated");
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
            this._flash("Device type updated");
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
        this._busy = true;
        try {
            this.device = await this.api.updateDevice(this.device.id, {
                emitter_entity_ids: newIds,
            });
            this._flash("Emitters updated");
            this.dispatchEvent(
                new CustomEvent("device-changed", { bubbles: true, composed: true }),
            );
        } catch (err) {
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
    }

    updated(changed: Map<string, unknown>): void {
        if (changed.has("device")) {
            void this._loadActionOptions();
            void this._loadTriggers();
        }
    }

    private async _loadActionOptions() {
        try {
            this._actionOptions = await this.api.getActionOptions(this.device.device_type);
        } catch {
            this._actionOptions = [];
        }
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

    private _onToggleTrigger(ev: CustomEvent): void {
        const cmd = ev.detail?.command as IRCommand | null;
        if (!cmd) return;

        // If a trigger already exists for this command, open edit mode.
        const existing = this._triggers.find(
            (t) => t.source_command_id === cmd.id,
        );
        if (existing) {
            this._triggerEdit = existing;
        } else {
            this._triggerCommand = cmd;
        }
    }

    private _closeTriggerDialog(): void {
        this._triggerCommand = null;
        this._triggerEdit = null;
    }

    private async _onTriggerSaved(): Promise<void> {
        this._triggerCommand = null;
        this._triggerEdit = null;
        await this._loadTriggers();
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
                return opt?.label ?? key;
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
            onStart: (e) => {
                this._sortableBefore = (e.item as Element).previousElementSibling;
            },
            onEnd: (e) => {
                // Revert SortableJS's DOM mutation so Lit can re-render
                // cleanly from the updated array.
                const item = e.item as HTMLElement;
                if (this._sortableBefore) {
                    this._sortableBefore.after(item);
                } else {
                    item.parentElement?.prepend(item);
                }
                this._sortableBefore = null;

                const oldIndex = e.oldIndex;
                const newIndex = e.newIndex;
                if (
                    oldIndex === undefined ||
                    newIndex === undefined ||
                    oldIndex === newIndex
                ) {
                    return;
                }

                const commands = [...this.device.commands];
                const [moved] = commands.splice(oldIndex, 1);
                commands.splice(newIndex, 0, moved);
                this.device = { ...this.device, commands };

                // Bubble the new order to the parent so its cached
                // ``_expandedDevice`` stays in sync. Without this, the
                // parent's next re-render (which happens for many HA
                // reasons) would pass its still-original device back
                // down, Lit would overwrite our local ``this.device``,
                // and ``repeat()`` would reconcile the DOM back to the
                // pre-drag order. The custom event is intentionally
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
                this._flash(`Reorder failed: ${(err as Error).message}`);
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
            this._flash(actionKey ? `Mapped to ${actionKey}` : "Mapping cleared");
            this.dispatchEvent(
                new CustomEvent("device-changed", { bubbles: true, composed: true }),
            );
        } catch (err) {
            this._flash(`Mapping failed: ${(err as Error).message}`);
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
            this._flash(`Sent "${command.name}"`);
        } catch (err) {
            this._flash(`Send failed: ${(err as Error).message}`);
        } finally {
            this._busy = false;
        }
    }

    private _onDelete(e: CustomEvent) {
        const { command } = e.detail as { command: IRCommand };
        if (!command) return;
        this._commandToDelete = command;
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
            this._flash(`Removed "${command.name}"`);
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
        this._flash(`Saved "${commandName}"`);
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
    // Render
    // ---------------------------------------------------------------

    render() {
        const commands = this.device.commands;
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
                                  title="Click to rename"
                              >
                                  ${this.device.name}
                                  <span class="edit-icon">&#9998;</span>
                              </h1>
                          `}
                </div>
                <button
                    class="action-btn collapse-btn"
                    @click=${() => this.dispatchEvent(new CustomEvent("collapse", { bubbles: true, composed: true }))}
                    title="Close"
                >&#x2715;</button>
            </section>

            <!-- Device metadata grid -->
            <div class="device-meta">
                <span class="meta-label">Type</span>
                <div class="meta-value">
                    <select
                        .value=${this.device.device_type}
                        @change=${this._onTypeChanged}
                        ?disabled=${this._busy}
                    >
                        ${DEVICE_TYPES.map(
                            (t) => html`
                                <option
                                    value=${t.value}
                                    ?selected=${this.device.device_type === t.value}
                                >
                                    ${t.label}
                                </option>
                            `,
                        )}
                    </select>
                </div>
                <span class="meta-label">Emitters</span>
                <div class="meta-value">
                    <ir-emitter-picker
                        .hass=${this.hass}
                        .value=${this.device.emitter_entity_ids ?? []}
                        ?disabled=${this._busy}
                        @emitters-changed=${this._onEmittersChanged}
                    ></ir-emitter-picker>
                </div>
            </div>

            <!-- Commands -->
            <div class="commands-section">
                <div class="commands-header">
                    <span>Commands (${count})</span>
                </div>
                <div class="commands-list">
                    ${commands.length > 0
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
                                      .hasTrigger=${this._commandHasTrigger(cmd)}
                                      @map-action=${this._onMapAction}
                                      @test=${this._onTest}
                                      @toggle-trigger=${this._onToggleTrigger}
                                      @delete=${this._onDelete}
                                  >
                                      <ha-svg-icon
                                          slot="status"
                                          class="grip-handle"
                                          .path=${ICON_GRIP}
                                          title="Drag to reorder"
                                      ></ha-svg-icon>
                                  </ir-command-row>
                              `,
                          )
                        : html`<div class="empty">No commands yet. Add one below.</div>`}

                    ${this._mappingCommandName
                        ? html`
                              <div
                                  class="action-popover"
                                  style="top:${this._popoverTop}px; left:${this._popoverLeft}px"
                              >
                                  <div class="popover-header">Map action</div>
                                  ${this._getCurrentActionKey(this._mappingCommandName)
                                      ? html`
                                            <button
                                                class="popover-item clear"
                                                @click=${() => this._selectAction(this._mappingCommandName!, null)}
                                            >
                                                <span class="popover-label">None (clear)</span>
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
                                              <span class="popover-label">${opt.label}</span>
                                              ${isCurrent
                                                  ? html`<span class="popover-check">&#10003;</span>`
                                                  : isOther
                                                    ? html`<span class="popover-existing">${existing}</span>`
                                                    : ""}
                                          </button>
                                      `;
                                  })}
                              </div>
                          `
                        : ""}
                </div>
            </div>

            <div class="footer-actions">
                <button
                    class="action-btn"
                    @click=${this._goToSniffer}
                    ?disabled=${this._busy}
                >+ Add Command</button>
                <button
                    class="action-btn delete-btn"
                    @click=${() => (this._confirmDelete = true)}
                    ?disabled=${this._busy}
                >Delete Device</button>
            </div>

            <!-- Dialogs -->
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
                          title="Delete ${this.device.name}?"
                          message="This removes all captured commands and the auto-created entity. The action cannot be undone."
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
                          title="Delete command?"
                          message="Remove &quot;${this._commandToDelete.name}&quot;? This cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${true}
                          @confirmed=${this._confirmCommandDelete}
                          @closed=${() => (this._commandToDelete = null)}
                      ></ir-confirm-dialog>
                  `
                : ""}
            ${this._triggerCommand
                ? html`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .protocol=${this._triggerCommand.protocol}
                          .code=${this._triggerCommand.code}
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
                          title="Delete Trigger"
                          message="Remove this trigger? The associated HA event entity will also be removed."
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

    static styles = css`
        :host {
            display: block;
        }

        /* --- Header --- */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
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

        /* --- Metadata grid --- */
        .device-meta {
            display: grid;
            grid-template-columns: 80px 1fr;
            gap: 8px 12px;
            align-items: start;
            margin: 16px 0 0;
        }
        .meta-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
            padding-top: 6px;
        }
        .meta-value select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .meta-value ir-emitter-picker {
            --picker-label-display: none;
        }

        /* --- Buttons --- */
        .action-btn {
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
            transition: background 150ms ease;
        }
        .action-btn:hover {
            background: var(--secondary-background-color);
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .action-btn.delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.25);
        }
        .action-btn.delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
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
        .commands-section {
            margin: 16px 0;
            border-top: 1px solid var(--divider-color);
            padding-top: 12px;
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
        /* --- Action popover --- */
        .action-popover {
            position: fixed;
            z-index: 50;
            min-width: 200px;
            max-width: 280px;
            background: var(--card-background-color, #1c1c1c);
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
            padding: 4px 0;
            overflow: auto;
            max-height: 320px;
        }
        .popover-header {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--secondary-text-color);
            padding: 6px 12px 4px;
        }
        .popover-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            padding: 7px 12px;
            background: none;
            border: none;
            color: var(--primary-text-color);
            font-size: 0.82rem;
            font-family: inherit;
            cursor: pointer;
            text-align: left;
            transition: background 100ms ease;
        }
        .popover-item:hover {
            background: var(--secondary-background-color);
        }
        .popover-item.active {
            color: var(--primary-color);
            font-weight: 500;
        }
        .popover-item.clear {
            color: var(--secondary-text-color);
            font-style: italic;
            border-bottom: 1px solid var(--divider-color);
            margin-bottom: 2px;
        }
        .popover-check {
            color: var(--primary-color);
            font-size: 0.9rem;
        }
        .popover-existing {
            font-size: 0.72rem;
            color: var(--secondary-text-color);
            font-style: italic;
            margin-left: 8px;
            flex-shrink: 0;
        }
        .empty {
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 12px 0;
        }
        .footer-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 16px 0;
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
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-detail": IrDeviceDetail;
    }
}
