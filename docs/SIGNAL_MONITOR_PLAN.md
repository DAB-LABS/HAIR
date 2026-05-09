# HAIR Signal Monitor -- Implementation Plan

*v3 (final) -- Updated with trio debate consensus items.*

## Overview

Replace HAIR's session-based "click Learn, press button" capture model with an
always-on IR signal monitor that passively observes all IR traffic, groups
signals by source device, ranks by activity, and lets users assign discovered
signals as named commands.

Think of it as an IR network scanner: plug in an ESP32 receiver and HAIR maps
your IR environment automatically.

**Hardware requirement:** The passive signal monitor requires an ESPHome device
with `ir_rf_proxy` + `remote_receiver` configured. Other IR hardware (Tuya,
Broadlink) stores learned commands internally and does not expose raw signal
data to Home Assistant. This limitation must be clearly communicated in the
setup UI and documentation.

## Motivation

- The current capture flow requires the user to initiate a session, pick a
  capture provider, and press a button within a timeout window. This is fragile
  and unfamiliar to non-technical users.
- Capture provider discovery lists every ESPHome device, not just IR-capable
  ones. Users see irrelevant entries.
- Tuya and other "opaque learner" devices cannot serve as capture providers
  because they store learned commands internally and never expose raw signal
  data to HA. Only ESPHome with `ir_rf_proxy` + `remote_receiver` returns raw
  timings.
- The new model is passive: HAIR watches, groups, and surfaces. The user names
  what they recognize.

## Architecture

### Signal Flow

```
IR Remote
    |
    v
ESP32 (TSOP38238 receiver)
    |  ESPHome ir_rf_proxy + remote_receiver
    v
Home Assistant event bus
    |  esphome.remote_received event (protocol, code, raw_timings)
    v
EventParser (adapter layer -- isolates ESPHome event format)
    |  produces CaptureResult
    v
SignalMonitor (always-on listener)
    |  1. check known commands (skip if already assigned)
    |  2. check dismiss list (skip if dismissed)
    |  3. check rate limiter (skip if flooding)
    |  4. group by device address + command fingerprint
    v
Unknown Signal Catalog (persisted storage)
    |  ranked by activity (hit_count, last_seen)
    v
Frontend Signal Monitor panel (real-time + historical)
    |  user clicks "Save as Command"
    v
HAIR Device + IRCommand (existing model)
```

### EventParser Adapter Layer

The ESPHome `ir_rf_proxy` component is marked experimental and its event
payload format may change. To isolate the rest of the system from this
instability, all event parsing goes through a dedicated `EventParser` class:

```python
class EventParser:
    """Parse esphome.remote_received events into CaptureResult instances.

    Single point of change if the ESPHome event format evolves.
    """
    @staticmethod
    def parse(event_data: dict) -> CaptureResult | None:
        ...

    @staticmethod
    def extract_device_address(protocol: str | None, code: str | None) -> str | None:
        ...
```

If the event format changes, only `EventParser` needs updating. The
`SignalMonitor`, storage, and WebSocket layers remain untouched.

### IR Protocol Device Addressing

Most IR protocols encode a device address and a command code separately:

- NEC: 8-bit address + 8-bit command (address identifies the device)
- Samsung: 8-bit custom code + 8-bit data
- Sony (SIRC): 5/8/13-bit address + 7-bit command
- RC5/RC6: 5-bit address + 6-bit command
- Raw (no protocol decoded): group by raw timing similarity hash

HAIR uses the device address portion to cluster signals from the same physical
remote into an `UnknownDevice`. Individual button presses within that remote
become `UnknownSignal` entries.

### NEC Repeat Code Handling

NEC remotes send the full code once, then flood short repeat frames while the
button is held. The `EventParser` must detect and collapse NEC repeat codes so
that holding a button counts as a single press, not dozens. Other protocols
retransmit the full code on repeat -- those are collapsed by the
SignalMonitor's fingerprint deduplication (same fingerprint within a short
window increments hit_count once).

**Repeat suppression window:** If the same signal fingerprint arrives within
300ms of the previous occurrence, treat it as a hold-repeat and do not
increment hit_count. This prevents held buttons from inflating activity
rankings.

### Raw Timing Fingerprinting Algorithm

For signals where no protocol is decoded, raw timings must be fingerprinted
consistently despite timing jitter between presses. Algorithm:

1. Quantize each timing value to the nearest 50us bin:
   `quantized = round(abs(timing) / 50) * 50 * sign(timing)`
2. Truncate to first 64 values (sufficient for identification, caps hash input)
3. Compute SHA-256 hash of the quantized, truncated timing list
4. Use first 16 hex chars as the fingerprint

This produces stable fingerprints across multiple presses of the same button
while distinguishing genuinely different signals.

## Data Models

### UnknownSignal

```python
@dataclass
class UnknownSignal:
    fingerprint: str           # hash(protocol + code) or quantized raw hash
    protocol: str | None       # "NEC", "Samsung", "Sony", "RC5", None
    code: str | None           # command portion, e.g., "0x08"
    raw_timings: list[int]     # raw pulse widths in microseconds
    frequency: int             # carrier frequency, captured from event
    hit_count: int             # total times this signal seen (repeat-suppressed)
    first_seen: str            # ISO timestamp
    last_seen: str             # ISO timestamp
```

Note: `frequency` is always captured from the event data. Not assumed to be
38kHz, since some protocols (RC5, RC6) use 36kHz.

### UnknownDevice

```python
@dataclass
class UnknownDevice:
    id: str                    # uuid
    fingerprint: str           # hash(protocol + device_address) or grouping key
    protocol: str | None
    device_address: str | None # address portion from protocol decode
    signals: list[UnknownSignal]
    hit_count: int             # aggregate across all signals
    first_seen: str
    last_seen: str
    dismissed: bool            # user chose to hide this device
```

## Storage

### Separate Store

Unknown signals get their own HA `Store` instance:
- Key: `hair_unknown_signals`
- Version: 1
- Separate from `hair_devices` so clearing unknowns does not touch configured
  devices and vice versa.

### Persistence

- Survives HA restarts
- Debounced writes: mark dirty on signal receipt, flush after 30 seconds of
  quiet. Timer resets on each new signal.
- **Hard ceiling:** Force-flush after 5 minutes regardless of activity to
  prevent write starvation in busy IR environments.
- Immediate save on user actions (assign, dismiss)
- Save on integration unload

### Eviction Policy

| Rule | Threshold | Rationale |
|------|-----------|-----------|
| Max unknown devices | 500 (configurable via options) | Prevent unbounded growth |
| Age + low activity | >30 days AND <5 hits | Noise cleanup |
| High activity retention | 10+ hits | Clearly real devices, keep until dismissed |
| Buffer full | Evict lowest hit_count, oldest last_seen first | Make room |
| Dismiss list | Unlimited (persist indefinitely) | Dismissed devices must never resurface |

Note: The dismiss list stores both the composite fingerprint and the
protocol+address pair (for decoded protocols). This prevents a dismissed device
from resurfacing due to minor raw timing drift. The dismiss list is persisted
and has no cap -- the storage cost is negligible (a few KB for thousands of
fingerprints).

### Constants

```python
SIGNAL_STORAGE_KEY = "hair_unknown_signals"
SIGNAL_STORAGE_VERSION = 1
SIGNAL_BUFFER_MAX_DEVICES = 500
SIGNAL_EVICT_AGE_DAYS = 30
SIGNAL_EVICT_MIN_HITS = 5
SIGNAL_CLUSTER_THRESHOLD = 3      # min hits before surfacing in UI
SIGNAL_REPEAT_SUPPRESS_MS = 300   # collapse repeats within this window
SIGNAL_SAVE_DEBOUNCE_S = 30       # debounced save delay
SIGNAL_SAVE_MAX_DELAY_S = 300     # hard ceiling: force save after 5 min
SIGNAL_RATE_LIMIT_PER_SEC = 10    # max events per fingerprint per second
EVENT_SIGNAL_DETECTED = f"{DOMAIN}_signal_detected"
```

## Components

### 1. EventParser (`event_parser.py`)

Adapter layer that isolates ESPHome event format from the rest of the system.

**Responsibilities:**
- Parse `esphome.remote_received` event data into `CaptureResult`
- Extract device address from decoded protocols (NEC address byte, Samsung
  custom code, etc.)
- Detect and flag NEC repeat codes
- Generate raw timing fingerprints using the quantization algorithm
- Generate device fingerprints from protocol + address

Single point of change if ESPHome's event format evolves. All other components
depend on `CaptureResult`, not on raw event data.

### 2. SignalMonitor (`signal_monitor.py`)

Core always-on service.

**Lifecycle:**
- `async_start()` -- called from `async_setup_entry()`. Subscribes to
  `esphome.remote_received` events on HA bus. Loads signal store.
- `async_stop()` -- called from `async_unload_entry()`. Unsubscribes, flushes
  storage.

**Event handling (`_on_ir_event`) -- corrected ordering:**
1. Parse event data via `EventParser` into a `CaptureResult` (bail if unparseable)
2. Check if signal matches any existing HAIR command -- if so, skip entirely
3. Check dismiss list -- if fingerprint or protocol+address is dismissed, skip
4. Check rate limiter -- if this fingerprint exceeds 10 events/sec, skip
5. Check repeat suppression -- if same fingerprint within 300ms, skip
6. Find or create `UnknownDevice` by device address fingerprint
7. Find or create `UnknownSignal` within that device by command fingerprint
8. Increment hit counts, update timestamps
9. Run eviction if buffer full
10. Mark storage dirty, schedule debounced save
11. Fire `EVENT_SIGNAL_DETECTED` on HA bus with signal summary
12. Notify WebSocket subscribers (rate-limited to max 5 pushes/sec per client)

**Concurrency:** An `asyncio.Lock` guards the find-or-create path (steps 6-8)
to prevent duplicate device/signal creation from interleaved coroutines.

**Rate limiting:** Per-fingerprint token bucket, max 10 events/sec. Prevents a
stuck remote or IR noise source from consuming memory and CPU. Rate limiter
state is in-memory only (not persisted).

**Public API:**
- `get_unknown_devices(include_dismissed=False, min_hits=None)` -> sorted by
  hit_count desc, filtered by `min_hits` (defaults to `SIGNAL_CLUSTER_THRESHOLD`,
  pass `min_hits=0` to include all signals including low-activity noise)
- `get_unknown_device(device_id)` -> single device with signals
- `dismiss_device(device_id)` -> marks dismissed, adds fingerprint to dismiss list
- `undismiss_device(device_id)` -> removes dismissed flag
- `assign_signal(device_id, signal_fingerprint, hair_device_id, command_name, command_category)` -> creates IRCommand from signal, adds to HAIR device, removes from unknowns (atomic: rolls back IRCommand on unknown-removal failure and vice versa)
- `test_signal(signal_fingerprint, emitter_entity_id)` -> sends the signal through the specified emitter without saving it (for user verification)
- `clear_all()` -> wipe unknown catalog
- `subscribe(callback)` / `unsubscribe()` -> real-time signal push

**Assign coordination:** The `assign_signal` method uses best-effort
coordinated saves across the two Store instances (hair_devices and
hair_unknown_signals). It wraps IRCommand creation and unknown signal removal
in a try/finally block and rolls back on partial failure. However, because
the two Stores are independent files, a crash between saves could leave a
duplicate (signal reappears as unknown after restart). This is the worst case
and is fully recoverable -- the user simply re-assigns the signal. True
cross-store atomicity is not feasible without a transactional storage layer,
which is not warranted for this use case.

### 3. Signal Store (`signal_store.py`)

Handles persistence of the unknown signal catalog.

- `async_load()` -> deserialize UnknownDevice/UnknownSignal from disk
- `async_save()` -> serialize to disk (debounced)
- `schedule_save(delay=30)` -> debounced save timer with 5-minute hard ceiling
- `evict()` -> apply eviction rules
- `add_dismissed(fingerprint, protocol_address=None)` -> add to dismiss list (both fingerprint and protocol+address if available)
- `is_dismissed(fingerprint, protocol_address=None)` -> check dismiss list (matches on either)
- `remove_dismissed(fingerprint)` -> remove from dismiss list

### 4. Capture Provider Filter (`capture.py` modification)

Refactor `get_available_capture_providers()`:
- ESPHome: only include devices that have a corresponding `infrared.*` entity
  registered in HA's entity registry (indicates `ir_rf_proxy` is configured)
- Broadlink: keep as legacy fallback
- Remove the "list every device" approach

### 5. Integration Wiring (`__init__.py` modification)

- Create `SignalMonitor` in `async_setup_entry()`
- Store in `hass.data[DOMAIN][entry_id]["signal_monitor"]`
- Call `signal_monitor.async_start()` after setup
- Call `signal_monitor.async_stop()` in `async_unload_entry()`
- Keep `CaptureOrchestrator` for manual learn-mode fallback (deprecate later)

### 6. WebSocket API (`websocket_api.py` additions)

New endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `hair/unknown/devices` | GET | List unknown devices sorted by activity (filtered by cluster threshold) |
| `hair/unknown/device` | GET | Single unknown device with all signals |
| `hair/unknown/dismiss` | POST | Hide a device from the list |
| `hair/unknown/undismiss` | POST | Unhide a dismissed device |
| `hair/unknown/assign` | POST | Assign signal to a HAIR device + command (was "claim") |
| `hair/unknown/test` | POST | Send a signal through an emitter for verification |
| `hair/unknown/clear` | POST | Wipe all unknown signals |
| `hair/unknown/subscribe` | SUB | Real-time push of new signals (rate-limited to 5/sec) |

Existing endpoints unchanged. `hair/capture/start` and `hair/capture/stop`
remain for manual fallback.

### 7. Frontend (separate effort, after backend is solid)

- New "Signal Monitor" tab in the HAIR admin panel
- Hardware requirement notice if no ESPHome IR receivers detected
- Unknown devices as cards, ranked by activity, most active at top
- Real-time pulse indicator when new signals arrive
- "Last 10 seconds" highlight filter for active discovery mode
- Expandable cards showing individual signals with hit counts
- "Test" button on each signal -- sends it through a selected emitter so the
  user can verify the right button was captured before saving
- "Save as Command" button on signal -> dialog to pick or create a HAIR device
  and name the command (inline device creation supported)
- "Save All" on device -> bulk assign all signals. Each signal must be named
  before the button is enabled. The UI presents a naming form for all signals
  in the device; the button remains disabled until every signal has a non-empty
  name.
- "Dismiss" button -> hides device
- "Dismissed" toggle to show/hide dismissed devices
- Activity sparkline or bar showing signal frequency over time
- `SIGNAL_CLUSTER_THRESHOLD` applied: only devices with 3+ hits shown by
  default. A toggle labeled "Show infrequent signals" reveals low-activity
  entries for debugging or manual inspection.

## Implementation Order

Tests are written alongside each phase, not deferred.

### Phase 1: Backend Core + Tests
1. `const.py` -- add new constants
2. `models.py` -- add UnknownSignal, UnknownDevice dataclasses
3. `event_parser.py` -- new file, adapter layer for ESPHome events
4. `signal_store.py` -- new file, persistent storage with eviction
5. `signal_monitor.py` -- new file, core always-on listener
6. `capture.py` -- refactor provider discovery filter
7. `test_event_parser.py` -- protocol parsing, address extraction, fingerprinting
8. `test_signal_store.py` -- persistence, eviction, dismiss list, debounce
9. `test_signal_monitor.py` -- event handling, grouping, clustering, assign flow, atomicity, rate limiting, repeat suppression

### Phase 1.5: Hardware Validation Gate
Backend must pass all mock-event unit tests before this phase begins. Once
ESP32 hardware arrives:
10. Flash ESPHome with `ir_rf_proxy` + `remote_receiver` config
11. Validate real `esphome.remote_received` event payloads against EventParser
12. Tune raw timing quantization bin size (50us) and repeat suppression window
    (300ms) with real-world signals
13. Confirm signal grouping and fingerprinting with multiple remotes

No frontend work begins until hardware validation passes.

### Phase 2: Integration Wiring + Tests
14. `__init__.py` -- wire up SignalMonitor lifecycle
15. `websocket_api.py` -- add new endpoints
16. `test_init.py` -- update with signal monitor lifecycle tests
17. `test_websocket_api.py` -- update with new endpoint tests

### Phase 3: Frontend (gated on Phase 1.5 completion)
14. Signal monitor panel component
15. Real-time WebSocket subscription
16. Assign flow UI with inline device creation
17. Test signal UI
18. Dismiss/undismiss UI
19. "Last 10 seconds" highlight mode

## Backward Compatibility

- Existing `CaptureOrchestrator` and manual capture WS endpoints remain
  functional. No breaking changes to the existing API.
- Existing `IRDevice` and `IRCommand` models unchanged.
- Existing entity platforms (remote, media_player, climate, fan) unchanged.
- Storage schema for `hair_devices` unchanged.
- New `hair_unknown_signals` storage file is additive.

## Risks and Open Questions

1. **ESPHome event format:** The `ir_rf_proxy` is experimental. The
   `EventParser` adapter layer isolates this risk. If the event shape changes,
   only `EventParser` needs updating.

2. **Protocol address extraction:** Parsing device addresses from decoded
   protocols requires protocol-specific logic. Initial implementation extracts
   NEC and Samsung addresses. Others fall back to full protocol+code
   fingerprinting. Address extraction is expanded incrementally as protocols
   are encountered in the wild.

3. **Signal similarity for raw timings:** The quantize-to-50us-bins algorithm
   needs validation with real hardware. The 50us bin size and 64-value
   truncation are initial values that may need tuning. The algorithm is
   encapsulated in `EventParser` for easy adjustment.

4. **Performance:** Rate limiting (10 events/sec per fingerprint) and repeat
   suppression (300ms window) prevent runaway resource consumption. The
   debounced save with 5-minute hard ceiling prevents disk thrashing without
   risking write starvation.

5. **No hardware to test yet:** ESP32 parts are on order. Backend can be built
   and unit-tested with mock events, but real validation waits for hardware
   arrival.

6. **Buffer sizing:** The 500-device cap is configurable via integration
   options. Real-world usage will determine if this needs adjustment. Eviction
   rules handle overflow gracefully.

## Dependencies

- ESPHome `ir_rf_proxy` component (experimental, API may change)
- HA 2026.4+ native `infrared` platform
- ESP32 with TSOP38238 (receiver) and TSAL6200 (emitter) -- hardware on order
