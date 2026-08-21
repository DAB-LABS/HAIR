/**
 * Add Blaster dialog for the Plucker tab.
 *
 * ONE WINDOW, ONE STACK OF CARDS (build spec:
 * docs/internal/plans/plucker-broadlink-ux-handoff.md, owner-approved
 * after four mockup rounds; reference mockup
 * plucker-broadlink-ux-mockup-p4-cards.html). There is no step 1 and no
 * step 2, no back affordance, and no confirmation before a pluck.
 *
 * Every discovered learned-code store gets its own card, Broadlink
 * first, Tuya Local after. Clicking a card anywhere plucks that store
 * immediately: the glyph spins, then becomes a check, and the counts
 * line is replaced in place by the landing summary. A toast repeats the
 * same sentence at the bottom of the body and fades on its own.
 *
 * Clicking a done card again re-plucks. That is safe by construction
 * rather than by warning: the import is idempotent server-side, so a
 * second pass adds nothing and reports what it already had. Errant
 * clicks are accepted as cheap by owner ruling, which is the whole
 * reason there is no confirm step. Do not add one back.
 *
 * The LAST card is the Tuya Local replay form, unchanged from what it
 * always was: pick a blaster, type the appliance, name it, press
 * Create. It does not get whole-card click, because clicking a form
 * would fight with focusing its own fields.
 *
 * Action labels are the Plucker's own verb (owner ruling 2026-08-21,
 * overriding the handoff's Import / Importing / Re-plucked): PLUCK,
 * PLUCKING, PLUCKED on a first import, RE-PLUCKED after that.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { dialogStyles } from "./ir-dialog-styles.js";
import type { HairApi } from "./api.js";
import type {
    LearnedStore,
    LearnedStoreImport,
    PluckVendor,
    UnknownDevice,
} from "./types.js";

interface Candidate {
    integration: string;
    entityId: string;
    vendorName: string;
    blasterName: string;
    applianceLabel: string;
    applianceHelp: string;
}

type CardState = "idle" | "busy" | "done";

// Tweezers (matches the Plucker tab icon), for the replay card.
const ICON_TWEEZERS =
    "M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z";
// Tray with an arrow into it: codes coming out of a file and into HAIR.
const ICON_TRAY_DOWN =
    "M2,12H4V17H20V12H22V17A2,2 0 0,1 20,19H4A2,2 0 0,1 2,17V12M12,15L17,10H14V3H10V10H7L12,15Z";
const ICON_CHECK = "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z";
// A three-quarter arc; CSS spins it.
const ICON_SPINNER = "M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z";

/** How long the completion toast stays up. Non-blocking either way. */
const TOAST_MS = 4200;

const KIND_KEYS: Record<string, string> = {
    broadlink: "pluckstore.kind.broadlink",
    tuya_local: "pluckstore.kind.tuya_local",
};

@customElement("ir-pluck-add-remote-dialog")
export class IrPluckAddRemoteDialog extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property() public pendingEntity = "";

    @state() private _candidates: Candidate[] = [];
    @state() private _stores: LearnedStore[] = [];
    @state() private _entityId = "";
    @state() private _appliance = "";
    @state() private _name = "";
    @state() private _busy = false;
    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _cardState: Record<string, CardState> = {};
    @state() private _summaries: Record<string, string> = {};
    @state() private _imports: Record<string, number> = {};
    @state() private _toast = "";
    private _nameEdited = false;
    private _toastTimer: ReturnType<typeof setTimeout> | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        if (this._toastTimer !== null) clearTimeout(this._toastTimer);
    }

    private async _load(): Promise<void> {
        this._loading = true;
        // The two halves are independent: a Broadlink user with no
        // replay vendor still gets their cards, and a Tuya replay user
        // with no readable store still gets the form. Neither failure
        // may take the other down, so they are settled separately.
        const [stores, vendors] = await Promise.allSettled([
            this.api.listLearnedStores(),
            this.api.listPluckVendors(),
        ]);

        if (stores.status === "fulfilled") {
            this._stores = stores.value.stores;
        } else {
            this._stores = [];
            this._error = (stores.reason as Error).message;
        }

        if (vendors.status === "fulfilled") {
            this._candidates = this._flatten(vendors.value.vendors);
            const pre =
                this._candidates.find((c) => c.entityId === this.pendingEntity) ??
                (this._candidates.length === 1 ? this._candidates[0] : undefined);
            if (pre) {
                this._entityId = pre.entityId;
                this._autofillName();
            }
        } else {
            this._candidates = [];
        }
        this._loading = false;
    }

    private _flatten(vendors: PluckVendor[]): Candidate[] {
        const out: Candidate[] = [];
        for (const v of vendors) {
            for (const b of v.blasters) {
                out.push({
                    integration: v.integration,
                    entityId: b.entity_id,
                    vendorName: v.name,
                    blasterName: b.name,
                    applianceLabel: v.appliance_label || t("pluckdlg.appliance"),
                    applianceHelp: v.appliance_help || "",
                });
            }
        }
        return out;
    }

    private get _selected(): Candidate | undefined {
        return this._candidates.find((c) => c.entityId === this._entityId);
    }

    // -----------------------------------------------------------------
    // Learned-code stores
    // -----------------------------------------------------------------

    private _kind(store: LearnedStore): string {
        const key = KIND_KEYS[store.integration];
        return key ? t(key) : store.integration;
    }

    private _counts(store: LearnedStore): string {
        let line = t("pluckstore.counts_line", {
            subdevices: tp("pluckstore.n_subdevices", store.subdevices),
            codes: tp("pluckstore.n_codes", store.codes),
        });
        if (store.rf_codes > 0) {
            line += t("pluckstore.counts_rf", { count: store.rf_codes });
        }
        return line;
    }

    /**
     * The landing sentence, per UX brief section 4. Every zero-count
     * clause is omitted, so a clean import says nothing about RF and a
     * store with no failed learns says nothing about timings.
     *
     * When every signal was already in the catalog the sentence
     * collapses to the dedupe truth and stops there: repeating the wash
     * numbers for an import that changed nothing would read as though
     * something had happened.
     */
    private _landing(s: LearnedStoreImport): string {
        const head = t("pluckstore.landing.head", {
            remotes: tp("pluckstore.n_remotes", s.remotes),
            signals: tp("pluckstore.n_signals", s.signals),
        });
        const parts = [head];
        if (s.signals > 0 && s.already_present === s.signals) {
            parts.push(tp("pluckstore.landing.already", s.already_present));
            return parts.join(" ");
        }
        if (s.washed > 0) parts.push(tp("pluckstore.landing.washed", s.washed));
        if (s.kept_raw > 0) {
            parts.push(tp("pluckstore.landing.kept_raw", s.kept_raw));
        }
        if (s.toggle_pairs > 0) {
            parts.push(tp("pluckstore.landing.toggle_pairs", s.toggle_pairs));
        }
        if (s.rf_receipted > 0) {
            parts.push(tp("pluckstore.landing.rf", s.rf_receipted));
        }
        if (s.no_timings > 0) {
            parts.push(tp("pluckstore.landing.no_timings", s.no_timings));
        }
        if (s.already_present > 0) {
            parts.push(tp("pluckstore.landing.already", s.already_present));
        }
        return parts.join(" ");
    }

    private _actionLabel(store: LearnedStore): string {
        const state = this._cardState[store.store_id] ?? "idle";
        if (state === "busy") return t("pluckstore.action.plucking");
        if (state === "done") {
            return (this._imports[store.store_id] ?? 0) > 1
                ? t("pluckstore.action.replucked")
                : t("pluckstore.action.plucked");
        }
        return t("pluckstore.action.pluck");
    }

    private _showToast(text: string): void {
        this._toast = text;
        if (this._toastTimer !== null) clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(() => {
            this._toast = "";
            this._toastTimer = null;
        }, TOAST_MS);
    }

    private async _pluckStore(store: LearnedStore): Promise<void> {
        if (store.error) return;
        // A busy card ignores every further click until its own pluck
        // resolves, so a double click cannot double import.
        if (this._cardState[store.store_id] === "busy") return;

        this._cardState = { ...this._cardState, [store.store_id]: "busy" };
        this._error = null;
        try {
            const summary = await this.api.importLearnedStore(store.store_id);
            this._imports = {
                ...this._imports,
                [store.store_id]: (this._imports[store.store_id] ?? 0) + 1,
            };
            const sentence = this._landing(summary);
            this._summaries = {
                ...this._summaries,
                [store.store_id]: sentence,
            };
            this._cardState = { ...this._cardState, [store.store_id]: "done" };
            this._showToast(sentence);
            // The Plucker behind this dialog is now stale. Tell it, and
            // leave the dialog open: a user with three stores is very
            // likely to click the next one.
            this.dispatchEvent(
                new CustomEvent("stores-plucked", {
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._cardState = { ...this._cardState, [store.store_id]: "idle" };
            this._error = (err as Error).message;
        }
    }

    private _onCardKey(store: LearnedStore, e: KeyboardEvent): void {
        if (e.key !== "Enter" && e.key !== " ") return;
        e.preventDefault();
        void this._pluckStore(store);
    }

    // -----------------------------------------------------------------
    // Replay card (unchanged behavior)
    // -----------------------------------------------------------------

    private _autofillName(): void {
        if (this._nameEdited) return;
        const c = this._selected;
        if (!c) return;
        const appliance = this._appliance.trim();
        this._name = (
            appliance ? `${c.blasterName}: ${appliance}` : c.blasterName
        ).trim();
    }

    private _onVendorChange(e: Event): void {
        this._entityId = (e.target as HTMLSelectElement).value;
        this._autofillName();
    }

    private _onApplianceInput(e: Event): void {
        this._appliance = (e.target as HTMLInputElement).value;
        this._autofillName();
    }

    private _close(): void {
        this.dispatchEvent(
            new CustomEvent("closed", { bubbles: true, composed: true }),
        );
    }

    private async _create(): Promise<void> {
        const c = this._selected;
        if (!c) {
            this._error = t("pluckdlg.blaster_required");
            return;
        }
        if (!this._appliance.trim()) {
            this._error = t("pluckdlg.appliance_required");
            return;
        }
        if (!this._name.trim()) {
            this._error = t("common.name_required");
            return;
        }
        this._busy = true;
        this._error = null;
        try {
            const device: UnknownDevice = await this.api.createPluckedBlaster({
                vendor_entity_id: c.entityId,
                appliance: this._appliance.trim(),
                name: this._name.trim(),
            });
            this.dispatchEvent(
                new CustomEvent("blaster-created", {
                    detail: device,
                    bubbles: true,
                    composed: true,
                }),
            );
        } catch (err) {
            this._error = (err as Error).message;
        } finally {
            this._busy = false;
        }
    }

    // -----------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------

    private _renderStoreCard(store: LearnedStore) {
        const state = this._cardState[store.store_id] ?? "idle";
        const summary = this._summaries[store.store_id];
        const disabled = Boolean(store.error);
        const glyph =
            state === "busy"
                ? ICON_SPINNER
                : state === "done"
                  ? ICON_CHECK
                  : ICON_TRAY_DOWN;
        return html`
            <div
                class="device-card ${state} ${disabled ? "disabled" : ""}"
                @click=${() => void this._pluckStore(store)}
            >
                <div class="card-glyph">
                    <ha-svg-icon .path=${ICON_TRAY_DOWN}></ha-svg-icon>
                </div>
                <div class="card-main">
                    <div class="card-name">${store.friendly_name}</div>
                    <div class="card-kind">
                        ${this._kind(store)}
                        <span class="card-id">${store.store_id}</span>
                    </div>
                    ${store.error
                        ? html`<div class="card-error">
                              ${t("pluckstore.unreadable")}
                          </div>`
                        : summary
                          ? html`<div class="card-summary">${summary}</div>`
                          : html`<div class="card-counts">
                                ${this._counts(store)}
                            </div>`}
                </div>
                <div class="card-action-wrap">
                    <button
                        class="card-action ${state}"
                        aria-label=${t("pluckstore.action.aria", {
                            name: store.friendly_name,
                        })}
                        ?disabled=${disabled}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            void this._pluckStore(store);
                        }}
                        @keydown=${(e: KeyboardEvent) =>
                            this._onCardKey(store, e)}
                    >
                        <ha-svg-icon .path=${glyph}></ha-svg-icon>
                    </button>
                    <span class="card-action-text"
                        >${this._actionLabel(store)}</span
                    >
                </div>
            </div>
        `;
    }

    private _renderEmptyCard() {
        return html`
            <div class="device-card disabled">
                <div class="card-glyph">
                    <ha-svg-icon .path=${ICON_TRAY_DOWN}></ha-svg-icon>
                </div>
                <div class="card-main">
                    <div class="card-name">${t("pluckstore.empty_name")}</div>
                    <div class="card-reason">${t("pluckstore.empty_reason")}</div>
                </div>
            </div>
        `;
    }

    private _renderReplayCard() {
        const c = this._selected;
        const none = this._candidates.length === 0;
        return html`
            <div class="device-card device-card-form ${none ? "disabled" : ""}">
                <div class="card-glyph">
                    <ha-svg-icon .path=${ICON_TWEEZERS}></ha-svg-icon>
                </div>
                <div class="form-card-body">
                    <div class="form-card-title">
                        ${this._candidates[0]?.vendorName ??
                        t("pluckstore.replay.title")}
                    </div>
                    <div class="form-card-line">
                        ${t("pluckstore.replay.line")}
                    </div>
                    ${none
                        ? html`<div class="card-reason">
                              ${t("pluckdlg.no_blasters")}
                          </div>`
                        : html`
                              <div class="field">
                                  <label>${t("pluckdlg.pluck_from")}</label>
                                  <select
                                      .value=${this._entityId}
                                      @change=${this._onVendorChange}
                                  >
                                      <option value="">
                                          ${t("pluckdlg.select_blaster")}
                                      </option>
                                      ${this._candidates.map(
                                          (cand) => html`<option
                                              value=${cand.entityId}
                                          >
                                              ${cand.vendorName}:
                                              ${cand.blasterName}
                                          </option>`,
                                      )}
                                  </select>
                              </div>
                              <div class="field">
                                  <label
                                      >${c?.applianceLabel ??
                                      t("pluckdlg.appliance")}</label
                                  >
                                  <input
                                      type="text"
                                      .value=${this._appliance}
                                      placeholder=${t(
                                          "pluckdlg.appliance_placeholder",
                                      )}
                                      required
                                      @input=${this._onApplianceInput}
                                  />
                                  ${c?.applianceHelp
                                      ? html`<div class="help">
                                            ${c.applianceHelp}
                                        </div>`
                                      : ""}
                              </div>
                              <div class="field">
                                  <label>${t("common.name")}</label>
                                  <input
                                      type="text"
                                      .value=${this._name}
                                      placeholder=${t(
                                          "pluckdlg.name_placeholder",
                                      )}
                                      @input=${(e: Event) => {
                                          this._name = (
                                              e.target as HTMLInputElement
                                          ).value;
                                          this._nameEdited = true;
                                      }}
                                  />
                              </div>
                              <div class="tuya-create-row">
                                  <button
                                      class="action-btn create-btn"
                                      @click=${this._create}
                                      ?disabled=${this._busy}
                                  >
                                      ${this._busy
                                          ? t("common.creating")
                                          : t("common.create")}
                                  </button>
                              </div>
                          `}
                </div>
            </div>
        `;
    }

    render() {
        return html`
            <ha-dialog
                open
                heading=${t("pluckdlg.add_heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <!-- BOTH, deliberately. HA's ha-dialog moved to wa-dialog
                     and now takes its title from this slot, leaving the
                     heading attribute inert; an older ha-dialog reads the
                     attribute and drops the unmatched slot. Neither shows
                     two titles, and the header reads "Add Blaster" either
                     way, which is the owner ruling. -->
                <span slot="headerTitle">${t("pluckdlg.add_heading")}</span>
                ${this._error
                    ? html`<ha-alert alert-type="error">${this._error}</ha-alert>`
                    : ""}

                <div class="dlg-body">
                    ${this._loading
                        ? html`<div class="muted">
                              ${t("pluckdlg.loading_blasters")}
                          </div>`
                        : html`
                              ${this._stores.length === 0
                                  ? this._renderEmptyCard()
                                  : this._stores.map((s) =>
                                        this._renderStoreCard(s),
                                    )}
                              ${this._renderReplayCard()}
                          `}
                    ${this._toast
                        ? html`<div class="toast">${this._toast}</div>`
                        : nothing}
                </div>

                <div class="dialog-actions">
                    <!-- CLOSE, not Cancel (owner ruling 2026-08-21).
                         Nothing here is cancelable: a card click imports
                         immediately and the replay form has its own
                         Create button, so this button has never undone
                         anything. It dismisses the window, and saying
                         Cancel implied there was something to take
                         back. Reuses common.close, which every
                         dictionary already carries. -->
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${t("common.close")}
                    </button>
                </div>
            </ha-dialog>
        `;
    }

    static styles = [
        dialogStyles,
        css`
        ha-dialog {
            --mdc-dialog-max-width: 560px;
            --mdc-dialog-min-width: min(560px, 92vw);
        }
        .dlg-body {
            max-height: min(58vh, 520px);
            overflow-y: auto;
            margin: 0 -4px;
            padding: 0 4px;
            position: relative;
        }
        .help {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        .muted {
            color: var(--secondary-text-color);
            font-size: 0.9rem;
            margin: 12px 0;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }

        /* --- One card per store; the whole card is the pluck target. --- */
        .device-card {
            display: flex;
            align-items: flex-start;
            gap: 14px;
            padding: 14px 14px 14px 16px;
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            margin-bottom: 10px;
            transition: background 150ms ease, border-color 150ms ease;
            cursor: pointer;
        }
        .device-card:last-child {
            margin-bottom: 0;
        }
        .device-card:hover:not(.disabled):not(.busy) {
            background: rgba(120, 144, 156, 0.08);
            border-color: #78909c;
        }
        .device-card.busy {
            cursor: default;
        }
        .device-card.done {
            border-color: rgba(120, 144, 156, 0.5);
            background: rgba(69, 90, 100, 0.08);
        }
        .device-card.disabled {
            cursor: default;
            opacity: 0.6;
        }
        .device-card.device-card-form {
            cursor: default;
        }
        .device-card.device-card-form:hover {
            background: none;
            border-color: var(--divider-color);
        }

        .card-glyph {
            flex: none;
            width: 22px;
            margin-top: 2px;
            color: #455a64;
        }
        .card-glyph ha-svg-icon {
            --mdc-icon-size: 20px;
        }
        .card-main,
        .form-card-body {
            flex: 1;
            min-width: 0;
        }
        .card-name,
        .form-card-title {
            font-size: 0.92rem;
            color: var(--primary-text-color);
        }
        .card-kind {
            font-size: 0.74rem;
            color: #78909c;
            margin-top: 3px;
        }
        .card-kind .card-id {
            color: var(--secondary-text-color);
            font-family: monospace;
            margin-left: 6px;
        }
        .card-counts,
        .form-card-line {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        .card-summary {
            font-size: 0.78rem;
            color: var(--primary-text-color);
            margin-top: 4px;
            line-height: 1.5;
        }
        .card-error {
            font-size: 0.78rem;
            color: var(--error-color, #e65100);
            margin-top: 4px;
            font-style: italic;
        }
        .card-reason {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            font-style: italic;
            margin-top: 4px;
        }

        /* --- The action control: idle -> busy -> done. --- */
        .card-action-wrap {
            flex: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            width: 62px;
        }
        .card-action {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: 1px solid #78909c;
            background: none;
            color: #78909c;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            padding: 0;
            transition: background 150ms ease, border-color 150ms ease,
                color 150ms ease;
        }
        .card-action ha-svg-icon {
            --mdc-icon-size: 18px;
        }
        .device-card:hover:not(.disabled):not(.busy) .card-action {
            background: rgba(120, 144, 156, 0.15);
        }
        .card-action.busy {
            border-color: var(--divider-color);
            color: var(--secondary-text-color);
            cursor: default;
        }
        .card-action.busy ha-svg-icon {
            animation: ir-pluck-spin 900ms linear infinite;
        }
        .card-action.done {
            background: rgba(69, 90, 100, 0.15);
        }
        .card-action:disabled {
            opacity: 0.4;
            border-color: var(--divider-color);
            cursor: default;
        }
        @keyframes ir-pluck-spin {
            from {
                transform: rotate(0deg);
            }
            to {
                transform: rotate(360deg);
            }
        }
        .card-action-text {
            font-size: 0.6rem;
            color: var(--secondary-text-color);
            text-transform: uppercase;
            letter-spacing: 0.03em;
            text-align: center;
        }

        /* --- The replay form, relocated but not restructured. --- */
        .field {
            margin: 10px 0 0;
        }
        .tuya-create-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 12px;
        }
        .create-btn {
            background: #455a64;
            color: #fff;
            border-color: #455a64;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
        input[type="text"]:focus,
        select:focus {
            outline: none;
            border-color: #455a64;
        }

        /* --- Completion toast: an acknowledgment, never a modal. --- */
        .toast {
            position: sticky;
            bottom: 4px;
            margin: 10px 2px 2px;
            background: var(--secondary-background-color);
            border: 1px solid #78909c;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 0.78rem;
            color: var(--primary-text-color);
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
            line-height: 1.5;
            pointer-events: none;
        }
    `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-pluck-add-remote-dialog": IrPluckAddRemoteDialog;
    }
}
