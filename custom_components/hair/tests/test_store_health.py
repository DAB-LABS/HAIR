"""The Sniffer stopped saving and said nothing (0.10.1 item 1).

WHAT HAPPENED, from the 0.10.0 regression bench. One capture decoded to
a ``decoded_command`` of about 1.5e23. Home Assistant's store writer
refuses an integer that size and refuses the WHOLE payload with it, so
every Sniffer save failed for eighty minutes (17:14 to 18:35 UTC on the
box) until the 200-signal cap happened to evict the offending row and
saves resumed on their own. HAIR's log and UI said nothing; only HA core
logged the failed writes.

Two halves, tested here:

- The cause. A decoded field that cannot be stored is refused at decode
  time and the signal is kept undecoded, which loses nothing: the raw
  timings are authoritative and the raw identity tiers still match it.
  Refused, not clamped -- a truncated identity is a WRONG identity, and
  a wrong one would match the wrong command forever.
- The symptom, for any future cause. A failed save raises ONE warning
  and ONE persistent notification, never one per write, and the next
  good save clears both.

THE FIXTURE. The row that actually broke the store was evicted by the
cap before the bench agent could capture it. What is saved here is a
live sibling from the same Sniffer group and the same decoder family, a
KASEIKYO64 whose command is 46 bits. It is the guard's other half: a
legitimately large value that must still decode, so the refusal cannot
quietly grow into "Kaseikyo does not decode any more".
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.protocol_decode import (
    _MAX_DECODED_FIELD,
    decode_to_fields,
    try_decode_identity,
)
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.storage import HAIRStore
from custom_components.hair.store_health import StoreHealth

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "kaseikyo64-oversize-sibling.json"
)


def _fixture() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))["signal"]


# ---------------------------------------------------------------------------
# The decode guard
# ---------------------------------------------------------------------------


class _Spec:
    """A registry spec whose decoder returns whatever we hand it."""

    def __init__(self, label, address, command, extras=None):
        self.key = "toy"
        self.labels = (label,)
        self.source = "local"
        self.tx_rebuild = False
        self.seek = None
        self.salvage = None
        self._values = (label, address, command, extras)

        class _Cmd:
            @staticmethod
            def from_raw_timings(timings):
                return object()

        self.command_cls = _Cmd
        self.extract = lambda cmd: self._values
        self.construct = None


def _with_registry(*specs):
    return patch(
        "custom_components.hair.protocol_decode._ensure_registry",
        return_value=list(specs),
    )


def test_an_oversize_command_is_refused(caplog):
    """The bench value: 77 bits, which no IR protocol HAIR decodes can
    produce and no HA store can hold."""
    oversize = 151134183299896320196608
    assert oversize > _MAX_DECODED_FIELD

    with _with_registry(_Spec("KASEIKYO64", 0xDA11, oversize)), caplog.at_level(
        logging.DEBUG, logger="custom_components.hair.protocol_decode"
    ):
        identity = try_decode_identity([100, -100, 100, -100])

    assert identity is None
    assert "out-of-range field" in caplog.text
    assert "KASEIKYO64" in caplog.text


def test_an_oversize_address_is_refused():
    with _with_registry(_Spec("TOY", _MAX_DECODED_FIELD, 1)):
        assert try_decode_identity([100, -100]) is None


def test_an_oversize_extra_is_refused():
    """Extras are stored beside the triple and break the same write."""
    with _with_registry(
        _Spec("TOY", 1, 2, {"toggle": _MAX_DECODED_FIELD + 5})
    ):
        assert try_decode_identity([100, -100]) is None


def test_a_negative_field_is_refused():
    with _with_registry(_Spec("TOY", 1, -3)):
        assert try_decode_identity([100, -100]) is None


def test_the_probe_moves_on_to_the_next_spec():
    """A refusal is not a decision about the signal, only about that
    decoder, so a later spec still gets its turn."""
    with _with_registry(
        _Spec("BAD", 1, _MAX_DECODED_FIELD), _Spec("GOOD", 0x11, 0x22)
    ):
        identity = try_decode_identity([100, -100])

    assert identity is not None
    assert identity.protocol == "GOOD"
    assert identity.command == 0x22


def test_a_value_at_the_boundary_is_kept():
    with _with_registry(_Spec("TOY", 0, _MAX_DECODED_FIELD - 1)):
        identity = try_decode_identity([100, -100])

    assert identity is not None
    assert identity.command == _MAX_DECODED_FIELD - 1


def test_decode_to_fields_reports_all_none():
    with _with_registry(_Spec("TOY", 1, _MAX_DECODED_FIELD)):
        assert decode_to_fields([100, -100]) == (None, None, None, None)


def test_identity_from_command_refuses_too():
    from custom_components.hair.protocol_decode import identity_from_command

    spec = _Spec("TOY", 1, _MAX_DECODED_FIELD)
    with _with_registry(spec):
        assert identity_from_command(spec.command_cls()) is None


class TestTheBenchFixture:
    """A real 46-bit KASEIKYO64 from the offending row's own group."""

    def test_the_sibling_still_decodes(self):
        signal = _fixture()
        assert signal["decoded_command"] > 0xFFFFFFFF

        identity = try_decode_identity(signal["raw_timings"])

        assert identity is not None
        assert identity.protocol == signal["decoded_protocol"]
        assert identity.address == signal["decoded_address"]
        assert identity.command == signal["decoded_command"]
        assert identity.fingerprint == signal["decoded_fingerprint"]

    def test_the_sibling_round_trips_through_the_store(self, fake_hass):
        """A value this size is legal and must survive a save/load."""
        from custom_components.hair.models import UnknownDevice, UnknownSignal

        signal = _fixture()
        unknown = UnknownSignal(
            fingerprint=signal["fingerprint"],
            byte_hash=signal["byte_hash"],
            protocol=signal["protocol"],
            code=signal["code"],
            raw_timings=list(signal["raw_timings"]),
            frequency=signal["frequency"],
            decoded_protocol=signal["decoded_protocol"],
            decoded_address=signal["decoded_address"],
            decoded_command=signal["decoded_command"],
            decoded_fingerprint=signal["decoded_fingerprint"],
        )
        device = UnknownDevice(
            fingerprint="grp", label="Test AC", signals=[unknown]
        )

        restored = UnknownDevice.from_dict(
            json.loads(json.dumps(device.to_dict()))
        )

        assert restored.signals[0].decoded_command == signal[
            "decoded_command"
        ]


# ---------------------------------------------------------------------------
# The save-failure surface
# ---------------------------------------------------------------------------


class _Recorder:
    """Stands in for persistent_notification."""

    def __init__(self):
        self.created: list[tuple] = []
        self.dismissed: list[str] = []

    def async_create(self, hass, message, title=None, notification_id=None):
        self.created.append((message, title, notification_id))

    def async_dismiss(self, hass, notification_id):
        self.dismissed.append(notification_id)


def _notifications():
    recorder = _Recorder()
    return recorder, patch.dict(
        "sys.modules",
        {"homeassistant.components.persistent_notification": recorder},
    )


def test_one_warning_and_one_notification_on_the_first_failure(caplog):
    recorder, patched = _notifications()
    health = StoreHealth(MagicMock(), "signals", "Sniffer catalog")

    with patched, caplog.at_level(
        logging.WARNING, logger="custom_components.hair.store_health"
    ):
        health.note_failure(OSError("disk full"))

    assert caplog.text.count("could not save") == 1
    assert len(recorder.created) == 1
    assert recorder.created[0][2] == "hair_store_save_failed_signals"


def test_further_failures_are_silent(caplog):
    recorder, patched = _notifications()
    health = StoreHealth(MagicMock(), "signals", "Sniffer catalog")

    with patched, caplog.at_level(
        logging.WARNING, logger="custom_components.hair.store_health"
    ):
        health.note_failure(OSError("one"))
        health.note_failure(OSError("two"))
        health.note_failure(OSError("three"))

    assert caplog.text.count("could not save") == 1
    assert len(recorder.created) == 1


def test_a_good_save_clears_it_and_says_so(caplog):
    recorder, patched = _notifications()
    health = StoreHealth(MagicMock(), "signals", "Sniffer catalog")

    with patched, caplog.at_level(
        logging.INFO, logger="custom_components.hair.store_health"
    ):
        health.note_failure(OSError("one"))
        health.note_failure(OSError("two"))
        health.note_success()

    assert recorder.dismissed == ["hair_store_save_failed_signals"]
    assert "saving again after 2 failed save(s)" in caplog.text
    assert health.failing is False


def test_a_good_save_with_nothing_wrong_says_nothing(caplog):
    recorder, patched = _notifications()
    health = StoreHealth(MagicMock(), "signals", "Sniffer catalog")

    with patched, caplog.at_level(
        logging.DEBUG, logger="custom_components.hair.store_health"
    ):
        health.note_success()
        health.note_success()

    assert recorder.created == []
    assert recorder.dismissed == []
    assert caplog.text == ""


def test_it_speaks_again_after_recovering(caplog):
    recorder, patched = _notifications()
    health = StoreHealth(MagicMock(), "signals", "Sniffer catalog")

    with patched, caplog.at_level(
        logging.WARNING, logger="custom_components.hair.store_health"
    ):
        health.note_failure(OSError("one"))
        health.note_success()
        health.note_failure(OSError("again"))

    assert caplog.text.count("could not save") == 2
    assert len(recorder.created) == 2


def test_two_stores_raise_two_notices():
    signals = StoreHealth(MagicMock(), "signals", "Sniffer catalog")
    devices = StoreHealth(MagicMock(), "devices", "device catalog")
    assert signals.notification_id != devices.notification_id


def test_a_broken_notification_service_never_breaks_a_save(caplog):
    class _Explodes:
        def async_create(self, *a, **kw):
            raise RuntimeError("no notifier")

    health = StoreHealth(MagicMock(), "signals", "Sniffer catalog")
    with patch.dict(
        "sys.modules",
        {"homeassistant.components.persistent_notification": _Explodes()},
    ):
        health.note_failure(OSError("disk full"))

    assert health.failing is True


@pytest.mark.asyncio
async def test_the_signal_store_surfaces_and_recovers(fake_hass):
    recorder, patched = _notifications()
    store = SignalStore(fake_hass)
    store._loaded = True
    store._store = MagicMock()
    store._store.async_save = AsyncMock(side_effect=OSError("refused"))

    with patched:
        await store.async_save()
        assert len(recorder.created) == 1

        store._store.async_save = AsyncMock()
        await store.async_save()

    assert recorder.dismissed == ["hair_store_save_failed_signals"]


@pytest.mark.asyncio
async def test_a_refused_signal_save_does_not_raise(fake_hass):
    """It is called as a fire-and-forget task off the capture path, so
    raising would lose the report and could take a capture with it."""
    _recorder, patched = _notifications()
    store = SignalStore(fake_hass)
    store._loaded = True
    store._store = MagicMock()
    store._store.async_save = AsyncMock(side_effect=OSError("refused"))

    with patched:
        await store.async_save()


@pytest.mark.asyncio
async def test_the_device_store_surfaces_and_recovers(fake_hass):
    recorder, patched = _notifications()
    store = HAIRStore(fake_hass)
    store._loaded = True
    store._store = MagicMock()
    store._store.async_save = AsyncMock(side_effect=OSError("refused"))

    with patched:
        await store.async_save()
        assert recorder.created[0][2] == "hair_store_save_failed_devices"

        store._store.async_save = AsyncMock()
        await store.async_save()

    assert recorder.dismissed == ["hair_store_save_failed_devices"]


# ---------------------------------------------------------------------------
# The failure a try/except cannot see (bench find, 2026-08-19)
# ---------------------------------------------------------------------------
#
# HA's Store._async_handle_write_data catches SerializationError and
# WriteError and logs them at ERROR rather than re-raising, so the exact
# failure class this ticket exists for never reaches the caller's await.
# That is also the real answer to "why was it invisible": HAIR had
# nothing to catch. These pin the log-record path, which is the only
# place the truth exists.


def _ha_error(key: str, message: str = "Bad data at $.data") -> None:
    """Emit the record HA emits when a store write is refused."""
    logging.getLogger("homeassistant.helpers.storage").error(
        "Error writing config for %s: %s", key, message
    )


@pytest.mark.asyncio
async def test_a_swallowed_write_error_still_surfaces(fake_hass, caplog):
    recorder, patched = _notifications()
    store = SignalStore(fake_hass)
    store._loaded = True
    store._store = MagicMock()

    async def _save_that_ha_swallows(payload):
        # Exactly what HA does: log, do not raise.
        _ha_error("hair_unknown_signals")

    store._store.async_save = _save_that_ha_swallows

    with patched, caplog.at_level(
        logging.WARNING, logger="custom_components.hair.store_health"
    ):
        await store.async_save()

    assert store._health.failing is True
    # The whole point of the watcher: HAIR speaks for itself rather than
    # leaving HA's ERROR as the only record.
    assert caplog.text.count("could not save") == 1
    assert "Sniffer catalog" in caplog.text
    assert len(recorder.created) == 1
    assert recorder.created[0][2] == "hair_store_save_failed_signals"


@pytest.mark.asyncio
async def test_the_swallowed_case_clears_on_the_next_good_save(fake_hass):
    recorder, patched = _notifications()
    store = SignalStore(fake_hass)
    store._loaded = True
    store._store = MagicMock()

    async def _bad(payload):
        _ha_error("hair_unknown_signals")

    store._store.async_save = _bad
    with patched:
        await store.async_save()
        store._store.async_save = AsyncMock()
        await store.async_save()

    assert store._health.failing is False
    assert recorder.dismissed == ["hair_store_save_failed_signals"]


@pytest.mark.asyncio
async def test_another_stores_write_error_is_not_ours(fake_hass):
    """Keyed on the store's own key, which HA passes as the first
    record argument."""
    recorder, patched = _notifications()
    store = SignalStore(fake_hass)
    store._loaded = True
    store._store = MagicMock()

    async def _someone_elses(payload):
        _ha_error("core.restore_state")

    store._store.async_save = _someone_elses

    with patched:
        await store.async_save()

    assert store._health.failing is False
    assert recorder.created == []


@pytest.mark.asyncio
async def test_an_unrelated_storage_error_is_not_a_write_failure(fake_hass):
    recorder, patched = _notifications()
    store = SignalStore(fake_hass)
    store._loaded = True
    store._store = MagicMock()

    async def _noise(payload):
        logging.getLogger("homeassistant.helpers.storage").error(
            "Could not read %s: %s", "hair_unknown_signals", "boom"
        )

    store._store.async_save = _noise

    with patched:
        await store.async_save()

    assert store._health.failing is False
    assert recorder.created == []


@pytest.mark.asyncio
async def test_the_device_store_hears_its_own_key(fake_hass):
    recorder, patched = _notifications()
    store = HAIRStore(fake_hass)
    store._loaded = True
    store._store = MagicMock()

    async def _bad(payload):
        _ha_error("hair_devices")

    store._store.async_save = _bad

    with patched:
        await store.async_save()

    assert recorder.created[0][2] == "hair_store_save_failed_devices"


def test_the_watcher_never_raises_into_logging():
    """A logging handler that raises would break logging itself."""
    from custom_components.hair.store_health import _WriteErrorWatcher

    watcher = _WriteErrorWatcher()
    watcher.watch("k", MagicMock())
    for record in (
        logging.LogRecord("homeassistant.helpers.storage", logging.ERROR,
                          "", 0, "Error writing config for %s: %s", None, None),
        logging.LogRecord("homeassistant.helpers.storage", logging.ERROR,
                          "", 0, "Error writing config for %s", ("k",), None),
        logging.LogRecord("other.logger", logging.ERROR, "", 0,
                          "Error writing config for %s: %s", ("k", "x"), None),
    ):
        watcher.emit(record)
