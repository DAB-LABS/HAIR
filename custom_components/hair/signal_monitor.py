"""Always-on IR signal monitor for HAIR.

Supports two receive paths:

1. **Native (HA 2026.6+):** subscribes to each ``InfraredReceiverEntity``
   via ``infrared.async_subscribe_receiver()``.  Hardware-agnostic --
   any integration implementing the receiver entity works automatically.
2. **Legacy (HA 2026.4-2026.5):** falls back to listening for
   ``esphome.remote_received`` events on the HA event bus.  Requires
   the ESPHome YAML bridge (``on_pronto`` + ``homeassistant.event``).

Groups observed signals by source device and surfaces unknown IR
activity for user assignment.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_UNAVAILABLE
from homeassistant.core import (
    CALLBACK_TYPE,
    CoreState,
    Event,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.event import (
    async_track_state_added_domain,
    async_track_state_change_event,
    async_track_state_removed_domain,
)

from .const import (
    ASSIGN_SERVICE_TIMEOUT_S,
    DEFAULT_CARRIER_FREQUENCY,
    DITTO_INTER_FRAME_MAX_S,
    ECHO_GARBLE_SIMILARITY,
    EVENT_DISMISS_ACTIVITY,
    EVENT_SIGNAL_DETECTED,
    EVENT_SIGNAL_REMOVED,
    EVENT_SIGNAL_UPDATED,
    LEGACY_ESPHOME_IR_EVENT,
    MAX_DITTO_COUNT,
    MAX_SEND_COUNT,
    MIRROR_DEVICE_FP,
    MIRROR_DEVICE_LABEL,
    MIRROR_ECHO_TTL_S,
    MIRROR_OWN_BEACON_WINDOW_S,
    MIRROR_UNKNOWN_SEND_FP_PREFIX,
    REPEAT_ATTRIBUTION_WINDOW,
    SEND_REPEAT_GAP,
    SIGNAL_CLUSTER_THRESHOLD,
    SIGNAL_RATE_LIMIT_PER_SEC,
    SIGNAL_REPEAT_SUPPRESS_MS,
    SIGNAL_WS_PUSH_RATE_LIMIT,
    TWEEZER_OBSERVER_ATTR,
)
from .event_parser import EventParser
from .ir_command import raw_to_pronto
from .models import CaptureResult, UnknownDevice, UnknownSignal
from .pronto_validator import validate_pronto
from .protocol_decode import try_decode_identity
from .signal_store import SignalStore
from .storage import HAIRStore

_LOGGER = logging.getLogger(__name__)


@dataclass
class NormalizedSignal:
    """Pure normalization output of the capture pipeline (Plucker, v0.5.0).

    The fingerprint / byte-hash / protocol-decode half of
    ``_process_parsed_signal``, split out so the Plucker can normalize a
    plucked ``Command`` without running the Sniffer's dedup / persist /
    live-feed pipeline.
    """

    protocol: str | None
    code: str | None
    raw_timings: list[int]
    frequency: int
    sig_fp: str
    device_address: str | None
    dev_fp: str
    byte_hash: str | None
    decoded_protocol: str | None
    decoded_address: int | None
    decoded_command: int | None
    decoded_fingerprint: str | None
    decoded_extras: dict[str, int] | None


def normalize(parsed: Any) -> NormalizedSignal:
    """Compute fingerprints, byte-hash, and protocol decode for a capture.

    Pure: no ``self`` / ``hass`` / store reference and no side effects.
    Extracted verbatim from ``_process_parsed_signal`` step 1; the
    route / store / push half stays in that method. Both the Sniffer
    pipeline and the Plucker call this, and Sniffer behavior is unchanged
    (same values computed in the same order).
    """
    sig_fp = EventParser.signal_fingerprint(
        parsed.protocol, parsed.code, parsed.raw_timings
    )
    device_address = EventParser.extract_device_address(
        parsed.protocol, parsed.code
    )
    dev_fp = EventParser.device_fingerprint(
        parsed.protocol, device_address, parsed.raw_timings,
        code=parsed.code,
    )
    # Byte-hash tiebreaker (v0.3.4): distinguishes two distinct commands
    # that collapse to the same S/L fingerprint (Panasonic, TCL, etc.).
    # None for non-Pronto codes, whose fingerprint is already unique.
    byte_hash = EventParser.pronto_byte_hash(parsed.code)
    # Protocol decode (v0.4.0 Phase A): identify NEC-family signals so the
    # matcher can key on the decoded fingerprint and the TX path can
    # re-encode canonical timings. None for undecodable signals or when the
    # library is unavailable.
    identity = try_decode_identity(parsed.raw_timings)
    return NormalizedSignal(
        protocol=parsed.protocol,
        code=parsed.code,
        raw_timings=list(parsed.raw_timings),
        frequency=getattr(parsed, "frequency", DEFAULT_CARRIER_FREQUENCY),
        sig_fp=sig_fp,
        device_address=device_address,
        dev_fp=dev_fp,
        byte_hash=byte_hash,
        decoded_protocol=identity.protocol if identity else None,
        decoded_address=identity.address if identity else None,
        decoded_command=identity.command if identity else None,
        decoded_fingerprint=identity.fingerprint if identity else None,
        decoded_extras=(
            dict(identity.extras) if identity and identity.extras else None
        ),
    )


def normalize_command(command: Any) -> NormalizedSignal:
    """Normalize an infrared ``Command`` captured by the HAIR Tweezer.

    Builds a ``CaptureResult`` from the Command's raw timings and modulation
    (mirroring ``EventParser.parse_received_signal``'s tail) and runs it
    through :func:`normalize`. Used by the Plucker only; never touches the
    Sniffer pipeline.
    """
    raw = list(command.get_raw_timings())
    frequency = (
        getattr(command, "modulation", None) or DEFAULT_CARRIER_FREQUENCY
    )
    parsed = CaptureResult(
        protocol="PRONTO",
        code=raw_to_pronto(raw, frequency=frequency),
        raw_timings=raw,
        frequency=frequency,
    )
    return normalize(parsed)


def _sl_fuzzy_substring_ratio(needle: str, haystack: str) -> float:
    """Edit-distance ratio of ``needle`` against the best-aligned
    substring of ``haystack``, normalized by ``len(needle)``.

    Standard fuzzy-substring DP: the match may start and end anywhere in
    ``haystack`` for free, so one metric covers every mangle shape the
    bench produced -- a truncated head (capture aligns mid-haystack), a
    merged tail (few substitutions), and short shards (small needle
    matching inside the full frame). 0.0 is a perfect substring; 1.0
    means every needle symbol had to be edited.
    """
    n, m = len(needle), len(haystack)
    if n == 0 or m == 0:
        return 1.0
    # prev[j] = min edits to match needle[:i] ending anywhere at haystack[:j].
    prev = [0] * (m + 1)  # free start: matching zero needle costs nothing
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if needle[i - 1] == haystack[j - 1] else 1
            cur[j] = min(
                prev[j - 1] + cost,  # sub / match
                prev[j] + 1,         # delete from needle
                cur[j - 1] + 1,      # insert from haystack
            )
        prev = cur
    return min(prev) / n  # free end


def _apply_signal_provenance(
    command,
    signal,
    *,
    send_count: int | None = None,
    repeat_count: int | None = None,
) -> None:
    """Carry identity from an UnknownSignal onto a newly-assigned IRCommand.

    Centralizes the per-field copy so a future addition to either dataclass
    is made in one place and cannot be half-added (the absent decoded_*
    copy on both assign paths is exactly the bug that produced this fix).

    Precedence on send_count:
      - an explicit WS arg (not None) wins, clamped to >= 1
      - None (the default, meaning the WS payload did not pass the field)
        falls back to signal.send_count, clamped to >= 1
      - a signal.send_count of 0 / falsy also falls back to 1

    Precedence on repeat_count (mirrors send_count):
      - an explicit WS arg (not None) wins, clamped to [0, MAX_DITTO_COUNT]
      - None (the default) falls back to signal.repeat_count

    The Optional sentinel is required for both because ``0 or X`` and ``1 or X``
    short-circuit under Python truthiness, so a truthy fallback cannot tell
    "caller passed 0/1" from "caller did not pass." observed_repeat_count is a
    capture-side observation and intentionally does NOT transfer.
    """
    command.byte_hash = signal.byte_hash
    command.decoded_protocol = signal.decoded_protocol
    command.decoded_address = signal.decoded_address
    command.decoded_command = signal.decoded_command
    command.decoded_fingerprint = signal.decoded_fingerprint
    command.decoded_extras = (
        dict(signal.decoded_extras) if signal.decoded_extras else None
    )
    if repeat_count is not None:
        command.repeat_count = max(0, min(int(repeat_count), MAX_DITTO_COUNT))
    else:
        command.repeat_count = signal.repeat_count
    if send_count is not None:
        command.send_count = max(1, send_count)
    else:
        command.send_count = max(1, signal.send_count or 1)
    command.plucked_command_name = signal.plucked_command_name


class SignalMonitor:
    """Core always-on IR signal listener.

    Lifecycle:
    - ``async_start()`` -- subscribe to HA event bus, load signal store.
    - ``async_stop()`` -- unsubscribe, flush pending writes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        signal_store: SignalStore,
        hair_store: HAIRStore,
        trigger_manager: Any | None = None,
    ) -> None:
        self._hass = hass
        self._signal_store = signal_store
        self._hair_store = hair_store
        self._trigger_manager = trigger_manager
        self._unsub: CALLBACK_TYPE | None = None
        self._unsubs: list[CALLBACK_TYPE] = []
        # Per-receiver subscription handles, keyed by entity_id (receiver
        # hot-plug, v0.5.8). Receivers are tracked DYNAMICALLY -- see
        # _reconcile_receivers -- so this dict grows and shrinks as
        # receiver entities appear and disappear; _unsubs keeps only the
        # non-per-receiver listeners (domain trackers, bridge tracking,
        # the started-once re-scan).
        self._receiver_subs: dict[str, CALLBACK_TYPE] = {}
        # Availability watcher over the current receiver inventory,
        # rewired at the end of every reconcile. This -- not the domain
        # add/remove trackers -- is what heals subscriptions across a
        # config entry reload: registry-registered entities are NEVER
        # state-removed on unload (HA writes an ``unavailable``
        # placeholder instead, verified live on 2026.7.2), so the reload
        # signal is the unavailable->available transition. Mirrors HA
        # core's own InfraredReceiverConsumerEntity, which drops its
        # subscription on unavailable and resubscribes on available.
        self._receiver_watch_unsub: CALLBACK_TYPE | None = None
        # --- The Mirror (v0.6.6): send expectations + emitter beacons ---
        # Expectations for HAIR's OWN sends: full identity known.
        # Each: {"decoded_fp", "sig_fp", "row_key", "expires", "cancel"}.
        self._echo_expectations: list[dict[str, Any]] = []
        # Foreign sends discovered via emitter state beacons: emitter ->
        # {"expires", "cancel", "label", "echoed"}.
        self._foreign_pending: dict[str, dict[str, Any]] = {}
        # Own-beacon suppression marks: emitter -> monotonic timestamp of
        # HAIR's most recent recorded send on that emitter.
        self._own_send_marks: dict[str, float] = {}
        self._beacon_unsub: CALLBACK_TYPE | None = None
        self._lock = asyncio.Lock()
        self._native_mode: bool = False

        # Rate limiting: fingerprint -> list of event timestamps (monotonic).
        self._rate_buckets: dict[str, list[float]] = defaultdict(list)

        # Repeat suppression: signal identity -> last event time (monotonic).
        # Keyed by (strongest identity, receiver_key): per-receiver so
        # cross-receiver captures of the same press are not dropped as
        # storage-path repeats (v0.5.7); identity is the strongest tier the
        # capture carries -- (tier, value) from SignalIdentity.strongest_key
        # -- so two different sub-threshold buttons in quick succession are
        # both stored, while a boundary protocol's fingerprint flip does
        # not defeat suppression (v0.5.8 unified identity).
        self._last_seen_times: dict[tuple[tuple[int, str], str], float] = {}

        # Per-device-fingerprint rate limit for the dismiss-activity bus
        # event push. Separate from ``_rate_buckets`` so the dismiss-activity
        # gate cannot consume budget from the in-feed signal path. Budget is
        # ``SIGNAL_WS_PUSH_RATE_LIMIT`` events / second / fingerprint, sliding
        # 1-second window. Keeps a held-down button on a dismissed remote
        # from flooding the WS channel with glow pulses.
        self._dismiss_push_buckets: dict[str, list[float]] = defaultdict(list)

        # Real-time subscribers (WebSocket push).
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []

        # HA device_ids that have fired ``esphome.remote_received`` events
        # since HA started. Populated lazily as bridge events arrive.
        # Used by ``capture.get_available_capture_providers`` to decide
        # whether to surface an ESPHome (legacy bridge) provider entry
        # for a given device. Resets on HA restart -- we have no way to
        # introspect the ESPHome YAML statically, so the only signal that
        # ``on_pronto:`` is configured is observing events.
        self._bridge_active_device_ids: set[str] = set()

        # Capture-side NEC ditto observation (v0.5.5). In-memory only; does
        # not persist across restarts.
        #
        # Per-receiver ditto anchors (v0.5.7). Keyed by receiver_entity_id, or
        # the "__legacy__" sentinel for legacy captures, so two receivers
        # observing the same physical press keep independent attribution
        # instead of corrupting a shared single anchor. Written synchronously
        # in _on_received_signal the moment a non-repeat signal arrives, then
        # filled with the persisted signal_id once _process_parsed_signal
        # completes, or removed if that path returns early.
        #   value (None, t, dev_fp)      -- main frame in flight (sentinel)
        #   value (signal_id, t, dev_fp) -- anchor live and writable
        # The dev_fp slot is unread today; kept for shape stability.
        self._ditto_anchor: dict[
            str, tuple[str | None, float, str | None]
        ] = {}
        # Running ditto count in the current burst, per receiver; reset on each
        # new main frame.
        self._ditto_running_count: dict[str, int] = {}
        # Timestamp of the most recent attributed ditto per receiver, for the
        # inter-frame gate. Key absent = no ditto yet in this burst.
        self._last_ditto_monotonic: dict[str, float] = {}

    @property
    def bridge_active_device_ids(self) -> set[str]:
        """Device IDs that have fired esphome.remote_received this session."""
        return self._bridge_active_device_ids

    # -----------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------

    async def async_start(self) -> None:
        """Start listening for IR events.

        Native path (HA 2026.6+): receivers are tracked DYNAMICALLY. Two
        separate questions used to be conflated here, and the difference
        is the blalor hot-plug/cold-boot bug class:

        - *Does this HA ship the native receiver API?* A capability
          question, stable for the process lifetime, answered by whether
          the import succeeds. This -- and ONLY this -- selects legacy
          mode (HA 2026.4-2026.5, ``_start_legacy_event_bus``).
        - *Are any receivers present right now?* A transient inventory
          question whose answer can legitimately be "none yet" (cold-boot
          ordering, proxy added later). Inventory is handled by
          ``_reconcile_receivers`` and the domain trackers, never by
          falling back to the legacy bus -- the old empty-inventory
          fallback latched HAIR onto a channel our shipped YAML does not
          even emit, permanently, until a manual reload.

        Even when the native path is active, we also wire a tracking-only
        listener on ``esphome.remote_received`` so the Receivers UI can
        surface ``RX-BRIDGE`` for devices that still have ``on_pronto:``
        YAML configured alongside their native receiver (this now also
        covers the native-with-zero-receivers wait state). In legacy mode
        the main ``_on_ir_event`` handler already records device_ids as
        part of its processing, so we don't double-subscribe.
        """
        if not self._signal_store.loaded:
            await self._signal_store.async_load()

        # The Mirror (v0.6.6): every platform send flips its emitter's
        # state to the send timestamp (core's @final bookkeeping), so a
        # state_changed on an infrared emitter is a send beacon -- which
        # emitter, exactly when -- for ANY integration's transmissions.
        self._beacon_unsub = self._hass.bus.async_listen(
            "state_changed", self._on_emitter_beacon
        )

        try:
            # Capability probe only -- no inventory consulted, nothing
            # subscribed here. Raises ImportError on HA 2026.4-2026.5,
            # where the infrared component lacks the receiver API.
            from homeassistant.components.infrared import (  # noqa: F401
                async_subscribe_receiver,
            )
        except ImportError:
            self._start_legacy_event_bus()
        else:
            self._start_native_tracking()

        if self._native_mode:
            unsub = self._hass.bus.async_listen(
                LEGACY_ESPHOME_IR_EVENT, self._on_bridge_tracking_event
            )
            self._unsubs.append(unsub)

    @callback
    def _on_bridge_tracking_event(self, event: Event) -> None:
        """Record bridge-active device_ids alongside native mode.

        Native mode handles signal processing via the receiver subscription;
        this listener exists purely so the UI can show ``RX-BRIDGE`` for
        ESPHome devices that still emit legacy bus events from a residual
        ``on_pronto:`` YAML block. Cheap; runs in the event loop.

        Native mode with ZERO receivers plus bridge activity is a special
        case worth shouting about: the device is emitting legacy events
        that nothing is processing (the native path owns processing, and
        it has no receivers). That is an old-firmware/old-YAML device on
        a modern HA -- tell the user, once per device, instead of letting
        the Sniffer silently show nothing.
        """
        device_id = (event.data or {}).get("device_id")
        if isinstance(device_id, str) and device_id:
            if (
                device_id not in self._bridge_active_device_ids
                and not self._receiver_subs
            ):
                _LOGGER.warning(
                    "ESPHome device %s is emitting legacy on_pronto bus "
                    "events, but no native receiver entity is subscribed, "
                    "so its signals are NOT being processed. On HA 2026.6+ "
                    "update the device's ESPHome YAML/firmware to the "
                    "native receiver platform (see HAIR's esphome/ "
                    "examples)",
                    device_id,
                )
            self._bridge_active_device_ids.add(device_id)

    @callback
    def _start_native_tracking(self) -> None:
        """Enter native mode and track receiver entities dynamically.

        ``_native_mode`` means exactly "we are on the native path" -- it is
        set here unconditionally, receivers present or not. The infrared
        component exposes no dispatcher signal or hook for receivers
        appearing (verified against HA 2026.7 source), so inventory is
        tracked the way HA core's own ``InfraredConsumerEntity`` does it:
        through the state machine, via the domain add/remove trackers.

        Ordering matters: the trackers are wired BEFORE the first
        reconcile, so a receiver registering in between is caught by the
        tracker instead of falling into a snapshot-vs-listener gap. The
        ``EVENT_HOMEASSISTANT_STARTED`` re-scan is belt-and-braces for
        cold boots (and guarded, so a config entry added at runtime does
        not wait on an event that already fired).
        """
        self._native_mode = True
        self._unsubs.append(
            async_track_state_added_domain(
                self._hass, "infrared", self._on_infrared_entity_added
            )
        )
        self._unsubs.append(
            async_track_state_removed_domain(
                self._hass, "infrared", self._on_infrared_entity_removed
            )
        )
        if self._hass.state is not CoreState.running:
            self._unsubs.append(
                self._hass.bus.async_listen_once(
                    EVENT_HOMEASSISTANT_STARTED, self._on_hass_started
                )
            )
        self._reconcile_receivers()
        if self._receiver_subs:
            _LOGGER.info(
                "Signal monitor started (native mode, %d receiver(s))",
                len(self._receiver_subs),
            )
        else:
            _LOGGER.info(
                "Signal monitor started (native mode); no receivers "
                "present yet, waiting for one to appear"
            )

    @callback
    def _on_hass_started(self, _event: Event) -> None:
        """Re-scan for receivers once Home Assistant finishes starting."""
        self._reconcile_receivers()

    @callback
    def _on_infrared_entity_added(self, event: Event) -> None:
        """An infrared-domain entity appeared in the state machine.

        Fires for emitters too (Tuya, Broadlink, HAIR's own Tweezer);
        harmless, because reconcile filters through
        ``async_get_receivers``. This tracker only sees BRAND-NEW
        entities (old_state None) -- a config entry reload does NOT fire
        it, because registered entities keep an ``unavailable`` state
        placeholder across unload; the reload heal lives in
        ``_on_receiver_availability_change``. The release-first branch
        below is defensive belt-and-braces for any path where an added
        event arrives for an id we still track.
        """
        entity_id = (event.data or {}).get("entity_id")
        if entity_id in self._receiver_subs:
            self._release_receiver(entity_id)
        self._reconcile_receivers()

    @callback
    def _on_infrared_entity_removed(self, event: Event) -> None:
        """An infrared-domain entity left the state machine.

        Only genuine removal from the state machine fires this -- an
        entity deleted outright, or removed from the entity registry.
        Config entry unload/reload does NOT: registered entities keep an
        ``unavailable`` placeholder (that transition is handled by
        ``_on_receiver_availability_change`` instead).
        """
        entity_id = (event.data or {}).get("entity_id")
        if entity_id in self._receiver_subs:
            self._release_receiver(entity_id)

    @callback
    def _reconcile_receivers(self) -> None:
        """Bring receiver subscriptions in line with the current inventory.

        Idempotent and cheap; safe to call from any path (initial start,
        domain trackers, the started-once re-scan). Subscribes every
        receiver not yet tracked and releases every tracked id no longer
        listed. One bad entity cannot abort the loop -- and can NEVER
        route us onto the legacy bus.
        """
        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_get_receivers,
            async_subscribe_receiver,
        )

        try:
            current = set(async_get_receivers(self._hass))
        except Exception:
            # Never fail setup (or a tracker callback) on a bad scan; the
            # trackers and the started-once re-scan retry naturally. And
            # never, ever select legacy mode from here.
            _LOGGER.warning(
                "Receiver inventory scan failed; will retry on the next "
                "reconcile",
                exc_info=True,
            )
            return
        states = self._hass.states
        for entity_id in [e for e in self._receiver_subs if e not in current]:
            self._release_receiver(entity_id)
        for entity_id in sorted(current - set(self._receiver_subs)):
            state = states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                # Mirror core's consumer entity: never subscribe to an
                # unavailable receiver (its object may be mid-teardown).
                # The availability watcher below subscribes it the moment
                # it comes (back) up.
                continue
            try:
                # rid=... binds the loop var by value (avoids late-binding)
                # and threads the capturing receiver's entity_id into the
                # callback so location-aware triggers know where the signal
                # was received.
                unsub = async_subscribe_receiver(
                    self._hass,
                    entity_id,
                    lambda sig, rid=entity_id: self._on_received_signal(
                        sig, rid
                    ),
                )
            except Exception:
                # HomeAssistantError when the entity is missing or not a
                # receiver (it may still be registering). Skip it; the
                # added-domain tracker will bring it back when it settles.
                _LOGGER.warning(
                    "Could not subscribe to receiver %s; skipping",
                    entity_id,
                    exc_info=True,
                )
                continue
            self._receiver_subs[entity_id] = unsub
            _LOGGER.debug("Subscribed to receiver %s", entity_id)

        # (Re)wire the availability watcher over the full inventory,
        # available or not -- unavailable receivers are exactly the ones
        # we need to hear come up.
        if self._receiver_watch_unsub is not None:
            self._receiver_watch_unsub()
            self._receiver_watch_unsub = None
        if current:
            self._receiver_watch_unsub = async_track_state_change_event(
                self._hass, sorted(current), self._on_receiver_availability_change
            )

    @callback
    def _on_receiver_availability_change(self, event: Event) -> None:
        """A tracked receiver's state changed; manage its subscription.

        The reload/ghost heal (mirrors HA core's
        ``InfraredReceiverConsumerEntity``): a receiver going
        ``unavailable`` has its subscription released -- across a config
        entry reload the entity object is about to be replaced, and a
        handle bound to the dead object would otherwise look "covered"
        forever. When it transitions back to available, subscribe fresh,
        which resolves the CURRENT entity object. Ordinary value updates
        (every received signal bumps the receiver's state) return on the
        cheap path.
        """
        data = event.data or {}
        entity_id = data.get("entity_id")
        new_state = data.get("new_state")
        available = (
            new_state is not None and new_state.state != STATE_UNAVAILABLE
        )
        if not available:
            if entity_id in self._receiver_subs:
                self._release_receiver(entity_id)
            return
        if entity_id not in self._receiver_subs:
            self._reconcile_receivers()

    @callback
    def _release_receiver(self, entity_id: str) -> None:
        """Release one receiver subscription and purge its state.

        The v0.5.7 in-flight ditto attribution is keyed per receiver; a
        fresh entity object must never inherit a stale anchor. Repeat
        suppression is keyed ``((tier, value), receiver_key)`` (v0.5.8
        unified identity) and its entries expire in
        ``SIGNAL_REPEAT_SUPPRESS_MS`` anyway, but the sweep bounds growth
        across many reload cycles.
        """
        unsub = self._receiver_subs.pop(entity_id, None)
        if unsub is not None:
            with contextlib.suppress(Exception):
                unsub()
        self._ditto_anchor.pop(entity_id, None)
        self._ditto_running_count.pop(entity_id, None)
        self._last_ditto_monotonic.pop(entity_id, None)
        for key in [k for k in self._last_seen_times if k[1] == entity_id]:
            del self._last_seen_times[key]
        _LOGGER.debug("Released receiver subscription for %s", entity_id)

    def _start_legacy_event_bus(self) -> None:
        """Subscribe to ``esphome.remote_received`` events (legacy path)."""
        self._unsub = self._hass.bus.async_listen(
            LEGACY_ESPHOME_IR_EVENT, self._on_ir_event
        )
        self._native_mode = False
        _LOGGER.info("Signal monitor started (legacy event bus mode)")

    @property
    def native_mode(self) -> bool:
        """Return True if using native receiver API."""
        return self._native_mode

    @property
    def has_receivers(self) -> bool:
        """Whether HAIR currently has any working receive path.

        True when at least one native receiver is actually subscribed, or
        at least one ESPHome bridge has fired an event this session. Note
        this is subscription presence, not mode (v0.5.8 hot-plug): native
        mode with zero receivers genuinely cannot receive, and the
        Sniffer's empty state should say "no receiver is set up" rather
        than implying the user simply has not pressed a button yet.
        """
        return bool(self._receiver_subs) or bool(self._bridge_active_device_ids)

    async def async_stop(self) -> None:
        """Stop listening, flush pending writes."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        for entity_id in list(self._receiver_subs):
            self._release_receiver(entity_id)
        if self._receiver_watch_unsub is not None:
            self._receiver_watch_unsub()
            self._receiver_watch_unsub = None
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._beacon_unsub is not None:
            self._beacon_unsub()
            self._beacon_unsub = None
        for exp in self._echo_expectations:
            cancel = exp.get("cancel")
            if cancel is not None:
                cancel.cancel()
        self._echo_expectations.clear()
        for pending in self._foreign_pending.values():
            cancel = pending.get("cancel")
            if cancel is not None:
                cancel.cancel()
        self._foreign_pending.clear()
        await self._signal_store.async_shutdown()
        _LOGGER.info("Signal monitor stopped")


    # -----------------------------------------------------------------
    # The Mirror (v0.6.6): send audit + echo attribution
    # -----------------------------------------------------------------

    def record_send(
        self,
        command: Any,
        source_label: str,
        emitter_entity_ids: list[str],
        decoded_fingerprint: str | None = None,
    ) -> None:
        """Log an outgoing HAIR transmission on the Mirror, send-time.

        Called by the device TX path and the catalog Test path with the
        actual Command object being transmitted. Creates or bumps the
        Mirror row immediately (a send is a fact whether or not anyone
        hears it), resets its heard_by window, registers an echo
        expectation so arriving captures attribute here instead of
        entering the Sniffer pipeline, and arms the own-beacon
        suppression so this send's emitter state flip is not mistaken
        for a foreign integration's transmission.
        """
        try:
            n = normalize_command(command)
        except Exception:  # never let audit bookkeeping break a send
            _LOGGER.exception("Mirror: failed to normalize outgoing command")
            return
        decoded_fp = decoded_fingerprint or n.decoded_fingerprint
        emitters = ", ".join(
            self._friendly_name(e) for e in emitter_entity_ids
        ) or "unknown emitter"
        label = f"{source_label} -- via {emitters}"
        now = monotonic()
        for entity_id in emitter_entity_ids:
            self._own_send_marks[entity_id] = now

        row_key = decoded_fp or n.sig_fp
        self._hass.async_create_task(
            self._mirror_upsert(
                n,
                decoded_fp=decoded_fp,
                echo_source=label,
                reset_heard=True,
            )
        )

        expectation: dict[str, Any] = {
            "decoded_fp": decoded_fp,
            "sig_fp": n.sig_fp,
            "row_key": row_key,
            "expires": now + MIRROR_ECHO_TTL_S,
            # The transmitted frame's S/L pattern, for the garbled-echo
            # swallow: a damaged echo misses both identity claims, but
            # its shape still resembles what we just sent. Lives a bit
            # longer than the identity claim (the beacon window clock --
            # a queued Broadlink can blast later than the echo TTL, and
            # the bench proved it).
            "sl": EventParser._pronto_sl_pattern(n.code),
            "garble_expires": now + MIRROR_OWN_BEACON_WINDOW_S,
            "cancel": None,
        }
        self._echo_expectations.append(expectation)

        def _expire() -> None:
            if expectation in self._echo_expectations:
                self._echo_expectations.remove(expectation)

        expectation["cancel"] = self._hass.loop.call_later(
            max(MIRROR_ECHO_TTL_S, MIRROR_OWN_BEACON_WINDOW_S), _expire
        )

    def _friendly_name(self, entity_id: str) -> str:
        state = self._hass.states.get(entity_id)
        if state is not None:
            name = state.attributes.get("friendly_name")
            if name:
                return str(name)
        return entity_id

    @callback
    def _on_emitter_beacon(self, event: Any) -> None:
        """A state change on an infrared emitter is a send beacon.

        Core's ``async_send_command_internal`` is @final and writes the
        emitter's state as the send timestamp on EVERY platform send, so
        this catches transmissions from any integration -- including
        ones that call the Python helper directly and therefore never
        produce service events. HAIR's own sends are filtered by the
        own-beacon window; the Tweezer never transmits and is filtered
        by its observer marker attribute.
        """
        data = event.data
        entity_id = data.get("entity_id") or ""
        if not entity_id.startswith("infrared."):
            return
        new_state = data.get("new_state")
        old_state = data.get("old_state")
        if new_state is None or old_state is None:
            return  # startup restore / removal, not a send
        attrs = getattr(new_state, "attributes", {}) or {}
        if attrs.get("device_class") != "emitter":
            return
        if attrs.get(TWEEZER_OBSERVER_ATTR):
            return  # the Tweezer observes; it does not transmit
        if new_state.state in (None, "unknown", "unavailable"):
            return
        # A transition FROM unavailable/unknown is the entity coming back
        # (integration reload, device reconnect, startup restore) -- the
        # state write is the restored last-send timestamp, not a new send.
        # Without this guard every Broadlink reconnect blip would mint a
        # phantom "unknown send" row (found chasing a bench artifact:
        # the integration reasserting its real state over a Dev Tools
        # override fires the same shape of not-a-send transition).
        if getattr(old_state, "state", None) in (
            None, "unknown", "unavailable",
        ):
            return
        if new_state.state == getattr(old_state, "state", None):
            return
        now = monotonic()
        own_mark = self._own_send_marks.get(entity_id)
        if own_mark is not None and now - own_mark < MIRROR_OWN_BEACON_WINDOW_S:
            return  # HAIR's own send; already recorded with full identity

        # Foreign send: emitter + moment known, identity only via echo.
        pending = self._foreign_pending.get(entity_id)
        if pending is not None and pending.get("cancel") is not None:
            pending["cancel"].cancel()
        context = getattr(event, "context", None)
        caused = "automation send" if getattr(
            context, "parent_id", None
        ) else "integration send"
        record: dict[str, Any] = {
            "expires": now + MIRROR_ECHO_TTL_S,
            "label": caused,
            "echoed": False,
            "cancel": None,
        }
        self._foreign_pending[entity_id] = record

        def _expire() -> None:
            current = self._foreign_pending.get(entity_id)
            if current is not record:
                return
            self._foreign_pending.pop(entity_id, None)
            if not record["echoed"]:
                # Sent, never heard, identity unknown: still audited.
                self._hass.async_create_task(
                    self._mirror_upsert_unknown(entity_id, record["label"])
                )

        record["cancel"] = self._hass.loop.call_later(
            MIRROR_ECHO_TTL_S, _expire
        )

    async def _match_echo(
        self, n: NormalizedSignal, receiver_entity_id: str | None
    ) -> bool:
        """Claim an arriving capture as an echo of a known send.

        HAIR's precise identity expectations claim first; foreign
        beacon windows second. A claimed capture is routed to the
        Mirror (heard_by enrichment) and never enters the trigger /
        catalog pipeline. Returns True when claimed.
        """
        now = monotonic()
        for exp in list(self._echo_expectations):
            if now > exp["expires"]:
                continue
            matched = (
                exp["decoded_fp"] is not None
                and n.decoded_fingerprint == exp["decoded_fp"]
            ) or n.sig_fp == exp["sig_fp"]
            if matched:
                await self._mirror_mark_heard(exp["row_key"], receiver_entity_id)
                return True
        for entity_id, pending in list(self._foreign_pending.items()):
            if now > pending["expires"]:
                continue
            # One identity-minting claim per beacon. Without this, a
            # pending window kept eating every capture for its full TTL,
            # one Mirror row each -- and a send whose echo arrives as
            # several mangled fragments minted a junk row per fragment
            # (bench find, v0.6.6). The first arrival is the send's
            # identity; later fragments fall through to the Sniffer as
            # ordinary capture noise, exactly as they did pre-Mirror.
            pending["echoed"] = True
            if pending.get("cancel") is not None:
                pending["cancel"].cancel()
            self._foreign_pending.pop(entity_id, None)
            label = (
                f"{pending['label']} -- via {self._friendly_name(entity_id)}"
            )
            await self._mirror_upsert(
                n,
                decoded_fp=n.decoded_fingerprint,
                echo_source=label,
                reset_heard=True,
                heard=receiver_entity_id,
            )
            return True

        # Last resort: the garbled-echo swallow (owner design, shampoo).
        # HAIR's own send coming back damaged -- merged tail, truncated
        # head, shard -- misses both identity claims above and used to
        # mint a junk Sniffer row per mangle (bench: dual-emitter and
        # RC-5 replay cases). If the capture is UNDECODABLE and its S/L
        # shape fuzzy-matches something we transmitted inside the window,
        # it is our own voice bouncing back: mark the send heard (a
        # mangled echo still proves the LED fired) and swallow it.
        # Captures that decode cleanly NEVER land here -- a clean decode
        # with a non-matching fingerprint is a real, different signal,
        # so pressing candles-off right after testing candles-on is safe.
        # Residual, accepted: an undecodable FOREIGN press that both
        # lands in the ~3s window and resembles our transmission is
        # swallowed too; it reappears on the next press.
        if n.decoded_fingerprint is None:
            cap_sl = EventParser._pronto_sl_pattern(n.code)
            if cap_sl:
                for exp in list(self._echo_expectations):
                    exp_sl = exp.get("sl")
                    if not exp_sl or now > exp["garble_expires"]:
                        continue
                    ratio = _sl_fuzzy_substring_ratio(cap_sl, exp_sl)
                    if ratio <= ECHO_GARBLE_SIMILARITY:
                        _LOGGER.debug(
                            "Mirror: swallowed garbled echo (ratio %.2f)"
                            " for send %s",
                            ratio,
                            exp["row_key"],
                        )
                        await self._mirror_mark_heard(
                            exp["row_key"], receiver_entity_id
                        )
                        return True
        return False

    async def _mirror_device(self) -> UnknownDevice:
        device = self._signal_store.get_device_by_fingerprint(MIRROR_DEVICE_FP)
        if device is None:
            device = UnknownDevice(
                fingerprint=MIRROR_DEVICE_FP,
                protocol=None,
                device_address=None,
                label=MIRROR_DEVICE_LABEL,
                source="echo",
            )
            self._signal_store.add_device(device)
        return device

    async def _mirror_upsert(
        self,
        n: NormalizedSignal,
        decoded_fp: str | None,
        echo_source: str,
        reset_heard: bool,
        heard: str | None = None,
    ) -> None:
        """Create or bump a Mirror row keyed by the send's identity."""
        now_iso = datetime.now(UTC).isoformat()
        async with self._lock:
            device = await self._mirror_device()
            signal = device.get_signal(
                n.sig_fp, n.byte_hash, decoded_fp
            )
            if signal is None:
                signal = UnknownSignal(
                    fingerprint=n.sig_fp,
                    byte_hash=n.byte_hash,
                    decoded_protocol=n.decoded_protocol,
                    decoded_address=n.decoded_address,
                    decoded_command=n.decoded_command,
                    decoded_fingerprint=decoded_fp,
                    decoded_extras=(
                        dict(n.decoded_extras) if n.decoded_extras else None
                    ),
                    protocol=n.protocol,
                    code=n.code,
                    raw_timings=list(n.raw_timings),
                    frequency=n.frequency,
                    source="echo",
                    heard_by=[],
                )
                device.signals.insert(0, signal)
            signal.hit_count += 1
            signal.last_seen = now_iso
            signal.echo_source = echo_source
            if reset_heard:
                signal.heard_by = []
            if heard and heard not in (signal.heard_by or []):
                signal.heard_by = [*(signal.heard_by or []), heard]
            device.hit_count += 1
            device.last_seen = now_iso
            summary = self._mirror_summary(device, signal)
        self._signal_store.schedule_save()
        self._hass.bus.async_fire(EVENT_SIGNAL_DETECTED, summary)
        self._notify_subscribers(summary)

    async def _mirror_mark_heard(
        self, row_key: str, receiver_entity_id: str | None
    ) -> None:
        """Append a receiver to the expected send's heard_by list."""
        if receiver_entity_id is None:
            receiver_entity_id = "legacy receiver"
        async with self._lock:
            device = self._signal_store.get_device_by_fingerprint(
                MIRROR_DEVICE_FP
            )
            if device is None:
                return
            signal = None
            for candidate in device.signals:
                if (
                    candidate.decoded_fingerprint == row_key
                    or candidate.fingerprint == row_key
                ):
                    signal = candidate
                    break
            if signal is None:
                return
            if receiver_entity_id not in (signal.heard_by or []):
                signal.heard_by = [
                    *(signal.heard_by or []),
                    receiver_entity_id,
                ]
            summary = self._mirror_summary(device, signal)
        self._signal_store.schedule_save()
        self._hass.bus.async_fire(EVENT_SIGNAL_DETECTED, summary)
        self._notify_subscribers(summary)

    async def _mirror_upsert_unknown(
        self, emitter_entity_id: str, label: str
    ) -> None:
        """A foreign send no receiver heard: audited, identity unknown."""
        now_iso = datetime.now(UTC).isoformat()
        sig_fp = f"{MIRROR_UNKNOWN_SEND_FP_PREFIX}{emitter_entity_id}"
        friendly = self._friendly_name(emitter_entity_id)
        async with self._lock:
            device = await self._mirror_device()
            signal = device.get_signal(sig_fp)
            if signal is None:
                # No alias: the frontend recognizes these rows by their
                # fingerprint prefix and titles them itself ("Unknown IR
                # signal sent" + the place-a-receiver hint). The old
                # backend-stamped alias "Unknown send" defeated that
                # detection -- the title chain honors alias first, so the
                # row kept rendering the pre-hint way (bench catch,
                # shampoo: served bundle was current, row still looked
                # old). Rows persisted with the legacy alias are mapped
                # by the frontend.
                signal = UnknownSignal(
                    fingerprint=sig_fp,
                    source="echo",
                    heard_by=[],
                )
                device.signals.insert(0, signal)
            signal.hit_count += 1
            signal.last_seen = now_iso
            signal.echo_source = f"{label} -- via {friendly}"
            signal.heard_by = []
            device.hit_count += 1
            device.last_seen = now_iso
            summary = self._mirror_summary(device, signal)
        self._signal_store.schedule_save()
        self._hass.bus.async_fire(EVENT_SIGNAL_DETECTED, summary)
        self._notify_subscribers(summary)

    def _mirror_summary(
        self, device: UnknownDevice, signal: UnknownSignal
    ) -> dict[str, Any]:
        return {
            "device_id": device.id,
            "device_fingerprint": device.fingerprint,
            "signal_id": signal.id,
            "signal_fingerprint": signal.fingerprint,
            "protocol": signal.protocol,
            "code": signal.code,
            "hit_count": signal.hit_count,
            "device_hit_count": device.hit_count,
        }

    def _notify_subscribers(self, summary: dict[str, Any]) -> None:
        for subscriber in self._subscribers:
            try:
                subscriber(summary)
            except Exception:
                _LOGGER.exception("Error notifying signal subscriber")

    # -----------------------------------------------------------------
    # Event handler
    # -----------------------------------------------------------------

    async def _on_ir_event(self, event: Event) -> None:
        """Handle an incoming IR event from the HA bus (legacy path).

        Parses the ESPHome event dict and delegates to the shared
        processing pipeline. Also records the source device_id so the
        Receivers UI can surface ``RX-BRIDGE`` only for devices that
        actually still have ``on_pronto:`` configured -- the only way to
        detect bridge presence is to observe events from it.
        """
        # Drop events forged through the HA API. ESPHome-originated bus
        # events carry no user context; a non-None ``user_id`` means an
        # authenticated user (admin or not) fired this event via the
        # WS/REST API. Since processing runs trigger matching before any
        # filtering, an unguarded handler lets a non-admin user fire HAIR
        # event entities (and any automations bound to them). Reject such
        # events before they touch bridge tracking or the pipeline.
        if event.context.user_id is not None:
            return

        event_data = event.data or {}

        # Track this device as having an active bridge (regardless of
        # whether the signal passes downstream filters).
        device_id = event_data.get("device_id")
        if isinstance(device_id, str) and device_id:
            if (
                device_id not in self._bridge_active_device_ids
                and not self._receiver_subs
            ):
                _LOGGER.warning(
                    "ESPHome device %s is emitting legacy on_pronto bus "
                    "events, but no native receiver entity is subscribed, "
                    "so its signals are NOT being processed. On HA 2026.6+ "
                    "update the device's ESPHome YAML/firmware to the "
                    "native receiver platform (see HAIR's esphome/ "
                    "examples)",
                    device_id,
                )
            self._bridge_active_device_ids.add(device_id)

        # Filter out repeat frames (no command data).
        # TODO(v0.6.0): ditto observation (v0.5.5) is native-only. If a
        # legacy-bridge user requests it, the same anchor / counter / max-merge
        # pattern from _on_received_signal applies here -- attribute the NEC
        # repeat instead of dropping it. Held until the legacy bridge phase-out
        # decision lands.
        if EventParser.is_nec_repeat(event_data):
            return
        if EventParser.is_pronto_repeat(event_data):
            return
        parsed = EventParser.parse(event_data)
        if parsed is None:
            return

        # Legacy captures cannot reliably map to an infrared.* receiver entity,
        # so scoped triggers will not match them; unscoped triggers still fire.
        await self._process_parsed_signal(parsed, receiver_entity_id=None)

    async def _process_parsed_signal(
        self, parsed: Any, receiver_entity_id: str | None = None
    ) -> None:
        """Shared signal processing pipeline for both native and legacy paths.

        Steps:
        1. Compute fingerprints
        2. Echo claim (the Mirror, v0.6.6): a capture matching a known
           send's expectation or a foreign beacon window is the house
           hearing itself -- routed to the Mirror, never to triggers or
           the catalog.
        3. Check triggers
        4. Check dismiss list
        5. Rate limit check
        6. Repeat suppression check
        7-9. Find/create device + signal (under lock)
        10. Schedule save
        11. Fire HA event
        12. Notify subscribers
        """
        # Per-receiver key for ditto attribution + repeat suppression (v0.5.7).
        rid_key = receiver_entity_id or "__legacy__"

        # Step 1: Compute fingerprints + byte-hash + protocol decode. This
        # pure normalization lives in the module-level normalize() so the
        # Plucker can reuse it without the route/store/push half below.
        # Rebound to locals to keep the downstream pipeline verbatim.
        n = normalize(parsed)
        sig_fp = n.sig_fp
        device_address = n.device_address
        dev_fp = n.dev_fp
        byte_hash = n.byte_hash
        decoded_protocol = n.decoded_protocol
        decoded_address = n.decoded_address
        decoded_command = n.decoded_command
        decoded_fingerprint = n.decoded_fingerprint
        decoded_extras = n.decoded_extras

        # Step 2: Echo claim (v0.6.6). BEFORE triggers, so the house's
        # own transmissions never fire them (the feedback-loop class) and
        # never pollute the human-press catalog. Claimed captures enrich
        # the Mirror's heard_by instead.
        if await self._match_echo(n, receiver_entity_id):
            self._ditto_anchor.pop(rid_key, None)
            return

        # Step 3: Check triggers. Threads the capturing receiver so scoped
        # triggers can match and the payload carries receiver + area
        # (v0.5.7).
        if self._trigger_manager is not None:
            self._trigger_manager.on_signal_captured(
                sig_fp, parsed.protocol, parsed.code, dev_fp,
                receiver_entity_id, byte_hash, decoded_fingerprint,
            )

        # The v0.4.0 known-command suppression is GONE (v0.6.6, "heard
        # means shown"): a human pressing an assigned button is Sniffer
        # activity like any other press -- the row flashes, counts, and
        # persists forever. Deleted rows resurrect on re-hearing; DISMISS
        # is the one and only hiding tool. The echo claim above now covers
        # the only thing the suppression was ever really for: keeping the
        # house's own transmissions out of the human-press feed.

        # Step 4: Check dismiss list.
        if self._signal_store.is_dismissed(dev_fp):
            # Signal is from a dismissed remote and gets dropped from the
            # live feed. Before the early-return, push a lightweight bus
            # event so the Sniffer's "Show Dismissed" button can glow and
            # surface a dot indicator. Payload is fingerprint-only -- we
            # deliberately do NOT include the signal code, raw timings, or
            # any storage-bound metadata because the signal itself is not
            # being stored. Rate-limited per-fingerprint via the dedicated
            # ``_dismiss_push_buckets`` so a held-down button does not flood
            # the WS channel.
            if self._check_dismiss_push_rate(dev_fp):
                self._hass.bus.async_fire(
                    EVENT_DISMISS_ACTIVITY,
                    {"device_fingerprint": dev_fp},
                )
            self._ditto_anchor.pop(rid_key, None)  # invalidate this receiver's sentinel
            return

        # Step 5: Rate limit.
        if not self._check_rate_limit(sig_fp):
            self._ditto_anchor.pop(rid_key, None)  # invalidate this receiver's sentinel
            return

        # Step 6: Repeat suppression (per receiver, so cross-receiver captures
        # of the same press are not dropped as storage-path repeats).
        if not self._check_repeat(
            sig_fp, receiver_entity_id, byte_hash, decoded_fingerprint
        ):
            self._ditto_anchor.pop(rid_key, None)  # invalidate this receiver's sentinel
            return

        # Steps 7-9: Find/create device and signal (locked).
        now_iso = datetime.now(UTC).isoformat()
        async with self._lock:
            device = self._signal_store.get_device_by_fingerprint(dev_fp)
            if device is None:
                next_num = len(self._signal_store.get_all_devices()) + 1
                device = UnknownDevice(
                    fingerprint=dev_fp,
                    protocol=parsed.protocol,
                    device_address=device_address,
                    label=f"Remote {next_num}",
                    first_seen=now_iso,
                    last_seen=now_iso,
                    hit_count=0,
                )
                self._signal_store.add_device(device)

            signal = device.get_signal(sig_fp, byte_hash, decoded_fingerprint)
            if signal is None:
                signal = UnknownSignal(
                    fingerprint=sig_fp,
                    byte_hash=byte_hash,
                    decoded_protocol=decoded_protocol,
                    decoded_address=decoded_address,
                    decoded_command=decoded_command,
                    decoded_fingerprint=decoded_fingerprint,
                    decoded_extras=(
                        dict(decoded_extras) if decoded_extras else None
                    ),
                    protocol=parsed.protocol,
                    code=parsed.code,
                    raw_timings=list(parsed.raw_timings) if parsed.raw_timings else [],
                    frequency=parsed.frequency,
                    first_seen=now_iso,
                    last_seen=now_iso,
                    hit_count=0,
                )
                # New signal goes on top of the remote's list so the
                # just-pressed button surfaces; existing signals keep
                # their position (only hit_count updates below).
                device.signals.insert(0, signal)

            signal.hit_count += 1
            signal.last_seen = now_iso
            device.hit_count += 1
            device.last_seen = now_iso

            # Evict if over buffer.
            if self._signal_store.device_count > 500:
                self._signal_store.evict()

        # Capture observation (v0.5.5): confirm the ditto anchor by writing in
        # the persisted signal_id. The timestamp and dev_fp came from the sync
        # entry point and are still correct. If the sentinel was already
        # invalidated (an early return, or a racing main frame), do not
        # resurrect it -- the next press starts a fresh anchor.
        anchor = self._ditto_anchor.get(rid_key)
        if anchor is not None:
            _, t_anchor, dev_fp_anchor = anchor
            self._ditto_anchor[rid_key] = (signal.id, t_anchor, dev_fp_anchor)

        # Step 10: Schedule save.
        self._signal_store.schedule_save()

        # Step 11: Fire HA event.
        summary = {
            "device_id": device.id,
            "device_fingerprint": dev_fp,
            "signal_id": signal.id,
            "signal_fingerprint": sig_fp,
            "protocol": parsed.protocol,
            "code": parsed.code,
            "hit_count": signal.hit_count,
            "device_hit_count": device.hit_count,
        }
        self._hass.bus.async_fire(EVENT_SIGNAL_DETECTED, summary)

        # Step 12: Notify subscribers.
        for subscriber in self._subscribers:
            try:
                subscriber(summary)
            except Exception:
                _LOGGER.exception("Error notifying signal subscriber")

    # -----------------------------------------------------------------
    # Native receiver callback (HA 2026.6+)
    # -----------------------------------------------------------------

    def _on_received_signal(
        self, signal: Any, receiver_entity_id: str | None = None
    ) -> None:
        """Handle a signal from the native ``InfraredReceiverEntity`` API.

        Called synchronously by HA's ``@callback`` subscription system.
        ``receiver_entity_id`` is threaded in by the per-receiver subscription
        closure so ditto attribution and location-aware triggers know which
        receiver captured the signal.
        """
        rid_key = receiver_entity_id or "__legacy__"
        # NEC ditto (short repeat frame): attribute it to the most recent main
        # frame on the SAME receiver instead of dropping it (v0.5.5/0.5.7).
        if EventParser.is_native_repeat(signal):
            self._maybe_attribute_repeat_frame(rid_key)
            return

        parsed = EventParser.parse_received_signal(signal)
        if parsed is None:
            return

        # Sentinel write BEFORE scheduling the async work, so a ditto arriving
        # between this callback and the async-task completion sees "main frame
        # in flight, hold off" rather than the stale previous anchor. Keyed per
        # receiver. signal_id stays None until _process_parsed_signal confirms
        # persistence (or removes the anchor on an early return). The dev_fp is
        # computed here too; duplicates the normalize() call -- acceptable for
        # the race fix.
        n_dev_fp = EventParser.device_fingerprint(
            parsed.protocol,
            EventParser.extract_device_address(parsed.protocol, parsed.code),
            parsed.raw_timings,
            code=parsed.code,
        )
        self._ditto_anchor[rid_key] = (None, time.monotonic(), n_dev_fp)
        self._ditto_running_count[rid_key] = 0
        self._last_ditto_monotonic.pop(rid_key, None)

        self._hass.async_create_task(
            self._process_parsed_signal(parsed, receiver_entity_id)
        )

    def _maybe_attribute_repeat_frame(self, rid_key: str) -> None:
        """Attribute an incoming short signal (NEC ditto) to the most recent
        main-frame arrival ON THE SAME RECEIVER, if it is within the
        attribution window AND the inter-frame gate is satisfied. Updates
        ``observed_repeat_count`` on the stored signal with max-merge (high
        water mark) semantics.

        Per-receiver (v0.5.7): ``rid_key`` selects this receiver's anchor so
        concurrent presses on different receivers do not corrupt each other.
        """
        anchor = self._ditto_anchor.get(rid_key)
        if anchor is None:
            return
        signal_id, last_main_monotonic, _ = anchor

        # Sentinel: the main frame has not been persisted yet. Drop -- we
        # cannot attribute to a signal_id we do not have.
        if signal_id is None:
            return

        now = time.monotonic()

        # Gate 1: outside the main-frame attribution window.
        if now - last_main_monotonic > REPEAT_ATTRIBUTION_WINDOW:
            return

        # Gate 2: inter-frame staleness. NEC dittos arrive ~110ms apart; a gap
        # > DITTO_INTER_FRAME_MAX_S means the burst is over and this short
        # signal starts a new orphan burst until the next main-frame anchor.
        last_ditto = self._last_ditto_monotonic.get(rid_key)
        if last_ditto is not None and now - last_ditto > DITTO_INTER_FRAME_MAX_S:
            return

        new_count = self._ditto_running_count.get(rid_key, 0) + 1
        self._ditto_running_count[rid_key] = new_count
        self._last_ditto_monotonic[rid_key] = now

        # Locate the stored UnknownSignal by id and max-merge the count.
        for device in self._signal_store.get_all_devices():
            sig = device.get_signal_by_id(signal_id)
            if sig is None:
                continue
            if new_count > sig.observed_repeat_count:
                sig.observed_repeat_count = new_count
                self._signal_store.schedule_save()
            return

    # -----------------------------------------------------------------
    # Known-command check
    # -----------------------------------------------------------------

    def _matches_known_command(
        self,
        signal_fingerprint: str,
        byte_hash: str | None,
        decoded_fingerprint: str | None,
    ) -> tuple[str, str] | None:
        """Return the ``(device_id, command_id)`` this signal is assigned to.

        Delegates to the store's tiered reverse index: decoded protocol
        identity first, then ``(S/L fingerprint, byte_hash)``, then the
        S/L fingerprint alone. Returns ``None`` when the signal is not an
        already-assigned command.

        Replaces the old exact ``protocol`` + ``code`` string compare,
        which missed two real cases: native-path captures re-encode Pronto
        from jittered timings so the code string rarely matched, and the
        v0.3.4 byte-hash tiebreaker stores distinct codes that the string
        compare could not tell apart (B5, 2026-06-09 third-party review).
        The identity is returned (not a bare bool) so the v0.4.1
        assigned-state work can label the row; in v0.4.0 it is used only
        to suppress the re-press from the live feed.
        """
        return self._hair_store.match_command(
            decoded_fingerprint, signal_fingerprint, byte_hash
        )

    # -----------------------------------------------------------------
    # Rate limiting
    # -----------------------------------------------------------------

    def _check_rate_limit(self, fingerprint: str) -> bool:
        """Return True if the event is within rate limits.

        Uses a sliding window of 1 second. Returns False (drop) if
        the fingerprint has exceeded ``SIGNAL_RATE_LIMIT_PER_SEC``.
        """
        now = time.monotonic()
        bucket = self._rate_buckets[fingerprint]

        # Purge timestamps older than 1 second.
        cutoff = now - 1.0
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)

        if len(bucket) >= SIGNAL_RATE_LIMIT_PER_SEC:
            return False

        bucket.append(now)
        return True

    def _check_dismiss_push_rate(self, device_fingerprint: str) -> bool:
        """Return True if the dismiss-activity push is within rate limits.

        Mirrors :meth:`_check_rate_limit` shape but uses a separate bucket
        and the ``SIGNAL_WS_PUSH_RATE_LIMIT`` budget. The dismiss-activity
        bus event drives the Sniffer's Show Dismissed glow + dot indicator
        and only needs to fire a few times a second to be visible -- a
        held-down button on a dismissed remote does not need to broadcast
        every individual frame.
        """
        now = time.monotonic()
        bucket = self._dismiss_push_buckets[device_fingerprint]

        # Purge timestamps older than 1 second.
        cutoff = now - 1.0
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)

        if len(bucket) >= SIGNAL_WS_PUSH_RATE_LIMIT:
            return False

        bucket.append(now)
        return True

    # -----------------------------------------------------------------
    # Repeat suppression
    # -----------------------------------------------------------------

    def _check_repeat(
        self,
        fingerprint: str,
        receiver_entity_id: str | None = None,
        byte_hash: str | None = None,
        decoded_fingerprint: str | None = None,
    ) -> bool:
        """Return True if the event is NOT a repeat (passes suppression).

        Suppresses duplicate signals within ``SIGNAL_REPEAT_SUPPRESS_MS``,
        keyed per receiver (v0.5.7) so the same press captured by two
        receivers is not dropped -- each receiver's captures suppress only
        their own. The signal side of the key is the STRONGEST identity
        tier the capture carries (v0.5.8 unified identity): two DIFFERENT
        sub-threshold buttons in quick succession (Sony red then green
        share an S/L fingerprint but differ in byte_hash) are both stored,
        while one button whose S/L fingerprint flips across the
        classification boundary between frames still suppresses correctly
        via its stable byte_hash. Known wrinkle (accepted): if one frame of
        a press decodes and the next frame's decode fails, the two frames
        key at different tiers and suppression misses between them -- the
        tiered store dedup still merges the rows, so the cost is live-feed
        noise only.
        """
        from .identity import SignalIdentity

        ident = SignalIdentity(decoded_fingerprint, byte_hash, fingerprint)
        key = (ident.strongest_key(), receiver_entity_id or "__legacy__")
        now = time.monotonic()
        last = self._last_seen_times.get(key)
        suppress_s = SIGNAL_REPEAT_SUPPRESS_MS / 1000.0

        if last is not None and (now - last) < suppress_s:
            return False

        self._last_seen_times[key] = now
        return True

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def get_unknown_devices(
        self,
        include_dismissed: bool = False,
        min_hits: int | None = None,
        source: str | None = None,
    ) -> list[UnknownDevice]:
        """Return unknown devices in manual display order.

        Ordered by the persisted ``order`` field (ascending; lower sorts
        higher), not by hit_count. Newly-discovered remotes are inserted
        on top via ``SignalStore.add_device`` and stay there until the
        user drags them. The min_hits noise filter is unchanged.

        Args:
            include_dismissed: Include dismissed devices in results.
            min_hits: Minimum hit_count to include. Defaults to
                ``SIGNAL_CLUSTER_THRESHOLD``. Pass ``0`` to include all.
            source: If given (``"sniffed"`` or ``"manual"``), return only
                devices of that source. Lets the Sniffer and Clips tabs
                each request their own slice. ``None`` returns both.
        """
        if min_hits is None:
            min_hits = SIGNAL_CLUSTER_THRESHOLD

        devices = self._signal_store.get_all_devices()
        if not include_dismissed:
            devices = [d for d in devices if not d.dismissed]
        if min_hits > 0:
            devices = [d for d in devices if d.hit_count >= min_hits]
        if source is not None:
            devices = [d for d in devices if d.source == source]

        return sorted(devices, key=lambda d: d.order)

    def get_unknown_device(self, device_id: str) -> UnknownDevice | None:
        """Return a single unknown device by ID."""
        return self._signal_store.get_device(device_id)

    def dismiss_device(self, device_id: str) -> bool:
        """Mark a device as dismissed.

        Adds the device fingerprint to the persistent dismiss list
        and sets the dismissed flag on the device record.
        """
        device = self._signal_store.get_device(device_id)
        if device is None:
            return False
        device.dismissed = True
        self._signal_store.add_dismissed(device.fingerprint)
        self._signal_store.schedule_save()
        return True

    def undismiss_device(self, device_id: str) -> bool:
        """Remove dismissed status from a device."""
        device = self._signal_store.get_device(device_id)
        if device is None:
            return False
        device.dismissed = False
        self._signal_store.remove_dismissed(device.fingerprint)
        self._signal_store.schedule_save()
        return True

    async def assign_signal(
        self,
        device_id: str,
        signal_id: str,
        hair_device_id: str,
        command_name: str,
        command_category: str,
        send_count: int | None = None,
        repeat_count: int | None = None,
    ) -> dict[str, Any]:
        """Assign an unknown signal as a named command on a HAIR device.

        Uses lock-first pattern with structured return. Rolls back cleanly
        on any failure. The signal is identified by its stable id, not its
        fingerprint, which is not unique on a remote (see UnknownSignal.id).

        Returns dict with ``success``, ``command_id``, or ``error``/``code``.
        """
        from .models import CaptureResult, CommandCategory

        async with self._lock:
            # Validate source.
            unknown_device = self._signal_store.get_device(device_id)
            if unknown_device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Unknown device not found"}
            signal = unknown_device.get_signal_by_id(signal_id)
            if signal is None:
                return {"success": False, "code": "signal_not_found",
                        "error": "Signal not found on device"}

            # Validate target.
            hair_device = self._hair_store.get_device(hair_device_id)
            if hair_device is None:
                return {"success": False, "code": "target_not_found",
                        "error": "Target HAIR device not found"}

            # Build IRCommand from the signal. The signal is COPIED into
            # the device and intentionally LEFT in the unknown catalog so
            # it can be assigned again -- to other devices or as other
            # commands. Only an explicit Delete / Dismiss / Clear All
            # removes it. No duplicate guard: assigning the same signal
            # more than once is the user's prerogative.
            capture = CaptureResult(
                protocol=signal.protocol,
                code=signal.code,
                raw_timings=list(signal.raw_timings),
                frequency=signal.frequency,
            )
            try:
                category = CommandCategory(command_category)
            except ValueError:
                category = CommandCategory.CUSTOM
            ir_command = capture.to_command(command_name, category)
            _apply_signal_provenance(
                ir_command, signal,
                send_count=send_count,
                repeat_count=repeat_count,
            )

            hair_device.add_command(ir_command)
            command_id = ir_command.id
            try:
                await self._hair_store.async_save()
            except Exception:
                hair_device.remove_command(command_id)
                _LOGGER.exception("Failed to save HAIR store during assign")
                return {"success": False, "code": "save_failed",
                        "error": "Failed to save command"}

        # Assignment set for this signal changed -- notify other browser tabs
        # so the green Assign badge / trigger dot refresh live (v0.5.7). Fired
        # outside the lock; the payload is fingerprint-only.
        self._hass.bus.async_fire(
            EVENT_SIGNAL_UPDATED, {"signal_fingerprint": signal.fingerprint}
        )
        return {"success": True, "command_id": command_id}

    async def assign_to_new_device(
        self,
        device_id: str,
        signal_id: str,
        device_name: str,
        device_type: str,
        emitter_entity_ids: list[str],
        command_name: str,
        command_category: str,
        send_count: int | None = None,
        repeat_count: int | None = None,
    ) -> dict[str, Any]:
        """Create a new HAIR device and assign the signal in one atomic op.

        HA device registry and entity creation happen only after both
        stores have persisted successfully, preventing phantom devices.

        Returns dict with ``success``, ``command_id``, ``device_id``,
        or ``error``/``code``.
        """
        from .models import (
            CaptureResult,
            CommandCategory,
            DeviceType,
            IRDevice,
        )

        async with self._lock:
            # Validate source signal.
            unknown_device = self._signal_store.get_device(device_id)
            if unknown_device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Unknown device not found"}
            signal = unknown_device.get_signal_by_id(signal_id)
            if signal is None:
                return {"success": False, "code": "signal_not_found",
                        "error": "Signal not found on device"}

            # Validate device type.
            try:
                dtype = DeviceType(device_type)
            except ValueError:
                return {"success": False, "code": "invalid_device_type",
                        "error": f"Invalid device type: {device_type}"}

            # Build IRCommand.
            capture = CaptureResult(
                protocol=signal.protocol,
                code=signal.code,
                raw_timings=list(signal.raw_timings),
                frequency=signal.frequency,
            )
            try:
                category = CommandCategory(command_category)
            except ValueError:
                category = CommandCategory.CUSTOM
            ir_command = capture.to_command(command_name, category)
            _apply_signal_provenance(
                ir_command, signal,
                send_count=send_count,
                repeat_count=repeat_count,
            )

            # Create device in memory (NOT persisted yet).
            new_device = IRDevice(
                name=device_name,
                device_type=dtype,
                emitter_entity_ids=list(emitter_entity_ids),
            )
            new_device.add_command(ir_command)
            command_id = ir_command.id
            new_device_id = new_device.id

            # Add to HAIRStore in memory. The source signal is COPIED into
            # the new device and intentionally LEFT in the unknown catalog
            # so it stays assignable. Only an explicit Delete / Dismiss /
            # Clear All removes it.
            self._hair_store.add_device(new_device)

            try:
                await self._hair_store.async_save()
            except Exception:
                # Rollback: drop the unsaved device.
                self._hair_store.remove_device(new_device_id)
                _LOGGER.exception(
                    "Failed to save HAIR store during assign-new-device"
                )
                return {"success": False, "code": "save_failed",
                        "error": "Failed to save new device"}

        # HAIR store persisted -- safe to register in HA now.
        # (Outside the lock since HA registry ops don't touch our stores.)
        # Notify other tabs that this signal's assignment set changed (v0.5.7).
        self._hass.bus.async_fire(
            EVENT_SIGNAL_UPDATED, {"signal_fingerprint": signal.fingerprint}
        )
        return {
            "success": True,
            "command_id": command_id,
            "device_id": new_device_id,
            "device": new_device,
        }

    async def delete_signal(
        self, device_id: str, signal_id: str
    ) -> dict[str, Any]:
        """Delete a single signal from an unknown device.

        Identified by stable id (fingerprints are not unique on a remote).
        Fires ``hair_signal_removed`` on success. Removes the parent
        unknown device if no signals remain.

        Returns dict with ``success`` or ``error``/``code``.
        """
        async with self._lock:
            unknown_device = self._signal_store.get_device(device_id)
            if unknown_device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Unknown device not found"}
            if not unknown_device.remove_signal_by_id(signal_id):
                return {"success": False, "code": "signal_not_found",
                        "error": "Signal not found on device"}

            device_emptied = not unknown_device.signals
            if device_emptied:
                self._signal_store.remove_device(device_id)

            try:
                await self._signal_store.async_save()
            except Exception:
                # Best-effort restore.
                _LOGGER.exception("Failed to save after signal deletion")
                return {"success": False, "code": "save_failed",
                        "error": "Failed to save after deletion"}

        # Fire event outside lock.
        self._hass.bus.async_fire(EVENT_SIGNAL_REMOVED, {
            "device_id": device_id,
            "signal_id": signal_id,
            "device_removed": device_emptied,
        })
        return {"success": True, "device_removed": device_emptied}

    async def test_signal(
        self, signal_id: str, emitter_entity_id: str
    ) -> dict[str, Any]:
        """Send an unknown signal through an emitter for user verification.

        Signal identified by stable id (fingerprints are not unique).
        Returns structured result dict with ``success`` and error details.
        """
        # Validate emitter entity exists.
        state = self._hass.states.get(emitter_entity_id)
        if state is None:
            return {"success": False, "code": "entity_not_found",
                    "error": f"Entity {emitter_entity_id} not found"}

        # Find the signal across all devices.
        signal = None
        for device in self._signal_store.get_all_devices():
            signal = device.get_signal_by_id(signal_id)
            if signal is not None:
                break

        if signal is None:
            return {"success": False, "code": "signal_not_found",
                    "error": "Signal not found"}

        # Lazy imports: infrared component only available at runtime on HA 2026.4+.
        from homeassistant.components.infrared import (
            async_send_command as ir_send,
        )

        from .ir_command import build_command, build_decoded_command

        # Prefer canonical encode-from-decoded when the signal carries a
        # decoded protocol identity, so the catalog-signal Test path (Sniffer
        # / Clipper / Plucker) transmits clean library-encoded timings rather
        # than replaying captured (receiver-distorted) ones. Mirrors
        # device_manager.async_send_command. Falls back to Pronto/raw replay
        # when undecodable.
        ir_cmd = None
        if signal.decoded_fingerprint:
            ir_cmd = build_decoded_command(
                signal.decoded_protocol,
                signal.decoded_address,
                signal.decoded_command,
                repeat_count=signal.repeat_count or 0,
                decoded_extras=signal.decoded_extras,
            )
        decoded_tx = ir_cmd is not None
        if ir_cmd is None:
            try:
                ir_cmd = build_command(
                    protocol=signal.protocol,
                    code=signal.code,
                    raw_timings=signal.raw_timings,
                    frequency=signal.frequency or 38000,
                    repeat_count=signal.repeat_count or 0,
                )
            except ValueError as exc:
                return {"success": False, "code": "no_signal_data",
                        "error": str(exc)}

        # Honor the signal's whole-frame send_count, mirroring
        # device_manager.async_send_command: transmit the built Command N times
        # with SEND_REPEAT_GAP between so the receiver registers them as
        # distinct presses. send_count defaults to 1.
        send_count = max(1, signal.send_count or 1)
        # The Mirror (v0.6.6): a catalog test is a send; audit it and arm
        # echo attribution BEFORE transmitting so the emitter's state
        # beacon and the loopback capture both attribute here.
        # Provenance label for the Mirror row. "Manual test send" per the
        # owner's bench ruling (was "Catalog test" during the build; the
        # frontend still parses the old prefix for rows persisted before
        # the rename).
        label = (
            f"Manual test send: {signal.alias}" if signal.alias
            else "Manual test send"
        )
        self.record_send(
            ir_cmd, label, [emitter_entity_id],
            decoded_fingerprint=signal.decoded_fingerprint,
        )
        # Route through the transmit gate: the frontend fires one test
        # call per selected emitter concurrently, and without the gate
        # both blasters key up at once -- the superimposed hybrid fails
        # the echo claim and mints a junk Sniffer row (see tx_gate).
        from .tx_gate import gated_send

        try:
            for i in range(send_count):
                if i:
                    await asyncio.sleep(SEND_REPEAT_GAP)
                await asyncio.wait_for(
                    gated_send(
                        self._hass, emitter_entity_id, ir_cmd, ir_send
                    ),
                    timeout=ASSIGN_SERVICE_TIMEOUT_S,
                )
        except (TimeoutError, asyncio.TimeoutError, asyncio.CancelledError):  # noqa: UP041
            return {"success": False, "code": "send_timeout",
                    "error": "Emitter timed out"}
        except Exception as exc:
            return {"success": False, "code": "send_failed",
                    "error": f"Emitter did not respond: {exc}"}

        # RC-5-family toggle state (v0.6.0): mirror
        # device_manager.async_send_command -- one Test is one logical
        # press, flipped once after a fully successful send. Fingerprint
        # excludes toggle, so the catalog row's identity is unchanged.
        if (
            decoded_tx
            and signal.decoded_extras
            and "toggle" in signal.decoded_extras
        ):
            signal.decoded_extras["toggle"] = (
                int(signal.decoded_extras["toggle"]) ^ 1
            )
            await self._signal_store.async_save()

        return {"success": True}

    def clear_all(self, source: str | None = None) -> None:
        """Wipe the unknown signal catalog.

        ``source=None`` clears everything. Passing ``"sniffed"`` or
        ``"manual"`` clears only that source, so the Sniffer and Clips
        tabs each clear their own world.
        """
        self._signal_store.clear_all(source)
        self._signal_store.schedule_save()

    # -----------------------------------------------------------------
    # Clips (manual remotes / signals)
    # -----------------------------------------------------------------

    async def create_manual_remote(self, name: str) -> UnknownDevice:
        """Create a new clipped (manual) remote.

        Manual remotes get a synthetic device fingerprint (``manual:<id>``)
        so live sniffed signals can never group into them -- the captured
        and pasted pipelines stay isolated.
        """
        label = (name or "").strip() or "Clipped Remote"
        now_iso = datetime.now(UTC).isoformat()
        async with self._lock:
            device = UnknownDevice(
                label=label,
                source="manual",
                first_seen=now_iso,
                last_seen=now_iso,
                hit_count=0,
            )
            device.fingerprint = f"manual:{device.id}"
            self._signal_store.add_device(device)
            await self._signal_store.async_save()
        return device

    async def create_manual_signal(
        self,
        device_id: str,
        pronto: str,
        alias: str = "",
        repeat_count: int | None = None,
        send_count: int | None = None,
    ) -> dict[str, Any]:
        """Add a manually-pasted Pronto signal to a clipped remote.

        Validates the Pronto server-side (defense in depth -- the frontend
        validates too). Returns a structured dict with ``success`` and the
        new signal record, or ``error``/``code``.
        """
        result = validate_pronto(pronto)
        if not result.valid:
            return {
                "success": False,
                "code": "invalid_pronto",
                "error": (
                    result.errors[0] if result.errors else "Invalid Pronto code"
                ),
            }

        async with self._lock:
            device = self._signal_store.get_device(device_id)
            if device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Clipped remote not found"}
            if device.source != "manual":
                return {"success": False, "code": "not_manual",
                        "error": "Can only add signals to a clipped remote"}

            now_iso = datetime.now(UTC).isoformat()
            code = result.normalized
            sig_fp = EventParser.signal_fingerprint("PRONTO", code, [])
            byte_hash = EventParser.pronto_byte_hash(code)
            from .ir_command import ProntoCommand

            # Decode-on-paste: mirror the Sniffer capture path so a pasted NEC
            # code transmits canonical re-encoded timings instead of the
            # quantized Pronto. Guarded; a non-NEC or unreadable code stays
            # Pronto-only. Timings are computed only to feed the decoder --
            # raw_timings stays [] (TX uses decoded_*, not raw). Runs BEFORE
            # the duplicate guard so the guard sees the full tiered identity.
            try:
                decode_raw = ProntoCommand(code).get_raw_timings()
            except Exception:
                decode_raw = None
            identity = try_decode_identity(decode_raw)
            decoded_protocol = identity.protocol if identity else None
            decoded_address = identity.address if identity else None
            decoded_command = identity.command if identity else None
            decoded_fingerprint = identity.fingerprint if identity else None
            decoded_extras = (
                dict(identity.extras) if identity and identity.extras else None
            )

            # Reject a paste of a signal already on this remote. The match
            # is the tiered identity rule (decoded > byte_hash > S/L
            # fingerprint): a genuinely different code that merely shares an
            # S/L fingerprint (e.g. Panasonic, TCL, Sony) differs at the
            # byte level and is allowed through as a distinct signal, while
            # a jittered copy of an existing button is refused even when its
            # coarse fingerprint flipped across the classification boundary.
            # The Sniffer dedupes the same way on capture.
            if device.get_signal(sig_fp, byte_hash, decoded_fingerprint) is not None:
                return {
                    "success": False,
                    "code": "duplicate_signal",
                    "error": "This signal is already on this remote",
                }
            frequency = (
                round(result.frequency_khz * 1000)
                if result.frequency_khz
                else DEFAULT_CARRIER_FREQUENCY
            )
            signal = UnknownSignal(
                fingerprint=sig_fp,
                byte_hash=byte_hash,
                decoded_protocol=decoded_protocol,
                decoded_address=decoded_address,
                decoded_command=decoded_command,
                decoded_fingerprint=decoded_fingerprint,
                decoded_extras=(
                    dict(decoded_extras) if decoded_extras else None
                ),
                protocol="PRONTO",
                code=code,
                raw_timings=[],
                frequency=frequency,
                hit_count=1,
                first_seen=now_iso,
                last_seen=now_iso,
                source="manual",
                alias=(alias or "").strip(),
            )
            # Create-time TX knobs from the editor (clamped). Absent -> the
            # dataclass defaults apply (repeat_count=DEFAULT_REPEAT_COUNT,
            # send_count=1).
            if repeat_count is not None:
                signal.repeat_count = max(0, min(int(repeat_count), MAX_DITTO_COUNT))
            if send_count is not None:
                signal.send_count = max(1, min(int(send_count), MAX_SEND_COUNT))
            # New signal goes on top so the just-added clip surfaces.
            device.signals.insert(0, signal)
            device.last_seen = now_iso
            await self._signal_store.async_save()
        return {"success": True, "signal": signal.to_dict()}

    async def create_plucked_blaster(
        self, vendor_entity_id: str, appliance: str, name: str
    ) -> UnknownDevice:
        """Create a plucked blaster (one vendor entity + one appliance).

        Mirrors ``create_manual_remote``: a synthetic device fingerprint
        (``plucked:<id>``) keeps live sniffed signals from ever grouping into
        it. ``vendor_entity_id`` and ``appliance`` are set here and are
        immutable for the life of the blaster.
        """
        label = (name or "").strip() or "Plucked Blaster"
        now_iso = datetime.now(UTC).isoformat()
        async with self._lock:
            device = UnknownDevice(
                label=label,
                source="plucked",
                vendor_entity_id=vendor_entity_id,
                appliance=appliance,
                first_seen=now_iso,
                last_seen=now_iso,
                hit_count=0,
            )
            device.fingerprint = f"plucked:{device.id}"
            self._signal_store.add_device(device)
            await self._signal_store.async_save()
        return device

    async def create_plucked_signal(
        self,
        device_id: str,
        pronto: str,
        command_name: str,
        alias: str = "",
    ) -> dict[str, Any]:
        """Place a plucked Pronto signal directly onto a named blaster.

        Mirrors ``create_manual_signal`` but is guarded to plucked blasters,
        records the user-typed ``command_name`` as ``plucked_command_name``,
        and tags the signal ``source="plucked"``. Validates the Pronto and
        rejects a true duplicate (same fingerprint AND byte_hash) already on
        the blaster. Placement is by ``device_id``; nothing is fingerprint-
        grouped and nothing reaches the Sniffer feed.
        """
        result = validate_pronto(pronto)
        if not result.valid:
            return {
                "success": False,
                "code": "invalid_pronto",
                "error": (
                    result.errors[0] if result.errors else "Invalid Pronto code"
                ),
            }

        async with self._lock:
            device = self._signal_store.get_device(device_id)
            if device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Plucked blaster not found"}
            if device.source != "plucked":
                return {"success": False, "code": "not_plucked",
                        "error": "Can only add plucked signals to a plucked blaster"}

            now_iso = datetime.now(UTC).isoformat()
            code = result.normalized
            sig_fp = EventParser.signal_fingerprint("PRONTO", code, [])
            byte_hash = EventParser.pronto_byte_hash(code)
            from .ir_command import ProntoCommand

            # Decode-on-place: mirror the Sniffer/clip path so a plucked NEC
            # code transmits canonical re-encoded timings. Guarded; a non-NEC
            # or unreadable code stays Pronto-only. Runs BEFORE the duplicate
            # guard so the guard sees the full tiered identity.
            try:
                decode_raw = ProntoCommand(code).get_raw_timings()
            except Exception:
                decode_raw = None
            identity = try_decode_identity(decode_raw)
            decoded_protocol = identity.protocol if identity else None
            decoded_address = identity.address if identity else None
            decoded_command = identity.command if identity else None
            decoded_fingerprint = identity.fingerprint if identity else None
            decoded_extras = (
                dict(identity.extras) if identity and identity.extras else None
            )

            # Tiered duplicate guard (matches the paste/edit/capture paths):
            # a re-encoding of an already-plucked command is refused even
            # when it bins or classifies differently, so the load-time heal
            # never has to merge (and thereby delete) a plucked row later.
            if device.get_signal(sig_fp, byte_hash, decoded_fingerprint) is not None:
                return {
                    "success": False,
                    "code": "duplicate_signal",
                    "error": "This signal is already on this blaster",
                }
            frequency = (
                round(result.frequency_khz * 1000)
                if result.frequency_khz
                else DEFAULT_CARRIER_FREQUENCY
            )
            signal = UnknownSignal(
                fingerprint=sig_fp,
                byte_hash=byte_hash,
                decoded_protocol=decoded_protocol,
                decoded_address=decoded_address,
                decoded_command=decoded_command,
                decoded_fingerprint=decoded_fingerprint,
                decoded_extras=(
                    dict(decoded_extras) if decoded_extras else None
                ),
                protocol="PRONTO",
                code=code,
                raw_timings=[],
                frequency=frequency,
                hit_count=1,
                first_seen=now_iso,
                last_seen=now_iso,
                source="plucked",
                alias=(alias or "").strip(),
                plucked_command_name=command_name,
            )
            device.signals.insert(0, signal)
            device.last_seen = now_iso
            await self._signal_store.async_save()
        return {"success": True, "signal": signal.to_dict()}

    async def edit_signal_pronto(
        self,
        device_id: str,
        signal_id: str,
        pronto: str,
        alias: str | None = None,
        repeat_count: int | None = None,
        send_count: int | None = None,
    ) -> dict[str, Any]:
        """Edit a stored signal's Pronto in place, re-evaluated as a capture.

        Validates, locates the signal by ``id``, and re-derives every
        identity field from the new code -- frequency, raw timings (from the
        Pronto), S/L fingerprint, byte_hash, and ``decoded_*`` -- so an edited
        signal is indistinguishable from a freshly captured one and stays
        snappable. Rejects a code that collides with a *different* signal on
        the same remote (self excluded by id). When the S/L fingerprint
        changes, bound triggers are auto-rewired to the new identity.

        Returns ``{success, signal, triggers}`` where ``triggers`` is the
        rewire result (``{"rewired": [...], "skipped": [...]}``) so the caller
        can name the affected trigger(s) in a note.
        """
        result = validate_pronto(pronto)
        if not result.valid:
            return {
                "success": False,
                "code": "invalid_pronto",
                "error": (
                    result.errors[0] if result.errors else "Invalid Pronto code"
                ),
            }

        from .ir_command import ProntoCommand

        async with self._lock:
            device = self._signal_store.get_device(device_id)
            if device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Remote not found"}
            signal = device.get_signal_by_id(signal_id)
            if signal is None:
                return {"success": False, "code": "signal_not_found",
                        "error": "Signal not found"}

            code = result.normalized
            new_fp = EventParser.signal_fingerprint("PRONTO", code, [])
            new_byte_hash = EventParser.pronto_byte_hash(code)

            # Re-evaluate the new code as a fresh capture: derive timings
            # from the Pronto and decode, so the signal stays first-class
            # and (on the Sniffer) snappable. Runs BEFORE the duplicate
            # guard so the guard sees the full tiered identity.
            try:
                raw = ProntoCommand(code).get_raw_timings()
            except Exception:
                raw = None
            identity = try_decode_identity(raw)
            decoded_protocol = identity.protocol if identity else None
            decoded_address = identity.address if identity else None
            decoded_command = identity.command if identity else None
            decoded_fingerprint = identity.fingerprint if identity else None
            decoded_extras = (
                dict(identity.extras) if identity and identity.extras else None
            )

            # Refuse a code a *different* signal on this remote already holds
            # (tiered identity, so a jittered re-paste of an existing button
            # is caught even when its coarse fingerprint flipped). Editing to
            # the identity the signal already has is allowed (it resolves to
            # this same signal, so no collision).
            existing = device.get_signal(new_fp, new_byte_hash, decoded_fingerprint)
            if existing is not None and existing.id != signal.id:
                return {
                    "success": False,
                    "code": "duplicate_signal",
                    "error": "Another signal on this remote already has that code",
                }

            old_fp = signal.fingerprint
            # Captured BEFORE the mutation below: a sub-threshold edit (Sony
            # code A to code B) changes only the byte_hash -- and rewire
            # needs the old byte-level AND decoded values to repoint
            # precisely (v0.5.8 unified identity).
            old_byte_hash = signal.byte_hash
            old_decoded_fingerprint = signal.decoded_fingerprint
            frequency = (
                round(result.frequency_khz * 1000)
                if result.frequency_khz
                else DEFAULT_CARRIER_FREQUENCY
            )

            # Re-derive identity from the new code. repeat_count, send_count,
            # and observed_repeat_count are TX knobs / capture observations,
            # NOT signal identity, so this re-derivation intentionally does NOT
            # touch them -- an edit preserves the user's tunings. Explicit
            # repeat_count / send_count args (from the editor Save) are applied
            # just below.
            signal.code = code
            signal.fingerprint = new_fp
            signal.byte_hash = new_byte_hash
            signal.raw_timings = list(raw) if raw else []
            signal.frequency = frequency
            signal.decoded_protocol = decoded_protocol
            signal.decoded_address = decoded_address
            signal.decoded_command = decoded_command
            signal.decoded_fingerprint = decoded_fingerprint
            signal.decoded_extras = decoded_extras
            if alias is not None:
                signal.alias = alias.strip()
            if repeat_count is not None:
                signal.repeat_count = max(0, min(int(repeat_count), MAX_DITTO_COUNT))
            if send_count is not None:
                signal.send_count = max(1, min(int(send_count), MAX_SEND_COUNT))
            signal.last_seen = datetime.now(UTC).isoformat()

            rewire: dict[str, list[str]] = {"rewired": [], "skipped": []}
            # Rewire on ANY identity component changing (v0.5.8): a
            # sub-threshold edit shifts only the byte_hash, never the S/L
            # fingerprint, and would otherwise orphan a scoped trigger.
            if self._trigger_manager is not None and (
                new_fp != old_fp
                or new_byte_hash != old_byte_hash
                or decoded_fingerprint != old_decoded_fingerprint
            ):
                rewire = await self._trigger_manager.rewire(
                    old_fp, new_fp, "PRONTO", code,
                    old_byte_hash=old_byte_hash,
                    new_byte_hash=new_byte_hash,
                    old_decoded_fingerprint=old_decoded_fingerprint,
                    new_decoded_fingerprint=decoded_fingerprint,
                )

            await self._signal_store.async_save()

        return {"success": True, "signal": signal.to_dict(), "triggers": rewire}

    async def import_manual_remote(
        self,
        name: str,
        entries: list[dict[str, Any]],
        merge_existing: bool = False,
    ) -> dict[str, Any]:
        """Create a clipped remote pre-filled from materialized codebook entries.

        ``entries`` are the Clipper-ready dicts from ``code_library``: each
        ``{name, code, decoded_protocol, decoded_address, decoded_command,
        decoded_fingerprint}`` plus an optional ``send_count`` (wig imports
        carry it; library entries do not). Signals are validated,
        deduplicated within the batch, and appended in order under a single
        lock and save. Invalid or duplicate codes are skipped; returns the
        device plus imported/skipped counts so the UI can report partial
        imports.

        ``merge_existing`` (wig imports): when a clipped remote with the
        same label already exists, its rows absorb the batch instead of a
        twin remote appearing -- re-materializing a wig you already
        imported collapses onto existing rows via the tiered duplicate
        guard (wigs.md section 6). Library imports keep their historical
        new-remote-every-time behavior.
        """
        label = (name or "").strip() or "Imported Remote"
        now_iso = datetime.now(UTC).isoformat()
        imported = 0
        skipped = 0
        async with self._lock:
            device = None
            if merge_existing:
                device = next(
                    (
                        d for d in self._signal_store.get_all_devices()
                        if d.source == "manual"
                        and (d.label or "").strip().casefold()
                        == label.casefold()
                    ),
                    None,
                )
            created = device is None
            if device is None:
                device = UnknownDevice(
                    label=label,
                    source="manual",
                    first_seen=now_iso,
                    last_seen=now_iso,
                    hit_count=0,
                )
                device.fingerprint = f"manual:{device.id}"
            for entry in entries:
                result = validate_pronto(entry.get("code") or "")
                if not result.valid:
                    skipped += 1
                    continue
                code = result.normalized
                sig_fp = EventParser.signal_fingerprint("PRONTO", code, [])
                byte_hash = EventParser.pronto_byte_hash(code)
                # Tiered in-batch duplicate guard: codebook entries carry a
                # decoded identity, so two encodings of the same command
                # dedupe here instead of surviving until the load-time heal.
                if device.get_signal(
                    sig_fp, byte_hash, entry.get("decoded_fingerprint")
                ) is not None:
                    skipped += 1
                    continue
                frequency = (
                    round(result.frequency_khz * 1000)
                    if result.frequency_khz
                    else DEFAULT_CARRIER_FREQUENCY
                )
                send_count = entry.get("send_count", 1)
                if not isinstance(send_count, int) or isinstance(
                    send_count, bool
                ):
                    send_count = 1
                signal = UnknownSignal(
                    fingerprint=sig_fp,
                    byte_hash=byte_hash,
                    decoded_protocol=entry.get("decoded_protocol"),
                    decoded_address=entry.get("decoded_address"),
                    decoded_command=entry.get("decoded_command"),
                    decoded_fingerprint=entry.get("decoded_fingerprint"),
                    decoded_extras=entry.get("decoded_extras") or None,
                    protocol="PRONTO",
                    code=code,
                    raw_timings=[],
                    frequency=frequency,
                    hit_count=1,
                    first_seen=now_iso,
                    last_seen=now_iso,
                    source="manual",
                    alias=(entry.get("name") or "").strip(),
                    send_count=max(1, min(send_count, MAX_SEND_COUNT)),
                )
                device.signals.append(signal)
                imported += 1
            if created:
                self._signal_store.add_device(device)
            else:
                device.last_seen = now_iso
            await self._signal_store.async_save()
        return {
            "device": device.to_dict(),
            "imported": imported,
            "skipped": skipped,
            "merged": not created,
        }

    async def set_signal_alias(
        self, device_id: str, signal_id: str, alias: str
    ) -> dict[str, Any]:
        """Set or clear the alias on a signal. Empty clears it.

        Identified by stable id, not fingerprint -- two signals on a remote
        can share a fingerprint, so aliasing by fingerprint would rewrite
        both (the original GH #13 symptom). Keying on id fixes that.
        """
        async with self._lock:
            device = self._signal_store.get_device(device_id)
            if device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Remote not found"}
            signal = device.get_signal_by_id(signal_id)
            if signal is None:
                return {"success": False, "code": "signal_not_found",
                        "error": "Signal not found"}
            signal.alias = (alias or "").strip()
            await self._signal_store.async_save()
        return {"success": True, "alias": signal.alias}

    async def delete_sniffed_remote(self, device_id: str) -> dict[str, Any]:
        """Delete a sniffed remote and all its signals (owner ask, v0.7.0).

        Sniffer resurrection semantics apply, same as per-row delete: the
        remote returns on the next hearing of any of its signals, so
        removal cannot lose the airwaves' truth. Restricted to sniffed
        devices; clipped/plucked remotes have their own delete paths and
        the Mirror's synthetic device must never be removable here.
        """
        async with self._lock:
            device = self._signal_store.get_device(device_id)
            if device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Remote not found"}
            if device.source != "sniffed":
                return {"success": False, "code": "not_sniffed",
                        "error": "Only sniffed remotes can be deleted here"}
            self._signal_store.remove_device(device_id)
            await self._signal_store.async_save()
        return {"success": True}

    async def delete_manual_remote(self, device_id: str) -> dict[str, Any]:
        """Delete a clipped (manual) remote and any signals it holds.

        Used by the Clipper tab to remove a remote directly. A remote with
        signals is normally removed when its last signal is deleted; this
        covers the case of a remote created with no signals yet. Restricted
        to manual remotes so it cannot touch sniffed devices.
        """
        async with self._lock:
            device = self._signal_store.get_device(device_id)
            if device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Remote not found"}
            if device.source not in ("manual", "plucked"):
                return {"success": False, "code": "not_manual",
                        "error": "Only clipped remotes can be deleted this way"}
            self._signal_store.remove_device(device_id)
            await self._signal_store.async_save()
        return {"success": True}

    # -----------------------------------------------------------------
    # Subscriber management (WebSocket push)
    # -----------------------------------------------------------------

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback for real-time signal notifications."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Remove a previously registered callback."""
        with contextlib.suppress(ValueError):
            self._subscribers.remove(callback)
