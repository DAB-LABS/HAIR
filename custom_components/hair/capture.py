"""IR capture provider abstraction and implementations.

Supports two capture paths:
1. **Native (HA 2026.6+):** ``NativeCaptureProvider`` uses
   ``infrared.async_subscribe_receiver()`` for hardware-agnostic capture.
2. **ESPHome (legacy):** ``ESPHomeCaptureProvider`` listens to
   ``esphome.remote_received`` events on the HA bus.

Broadlink RX is not supported: its learn-mode packets are neither Pronto
nor raw timings, and it exposes no receive path HAIR can consume. The
receiver-list UI labels such devices RX-UNSUPPORTED.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    DEFAULT_CAPTURE_TIMEOUT,
    DEFAULT_CARRIER_FREQUENCY,
    DOMAIN,
    CaptureProviderType,
)
from .models import CaptureResult

_LOGGER = logging.getLogger(__name__)


class CaptureProvider(ABC):
    """Abstract base class for IR signal capture."""

    @property
    @abstractmethod
    def provider_type(self) -> CaptureProviderType:
        """The provider type identifier."""

    @property
    @abstractmethod
    def device_name(self) -> str:
        """Human-readable name of the capture device."""

    @abstractmethod
    async def async_start_capture(
        self, timeout: int = DEFAULT_CAPTURE_TIMEOUT
    ) -> None:
        """Enter learning/listening mode."""

    @abstractmethod
    async def async_stop_capture(self) -> None:
        """Exit learning mode and clean up."""

    @abstractmethod
    async def async_wait_for_signal(self) -> CaptureResult | None:
        """Block until signal received or timeout. Returns None on timeout."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if capture hardware is ready."""


class ESPHomeCaptureProvider(CaptureProvider):
    """Capture IR signals via an ESPHome remote_receiver component."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        device_id: str,
    ) -> None:
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._timeout = DEFAULT_CAPTURE_TIMEOUT
        self._unsubscribe = None
        self._signal_queue: asyncio.Queue[CaptureResult] = asyncio.Queue()
        self._running = False

    @property
    def provider_type(self) -> CaptureProviderType:
        return CaptureProviderType.ESPHOME

    @property
    def device_name(self) -> str:
        registry = dr.async_get(self._hass)
        device = registry.async_get(self._device_id)
        if device is None:
            return "ESPHome IR Receiver"
        return device.name_by_user or device.name or "ESPHome IR Receiver"

    async def async_start_capture(
        self, timeout: int = DEFAULT_CAPTURE_TIMEOUT
    ) -> None:
        if self._running:
            raise RuntimeError("ESPHome capture already running")
        self._timeout = timeout
        self._signal_queue = asyncio.Queue()
        self._running = True

        try:
            from homeassistant.components import esphome  # noqa: F401  # type: ignore
        except ImportError:
            self._running = False
            raise RuntimeError("ESPHome integration not available") from None

        # ESPHome publishes raw IR receiver events on the bus when the device
        # is configured with a remote_receiver yielding `dump:`. Register the
        # listener returned by ``callback_factory`` directly. Applying the
        # factory as a decorator on a stub (the pre-v0.4.0 code) registered
        # an unawaited coroutine object that never fired, so every legacy
        # capture session timed out (H1, 2026-06-09 third-party review).
        self._unsubscribe = self._hass.bus.async_listen(
            "esphome.remote_received",
            callback_factory(self._signal_queue, self._device_id),
        )

    async def async_wait_for_signal(self) -> CaptureResult | None:
        try:
            result = await asyncio.wait_for(
                self._signal_queue.get(), timeout=self._timeout
            )
            return result
        except (TimeoutError, asyncio.TimeoutError):  # noqa: UP041
            return None

    async def async_stop_capture(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self._running = False

    def is_available(self) -> bool:
        registry = dr.async_get(self._hass)
        device = registry.async_get(self._device_id)
        return device is not None and not device.disabled


def callback_factory(queue: asyncio.Queue, device_id: str):
    """Return an event listener that pushes captures to ``queue``.

    Defined at module scope so the closure capture is unambiguous and
    so tests can target it. Production wiring will translate ESPHome
    raw events into ``CaptureResult`` instances.
    """

    async def _listener(event):
        data = event.data or {}
        if data.get("device_id") not in (device_id, None):
            return
        timings = data.get("raw") or data.get("raw_timings") or []
        result = CaptureResult(
            protocol=data.get("protocol"),
            code=data.get("code"),
            raw_timings=list(timings),
            frequency=int(data.get("frequency", DEFAULT_CARRIER_FREQUENCY)),
            confidence=float(data.get("confidence", 1.0)),
        )
        await queue.put(result)

    return _listener


class NativeCaptureProvider(CaptureProvider):
    """Capture IR signals via native ``InfraredReceiverEntity`` (HA 2026.6+).

    Uses ``infrared.async_subscribe_receiver()`` to listen on a specific
    receiver entity during capture sessions.  Hardware-agnostic -- works
    with any integration implementing the receiver entity.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        receiver_entity_id: str,
    ) -> None:
        self._hass = hass
        self._receiver_entity_id = receiver_entity_id
        self._timeout = DEFAULT_CAPTURE_TIMEOUT
        self._unsubscribe = None
        self._signal_queue: asyncio.Queue[CaptureResult] = asyncio.Queue()
        self._running = False

    @property
    def provider_type(self) -> CaptureProviderType:
        return CaptureProviderType.NATIVE

    @property
    def device_name(self) -> str:
        state = self._hass.states.get(self._receiver_entity_id)
        if state is not None:
            name = state.attributes.get("friendly_name")
            if name:
                return str(name)
        return self._receiver_entity_id

    async def async_start_capture(
        self, timeout: int = DEFAULT_CAPTURE_TIMEOUT
    ) -> None:
        if self._running:
            raise RuntimeError("Native capture already running")
        self._timeout = timeout
        self._signal_queue = asyncio.Queue()
        self._running = True

        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_subscribe_receiver,
        )

        from .event_parser import EventParser

        def _on_signal(signal) -> None:
            """Convert native signal to CaptureResult and enqueue (sync callback)."""
            parsed = EventParser.parse_received_signal(signal)
            if parsed is not None:
                self._signal_queue.put_nowait(parsed)

        self._unsubscribe = async_subscribe_receiver(
            self._hass,
            self._receiver_entity_id,
            _on_signal,
        )

    async def async_wait_for_signal(self) -> CaptureResult | None:
        try:
            result = await asyncio.wait_for(
                self._signal_queue.get(), timeout=self._timeout
            )
            return result
        except (TimeoutError, asyncio.TimeoutError):  # noqa: UP041
            return None

    async def async_stop_capture(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self._running = False

    def is_available(self) -> bool:
        state = self._hass.states.get(self._receiver_entity_id)
        return state is not None


class MockCaptureProvider(CaptureProvider):
    """Mock provider for tests."""

    def __init__(
        self,
        result: CaptureResult | None = None,
        delay: float = 0.05,
        fail: bool = False,
        device_name: str = "Mock IR Receiver",
    ) -> None:
        self._result = result or CaptureResult(
            protocol="NEC",
            code="0xDEADBEEF",
            raw_timings=[9000, -4500, 560, -560, 560, -1690],
            frequency=DEFAULT_CARRIER_FREQUENCY,
            confidence=1.0,
        )
        self._delay = delay
        self._fail = fail
        self._available = True
        self._cancelled = False
        self._device_name = device_name
        self._started = False

    @property
    def provider_type(self) -> CaptureProviderType:
        return CaptureProviderType.MOCK

    @property
    def device_name(self) -> str:
        return self._device_name

    async def async_start_capture(
        self, timeout: int = DEFAULT_CAPTURE_TIMEOUT
    ) -> None:
        if self._fail:
            raise RuntimeError("Mock capture configured to fail")
        self._started = True
        self._cancelled = False

    async def async_wait_for_signal(self) -> CaptureResult | None:
        if not self._started:
            raise RuntimeError("Capture not started")
        await asyncio.sleep(self._delay)
        if self._cancelled:
            return None
        return self._result

    async def async_stop_capture(self) -> None:
        self._cancelled = True
        self._started = False

    def is_available(self) -> bool:
        return self._available

    def set_available(self, value: bool) -> None:
        self._available = value


def _get_bridge_active_device_ids(hass: HomeAssistant) -> set[str]:
    """Return HA device IDs whose ESPHome bridge has fired events this session.

    Looks up the active ``SignalMonitor`` instance via ``hass.data`` and
    returns its bridge-tracking set. Returns an empty set if HAIR isn't
    fully set up yet (e.g. during config flow), so callers can iterate
    without needing a None check.
    """
    entries = hass.data.get(DOMAIN, {})
    for value in entries.values():
        if not isinstance(value, dict):
            continue
        monitor = value.get("signal_monitor")
        if monitor is not None and hasattr(monitor, "bridge_active_device_ids"):
            return set(monitor.bridge_active_device_ids)
    return set()


def _has_ir_entities(ent_registry: Any, device_id: str) -> bool:
    """Return True if the device has IR-related entities.

    Checks for ``infrared.*`` entities (ESPHome ``ir_rf_proxy``) or
    ``remote.*`` entities as a fallback.  Non-IR ESPHome devices
    (sensors, switches, lights, etc.) are excluded.
    """
    entities = er.async_entries_for_device(ent_registry, device_id)
    for entity in entities:
        entity_id = entity.entity_id if hasattr(entity, "entity_id") else str(entity)
        if entity_id.startswith("infrared.") or entity_id.startswith("remote."):
            return True
    return False


async def get_available_capture_providers(
    hass: HomeAssistant,
) -> list[dict[str, Any]]:
    """Discover available capture-capable devices.

    Returns lightweight dicts (not provider instances) suitable for
    sending over WebSocket. Provider instances are constructed on
    demand by ``get_capture_provider_for_device``.

    On HA 2026.6+, native ``InfraredReceiverEntity`` instances are
    discovered first.  Falls back to ESPHome device scanning (the legacy
    event-bus bridge) for older HA versions. Broadlink is not discovered
    for capture -- it has no receive path HAIR can consume.
    """
    providers: list[dict[str, Any]] = []

    # Native receivers (HA 2026.6+).
    native_receiver_ids: set[str] = set()
    try:
        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_get_receivers,
        )

        receivers = async_get_receivers(hass)
        for entity_id in receivers:
            native_receiver_ids.add(entity_id)
            state = hass.states.get(entity_id)
            name = entity_id
            if state is not None:
                name = state.attributes.get("friendly_name", entity_id)
            providers.append(
                {
                    "type": str(CaptureProviderType.NATIVE),
                    "device_id": entity_id,
                    "name": str(name),
                    "config_entry_id": None,
                    "receiver_entity_id": entity_id,
                }
            )
    except (ImportError, AttributeError):
        pass  # Pre-2026.6: no native receiver API.

    # ESPHome devices via the legacy event-bus bridge.
    #
    # We can't introspect a device's YAML to know whether ``on_pronto:``
    # is configured, so the only reliable signal is "have we seen an
    # ``esphome.remote_received`` event from this device this session?"
    # The signal monitor records that set; we surface bridge providers
    # only for those devices. This means: after HA restart, the bridge
    # badge stays hidden until the user presses a button on a remote
    # whose ESPHome host actually forwards events. That trade-off is
    # acceptable -- the badge is informational, and once a bridge is
    # detected it stays surfaced for the rest of the HA session.
    bridge_active_device_ids = _get_bridge_active_device_ids(hass)
    if "esphome" in hass.config.components and bridge_active_device_ids:
        dev_registry = dr.async_get(hass)
        ent_registry = er.async_get(hass)
        for entry in hass.config_entries.async_entries("esphome"):
            for device in dr.async_entries_for_config_entry(
                dev_registry, entry.entry_id
            ):
                if device.id not in bridge_active_device_ids:
                    continue
                if not _has_ir_entities(ent_registry, device.id):
                    continue
                providers.append(
                    {
                        "type": str(CaptureProviderType.ESPHOME),
                        "device_id": device.id,
                        "name": device.name_by_user
                        or device.name
                        or "ESPHome IR device",
                        "config_entry_id": entry.entry_id,
                    }
                )

    # Broadlink RX is intentionally NOT discovered. Broadlink exposes IR
    # transmit through HA's infrared platform but has no receive path HAIR
    # can consume (it does not fire esphome.remote_received and does not
    # implement InfraredReceiverEntity), and its learn-mode packets are
    # not Pronto or raw timings. The receiver-list UI labels such devices
    # RX-UNSUPPORTED. If Broadlink upstream adopts InfraredReceiverEntity,
    # HAIR picks it up automatically via the native path above. (H2,
    # 2026-06-09 third-party review.)

    return providers


async def get_capture_provider_for_device(
    hass: HomeAssistant,
    provider_type: CaptureProviderType,
    device_id: str,
    config_entry_id: str | None = None,
) -> CaptureProvider | None:
    """Construct a capture provider instance for a given device."""
    if provider_type == CaptureProviderType.NATIVE:
        # device_id is the receiver entity_id for native providers.
        return NativeCaptureProvider(hass, device_id)

    if provider_type == CaptureProviderType.ESPHOME:
        if config_entry_id is None:
            registry = dr.async_get(hass)
            device = registry.async_get(device_id)
            if device is None:
                return None
            config_entry_id = next(iter(device.config_entries), None)
        if config_entry_id is None:
            return None
        return ESPHomeCaptureProvider(hass, config_entry_id, device_id)

    if provider_type == CaptureProviderType.MOCK:
        return MockCaptureProvider()

    return None
