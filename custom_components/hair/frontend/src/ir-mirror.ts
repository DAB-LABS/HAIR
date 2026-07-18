/**
 * The Mirror tab (v0.6.6) -- what your house transmits.
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
 * A log with a wipe rag: no dismiss, no reorder, no clear-all, but a
 * per-row Delete that clears the ledger entry -- the row returns on
 * the next send of the same identity, the same resurrection semantics
 * the Sniffer has, so removal cannot damage the audit (owner ruling,
 * v0.6.6 bench, reversing the earlier no-delete stance). Rows carry
 * the Sniffer's exact action chips (Assign / Test / Trigger / Delete
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
// Hand mirror (SVG Repo, owner-supplied images/mirror-makeup-svgrepo-com.svg),
// rotated 45 degrees to the tool-icon diagonal (head top-right, handle
// bottom-left, matching the clippers and tweezers) and scaled to a 24x24 box.
const ICON_MIRROR =
    "M 19.39,4.60 C 16.51,1.71 11.78,1.71 8.89,4.60 C 6.00,7.49 6.00,12.21 8.89,15.10 C 11.78,17.99 16.51,17.99 19.39,15.10 C 22.28,12.21 22.28,7.49 19.39,4.60 M 9.29,14.70 C 6.63,12.03 6.63,7.67 9.29,5.00 C 11.96,2.34 16.32,2.34 18.99,5.00 C 21.66,7.67 21.66,12.03 18.99,14.70 C 16.32,17.36 11.96,17.36 9.29,14.70 M 4.85,19.14 C 4.29,18.58 3.40,18.58 2.83,19.14 C 2.27,19.71 2.27,20.60 2.83,21.16 C 3.40,21.73 4.29,21.73 4.85,21.16 C 5.42,20.60 5.42,19.71 4.85,19.14 M 3.24,20.76 C 2.89,20.41 2.89,19.89 3.24,19.55 C 3.58,19.20 4.10,19.20 4.45,19.55 C 4.79,19.89 4.79,20.41 4.45,20.76 C 4.10,21.10 3.58,21.10 3.24,20.76 M 22.99,9.57 C 22.91,7.10 21.84,4.82 19.98,3.20 C 16.65,0.28 11.62,0.26 8.31,3.20 C 5.52,5.67 4.57,9.49 5.86,12.96 C 6.33,14.19 6.02,15.55 5.13,16.43 C 4.65,16.92 4.04,17.24 3.40,17.32 C 2.79,17.40 2.25,17.71 1.82,18.13 C 0.75,19.20 0.73,21.00 1.78,22.09 C 1.80,22.11 1.82,22.13 1.84,22.15 C 2.37,22.68 3.07,22.98 3.82,23.00 C 4.61,23.02 5.32,22.72 5.88,22.15 C 6.31,21.73 6.57,21.18 6.67,20.60 C 6.77,19.93 7.07,19.34 7.56,18.86 C 8.45,17.97 9.82,17.69 11.03,18.13 C 14.28,19.36 17.96,18.56 20.40,16.11 C 22.12,14.39 23.07,11.99 22.99,9.57 M 11.23,17.61 C 9.82,17.08 8.20,17.40 7.15,18.45 C 6.59,19.02 6.22,19.75 6.10,20.51 C 6.02,21.00 5.80,21.42 5.46,21.77 C 5.01,22.21 4.43,22.43 3.82,22.43 C 3.17,22.43 2.61,22.19 2.18,21.73 C 1.34,20.84 1.38,19.42 2.21,18.56 C 2.55,18.21 2.99,17.97 3.48,17.89 C 4.25,17.77 4.97,17.40 5.54,16.84 C 6.59,15.79 6.93,14.19 6.39,12.76 C 5.17,9.53 6.06,5.93 8.69,3.63 C 11.80,0.88 16.49,0.88 19.60,3.63 C 19.74,3.73 19.88,3.87 20.00,3.99 C 21.49,5.49 22.36,7.45 22.42,9.57 C 22.48,11.89 21.64,14.07 20.00,15.71 C 17.70,18.01 14.26,18.74 11.23,17.61 M 17.58,10.86 L 10.71,10.86 C 10.55,10.86 10.43,10.98 10.43,11.14 C 10.43,11.22 10.47,11.30 10.51,11.34 C 10.55,11.38 10.63,11.43 10.71,11.43 L 17.58,11.43 C 17.74,11.43 17.86,11.30 17.86,11.14 C 17.86,10.98 17.72,10.88 17.58,10.86 M 17.88,8.54 C 17.88,8.38 17.76,8.25 17.60,8.25 L 10.73,8.25 C 10.57,8.25 10.45,8.38 10.45,8.54 C 10.45,8.62 10.49,8.70 10.53,8.74 C 10.57,8.78 10.65,8.82 10.73,8.82 L 17.60,8.82 C 17.72,8.82 17.86,8.68 17.88,8.54";
// mdi:repeat -- whole-frame send-count indicator (orange), same anatomy as
// the command rows'. A Mirror row can carry TX knobs (someone edits a row
// here and then assigns it), so the row shows them the same way.
const ICON_REPEAT =
    "M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z";
// mdi:dots-horizontal -- NEC ditto-count indicator (blue).
const ICON_DITTO =
    "M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z";

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
    @state() private _deleteSignal: UnknownSignal | null = null;
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
        // "Manual test send[: <alias>]" is the current label for a
        // catalog-tab Test press; "Catalog test[: <alias>]" is its
        // pre-rename form, still present on rows persisted before the
        // v0.6.6 bench rename. Either way the chip is the provenance and
        // the title falls through to the identity chain below. Chips
        // render Title Case per the owner's bench ruling.
        const testPrefix = ["Manual test send", "Catalog test"].find((p) =>
            label.startsWith(p),
        );
        if (label === "automation send") {
            chip = "Automation Send";
        } else if (label === "integration send") {
            chip = "Integration Send";
        } else if (testPrefix) {
            chip = "Manual Test Send";
            labelTitle =
                label.slice(testPrefix.length).replace(/^:\s*/, "").trim() ||
                null;
        } else if (label) {
            chip = "HAIR Device";
            labelTitle = label;
        } else {
            chip = "Send";
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

    /** Delete clears the ledger entry; the row returns on the next send
     * of the same identity (uniform with the Sniffer's resurrection
     * semantics -- delete is "clear this entry", never "never again").
     * Added on the v0.6.6 bench, reversing the earlier no-delete ruling:
     * stale test entries needed a way out, and resurrection makes
     * removal harmless to the audit. */
    private async _confirmDeleteSignal(): Promise<void> {
        const sig = this._deleteSignal;
        this._deleteSignal = null;
        if (!sig || !this._device) return;
        try {
            await this.api.deleteSignal(this._device.id, sig.id);
            await this._refreshDevice();
        } catch (err) {
            this._error = `Delete failed: ${(err as Error).message}`;
        }
    }

    // -----------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------

    render() {
        const rows = this._rows();
        const filtered = this._filteredRows(rows);

        return html`
            <div class="tab-head">
                <span class="title">
                    <ha-svg-icon .path=${ICON_MIRROR}></ha-svg-icon>
                    HAIR Mirror
                    ${!this._loading
                        ? html`<span class="count"
                              >(${rows.length}
                              ${rows.length === 1 ? "signal" : "signals"})</span
                          >`
                        : ""}
                </span>
            </div>
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
                        ${(sig.send_count ?? 1) > 1
                            ? html`<span
                                  class="repeat-indicator"
                                  title="Sends this signal ${sig.send_count} times"
                                  ><ha-svg-icon
                                      .path=${ICON_REPEAT}
                                  ></ha-svg-icon
                                  >${sig.send_count}</span
                              >`
                            : ""}
                        ${(sig.repeat_count ?? 1) > 1 && sig.decoded_protocol
                            ? html`<span
                                  class="ditto-indicator"
                                  title="Appends ${sig.repeat_count} NEC dittos"
                                  ><ha-svg-icon
                                      .path=${ICON_DITTO}
                                  ></ha-svg-icon
                                  >${sig.repeat_count}</span
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
                    <button
                        class="action-btn delete-btn"
                        title="Clear this entry (it returns on the next send)"
                        @click=${(e: Event) => {
                            e.stopPropagation();
                            this._deleteSignal = sig;
                        }}
                    >Delete</button>
                </div>
            </div>
        `;
    }

    private _renderEmpty() {
        return html`
            <div class="empty">
                <ha-svg-icon
                    class="empty-icon"
                    .path=${ICON_MIRROR}
                ></ha-svg-icon>
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
            ${this._deleteSignal
                ? html`<ir-confirm-dialog
                      title="Clear Mirror Entry"
                      message="Remove this entry from the Mirror? It will come back the next time this signal is sent."
                      confirmLabel="Delete"
                      .destructive=${true}
                      @confirmed=${this._confirmDeleteSignal}
                      @closed=${() => (this._deleteSignal = null)}
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

            /* Tab header, same anatomy as the Sniffer/Clipper/Plucker
               titles; the mirror icon wears the tab's silver. */
            .tab-head {
                display: flex;
                align-items: center;
                margin-bottom: 12px;
            }
            .title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 1.1rem;
                font-weight: 500;
                color: var(--primary-text-color);
            }
            .title ha-svg-icon {
                --mdc-icon-size: 24px;
                color: #607d8b;
            }
            .title .count {
                font-size: 0.85rem;
                font-weight: 400;
                color: var(--secondary-text-color);
            }
            .error {
                color: var(--error-color, #db4437);
                padding: 8px 0;
            }

            /* Stats strip: the silver sheen lives here, as texture.
               Deliberately slim (owner bench note: less air above and
               below) -- values and labels sit on one line per stat. */
            .stats {
                display: flex;
                align-items: baseline;
                gap: 22px;
                background: var(--secondary-background-color);
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                padding: 6px 14px;
                margin-bottom: 12px;
                background-image: linear-gradient(
                    105deg,
                    transparent 42%,
                    rgba(144, 164, 174, 0.12) 50%,
                    transparent 58%
                );
            }
            .stat {
                display: flex;
                align-items: baseline;
                gap: 5px;
            }
            .stat .v {
                font-size: 15px;
                font-weight: 600;
                color: var(--primary-text-color);
            }
            .stat .l {
                font-size: 10.5px;
                color: var(--secondary-text-color);
                letter-spacing: 0.4px;
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
            /* TX-knob indicators, same anatomy as the command rows'. */
            .repeat-indicator,
            .ditto-indicator {
                display: inline-flex;
                align-items: center;
                gap: 1px;
                font-size: 9px;
                font-weight: 600;
                opacity: 0.85;
            }
            .repeat-indicator {
                color: var(--warning-color, #ff9800);
            }
            .ditto-indicator {
                color: var(--primary-color);
            }
            .repeat-indicator ha-svg-icon,
            .ditto-indicator ha-svg-icon {
                --mdc-icon-size: 10px;
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
            .empty-icon {
                --mdc-icon-size: 44px;
                color: #607d8b;
                margin-bottom: 12px;
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
