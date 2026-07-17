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

export type CommandSourceId = "captured" | "database" | "imported";

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
}

export interface CodeBrand {
    brand: string;
    label: string;
    codebooks: CodeCodebook[];
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

export type SignalSourceId = "sniffed" | "manual" | "plucked";

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
    // Assignment provenance (dots polish, v0.5.7). Number of HAIR device
    // commands whose fingerprint matches this signal, and their
    // "<device>.<command>" labels for the green Assign dot's tooltip.
    assignment_count?: number;
    assigned_to?: string[];
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
