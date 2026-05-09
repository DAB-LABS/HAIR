/**
 * Device detail view: header, setup-progress bar, command checklist
 * grouped into Essential / Optional / Custom sections, and the auto-
 * created entity summary.
 *
 * Owns the capture queue: when the user clicks Save & Learn Next on the
 * capture dialog, this component opens the dialog for the next un-
 * learned essential template and drives them through the full list.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import "./ir-progress-bar.js";
import "./ir-command-row.js";
import "./ir-capture-dialog.js";
import type { HairApi } from "./api.js";
import type { CommandTemplate, IRCommand, IRDevice } from "./types.js";

interface ChecklistEntry {
    template: CommandTemplate | null;
    name: string;
    command: IRCommand | null;
    essential: boolean;
    custom: boolean;
}

@customElement("ir-device-detail")
export class IrDeviceDetail extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass: any;
    @property({ attribute: false }) public device!: IRDevice;

    @state() private _templates: CommandTemplate[] = [];
    @state() private _busy = false;
    @state() private _captureName: string | null = null;
    @state() private _captureQueue: string[] = [];
    @state() private _customDialogOpen = false;
    @state() private _customName = "";
    @state() private _toast: string | null = null;
    @state() private _confirmDelete = false;

    connectedCallback(): void {
        super.connectedCallback();
        void this._loadTemplates();
    }

    protected updated(changed: Map<string, unknown>): void {
        if (changed.has("device") && this.device) {
            void this._loadTemplates();
        }
    }

    private async _loadTemplates() {
        try {
            this._templates = await this.api.listTemplates(this.device.device_type);
        } catch (err) {
            this._templates = [];
        }
    }

    private get _entries(): ChecklistEntry[] {
        const captured = new Map(
            this.device.commands.map((c) => [c.name.toLowerCase(), c]),
        );
        const seenTemplate = new Set<string>();
        const entries: ChecklistEntry[] = [];

        for (const template of this._templates) {
            seenTemplate.add(template.name.toLowerCase());
            entries.push({
                template,
                name: template.name,
                command: captured.get(template.name.toLowerCase()) ?? null,
                essential: template.essential,
                custom: false,
            });
        }
        for (const command of this.device.commands) {
            if (!seenTemplate.has(command.name.toLowerCase())) {
                entries.push({
                    template: null,
                    name: command.name,
                    command,
                    essential: false,
                    custom: true,
                });
            }
        }
        return entries;
    }

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

    private async _onLearn(e: CustomEvent) {
        const { templateName } = e.detail;
        this._captureQueue = [];
        this._captureName = templateName;
    }

    private async _onRelearn(e: CustomEvent) {
        const { templateName } = e.detail;
        this._captureQueue = [];
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

    private async _onDelete(e: CustomEvent) {
        const { command } = e.detail as { command: IRCommand };
        if (!command) return;
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

    private _onCaptureClosed() {
        this._captureName = null;
        this._captureQueue = [];
    }

    private async _onCommandSaved(e: CustomEvent) {
        const { saveAndNext, commandName } = e.detail as {
            saveAndNext: boolean;
            commandName: string;
        };
        await this._refresh();
        this._flash(`Saved "${commandName}"`);

        if (saveAndNext) {
            const queue = this._buildNextQueue(commandName);
            if (queue.length > 0) {
                this._captureQueue = queue;
                this._captureName = queue[0];
                return;
            }
        }
        this._captureName = null;
    }

    private _buildNextQueue(justSaved: string): string[] {
        const captured = new Set(
            this.device.commands.map((c) => c.name.toLowerCase()),
        );
        captured.add(justSaved.toLowerCase());
        return this._templates
            .filter(
                (t) => t.essential && !captured.has(t.name.toLowerCase()),
            )
            .map((t) => t.name);
    }

    private _openCustomDialog() {
        this._customName = "";
        this._customDialogOpen = true;
    }

    private _closeCustomDialog() {
        this._customDialogOpen = false;
    }

    private _confirmCustom() {
        const name = this._customName.trim();
        if (!name) return;
        this._customDialogOpen = false;
        this._captureName = name;
        this._captureQueue = [];
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

    render() {
        const entries = this._entries;
        const essential = entries.filter((e) => e.essential);
        const optional = entries.filter((e) => !e.essential && !e.custom);
        const custom = entries.filter((e) => e.custom);
        const learned = entries.filter((e) => e.command !== null).length;
        const total = entries.length || essential.length;
        const mappedFeatures = Object.keys(this.device.entity_config.command_mapping);
        const platform = this.device.entity_config.platform;

        return html`
            <section class="header">
                <div>
                    <h1>${this.device.name}</h1>
                    <div class="subtitle">
                        ${[
                            this.device.manufacturer,
                            this.device.model,
                            this.device.emitter_entity_id,
                        ]
                            .filter(Boolean)
                            .join(" • ")}
                    </div>
                </div>
                <div class="header-actions">
                    <mwc-button
                        @click=${() => (this._confirmDelete = true)}
                        ?disabled=${this._busy}
                    >
                        Delete
                    </mwc-button>
                </div>
            </section>

            <ir-progress-bar
                .learned=${learned}
                .total=${total}
            ></ir-progress-bar>

            ${essential.length > 0
                ? html`
                      <ha-card>
                          <h2>Essential Commands</h2>
                          ${essential.map(
                              (entry) => html`
                                  <ir-command-row
                                      .templateName=${entry.name}
                                      .command=${entry.command}
                                      .busy=${this._busy}
                                      @learn=${this._onLearn}
                                      @relearn=${this._onRelearn}
                                      @test=${this._onTest}
                                      @delete=${this._onDelete}
                                  ></ir-command-row>
                              `,
                          )}
                      </ha-card>
                  `
                : ""}
            ${optional.length > 0
                ? html`
                      <ha-card>
                          <h2>Optional Commands</h2>
                          ${optional.map(
                              (entry) => html`
                                  <ir-command-row
                                      .templateName=${entry.name}
                                      .command=${entry.command}
                                      .busy=${this._busy}
                                      @learn=${this._onLearn}
                                      @relearn=${this._onRelearn}
                                      @test=${this._onTest}
                                      @delete=${this._onDelete}
                                  ></ir-command-row>
                              `,
                          )}
                      </ha-card>
                  `
                : ""}
            ${custom.length > 0
                ? html`
                      <ha-card>
                          <h2>Custom Commands</h2>
                          ${custom.map(
                              (entry) => html`
                                  <ir-command-row
                                      .templateName=${entry.name}
                                      .command=${entry.command}
                                      .busy=${this._busy}
                                      @relearn=${this._onRelearn}
                                      @test=${this._onTest}
                                      @delete=${this._onDelete}
                                  ></ir-command-row>
                              `,
                          )}
                      </ha-card>
                  `
                : ""}

            <div class="custom-add">
                <mwc-button
                    raised
                    @click=${this._openCustomDialog}
                    ?disabled=${this._busy}
                >
                    + Add Custom Command
                </mwc-button>
            </div>

            <ha-card class="entity-summary">
                <h2>Entity</h2>
                <div class="meta">
                    Platform: <code>${platform}</code>
                </div>
                <div class="meta">
                    Mapped features:
                    ${mappedFeatures.length > 0
                        ? mappedFeatures.join(", ")
                        : "None yet — capture commands to enable features."}
                </div>
            </ha-card>

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
            ${this._customDialogOpen
                ? html`
                      <ha-dialog
                          open
                          heading="Add Custom Command"
                          @closed=${this._closeCustomDialog}
                      >
                          <ha-textfield
                              label="Command name"
                              .value=${this._customName}
                              @input=${(e: Event) =>
                                  (this._customName = (
                                      e.target as HTMLInputElement
                                  ).value)}
                          ></ha-textfield>
                          <mwc-button slot="secondaryAction" @click=${this._closeCustomDialog}>
                              Cancel
                          </mwc-button>
                          <mwc-button slot="primaryAction" raised @click=${this._confirmCustom}>
                              Start Learning
                          </mwc-button>
                      </ha-dialog>
                  `
                : ""}
            ${this._confirmDelete
                ? html`
                      <ha-dialog
                          open
                          heading="Delete ${this.device.name}?"
                          @closed=${() => (this._confirmDelete = false)}
                      >
                          <p>
                              This removes all captured commands and the
                              auto-created entity. The action cannot be
                              undone.
                          </p>
                          <mwc-button
                              slot="secondaryAction"
                              @click=${() => (this._confirmDelete = false)}
                          >
                              Cancel
                          </mwc-button>
                          <mwc-button
                              slot="primaryAction"
                              class="destructive"
                              @click=${this._deleteDevice}
                          >
                              Delete
                          </mwc-button>
                      </ha-dialog>
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
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
        }
        h1 {
            font-size: 1.5rem;
            margin: 0;
        }
        .subtitle {
            color: var(--secondary-text-color);
            margin-top: 4px;
            font-size: 0.9rem;
        }
        .header-actions {
            display: flex;
            gap: 6px;
        }
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
        .custom-add {
            margin: 16px 0;
        }
        .entity-summary .meta {
            font-size: 0.9rem;
            color: var(--primary-text-color);
            margin: 4px 0;
        }
        .destructive {
            --mdc-theme-primary: var(--error-color, #c62828);
        }
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
