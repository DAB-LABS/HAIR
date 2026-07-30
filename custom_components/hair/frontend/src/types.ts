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
}

// Perfect Fit: the fitting layer.
export interface FittingSummary {
    state: "perfect" | "partial" | null;
    user_state: "perfect" | "partial" | null;
    user_draft: boolean;
    confirmed: number;
    failed: number;
    total: number;
    others_complete: number;
    warnings: string[];
}

export interface FittingLedgerRow {
    handle: string;
    github: string | null;
    date: string | null;
    hair_version: string | null;
    ha_version: string | null;
    emitter: string | null;
    receiver: string | null;
    signals_heard: number | null;
    note: string | null;
    // Send times the fitter recorded (fine-tuned-fittings). null =
    // absent = unknown (pre-field fitting), which renders as nothing.
    // Absent is not 1.
    send_times_used?: number | null;
    confirmed: number;
    failed: number;
    draft: boolean;
    valid: boolean;
    complete: boolean;
    signed: "valid" | "invalid" | null;
    key_fingerprint: string | null;
}

// Cold Cuts (v0.8.8): one fitting-session row. Signal wigs carry the
// minimal shape (key = alias, section null); matrix wigs add the
// dimension-check display facts so the dialog renders the sectioned
// CC1 layout without re-deriving the checklist client-side.
export interface FittingRow {
    key: string;
    section: "start" | "modes" | "fan" | "swing" | "temp" | "wrap" | null;
    mode?: string | null;
    fan?: string | null;
    swing?: string | null;
    temp?: number | null;
    temp_less?: boolean;
    temp_role?: "min" | "max" | null;
    confirmed: boolean;
    failed: boolean;
}

export interface FittingState {
    filename: string;
    username: string;
    kind: string | null;
    // True when this wig fits through the dimension check (Cold Cuts).
    matrix: boolean;
    // Matrix wigs only, null for signal wigs (unit ruling 2026-07-29):
    // the matrix's native unit and precision. Row temps stay native;
    // the dialog converts labels for display with these two facts.
    unit?: "C" | "F" | null;
    precision?: number | null;
    // Row keys in session order; for signal wigs this is the alias
    // list, byte-identical to the pre-0.8.8 payload.
    signals: string[];
    rows: FittingRow[];
    draft: {
        confirmed: string[];
        failed: string[];
        heard: string[];
        date: string | null;
        send_times_used?: number | null;
    } | null;
    ledger: FittingLedgerRow[];
    summary: FittingSummary;
    // Restore value for the session's send-times control: the live
    // session where one exists, else the draft's persisted record.
    // null = fresh session, control starts at 1.
    send_times?: number | null;
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
