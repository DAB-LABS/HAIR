"""Always-on IR signal monitor for HAIR.

Subscribes to ``esphome.remote_received`` events on the HA event bus,
groups observed signals by source device, and surfaces unknown IR
activity for user assignment.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant

from .const import (
    ASSIGN_SERVICE_TIMEOUT_S,
    DOMAIN,
    EVENT_SIGNAL_DETECTED,
    EVENT_SIGNAL_REMOVED,
    SIGNAL_CLUSTER_THRESHOLD,
    SIGNAL_RATE_LIMIT_PER_SEC,
    SIGNAL_REPEAT_SUPPRESS_MS,
)
from .event_parser import EventParser
from .models import UnknownDevice, UnknownSignal
from .signal_store import SignalStore
from .storage import HAIRStore

_LOGGER = logging.getLogger(__name__)

# HA event name fired by ESPHome ir_rf_proxy.
_ESPHOME_IR_EVENT = "esphome.remote_received"


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
    ) -> None:
        self._hass = hass
        self._signal_store = signal_store
        self._hair_store = hair_store
        self._unsub: CALLBACK_TYPE | None = None
        self._lock = asyncio.Lock()

        # Rate limiting: fingerprint -> list of event timestamps (monotonic).
        self._rate_buckets: dict[str, list[float]] = defaultdict(list)

        # Repeat suppression: fingerprint -> last event time (monotonic).
        self._last_seen_times: dict[str, float] = {}

        # Real-time subscribers (WebSocket push).
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []

    # -----------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------

    async def async_start(self) -> None:
        """Start listening for IR events."""
        if not self._signal_store.loaded:
            await self._signal_store.async_load()

        self._unsub = self._hass.bus.async_listen(
            _ESPHOME_IR_EVENT, self._on_ir_event
        )
        _LOGGER.info("Signal monitor started")

    async def async_stop(self) -> None:
        """Stop listening, flush pending writes."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await self._signal_store.async_shutdown()
        _LOGGER.info("Signal monitor stopped")

    # -----------------------------------------------------------------
    # Event handler
    # -----------------------------------------------------------------

    async def _on_ir_event(self, event: Event) -> None:
        """Handle an incoming IR event from the HA bus.

        Steps (plan v3 corrected ordering):
        1. Parse via EventParser (bail if unparseable or NEC repeat)
        2. Compute fingerprints
        3. Check known commands -- skip if already assigned
        4. Check dismiss list
        5. Rate limit check
        6. Repeat suppression check
        7-9. Find/create device + signal (under lock)
        10. Schedule save
        11. Fire HA event
        12. Notify subscribers
        """
        event_data = event.data or {}

        # Step 1: Parse.
        if EventParser.is_nec_repeat(event_data):
            return
        parsed = EventParser.parse(event_data)
        if parsed is None:
            return

        # Step 2: Compute fingerprints.
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

        # Step 3: Check known commands.
        if self._matches_known_command(parsed):
            return

        # Step 4: Check dismiss list.
        if self._signal_store.is_dismissed(dev_fp):
            return

        # Step 5: Rate limit.
        if not self._check_rate_limit(sig_fp):
            return

        # Step 6: Repeat suppression.
        if not self._check_repeat(sig_fp):
            return

        # Steps 7-9: Find/create device and signal (locked).
        now_iso = datetime.now(timezone.utc).isoformat()
        async with self._lock:
            device = self._signal_store.get_device_by_fingerprint(dev_fp)
            if device is None:
                device = UnknownDevice(
                    fingerprint=dev_fp,
                    protocol=parsed.protocol,
                    device_address=device_address,
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
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Error notifying signal subscriber")

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
    ) -> list[UnknownDevice]:
        """Return unknown devices sorted by hit_count descending.

        Args:
            include_dismissed: Include dismissed devices in results.
            min_hits: Minimum hit_count to include. Defaults to
                ``SIGNAL_CLUSTER_THRESHOLD``. Pass ``0`` to include all.
        """
        if min_hits is None:
            min_hits = SIGNAL_CLUSTER_THRESHOLD

        devices = self._signal_store.get_all_devices()
        if not include_dismissed:
            devices = [d for d in devices if not d.dismissed]
        if min_hits > 0:
            devices = [d for d in devices if d.hit_count >= min_hits]

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

            # Idempotency: reject if this fingerprint is already assigned.
            for cmd in hair_device.commands:
                if (cmd.protocol == signal.protocol
                        and cmd.code == signal.code
                        and cmd.protocol is not None
                        and cmd.code is not None):
                    return {"success": False, "code": "duplicate_signal",
                            "error": "Signal already assigned to this device"}

            # Build IRCommand from signal.
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

            # Mutate both stores in memory.
            hair_device.add_command(ir_command)
            command_id = ir_command.id
            unknown_device.remove_signal(signal_fingerprint)
            device_emptied = not unknown_device.signals
            if device_emptied:
                self._signal_store.remove_device(device_id)

            try:
                # Persist HAIRStore first (source of truth for commands).
                await self._hair_store.async_save()
            except Exception:
                # Rollback in-memory changes.
                hair_device.remove_command(command_id)
                if device_emptied:
                    self._signal_store.add_device(unknown_device)
                unknown_device.signals.append(signal)
                _LOGGER.exception("Failed to save HAIR store during assign")
                return {"success": False, "code": "save_failed",
                        "error": "Failed to save command"}

            try:
                # Persist SignalStore second.
                await self._signal_store.async_save()
            except Exception:
                # HAIRStore already saved with the command -- revert it.
                hair_device.remove_command(command_id)
                if device_emptied:
                    self._signal_store.add_device(unknown_device)
                unknown_device.signals.append(signal)
                try:
                    await self._hair_store.async_save()
                except Exception:
                    _LOGGER.exception(
                        "CRITICAL: Failed to rollback HAIR store after "
                        "signal store save failure"
                    )
                _LOGGER.exception("Failed to save signal store during assign")
                return {"success": False, "code": "save_failed",
                        "error": "Failed to update signal store"}

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

            # Add to HAIRStore in memory.
            self._hair_store.add_device(new_device)

            # Remove signal from unknowns in memory.
            unknown_device.remove_signal(signal_fingerprint)
            device_emptied = not unknown_device.signals
            if device_emptied:
                self._signal_store.remove_device(device_id)

            try:
                await self._hair_store.async_save()
            except Exception:
                # Rollback: remove device from store, restore signal.
                self._hair_store.remove_device(new_device_id)
                if device_emptied:
                    self._signal_store.add_device(unknown_device)
                unknown_device.signals.append(signal)
                _LOGGER.exception(
                    "Failed to save HAIR store during assign-new-device"
                )
                return {"success": False, "code": "save_failed",
                        "error": "Failed to save new device"}

            try:
                await self._signal_store.async_save()
            except Exception:
                # Rollback HAIRStore.
                self._hair_store.remove_device(new_device_id)
                if device_emptied:
                    self._signal_store.add_device(unknown_device)
                unknown_device.signals.append(signal)
                try:
                    await self._hair_store.async_save()
                except Exception:
                    _LOGGER.exception(
                        "CRITICAL: Failed to rollback HAIR store after "
                        "signal store save failure in assign-new-device"
                    )
                _LOGGER.exception(
                    "Failed to save signal store during assign-new-device"
                )
                return {"success": False, "code": "save_failed",
                        "error": "Failed to update signal store"}

        # Both stores persisted -- safe to register in HA now.
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
        from homeassistant.components.infrared import (  # noqa: E402
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
        except (TimeoutError, asyncio.TimeoutError, asyncio.CancelledError):
            return {"success": False, "code": "send_timeout",
                    "error": "Emitter timed out"}
        except Exception as exc:
            return {"success": False, "code": "send_failed",
                    "error": f"Emitter did not respond: {exc}"}

        return {"success": True}

    def clear_all(self) -> None:
        """Wipe the entire unknown signal catalog."""
        self._signal_store.clear_all()
        self._signal_store.schedule_save()

    # -----------------------------------------------------------------
    # Subscriber management (WebSocket push)
    # -----------------------------------------------------------------

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback for real-time signal notifications."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Remove a previously registered callback."""
        try:
            self._subscribers.remove(callback)
        except ValueError:
            pass
