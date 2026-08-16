/**
 * Collapse-to-active header chip group (add-popups, signpost 3,
 * Track 1 item 5).
 *
 * Generalizes the pattern s11's "Header pin management" demo
 * introduced (`.hw-picker` / `.hdr-chip` in the mockup's own JS/CSS --
 * see that file's script block): a labeled row of toggle chips that
 * shows only the ON ones by default, with a "+" that expands it to
 * show every option (on and off) for editing, collapsing back down on
 * an outside click or Escape. NOT a timer -- the mockup's own callout
 * calls that out explicitly as the wrong mechanism (unpredictable,
 * pauses mid-decision, etc).
 *
 * This did NOT already exist in the real app before this component --
 * checked before writing anything (see the coding-plan-review that
 * flagged this back to the owner): ir-emitter-picker.ts and
 * ir-receiver-picker.ts, the two existing chip pickers, always render
 * every chip, on and off, with no collapse state at all. That
 * "always-open" behavior is INTENTIONAL and stays exactly as-is in
 * every dialog context (Add dialogs, assign-signal, promote) per
 * owner direction -- picking hardware for something you're actively
 * configuring wants to see every option at a glance, no "+" required.
 * This component is therefore a NEW, separate piece used only on the
 * two detail-page headers (ir-device-detail.ts's Emitters: + gated
 * Pin: groups, and ir-device-list.ts's inline Remote detail's
 * Receivers: + gated Pin: group) -- a glanceable summary that expands
 * on demand, not a replacement for the dialog pickers.
 *
 * Deliberately generic: takes rows + a raw `tone` color string rather
 * than any origin/kind-color lookup of its own, so it doesn't need to
 * know whether it's showing emitters, receivers, or pins -- the
 * consumer picks the token per call site (ORIGIN_COLORS.device,
 * ORIGIN_COLORS.remote, or PIN_BLUE from ir-pin-flag.ts) and computes
 * the label text itself (including the Pin group's live "Pin:" /
 * "Pinned Remotes:" swap -- this component just renders whatever
 * label string it's given, every render).
 *
 * Three visual chip states, not two: `on` (assigned, glows), `down`
 * (assigned but unreachable -- only emitters ever set this, mirroring
 * ir-emitter-picker.ts's own three-state treatment so the header
 * summary doesn't quietly drop the "this blaster is unplugged" signal
 * that component was built to surface), and `off` (unassigned, hidden
 * while collapsed).
 *
 * `readonly`: the expand/collapse "+" still works (browsing candidates
 * is honest even with nothing behind it), but chip clicks are no-ops
 * -- no `chips-changed` event, no local toggle either. Used for the
 * gated Pin groups, which have no backend to call yet (pin storage is
 * Track 2 item 5); a fake local toggle would look live and isn't.
 *
 * Click-outside / Escape collapse is per-instance (each instance adds
 * its own document listeners while connected, mirroring the mockup's
 * global `collapseAllPickers()` but without a singleton registry --
 * Lit doesn't need one). A click that originates inside this
 * component's own composed path never collapses it, so clicking the
 * "+" or a chip doesn't immediately re-collapse the group it just
 * opened; two groups on the same page can be expanded independently.
 *
 * Fires `chips-changed` with detail: { value: string[] } (the full new
 * list of "on" row ids) -- same shape ir-emitter-picker.ts's
 * `emitters-changed` and ir-receiver-picker.ts's `receivers-changed`
 * already use, so a consumer wiring this in place of either dialog
 * picker can reuse its existing handler unchanged.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t } from "./localize.js";

export interface HeaderChipRow {
    id: string;
    name: string;
    on: boolean;
    /** Assigned but unreachable -- meaningless unless `on` is also
     *  true. Only emitters use this; receivers/pin rows never set it. */
    down?: boolean;
}

@customElement("ir-header-chip-group")
export class IrHeaderChipGroup extends LitElement {
    @property() public label = "";

    @property({ attribute: false }) public rows: HeaderChipRow[] = [];

    /** Raw CSS color for "on" chips, the dot, and the border -- see the
     *  file header on why this stays a plain string. */
    @property() public tone = "var(--primary-color)";

    @property({ type: Boolean }) public disabled = false;

    /** No backend yet for this group (the Pin groups, this signpost) --
     *  browsing still works, toggling doesn't. See the file header. */
    @property({ type: Boolean }) public readonly = false;

    @state() private _expanded = false;

    private _onDocClick = (e: MouseEvent): void => {
        if (!this._expanded) return;
        if (e.composedPath().includes(this)) return;
        this._expanded = false;
    };

    private _onDocKeydown = (e: KeyboardEvent): void => {
        if (e.key === "Escape" && this._expanded) this._expanded = false;
    };

    connectedCallback(): void {
        super.connectedCallback();
        document.addEventListener("click", this._onDocClick);
        document.addEventListener("keydown", this._onDocKeydown);
    }

    disconnectedCallback(): void {
        document.removeEventListener("click", this._onDocClick);
        document.removeEventListener("keydown", this._onDocKeydown);
        super.disconnectedCallback();
    }

    private _toggleExpanded(): void {
        if (this.disabled) return;
        this._expanded = !this._expanded;
    }

    private _toggleChip(row: HeaderChipRow): void {
        if (this.disabled || this.readonly || !this._expanded) return;
        const newIds = this.rows
            .map((r) => (r.id === row.id ? { ...r, on: !r.on } : r))
            .filter((r) => r.on)
            .map((r) => r.id);
        this.dispatchEvent(
            new CustomEvent("chips-changed", {
                detail: { value: newIds },
                bubbles: true,
                composed: true,
            }),
        );
    }

    render() {
        const visible = this._expanded ? this.rows : this.rows.filter((r) => r.on);
        return html`
            <div class="group ${this._expanded ? "expanded" : ""}" style="--tone:${this.tone}">
                <span class="group-label">${this.label}</span>
                ${visible.map((row) => this._renderChip(row))}
                <button
                    class="add-btn"
                    ?disabled=${this.disabled}
                    title=${this._expanded ? t("common.close") : t("hdrchips.expand_title")}
                    aria-label=${this._expanded ? t("common.close") : t("hdrchips.expand_title")}
                    @click=${this._toggleExpanded}
                >${this._expanded ? "×" : "+"}</button>
            </div>
        `;
    }

    private _renderChip(row: HeaderChipRow) {
        const cls = row.on ? (row.down ? "down" : "on") : "off";
        const word = row.on
            ? row.down
                ? t("picker.state_unavailable")
                : t("picker.state_on")
            : t("picker.state_off");
        return html`
            <button
                class="chip ${cls} ${this.readonly ? "readonly" : ""}"
                role="switch"
                aria-checked=${row.on ? "true" : "false"}
                aria-label="${row.name}, ${word}"
                ?disabled=${this.disabled}
                title="${row.name} · ${word}"
                @click=${() => this._toggleChip(row)}
            >
                <span class="dot"></span>
                <span class="chip-name">${row.name}</span>
            </button>
        `;
    }

    static styles = css`
        :host {
            display: inline-block;
        }
        .group {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
        }
        .group-label {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--secondary-text-color);
            margin-right: 2px;
            white-space: nowrap;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 10px 3px 8px;
            border: 1px solid var(--divider-color);
            border-radius: 14px;
            background: none;
            font-family: inherit;
            font-size: 11.5px;
            color: var(--secondary-text-color);
            cursor: default;
            transition: border-color 140ms ease, background 140ms ease,
                color 140ms ease;
        }
        .group.expanded .chip {
            cursor: pointer;
        }
        .group.expanded .chip:hover:not(:disabled) {
            border-color: var(--tone);
        }
        .chip:disabled {
            cursor: default;
            opacity: 0.55;
        }
        .chip.readonly {
            opacity: 0.7;
            cursor: default !important;
        }
        .chip-name {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 160px;
        }
        .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #4d5359;
            flex: none;
        }
        .chip.on {
            border-color: var(--tone);
            background: color-mix(in srgb, var(--tone) 14%, transparent);
            color: var(--primary-text-color);
        }
        .chip.on .dot {
            background: var(--tone);
            box-shadow: 0 0 5px color-mix(in srgb, var(--tone) 65%, transparent);
        }
        /* Assigned but unreachable (emitters only) -- amber, same
         *  treatment ir-emitter-picker.ts uses, deliberately NOT the
         *  group's own tone color (this state means "trouble", not
         *  "on", regardless of which group it's in). */
        .chip.down {
            border-color: rgba(217, 164, 65, 0.45);
            color: #e8dcc2;
        }
        .chip.down .dot {
            background: #d9a441;
            box-shadow: none;
        }
        .add-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            border: 1px dashed var(--divider-color);
            background: none;
            color: var(--secondary-text-color);
            font-size: 13px;
            line-height: 1;
            cursor: pointer;
            font-family: inherit;
        }
        .add-btn:hover:not(:disabled) {
            border-color: var(--tone);
            color: var(--tone);
        }
        .add-btn:disabled {
            cursor: default;
            opacity: 0.55;
        }
    `;
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-header-chip-group": IrHeaderChipGroup;
    }
}
