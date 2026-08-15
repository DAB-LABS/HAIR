/**
 * Flat, searchable controlled-device picker for the Device tab of the
 * Add Trigger Remote dialog (add-popups, signpost 2). Add Controlled
 * Device has no Device tab -- a device can't source itself.
 *
 * Flat list, command count per row, plain search box. No filter chips:
 * a controlled-device list has no library/yours or kind split to filter
 * on (confirmed as the right call in the coding plan review, not just
 * an omission -- every row here is already "yours").
 *
 * Matrix rule (KNOWN GAP, not applied yet): the coding plan calls for
 * the same disabled-with-reason treatment ir-wig-picker.ts gives a
 * matrix wig -- "a matrix-backed device offers the same discrete-press
 * subset." `DeviceSummary` (websocket_api.py `_device_summary()`,
 * backing `hair/devices/list`) does not carry a `matrix` field today --
 * only the full single-device payload does (`_device_full()`,
 * `device.to_dict()` plus the matrix-summary rider, owner ruling
 * 2026-07-28). Adding it to the list-level summary is a small, one-line
 * backend change but is a Python change outside this frontend-only
 * track's scope, so every row here renders as plainly pickable for now.
 * Track 2/3 (the first to actually wire this picker into a dialog)
 * should either add `matrix` to `_device_summary()` and restore the
 * annotation, or confirm the omission is fine to ship as-is.
 *
 * Selection is presentational only, same contract as ir-wig-picker.ts:
 * this component resolves and emits the picked device, the consuming
 * dialog decides what creating a trigger remote "from a device" means.
 *
 * Fires `device-picked` with detail: { value: string | null, device: DeviceSummary | null }
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import type { HairApi } from "./api.js";
import type { DeviceSummary } from "./types.js";

@customElement("ir-device-picker")
export class IrDevicePicker extends LitElement {
    /** HAIR API client. Required -- the device list comes from it. */
    @property({ attribute: false }) public api!: HairApi;

    /** Currently selected device id, or null for no selection. */
    @property({ attribute: false }) public value: string | null = null;

    /** Disable all interactions. */
    @property({ type: Boolean }) public disabled = false;

    @state() private _devices: DeviceSummary[] = [];
    @state() private _search = "";
    @state() private _loaded = false;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
    }

    private async _load(): Promise<void> {
        if (!this.api) return;
        try {
            this._devices = await this.api.listDevices();
        } catch {
            this._devices = [];
        } finally {
            this._loaded = true;
        }
    }

    private _visibleDevices(): DeviceSummary[] {
        const query = this._search.trim().toLowerCase();
        if (!query) return this._devices;
        return this._devices.filter((d) => d.name.toLowerCase().includes(query));
    }

    private _pick(device: DeviceSummary): void {
        if (this.disabled) return;
        this.value = device.id;
        this.dispatchEvent(
            new CustomEvent("device-picked", {
                detail: { value: device.id, device },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        if (this._loaded && this._devices.length === 0) {
            return html`<div class="dlg-empty-line">${t("devicepicker.empty")}</div>`;
        }

        const devices = this._visibleDevices();

        return html`
            <input
                class="search"
                type="text"
                .value=${this._search}
                placeholder=${t("devicepicker.search")}
                ?disabled=${this.disabled}
                @input=${(e: Event) =>
                    (this._search = (e.target as HTMLInputElement).value)}
            />
            <div class="list">
                ${devices.map((d) => this._renderRow(d))}
                ${devices.length === 0
                    ? html`<div class="no-matches">${t("devicepicker.no_matches")}</div>`
                    : ""}
            </div>
        `;
    }

    private _renderRow(device: DeviceSummary) {
        const selected = this.value === device.id;
        const cls = ["row", selected ? "selected" : ""].filter(Boolean).join(" ");
        return html`
            <div
                class=${cls}
                ?inert=${this.disabled}
                @click=${() => this._pick(device)}
            >
                <div class="row-main">
                    <div class="row-name">${device.name}</div>
                    <div class="row-sub">
                        ${tp("devicepicker.command_count", device.command_count)}
                    </div>
                </div>
                <div class="row-count">${device.command_count}</div>
            </div>
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        .search {
            display: block;
            width: 100%;
            box-sizing: border-box;
            padding: 7px 10px;
            border-radius: 6px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.85rem;
            font-family: inherit;
            margin-bottom: 10px;
        }
        .list {
            max-height: 320px;
            overflow-y: auto;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
        }
        .row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 9px 12px;
            border-bottom: 1px solid var(--divider-color);
            cursor: pointer;
        }
        .row:last-child {
            border-bottom: none;
        }
        .row:hover {
            background: var(--secondary-background-color);
        }
        .row.selected {
            background: rgba(46, 125, 50, 0.12);
            border-left: 3px solid var(--origin-device, #2e7d32);
            padding-left: 9px;
        }
        .row-main {
            flex: 1;
            min-width: 0;
        }
        .row-name {
            font-size: 0.88rem;
            color: var(--primary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .row-sub {
            font-size: 0.74rem;
            color: var(--secondary-text-color);
        }
        .row-count {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            flex: none;
        }
        .no-matches {
            padding: 16px 4px;
            text-align: center;
            font-size: 0.8rem;
            font-style: italic;
            color: var(--secondary-text-color);
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-device-picker": IrDevicePicker;
    }
}
