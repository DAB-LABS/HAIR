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
 * ORIGIN_COLORS.remote, or PIN_BLUE from ir-pin-flag.ts).
 *
 * LAYOUT REWORKED for punch list item 9 (`header-pin-layout-handoff.md`,
 * owner-approved 2026-08-16), reconciled against this shipped component
 * per punch list item 11: the handoff's mockups were built before this
 * component was on a branch anyone could read, so its LAYOUT lands here
 * while this component's BEHAVIOR (reports the full new "on" list, the
 * parent refetches so the chips show what the backend actually kept)
 * is what stays.
 *
 * The layout change is one shape, and it buys two properties at once.
 * The label used to sit INSIDE the same wrapping flex as the chips,
 * which meant a wrapped second line of chips slid back under the label,
 * and two stacked groups could not line their colons up because each
 * label was only as wide as its own text. Now the label is a
 * fixed-width, right-justified flex item and the chips live in a
 * `flex-wrap` SIBLING, so wrapped lines always land under the chips
 * column and every row sharing a `labelWidth` shares a colon. Do not
 * "simplify" this back to text-align or a margin on the label alone --
 * the fixed-width-sibling shape is what makes both true together.
 *
 * `labelWidth` is derived per surface, not arbitrary: 80px on the
 * Remote header (sized to "RECEIVERS:", 10 characters) and 76px on the
 * Device header (sized to "EMITTERS:", 9). Re-measure against the
 * longest label in that column before adding a new one.
 *
 * The label text and the button glyph both follow the row's own live
 * pill count, not a static "is this editable" flag: zero chips on and
 * the label reads `labelEmpty` with a lone "+", one or more and it
 * reads `label` with "±". That rule holds for Receivers/Emitters too,
 * even though those are rarely empty in practice -- it is
 * row-state-driven, not row-identity-driven. `labelEmpty` is optional
 * and falls back to `label`, which is how the Receivers/Emitters rows
 * keep one caption in both states.
 *
 * Owner ruling 2026-08-16, the one place this deliberately parts from
 * the mockup: while the group is EXPANDED the button reads "×", not
 * the +/± glyph the mockup keeps. The mockup leaned on a border color
 * to say "open"; this component already had an explicit close
 * affordance and it stays.
 *
 * Three visual chip states, not two: `on` (assigned, glows), `down`
 * (assigned but unreachable -- only emitters ever set this, mirroring
 * ir-emitter-picker.ts's own three-state treatment so the header
 * summary doesn't quietly drop the "this blaster is unplugged" signal
 * that component was built to surface), and `off` (unassigned, hidden
 * while collapsed).
 *
 * (The `readonly` prop retired in signpost 4, Track 4. It existed so
 * the gated Pin groups could be browsed while having no backend to
 * call; they have one now, and a prop whose only consumer went live
 * is dead weight.)
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
    /** Caption while the row holds at least one "on" chip. */
    @property() public label = "";

    /** Caption while the row holds none -- optional, falls back to
     *  `label` so a row with one caption in both states says nothing. */
    @property() public labelEmpty = "";

    /** Fixed width of the label column, in px. Every row on the same
     *  header passes the same value; that is what aligns the colons. */
    @property({ type: Number }) public labelWidth = 80;

    @property({ attribute: false }) public rows: HeaderChipRow[] = [];

    /** Raw CSS color for "on" chips, the dot, and the border -- see the
     *  file header on why this stays a plain string. */
    @property() public tone = "var(--primary-color)";

    @property({ type: Boolean }) public disabled = false;

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
        if (this.disabled || !this._expanded) return;
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
        const on = this.rows.filter((r) => r.on);
        const visible = this._expanded ? this.rows : on;
        // Both the caption and the glyph read the live count, per the
        // handoff's row-state rule. "×" while expanded is the owner's
        // one deviation from the mockup (see the file header).
        const caption = on.length === 0 && this.labelEmpty ? this.labelEmpty : this.label;
        const glyph = this._expanded ? "×" : on.length === 0 ? "+" : "±";
        return html`
            <div class="hdr-row" style="--tone:${this.tone}">
                <span class="hdr-row-label" style="width:${this.labelWidth}px">${caption}</span>
                <div class="hdr-row-pills ${this._expanded ? "expanded" : ""}">
                    ${visible.map((row) => this._renderChip(row))}
                    <button
                        class="add-btn"
                        ?disabled=${this.disabled}
                        title=${this._expanded ? t("common.close") : t("hdrchips.expand_title")}
                        aria-label=${this._expanded ? t("common.close") : t("hdrchips.expand_title")}
                        @click=${this._toggleExpanded}
                    >${glyph}</button>
                </div>
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
                class="chip ${cls}"
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
        /* The host fills the header's row column rather than shrinking
           to its own content: the label's fixed width plus a flexible
           chips column is the whole mechanism, and an inline-block host
           would collapse the flexible half. */
        :host {
            display: block;
        }
        .hdr-row {
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }
        /* Fixed width comes from the consumer (labelWidth), so every row
           on a header shares one colon line. Right-justified against
           that width; padding-top lines the cap height up with the first
           row of chips rather than their box tops. */
        .hdr-row-label {
            flex-shrink: 0;
            text-align: right;
            padding-top: 5px;
            font-size: 0.66rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        /* min-width: 0 is load-bearing -- without it the column takes a
           content-based minimum from its own nowrap chips and overflows
           sideways instead of wrapping in place. */
        .hdr-row-pills {
            flex: 1;
            min-width: 0;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 7px;
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
        .hdr-row-pills.expanded .chip {
            cursor: pointer;
        }
        .hdr-row-pills.expanded .chip:hover:not(:disabled) {
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
