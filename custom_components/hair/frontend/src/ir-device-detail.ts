/**
 * Device detail view: editable header (name, type, emitter),
 * read-only hardware cards (TX / RX), flat command list.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import "./ir-command-row.js";
import "./ir-capture-dialog.js";
import "./ir-confirm-dialog.js";
import type { HairApi } from "./api.js";
import type { IRCommand, IRDevice, DeviceTypeId } from "./types.js";

const DEVICE_TYPES: { value: DeviceTypeId; label: string }[] = [
    { value: "tv", label: "TV / Monitor" },
    { value: "ac", label: "Air Conditioner" },
    { value: "fan", label: "Fan" },
    { value: "soundbar", label: "Soundbar / Audio" },
    { value: "projector", label: "Projector" },
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

    // Inline name editing
    @state() private _editingName = false;
    @state() private _draftName = "";

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

    private async _onEmitterChanged(e: Event) {
        const newEmitter = (e.target as HTMLSelectElement).value;
        if (newEmitter === this.device.emitter_entity_id) return;
        this._busy = true;
        try {
            this.device = await this.api.updateDevice(this.device.id, {
                emitter_entity_id: newEmitter,
            });
            this._flash("Emitter updated");
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
    // Command actions
    // ---------------------------------------------------------------

    private async _onRelearn(e: CustomEvent) {
        const { templateName } = e.detail;
        this._captureName = templateName;
    }

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
    // Emitter list for dropdown
    // ---------------------------------------------------------------

    private _getEmitters(): { entity_id: string; name: string }[] {
        const states = (this.hass?.states ?? {}) as Record<
            string,
            { entity_id: string; attributes: { friendly_name?: string } }
        >;
        const emitters: { entity_id: string; name: string }[] = [];
        for (const [entityId, st] of Object.entries(states)) {
            if (entityId.startsWith("infrared.")) {
                emitters.push({
                    entity_id: entityId,
                    name: st.attributes.friendly_name ?? entityId,
                });
            }
        }
        return emitters;
    }

    // ---------------------------------------------------------------
    // Render
    // ---------------------------------------------------------------

    render() {
        const commands = this.device.commands;
        const count = commands.length;
        const emitters = this._getEmitters();

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
                <div class="header-actions">
                    <button
                        class="action-btn delete-btn"
                        @click=${() => (this._confirmDelete = true)}
                        ?disabled=${this._busy}
                    >Delete</button>
                </div>
            </section>

            <!-- Editable fields: type + emitter -->
            <div class="device-fields">
                <div class="field">
                    <label>Device Type</label>
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
                <div class="field">
                    <label>IR Emitter</label>
                    ${emitters.length === 0
                        ? html`<span class="no-emitters">No emitters found</span>`
                        : html`
                              <select
                                  .value=${this.device.emitter_entity_id}
                                  @change=${this._onEmitterChanged}
                                  ?disabled=${this._busy}
                              >
                                  ${emitters.map(
                                      (em) => html`
                                          <option
                                              value=${em.entity_id}
                                              ?selected=${this.device.emitter_entity_id === em.entity_id}
                                          >
                                              ${em.name}
                                          </option>
                                      `,
                                  )}
                              </select>
                          `}
                </div>
            </div>

            <!-- Hardware cards: TX + RX -->
            <div class="hardware-section">
                <h2>Hardware</h2>
                <div class="hardware-cards">
                    <!-- TX card (emitter) -->
                    <div
                        class="hw-card tx-card"
                        @click=${() =>
                            this._navigateIntegration(
                                this._entityIntegrationUrl(this.device.emitter_entity_id),
                            )}
                        title="View integration"
                    >
                        <div class="hw-badge tx-badge">TX</div>
                        <div class="hw-info">
                            <div class="hw-name">
                                ${this._emitterName(this.device.emitter_entity_id)}
                            </div>
                            <div class="hw-entity">${this.device.emitter_entity_id}</div>
                        </div>
                        <div class="hw-arrow">&#8250;</div>
                    </div>

                    <!-- RX card (capture proxy) -- only if set -->
                    ${this.device.capture_device_id
                        ? html`
                              <div
                                  class="hw-card rx-card"
                                  @click=${() => {
                                      const ceId = this._deviceConfigEntryId(
                                          this.device.capture_device_id!,
                                      );
                                      this._navigateIntegration(
                                          this._integrationUrl(ceId),
                                      );
                                  }}
                                  title="View integration"
                              >
                                  <div class="hw-badge rx-badge">RX</div>
                                  <div class="hw-info">
                                      <div class="hw-name">
                                          ${this._deviceRegistryName(
                                              this.device.capture_device_id!,
                                          )}
                                      </div>
                                      <div class="hw-entity">
                                          ${this.device.capture_provider_type}
                                      </div>
                                  </div>
                                  <div class="hw-arrow">&#8250;</div>
                              </div>
                          `
                        : nothing}
                </div>
            </div>

            <!-- Commands -->
            <ha-card>
                <h2>Commands (${count})</h2>
                ${commands.length > 0
                    ? commands.map(
                          (cmd) => html`
                              <ir-command-row
                                  .templateName=${cmd.name}
                                  .command=${cmd}
                                  .busy=${this._busy}
                                  @relearn=${this._onRelearn}
                                  @test=${this._onTest}
                                  @delete=${this._onDelete}
                              ></ir-command-row>
                          `,
                      )
                    : html`<div class="empty">No commands yet. Add one below.</div>`}
            </ha-card>

            <div class="custom-add">
                <button
                    class="action-btn"
                    @click=${this._goToSniffer}
                    ?disabled=${this._busy}
                >+ Add Command</button>
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
        .header-actions {
            display: flex;
            gap: 6px;
        }

        /* --- Editable fields --- */
        .device-fields {
            display: flex;
            gap: 16px;
            margin: 12px 0 0;
        }
        .field {
            flex: 1;
        }
        .field label {
            display: block;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
            margin-bottom: 4px;
        }
        .field select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .no-emitters {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }

        /* --- Hardware cards --- */
        .hardware-section {
            margin: 20px 0 0;
        }
        .hardware-section h2 {
            margin: 0 0 8px;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
        }
        .hardware-cards {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .hw-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 150ms ease, box-shadow 150ms ease;
        }
        .hw-card:hover {
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
        }
        .tx-card {
            background: rgba(30, 136, 229, 0.08);
            border: 1px solid rgba(30, 136, 229, 0.2);
        }
        .tx-card:hover {
            background: rgba(30, 136, 229, 0.14);
        }
        .rx-card {
            background: rgba(56, 142, 60, 0.08);
            border: 1px solid rgba(56, 142, 60, 0.2);
        }
        .rx-card:hover {
            background: rgba(56, 142, 60, 0.14);
        }
        .hw-badge {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            padding: 2px 8px;
            border-radius: 4px;
            flex-shrink: 0;
        }
        .tx-badge {
            background: rgba(30, 136, 229, 0.18);
            color: #1565c0;
        }
        .rx-badge {
            background: rgba(56, 142, 60, 0.18);
            color: #2e7d32;
        }
        .hw-info {
            flex: 1;
            min-width: 0;
        }
        .hw-name {
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--primary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .hw-entity {
            font-size: 0.75rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .hw-arrow {
            font-size: 1.2rem;
            color: var(--secondary-text-color);
            flex-shrink: 0;
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
            color: #b71c1c;
            border-color: rgba(183, 28, 28, 0.2);
        }
        .action-btn.delete-btn:hover {
            background: rgba(183, 28, 28, 0.06);
        }

        /* --- Commands card --- */
        ha-card {
            margin: 16px 0;
            padding: 16px;
        }
        ha-card h2 {
            margin: 0 0 8px;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
        }
        .empty {
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 12px 0;
        }
        .custom-add {
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
