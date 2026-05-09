/**
 * One row in the device-detail command checklist.
 * - Captured commands show protocol info plus Test / Re-learn / Delete actions.
 * - Unlearned templates show a single Learn button.
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { IRCommand } from "./types.js";

@customElement("ir-command-row")
export class IrCommandRow extends LitElement {
    @property({ attribute: false }) public templateName: string = "";
    @property({ attribute: false }) public command: IRCommand | null = null;
    @property({ type: Boolean }) public busy = false;

    private _emit(name: string) {
        this.dispatchEvent(
            new CustomEvent(name, {
                detail: { templateName: this.templateName, command: this.command },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const learned = this.command !== null;
        return html`
            <div class="row" data-learned=${learned ? "true" : "false"}>
                <div class="status" aria-hidden="true">
                    ${learned ? "✅" : "○"}
                </div>
                <div class="info">
                    <div class="name">${this.templateName}</div>
                    <div class="meta">
                        ${learned
                            ? html`${this.command!.protocol ?? "Raw"} ·
                              ${this.command!.code ?? "timings"}`
                            : html`<span class="muted">Not yet learned</span>`}
                    </div>
                </div>
                <div class="actions">
                    ${learned
                        ? html`
                              <mwc-button
                                  dense
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("test")}
                              >
                                  ▶ Test
                              </mwc-button>
                              <mwc-button
                                  dense
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("relearn")}
                              >
                                  ↻ Re-learn
                              </mwc-button>
                              <mwc-icon-button
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("delete")}
                                  aria-label="Delete command"
                              >
                                  <ha-svg-icon
                                      .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                                  ></ha-svg-icon>
                              </mwc-icon-button>
                          `
                        : html`
                              <mwc-button
                                  raised
                                  dense
                                  ?disabled=${this.busy}
                                  @click=${() => this._emit("learn")}
                              >
                                  Learn
                              </mwc-button>
                          `}
                </div>
            </div>
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        .row {
            display: grid;
            grid-template-columns: 32px 1fr auto;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            border-radius: 8px;
        }
        .row[data-learned="false"] {
            background: var(--secondary-background-color);
        }
        .status {
            font-size: 1.1rem;
            text-align: center;
        }
        .name {
            font-weight: 500;
        }
        .meta {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-family: var(--code-font-family, monospace);
        }
        .muted {
            font-style: italic;
        }
        .actions {
            display: flex;
            gap: 4px;
            align-items: center;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-command-row": IrCommandRow;
    }
}
