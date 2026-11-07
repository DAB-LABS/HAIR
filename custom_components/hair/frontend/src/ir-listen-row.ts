/**
 * The Sniffer's Listen row (BroadSniff Listen, 2026-10-17; any capture
 * device since windowed receivers, round 3; every radio receiver since
 * RF hear round 1).
 *
 * One pill (``ir-listen-chip``) per receiver, ordered by device name so
 * one device's IR and RF pills sit together (fix round 1, item 6): every
 * capture device, infrared or radio; every always-on radio receiver (its
 * window is HAIR's own: known codes fire all the time, new radio
 * remotes are minted only while it is open); and every always-on
 * infrared receiver, as a status pill with nothing to press. No label:
 * the Sniffer puts its filter glyphs at the right end of the same line.
 *
 * The row holds the one radio subscription (``hair/receivers/rf/
 * subscribe``) its software-window pills read their window from, and
 * hands each pill its receiver's latest item.
 *
 * The look is the device pages' header chip group, from the shared
 * ir-header-chip-styles module, except for the label (round 2, owner):
 * here it sits flush with the section title's left edge and the pills
 * follow it, wrapping when there are several, one to a row on a phone.
 */
import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import type { HairApi } from "./api.js";
import { headerChipStyles } from "./ir-header-chip-styles.js";
import "./ir-listen-chip.js";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";
import type { CaptureReceiverRow, RfReceiverItem } from "./types.js";

@customElement("ir-listen-row")
export class IrListenRow extends LitElement {
    @property({ attribute: false }) public hass?: any;
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public rows: CaptureReceiverRow[] = [];

    /** Each software window's latest item, by receiver. */
    @state() private _items: Record<string, RfReceiverItem> = {};
    private _sub: Promise<() => void> | null = null;

    disconnectedCallback(): void {
        super.disconnectedCallback();
        this._unsubscribe();
    }

    protected updated(changed: PropertyValues): void {
        if (!changed.has("rows") && !changed.has("api")) return;
        const wanted = this.api && this.rows.some((r) => r.software_window);
        if (wanted && this._sub === null) this._subscribe();
        else if (!wanted && this._sub !== null) this._unsubscribe();
    }

    private _subscribe(): void {
        // The promise is the guard: set in the same tick the subscribe
        // starts, so a second update cannot start another.
        this._sub = this.api
            .subscribeRfReceivers((item) => {
                this._items = { ...this._items, [item.receiver_entity_id]: item };
            })
            .catch(() => () => undefined);
    }

    private _unsubscribe(): void {
        const sub = this._sub;
        this._sub = null;
        this._items = {};
        void sub?.then((stop) => stop()).catch(() => undefined);
    }

    render() {
        if (this.rows.length === 0) return nothing;
        // No "Listen" label (fix round 1, item 6): the row is the
        // receivers, live; the group keeps the word for screen readers.
        return html`
            <div class="hdr-row" role="group" aria-label=${t("listen.label")}>
                <div class="hdr-row-pills">
                    ${this.rows.map(
                        (row) => html`<ir-listen-chip
                            .hass=${this.hass}
                            .api=${this.api}
                            .row=${row}
                            .item=${this._items[row.receiver_entity_id] ?? null}
                        ></ir-listen-chip>`,
                    )}
                </div>
            </div>
        `;
    }

    static styles = [
        headerChipStyles,
        css`
            :host {
                display: block;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-listen-row": IrListenRow;
    }
}
