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
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant

from .const import (
    ASSIGN_SERVICE_TIMEOUT_S,
    DEFAULT_CARRIER_FREQUENCY,
    EVENT_DISMISS_ACTIVITY,
    EVENT_SIGNAL_DETECTED,
    EVENT_SIGNAL_REMOVED,
    LEGACY_ESPHOME_IR_EVENT,
    SIGNAL_CLUSTER_THRESHOLD,
    SIGNAL_RATE_LIMIT_PER_SEC,
    SIGNAL_REPEAT_SUPPRESS_MS,
    SIGNAL_WS_PUSH_RATE_LIMIT,
)
from .event_parser import EventParser
from .models import UnknownDevice, UnknownSignal
from .pronto_validator import validate_pronto
from .signal_store import SignalStore
from .storage import HAIRStore

_LOGGER = logging.getLogger(__name__)


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
        self._lock = asyncio.Lock()
        self._native_mode: bool = False

        # Rate limiting: fingerprint -> list of event timestamps (monotonic).
        self._rate_buckets: dict[str, list[float]] = defaultdict(list)

        # Repeat suppression: fingerprint -> last event time (monotonic).
        self._last_seen_times: dict[str, float] = {}

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

    @property
    def bridge_active_device_ids(self) -> set[str]:
        """Device IDs that have fired esphome.remote_received this session."""
        return self._bridge_active_device_ids

    # -----------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------

    async def async_start(self) -> None:
        """Start listening for IR events.

        Tries the native receiver API (HA 2026.6+) first.  Falls back
        to the legacy ESPHome event bus bridge if ``async_subscribe_receiver``
        is not available.

        Even when the native path succeeds, we also wire a tracking-only
        listener on ``esphome.remote_received`` so the Receivers UI can
        surface ``RX-BRIDGE`` for devices that still have ``on_pronto:``
        YAML configured alongside their native receiver. In legacy mode
        the main ``_on_ir_event`` handler already records device_ids as
        part of its processing, so we don't double-subscribe.
        """
        if not self._signal_store.loaded:
            await self._signal_store.async_load()

        try:
            await self._start_native_receivers()
        except ImportError:
            self._start_legacy_event_bus()
        except Exception:
            _LOGGER.warning(
                "Native receiver API failed; falling back to legacy event bus",
                exc_info=True,
            )
            self._start_legacy_event_bus()

        if self._native_mode:
            unsub = self._hass.bus.async_listen(
                LEGACY_ESPHOME_IR_EVENT, self._on_bridge_tracking_event
            )
            self._unsubs.append(unsub)

    def _on_bridge_tracking_event(self, event: Event) -> None:
        """Record bridge-active device_ids alongside native mode.

        Native mode handles signal processing via the receiver subscription;
        this listener exists purely so the UI can show ``RX-BRIDGE`` for
        ESPHome devices that still emit legacy bus events from a residual
        ``on_pronto:`` YAML block. Cheap, runs on the bus thread.
        """
        device_id = (event.data or {}).get("device_id")
        if isinstance(device_id, str) and device_id:
            self._bridge_active_device_ids.add(device_id)

    async def _start_native_receivers(self) -> None:
        """Subscribe to all native ``InfraredReceiverEntity`` instances.

        Uses ``infrared.async_subscribe_receiver()`` from HA 2026.6+.
        Both helpers are synchronous ``@callback`` functions (not coroutines).
        Raises ``ImportError`` if the API is not available (pre-2026.6).
        """
        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_get_receivers,
            async_subscribe_receiver,
        )

        receivers = async_get_receivers(self._hass)
        if not receivers:
            _LOGGER.info(
                "Native receiver API available but no receivers found; "
                "falling back to legacy event bus"
            )
            self._start_legacy_event_bus()
            return

        for receiver_entity_id in receivers:
            unsub = async_subscribe_receiver(
                self._hass,
                receiver_entity_id,
                self._on_received_signal,
            )
            self._unsubs.append(unsub)

        self._native_mode = True
        _LOGGER.info(
            "Signal monitor started (native mode, %d receiver(s))",
            len(receivers),
        )

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

    async def async_stop(self) -> None:
        """Stop listening, flush pending writes."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._signal_store.async_shutdown()
        _LOGGER.info("Signal monitor stopped")

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
        event_data = event.data or {}

        # Track this device as having an active bridge (regardless of
        # whether the signal passes downstream filters).
        device_id = event_data.get("device_id")
        if isinstance(device_id, str) and device_id:
            self._bridge_active_device_ids.add(device_id)

        # Filter out repeat frames (no command data).
        if EventParser.is_nec_repeat(event_data):
            return
        if EventParser.is_pronto_repeat(event_data):
            return
        parsed = EventParser.parse(event_data)
        if parsed is None:
            return

        await self._process_parsed_signal(parsed)

    async def _process_parsed_signal(self, parsed: Any) -> None:
        """Shared signal processing pipeline for both native and legacy paths.

        Steps:
        1. Compute fingerprints
        2. Check triggers (before known-command skip)
        3. Check known commands -- skip if already assigned
        4. Check dismiss list
        5. Rate limit check
        6. Repeat suppression check
        7-9. Find/create device + signal (under lock)
        10. Schedule save
        11. Fire HA event
        12. Notify subscribers
        """
        # Step 1: Compute fingerprints.
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

        # Step 2: Check triggers (before known-command skip so triggers
        # work for both assigned commands and unknown signals).
        if self._trigger_manager is not None:
            self._trigger_manager.on_signal(
                sig_fp, parsed.protocol, parsed.code, dev_fp
            )

        # Step 3: Check known commands.
        if self._matches_known_command(parsed):
            return

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
            return

        # Step 5: Rate limit.
        if not self._check_rate_limit(sig_fp):
            return

        # Step 6: Repeat suppression.
        if not self._check_repeat(sig_fp):
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

            signal = device.get_signal(sig_fp)
            if signal is None:
                signal = UnknownSignal(
                    fingerprint=sig_fp,
                    protocol=parsed.protocol,
                    code=parsed.code,
                    raw_timings=list(parsed.raw_timings) if parsed.raw_timings else [],
                    frequency=parsed.frequency,
                    first_seen=now_iso,
                    last_seen=now_iso,
                    hit_count=0,
                )
                device.signals.append(signal)

            signal.hit_count += 1
            signal.last_seen = now_iso
            device.hit_count += 1
            device.last_seen = now_iso

            # Evict if over buffer.
            if self._signal_store.device_count > 500:
                self._signal_store.evict()

        # Step 10: Schedule save.
        self._signal_store.schedule_save()

        # Step 11: Fire HA event.
        summary = {
            "device_id": device.id,
            "device_fingerprint": dev_fp,
            "signal_fingerprint": sig_fp,
            "protocol": parsed.protocol,
            "code": parsed.code,
            "hit_count": signal.hit_count,
            "device_hit_count": device.hit_count,
        }
        self._hass.bus.async_fire(EVENT_SIGNAL_DETECTED, summary)

        # Step 12: Notify subscribers.
        for callback in self._subscribers:
            try:
                callback(summary)
            except Exception:
                _LOGGER.exception("Error notifying signal subscriber")

    # -----------------------------------------------------------------
    # Native receiver callback (HA 2026.6+)
    # -----------------------------------------------------------------

    def _on_received_signal(self, signal: Any) -> None:
        """Handle a signal from the native ``InfraredReceiverEntity`` API.

        Called synchronously by HA's ``@callback`` subscription system.
        Converts the ``InfraredReceivedSignal`` to Pronto hex at the
        entry point, then schedules the async processing pipeline.
        """
        # Filter repeat frames.
        if EventParser.is_native_repeat(signal):
            return

        parsed = EventParser.parse_received_signal(signal)
        if parsed is None:
            return

        self._hass.async_create_task(self._process_parsed_signal(parsed))

    # -----------------------------------------------------------------
    # Known-command check
    # -----------------------------------------------------------------

    def _matches_known_command(self, parsed: Any) -> bool:
        """Return True if the parsed signal matches any existing HAIR command."""
        if not parsed.protocol or not parsed.code:
            return False
        for device in self._hair_store.get_all_devices():
            for cmd in device.commands:
                if cmd.protocol == parsed.protocol and cmd.code == parsed.code:
                    return True
        return False

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

    def _check_repeat(self, fingerprint: str) -> bool:
        """Return True if the event is NOT a repeat (passes suppression).

        Suppresses duplicate fingerprints within ``SIGNAL_REPEAT_SUPPRESS_MS``.
        """
        now = time.monotonic()
        last = self._last_seen_times.get(fingerprint)
        suppress_s = SIGNAL_REPEAT_SUPPRESS_MS / 1000.0

        if last is not None and (now - last) < suppress_s:
            return False

        self._last_seen_times[fingerprint] = now
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
        """Return unknown devices sorted by hit_count descending.

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

        return sorted(devices, key=lambda d: d.hit_count, reverse=True)

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
        signal_fingerprint: str,
        hair_device_id: str,
        command_name: str,
        command_category: str,
    ) -> dict[str, Any]:
        """Assign an unknown signal as a named command on a HAIR device.

        Uses lock-first pattern with structured return. Checks idempotency
        (rejects duplicate fingerprint on target device). Rolls back
        cleanly on any failure.

        Returns dict with ``success``, ``command_id``, or ``error``/``code``.
        """
        from .models import CaptureResult, CommandCategory

        async with self._lock:
            # Validate source.
            unknown_device = self._signal_store.get_device(device_id)
            if unknown_device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Unknown device not found"}
            signal = unknown_device.get_signal(signal_fingerprint)
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

            hair_device.add_command(ir_command)
            command_id = ir_command.id
            try:
                await self._hair_store.async_save()
            except Exception:
                hair_device.remove_command(command_id)
                _LOGGER.exception("Failed to save HAIR store during assign")
                return {"success": False, "code": "save_failed",
                        "error": "Failed to save command"}

        return {"success": True, "command_id": command_id}

    async def assign_to_new_device(
        self,
        device_id: str,
        signal_fingerprint: str,
        device_name: str,
        device_type: str,
        emitter_entity_ids: list[str],
        command_name: str,
        command_category: str,
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
            signal = unknown_device.get_signal(signal_fingerprint)
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
        return {
            "success": True,
            "command_id": command_id,
            "device_id": new_device_id,
            "device": new_device,
        }

    async def delete_signal(
        self, device_id: str, signal_fingerprint: str
    ) -> dict[str, Any]:
        """Delete a single signal from an unknown device.

        Fires ``hair_signal_removed`` on success. Removes the parent
        unknown device if no signals remain.

        Returns dict with ``success`` or ``error``/``code``.
        """
        async with self._lock:
            unknown_device = self._signal_store.get_device(device_id)
            if unknown_device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Unknown device not found"}
            if not unknown_device.remove_signal(signal_fingerprint):
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
            "signal_fingerprint": signal_fingerprint,
            "device_removed": device_emptied,
        })
        return {"success": True, "device_removed": device_emptied}

    async def test_signal(
        self, signal_fingerprint: str, emitter_entity_id: str
    ) -> dict[str, Any]:
        """Send an unknown signal through an emitter for user verification.

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
            signal = device.get_signal(signal_fingerprint)
            if signal is not None:
                break

        if signal is None:
            return {"success": False, "code": "signal_not_found",
                    "error": "Signal not found"}

        # Lazy imports: infrared component only available at runtime on HA 2026.4+.
        from homeassistant.components.infrared import (
            async_send_command as ir_send,
        )

        from .ir_command import build_command

        # Build an infrared_protocols.Command from the stored signal data.
        try:
            ir_cmd = build_command(
                protocol=signal.protocol,
                code=signal.code,
                raw_timings=signal.raw_timings,
                frequency=signal.frequency or 38000,
            )
        except ValueError as exc:
            return {"success": False, "code": "no_signal_data",
                    "error": str(exc)}

        try:
            await asyncio.wait_for(
                ir_send(self._hass, emitter_entity_id, ir_cmd),
                timeout=ASSIGN_SERVICE_TIMEOUT_S,
            )
        except (TimeoutError, asyncio.TimeoutError, asyncio.CancelledError):  # noqa: UP041
            return {"success": False, "code": "send_timeout",
                    "error": "Emitter timed out"}
        except Exception as exc:
            return {"success": False, "code": "send_failed",
                    "error": f"Emitter did not respond: {exc}"}

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
        self, device_id: str, pronto: str, alias: str = ""
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
            frequency = (
                round(result.frequency_khz * 1000)
                if result.frequency_khz
                else DEFAULT_CARRIER_FREQUENCY
            )
            signal = UnknownSignal(
                fingerprint=sig_fp,
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
            device.signals.append(signal)
            device.last_seen = now_iso
            await self._signal_store.async_save()
        return {"success": True, "signal": signal.to_dict()}

    async def set_signal_alias(
        self, device_id: str, signal_fingerprint: str, alias: str
    ) -> dict[str, Any]:
        """Set or clear the alias on a signal. Empty clears it."""
        async with self._lock:
            device = self._signal_store.get_device(device_id)
            if device is None:
                return {"success": False, "code": "device_not_found",
                        "error": "Remote not found"}
            signal = device.get_signal(signal_fingerprint)
            if signal is None:
                return {"success": False, "code": "signal_not_found",
                        "error": "Signal not found"}
            signal.alias = (alias or "").strip()
            await self._signal_store.async_save()
        return {"success": True, "alias": signal.alias}

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
            if device.source != "manual":
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
