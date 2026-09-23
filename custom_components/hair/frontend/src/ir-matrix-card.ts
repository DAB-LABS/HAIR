/**
 * The STATE MATRIX card (signpost 4, Track M, coding-plan decision 7).
 *
 * One card, two sides of the same lattice. The DEVICE page has always
 * used it to pick a state and transmit it; the REMOTE page uses it to
 * watch states arrive. Both draw the same chips, the same temperature
 * grid, and the same action bar, so they live here rather than as two
 * near-copies drifting apart -- which is exactly what happened to the
 * popover CSS before ir-popover-styles.ts extracted it.
 *
 * The card owns the BROWSE state (which mode/fan/swing/temperature the
 * user is looking at) and nothing else. It does not fetch its own
 * lattice, does not know what a device or a remote is, and never
 * transmits: it asks for cells through ``cellsLoader`` and reports what
 * the user did through three events, leaving the caller to decide what
 * that means.
 *
 *   matrix-send          send mode: transmit this state now
 *   matrix-save-command  send mode: keep it as a device command row
 *   matrix-save-trigger  hear mode: mint a trigger for it
 *
 * Every one carries the same detail shape -- the resolved coordinates
 * plus the display name -- so a consumer never has to reach back into
 * the card for what was picked.
 *
 * Deliberately NO ``api`` handle, though the plan's prop list floated
 * one: ``cellsLoader`` is the only backend call the card makes, and the
 * device and remote endpoints differ, so the callback IS the seam. A
 * second door would only invite the card to start fetching on its own.
 *
 * THINNING (thinning-plan.md 7) follows the same rule: ``thinSaver`` is
 * a callback the device page hands in, and the card never learns what
 * a device is. With it set, send mode grows the house pencil, and the
 * card becomes the editor in place: the browse rows give way to one
 * group per lattice and one line per mode, every value a keep / remove
 * toggle, and the actions row gives way to the save strip. The draft
 * and its rules live in ``matrix-thin.ts`` so a test can run them.
 */
import { LitElement, html, css, nothing } from "lit";
import { actionChipStyles } from "./ir-action-chip-styles";
import { customElement, property, state } from "./decorators.js";
import { t, tp } from "./localize.js";
import { BloomTracker, bloomStyles } from "./ir-bloom-styles.js";
import {
    editButtonStyles,
    exitToEntityButtonStyles,
    renderEditBtn,
    renderExitToEntityBtn,
} from "./ir-icons.js";
import type {
    LastHeard,
    MatrixCellCoord,
    MatrixCells,
    MatrixLattice,
    MatrixSummary,
    MatrixThinResult,
    MatrixThinShape,
} from "./types.js";
import { heardInLattice, latticeView } from "./matrix-lattice.js";
import type { LatticeRef, LatticeView } from "./matrix-lattice.js";
import {
    defaultOpen,
    depthOf,
    latticeKept,
    latticeTotal,
    modeKept,
    removesAnything,
    startDraft,
    thinPayload,
    toggleLattice,
    toggleMode,
    toggleOn,
    toggleValue,
    totals,
} from "./matrix-thin.js";
import type {
    DraftLattice,
    DraftMode,
    OpenState,
    ThinAxis,
    ThinDraft,
} from "./matrix-thin.js";
import { displayTemp, installUnit } from "./temperature.js";

/** What a card event reports: the resolved coordinates plus the name.
 * ``power`` wins when it is set -- a power press is a sibling of the
 * cell branch, not a point inside it (matrix-power-row.md item 1). */
export interface MatrixCardPick {
    power: "on" | "off" | null;
    mode: string | null;
    fan: string | null;
    swing: string | null;
    temp: number | null;
    name: string;
    /** Which lattice the coordinates belong to, both null for the main
     * one. They travel together or not at all, which is what the four
     * websocket doors validate. Coordinates alone cannot say: every
     * coordinate the lattices share carries a DIFFERENT code. */
    axis?: string | null;
    lattice?: string | null;
}

@customElement("ir-matrix-card")
export class IrMatrixCard extends LitElement {
    @property({ attribute: false }) hass: any;
    /** "send" = the device page's transmitter. "hear" = the remote
     * page's listener (Track M): no SEND, and the action bar mints a
     * trigger instead of a command. */
    @property() mode: "send" | "hear" = "send";
    @property({ attribute: false }) summary!: MatrixSummary;
    /** Fetches the lattice. Called once per ``cellsKey``. */
    @property({ attribute: false }) cellsLoader:
        | (() => Promise<MatrixCells>)
        | null = null;
    /** Identity of the thing the lattice belongs to (a device or remote
     * id). A change reloads; nothing else does, so a parent re-render
     * costs no traffic. */
    @property() cellsKey: string | null = null;
    /** Send mode: the climate entity's current cell, which wears the
     * cold ring. */
    @property() currentName: string | null = null;
    /** Hear mode: the last state actually heard off the handset.
     * Persisted on the remote, so it is already filled on the first
     * render after a reload -- the rest ring comes back with it. */
    @property({ attribute: false }) heard: LastHeard | null = null;
    /** Hear mode: the remote's HA device page, for the note's glyph. */
    @property() haDeviceId: string | null = null;
    @property({ type: Boolean }) busy = false;
    /** Send mode: saves a thinned shape (``hair/devices/matrix-thin``)
     * and resolves with the door's answer. Absent, there is no pencil:
     * the remote page never passes one, and hear mode never draws one
     * even if it did. */
    @property({ attribute: false }) thinSaver:
        | ((shape: MatrixThinShape) => Promise<MatrixThinResult>)
        | null = null;

    // THE THINNING EDITOR (thinning-plan.md 7). ``_draft`` is the whole
    // desired shape, held here and nowhere else until SAVE; Cancel, the
    // pencil pressed again, and a different device all discard it.
    @state() private _editing = false;
    @state() private _draft: ThinDraft | null = null;
    @state() private _open: OpenState = {};
    @state() private _offNote = false;
    private _offNoteTimer: number | undefined;
    @state() private _thinBusy = false;

    @state() private _cells: MatrixCells | null = null;
    private _cellsFor: string | null = null;
    @state() private _selMode: string | null = null;
    @state() private _selFan: string | null = null;
    @state() private _selSwing: string | null = null;
    @state() private _selTemp: number | null = null;
    // Power row (matrix-power-row.md item 1): a power press is a
    // sibling selection to the cell branch, not a branch itself --
    // picking a power chip clears the cell dimensions and vice versa,
    // so only one of the two can ever be "the thing Send would send".
    @state() private _selPower: "on" | "off" | null = null;
    // WHICH LATTICE IS BEING BROWSED, by its key; null is the main one
    // (extras-in-the-matrix-card.md 6). A device with no extras never
    // leaves null and never draws the chooser, so its card is what it
    // always was, chip for chip.
    @state() private _selLattice: string | null = null;
    // HEAR MODE keeps two facts apart that send mode never had to.
    // BROWSED is what the user clicked; HEARD is what came off the
    // handset. The card always has a display branch (something has to
    // be drawn), but until the user actually clicks, that branch is a
    // default rather than a selection: nothing fills blue and the
    // action bar has nothing to mint. Hearing never changes what is
    // browsed, and browsing never changes what was heard.
    @state() private _browsed = false;
    // Set once a Mode/Fan/Swing chip is clicked. A temperature click
    // does not count: it moves within a branch rather than leaving it,
    // and the temperature ring's scope is the branch (handoff, the
    // resolved rest-rim rule).
    @state() private _browsedBranch = false;
    @state() private _bloom = false;
    private _bloomTracker = new BloomTracker();
    private _heardAt: string | null = null;
    // A reload is not a hearing. The stored heard state comes back
    // already filled (handoff, persistence addendum), so the first
    // pass records it and rests -- only a frame that arrives while
    // the card is on screen blooms.
    private _heardSeen = false;

    willUpdate(): void {
        if (this.cellsLoader && this._cellsFor !== this.cellsKey) {
            this._cellsFor = this.cellsKey;
            // A different device: an open edit is discarded without
            // asking (brief 8), and the last save's line belongs to the
            // device it was about.
            this._editing = false;
            this._draft = null;
            void this._loadCells();
        }
    }

    private async _loadCells(): Promise<void> {
        this._cells = null;
        try {
            const cells = await this.cellsLoader!();
            this._cells = cells;
            // A lattice thinned away under the selection is gone: fall
            // back to the main one rather than browse a stale key.
            if (
                this._selLattice !== null &&
                !(cells.lattices ?? []).some((l) => l.key === this._selLattice)
            ) {
                this._selLattice = null;
            }
            this._seedBranch();
        } catch {
            // Summary-only card; the backend already logged why.
            this._cells = null;
        }
    }

    /** The extras lattices this matrix carries, never undefined. */
    private _lattices(): MatrixLattice[] {
        return this._cells?.lattices ?? [];
    }

    /** The lattice being browsed, as cells plus its own vocabulary.
     *
     * ONE ACCESSOR, so every browsing helper below reads the selected
     * lattice rather than the matrix. */
    private _view(): LatticeView {
        return latticeView(this._cells!, this._selLattice);
    }

    /** The lattice on screen as a ref: both fields for an extra,
     * nothing for the main one. What the heard state is matched
     * against before anything is ringed. */
    private _selectedRef(): LatticeRef {
        if (this._selLattice === null) return {};
        const extra = this._lattices().find((l) => l.key === this._selLattice);
        return extra ? { axis: extra.axis, lattice: extra.key } : {};
    }

    /** Is the heard state in the lattice on screen? LISTENING-MODE
     * MARKING: without this, an Eco press lit the main lattice's tile
     * at the same coordinates, which is a different code. */
    private _heardHere(): boolean {
        return heardInLattice(this.heard, this._selectedRef());
    }

    /** Fan values the mode branch actually holds, in vocabulary order. */
    private _fansFor(mode: string): string[] {
        const view = this._view();
        const seen = new Set<string>();
        for (const c of view.cells) {
            if (c.m === mode && c.f !== undefined) seen.add(c.f);
        }
        return view.fan_modes.filter((f) => seen.has(f));
    }

    /** Swing values under (mode, fan), in vocabulary order. */
    private _swingsFor(mode: string, fan: string | null): string[] {
        const view = this._view();
        const seen = new Set<string>();
        for (const c of view.cells) {
            if (
                c.m === mode &&
                (c.f ?? null) === fan &&
                c.s !== undefined
            ) {
                seen.add(c.s);
            }
        }
        return view.swing_modes.filter((s) => seen.has(s));
    }

    /** Every cell of the selected branch (exact dimension match --
     * absent dimensions pair only with null, mirroring exact_cell). */
    private _branchCells(
        mode: string,
        fan: string | null,
        swing: string | null,
    ): MatrixCellCoord[] {
        return this._view().cells.filter(
            (c) =>
                c.m === mode &&
                (c.f ?? null) === fan &&
                (c.s ?? null) === swing,
        );
    }

    /** Move the selection, re-resolving the deeper dimensions so the
     * result is always a branch the matrix actually has: a fan/swing
     * that vanished with the mode change falls to the branch's first,
     * a temperature falls to the nearest available (middle when the
     * branch is fresh -- the entity's resolve_cell default). */
    private _applyBranch(
        mode: string,
        fan: string | null,
        swing: string | null,
        temp: number | null,
    ): void {
        const fans = this._fansFor(mode);
        const useFan =
            fan !== null && fans.includes(fan) ? fan : (fans[0] ?? null);
        const swings = this._swingsFor(mode, useFan);
        const useSwing =
            swing !== null && swings.includes(swing)
                ? swing
                : (swings[0] ?? null);
        const temps = this._branchCells(mode, useFan, useSwing)
            .filter((c) => c.t !== undefined)
            .map((c) => c.t!)
            .sort((a, b) => a - b);
        let useTemp: number | null = null;
        if (temps.length > 0) {
            if (temp === null) {
                useTemp = temps[Math.floor(temps.length / 2)];
            } else if (temps.includes(temp)) {
                useTemp = temp;
            } else {
                useTemp = temps.reduce((best, x) =>
                    Math.abs(x - temp) < Math.abs(best - temp) ? x : best,
                );
            }
        }
        this._selMode = mode;
        this._selFan = useFan;
        this._selSwing = useSwing;
        this._selTemp = useTemp;
        this._selPower = null;
    }

    /** A user picked a temperature tile (or the bare branch tile).
     * Browsing starts here: from now on the blue fill and the action
     * bar mean something the person chose. */
    private _select(
        mode: string,
        fan: string | null,
        swing: string | null,
        temp: number | null,
    ): void {
        this._applyBranch(mode, fan, swing, temp);
        this._browsed = true;
    }

    /** A user picked a Mode / Fan / Swing chip. Same as _select plus
     * the branch flag: this is the click that can take the view off
     * the heard branch, which is what un-rings the temperature tile. */
    private _selectDim(
        mode: string,
        fan: string | null,
        swing: string | null,
        temp: number | null,
    ): void {
        this._applyBranch(mode, fan, swing, temp);
        this._browsed = true;
        this._browsedBranch = true;
    }

    /** The branch to DRAW before anyone has clicked: the heard one
     * when there is a heard one, else the file's first mode. Nothing
     * is marked selected -- "not browsed yet" is a real state, and it
     * is the one a freshly loaded remote is in. */
    private _seedBranch(): void {
        const mc = this._cells;
        if (!mc) return;
        const view = this._view();
        if (view.modes.length === 0) return;
        const h = this.mode === "hear" ? this.heard : null;
        if (h && h.power === null && h.mode && this._heardHere()) {
            this._applyBranch(h.mode, h.fan, h.swing, h.temp);
        } else {
            this._applyBranch(view.modes[0], null, null, null);
        }
    }

    /** Pick a lattice. Re-seeds the branch from THAT lattice's
     * vocabulary, because the coordinates standing in the old one
     * usually do not exist in the new: an extra is typically narrower.
     * Clears the power selection for the same reason the chooser hides
     * the power row while an extra is up -- off and on belong to the
     * matrix, never to a lattice. */
    private _selectLattice(key: string | null): void {
        if (this._selLattice === key) return;
        this._selLattice = key;
        this._selPower = null;
        this._seedBranch();
        this._browsed = true;
        this._browsedBranch = true;
    }

    /** Is the browsed branch the heard one? "Not browsed yet" counts
     * as yes: the card shows what just happened rather than an
     * arbitrary starting point, so a fresh frame rings its tile
     * without the user having to click through to it first (handoff,
     * the correction the mockup needed on its first pass). */
    private _onHeardBranch(): boolean {
        const h = this.heard;
        if (!h || h.power !== null) return false;
        if (!this._heardHere()) return false;
        if (!this._browsedBranch) return true;
        return (
            this._selMode === h.mode &&
            (this._selFan ?? null) === (h.fan ?? null) &&
            (this._selSwing ?? null) === (h.swing ?? null)
        );
    }

    /** Does a chip matching the current branch read as SELECTED?
     *
     * Punch list item 16. Hear mode draws a branch before anyone has
     * clicked -- something has to be on screen -- but that branch is a
     * default, not a selection, and the handoff is explicit that
     * nothing fills blue until a real click. The temperature tiles
     * already knew this (they gate on ``_browsed``); the Mode / Fan /
     * Swing chips did not, so a never-touched card came up reading as
     * though the user had picked its first mode.
     *
     * Send mode is UNCHANGED: the device card has always drawn its
     * seeded branch filled, its Set-state line is armed from the first
     * render, and there is no browsed-versus-not distinction there to
     * express.
     */
    private get _fills(): boolean {
        return this.mode !== "hear" || this._browsed;
    }

    /** A new frame arrived: bloom every dimension value of the heard
     * cell at once, and -- if nobody has browsed away -- move the
     * drawn branch onto it so the rest ring lands somewhere visible. */
    updated(): void {
        const at = this.heard?.at ?? null;
        if (at === this._heardAt && this._heardSeen) return;
        const first = !this._heardSeen;
        this._heardSeen = true;
        this._heardAt = at;
        if (first || at === null || this.mode !== "hear") return;
        if (!this._browsed) this._seedBranch();
        this._bloomTracker.trigger(
            "heard",
            () => {
                this._bloom = true;
            },
            () => {
                this._bloom = false;
            },
        );
    }

    /** Pick a power chip (Off, or On when the matrix declares one).
     * matrix-power-row.md item 1: "clicking a power chip clears the
     * cell selection." That's true of what Send/Save read (_selPower
     * wins, checked first everywhere) and of what's drawn (Mode/Fan/
     * Swing/grid chips stop rendering "on" once _selPower is set --
     * see the `this._selPower === null ? ... : null` guards at their
     * call sites in render/_renderGrid). What this method deliberately
     * does NOT do is null out _selMode/_selFan/_selSwing/_selTemp
     * themselves: the Mode/Fan/Swing/Grid block is gated on
     * `_selMode !== null`, and that block is where the Power row
     * itself lives, so clearing _selMode would erase the very chips
     * the user needs to switch back to cell-picking. */
    private _selectPower(power: "on" | "off"): void {
        this._selPower = power;
    }

    /** The exact cell the selection points at, or null mid-load. */
    private _selectedCell(): MatrixCellCoord | null {
        if (!this._cells || this._selMode === null) return null;
        return (
            this._branchCells(
                this._selMode,
                this._selFan,
                this._selSwing,
            ).find((c) => (c.t ?? null) === this._selTemp) ?? null
        );
    }

    /** One matrix temperature as display text, converted to the
     * viewer's install unit when it differs from the matrix's native
     * unit (unit ruling 2026-07-29). Display-only: coordinates and
     * the absent-tile walk stay native. */
    private _displayTemp(temp: number): string {
        const mc = this._cells;
        return displayTemp(
            temp,
            mc?.unit ?? this.summary?.unit ?? "C",
            installUnit(this.hass),
            mc?.precision ?? 1,
        );
    }

    /** The CC4 display grammar, client-side: mode bare, fan and swing
     * labeled, temperature a bare number last. Must mirror
     * wig_climate.cell_display_name byte-for-byte -- the current-tile
     * glow compares this against the entity's matrix_cell attribute,
     * which the backend also converts to the install's unit at send
     * time, so the temperature part converts here too. */
    private _cellName(c: MatrixCellCoord): string {
        const parts = [c.m];
        if (c.f !== undefined) parts.push(`fan: ${c.f}`);
        if (c.s !== undefined) parts.push(`swing: ${c.s}`);
        if (c.t !== undefined) parts.push(this._displayTemp(c.t));
        const name = parts.join(" / ");
        // The lattice in parentheses FIRST, then the grammar above
        // unchanged (owner ruling 2026-09-19). Mirrors
        // wig_climate.cell_display_name, which the Set-state preview
        // and the saved command's name both come from, and which
        // add_command keys on: two lattices saving one coordinate must
        // mint two commands, not one eating the other.
        return this._selLattice !== null
            ? `(${this._selLattice}) ${name}`
            : name;
    }

    /** What the action bar is aimed at right now, or null. */
    private _pick(): MatrixCardPick | null {
        if (this._selPower !== null) {
            return {
                power: this._selPower,
                mode: null,
                fan: null,
                swing: null,
                temp: null,
                name:
                    this._selPower === "on"
                        ? t("fitting.row_on")
                        : t("fitting.row_off"),
            };
        }
        const cell = this._selectedCell();
        if (!cell) return null;
        const extra =
            this._selLattice === null
                ? null
                : (this._lattices().find(
                      (l) => l.key === this._selLattice,
                  ) ?? null);
        return {
            power: null,
            mode: cell.m,
            fan: cell.f ?? null,
            swing: cell.s ?? null,
            temp: cell.t ?? null,
            name: this._cellName(cell),
            axis: extra?.axis ?? null,
            lattice: extra?.key ?? null,
        };
    }

    private _emit(name: string): void {
        const pick = this._pick();
        if (!pick) return;
        this.dispatchEvent(
            new CustomEvent<MatrixCardPick>(name, {
                detail: pick,
                bubbles: true,
                composed: true,
            }),
        );
    }

    /** The lattice chooser, ABOVE the dimension browser
     * (extras-in-the-matrix-card.md 6).
     *
     * ABSENT, NOT EMPTY, when the matrix carries no extras: a device
     * that has never seen a hair-wig/4 wig renders exactly the card it
     * rendered before this existed, with no extra row and no gap where
     * one would be. The main lattice leads under its existing name,
     * then each extra by its own word, verbatim from the file. */
    private _renderLatticeRow() {
        const lattices = this._lattices();
        if (lattices.length === 0) return nothing;
        const options: Array<{ value: string | null; label: string }> = [
            { value: null, label: t("devices.matrix_lattice_main") },
            ...lattices.map((l) => ({ value: l.key, label: l.key })),
        ];
        return html`
            <div class="mx-dim-row">
                <span class="mx-dim-label"
                    >${t("devices.matrix_dim_lattice")}</span
                >
                <span class="mx-chips">
                    ${options.map((o) => {
                        return html`<button
                            class="mx-chip ${this._selLattice === o.value
                                ? "on"
                                : ""}"
                            @click=${() => this._selectLattice(o.value)}
                        >
                            ${o.label}
                        </button>`;
                    })}
                </span>
            </div>
        `;
    }

    /** The Power row (matrix-power-row.md item 1): Off always, On only
     * when the matrix declares an explicit wake code (has_on). Kept
     * separate from _renderDimRow rather than reusing it, since the
     * internal values ("on"/"off") differ from their displayed labels
     * (t("fitting.row_on")/t("fitting.row_off")). */
    private _renderPowerRow(mc: MatrixCells) {
        const options: Array<{ value: "on" | "off"; label: string }> = [
            { value: "off", label: t("fitting.row_off") },
        ];
        if (mc.has_on) {
            options.push({ value: "on", label: t("fitting.row_on") });
        }
        return html`
            <div class="mx-dim-row">
                <span class="mx-dim-label"
                    >${t("devices.matrix_dim_power")}</span
                >
                <span class="mx-chips">
                    ${options.map((o) => {
                        const rest = this.heard?.power === o.value;
                        return html`<button
                            class="mx-chip ${o.value === this._selPower
                                ? "on"
                                : ""} ${rest ? "rest" : ""} ${rest &&
                            this._bloom
                                ? "bloom"
                                : ""}"
                            @click=${() => this._selectPower(o.value)}
                        >
                            ${o.label}
                        </button>`;
                    })}
                </span>
            </div>
        `;
    }

    /** One dimension chip row (Mode / Fan / Swing). */
    private _renderDimRow(
        label: string,
        values: string[],
        selected: string | null,
        pick: (value: string) => void,
        /** The heard value on this dimension, or null. Mode / Fan /
         * Swing rings are DIMENSION-LEVEL and unconditional: there is
         * only one of each row, so the heard branch's chip stays gold
         * whatever is browsed (handoff, resolved rest-rim rule). */
        heardValue: string | null = null,
    ) {
        return html`
            <div class="mx-dim-row">
                <span class="mx-dim-label">${label}</span>
                <span class="mx-chips">
                    ${values.map((v) => {
                        const rest = heardValue !== null && v === heardValue;
                        return html`<button
                            class="mx-chip ${v === selected && this._fills
                                ? "on"
                                : ""} ${rest ? "rest" : ""} ${rest &&
                            this._bloom
                                ? "bloom"
                                : ""}"
                            @click=${() => pick(v)}
                        >
                            ${v}
                        </button>`;
                    })}
                </span>
            </div>
        `;
    }

    /** The temperature tiles of the selected branch: present tiles
     * show the number, absent positions (branch min to max stepping
     * precision) render dashed and inert, the selected tile fills
     * cold blue, and the tile matching the entity's current cell
     * wears the cold glow ring. Depth-limited branches (no
     * temperature dimension) render one bare tile for the branch. */
    private _renderGrid(currentName: string | null) {
        const mode = this._selMode!;
        const branch = this._branchCells(
            mode,
            this._selFan,
            this._selSwing,
        );
        const byTemp = new Map<number, MatrixCellCoord>();
        for (const c of branch) {
            if (c.t !== undefined) byTemp.set(c.t, c);
        }
        const temps = [...byTemp.keys()].sort((a, b) => a - b);
        if (temps.length === 0) {
            const bare = branch.find((c) => c.t === undefined) ?? null;
            if (!bare) return nothing;
            const isCurrent =
                currentName !== null &&
                this._cellName(bare) === currentName;
            const isSel = this._selPower === null && this._browsed;
            const rest = this._onHeardBranch() && this.heard!.temp === null;
            return html`<div class="mx-grid">
                <button
                    class="mx-tile ${isSel ? "sel" : ""} ${isCurrent
                        ? "cur"
                        : ""} ${rest ? "rest" : ""} ${rest && this._bloom
                        ? "bloom"
                        : ""}"
                    @click=${() =>
                        this._select(
                            mode,
                            this._selFan,
                            this._selSwing,
                            null,
                        )}
                >
                    ${mode}
                </button>
            </div>`;
        }
        const step =
            this._cells!.precision > 0 ? this._cells!.precision : 1;
        const positions: number[] = [];
        for (
            let x = temps[0];
            x <= temps[temps.length - 1] + step / 2;
            x += step
        ) {
            // Two-decimal rounding keeps 0.5-precision walks exact.
            positions.push(Math.round(x * 100) / 100);
        }
        return html`<div class="mx-grid">
            ${positions.map((pos) => {
                const cell = byTemp.get(pos);
                if (!cell) {
                    return html`<button
                        class="mx-tile absent"
                        disabled
                        title=${t("devices.matrix_absent")}
                    >
                        ${this._displayTemp(pos)}
                    </button>`;
                }
                const isCurrent =
                    currentName !== null &&
                    this._cellName(cell) === currentName;
                // The temperature ring is BRANCH-SCOPED: the same
                // tile position is a different command under a
                // different Mode/Fan/Swing, so ringing it under a
                // mismatched browse would misattribute the heard
                // state to the wrong command.
                const rest =
                    this._onHeardBranch() && this.heard!.temp === pos;
                return html`<button
                    class="mx-tile ${
                        this._selPower === null &&
                        this._browsed &&
                        pos === this._selTemp
                            ? "sel"
                            : ""
                    } ${isCurrent ? "cur" : ""} ${rest ? "rest" : ""} ${
                        rest && this._bloom ? "bloom" : ""
                    }"
                    @click=${() =>
                        this._select(
                            mode,
                            this._selFan,
                            this._selSwing,
                            pos,
                        )}
                >
                    ${this._displayTemp(pos)}
                </button>`;
            })}
        </div>`;
    }

    render() {
        const m = this.summary;
        if (!m) return nothing;
        const current = this.currentName;
        const mc = this._cells;
        // Summary range: converted to the viewer's unit with the unit
        // letter as suffix ("61 to 86 F"); when converted, the file's
        // native range rides in a title tooltip (chosen over parens:
        // the one-line summary is already five facts long). Precision
        // comes from the loaded lattice when available; summary-only
        // renders fall back to whole degrees, which corpus bounds are.
        const viewUnit = installUnit(this.hass);
        const converted = viewUnit !== m.unit;
        const rangeTitle = converted
            ? t("devices.matrix_native_range", {
                  min: String(m.min_temp),
                  max: String(m.max_temp),
                  unit: m.unit,
              })
            : "";
        const summaryText = t("devices.matrix_summary", {
            cells: String(m.cells),
            modes: String(m.modes.length),
            fans: String(m.fan_modes.length),
            min: displayTemp(
                m.min_temp,
                m.unit,
                viewUnit,
                mc?.precision ?? 1,
            ),
            max: displayTemp(
                m.max_temp,
                m.unit,
                viewUnit,
                mc?.precision ?? 1,
            ),
            unit: viewUnit,
        });
        // WHAT A TRIM COST, as the summary line's last clause (owner
        // ruling 2026-09-22): same dot, same font, same grey as the
        // rest of the line, and absent entirely on a matrix nobody has
        // trimmed. "from" is the size before the first trim, so a
        // matrix trimmed twice still reads from its original size.
        const trimmedText = m.trimmed
            ? t("devices.matrix_trimmed", {
                  from: String(m.trimmed.from),
                  to: String(m.trimmed.to),
              })
            : "";
        const hear = this.mode === "hear";
        const h = this.heard;
        const selected = this._selectedCell();
        const fans =
            mc && this._selMode !== null
                ? this._fansFor(this._selMode)
                : [];
        const swings =
            mc && this._selMode !== null
                ? this._swingsFor(this._selMode, this._selFan)
                : [];
        // Send mode arms as soon as the lattice resolves a cell, the
        // way it always has. Hear mode arms only on a real click: a
        // never-heard, never-browsed remote has nothing to mint yet,
        // and says so instead of offering a default nobody picked.
        const armed = hear
            ? this._browsed && !!(selected || this._selPower)
            : !!(selected || this._selPower);
        // The heard state rings chips only in its own lattice.
        const heardHere = !!h && h.power === null && this._heardHere();
        const editing = this._editing && this._draft !== null;
        // The pencil: send mode, a readable lattice, and a page that
        // knows how to save. Never in hear mode (brief 2).
        const canThin = !hear && !!mc && this.thinSaver !== null;
        return html`
            <div class="matrix-card ${editing ? "editing" : ""}">
                <div class="mx-head">
                    <span class="mx-title">${t("devices.matrix_title")}</span>
                    <span class="mx-summary" title=${rangeTitle}>
                        ${summaryText}${trimmedText}
                    </span>
                    ${canThin
                        ? html`<span class="mx-head-spacer"></span>
                              <span class="thin-pencil ${editing ? "on" : ""}"
                                  >${renderEditBtn(
                                      () => this._togglePencil(),
                                      t("devices.thin_pencil"),
                                      this.busy || this._thinBusy,
                                  )}</span
                              >`
                        : nothing}
                </div>
                ${editing
                    ? this._renderEditor(mc!)
                    : this._renderBrowse(mc, hear, h, heardHere, current,
                          fans, swings, armed)}
            </div>
        `;
    }

    /** The browse card, exactly as it has always been drawn. Lifted
     * out of render() whole so edit mode can swap it for the editor
     * without a second copy; the only change inside is that a heard
     * state rings its chips in its own lattice only. */
    private _renderBrowse(
        mc: MatrixCells | null,
        hear: boolean,
        h: LastHeard | null,
        heardHere: boolean,
        current: string | null,
        fans: string[],
        swings: string[],
        armed: boolean,
    ) {
        return html`
                ${hear
                    ? html`
                          <div class="matrix-current">
                              ${h
                                  ? t("devices.matrix_last_heard", {
                                        cell: h.cell_name,
                                    })
                                  : t("devices.matrix_never_heard")}
                          </div>
                          <div class="mx-note">
                              ${t("devices.matrix_state_note")}
                              ${this.haDeviceId
                                  ? renderExitToEntityBtn(
                                        `/config/devices/device/${this.haDeviceId}`,
                                        t("devices.open_in_ha"),
                                    )
                                  : nothing}
                          </div>
                      `
                    : current != null
                      ? html`<div class="matrix-current">
                            ${t("devices.matrix_current", { cell: current })}
                        </div>`
                      : nothing}
                ${mc && this._selMode !== null
                    ? html`
                          ${this._renderLatticeRow()}
                          ${this._selLattice === null
                              ? this._renderPowerRow(mc)
                              : nothing}
                          ${this._renderDimRow(
                              t("devices.matrix_dim_mode"),
                              mc.modes,
                              this._selPower === null
                                  ? this._selMode
                                  : null,
                              (v) =>
                                  this._selectDim(
                                      v,
                                      this._selFan,
                                      this._selSwing,
                                      this._selTemp,
                                  ),
                              heardHere ? h!.mode : null,
                          )}
                          ${fans.length > 0
                              ? this._renderDimRow(
                                    t("devices.matrix_dim_fan"),
                                    fans,
                                    this._selPower === null
                                        ? this._selFan
                                        : null,
                                    (v) =>
                                        this._selectDim(
                                            this._selMode!,
                                            v,
                                            this._selSwing,
                                            this._selTemp,
                                        ),
                                    heardHere ? h!.fan : null,
                                )
                              : nothing}
                          ${swings.length > 0
                              ? this._renderDimRow(
                                    t("devices.matrix_dim_swing"),
                                    swings,
                                    this._selPower === null
                                        ? this._selSwing
                                        : null,
                                    (v) =>
                                        this._selectDim(
                                            this._selMode!,
                                            this._selFan,
                                            v,
                                            this._selTemp,
                                        ),
                                    heardHere ? h!.swing : null,
                                )
                              : nothing}
                          ${this._renderGrid(current)}
                          <div class="mx-actions">
                              <span class="mx-set ${!armed && hear
                                  ? "mx-prompt"
                                  : ""}">
                                  ${armed
                                      ? t("devices.matrix_set_state", {
                                            name: this._pick()!.name,
                                        })
                                      : hear
                                        ? t("devices.matrix_browse_prompt")
                                        : nothing}
                              </span>
                              ${this.mode === "send"
                                  ? html`
                                        <button
                                            class="action-btn test-btn"
                                            ?disabled=${this.busy || !armed}
                                            @click=${() =>
                                                this._emit("matrix-send")}
                                        >
                                            ${t("fitting.send")}
                                        </button>
                                        <button
                                            class="action-btn mx-cmd-btn"
                                            ?disabled=${this.busy || !armed}
                                            @click=${() =>
                                                this._emit(
                                                    "matrix-save-command",
                                                )}
                                        >
                                            ${t("devices.matrix_add_command")}
                                        </button>
                                    `
                                  : html`
                                        <button
                                            class="action-btn trigger-btn"
                                            ?disabled=${this.busy || !armed}
                                            @click=${() =>
                                                this._emit(
                                                    "matrix-save-trigger",
                                                )}
                                        >
                                            ${t("trow.add_trigger")}
                                        </button>
                                    `}
                          </div>
                      `
                    : nothing}
        `;
    }

    // --- The thinning editor (thinning-plan.md 7) ---------------------

    /** Pencil: open the editor on a fresh draft, or discard it. */
    private _togglePencil(): void {
        if (this._editing) {
            this._cancelEdit();
            return;
        }
        if (!this._cells) return;
        this._draft = startDraft(this._cells);
        this._open = defaultOpen(this._draft);
        this._editing = true;
    }

    private _cancelEdit(): void {
        this._editing = false;
        this._draft = null;
        this._offNote = false;
    }

    /** Apply one draft rule and re-render when it changed anything. The
     * draft is mutated in place, so the state property is re-assigned
     * to tell Lit. */
    private _change(changed: boolean): void {
        if (changed && this._draft) this._draft = { ...this._draft };
    }

    private _flip(key: string): void {
        this._open = { ...this._open, [key]: !this._open[key] };
    }

    private _offClicked(): void {
        this._offNote = true;
        window.clearTimeout(this._offNoteTimer);
        this._offNoteTimer = window.setTimeout(() => {
            this._offNote = false;
        }, 1800);
    }

    /** Save the draft, then leave edit mode and reload.
     *
     * THE RECEIPT IS THE PAGE'S, NOT THE CARD'S (owner bench
     * 2026-09-22, item 2). Round one wrote the line into a state
     * property of this element and it never reached the bench: the
     * device page around the card is rebuilt for reasons the card
     * cannot see, and anything held here goes with it. So the page's
     * own flash says what happened, exactly as it does for a saved
     * state, and the card reports only by resolving or rejecting.
     *
     * A refusal or a failed write leaves the draft open -- nothing
     * changed on the device, and the person's work should still be
     * there to fix or cancel. The page has already said why.
     */
    private async _saveThin(): Promise<void> {
        const draft = this._draft;
        if (!draft || !this.thinSaver || !removesAnything(draft)) return;
        if (this._thinBusy) return;
        this._thinBusy = true;
        try {
            await this.thinSaver(thinPayload(draft));
            this._editing = false;
            this._draft = null;
            await this._loadCells();
        } catch {
            // Reported by the page; the draft stays.
        } finally {
            this._thinBusy = false;
        }
    }

    /** The house chevron from ir-clips.ts: bare stroked path, 22px
     * glyph in a 32px button, rotated when open. ``blank`` keeps its
     * place for a line with nothing to open. */
    private _chevron(open: boolean, onClick: () => void, blank = false) {
        return html`<button
            class="expand-btn ${blank ? "blank" : ""}"
            title=${open ? t("sniffer.collapse") : t("sniffer.expand")}
            aria-label=${open ? t("sniffer.collapse") : t("sniffer.expand")}
            aria-expanded=${open ? "true" : "false"}
            ?disabled=${blank || this._thinBusy}
            @click=${(e: Event) => {
                e.stopPropagation();
                if (!blank) onClick();
            }}
        >
            <svg
                class="chevron ${open ? "chevron-open" : ""}"
                viewBox="0 0 24 24"
                aria-hidden="true"
            >
                <path d="M6 9l6 6 6-6"></path>
            </svg>
        </button>`;
    }

    private _renderEditor(mc: MatrixCells) {
        const d = this._draft!;
        const sums = totals(d);
        const nothingYet = !removesAnything(d);
        return html`
            <div class="thin-banner">
                <b>${t("devices.thin_banner_title")}</b>
                ${t("devices.thin_banner_body")}
            </div>
            <div class="mx-dim-row">
                <span class="mx-dim-label"
                    >${t("devices.matrix_dim_power")}</span
                >
                <span class="mx-chips">
                    <button
                        class="mx-chip keep locked"
                        title=${t("devices.thin_off_tip")}
                        ?disabled=${this._thinBusy}
                        @click=${() => this._offClicked()}
                    >
                        ${t("fitting.row_off")}
                    </button>
                    ${d.hasOn
                        ? html`<button
                              class="mx-chip ${d.keepOn ? "keep" : "drop"}"
                              title=${t("devices.thin_on_tip")}
                              ?disabled=${this._thinBusy}
                              @click=${() => this._change(toggleOn(d))}
                          >
                              ${t("fitting.row_on")}
                          </button>`
                        : nothing}
                    <span class="thin-off-note ${this._offNote ? "show" : ""}"
                        >${t("devices.thin_off_note")}</span
                    >
                </span>
            </div>
            ${d.lattices.map((l, li) => this._renderGroup(mc, l, li))}
            <div class="thin-save">
                <div class="thin-cost">
                    ${t("devices.thin_cost_1")}
                    <b>${t("devices.thin_cost_new_wig")}</b>${t(
                        "devices.thin_cost_2",
                    )}<b>${t("devices.thin_cost_your_own")}</b>${t(
                        "devices.thin_cost_3",
                    )}
                </div>
                <div class="thin-save-row">
                    <span class="thin-save-count"
                        >${nothingYet ? nothing : this._countLine(sums)}</span
                    >
                    <button
                        class="thin-cancel"
                        ?disabled=${this._thinBusy}
                        @click=${() => this._cancelEdit()}
                    >
                        ${t("common.cancel")}
                    </button>
                    <button
                        class="thin-go ${this._thinBusy ? "working" : ""}"
                        ?disabled=${nothingYet || this._thinBusy || this.busy}
                        @click=${() => void this._saveThin()}
                    >
                        ${this._thinBusy
                            ? t("common.saving")
                            : tp("devices.thin_remove_btn", sums.removed)}
                    </button>
                </div>
            </div>
        `;
    }

    /** "322 cells will be removed across 2 modes (dry, heat_cool),
     * including the whole (boost) lattice. 834 will remain." Built from
     * pieces so each one can carry its own plural. */
    private _countLine(sums: ReturnType<typeof totals>) {
        const modes = sums.modes.length
            ? tp("devices.thin_count_modes", sums.modes.length, {
                  names: sums.modes.join(", "),
              })
            : "";
        const lattices = sums.lattices.length
            ? tp("devices.thin_count_lattices", sums.lattices.length, {
                  names: sums.lattices.join(", "),
              })
            : "";
        const on = sums.onRemoved ? t("devices.thin_count_on") : "";
        return html`<b>${tp("devices.thin_count_cells", sums.removed)}</b>${tp(
                "devices.thin_count_removed",
                sums.removed,
            )}${modes}${lattices}${on}${t("devices.thin_count_stop")}
            ${tp("devices.thin_count_remain", sums.kept)}`;
    }

    private _renderGroup(mc: MatrixCells, l: DraftLattice, li: number) {
        const open = l.on && !!this._open[`g:${li}`];
        const total = latticeTotal(l);
        const kept = latticeKept(l);
        const count = !l.on
            ? html`<span class="cut"
                  >${tp("devices.thin_group_goes", total)}</span
              >`
            : kept < total
              ? html`${t("devices.thin_keeps", {
                        kept: String(kept),
                        total: String(total),
                    })}<span class="cut"
                        >${tp("devices.thin_removed", total - kept)}</span
                    >`
              : tp("devices.thin_group_all", total);
        return html`
            <div class="thin-group ${l.on ? "" : "off"}">
                <div class="thin-ghead">
                    ${li === 0
                        ? html`<span class="thin-gname"
                              >${t("devices.thin_main")}</span
                          >`
                        : html`<button
                                  class="mx-chip thin-head-chip ${l.on
                                      ? "keep"
                                      : "drop"}"
                                  ?disabled=${this._thinBusy}
                                  @click=${() =>
                                      this._change(toggleLattice(this._draft!, li))}
                              >
                                  (${l.key})
                              </button>
                              <span class="thin-tag">${l.axis}</span>`}
                    <span class="thin-count">${count}</span>
                    ${this._chevron(open, () => this._flip(`g:${li}`), !l.on)}
                </div>
                ${open
                    ? l.modes.map((m) => this._renderModeLine(mc, l, li, m))
                    : nothing}
            </div>
        `;
    }

    private _renderModeLine(
        mc: MatrixCells,
        l: DraftLattice,
        li: number,
        m: DraftMode,
    ) {
        const depth = depthOf(m);
        const open = m.on && depth > 0 && !!this._open[`m:${li}:${m.mode}`];
        const total = m.cells.length;
        const kept = modeKept(l, m);
        const count = !m.on
            ? html`<span class="cut"
                  >${tp("devices.thin_mode_goes", total)}</span
              >`
            : kept < total
              ? html`${t("devices.thin_keeps", {
                        kept: String(kept),
                        total: String(total),
                    })}<span class="cut"
                        >${tp("devices.thin_removed", total - kept)}</span
                    >`
              : tp("devices.thin_mode_all", total);
        return html`
            <div class="thin-mode ${m.on ? "" : "off"}">
                <div class="thin-mhead">
                    <button
                        class="mx-chip thin-head-chip ${m.on ? "keep" : "drop"}"
                        ?disabled=${this._thinBusy}
                        @click=${() =>
                            this._change(toggleMode(this._draft!, li, m.mode))}
                    >
                        ${m.mode}
                    </button>
                    <span class="thin-tag"
                        >${depth === 0
                            ? t("devices.thin_depth_single")
                            : tp("devices.thin_depth", depth)}</span
                    >
                    <span class="thin-count">${count}</span>
                    ${this._chevron(
                        open,
                        () => this._flip(`m:${li}:${m.mode}`),
                        !m.on || depth === 0,
                    )}
                </div>
                ${open
                    ? html`
                          ${this._renderAxis(li, m, "fans",
                              t("devices.matrix_dim_fan"))}
                          ${this._renderAxis(li, m, "swings",
                              t("devices.matrix_dim_swing"))}
                          ${this._renderTemps(mc, li, m)}
                      `
                    : nothing}
            </div>
        `;
    }

    private _renderAxis(
        li: number,
        m: DraftMode,
        axis: Exclude<ThinAxis, "temps">,
        label: string,
    ) {
        const values = m.carried[axis];
        const kept = m.kept[axis];
        if (!values || !kept) return nothing;
        return html`
            <div class="mx-dim-row">
                <span class="mx-dim-label">${label}</span>
                <span class="mx-chips">
                    ${values.map(
                        (v) => html`<button
                            class="mx-chip ${kept.has(v) ? "keep" : "drop"}"
                            ?disabled=${this._thinBusy}
                            @click=${() =>
                                this._change(
                                    toggleValue(this._draft!, li, m.mode, axis, v),
                                )}
                        >
                            ${v}
                        </button>`,
                    )}
                </span>
            </div>
        `;
    }

    /** The temperatures in the grid the card already draws. */
    private _renderTemps(mc: MatrixCells, li: number, m: DraftMode) {
        const values = m.carried.temps;
        const kept = m.kept.temps;
        if (!values || !kept) return nothing;
        return html`
            <div class="mx-dim-row">
                <span class="mx-dim-label">${t("devices.thin_temp")}</span>
                <div class="mx-grid">
                    ${values.map(
                        (v) => html`<button
                            class="mx-tile ${kept.has(v) ? "keep" : "drop"}"
                            ?disabled=${this._thinBusy}
                            @click=${() =>
                                this._change(
                                    toggleValue(this._draft!, li, m.mode, "temps", v),
                                )}
                        >
                            ${displayTemp(
                                v,
                                mc.unit,
                                installUnit(this.hass),
                                mc.precision,
                            )}
                        </button>`,
                    )}
                </div>
            </div>
        `;
    }

    static styles = [
        actionChipStyles,
        bloomStyles,
        editButtonStyles,
        exitToEntityButtonStyles,
        css`
            /* The card is a block in its parent's flow, exactly as the
               plain <div class="matrix-card"> it replaced was. */
            :host {
                display: block;
            }

            /* The STATE MATRIX card (Cold Cuts second half, mockup CC3):
               the cell browser in the cold-blue family (#58a6d8) -- the
               stateful signature the closet's fit-tick glow introduced.
               Everything in here is the card's own dialect; the action bar
               reuses the shared chip anatomy. */
            .matrix-card {
                margin-top: 12px;
                padding: 9px 12px 10px;
                border: 1px solid rgba(88, 166, 216, 0.45);
                border-radius: 8px;
                font-size: 0.85rem;
                color: var(--primary-text-color);
                line-height: 1.5;
            }
            .mx-head {
                display: flex;
                align-items: baseline;
                gap: 10px;
                flex-wrap: wrap;
            }
            .mx-title {
                font-size: 0.72rem;
                font-weight: 600;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: #58a6d8;
            }
            .mx-summary {
                font-size: 0.8rem;
                color: var(--secondary-text-color);
            }
            .matrix-current {
                font-size: 0.78rem;
                color: var(--secondary-text-color);
            }
            .mx-dim-row {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 8px;
            }
            .mx-dim-label {
                flex: none;
                width: 44px;
                font-size: 0.68rem;
                font-weight: 600;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                color: var(--secondary-text-color);
            }
            .mx-chips {
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
            }
            .mx-chip {
                font-size: 0.75rem;
                font-family: inherit;
                padding: 3px 10px;
                border-radius: 12px;
                border: 1px solid var(--divider-color);
                background: none;
                color: var(--primary-text-color);
                cursor: pointer;
                transition: background 150ms ease, border-color 150ms ease;
            }
            .mx-chip:hover {
                border-color: rgba(88, 166, 216, 0.6);
            }
            .mx-chip.on {
                background: #58a6d8;
                border-color: #58a6d8;
                color: #fff;
            }
            .mx-grid {
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
                margin-top: 10px;
            }
            .mx-tile {
                width: 52px;
                height: 38px;
                box-sizing: border-box;
                border: 1px solid var(--divider-color);
                border-radius: 6px;
                background: none;
                font-family: inherit;
                font-size: 0.82rem;
                font-weight: 500;
                color: var(--primary-text-color);
                cursor: pointer;
                transition: background 150ms ease, border-color 150ms ease,
                            box-shadow 300ms ease;
            }
            .mx-tile:hover:not(:disabled):not(.sel) {
                border-color: rgba(88, 166, 216, 0.6);
            }
            /* Absent position: the matrix is sparse and says so -- dashed,
               inert, dimmed, with the tooltip carrying the sentence. */
            .mx-tile.absent {
                border-style: dashed;
                color: var(--secondary-text-color);
                opacity: 0.45;
                cursor: default;
            }
            .mx-tile.sel {
                background: #58a6d8;
                border-color: #58a6d8;
                color: #fff;
            }
            /* The entity's CURRENT cell wears the cold glow ring, whatever
               else it is -- same cue language as the closet's matrix tick. */
            .mx-tile.cur {
                box-shadow:
                    0 0 0 2px rgba(88, 166, 216, 0.5),
                    0 0 10px rgba(88, 166, 216, 0.55);
            }
            /* The REST RIM (Track M): what was last heard keeps a gold
               ring after its bloom fades, until the next frame
               supersedes it. Same box-shadow technique as .cur above,
               in the trigger family's gold rather than the cold blue,
               because heard and current are different facts and a
               remote page shows only the first. */
            .mx-chip.rest,
            .mx-tile.rest {
                box-shadow:
                    0 0 0 2px rgba(212, 160, 23, 0.5),
                    0 0 10px rgba(212, 160, 23, 0.5);
            }
            /* The listener note under the summary (brief section 5,
               option b): one line, not a row in the trigger list. */
            .mx-note {
                display: flex;
                align-items: center;
                gap: 4px;
                font-size: 0.76rem;
                color: var(--secondary-text-color);
                font-style: italic;
            }
            /* Nothing browsed yet: the action bar says what to do
               rather than naming a state nobody picked. */
            .mx-set.mx-prompt {
                color: var(--secondary-text-color);
                font-family: inherit;
                font-style: italic;
            }
            .mx-actions {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 12px;
                padding-top: 10px;
                border-top: 1px solid var(--divider-color);
            }
            .mx-set {
                flex: 1;
                min-width: 0;
                font-size: 0.8rem;
                color: var(--primary-text-color);
                font-family: var(--code-font-family, monospace);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            /* Save-state-as-command wears the Clipper's copper: it does the
               same kind of thing as Add Signal -- one more command row. */
            .action-btn.mx-cmd-btn {
                color: #b87333;
                border-color: rgba(184, 115, 51, 0.35);
            }
            .action-btn.mx-cmd-btn:hover:not(:disabled) {
                background: rgba(184, 115, 51, 0.08);
            }

            /* --- Thinning (thinning-design-brief.md 3 to 7) ---------
               Ember (#e65100, HAIR's delete colour) does exactly four
               jobs here: the card border in edit mode, the lit pencil,
               every removed value, and the Remove button. The banner
               and the cost paragraph are neutral on purpose. */
            .mx-head-spacer {
                flex: 1;
            }
            .mx-head .thin-pencil {
                align-self: center;
            }
            .matrix-card.editing {
                border-color: #e65100;
            }
            .thin-pencil.on .edit-btn {
                color: #e65100;
                background: rgba(230, 81, 0, 0.2);
            }
            .thin-banner,
            .thin-cost {
                margin: 10px 0 2px;
                padding: 8px 11px;
                border-radius: 5px;
                background: var(--secondary-background-color, rgba(127, 127, 127, 0.1));
                font-size: 0.8rem;
                line-height: 1.6;
                color: var(--secondary-text-color);
            }
            .thin-banner b,
            .thin-cost b {
                color: var(--primary-text-color);
            }
            .thin-group {
                margin-top: 14px;
            }
            .thin-ghead,
            .thin-mhead {
                display: flex;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
            }
            .thin-ghead {
                padding: 4px 0 2px;
                border-bottom: 1px solid var(--divider-color);
            }
            .thin-gname {
                font-size: 0.72rem;
                font-weight: 600;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                color: var(--secondary-text-color);
            }
            .thin-tag {
                font-size: 0.66rem;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: var(--secondary-text-color);
                border: 1px solid var(--divider-color);
                border-radius: 3px;
                padding: 0 5px;
            }
            .thin-count {
                font-size: 0.76rem;
                color: var(--secondary-text-color);
            }
            .thin-count .cut,
            .thin-save-count b {
                color: #e65100;
                font-weight: 600;
            }
            .thin-mode {
                border: 1px solid var(--divider-color);
                border-radius: 6px;
                padding: 4px 10px 8px;
                margin-top: 10px;
            }
            .thin-mode.off,
            .thin-group.off {
                opacity: 0.75;
            }
            .thin-head-chip {
                font-weight: 600;
            }
            .thin-off-note {
                font-size: 0.72rem;
                color: #e65100;
                opacity: 0;
                transition: opacity 150ms ease;
            }
            .thin-off-note.show {
                opacity: 1;
            }
            .thin-save {
                margin-top: 14px;
                padding-top: 12px;
                border-top: 1px solid var(--divider-color);
            }
            .thin-save-row {
                display: flex;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 10px;
            }
            .thin-save-count {
                flex: 1;
                min-width: 200px;
                font-size: 0.82rem;
            }
            .thin-cancel,
            .thin-go {
                font-family: inherit;
                font-size: 0.8rem;
                padding: 6px 14px;
                border-radius: 4px;
                cursor: pointer;
            }
            .thin-cancel {
                border: 1px solid var(--divider-color);
                background: none;
                color: var(--primary-text-color);
            }
            .thin-go {
                border: 1px solid #e65100;
                background: #e65100;
                color: #fff;
                font-weight: 600;
            }
            .thin-go:disabled,
            .thin-cancel:disabled {
                opacity: 0.4;
                cursor: default;
            }
            /* A save in flight: the whole edit view goes inert, so a
               chip cannot change the draft under a write already on
               its way, and the button says what it is doing. */
            .thin-go.working {
                opacity: 0.7;
            }
            .mx-chip:disabled,
            .mx-tile:disabled,
            .expand-btn:disabled {
                cursor: default;
            }
            /* The house chevron, lifted from ir-clips.ts with its three
               tuning knobs, pushed to the right edge of its line. */
            .expand-btn {
                --hair-chevron-size: 32px;
                --hair-chevron-glyph: 22px;
                --hair-chevron-weight: 2.5;
                width: var(--hair-chevron-size);
                height: var(--hair-chevron-size);
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
                border: 0;
                background: none;
                color: var(--secondary-text-color);
                cursor: pointer;
                transition: color 150ms ease;
                margin-left: auto;
            }
            .expand-btn .chevron {
                width: var(--hair-chevron-glyph);
                height: var(--hair-chevron-glyph);
                fill: none;
                stroke: currentColor;
                stroke-width: var(--hair-chevron-weight);
                stroke-linecap: round;
                stroke-linejoin: round;
                transition: transform 150ms ease;
            }
            .expand-btn .chevron-open {
                transform: rotate(180deg);
            }
            .expand-btn:hover {
                color: var(--primary-text-color);
            }
            .expand-btn.blank {
                visibility: hidden;
            }
            /* KEEP and DROP, declared LAST, after .mx-chip and .mx-tile
               and their .on / .sel, at equal specificity so they win on
               order. Mockup T3 shipped with the grid cell's own
               background beating .keep; T4 fixed it this way. */
            .mx-chip.keep,
            .mx-tile.keep {
                background: rgba(67, 160, 71, 0.16);
                border-color: #43a047;
                color: var(--primary-text-color);
            }
            .mx-chip.drop,
            .mx-tile.drop {
                background: rgba(230, 81, 0, 0.2);
                border-color: #e65100;
                color: var(--secondary-text-color);
                text-decoration: line-through;
            }
            .mx-chip.locked {
                cursor: default;
            }
        `,
    ];
}

declare global {
    interface HTMLElementTagNameMap {
        "ir-matrix-card": IrMatrixCard;
    }
}
