/**
 * Setup progress bar for the device detail view.
 * Shows learned/total commands as a horizontal progress strip.
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "./decorators.js";

@customElement("ir-progress-bar")
export class IrProgressBar extends LitElement {
    @property({ type: Number }) public learned = 0;
    @property({ type: Number }) public total = 0;

    render() {
        const ratio = this.total > 0 ? this.learned / this.total : 0;
        const pct = Math.min(100, Math.max(0, Math.round(ratio * 100)));
        return html`
            <div
                class="bar"
                role="progressbar"
                aria-valuenow=${this.learned}
                aria-valuemax=${this.total}
            >
                <div class="fill" style="width: ${pct}%"></div>
            </div>
            <div class="label">${this.learned}/${this.total} commands</div>
        `;
    }

    static styles = css`
        :host {
            display: block;
            margin: 12px 0 16px;
        }
        .bar {
            background: var(--secondary-background-color);
            border-radius: 4px;
            height: 8px;
            overflow: hidden;
        }
        .fill {
            background: var(--primary-color);
            height: 100%;
            transition: width 200ms ease;
        }
        .label {
            margin-top: 6px;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-progress-bar": IrProgressBar;
    }
}
