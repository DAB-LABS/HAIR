/**
 * Shared TypeScript type definitions for the HAIR admin panel.
 *
 * Mirrors the Python dataclasses in custom_components/hair/models.py.
 * Field names use snake_case to match the WebSocket payloads emitted
 * by websocket_api.py.
 */

export type DeviceTypeId =
    | "media_player"
    | "ac"
    | "fan"
    | "light"
    | "switch"
    | "screen"
    | "other";

export type CommandCategoryId =
    | "power"
    | "volume"
    | "channel"
    | "navigation"
    | "mode"
    | "temperature"
    | "fan_speed"
    | "brightness"
    | "color_temp"
    | "cover"
    | "media_control"
    | "custom";

export interface ActionOption {
    key: string;
    label: string;
}

export type CommandSourceId = "captured" | "database" | "imported" | "matrix";

export type CaptureProviderTypeId = "esphome" | "broadlink" | "native" | "mock";

export interface IRCommand {
    id: string;
    name: string;
    category: CommandCategoryId;
    source: CommandSourceId;
    protocol: string | null;
    code: string | null;
    raw_timings?: number[] | null;
    frequency: number;
    repeat_count: number;
    // Whole-frame send count (v0.4.x): transmit the built signal this many
    // times (1 = once). Drives the orange row indicator and the editor field.
    send_count: number;
    // Decoded protocol identity (v0.4.0). Present when the command was
    // decoded as a known protocol; gates the canonical-TX toggle and labels
    // its button (e.g. NEC).
    decoded_protocol?: string | null;
    decoded_fingerprint?: string | null;
    // Protocol state beyond the identity (v0.6.0): RC-5/Marantz toggle,
    // Sharp extension. Server-managed; surfaced for display only.
    decoded_extras?: Record<string, number> | null;
    // Byte-level identity (v0.3.4 tiebreaker; identity since v0.5.8).
    // Was missing from this interface -- the device-detail trigger dialog
    // reads it -- which surfaced as a TS2339 build warning.
    byte_hash?: string | null;
    tx_force_raw?: boolean;
    // The comb doubted this row in the wig it was adopted from
    // (v0.9.5). Display only: it colours a dot on the row so the
    // person can test exactly what was doubted. Nothing refuses a send
    // because of it.
    comb_suspect?: boolean;
    /** WHICH comb finding flagged it, e.g. "duplicated-neighbour".
     * The marker's tooltip says what the comb found rather than a
     * generic "suspect". */
    comb_finding?: string | null;
    /** A PORTHOLE to a lattice cell: every action through this row
     * acts on the matrix, so delete removes the cell and the confirm
     * names the coordinates. */
    matrix_cell?: Record<string, unknown> | null;
    created_at: string;
}

export interface CommandTemplate {
    name: string;
    category: CommandCategoryId;
    essential: boolean;
}

// Code database picker (Add Remote): the introspected brand -> codebook ->
// function tree from the installed infrared-protocols codebooks.
export interface CodeFunction {
    id: string;
    name: string;
}

export interface CodeCodebook {
    id: string;
    label: string;
    functions: CodeFunction[];
    // "library" = installed infrared-protocols codebook; "local" = a wig
    // from /config/hair/wigs/. Absent on pre-0.7.0 payloads -> library.
    source?: "library" | "local";
}

export interface CodeBrand {
    brand: string;
    label: string;
    codebooks: CodeCodebook[];
}

// Cold Cuts (v0.8.8): the climate-matrix summary block. Served on
// wigs/list entries and full device payloads (owner ruling 2026-07-28)
// so matrix rows and the device page render counts, vocabularies, and
// temp bounds without ever loading cells.
export interface MatrixSummary {
    cells: number;
    // Whether the matrix carries a discrete On power code (many files
    // only have Off). Bounds the clip-confirm count.
    has_on: boolean;
    modes: string[];
    fan_modes: string[];
    swing_modes: string[];
    // Bounds are NATIVE file numbers with the file's unit riding
    // along (unit ruling 2026-07-29): consumers convert for display
    // per render, the payload never pre-converts.
    min_temp: number;
    max_temp: number;
    unit: "C" | "F";
}

// One cell's coordinates in the cell-browser payload (Cold Cuts second
// half, hair/devices/matrix-cells). Single-letter keys because the
// census worst case is 2,689 cells; a dimension the cell does not
// carry is OMITTED, never null. These coordinates round-trip verbatim
// into matrix-send and matrix-command.
export interface MatrixCellCoord {
    m: string;
    f?: string;
    s?: string;
    t?: number;
}

// The full matrix-cells payload: bounds, precision, vocabulary lists
// (matrix_summary ordering: declared first, observed strays after),
// has_on, and every cell as coordinates without a byte of Pronto.
export interface MatrixCells {
    min_temp: number;
    max_temp: number;
    precision: number;
    // The matrix's native unit (unit ruling 2026-07-29). Cell temps
    // and bounds above are in it; displays convert, computations
    // (absent tiles, coordinates) never do.
    unit: "C" | "F";
    modes: string[];
    fan_modes: string[];
    swing_modes: string[];
    has_on: boolean;
    cells: MatrixCellCoord[];
}

// Wigs (v0.7.0 Big Wig): portable code sets in /config/hair/wigs/.
export interface WigInfo {
    filename: string;
    name: string;
    brand: string | null;
    model: string | null;
    notes: string | null;
    origin: string | null;
    signal_count: number;
    // Signal aliases for the count-click peek popover (v0.7.0).
    signals?: string[];
    // What the device IS ("candles", "tv"): squashed lowercase slug,
    // set at signing or in the editor (v0.8.0).
    kind?: string | null;
    // Product identity anchors (v0.8.0): fcc_id / upc / asin / oem
    // conventions, single or multiple values. Editor fields shipped
    // with v0.8.0; closet search matches these since v0.8.1.
    identifiers?: Record<string, string | string[]> | null;
    // Fitting summary (Perfect Fit): drives the row check marks and
    // the fitted/unfitted filter, computed server-side.
    fitting?: FittingSummary;
    // Adopt Device (v0.8.1): HAIR devices already carrying this wig's
    // codes, by tiered identity match.
    linked_devices?: { device_id: string; device_name: string }[];
    // Cold Cuts (v0.8.8): non-null for matrix wigs. Drives the "N
    // states" chip, the peek summary, CLIP suppression, and the
    // fit-tick's cold blue glow.
    matrix?: MatrixSummary | null;
    // Smart Perm: the stored comb receipt, or null when nobody has
    // combed this wig. Drives the comb glyph's glow.
    comb?: CombSummary | null;
}

// Combing (Smart Perm phase 2): the closet's code check.
export interface CombFinding {
    check: string;
    keys: string[];
    // A localization key plus its substitutions; the backend never ships
    // prebaked English.
    message: string;
    params?: Record<string, string>;
}

// What the closet row needs to draw the comb glyph. null on a wig with no
// receipt, which means NOBODY HAS COMBED IT -- deliberately not the same
// as clean, which is a receipt carrying zero suspects.
export interface CombSummary {
    suspects: number;
    date: string | null;
    version: number | null;
    // True when a duplicated neighbour is present: the class the device
    // answers while setting the wrong state. Drives red over yellow.
    dangerous: boolean;
    counts: Record<string, number>;
}

export interface CombReport extends CombSummary {
    filename: string;
    name: string;
    matrix: boolean;
    findings: CombFinding[];
    truncated?: number;
    // Rows the comb did not judge because they are pinned to raw. It
    // records these in the receipt already; naming them here is what
    // stops a clean report implying a check that never ran.
    skipped?: string[];
}

// Attestation: claims about wigs.
/**
 * The closet row's check, derived from claims.
 *
 * Perfect or nothing (owner ruling 2026-08-07, retiring the three-tier
 * RULED 2026-08-03 shape): null (no complete attestation -- nothing at
 * all, or a signed bundle that does not cover every row) or "perfect"
 * (at least one person's claims cover every row). An incomplete bundle
 * still counts toward `fitters`/`covered` -- display of history is not
 * judgment -- it just has no state of its own for the tick to show.
 * Green is keyed to ONE person's complete coverage -- union coverage
 * never inflates it, and rides in the tooltip instead.
 */
export interface FittingSummary {
    state: "perfect" | null;
    user_state: "perfect" | null;
    /** How many people have attested at all. */
    fitters: number;
    /** Who has a perfect fit, for the tooltip. */
    perfect_by: string[];
    /** Union coverage across every fitter. Tooltip material only. */
    covered: number;
    total: number;
}

/** One row inside one person's attestation, as the ledger shows it. */
export interface ClaimRow {
    /** What the row was called WHEN CLAIMED. Display context: the alias
     * is not in the digest, so a rename never orphans a claim. */
    alias: string;
    digest: string;
    verdict: "worked" | "not_on_device" | "wont_work";
    /** False when the wig no longer has a row with this digest: the
     * recipe was edited after somebody proved it. Not an error and not
     * hidden -- it is the most useful thing the ledger can say. */
    present: boolean;
}

/** One signed attestation: one person, one sitting, one wig. */
export interface ClaimBundle {
    handle: string | null;
    github: string | null;
    date: string | null;
    note: string | null;
    /** null = unsigned. A bad signature discredits the ATTRIBUTION,
     * never the data, and the wording has to say which. */
    signed: "valid" | "invalid" | null;
    key_fingerprint: string | null;
    complete: boolean;
    worked: number;
    excluded: number;
    orphaned: number;
    /** Matrix only: the lattice this checklist vouched for. */
    cells_hash: string | null;
    /** Matrix only, null on a flat wig: whether that lattice is still
     * the one on the file. */
    lattice_current: boolean | null;
    mine: boolean;
    rows: ClaimRow[];
}

/** The read-only ledger (hair/wigs/claims).
 *
 * It replaced a tab inside the fitting dialog. There is deliberately
 * no write command paired with this one: attestation happens once, at
 * SAVE TO CLOSET, on the device that was actually tested.
 */
export interface ClaimsLedger {
    filename: string;
    name: string;
    wig_id: string | null;
    matrix: boolean;
    /** Flat rows on the wig. 0 for a matrix wig, whose claims bind the
     * lattice as a set rather than a list of digests. */
    total: number;
    /** Union coverage across every attestation. */
    covered: number;
    entries: ClaimBundle[];
}

// One event from the command editor's Replace section. Same shape as
// the fitting variant, its own event names: both surfaces can be open
// at once during the release that carries them, and a shared name would
// cross their wires.
export type CommandListenEvent =
    | {
          type: "command_capture";
          pronto: string;
          decoded: boolean;
          protocol: string | null;
          receiver: string | null;
      }
    | { type: "command_listen_timeout" };

/** One line of the attestation list, as the dialog draws it. */
export interface SavePlanRow {
    /** The device command this row came from. TEST sends through this;
     * claims come back keyed by digest. Both ends agree on which
     * physical command is meant, which they would not if the row were
     * identified by position -- a command with no usable Pronto never
     * becomes a wig signal, so the two lists are not parallel. */
    command_id: string;
    alias: string;
    digest: string;
    send_count: number;
    ditto_count: number;
    bypass: boolean;
    protocol: string | null;
    wig_index: number | null;
    /** Set when this row matched a source wig row (UPDATE or
     * SUCCESSION): what the WIG calls it. */
    wig_alias: string | null;
    matched: boolean;
    /** Matched by bytes but not by name: the rename line. UPDATE only
     * -- a SUCCESSION successor is authored from the device's current
     * alias directly, so there is no upstream file to propose a
     * rename onto. */
    renamed: boolean;
    /** MATRIX ONLY. A checklist row addresses a cell by coordinate
     * rather than a command by id: TEST sends these, and they compose
     * the row's human label. */
    section?: string | null;
    mode?: string | null;
    fan?: string | null;
    swing?: string | null;
    temp?: number | null;
    temp_less?: boolean;
    temp_role?: string | null;
    power?: string | null;
    /** The comb gate (RULED 2026-08-08). Set on a porthole row minted
     * over a comb-flagged cell -- threaded from the device command's
     * own flag, never recomputed here. */
    comb_suspect?: boolean;
    /** The comb's finding for this row, tooltip material only. */
    comb_finding?: string | null;
}

/** A wig row nothing on the device covers. Second Fitting amendment v2
 * (owner ruling on missing rows, option 2): always a removal now,
 * diverging the save to SUCCESSION -- rendered struck-through with a
 * disabled checkbox, never an exclusion candidate. */
export interface SavePlanMissingRow {
    wig_index: number;
    alias: string;
    digest: string;
}

/** One way the device's lattice differs from the wig it came from. */
export interface CellChange {
    /** "changed" | "deleted" | "added". */
    kind: string;
    /** Coordinate name, matching what the porthole row on the device
     * calls the same cell. */
    label: string;
    mode: string | null;
    fan: string | null;
    swing: string | null;
    temp: number | null;
}

export interface SavePlan {
    /** Second Fitting amendment v2: the verb is derived server-side,
     * never picked by the caller. "succession" mints a successor wig
     * when the device's commands have diverged from the source wig's
     * rows by digest. */
    variant: "create" | "update" | "succession";
    rows: SavePlanRow[];
    missing_rows: SavePlanMissingRow[];
    source_filename: string | null;
    source_wig_id: string | null;
    source_wig_name: string | null;
    /** The device remembers a wig the closet no longer holds. The save
     * falls back to CREATE and says so. */
    source_missing: boolean;
    converted_from: string | null;
    metadata: Record<string, string>;
    skipped: number;
    notes: string[];
    /** How many fittings the source wig already carries. Shown so an
     * UPDATE reads as joining a record rather than starting one. */
    existing_fittings: number;
    /** MATRIX ONLY: the lattice the checklist vouches for, and the
     * units its temperatures are written in. The hash is display and
     * provenance only -- the server stamps the bundle from the matrix
     * it reads at save time, never from this. */
    cells_hash: string | null;
    unit: "C" | "F";
    precision: number;
    /** MATRIX UPDATE only: how the device's lattice differs from the
     * wig's. Non-empty blocks the matrix attestation, because a
     * checklist bundle binds cells_hash, a SET -- signing a diverged
     * lattice would bind bytes the fitter never tested. */
    cell_changes: CellChange[];
    lattice_diverged: boolean;
    /** A climate matrix device. Its lattice lives in the climate
     * entity, not the command list, so the rows above are only its
     * depth-0 extras and the perfect-fit block stays closed. */
    matrix: boolean;
    /** SUCCESSION only (Second Fitting v3): the source wig's own
     * fitting history, graded, for the Update Closet Wig dialog's
     * inline warning before the click. Null state means present but
     * unfitted -- nothing extra renders, same as no claims at all. */
    old_fitting_grade: {
        state: "perfect" | null;
        count: number;
        handles: string[];
    } | null;
    /** Save as New only (Second Fitting v3 punch list, item 4): a
     * shelf-collision-safe default name, present whenever there is a
     * source wig regardless of divergence. Update and Perfect Fit
     * prefill from metadata.name verbatim instead -- a replace keeps
     * the source wig's name. */
    suggested_new_name: string | null;
    /** Second Fitting v3 punch list, item 1: this install already has
     * a bundle on the wig being attested. Present only on a
     * not-diverged plan with a same-key match -- append_claims will
     * replace that bundle rather than add a second one. */
    same_key_notice: { handle: string | null; date: string | null } | null;
}

/** A device that came from the superseded Wig, and how many of the
 * arrival's rows it still lacks (v0.9.7 Second Fitting). */
export interface SupersedeDevice {
    id: string;
    name: string;
    missing_commands: number;
    /** The arrival's rows this device still lacks, by alias (amendment
     * v2 section 2: the confirm names them, not just counts them).
     * Same length as ``missing_commands``, file order. */
    missing_aliases: string[];
}

/** The superseded wig's own fitting history, graded for the confirm
 * (amendment v2 section 2). ``handles`` is every handle that ever
 * fitted the ancestor, first-seen order, regardless of whether their
 * claims were complete -- it credits the grade AND answers the self
 * doorway's "is anyone other than me on this ancestor" question,
 * which needs everyone, not just the perfect ones. */
export interface SupersedeOldFittings {
    count: number;
    state: "perfect" | null;
    handles: string[];
}

/** The replace-flow invitation the server computes at both doorways: an
 * arriving Wig meets an ancestor still in the closet. */
export interface SupersessionBlock {
    old_filename: string;
    old_name: string;
    old_signals: number;
    new_signals: number;
    /** Rows of the local copy the arrival does not carry, by digest. Empty
     * in the friendly state; non-empty arms the guarded one. */
    lost_digests: string[];
    lost_aliases: string[];
    devices: SupersedeDevice[];
    old_fittings: SupersedeOldFittings;
}

/** The reverse-direction import check (v0.9.7 Second Fitting, amendment
 * v2 section 3): the arrival names an id that a wig ALREADY in this
 * closet lists as an ancestor it superseded. ``name``/``signal_count``
 * describe that newer local wig, not the arrival -- the dialog reads
 * "a newer wig here supersedes this one: {name}, {n} signals." */
export interface ReverseSupersessionBlock {
    name: string;
    signal_count: number;
}

/** The outcome of hair/wigs/supersede, per device, for the receipt. */
export interface SupersedeResult {
    deleted: boolean;
    old_filename: string;
    new_filename: string;
    devices: {
        id: string;
        name: string;
        relinked: boolean;
        commands_added: number;
    }[];
}

export interface SaveResult {
    filename: string | null;
    wig_id: string | null;
    signal_count: number;
    skipped: number;
    attested: number;
    /** What the server actually wrote. A SUCCESSION save still comes
     * back "create" -- it mints a wig the same way a CREATE does, so
     * the supersession fires from ``supersession`` below rather than
     * from this field. */
    variant: "create" | "update";
    notes: string[];
    /** Renames that matched nothing. Reported, never silent. */
    stale_renames: string[];
    /** What the fresh comb receipt says about the file just written. */
    suspects: number;
    /** Lattice cells this save proposed upstream. */
    cells_proposed: number;
    /** Present when Save as new mints a self-superseding Wig whose
     * ancestor is still local: the second doorway (v0.9.7). Second
     * Fitting v3's Save as New dialog deliberately never acts on this
     * -- the post-save confirm it used to open is retired as a
     * decision point (spec section 6); only the import doorway still
     * reads it. */
    supersession?: SupersessionBlock;
    /** Present when Update Closet Wig's `replace: true` auto-replaced
     * an ancestor as part of this same save (Second Fitting v3,
     * Commit 2): the dual-act receipt, "Saved as <file>; replaced
     * <old>." */
    replaced?: {
        old_filename: string;
        /** Second Fitting v3 punch list item 13: the receipt names
         * this wig, not its filename. */
        old_name: string;
        deleted: boolean;
        devices: { id: string; name: string }[];
    };
}

export interface WigInvalid {
    filename: string;
    errors: string[];
}

export interface WigsList {
    wigs: WigInfo[];
    invalid: WigInvalid[];
    library: CodeBrand[];
    library_version: string | null;
}

export interface EntityConfig {
    platform: string;
    command_mapping: Record<string, string>;
    temperature_presets?: number[] | null;
    hvac_modes?: string[] | null;
    fan_modes?: string[] | null;
    swing_modes?: string[] | null;
}

export interface IRDevice {
    id: string;
    name: string;
    device_type: DeviceTypeId;
    manufacturer: string | null;
    model: string | null;
    emitter_entity_ids: string[];
    capture_device_id: string | null;
    capture_provider_type: CaptureProviderTypeId;
    commands: IRCommand[];
    entity_config: EntityConfig;
    database_id: string | null;
    created_at: string;
    updated_at: string;
    command_count: number;
    // Cold Cuts (v0.8.8): the state-matrix summary on full device
    // payloads, null for devices without a matrix. Feeds the device
    // page's compact matrix card.
    matrix?: MatrixSummary | null;
    // Second Fitting v3 punch list item 6: the closet wig this device
    // was captured from, if any -- the backend always serializes it
    // (models.py IRDevice.to_dict), and the decision window's
    // synchronous ``hasSource`` gate (whether UPDATE CLOSET WIG is
    // even offered) reads straight off this field, no fetch needed.
    source_wig_id: string | null;
}

export interface DeviceSummary {
    id: string;
    name: string;
    device_type: DeviceTypeId;
    manufacturer: string | null;
    model: string | null;
    emitter_entity_ids: string[];
    command_count: number;
    created_at: string;
    updated_at: string;
}

export interface CaptureProviderInfo {
    type: CaptureProviderTypeId;
    device_id: string;
    name: string;
    config_entry_id: string | null;
    receiver_entity_id?: string;
}

export interface ReceiverInfo {
    entity_id: string;
    name: string;
}

export interface CaptureResult {
    protocol: string | null;
    code: string | null;
    raw_timings: number[];
    frequency: number;
    confidence: number;
}

export type CaptureEvent =
    | { type: "capture_listening" }
    | {
          type: "capture_received";
          result: CaptureResult;
          duplicate_of?: { id: string; name: string };
      }
    | { type: "capture_timeout" }
    | { type: "capture_error"; error: string }
    | { type: "capture_cancelled" };

export interface CaptureStartResponse {
    session_id: string;
    device_id: string;
    timeout: number;
}

// ---------------------------------------------------------------------------
// Signal Monitor (unknown devices)
// ---------------------------------------------------------------------------

export type SignalSourceId = "sniffed" | "manual" | "plucked" | "echo";

// The Mirror's synthetic catalog device (v0.6.6). Rows under this
// fingerprint are send-audit entries, rendered by the Mirror tab and
// filtered out of the Sniffer's live feed.
export const MIRROR_DEVICE_FP = "hair-mirror";

// Fingerprint prefix of the Mirror's unknown-send rows (foreign send,
// never heard, no code). Mirrors MIRROR_UNKNOWN_SEND_FP_PREFIX in
// const.py; the Mirror tab detects these rows by prefix to render the
// explanatory hint in place of the normal sub-line.
export const MIRROR_UNKNOWN_FP_PREFIX = "mirror-unknown::";

export interface UnknownSignal {
    // Stable per-signal identity. The fingerprint is NOT unique on a remote
    // (two distinct commands can share an S/L pattern), so all per-signal
    // operations and the row key use this id. Triggers key on
    // (fingerprint, byte_hash) since v0.5.8; see triggerMatchesSignal().
    id: string;
    fingerprint: string;
    byte_hash?: string | null;
    protocol: string | null;
    code: string | null;
    raw_timings: number[];
    frequency: number;
    hit_count: number;
    first_seen: string;
    last_seen: string;
    sl_pattern?: string | null;
    source?: SignalSourceId;
    alias?: string;
    plucked_command_name?: string | null;
    // Decoded protocol identity, populated when the signal matches a known
    // protocol (NEC today). Mirrors the same fields on IRCommand. Optional
    // because non-decoded signals leave them null.
    decoded_protocol?: string | null;
    decoded_address?: number | null;
    decoded_command?: number | null;
    decoded_fingerprint?: string | null;
    decoded_extras?: Record<string, number> | null;
    // User-tunable TX knobs (mirror IRCommand) plus the capture-side ditto
    // observation surfaced as an editor hint.
    repeat_count?: number;
    send_count?: number;
    // Send the captured Pronto verbatim instead of re-encoding from the
    // decoded identity (Highlights, GH #78). The third knob of the same
    // kind: set here, carried onto the command at assign, into a wig at
    // export. A user decision that survives re-capture.
    tx_force_raw?: boolean;
    observed_repeat_count?: number;
    // Assignment provenance (dots polish, v0.5.7; structured payloads for
    // the assigned popover, v0.6.6). Number of HAIR device commands whose
    // identity matches this signal, plus one structured entry per match:
    // names render the popover rows, ids drive click-through navigation
    // to the device card.
    assignment_count?: number;
    assigned_to?: SignalAssignment[];
    // The Mirror (v0.6.6, source "echo" rows only). echo_source is the
    // provenance display string "<label> -- via <friendly emitters>";
    // heard_by lists the receiver entity_ids that echoed the LAST send
    // (empty = sent, not heard).
    echo_source?: string | null;
    heard_by?: string[] | null;
}

// One catalog-signal-to-HAIR-command assignment link (v0.6.6, assigned
// popover). Serialized by websocket_api._assignment_index.
export interface SignalAssignment {
    device_id: string;
    device_name: string;
    command_id: string;
    command_name: string;
}

export interface UnknownDeviceSummary {
    id: string;
    fingerprint: string;
    protocol: string | null;
    device_address: string | null;
    label: string | null;
    signal_count: number;
    hit_count: number;
    first_seen: string;
    last_seen: string;
    dismissed: boolean;
    source?: SignalSourceId;
    order?: number;
    vendor_entity_id?: string | null;
    appliance?: string | null;
    // The HAIR devices this remote feeds (v0.7.0): stored promote link
    // plus per-signal assignment targets, resolved live by id.
    linked_devices?: { device_id: string; device_name: string }[];
    // Cold Cuts (v0.8.8): the matrix-clip provenance stamp. Non-null
    // only for remotes clipped open (include_matrix) from a matrix
    // wig; drives the adopt signpost.
    source_wig?: { filename: string; cells_hash: string } | null;
    // Resolved live against the closet, list call only and only for
    // stamped remotes: filename intact, renamed (cells hash still
    // matches a closet wig), or honestly gone.
    source_wig_state?: "present" | "renamed" | "gone";
    // The wig's CURRENT filename; present/renamed only.
    source_wig_filename?: string;
}

export interface UnknownDevice {
    id: string;
    fingerprint: string;
    protocol: string | null;
    device_address: string | null;
    label: string | null;
    signals: UnknownSignal[];
    hit_count: number;
    first_seen: string;
    last_seen: string;
    dismissed: boolean;
    source?: SignalSourceId;
    order?: number;
    vendor_entity_id?: string | null;
    appliance?: string | null;
}

// ---------------------------------------------------------------------------
// Plucker (vendor code import)
// ---------------------------------------------------------------------------

export interface PluckBlaster {
    entity_id: string;
    name: string;
}

export interface PluckVendor {
    integration: string;
    name: string;
    appliance_label?: string | null;
    appliance_help?: string | null;
    blasters: PluckBlaster[];
}

export interface PluckedSignalPreview {
    code: string | null;
    protocol: string | null;
    frequency: number;
    raw_timings: number[];
    fingerprint: string;
    byte_hash?: string | null;
    decoded_protocol?: string | null;
    decoded_address?: number | null;
    decoded_command?: number | null;
    decoded_fingerprint?: string | null;
    decoded_extras?: Record<string, number> | null;
    plucked_command_name: string;
    suggested_alias: string;
}

export interface PluckRunResult {
    signals?: PluckedSignalPreview[];
    error?: string;
    message?: string;
}

/**
 * Result of validating a pasted Pronto code (hair/clip/validate-pronto).
 * Mirrors ProntoValidationResult in pronto_validator.py.
 */
export interface ProntoValidation {
    valid: boolean;
    errors: string[];
    warnings: string[];
    frequency_khz: number | null;
    burst_pair_count: number | null;
    normalized: string;
    recognized_protocol?: string | null;
}

export interface UnknownSignalEvent {
    device_id: string;
    device_fingerprint: string;
    signal_id: string;
    signal_fingerprint: string;
    protocol: string | null;
    code: string | null;
    hit_count: number;
    device_hit_count: number;
}

// ---------------------------------------------------------------------------
// Signal Action results
// ---------------------------------------------------------------------------

export interface AssignResult {
    assigned: boolean;
    command_id?: string;
    device_id?: string;
}

export interface TestSignalResult {
    sent: boolean;
}

export interface DeleteSignalResult {
    deleted: boolean;
    device_removed: boolean;
}

export interface SignalRemovedEvent {
    device_id: string;
    signal_id: string;
    device_removed: boolean;
}

/**
 * Fired (rate-limited) when a signal arrives from a remote whose device
 * fingerprint is in the persisted dismiss set. Drives the Sniffer's
 * Show Dismissed button glow + dot indicator. The signal itself is NOT
 * stored or shown in the live feed -- this event is informational only.
 */
export interface DismissActivityEvent {
    device_fingerprint: string;
}

// ---------------------------------------------------------------------------
// Triggers
// ---------------------------------------------------------------------------

export interface IRTrigger {
    id: string;
    name: string;
    signal_fingerprint: string;
    protocol: string | null;
    code: string | null;
    min_hits: number;
    enabled: boolean;
    source_device_id: string | null;
    source_command_id: string | null;
    created_at: string;
    updated_at: string;
    // Receiver scope (location-aware triggers, v0.5.7). Empty = any receiver.
    receiver_entity_ids: string[];
    // Byte-level identity (v0.5.8). null/absent = legacy trigger, matches
    // any byte_hash on the fingerprint. Set = fires only on its button.
    byte_hash?: string | null;
    // Decoded protocol identity (v0.5.8 unified identity). The strongest
    // identity tier; jitter-immune, so it survives the S/L fingerprint
    // flipping on boundary protocols (Sony). null/absent = not decoded.
    decoded_fingerprint?: string | null;
}

/**
 * Whether a trigger belongs to a catalog signal / command row (v0.5.8
 * unified identity).
 *
 * Tiered rule, mirroring the backend's SignalIdentity: the highest
 * identity tier BOTH sides carry decides -- decoded fingerprint, then
 * byte_hash, then the S/L fingerprint. A tier only one side carries is
 * skipped; a decided-tier mismatch is final (no fallthrough). Notably
 * there is NO fingerprint-equality precondition anymore: a Sony row whose
 * coarse fingerprint flipped across the classification boundary still
 * shows its trigger via byte_hash. Sub-threshold sibling rows (shared
 * fingerprint, different hashes) stay separated exactly as before, which
 * keeps the yellow dot, the trigger popover, and the editor from
 * attributing one button's triggers to its siblings.
 */
export function triggerMatchesSignal(
    trigger: IRTrigger,
    signal: {
        fingerprint: string;
        byte_hash?: string | null;
        decoded_fingerprint?: string | null;
    },
): boolean {
    const tDec = trigger.decoded_fingerprint ?? null;
    const sDec = signal.decoded_fingerprint ?? null;
    if (tDec !== null && sDec !== null) return tDec === sDec;
    const tBh = trigger.byte_hash ?? null;
    const sBh = signal.byte_hash ?? null;
    if (tBh !== null && sBh !== null) return tBh === sBh;
    return trigger.signal_fingerprint === signal.fingerprint;
}

export interface TriggerFiredEvent {
    trigger_id: string;
    trigger_name: string;
    hit_count: number;
    protocol: string | null;
    code: string | null;
    source_remote: string | null;
    timestamp: string;
    // Location-aware fields (v0.5.7). Null for legacy captures or a receiver
    // whose device has no HA area assignment.
    receiver_entity_id: string | null;
    receiver_area_id: string | null;
    receiver_area_name: string | null;
}

/**
 * Fired when a signal's assignment set changes (assign, or a device command
 * referencing it is added/removed). Lets the Sniffer/Clipper/Plucker refresh
 * the green Assign badge and yellow trigger dot on other browser tabs.
 */
export interface SignalUpdatedEvent {
    signal_fingerprint: string;
}
