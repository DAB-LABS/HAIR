/**
 * The Mirror tab (v0.6.3) -- what your house transmits.
 *
 * Renders the synthetic Mirror catalog device (source "echo",
 * fingerprint "hair-mirror") the SignalMonitor maintains: one row per
 * distinct send identity, created at SEND time and enriched with
 * heard_by when a receiver echoes it back. Every HA-originated IR
 * transmission lands here -- HAIR device commands, catalog tests,
 * automations, and foreign integrations caught by emitter state
 * beacons -- with its provenance and its journey (via which emitter,
 * heard in which areas).
 *
 * Deliberately a log: no delete, no dismiss, no reorder, no clear-all.
 * Rows carry the Sniffer's exact action chips (Assign / Test / Trigger
 * via the shared actionChipStyles -- this is the first tab to never
 * own a private copy) with the v0.5.7 corner count-dots. Triggers
 * created here are legitimate: they fire when the identity arrives
 * from OUTSIDE Home Assistant (the echo gate keeps the house's own
 * sends from tripping them), and the trigger dialog says so in one
 * line (mirrorContext).
 *
 * "Not heard" renders neutral grey, not amber: plenty of homes are
 * transmit-only, and normal is not an alarm. The Not heard FILTER chip
 * keeps its amber for troubleshooting findability (the dead-LED
 * finder). Zero-receiver homes suppress the heard clause entirely.
 *
 * Authoritative design: docs/internal/mockups/mirror-tab-mockup-m5.html.
 */
import { LitElement, html, css } from "lit";
import { actionChipStyles } from "./ir-action-chip-styles";
import { customElement, property, state } from "./decorators.js";
import { HairApi } from "./api.js";
import "./ir-assign-signal-dialog.js";
import "./ir-confirm-dialog.js";
import "./ir-signal-editor.js";
import "./ir-test-emitter-dialog.js";
import "./ir-trigger-dialog.js";
import "./ir-count-dot.js";
import "./ir-trigger-popover.js";
import "./ir-assigned-popover.js";
import { MIRROR_DEVICE_FP, triggerMatchesSignal } from "./types.js";
import type {
    AssignResult,
    IRTrigger,
    ReceiverInfo,
    SignalAssignment,
    UnknownDevice,
    UnknownSignal,
    UnknownSignalEvent,
} from "./types.js";

/** Relative time like "2m" (compact, for the row meta). */
function relShort(iso: string | undefined): string {
    if (!iso) return "";
    try {
        const diff = Date.now() - new Date(iso).getTime();
        if (diff < 60_000) return "just now";
        if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m`;
        if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h`;
        return `${Math.floor(diff / 86_400_000)}d`;
    } catch {
        return "";
    }
}

// mdi:content-copy (the code glyph, same as the other catalog tabs)
const ICON_COPY =
    "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z";

/** The separator record_send/_match_echo bake into echo_source. */
const VIA_SEP = " -- via ";

/** Bloom duration must match the CSS animation. */
const BLOOM_MS = 1400;

/** Debounce between a live push and the full device re-fetch. */
const REFRESH_DEBOUNCE_MS = 300;

interface MirrorRowView {
    sig: UnknownSignal;
    title: string;
    pill: string | null;
    pillRaw: boolean;
    via: string;
    viaFull: string;
    emitters: string[];
    chip: string;
    heard: string | null; // null = suppress clause (zero-receiver home)
    heardOk: boolean;
}

@customElement("ir-mirror")
export class IrMirror extends LitElement {
    @property({ attribute: false }) public api!: HairApi;
    @property({ attribute: false }) public hass?: any;

    @state() private _device: UnknownDevice | null = null;
    @state() private _loading = true;
    @state() private _error: string | null = null;
    @state() private _triggers: IRTrigger[] = [];
    @state() private _receivers: ReceiverInfo[] = [];
    @state() private _hasReceivers = true;
    @state() private _filter: string = "all"; // "all" | "notheard" | emitter name
    @state() private _search = "";
    @state() private _bloomIds = new Set<string>();

    // Dialog / popover state (the Sniffer's row-action vocabulary)
    @state() private _assignSignal: {
        signal: UnknownSignal;
        initialMode: "existing" | "new";
    } | null = null;
    @state() private _assignedPopover: {
        signal: UnknownSignal;
        top: number;
        left: number;
    } | null = null;
    @state() private _triggerDialog: UnknownSignal | null = null;
    @state() private _triggerEditDialog: IRTrigger | null = null;
    @state() private _triggerPopover: {
        signal: UnknownSignal;
        top: number;
        left: number;
    } | null = null;
    @state() private _confirmDeleteTriggerId: string | null = null;
    @state() private _editSignal: UnknownSignal | null = null;
    @state() private _testDialog: UnknownSignal | null = null;
    @state() private _testEmitters: string[] = [];
    @state() private _testingSignalId: string | null = null;
    @state() private _testResult: string | null = null;

    private _unsubSignals: (() => Promise<void>) | null = null;
    private _unsubUpdated: (() => Promise<void>) | null = null;
    private _refreshTimer: number | null = null;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
        void this._subscribe();
    }

    disconnectedCallback(): void {
        super.disconnectedCallback();
        void this._unsubscribe();
        this._removePopoverDismiss();
        if (this._refreshTimer !== null) {
            clearTimeout(this._refreshTimer);
            this._refreshTimer = null;
        }
    }

    // -----------------------------------------------------------------
    // Data
    // -----------------------------------------------------------------

    private async _load(): Promise<void> {
        this._loading = true;
        try {
            const [summaries, triggers, status] = await Promise.all([
                this.api.getUnknownDevices({ source: "echo", min_hits: 0 }),
                this.api.listTriggers(),
                this.api.getSnifferStatus(),
            ]);
            this._triggers = triggers;
            this._hasReceivers = status.has_receivers;
            const mirror = summaries.find(
                (d) => d.fingerprint === MIRROR_DEVICE_FP,
            );
            this._device = mirror
                ? await this.api.getUnknownDevice(mirror.id)
                : null;
            this._error = null;
            this.api
                .listReceivers()
                .then((r) => {
                    this._receivers = r;
                })
                .catch(() => {
                    this._receivers = [];
                });
        } catch (err) {
            this._error = `Failed to load: ${(err as Error).message}`;
        } finally {
            this._loading = false;
        }
    }

    private async _refreshDevice(): Promise<void> {
        if (!this._device) {
            await this._load();
            return;
        }
        try {
            this._device = await this.api.getUnknownDevice(this._device.id);
        } catch {
            await this._load();
        }
    }

    private async _subscribe(): Promise<void> {
        try {
            this._unsubSignals = await this.api.subscribeUnknownSignals(
                (ev) => this._onLiveSignal(ev),
            );
        } catch {
            // Non-fatal.
        }
        try {
            this._unsubUpdated = await this.api.subscribeSignalUpdated(() => {
                void this._refreshDots();
            });
        } catch {
            // Non-fatal.
        }
    }

    private async _unsubscribe(): Promise<void> {
        if (this._unsubSignals) {
            await this._unsubSignals();
            this._unsubSignals = null;
        }
        if (this._unsubUpdated) {
            await this._unsubUpdated();
            this._unsubUpdated = null;
        }
    }

    /** Assignment/trigger dots changed elsewhere: refresh both. */
    private async _refreshDots(): Promise<void> {
        try {
            this._triggers = await this.api.listTriggers();
        } catch {
            // Non-fatal.
        }
        await this._refreshDevice();
    }

    private _onLiveSignal(ev: UnknownSignalEvent): void {
        // Only the house's own sends belong to this tab.
        if (ev.device_fingerprint !== MIRROR_DEVICE_FP) return;

        // Silver bloom on the touched row while you watch.
        this._bloomIds = new Set([...this._bloomIds, ev.signal_id]);
        setTimeout(() => {
            const next = new Set(this._bloomIds);
            next.delete(ev.signal_id);
            this._bloomIds = next;
        }, BLOOM_MS);

        // Debounced re-fetch: a dial drag can fire many sends per second.
        if (this._refreshTimer !== null) clearTimeout(this._refreshTimer);
        this._refreshTimer = window.setTimeout(() => {
            this._refreshTimer = null;
            void this._refreshDevice();
        }, REFRESH_DEBOUNCE_MS);
    }

    // -----------------------------------------------------------------
    // Row derivation
    // -----------------------------------------------------------------

    private _friendlyReceiver(entityId: string): string {
        const match = this._receivers.find((r) => r.entity_id === entityId);
        if (match?.name) return match.name;
        const st = this.hass?.states?.[entityId];
        return st?.attributes?.friendly_name ?? entityId;
    }

    /** Resolve a receiver's HA area name, or null (v0.5.7 machinery:
     * entity area first, then its device's area). */
    private _receiverArea(entityId: string): string | null {
        const ent = this.hass?.entities?.[entityId];
        const areaId =
            ent?.area_id ??
            (ent?.device_id
                ? this.hass?.devices?.[ent.device_id]?.area_id
                : null);
        if (!areaId) return null;
        return this.hass?.areas?.[areaId]?.name ?? null;
    }

    private _decodedDisplay(sig: UnknownSignal): string | null {
        const fp = sig.decoded_fingerprint;
        if (!fp) return null;
        const parts = fp.split(":");
        if (parts.length >= 3) {
            return `${parts[0]} ${parts[1]} : ${parts.slice(2).join(":")}`;
        }
        return fp;
    }

    private _rowView(sig: UnknownSignal): MirrorRowView {
        const src = sig.echo_source ?? "";
        const sepIdx = src.indexOf(VIA_SEP);
        const label = sepIdx >= 0 ? src.slice(0, sepIdx) : src;
        const viaFull = sepIdx >= 0 ? src.slice(sepIdx + VIA_SEP.length) : "";
        const emitters = viaFull ? viaFull.split(", ") : [];

        let chip: string;
        let labelTitle: string | null = null;
        if (label === "automation send" || label === "integration send") {
            chip = label;
        } else if (label.startsWith("Catalog test")) {
            // "Catalog test: <alias>" or bare "Catalog test" (unnamed
            // signal) -- either way the chip is the provenance and the
            // title falls through to the identity chain below.
            chip = "Catalog test";
            labelTitle =
                label.slice("Catalog test".length).replace(/^:\s*/, "").trim() ||
                null;
        } else if (label) {
            chip = "HAIR device";
            labelTitle = label;
        } else {
            chip = "send";
        }

        // Title chain: alias > send label > decoded identity > the S/L
        // diamonds (the panel's established unnamed-signal identity) >
        // "Unknown send" (foreign, never heard, nothing known).
        const title =
            sig.alias ||
            labelTitle ||
            this._decodedDisplay(sig) ||
            (sig.sl_pattern
                ? [...sig.sl_pattern]
                      .map((ch) => (ch === "L" ? "◆" : "◇"))
                      .join("")
                : null) ||
            "Unknown send";

        const pill = sig.decoded_protocol ?? sig.protocol;
        const pillRaw = !sig.decoded_protocol;

        const via =
            emitters.length > 2
                ? `via ${emitters.length} emitters`
                : viaFull
                  ? `via ${viaFull}`
                  : "";

        // Zero-receiver homes suppress the clause entirely: amber (or even
        // grey) everywhere would be alarm without information.
        let heard: string | null = null;
        let heardOk = false;
        if (this._hasReceivers) {
            const by = sig.heard_by ?? [];
            if (by.length === 0) {
                heard = "not heard";
            } else {
                heardOk = true;
                const areas = by.map((r) => this._receiverArea(r));
                if (areas.every((a) => a !== null)) {
                    const unique = [...new Set(areas as string[])];
                    heard = `heard in ${unique.join(", ")}`;
                } else {
                    const names = by.map((r) => this._friendlyReceiver(r));
                    heard = `heard by ${names.join(", ")}`;
                }
            }
        }

        return {
            sig,
            title,
            pill: pill ?? null,
            pillRaw,
            via,
            viaFull,
            emitters,
            chip,
            heard,
            heardOk,
        };
    }

    private _rows(): MirrorRowView[] {
        return (this._device?.signals ?? []).map((s) => this._rowView(s));
    }

    private _filteredRows(rows: MirrorRowView[]): MirrorRowView[] {
        let out = rows;
        if (this._filter === "notheard") {
            out = out.filter(
                (r) => (r.sig.heard_by ?? []).length === 0,
            );
        } else if (this._filter !== "all") {
            out = out.filter((r) => r.emitters.includes(this._filter));
        }
        const q = this._search.trim().toLowerCase();
        if (q) {
            out = out.filter((r) =>
                [
                    r.title,
                    r.pill ?? "",
                    r.viaFull,
                    r.chip,
                    r.sig.decoded_fingerprint ?? "",
                    r.sig.alias ?? "",
                ]
                    .join(" ")
                    .toLowerCase()
                    .includes(q),
            );
        }
        return out;
    }

    // -----------------------------------------------------------------
    // Dots (identity-aware, v0.5.8)
    // -----------------------------------------------------------------

    private _triggerCountFor(signal: UnknownSignal): number {
        return this._triggers.filter((t) => triggerMatchesSignal(t, signal))
            .length;
    }

    // -----------------------------------------------------------------
    // Row actions -- the Sniffer's vocabulary, minus delete (it's a log)
    // -----------------------------------------------------------------

    private _onAssignClick(signal: UnknownSignal, ev?: Event): void {
        if (!this._device) return;
        if (!signal.assigned_to?.length) {
            this._assignSignal = { signal, initialMode: "existing" };
            return;
        }
        const btn = ev?.currentTarget as HTMLElement | undefined;
        const rect = btn?.getBoundingClientRect();
        this._assignedPopover = {
            signal,
            top: rect ? rect.bottom + 4 : 120,
            left: rect ? Math.max(8, rect.right - 220) : 120,
        };
        this._installPopoverDismiss();
    }

    private _closeAssignedPopover(): void {
        this._assignedPopover = null;
        this._removePopoverDismiss();
    }

    private _onAssignedPopoverCreateNew(): void {
        const p = this._assignedPopover;
        this._closeAssignedPopover();
        if (p) this._assignSignal = { signal: p.signal, initialMode: "existing" };
    }

    private _onAssignedPopoverOpen(ev: CustomEvent): void {
        const a = ev.detail as SignalAssignment | undefined;
        this._closeAssignedPopover();
        if (!a) return;
        this.dispatchEvent(
            new CustomEvent("navigate-device", {
                detail: a.device_id,
                bubbles: true,
                composed: true,
            }),
        );
    }

    private async _onSignalAssigned(_ev: CustomEvent<AssignResult>): Promise<void> {
        this._assignSignal = null;
        await this._refreshDots();
    }

    private _openTriggerDialog(signal: UnknownSignal, ev?: Event): void {
        const matches = this._triggers.filter((t) =>
            triggerMatchesSignal(t, signal),
        );
        if (matches.length === 0) {
            this._triggerDialog = signal;
            return;
        }
        const btn = ev?.currentTarget as HTMLElement | undefined;
        const rect = btn?.getBoundingClientRect();
        this._triggerPopover = {
            signal,
            top: rect ? rect.bottom + 4 : 120,
            left: rect ? Math.max(8, rect.right - 220) : 120,
        };
        this._installPopoverDismiss();
    }

    private _closeTriggerPopover(): void {
        this._triggerPopover = null;
        this._removePopoverDismiss();
    }

    private _onPopoverCreateNew(): void {
        const p = this._triggerPopover;
        this._closeTriggerPopover();
        if (p) this._triggerDialog = p.signal;
    }

    private _onPopoverEditTrigger(ev: CustomEvent): void {
        const t = ev.detail as IRTrigger | undefined;
        this._closeTriggerPopover();
        if (t) this._triggerEditDialog = t;
    }

    private async _onTriggerSaved(): Promise<void> {
        this._triggerDialog = null;
        this._triggerEditDialog = null;
        try {
            this._triggers = await this.api.listTriggers();
        } catch {
            // Non-fatal.
        }
    }

    private _closeTriggerDialog(): void {
        this._triggerDialog = null;
        this._triggerEditDialog = null;
    }

    private _requestDeleteTrigger(triggerId: string): void {
        this._closeTriggerDialog();
        this._confirmDeleteTriggerId = triggerId;
    }

    private async _confirmDeleteTrigger(): Promise<void> {
        const id = this._confirmDeleteTriggerId;
        this._confirmDeleteTriggerId = null;
        if (!id) return;
        try {
            await this.api.deleteTrigger(id);
            this._triggers = await this.api.listTriggers();
        } catch (err) {
            this._error = `Delete failed: ${(err as Error).message}`;
        }
    }

    private _onDocClickForPopover = (ev: Event): void => {
        const path = ev.composedPath();
        const trig = this.shadowRoot?.querySelector("ir-trigger-popover");
        const asgn = this.shadowRoot?.querySelector("ir-assigned-popover");
        if ((trig && path.includes(trig)) || (asgn && path.includes(asgn))) {
            return;
        }
        this._closeTriggerPopover();
        this._closeAssignedPopover();
    };

    private _onScrollForPopover = (): void => {
        this._closeTriggerPopover();
        this._closeAssignedPopover();
    };

    private _installPopoverDismiss(): void {
        setTimeout(() => {
            document.addEventListener("click", this._onDocClickForPopover, true);
            window.addEventListener("scroll", this._onScrollForPopover, true);
        }, 0);
    }

    private _removePopoverDismiss(): void {
        document.removeEventListener("click", this._onDocClickForPopover, true);
        window.removeEventListener("scroll", this._onScrollForPopover, true);
    }

    private async _sendTest(e: CustomEvent): Promise<void> {
        if (!this._testDialog) return;
        const signal = this._testDialog;
        const emitters = e.detail.emitters as string[];
        if (emitters.length === 0) return;
        this._testingSignalId = signal.id;
        this._testResult = null;
        this._testDialog = null;
        try {
            const results = await Promise.allSettled(
                emitters.map((eid) => this.api.testSignal(signal.id, eid)),
            );
            const sent = results.filter(
                (r) => r.status === "fulfilled" && r.value.sent,
            ).length;
            const total = emitters.length;
            if (sent === total) {
                this._testResult =
                    total === 1 ? "Sent!" : `Sent! (${sent}/${total})`;
            } else if (sent === 0) {
                this._testResult = "Failed";
            } else {
                this._testResult = `Sent (${sent}/${total})`;
            }
        } catch {
            this._testResult = "Error";
        }
        setTimeout(() => {
            this._testResult = null;
            this._testingSignalId = null;
        }, 3000);
    }

    private async _onSignalEdited(): Promise<void> {
        this._editSignal = null;
        await this._refreshDevice();
    }

    // -----------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------

    render() {
        const rows = this._rows();
        const filtered = this._filteredRows(rows);

        return html`
            ${this._error
                ? html`<div class="error">${this._error}</div>`
                : ""}
            ${this._loading && !this._device
                ? html`<div class="loading">Loading…</div>`
                : rows.length === 0
                  ? this._renderEmpty()
                  : html`
                        ${this._renderStats(rows)}
                        ${this._renderToolbar(rows)}
                        <div class="rows">
                            ${filtered.length === 0
                                ? html`<div class="no-match">
                                      No sends match.
                                  </div>`
                                : filtered.map((r) => this._renderRow(r))}
                        </div>
                    `}
            ${this._renderDialogs()}
        `;
    }

    private _renderStats(rows: MirrorRowView[]) {
        const notHeard = rows.filter(
            (r) => (r.sig.heard_by ?? []).length === 0,
        ).length;
        const emitters = new Set<string>();
        for (const r of rows) r.emitters.forEach((e) => emitters.add(e));
        const last = this._device?.last_seen;
        return html`
            <div class="stats">
                <div class="stat">
                    <div class="v">${this._device?.hit_count ?? 0}</div>
                    <div class="l">SENDS</div>
                </div>
                ${this._hasReceivers
                    ? html`
                          <div class="stat">
                              <div class="v ${notHeard ? "warn" : ""}">
                                  ${notHeard}
                              </div>
                              <div class="l">NOT HEARD</div>
                          </div>
                      `
                    : ""}
                <div class="stat">
                    <div class="v">${emitters.size}</div>
                    <div class="l">EMITTERS</div>
                </div>
                <div class="stat">
                    <div class="v">${rows.length}</div>
                    <div class="l">SIGNALS</div>
                </div>
                <span class="updated">
                    ${this._hasReceivers
                        ? last
                            ? `last send ${relShort(last)}${relShort(last) === "just now" ? "" : " ago"}`
                            : ""
                        : "no receivers"}
                </span>
            </div>
        `;
    }

    private _renderToolbar(rows: MirrorRowView[]) {
        const notHeard = rows.filter(
            (r) => (r.sig.heard_by ?? []).length === 0,
        ).length;
        const emitterCounts = new Map<string, number>();
        for (const r of rows) {
            for (const e of r.emitters) {
                emitterCounts.set(e, (emitterCounts.get(e) ?? 0) + 1);
            }
        }
        return html`
            <div class="toolbar">
                <button
                    class="fchip ${this._filter === "all" ? "on" : ""}"
                    @click=${() => (this._filter = "all")}
                >
                    All (${rows.length})
                </button>
                ${this._hasReceivers
                    ? html`
                          <button
                              class="fchip warnc ${this._filter === "notheard" ? "on" : ""}"
                              @click=${() => (this._filter = "notheard")}
                          >
                              Not heard (${notHeard})
                          </button>
                      `
                    : ""}
                ${[...emitterCounts.entries()].map(
                    ([name, count]) => html`
                        <button
                            class="fchip ${this._filter === name ? "on" : ""}"
                            @click=${() => (this._filter = name)}
                        >
                            ${name} (${count})
                        </button>
                    `,
                )}
                <input
                    class="search"
                    type="text"
                    placeholder="Search sends..."
                    .value=${this._search}
                    @input=${(e: Event) => {
                        this._search = (e.target as HTMLInputElement).value;
                    }}
                />
            </div>
        `;
    }

    private _renderRow(r: MirrorRowView) {
        const sig = r.sig;
        const bloom = this._bloomIds.has(sig.id);
        const actionable = !!sig.code;
        const isTesting = this._testingSignalId === sig.id;
        return html`
            <div class="mrow ${bloom ? "bloom" : ""}">
                <div class="mrow-main">
                    <div class="mrow-title">
                        <span class="name">${r.title}</span>
                        ${r.pill
                            ? html`<span
                                  class="pill ${r.pillRaw ? "raw" : ""}"
                                  >${r.pill}</span
                              >`
                            : ""}
                    </div>
                    <div class="mrow-sub">
                        ${r.via
                            ? html`<span title=${r.viaFull}>${r.via}</span>`
                            : ""}
                        ${r.heard !== null
                            ? html`
                                  <span class="arrow">&#10142;</span>
                                  <span
                                      class=${r.heardOk
                                          ? "heard"
                                          : "not-heard"}
                                      >${r.heard}</span
                                  >
                              `
                            : ""}
                        <span class="src-chip">${r.chip}</span>
                    </div>
                </div>
                <div class="mrow-meta">
                    <span class="counts"
                        >${sig.hit_count}
                        ${sig.hit_count === 1 ? "send" : "sends"}${sig.last_seen
                            ? html` &middot; ${relShort(sig.last_seen)}`
                            : ""}</span
                    >
                    ${sig.code
                        ? html`
                              <button
                                  class="code-btn"
                                  title="View or edit code"
                                  @click=${(e: Event) => {
                                      e.stopPropagation();
                                      this._editSignal = sig;
                                  }}
                              >
                                  <ha-svg-icon
                                      .path=${ICON_COPY}
                                      style="--mdc-icon-size:10px"
                                  ></ha-svg-icon>
                              </button>
                          `
                        : ""}
                    <button
                        class="action-btn assign-btn"
                        ?disabled=${!actionable}
                        title=${!actionable
                            ? "Identity unknown -- nothing was heard back to assign"
                            : sig.assignment_count && sig.assigned_to?.length
                              ? sig.assignment_count === 1
                                  ? `Assigned to ${sig.assigned_to[0].device_name} / ${sig.assigned_to[0].command_name}`
                                  : `Assigned to ${sig.assignment_count} commands:\n- ${sig.assigned_to.map((a) => `${a.device_name} / ${a.command_name}`).join("\n- ")}`
                              : "Assign this signal to a HAIR device"}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._onAssignClick(sig, e);
                        }}
                    >Assign<ir-count-dot
                            color="green"
                            .count=${sig.assignment_count ?? 0}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${!actionable || isTesting}
                        title=${actionable
                            ? "Send this signal through an emitter to test it"
                            : "Identity unknown -- nothing to send"}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._testDialog = sig;
                        }}
                    >${isTesting
                        ? (this._testResult ?? "Sending...")
                        : "Test"}</button>
                    <button
                        class="action-btn trigger-btn"
                        ?disabled=${!actionable}
                        title=${!actionable
                            ? "Identity unknown -- nothing to bind"
                            : this._triggerCountFor(sig) > 0
                              ? "Edit trigger(s) for this signal"
                              : "Fires when this signal arrives from outside Home Assistant"}
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._openTriggerDialog(sig, e);
                        }}
                    >Trigger<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(sig)}
                        ></ir-count-dot></button>
                </div>
            </div>
        `;
    }

    private _renderEmpty() {
        return html`
            <div class="empty">
                <div class="mirror-glyph"></div>
                <div class="empty-title">Nothing sent yet</div>
                <div class="empty-sub">
                    Commands sent by HAIR devices, automations, or any
                    integration on the infrared platform will appear here,
                    with where they went and who heard them.
                </div>
            </div>
        `;
    }

    private _renderDialogs() {
        return html`
            ${this._triggerPopover
                ? html`<ir-trigger-popover
                      .triggers=${this._triggers.filter((t) =>
                          triggerMatchesSignal(t, this._triggerPopover!.signal),
                      )}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`
                : ""}
            ${this._assignedPopover
                ? html`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to ?? []}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`
                : ""}
            ${this._triggerDialog
                ? html`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.fingerprint}
                      .byteHash=${this._triggerDialog.byte_hash ?? null}
                      .decodedFingerprint=${this._triggerDialog.decoded_fingerprint ?? null}
                      .protocol=${this._triggerDialog.protocol}
                      .code=${this._triggerDialog.code}
                      .slPattern=${this._triggerDialog.sl_pattern ?? null}
                      .alias=${this._triggerDialog.alias || null}
                      .mirrorContext=${true}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                  ></ir-trigger-dialog>`
                : ""}
            ${this._triggerEditDialog
                ? html`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      .mirrorContext=${true}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${(e: CustomEvent) =>
                          this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`
                : ""}
            ${this._confirmDeleteTriggerId
                ? html`<ir-confirm-dialog
                      title="Delete Trigger"
                      message="Remove this trigger permanently? Automations using it will stop firing."
                      confirmLabel="Delete"
                      .destructive=${true}
                      @confirmed=${this._confirmDeleteTrigger}
                      @closed=${() => (this._confirmDeleteTriggerId = null)}
                  ></ir-confirm-dialog>`
                : ""}
            ${this._assignSignal && this._device
                ? html`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._device.id}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${""}
                      .initialMode=${this._assignSignal.initialMode}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${() => (this._assignSignal = null)}
                  ></ir-assign-signal-dialog>`
                : ""}
            ${this._editSignal && this._device
                ? html`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._device.id}
                      .signalId=${this._editSignal.id}
                      .initialPronto=${this._editSignal.code ?? ""}
                      .initialAlias=${this._editSignal.alias ?? ""}
                      .initialSendCount=${this._editSignal.send_count ?? 1}
                      .initialDitto=${this._editSignal.repeat_count ?? 1}
                      .initialObservedRepeatCount=${this._editSignal
                          .observed_repeat_count ?? 0}
                      .hasTrigger=${this._triggerCountFor(this._editSignal) > 0}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${() => (this._editSignal = null)}
                  ></ir-signal-editor>`
                : ""}
            ${this._testDialog
                ? html`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${(e: CustomEvent) =>
                          (this._testEmitters = e.detail.value)}
                      @send=${this._sendTest}
                      @closed=${() => (this._testDialog = null)}
                  ></ir-test-emitter-dialog>`
                : ""}
        `;
    }

    static styles = [
        actionChipStyles,
        css`
            :host {
                display: block;
            }
            .loading,
            .no-match {
                text-align: center;
                color: var(--secondary-text-color);
                padding: 24px;
            }
            .error {
                color: var(--error-color, #db4437);
                padding: 8px 0;
            }

            /* Stats strip: the silver sheen lives here, as texture. */
            .stats {
                display: flex;
                align-items: center;
                gap: 26px;
                background: var(--secondary-background-color);
                border: 1px solid var(--divider-color);
                border-radius: 10px;
                padding: 12px 18px;
                margin-bottom: 14px;
                background-image: linear-gradient(
                    105deg,
                    transparent 42%,
                    rgba(144, 164, 174, 0.12) 50%,
                    transparent 58%
                );
            }
            .stat .v {
                font-size: 19px;
                font-weight: 600;
                color: var(--primary-text-color);
            }
            .stat .l {
                font-size: 11px;
                color: var(--secondary-text-color);
                letter-spacing: 0.4px;
                margin-top: 1px;
            }
            .stat .v.warn {
                color: #e65100;
            }
            .stats .updated {
                margin-left: auto;
                font-size: 11.5px;
                color: var(--secondary-text-color);
            }

            /* Toolbar */
            .toolbar {
                display: flex;
                gap: 8px;
                align-items: center;
                margin-bottom: 14px;
                flex-wrap: wrap;
            }
            .fchip {
                font-size: 12.5px;
                padding: 5px 13px;
                border-radius: 16px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                color: var(--secondary-text-color);
                font-family: inherit;
                cursor: pointer;
            }
            .fchip.on {
                background: #607d8b;
                border-color: #607d8b;
                color: #fff;
            }
            .fchip.warnc:not(.on) {
                color: #e65100;
                border-color: #ffcf9e;
            }
            .search {
                flex: 1 1 180px;
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-family: inherit;
                background: var(--card-background-color);
                color: var(--primary-text-color);
            }
            .search:focus {
                outline: none;
                border-color: #607d8b;
            }

            /* Rows */
            .rows {
                border: 1px solid var(--divider-color);
                border-radius: 10px;
                overflow: hidden;
            }
            .mrow {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 16px;
                border-bottom: 1px solid var(--divider-color);
                background: var(--card-background-color);
            }
            .mrow:last-child {
                border-bottom: none;
            }
            .mrow:hover {
                background: var(--secondary-background-color);
            }
            /* The silver bloom a send makes while you watch. */
            .mrow.bloom {
                animation: mirror-bloom 1.4s ease-out;
            }
            @keyframes mirror-bloom {
                0% {
                    box-shadow:
                        inset 3px 0 0 #90a4ae,
                        0 0 10px rgba(144, 164, 174, 0.55);
                }
                100% {
                    box-shadow:
                        inset 3px 0 0 rgba(144, 164, 174, 0),
                        0 0 0 rgba(144, 164, 174, 0);
                }
            }
            .mrow-main {
                min-width: 0;
            }
            .mrow-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
            }
            .mrow-title .name {
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .pill {
                font-size: 10px;
                letter-spacing: 0.4px;
                font-weight: 500;
                padding: 2px 7px;
                border-radius: 9px;
                background: rgba(33, 150, 243, 0.12);
                color: #1565c0;
                white-space: nowrap;
            }
            .pill.raw {
                background: rgba(230, 140, 60, 0.12);
                color: #b87333;
            }
            .mrow-sub {
                margin-top: 4px;
                font-size: 12px;
                color: var(--secondary-text-color);
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
            }
            .arrow {
                color: #b0bec5;
            }
            .heard {
                color: #2e7d32;
            }
            /* Neutral grey, not amber: one-way homes are normal. */
            .not-heard {
                color: #90a4ae;
            }
            .src-chip {
                font-size: 10.5px;
                padding: 1px 8px;
                border-radius: 8px;
                background: rgba(96, 125, 139, 0.12);
                color: #546e7a;
                white-space: nowrap;
            }
            .mrow-meta {
                margin-left: auto;
                display: flex;
                align-items: center;
                gap: 10px;
                white-space: nowrap;
            }
            .counts {
                font-size: 12px;
                color: var(--secondary-text-color);
            }
            .code-btn {
                background: none;
                border: none;
                cursor: pointer;
                color: var(--secondary-text-color);
                padding: 2px;
                display: inline-flex;
                align-items: center;
            }

            /* Empty state: the feature explaining itself. */
            .empty {
                text-align: center;
                padding: 44px 20px 52px;
            }
            .mirror-glyph {
                width: 44px;
                height: 44px;
                margin: 0 auto 14px;
                border-radius: 10px;
                border: 2.5px solid #607d8b;
                background: linear-gradient(
                    135deg,
                    #eceff1 30%,
                    #ffffff 45%,
                    #eceff1 60%
                );
                position: relative;
            }
            .mirror-glyph::after {
                content: "";
                position: absolute;
                top: 5px;
                left: 11px;
                width: 5px;
                height: 24px;
                background: rgba(255, 255, 255, 0.95);
                transform: rotate(18deg);
                border-radius: 3px;
            }
            .empty-title {
                font-size: 15px;
                font-weight: 500;
                color: var(--primary-text-color);
            }
            .empty-sub {
                font-size: 12.5px;
                color: var(--secondary-text-color);
                margin-top: 6px;
                max-width: 420px;
                margin-left: auto;
                margin-right: auto;
                line-height: 1.5;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-mirror": IrMirror;
    }
}
