"""Signpost 4, Track M: a matrix Remote hears its own lattice.

The contracts under test:

- The cell index carries the decoded, (fingerprint, byte_hash) and
  byte_hash tiers, and deliberately NOT the bare-fingerprint tier -- an
  AC branch's frames are S/L neighbours, so a fingerprint-only match
  would name the wrong state, and a wrong state is worse than none.
- A heard cell stamps last_heard, fires hair_state_heard with the
  coordinates and the v0.5.7 location trio, and pushes down the panel's
  existing subscription with a kind discriminator.
- Receiver scope applies (the remote's own list), one physical press
  heard by two receivers records once, and a matrix write invalidates
  the index.
- The remote's HA device offers one state-heard row, and only when it
  actually carries a lattice.
"""
from __future__ import annotations

import csv as _csv
import gzip as _gzip
import io as _io
import json as _json
import logging as _logging
from pathlib import Path as _Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import matrix_listener as _ml
from custom_components.hair.const import (
    DOMAIN,
    EVENT_STATE_HEARD,
    MATRIX_STATE_DEDUP_WINDOW_S,
)
from custom_components.hair.identity import TIER_BYTE_HASH, TIER_NORM_FP
from custom_components.hair.matrix_listener import (
    CellIndex,
    MatrixListener,
    build_cell_index,
)
from custom_components.hair.models import TriggerRemote
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

PRONTO_COOL_22 = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_COOL_23 = "0000 006D 0002 0000 0040 0020 0040 0020"
PRONTO_OFF = "0000 006D 0002 0000 0020 0020 0040 0040"
# A second unit's codes for the same states. Different bytes on
# purpose: a pinned send that came out of the wrong lattice is then a
# visible failure rather than a coincidence.
PRONTO_DEV_22 = "0000 006D 0002 0000 0060 0080 0060 0080"
PRONTO_DEV_23 = "0000 006D 0002 0000 0080 0060 0080 0060"
PRONTO_DEV_OFF = "0000 006D 0002 0000 0060 0060 0080 0080"


def _matrix() -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool"],
        fan_modes=["auto"],
        swing_modes=[],
        off=PRONTO_OFF,
        cells=[
            ClimateCell(
                mode="cool", fan="auto", temp=22.0, pronto=PRONTO_COOL_22
            ),
            ClimateCell(
                mode="cool", fan="auto", temp=23.0, pronto=PRONTO_COOL_23
            ),
        ],
    )


def _device_matrix(
    fan: str = "auto",
    prontos: tuple[str, str] = (PRONTO_DEV_22, PRONTO_DEV_23),
    off: str = PRONTO_DEV_OFF,
) -> ClimateMatrix:
    """The lattice on the PINNED DEVICE side.

    Same shape as the remote's, with its own bytes, and a fan word the
    caller can change: two wigs for one air conditioner need not spell
    the dimensions the same way.
    """
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool"],
        fan_modes=[fan],
        swing_modes=[],
        off=off,
        cells=[
            ClimateCell(mode="cool", fan=fan, temp=22.0, pronto=prontos[0]),
            ClimateCell(mode="cool", fan=fan, temp=23.0, pronto=prontos[1]),
        ],
    )


def _identity(pronto: str):
    from custom_components.hair.wig_identity import wig_signal_identity

    identity = wig_signal_identity(pronto)
    assert identity is not None
    return identity


def _hass(store):
    hass = MagicMock()
    hass.data = {DOMAIN: {"entry-1": {"store": store, "device_manager": MagicMock()}}}
    hass.config.config_dir = "/config"
    hass.config.units.temperature_unit = "°C"
    hass.bus.async_fire = MagicMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    return hass


def _store_with(*remotes):
    store = MagicMock()
    store.get_all_trigger_remotes = MagicMock(return_value=list(remotes))
    store.get_trigger_remote = MagicMock(
        side_effect=lambda rid: next(
            (r for r in remotes if r.id == rid), None
        )
    )
    store.update_trigger_remote = MagicMock()
    store.async_save = AsyncMock()
    return store


def _listener_ready(remote, store=None, trigger_manager=None, matrix=None):
    """A listener with the remote's index already built.

    ``matrix`` overrides the toy lattice for the tests that need real
    codes (the air-path ones at the foot of this file).
    """
    lattice = matrix if matrix is not None else _matrix()
    store = store or _store_with(remote)
    hass = _hass(store)
    listener = MatrixListener(hass, store, trigger_manager)
    listener._matrix_cache[remote.id] = lattice
    listener._index_cache[remote.id] = build_cell_index(lattice)
    return hass, store, listener


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------


def test_index_carries_every_cell_and_both_power_codes():
    matrix = _matrix()
    matrix.on = "0000 006D 0002 0000 0040 0040 0020 0020"
    index = build_cell_index(matrix)

    names = {hit.cell_name for hit in index.fp_bytehash.values()}
    assert "cool / fan: auto / 22" in names
    assert "cool / fan: auto / 23" in names
    powers = {hit.power for hit in index.fp_bytehash.values()}
    assert powers == {None, "off", "on"}


def test_index_matches_a_cell_by_fingerprint_and_hash():
    index = build_cell_index(_matrix())
    identity = _identity(PRONTO_COOL_22)

    hit, tier = index.match(
        identity.decoded_fingerprint, identity.fingerprint, identity.byte_hash
    )
    assert tier == TIER_BYTE_HASH
    assert hit.cell_key == "cool/auto/22"
    assert hit.mode == "cool"
    assert hit.fan == "auto"
    assert hit.temp == 22.0
    assert hit.power is None
    assert hit.sl_pattern


def test_index_matches_by_byte_hash_alone():
    """The tier that carries most AC frames: a receiver's jitter flips
    the S/L fingerprint, the bytes do not."""
    index = build_cell_index(_matrix())
    identity = _identity(PRONTO_COOL_23)

    hit, tier = index.match(None, "a-fingerprint-from-another-capture",
                            identity.byte_hash)
    assert tier == TIER_BYTE_HASH
    assert hit.cell_key == "cool/auto/23"


def test_index_matches_the_form_that_comes_off_the_air():
    """The bench find (2026-08-17): a capture is rebuilt from raw
    timings, and ProntoCommand's trailing-space strip moves BOTH the
    fingerprint and the byte hash, so a cell indexed only under its
    file form would never match anything a handset sends."""
    from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto

    index = build_cell_index(_matrix())
    command = ProntoCommand(PRONTO_COOL_22)
    wire = raw_to_pronto(
        command.get_raw_timings(), frequency=command.modulation
    )
    heard = _identity(wire)

    hit, _tier = index.match(
        heard.decoded_fingerprint, heard.fingerprint, heard.byte_hash
    )
    assert hit.cell_key == "cool/auto/22"


def test_index_keeps_the_file_form_too():
    """Both forms share one CellHit, so a paste of the stored code
    resolves to the same state a heard frame does."""
    index = build_cell_index(_matrix())
    filed = _identity(PRONTO_COOL_23)

    hit, _tier = index.match(
        filed.decoded_fingerprint, filed.fingerprint, filed.byte_hash
    )
    assert hit.cell_key == "cool/auto/23"


def test_index_never_matches_on_a_bare_fingerprint():
    """The missing tier, on purpose. A frame with no hash and no decoded
    identity is not enough to name a state."""
    index = build_cell_index(_matrix())
    identity = _identity(PRONTO_COOL_22)

    assert index.match(None, identity.fingerprint, None) is None


def test_index_skips_a_cell_whose_pronto_is_broken():
    matrix = _matrix()
    matrix.cells.append(
        ClimateCell(mode="dry", fan="auto", pronto="not a pronto code")
    )
    index = build_cell_index(matrix)

    assert not any(hit.mode == "dry" for hit in index.fp_bytehash.values())


def test_index_names_cells_in_the_display_unit():
    """Names are the human surface, so they follow the install's unit
    (the device card's live-surface rule)."""
    index = build_cell_index(_matrix(), display_unit="F")

    names = {hit.cell_name for hit in index.fp_bytehash.values()}
    assert "cool / fan: auto / 72" in names


def test_empty_index_is_falsey():
    assert not CellIndex()


# ---------------------------------------------------------------------------
# Hearing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heard_cell_stamps_last_heard_and_fires_the_event():
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=("area-1", "Bedroom"))
    hass, store, listener = _listener_ready(remote, trigger_manager=tm)
    identity = _identity(PRONTO_COOL_22)

    heard = await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.bedroom",
    )

    assert heard == ["r1"]
    assert remote.last_heard["cell_key"] == "cool/auto/22"
    assert remote.last_heard["cell_name"] == "cool / fan: auto / 22"
    assert remote.last_heard["mode"] == "cool"
    assert remote.last_heard["temp"] == 22.0
    assert remote.last_heard["power"] is None
    assert remote.last_heard["receiver_entity_id"] == "infrared.bedroom"
    assert remote.last_heard["receiver_area_name"] == "Bedroom"
    assert remote.last_heard["sl_pattern"]
    assert remote.last_heard["at"]
    store.update_trigger_remote.assert_called_once_with(remote)

    event_type, event_data = hass.bus.async_fire.call_args[0]
    assert event_type == EVENT_STATE_HEARD
    assert event_data["remote_id"] == "r1"
    assert event_data["remote_name"] == "Bedroom AC"
    assert event_data["cell_key"] == "cool/auto/22"
    assert event_data["mode"] == "cool"
    assert event_data["fan"] == "auto"
    assert event_data["temp"] == 22.0
    assert event_data["receiver_area_id"] == "area-1"
    assert event_data["receiver_area_name"] == "Bedroom"


@pytest.mark.asyncio
async def test_heard_state_pushes_down_the_trigger_subscription():
    """One channel, two kinds of news: the panel's existing subscribe
    command carries the bloom, discriminated by kind."""
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=(None, None))
    _h, _s, listener = _listener_ready(remote, trigger_manager=tm)
    identity = _identity(PRONTO_COOL_22)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.bedroom",
    )

    payload = tm.notify_subscribers.call_args[0][0]
    assert payload["kind"] == "state_heard"
    assert payload["cell_key"] == "cool/auto/22"


@pytest.mark.asyncio
async def test_a_power_frame_is_heard_as_power():
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    _h, _s, listener = _listener_ready(remote)
    identity = _identity(PRONTO_OFF)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, None,
    )

    assert remote.last_heard["power"] == "off"
    assert remote.last_heard["cell_key"] == "off"
    assert remote.last_heard["mode"] is None


@pytest.mark.asyncio
async def test_two_receivers_hearing_one_press_record_once():
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    hass, _s, listener = _listener_ready(remote)
    identity = _identity(PRONTO_COOL_22)

    for receiver in ("infrared.bedroom", "infrared.hall"):
        await listener.on_signal_captured(
            identity.fingerprint, identity.byte_hash,
            identity.decoded_fingerprint, receiver,
        )

    assert hass.bus.async_fire.call_count == 1


@pytest.mark.asyncio
async def test_a_later_press_is_heard_again():
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    hass, _s, listener = _listener_ready(remote)
    identity = _identity(PRONTO_COOL_22)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.bedroom",
    )
    # Past the dedup window: a real second press.
    listener._recent_hits.clear()  # past the window: a real second press
    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.bedroom",
    )

    assert hass.bus.async_fire.call_count == 2


@pytest.mark.asyncio
async def test_receiver_scope_is_honored():
    remote = TriggerRemote(
        id="r1", name="Bedroom AC", climate_matrix=True,
        receiver_scope=["infrared.bedroom"],
    )
    hass, _s, listener = _listener_ready(remote)
    identity = _identity(PRONTO_COOL_22)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.kitchen",
    )

    assert hass.bus.async_fire.call_count == 0
    assert remote.last_heard is None


@pytest.mark.asyncio
async def test_a_flat_remote_hears_nothing():
    remote = TriggerRemote(id="r1", name="TV Remote")
    hass, _s, listener = _listener_ready(remote)
    identity = _identity(PRONTO_COOL_22)

    assert await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, None,
    ) == []
    assert hass.bus.async_fire.call_count == 0


@pytest.mark.asyncio
async def test_an_unrelated_frame_is_not_heard():
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    hass, _s, listener = _listener_ready(remote)

    await listener.on_signal_captured("some-fp", "some-hash", None, None)

    assert hass.bus.async_fire.call_count == 0
    assert remote.last_heard is None


@pytest.mark.asyncio
async def test_the_first_frame_builds_the_index_and_does_not_match():
    """The build runs off the capture path, so the frame that starts it
    is the accepted cost -- and the next one matches."""
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    store = _store_with(remote)
    hass = _hass(store)
    built: list[object] = []
    hass.async_create_task = MagicMock(side_effect=built.append)
    listener = MatrixListener(hass, store)
    identity = _identity(PRONTO_COOL_22)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, None,
    )

    assert hass.bus.async_fire.call_count == 0
    assert len(built) == 1
    with patch(
        "custom_components.hair.matrix_store.load_matrix",
        return_value=_matrix(),
    ):
        await built[0]
    assert listener._index_cache["r1"]

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, None,
    )
    assert hass.bus.async_fire.call_count == 1


@pytest.mark.asyncio
async def test_invalidate_drops_the_index_too():
    """A rewritten matrix must not keep matching the old lattice."""
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    _h, _s, listener = _listener_ready(remote)

    listener.invalidate("r1")

    assert "r1" not in listener._index_cache
    assert "r1" not in listener._matrix_cache


# ---------------------------------------------------------------------------
# Driving a pinned matrix Device (Track 4)
# ---------------------------------------------------------------------------
#
# The contract: what was HEARD as a state is SENT as that same state
# out of the pinned device's own lattice. Coordinates first, the frame
# itself second when the two files disagree about words, and silence
# third -- a near-miss cell would be a plausible lie sent at a real air
# conditioner.


class _RecordingDeviceManager:
    def __init__(self, matrix):
        self._matrix = matrix
        self.sends: list[tuple] = []
        self.states: list[dict] = []

    async def async_get_matrix(self, device_id):
        return self._matrix

    async def async_send_matrix_cell(
        self, device_id, cell_name, pronto, send_count=1,
        heard_future=None, pinned=False, cell=None, power=None,
        origin=None,
    ):
        self.sends.append((device_id, cell_name, pronto, send_count, pinned))
        # 0.10.1 item 7: a pinned retransmit carries the DEVICE's own
        # coordinates so its climate card follows the send.
        self.states.append({"cell": cell, "power": power})


def _pinned(device_matrix=None, *, climate_matrix=True, device_index=None):
    """A matrix remote pinned to one device, both indexes primed."""
    remote = TriggerRemote(
        id="r1", name="Bedroom AC", climate_matrix=True,
        pinned_device_ids=["dev-1"],
    )
    store = _store_with(remote)
    device = MagicMock(id="dev-1", climate_matrix=climate_matrix)
    device.name = "Bedroom Head Unit"
    store.get_device = MagicMock(return_value=device)

    hass = _hass(store)
    tasks: list = []
    hass.async_create_task = MagicMock(side_effect=tasks.append)

    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=(None, None))
    tm.dispatch_cell_retransmit = MagicMock(return_value=True)

    dm = _RecordingDeviceManager(
        _device_matrix() if device_matrix is None else device_matrix
    )
    listener = MatrixListener(hass, store, tm, dm)
    listener._matrix_cache["r1"] = _matrix()
    listener._index_cache["r1"] = build_cell_index(_matrix())
    if device_index is not None:
        listener._index_cache["dev-1"] = device_index
    return listener, tm, dm, tasks


async def _hear(listener, tasks, pronto=PRONTO_COOL_22):
    identity = _identity(pronto)
    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, None,
    )
    # The record path saves and dispatches as tasks; run them.
    while tasks:
        batch, tasks[:] = list(tasks), []
        for coro in batch:
            await coro


@pytest.mark.asyncio
async def test_a_heard_state_drives_the_pinned_matrix_device():
    listener, tm, _dm, tasks = _pinned()

    await _hear(listener, tasks)

    tm.dispatch_cell_retransmit.assert_called_once_with(
        "r1", "dev-1", "cool/auto/22",
        ("Bedroom AC", "Bedroom Head Unit", "cool / fan: auto / 22"),
    )


@pytest.mark.asyncio
async def test_the_pinned_send_uses_the_devices_own_bytes():
    """The remote's lattice says WHICH state; the device's says what
    that state is on that unit. Two units sharing a wig transmit the
    same code, but nothing here may assume it."""
    listener, _tm, dm, tasks = _pinned()

    await _hear(listener, tasks)
    await listener.async_send_pinned_cell("dev-1", "cool/auto/22")

    assert dm.sends == [
        ("dev-1", "cool / fan: auto / 22", PRONTO_DEV_22, 1, True)
    ]


@pytest.mark.asyncio
async def test_the_pinned_send_announces_itself_as_pinned():
    """pinned=True is what mints the echo ticket and labels the Mirror
    row; without it the house's own send reads as a panel press."""
    listener, _tm, dm, tasks = _pinned()

    await _hear(listener, tasks)
    await listener.async_send_pinned_cell("dev-1", "cool/auto/22")

    assert dm.sends[0][-1] is True


@pytest.mark.asyncio
async def test_a_vocabulary_mismatch_falls_back_to_the_frame_itself():
    """Two wigs for one unit spell the fan speed differently, so the
    coordinates miss. The bytes cannot: a device cell that transmits
    exactly what was just heard IS the heard state."""
    device_matrix = _device_matrix(
        fan="Auto", prontos=(PRONTO_COOL_22, PRONTO_COOL_23)
    )
    listener, tm, dm, tasks = _pinned(
        device_matrix, device_index=build_cell_index(device_matrix)
    )

    await _hear(listener, tasks)
    await listener.async_send_pinned_cell("dev-1", "cool/auto/22")

    assert tm.dispatch_cell_retransmit.call_count == 1
    assert dm.sends == [
        ("dev-1", "cool / fan: Auto / 22", PRONTO_COOL_22, 1, True)
    ]


@pytest.mark.asyncio
async def test_a_state_the_device_does_not_have_sends_nothing(caplog):
    """Neither the words nor the bytes match. Silence, and one line in
    the log per pairing rather than one per press."""
    device_matrix = _device_matrix(
        fan="Auto", prontos=(PRONTO_DEV_22, PRONTO_DEV_23)
    )
    listener, tm, dm, tasks = _pinned(
        device_matrix, device_index=build_cell_index(device_matrix)
    )

    with caplog.at_level("DEBUG", logger="custom_components.hair.matrix_listener"):
        await _hear(listener, tasks)
        listener._recent_hits.clear()  # past the window: a real second press
        await _hear(listener, tasks)
    await listener.async_send_pinned_cell("dev-1", "cool/auto/22")

    assert tm.dispatch_cell_retransmit.call_count == 0
    assert dm.sends == []
    assert sum(
        "has no such state" in r.getMessage() for r in caplog.records
    ) == 1


@pytest.mark.asyncio
async def test_a_pairing_that_starts_working_reports_again_if_it_breaks():
    """The once-per-pair mute is not permanent, or a lattice repaired
    and then broken again would fail silently forever."""
    listener, _tm, _dm, tasks = _pinned(
        _device_matrix(fan="Auto"),
        device_index=build_cell_index(_device_matrix(fan="Auto")),
    )

    await _hear(listener, tasks)
    assert ("r1", "dev-1") in listener._unmapped

    listener._index_cache["dev-1"] = build_cell_index(_device_matrix())
    listener._device_manager._matrix = _device_matrix()
    listener._recent_hits.clear()  # past the window: a real second press
    await _hear(listener, tasks)

    assert ("r1", "dev-1") not in listener._unmapped


@pytest.mark.asyncio
async def test_a_pinned_flat_device_is_skipped():
    """Track 4.2: a state has no command row to land on, and a flat
    device's lattice does not exist to look one up in."""
    listener, tm, _dm, tasks = _pinned(climate_matrix=False)

    await _hear(listener, tasks)

    assert tm.dispatch_cell_retransmit.call_count == 0
    assert listener._unmapped == set()


@pytest.mark.asyncio
async def test_power_maps_to_the_devices_own_power_code():
    """Off and on are the two states every lattice has whatever its
    climate vocabulary looks like, so they never need the fallback."""
    listener, tm, dm, tasks = _pinned(
        _device_matrix(fan="Auto"),
        device_index=build_cell_index(_device_matrix(fan="Auto")),
    )

    await _hear(listener, tasks, PRONTO_OFF)
    await listener.async_send_pinned_cell("dev-1", "off")

    tm.dispatch_cell_retransmit.assert_called_once_with(
        "r1", "dev-1", "off", ("Bedroom AC", "Bedroom Head Unit", "Off"),
    )
    assert dm.sends == [("dev-1", "Off", PRONTO_DEV_OFF, 1, True)]


@pytest.mark.asyncio
async def test_a_device_with_no_on_code_is_not_sent_one():
    listener, tm, dm, tasks = _pinned()
    matrix = _matrix()
    matrix.on = "0000 006D 0002 0000 0040 0040 0020 0020"
    listener._matrix_cache["r1"] = matrix
    listener._index_cache["r1"] = build_cell_index(matrix)

    await _hear(listener, tasks, matrix.on)
    await listener.async_send_pinned_cell("dev-1", "on")

    assert tm.dispatch_cell_retransmit.call_count == 0
    assert dm.sends == []


@pytest.mark.asyncio
async def test_an_unheard_cell_key_sends_nothing():
    """The send resolves the frame it was dispatched for. A key nobody
    heard has no coordinates behind it, so there is nothing to send."""
    listener, _tm, dm, _tasks = _pinned()

    await listener.async_send_pinned_cell("dev-1", "heat/low/30")

    assert dm.sends == []


@pytest.mark.asyncio
async def test_an_unpinned_matrix_remote_dispatches_nothing():
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=(None, None))
    hass, _s, listener = _listener_ready(remote, trigger_manager=tm)
    identity = _identity(PRONTO_COOL_22)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, None,
    )

    assert tm.dispatch_cell_retransmit.call_count == 0
    # One task only: the store save. No dispatch was scheduled.
    assert hass.async_create_task.call_count == 1


@pytest.mark.asyncio
async def test_the_first_press_builds_the_devices_index_and_sends_nothing():
    """The fallback index is built off the capture path for the same
    reason the hear-side one is, so the press that needs it resolves
    nothing and the next one resolves."""
    device_matrix = _device_matrix(
        fan="Auto", prontos=(PRONTO_COOL_22, PRONTO_COOL_23)
    )
    listener, tm, _dm, tasks = _pinned(device_matrix)

    await _hear(listener, tasks)
    assert tm.dispatch_cell_retransmit.call_count == 0

    # The build lands.
    listener._index_cache["dev-1"] = build_cell_index(device_matrix)
    listener._recent_hits.clear()  # past the window: a real second press
    await _hear(listener, tasks)

    assert tm.dispatch_cell_retransmit.call_count == 1


# ---------------------------------------------------------------------------
# The capture path and the device trigger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_capture_path_consults_the_listener_after_triggers():
    """Same call site, same not-echo gate: an echo-claimed capture
    reaches neither the trigger manager nor the lattice."""
    from custom_components.hair.signal_monitor import SignalMonitor

    listener = MagicMock()
    listener.on_signal_captured = AsyncMock(return_value=[])
    monitor = SignalMonitor(
        MagicMock(), MagicMock(), MagicMock(), MagicMock(), listener
    )
    monitor._match_echo = AsyncMock(return_value=True)

    parsed = MagicMock(
        protocol="PRONTO", code=PRONTO_COOL_22,
        raw_timings=[600, -600], frequency=38000,
    )
    await monitor._process_parsed_signal(parsed, "infrared.bedroom")

    listener.on_signal_captured.assert_not_awaited()


def test_device_trigger_row_only_on_a_matrix_remote(fake_hass):
    from custom_components.hair import device_trigger

    matrix_remote = TriggerRemote(
        id="rem-m", name="Bedroom AC", climate_matrix=True
    )
    flat_remote = TriggerRemote(id="rem-f", name="TV Remote")
    store = _store_with(matrix_remote, flat_remote)
    store.get_triggers_for_remote = MagicMock(return_value=[])
    fake_hass.data[DOMAIN] = {
        "entry-1": {"store": store, "device_manager": MagicMock()}
    }

    import asyncio

    def _rows(remote_id):
        with patch.object(
            device_trigger, "_owning_scope_for_device", return_value=remote_id
        ):
            return asyncio.run(
                device_trigger.async_get_triggers(fake_hass, "ha-dev-1")
            )

    matrix_rows = _rows("rem-m")
    assert [r["type"] for r in matrix_rows] == ["state_heard"]
    assert matrix_rows[0]["subtype"] == "State heard"
    assert _rows("rem-f") == []


# ---------------------------------------------------------------------------
# The index on disk: built once, not once per boot
# ---------------------------------------------------------------------------


def test_a_built_index_round_trips_through_disk(tmp_path):
    from custom_components.hair.matrix_listener import (
        _index_to_payload,
        _payload_to_index,
    )

    index = build_cell_index(_matrix(), display_unit="C")
    restored = _payload_to_index(_index_to_payload(index, "h1", "C"))

    assert restored is not None
    identity = _identity(PRONTO_COOL_22)
    hit, _tier = restored.match(
        identity.decoded_fingerprint, identity.fingerprint, identity.byte_hash
    )
    assert hit.cell_key == "cool/auto/22"
    assert hit.temp == 22.0
    assert restored.match(None, None, None) is None


def test_the_stored_index_is_reused_when_the_matrix_is_unchanged(tmp_path):
    from custom_components.hair.matrix_listener import (
        _build_and_store_index,
        _load_stored_index,
    )
    from custom_components.hair.matrix_store import write_matrix

    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")

    reused = _load_stored_index(str(tmp_path), "r1", "C")
    assert reused is not None
    identity = _identity(PRONTO_COOL_23)
    assert reused.match(
        identity.decoded_fingerprint, identity.fingerprint, identity.byte_hash
    )[0].cell_key == "cool/auto/23"


def test_a_rewritten_matrix_is_never_matched_against_a_stale_index(tmp_path):
    from custom_components.hair.matrix_listener import (
        _build_and_store_index,
        _load_stored_index,
    )
    from custom_components.hair.matrix_store import write_matrix

    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")

    other = _matrix()
    other.cells = other.cells[:1]
    write_matrix(tmp_path, "r1", other)

    assert _load_stored_index(str(tmp_path), "r1", "C") is None


def test_a_flipped_display_unit_rebuilds(tmp_path):
    """Cell names freeze the unit they were built in."""
    from custom_components.hair.matrix_listener import (
        _build_and_store_index,
        _load_stored_index,
    )
    from custom_components.hair.matrix_store import write_matrix

    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")

    assert _load_stored_index(str(tmp_path), "r1", "F") is None


def test_deleting_a_matrix_takes_its_index(tmp_path):
    from custom_components.hair.matrix_listener import _build_and_store_index
    from custom_components.hair.matrix_store import (
        delete_matrix,
        index_path,
        write_matrix,
    )

    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")
    assert index_path(tmp_path, "r1").is_file()

    delete_matrix(tmp_path, "r1")

    assert not index_path(tmp_path, "r1").is_file()


@pytest.mark.asyncio
async def test_invalidate_drops_the_stored_index_too(tmp_path):
    from custom_components.hair.matrix_listener import _build_and_store_index
    from custom_components.hair.matrix_store import index_path, write_matrix

    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    store = _store_with(remote)
    hass = _hass(store)
    hass.config.config_dir = str(tmp_path)
    listener = MatrixListener(hass, store)
    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")

    listener.invalidate("r1")

    assert not index_path(tmp_path, "r1").is_file()


# ---------------------------------------------------------------------------
# The receiver-tolerant tier (2026-08-18), against the air-path captures
# ---------------------------------------------------------------------------
#
# The toy Prontos above are two burst pairs long and deliberately carry
# no normalized fingerprint at all (nothing to find two levels in), so
# these tests use the real lattice codes and the real captures from the
# air-path run instead. See tests/fixtures/air-path/README.md.

_AIR = _Path(__file__).parent / "fixtures" / "air-path"


def _air_code(name: str) -> str:
    return (_AIR / f"{name}.pronto").read_text(encoding="utf-8").strip()


def _air_captures(code: str, transmitter: str | None = None) -> list[dict]:
    with _gzip.open(_AIR / "captures.csv.gz", "rt", encoding="utf-8") as fh:
        rows = list(_csv.DictReader(_io.StringIO(fh.read())))
    return [
        r for r in rows
        if r["code"] == code
        and (transmitter is None or r["transmitter"] == transmitter)
    ]


def _heard(row: dict):
    """One capture, normalized exactly as the Sniffer normalizes it."""
    from custom_components.hair.ir_command import raw_to_pronto
    from custom_components.hair.models import CaptureResult
    from custom_components.hair.signal_monitor import normalize

    values = _json.loads(row["timings_us"])
    raw = [v if i % 2 == 0 else -abs(v) for i, v in enumerate(values)]
    return normalize(
        CaptureResult(
            protocol="PRONTO",
            code=raw_to_pronto(raw, frequency=38000),
            raw_timings=raw,
            frequency=38000,
        )
    )


def _air_matrix() -> ClimateMatrix:
    """Two real cells of the bench Mitsubishi lattice."""
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool", "heat"],
        fan_modes=["auto", "low"],
        swing_modes=[],
        off=None,
        cells=[
            ClimateCell(
                mode="cool", fan="auto", temp=23.0, pronto=_air_code("C1")
            ),
            ClimateCell(
                mode="heat", fan="low", temp=20.0, pronto=_air_code("C2")
            ),
        ],
    )


def test_a_real_press_lands_on_its_cell_through_the_lowest_tier():
    """The whole point, on the bench's own captures.

    Every ESPHome press of C1 resolves to cool/auto/23, and none of them
    would have on any tier above: the byte hash of a lattice frame is a
    fresh value on every press.
    """
    index = build_cell_index(_air_matrix())
    rows = _air_captures("C1", "esphome")
    assert len(rows) == 8
    for row in rows:
        heard = _heard(row)
        assert heard.byte_hash not in index.bytehash
        assert (heard.sig_fp, heard.byte_hash) not in index.fp_bytehash
        matched = index.match(
            heard.decoded_fingerprint, heard.sig_fp, heard.byte_hash,
            heard.norm_fp,
        )
        assert matched is not None, row["first_seen"]
        hit, tier = matched
        assert (hit.cell_key, tier) == ("cool/auto/23", TIER_NORM_FP)


def test_the_broadlink_worst_case_lands_on_its_cell_too():
    """Seven of seven for C1 through a consumer blaster."""
    index = build_cell_index(_air_matrix())
    rows = _air_captures("C1", "broadlink")
    assert len(rows) == 7
    keys = set()
    for row in rows:
        heard = _heard(row)
        matched = index.match(
            heard.decoded_fingerprint, heard.sig_fp, heard.byte_hash,
            heard.norm_fp,
        )
        assert matched is not None, row["first_seen"]
        keys.add(matched[0].cell_key)
    assert keys == {"cool/auto/23"}


def test_the_second_cell_is_not_confused_with_the_first():
    """Two cells of one lattice, 29 captures, nothing crosses over."""
    index = build_cell_index(_air_matrix())
    for code, expected in (("C1", "cool/auto/23"), ("C2", "heat/low/20")):
        for row in _air_captures(code):
            heard = _heard(row)
            matched = index.match(
                heard.decoded_fingerprint, heard.sig_fp, heard.byte_hash,
                heard.norm_fp,
            )
            if matched is None:
                continue  # the one clipped Broadlink send of C2
            assert matched[0].cell_key == expected


def test_a_capture_that_decoded_never_reaches_the_lowest_tier():
    """A frame the library read is answered by tier 1 or not at all.

    If a decoded identity is not in this lattice, the honest answer is
    that the lattice does not hold it -- not that something of a
    similar shape does.
    """
    index = build_cell_index(_air_matrix())
    heard = _heard(_air_captures("C1", "esphome")[0])
    assert index.match(
        "NEC:0x1234:0x56", heard.sig_fp, heard.byte_hash, heard.norm_fp
    ) is None


def test_a_lattice_that_spells_one_shape_twice_answers_neither():
    """Ambiguity is not a match.

    Two cells whose codes are different but whose normalized shape is
    identical poison the value: the card would otherwise name whichever
    cell was indexed last, with full confidence, on a frame that could
    be either.
    """
    matrix = _air_matrix()
    # A second cell carrying C1's SHAPE at a different speed: every
    # timing word stretched by 15%, which is a different waveform by
    # every other tier (its byte hash differs) and the same one to a
    # measure that divides by the code's own median.
    words = _air_code("C1").split()
    stretched = words[:4] + [
        f"{round(int(w, 16) * 1.15):04X}" for w in words[4:]
    ]
    matrix.cells.append(
        ClimateCell(
            mode="cool", fan="auto", temp=24.0, pronto=" ".join(stretched)
        )
    )
    index = build_cell_index(matrix)
    heard = _heard(_air_captures("C1", "esphome")[0])
    assert heard.norm_fp in index.norm_fp.ambiguous
    assert index.match(
        None, heard.sig_fp, heard.byte_hash, heard.norm_fp
    ) is None


def test_the_stored_index_carries_the_lowest_tier(tmp_path):
    from custom_components.hair.matrix_listener import (
        _index_to_payload,
        _payload_to_index,
    )

    index = build_cell_index(_air_matrix(), display_unit="C")
    payload = _index_to_payload(index, "h1", "C")
    # The literal lives in test_a_stale_cell_index_is_refused, which is
    # what pins the version. Here it only has to be the current one, so
    # a bump does not need this test edited to stay honest.
    assert payload["format"] == _ml.INDEX_FORMAT
    restored = _payload_to_index(payload)
    assert restored is not None
    heard = _heard(_air_captures("C1", "esphome")[0])
    matched = restored.match(
        None, heard.sig_fp, heard.byte_hash, heard.norm_fp
    )
    assert matched is not None
    assert matched[0].cell_key == "cool/auto/23"


def test_an_index_written_before_the_tier_existed_is_rebuilt():
    """The format bump is what makes every lattice gain the new map."""
    from custom_components.hair.matrix_listener import (
        _index_to_payload,
        _payload_to_index,
    )

    payload = _index_to_payload(build_cell_index(_matrix()), "h1", "C")
    payload["format"] = "hair-cell-index/1"
    assert _payload_to_index(payload) is None


# ---------------------------------------------------------------------------
# One press is one event (owner ruling 2026-08-18, after the rehearsal)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_two_frames_of_one_press_are_one_event():
    """The bench's finding A, closed.

    A C1 press reaches the receiver as two complete frames, measured 103
    to 148 ms apart, which the old 100 ms window did not cover: every
    press of a two-frame cell fired hair_state_heard twice and saved the
    store twice.
    """
    remote = TriggerRemote(id="r1", name="Bench Handset", climate_matrix=True)
    hass, _s, listener = _listener_ready(remote, matrix=_air_matrix())
    frames = _air_captures("C1", "esphome")[:2]

    for row in frames:
        signal = _heard(row)
        await listener.on_signal_captured(
            signal.sig_fp, signal.byte_hash, signal.decoded_fingerprint,
            "infrared.athom_rx", signal.norm_fp,
        )

    assert hass.bus.async_fire.call_count == 1


@pytest.mark.asyncio
async def test_a_different_state_inside_the_window_is_a_second_event():
    """The key carries the cell, so cool 23 then off is still two.

    A window keyed on the remote alone would swallow a deliberate
    change of state made inside a third of a second -- which a script,
    an automation, or a fast hand can do.
    """
    remote = TriggerRemote(id="r1", name="Bench Handset", climate_matrix=True)
    hass, _s, listener = _listener_ready(remote, matrix=_air_matrix())

    for name in ("C1", "C2"):
        signal = _heard(_air_captures(name, "esphome")[0])
        await listener.on_signal_captured(
            signal.sig_fp, signal.byte_hash, signal.decoded_fingerprint,
            "infrared.athom_rx", signal.norm_fp,
        )

    assert hass.bus.async_fire.call_count == 2
    heard = [call.args[1]["cell_key"] for call in hass.bus.async_fire.call_args_list]
    assert heard == ["cool/auto/23", "heat/low/20"]


@pytest.mark.asyncio
async def test_a_press_whose_frames_split_by_330ms_is_still_one_event(
    monkeypatch,
):
    """The one outlier of the ESPHome pass, ruled a non-event.

    Fifty presses through the ESP32 put 29 of 30 AC presses inside
    300 ms and exactly one at 330, which counted twice. 400 ms covers
    it, and a human cannot release and re-press inside that.
    """
    clock = {"t": 1000.0}
    monkeypatch.setattr(
        _ml.time, "monotonic", lambda: clock["t"]
    )
    remote = TriggerRemote(id="r1", name="Bench Handset", climate_matrix=True)
    hass, _s, listener = _listener_ready(remote, matrix=_air_matrix())
    signal = _heard(_air_captures("C1", "esphome")[0])

    async def hear():
        await listener.on_signal_captured(
            signal.sig_fp, signal.byte_hash, signal.decoded_fingerprint,
            "infrared.athom_rx", signal.norm_fp,
        )

    await hear()
    clock["t"] += 0.330
    await hear()
    assert hass.bus.async_fire.call_count == 1

    # And a real second press, well past the window, is heard again.
    clock["t"] += 0.500
    await hear()
    assert hass.bus.async_fire.call_count == 2


def test_the_window_is_the_ruled_number():
    """Pinned, because the number is a ruling and not a taste."""
    assert MATRIX_STATE_DEDUP_WINDOW_S == 0.400


# ---------------------------------------------------------------------------
# Warming the index at setup (0.10.1 item 3)
# ---------------------------------------------------------------------------
#
# The lazy first-frame build is 6 to 12 ms of disk read, which is small
# enough to look safe and is not: a single-frame file-sourced code
# pressed in the first moments after a restart falls inside it and is
# missed outright. These pin that the warm happens before any frame can
# arrive, and that the lazy path is still there for a remote minted
# later in the run.


def _warm_listener(*remotes, config_dir, devices=()):
    """A listener whose store answers for these remotes and devices."""
    store = _store_with(*remotes)
    by_id = {d.id: d for d in devices}
    store.get_device = MagicMock(side_effect=by_id.get)
    hass = _hass(store)
    hass.config.config_dir = str(config_dir)
    return hass, store, MatrixListener(hass, store)


@pytest.mark.asyncio
async def test_a_single_frame_right_after_the_warm_matches(tmp_path):
    """The regression itself: one frame, immediately, and it is heard."""
    from custom_components.hair.matrix_listener import _build_and_store_index
    from custom_components.hair.matrix_store import write_matrix

    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    hass, _store, listener = _warm_listener(remote, config_dir=tmp_path)

    await listener.async_warm_indexes()

    assert listener._index_cache["r1"]
    identity = _identity(PRONTO_COOL_22)
    heard = await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, None,
    )
    assert heard == ["r1"]
    assert hass.bus.async_fire.call_count == 1


@pytest.mark.asyncio
async def test_the_warm_reads_a_stored_index_rather_than_rebuilding(tmp_path):
    from custom_components.hair.matrix_listener import _build_and_store_index
    from custom_components.hair.matrix_store import write_matrix

    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    _h, _s, listener = _warm_listener(remote, config_dir=tmp_path)

    with patch(
        "custom_components.hair.matrix_listener.build_cell_index"
    ) as never:
        await listener.async_warm_indexes()

    never.assert_not_called()
    assert listener._index_cache["r1"]


@pytest.mark.asyncio
async def test_the_warm_builds_and_stores_an_index_when_none_is_on_disk(
    tmp_path,
):
    from custom_components.hair.matrix_store import index_path, write_matrix

    write_matrix(tmp_path, "r1", _matrix())
    assert not index_path(tmp_path, "r1").is_file()
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    _h, _s, listener = _warm_listener(remote, config_dir=tmp_path)

    await listener.async_warm_indexes()

    assert listener._index_cache["r1"]
    assert index_path(tmp_path, "r1").is_file()


@pytest.mark.asyncio
async def test_the_warm_covers_a_pinned_matrix_device_too(tmp_path):
    """The Track 4 fallback indexes through the same cache."""
    from custom_components.hair.matrix_store import write_matrix

    write_matrix(tmp_path, "r1", _matrix())
    write_matrix(tmp_path, "dev-1", _device_matrix())
    remote = TriggerRemote(
        id="r1", name="Bedroom AC", climate_matrix=True,
        pinned_device_ids=["dev-1", "flat-1"],
    )
    device = MagicMock(id="dev-1", climate_matrix=True)
    flat = MagicMock(id="flat-1", climate_matrix=False)
    _h, _s, listener = _warm_listener(
        remote, config_dir=tmp_path, devices=(device, flat)
    )

    await listener.async_warm_indexes()

    assert listener._index_cache["r1"]
    assert listener._index_cache["dev-1"]
    assert "flat-1" not in listener._index_cache


@pytest.mark.asyncio
async def test_the_warm_is_silent_with_no_matrix_remotes(caplog, tmp_path):
    remote = TriggerRemote(id="r1", name="Living room TV")
    _h, _s, listener = _warm_listener(remote, config_dir=tmp_path)

    with caplog.at_level(
        _logging.INFO, logger="custom_components.hair.matrix_listener"
    ):
        await listener.async_warm_indexes()

    assert listener._index_cache == {}
    assert "Warmed" not in caplog.text


@pytest.mark.asyncio
async def test_one_unreadable_lattice_does_not_sink_the_warm(tmp_path):
    """A failure warms one lattice less; it never fails setup."""
    from custom_components.hair.matrix_store import write_matrix

    write_matrix(tmp_path, "r2", _matrix())
    bad = TriggerRemote(id="r1", name="Bad", climate_matrix=True)
    good = TriggerRemote(id="r2", name="Good", climate_matrix=True)
    _h, _s, listener = _warm_listener(bad, good, config_dir=tmp_path)
    real = listener._async_build_index

    async def _explode(matrix_id):
        if matrix_id == "r1":
            listener._building.discard(matrix_id)
            raise OSError("no")
        return await real(matrix_id)

    listener._async_build_index = _explode

    await listener.async_warm_indexes()

    assert "r1" not in listener._index_cache
    assert listener._index_cache["r2"]


@pytest.mark.asyncio
async def test_the_warm_skips_a_lattice_already_cached(tmp_path):
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    _h, _s, listener = _warm_listener(remote, config_dir=tmp_path)
    listener._index_cache["r1"] = build_cell_index(_matrix())

    with patch(
        "custom_components.hair.matrix_listener._load_stored_index"
    ) as never:
        await listener.async_warm_indexes()

    never.assert_not_called()


@pytest.mark.asyncio
async def test_a_remote_minted_at_runtime_is_warmed_by_its_mint_door():
    """The lazy path stays, but the mint doors do not wait for it."""
    listener = MagicMock()
    from custom_components.hair.websocket_api import _warm_remote_matrix

    _warm_remote_matrix({"matrix_listener": listener}, "r9")

    listener.warm_index.assert_called_once_with("r9")
    # A caller assembled without a listener must not raise.
    _warm_remote_matrix({}, "r9")


def test_a_stale_cell_index_is_refused(tmp_path):
    """The INDEX_FORMAT bump, pinned against being reverted as noise.

    GH #125 moved the identity algorithm and nothing else. The matrix
    file is untouched, so its content hash is unchanged, and the display
    unit is unchanged, so an index written under the old hashes passes
    both of the other freshness checks. The format version is the only
    thing that can refuse it.
    """
    from custom_components.hair.matrix_listener import (
        INDEX_FORMAT,
        _build_and_store_index,
        _load_stored_index,
    )
    from custom_components.hair.matrix_store import index_path, write_matrix

    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")
    # /9 since a hit carries the merged group it answers for and the
    # index carries the groups: an /8 index names a dry press by its
    # last cell and gives the send side no group to read. /8 was a hit
    # row gaining its axis and lattice, /7 DAIKIN152 joining read-bytes
    # identity and the Daikin settings frame taking one shared key
    # (GH #183), /6 read-bytes identity, /5 setting-frame identity, and
    # /4 replaced /3, which let one Daikin key answer for the whole
    # lattice.
    assert INDEX_FORMAT == "hair-cell-index/9"
    assert _load_stored_index(str(tmp_path), "r1", "C") is not None

    path = index_path(tmp_path, "r1")
    payload = _json.loads(path.read_text())
    # The other two freshness keys are intact: only the format is old.
    assert payload["unit"] == "C"
    assert payload["matrix"]
    payload["format"] = "hair-cell-index/8"
    path.write_text(_json.dumps(payload))

    assert _load_stored_index(str(tmp_path), "r1", "C") is None


def test_a_rebuilt_index_matches_a_capture_after_the_identity_move(tmp_path):
    """The other half of the bump: once rebuilt, the index answers a
    real capture of the cell it indexes.

    The capture is reconstructed from raw timings the way every receive
    path reconstructs one, so this is the wire form and not the file
    text. Since GH #125 the two hash alike, which is what lets a lattice
    recognize its own cell off the air.
    """
    from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
    from custom_components.hair.matrix_listener import (
        _build_and_store_index,
        _load_stored_index,
    )
    from custom_components.hair.matrix_store import write_matrix
    from custom_components.hair.models import CaptureResult
    from custom_components.hair.signal_monitor import normalize

    write_matrix(tmp_path, "r1", _matrix())
    _build_and_store_index(str(tmp_path), "r1", _matrix(), "C")
    index = _load_stored_index(str(tmp_path), "r1", "C")
    assert index is not None

    command = ProntoCommand(PRONTO_COOL_23)
    raw = command.get_raw_timings()
    heard = normalize(
        CaptureResult(
            protocol="PRONTO",
            code=raw_to_pronto(raw, frequency=command.modulation),
            raw_timings=raw,
            frequency=command.modulation,
        )
    )

    hit, tier = index.match(
        heard.decoded_fingerprint, heard.sig_fp, heard.byte_hash
    )
    assert hit.cell_key == "cool/auto/23"
    assert tier == TIER_BYTE_HASH


# ---------------------------------------------------------------------------
# Extras lattices are heard too (extras-in-the-matrix-card.md item 5c)
# ---------------------------------------------------------------------------

# An extras code for the SAME coordinates as PRONTO_COOL_22, with its
# own bytes. That is what the real corpus does, and it is what makes
# matching by identity find the right lattice.
PRONTO_ECO_22 = "0000 006D 0002 0000 00A0 00C0 00A0 00C0"


def _matrix_with_extra() -> ClimateMatrix:
    from custom_components.hair.wig_format import ClimateExtra

    matrix = _matrix()
    matrix.extras = [
        ClimateExtra(
            axis="preset",
            key="eco",
            cells=[
                ClimateCell(
                    mode="cool", fan="auto", temp=22.0, pronto=PRONTO_ECO_22
                ),
            ],
        ),
    ]
    return matrix


def test_the_index_carries_the_extras_cells_and_names_them():
    index = build_cell_index(_matrix_with_extra())

    names = {hit.cell_name for hit in index.fp_bytehash.values()}
    # The main lattice is untouched and the extra arrives beside it.
    assert "cool / fan: auto / 22" in names
    assert "(eco) cool / fan: auto / 22" in names
    lattices = {hit.lattice for hit in index.fp_bytehash.values()}
    assert lattices == {None, "eco"}


def test_the_main_lattice_index_is_unchanged_by_an_extra():
    """Extras add reach without taking any away: an extras code never
    collides with a main-lattice one, so every main hit is the hit it
    was before."""
    plain = build_cell_index(_matrix())
    withextra = build_cell_index(_matrix_with_extra())
    for key, hit in plain.fp_bytehash.items():
        assert key in withextra.fp_bytehash
        twin = withextra.fp_bytehash[key]
        assert twin.cell_name == hit.cell_name
        assert twin.cell_key == hit.cell_key
        assert twin.lattice is None and twin.axis is None


@pytest.mark.asyncio
async def test_a_heard_extras_code_fires_state_heard_naming_its_lattice():
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    hass, _store, listener = _listener_ready(
        remote, matrix=_matrix_with_extra()
    )
    identity = _identity(PRONTO_ECO_22)

    heard = await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.bedroom",
    )

    assert heard == ["r1"]
    assert remote.last_heard["cell_name"] == "(eco) cool / fan: auto / 22"
    assert remote.last_heard["axis"] == "preset"
    assert remote.last_heard["lattice"] == "eco"
    # The coordinates are the cell's own, as they are for any hit.
    assert remote.last_heard["mode"] == "cool"
    assert remote.last_heard["temp"] == 22.0

    _event_type, event_data = hass.bus.async_fire.call_args[0]
    assert event_data["lattice"] == "eco"
    assert event_data["axis"] == "preset"


@pytest.mark.asyncio
async def test_a_heard_main_lattice_code_behaves_exactly_as_today():
    """The same lattice file, the main code: null on both new fields,
    which is what every row written before this carries."""
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    hass, _store, listener = _listener_ready(
        remote, matrix=_matrix_with_extra()
    )
    identity = _identity(PRONTO_COOL_22)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.bedroom",
    )

    assert remote.last_heard["cell_name"] == "cool / fan: auto / 22"
    assert remote.last_heard["axis"] is None
    assert remote.last_heard["lattice"] is None
    _event_type, event_data = hass.bus.async_fire.call_args[0]
    assert event_data["lattice"] is None


@pytest.mark.asyncio
async def test_the_two_codes_at_one_coordinate_are_heard_apart():
    """A trigger minted on an extras state fires on that code and not
    on the main-lattice code at the same coordinates. Identity is what
    tells them apart, which is why indexing the extras is enough."""
    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    index = build_cell_index(_matrix_with_extra())
    main = _identity(PRONTO_COOL_22)
    eco = _identity(PRONTO_ECO_22)

    main_hit = index.fp_bytehash[(main.fingerprint, main.byte_hash)]
    eco_hit = index.fp_bytehash[(eco.fingerprint, eco.byte_hash)]

    assert main.byte_hash != eco.byte_hash
    assert main_hit.lattice is None
    assert eco_hit.lattice == "eco"
    assert main_hit.cell_name != eco_hit.cell_name
    assert remote.climate_matrix


# ---------------------------------------------------------------------------
# An extras hit read back from disk, and sent on a pinned device
# ---------------------------------------------------------------------------

# The pinned device's own Eco code at cool / auto / 22. Different bytes
# from both the remote's Eco code and the device's main cell at the same
# coordinates, so a send out of the wrong lattice is visible.
PRONTO_DEV_ECO_22 = "0000 006D 0002 0000 00C0 00A0 00C0 00A0"


def _device_matrix_with_extra(
    key: str = "eco", pronto: str = PRONTO_DEV_ECO_22
) -> ClimateMatrix:
    from custom_components.hair.wig_format import ClimateExtra

    matrix = _device_matrix()
    matrix.extras = [
        ClimateExtra(
            axis="preset",
            key=key,
            cells=[
                ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=pronto),
            ],
        ),
    ]
    return matrix


def _stored(index: CellIndex) -> CellIndex:
    """The index as a restart reads it back: through JSON, which has no
    tuples and no sets, exactly as the file on disk does. A round trip
    that skipped JSON would let a tuple survive that a restart turns
    into a list."""
    restored = _ml._payload_to_index(_json.loads(_json.dumps(
        _ml._index_to_payload(index, "h1", "C")
    )))
    assert restored is not None
    return restored


def test_a_stored_index_keeps_an_extras_hits_lattice():
    """After a restart the index comes off disk. A hit that lost its
    lattice there is published, and re-sent, as the main-lattice state
    at the same coordinates, which is a different code."""
    index = build_cell_index(_matrix_with_extra())
    eco = _identity(PRONTO_ECO_22)
    main = _identity(PRONTO_COOL_22)

    restored = _stored(index)

    eco_hit = restored.fp_bytehash[(eco.fingerprint, eco.byte_hash)]
    assert (eco_hit.axis, eco_hit.lattice) == ("preset", "eco")
    assert eco_hit.cell_name == "(eco) cool / fan: auto / 22"
    main_hit = restored.fp_bytehash[(main.fingerprint, main.byte_hash)]
    assert (main_hit.axis, main_hit.lattice) == (None, None)
    for key, hit in index.fp_bytehash.items():
        assert restored.fp_bytehash[key] == hit


def test_an_index_stored_before_hits_carried_their_lattice_is_rebuilt(
    tmp_path,
):
    """A /7 row has eight fields and no lattice. It must never be read
    as a main-lattice hit; the format refuses it and the lattice
    rebuilds."""
    from custom_components.hair.matrix_listener import (
        _build_and_store_index,
        _load_stored_index,
    )
    from custom_components.hair.matrix_store import index_path, write_matrix

    matrix = _matrix_with_extra()
    write_matrix(tmp_path, "r1", matrix)
    _build_and_store_index(str(tmp_path), "r1", matrix, "C")
    path = index_path(tmp_path, "r1")
    payload = _json.loads(path.read_text())
    payload["format"] = "hair-cell-index/7"
    payload["hits"] = [row[:8] for row in payload["hits"]]
    path.write_text(_json.dumps(payload))

    assert _load_stored_index(str(tmp_path), "r1", "C") is None

    _build_and_store_index(str(tmp_path), "r1", matrix, "C")
    rebuilt = _load_stored_index(str(tmp_path), "r1", "C")
    assert rebuilt is not None
    assert {hit.lattice for hit in rebuilt.fp_bytehash.values()} == {
        None, "eco",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("from_disk", [False, True])
async def test_a_pinned_device_is_sent_its_own_extras_cell(from_disk):
    """Eco pressed on the handset sends the device's Eco code, not its
    main-lattice code at the same coordinates, live or after a
    restart."""
    listener, tm, dm, tasks = _pinned(_device_matrix_with_extra())
    index = build_cell_index(_matrix_with_extra())
    listener._matrix_cache["r1"] = _matrix_with_extra()
    listener._index_cache["r1"] = _stored(index) if from_disk else index

    await _hear(listener, tasks, PRONTO_ECO_22)
    await listener.async_send_pinned_cell("dev-1", "cool/auto/22")

    tm.dispatch_cell_retransmit.assert_called_once()
    assert dm.sends == [
        ("dev-1", "(eco) cool / fan: auto / 22", PRONTO_DEV_ECO_22, 1, True)
    ]
    assert dm.states[0]["cell"] == {
        "mode": "cool", "fan": "auto", "swing": None, "temp": 22.0,
        "axis": "preset", "lattice": "eco",
    }


@pytest.mark.asyncio
async def test_an_extras_press_the_device_has_no_lattice_for_sends_nothing():
    """The device carries no Eco lattice and no cell with the heard
    bytes. Its main cell at the same coordinates is a different code,
    so the answer is silence, as for any state the device lacks."""
    listener, tm, dm, tasks = _pinned(
        device_index=build_cell_index(_device_matrix())
    )
    listener._matrix_cache["r1"] = _matrix_with_extra()
    listener._index_cache["r1"] = build_cell_index(_matrix_with_extra())

    await _hear(listener, tasks, PRONTO_ECO_22)
    await listener.async_send_pinned_cell("dev-1", "cool/auto/22")

    assert tm.dispatch_cell_retransmit.call_count == 0
    assert dm.sends == []


@pytest.mark.asyncio
async def test_the_frame_fallback_resolves_on_the_devices_extras_lattice():
    """The device's file spells the preset "Eco", so the words miss,
    and holds the very bytes heard. The frame finds the device's Eco
    cell, and the send names that lattice rather than the main one."""
    device_matrix = _device_matrix_with_extra("Eco", PRONTO_ECO_22)
    listener, _tm, dm, tasks = _pinned(
        device_matrix, device_index=build_cell_index(device_matrix)
    )
    listener._matrix_cache["r1"] = _matrix_with_extra()
    listener._index_cache["r1"] = build_cell_index(_matrix_with_extra())

    await _hear(listener, tasks, PRONTO_ECO_22)
    await listener.async_send_pinned_cell("dev-1", "cool/auto/22")

    assert dm.sends == [
        ("dev-1", "(Eco) cool / fan: auto / 22", PRONTO_ECO_22, 1, True)
    ]
    assert dm.states[0]["cell"]["lattice"] == "Eco"


# ---------------------------------------------------------------------------
# A code the file stores under several settings (the merged-group dial)
# ---------------------------------------------------------------------------

# cool / auto / 22 and 23 are one code here, the way a file stores a
# mode whose temperature the unit ignores; 24 is a code of its own.


def _grouped_matrix() -> ClimateMatrix:
    matrix = _matrix()
    matrix.cells = [
        ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=PRONTO_COOL_22),
        ClimateCell(mode="cool", fan="auto", temp=23.0, pronto=PRONTO_COOL_22),
        ClimateCell(mode="cool", fan="auto", temp=24.0, pronto=PRONTO_COOL_23),
    ]
    return matrix


def _matrix_with_extra_group() -> ClimateMatrix:
    """``_matrix_with_extra`` with an Eco group: one code at 22-24."""
    matrix = _matrix_with_extra()
    matrix.extras[0].cells = [
        ClimateCell(mode="cool", fan="auto", temp=float(t), pronto=PRONTO_ECO_22)
        for t in (22, 23, 24)
    ]
    return matrix


def _device_matrix_with_extra_group() -> ClimateMatrix:
    """The device's own Eco group, in its own bytes. The send side reads
    the DEVICE's group, so a test of the extras rule needs one here."""
    matrix = _device_matrix_with_extra()
    matrix.extras[0].cells = [
        ClimateCell(
            mode="cool", fan="auto", temp=float(t), pronto=PRONTO_DEV_ECO_22,
        )
        for t in (22, 23, 24)
    ]
    return matrix


@pytest.mark.asyncio
async def test_a_spanned_press_is_published_with_what_it_does_not_pin_down():
    """THE CONTRACT PIN for ``hair_state_heard`` (owner ruling
    2026-10-01): in the event, a setting the press does not pin down is
    null and ``spanned`` lists what it could be; ``last_heard`` keeps
    the representative's coordinates, for the "+ Trigger" door and the
    card's seed, and gains the members the card rings by. The members
    ride the panel push and never the event, which the recorder keeps.
    """
    from unittest.mock import ANY

    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=("area-1", "Bedroom"))
    hass, _store, listener = _listener_ready(
        remote, trigger_manager=tm, matrix=_grouped_matrix(),
    )
    identity = _identity(PRONTO_COOL_22)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.bedroom",
    )

    members = [["cool", "auto", None, 22.0], ["cool", "auto", None, 23.0]]
    assert remote.last_heard == {
        "cell_key": "cool/auto/23",
        "cell_name": "cool / fan: auto / 22-23",
        "power": None,
        "mode": "cool", "fan": "auto", "swing": None, "temp": 23.0,
        "axis": None, "lattice": None,
        "spanned": {"temp": [22.0, 23.0]},
        "sl_pattern": ANY,
        "at": ANY,
        "receiver_entity_id": "infrared.bedroom",
        "receiver_area_name": "Bedroom",
        "members": members,
    }
    event_type, event_data = hass.bus.async_fire.call_args[0]
    assert event_type == EVENT_STATE_HEARD
    assert event_data == {
        "remote_id": "r1",
        "remote_name": "Bedroom AC",
        "cell_key": "cool/auto/23",
        "cell_name": "cool / fan: auto / 22-23",
        "power": None,
        "mode": "cool", "fan": "auto", "swing": None, "temp": None,
        "axis": None, "lattice": None,
        "spanned": {"temp": [22.0, 23.0]},
        "timestamp": ANY,
        "receiver_entity_id": "infrared.bedroom",
        "receiver_area_id": "area-1",
        "receiver_area_name": "Bedroom",
    }
    assert tm.notify_subscribers.call_args[0][0] == {
        "kind": "state_heard", **event_data, "members": members,
    }


@pytest.mark.asyncio
async def test_a_plain_press_is_published_as_it_always_was():
    """The same lattice, the code it stores once: every coordinate, an
    empty ``spanned`` and no members anywhere."""
    from unittest.mock import ANY

    remote = TriggerRemote(id="r1", name="Bedroom AC", climate_matrix=True)
    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=("area-1", "Bedroom"))
    hass, _store, listener = _listener_ready(
        remote, trigger_manager=tm, matrix=_grouped_matrix(),
    )
    identity = _identity(PRONTO_COOL_23)

    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, "infrared.bedroom",
    )

    assert remote.last_heard == {
        "cell_key": "cool/auto/24",
        "cell_name": "cool / fan: auto / 24",
        "power": None,
        "mode": "cool", "fan": "auto", "swing": None, "temp": 24.0,
        "axis": None, "lattice": None,
        "spanned": {},
        "sl_pattern": ANY,
        "at": ANY,
        "receiver_entity_id": "infrared.bedroom",
        "receiver_area_name": "Bedroom",
    }
    _event_type, event_data = hass.bus.async_fire.call_args[0]
    assert event_data == {
        "remote_id": "r1",
        "remote_name": "Bedroom AC",
        "cell_key": "cool/auto/24",
        "cell_name": "cool / fan: auto / 24",
        "power": None,
        "mode": "cool", "fan": "auto", "swing": None, "temp": 24.0,
        "axis": None, "lattice": None,
        "spanned": {},
        "timestamp": ANY,
        "receiver_entity_id": "infrared.bedroom",
        "receiver_area_id": "area-1",
        "receiver_area_name": "Bedroom",
    }
    assert "members" not in tm.notify_subscribers.call_args[0][0]


def test_a_stored_index_keeps_its_groups_and_every_hits_group(tmp_path):
    """Through ``write_cell_index`` and ``load_cell_index``, which is
    JSON: every group comes back with tuple members, float
    temperatures, a set of digests and a set of tuple branches, the
    extra's group keyed by its axis and key, and every hit pointing at
    its group's one members tuple. ``write_cell_index`` swallows a
    TypeError, so the True below is what proves the payload is JSON."""
    from custom_components.hair.matrix_store import (
        load_cell_index,
        write_cell_index,
    )

    matrix = _matrix_with_extra_group()
    matrix.cells = _grouped_matrix().cells
    index = build_cell_index(matrix)
    assert {g.lattice for g in index.groups.values()} == {
        None, ("preset", "eco"),
    }

    assert write_cell_index(
        tmp_path, "r1", _ml._index_to_payload(index, "h1", "C")
    ) is True
    restored = _ml._payload_to_index(load_cell_index(tmp_path, "r1"))

    assert restored is not None
    assert restored.groups == index.groups
    for key, group in restored.groups.items():
        assert isinstance(group.members, tuple)
        assert all(isinstance(m, tuple) for m in group.members)
        assert all(isinstance(b, tuple) for b in group.full_branches)
        assert isinstance(group.digests, frozenset)
        assert key[0] == group.lattice
    for tier in ("decoded", "fp_bytehash", "bytehash"):
        for key, hit in getattr(index, tier).items():
            twin = getattr(restored, tier)[key]
            assert twin == hit
            if twin.members:
                assert any(
                    twin.members is g.members for g in restored.groups.values()
                )
    eco = _identity(PRONTO_ECO_22)
    eco_hit = restored.fp_bytehash[(eco.fingerprint, eco.byte_hash)]
    assert eco_hit.spanned == (("temp", (22.0, 23.0, 24.0)),)
    assert eco_hit.cell_name == "(eco) cool / fan: auto / 22-24"
    assert (eco_hit.axis, eco_hit.lattice) == ("preset", "eco")


def test_an_index_stored_before_groups_is_rebuilt_with_them(tmp_path):
    """An /8 index has no groups and names a dry press by its last cell.
    It is refused, and the rebuild carries the groups."""
    from custom_components.hair.matrix_listener import (
        _build_and_store_index,
        _load_stored_index,
    )
    from custom_components.hair.matrix_store import index_path, write_matrix

    matrix = _grouped_matrix()
    write_matrix(tmp_path, "r1", matrix)
    _build_and_store_index(str(tmp_path), "r1", matrix, "C")
    path = index_path(tmp_path, "r1")
    payload = _json.loads(path.read_text())
    payload["format"] = "hair-cell-index/8"
    del payload["groups"]
    payload["hits"] = [row[:10] for row in payload["hits"]]
    path.write_text(_json.dumps(payload))

    assert _load_stored_index(str(tmp_path), "r1", "C") is None

    _build_and_store_index(str(tmp_path), "r1", matrix, "C")
    rebuilt = _load_stored_index(str(tmp_path), "r1", "C")
    assert rebuilt is not None and rebuilt.groups


# --- The device index is warm when a send needs its groups ----------------


def _bench(tmp_path, remote_matrix, device_matrix, *, pinned=True):
    """A real listener over a real config dir, both files written, the
    remote's index warm and the device's cold. Tasks are collected, not
    run, so each test decides what has happened when."""
    from custom_components.hair.matrix_store import write_matrix

    write_matrix(tmp_path, "r1", remote_matrix)
    write_matrix(tmp_path, "dev-1", device_matrix)
    remote = TriggerRemote(
        id="r1", name="Bedroom AC", climate_matrix=True,
        pinned_device_ids=["dev-1"] if pinned else [],
    )
    store = _store_with(remote)
    device = MagicMock(id="dev-1", climate_matrix=True)
    device.name = "Bedroom Head Unit"
    store.get_device = MagicMock(return_value=device)
    hass = _hass(store)
    hass.config.config_dir = str(tmp_path)
    tasks: list = []
    hass.async_create_task = MagicMock(side_effect=tasks.append)
    tm = MagicMock()
    tm.resolve_receiver_area = MagicMock(return_value=(None, None))
    dm = _RecordingDeviceManager(device_matrix)
    listener = MatrixListener(hass, store, tm, dm)
    listener._index_cache["r1"] = build_cell_index(remote_matrix)
    return listener, store, remote, tm, dm, tasks


async def _drain(tasks):
    while tasks:
        batch, tasks[:] = list(tasks), []
        for coro in batch:
            await coro


async def _press_and_send(listener, tasks, tm, dm, pronto):
    """Hear, dispatch and send WITHOUT running a build the press
    scheduled: the harness would otherwise drain it inside the press and
    hide which press had the group."""
    identity = _identity(pronto)
    tm.dispatch_cell_retransmit.reset_mock()
    await listener.on_signal_captured(
        identity.fingerprint, identity.byte_hash,
        identity.decoded_fingerprint, None,
    )
    held = []
    while tasks:
        batch, tasks[:] = list(tasks), []
        for coro in batch:
            if getattr(coro, "__qualname__", "").endswith("_async_build_index"):
                held.append(coro)
            else:
                await coro
    listener._recent_hits.clear()
    key = tm.dispatch_cell_retransmit.call_args.args[2]
    await listener.async_send_pinned_cell("dev-1", key)
    tasks.extend(held)
    return dm.states[-1]["cell"]


@pytest.mark.asyncio
async def test_a_press_that_finds_the_device_index_cold_builds_it(tmp_path):
    """A same-file pairing never misses its coordinates, so nothing else
    would build the device's index. That press goes out as it always
    did, without a group; it schedules the build, and the next press
    has the group."""
    listener, _s, _r, tm, dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )

    first = await _press_and_send(listener, tasks, tm, dm, PRONTO_COOL_22)

    assert "spanned" not in first
    assert "dev-1" in listener._building
    await _drain(tasks)
    assert listener._index_cache["dev-1"].groups
    second = await _press_and_send(listener, tasks, tm, dm, PRONTO_COOL_22)
    assert second["spanned"] == {"temp": [22.0, 23.0]}


@pytest.mark.asyncio
async def test_pinning_at_runtime_warms_the_devices_index(tmp_path, fake_hass):
    """The pin door warms the device's lattice, so the FIRST press after
    a runtime pin already has its group."""
    from custom_components.hair.websocket_api import (
        ws_pin_trigger_remote_device,
    )

    from .test_websocket_api import _make_connection, _wire_triggers

    listener, store, remote, tm, dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(), pinned=False,
    )
    _wire_triggers(fake_hass, store)
    fake_hass.data[DOMAIN]["entry-1"]["matrix_listener"] = listener
    store.get_trigger_remote = MagicMock(return_value=remote)

    await ws_pin_trigger_remote_device(fake_hass, _make_connection(), {
        "id": 1, "type": "hair/trigger-remote/pin",
        "remote_id": "r1", "device_id": "dev-1",
    })
    await _drain(tasks)

    # Before any press.
    assert listener._index_cache["dev-1"].groups
    sent = await _press_and_send(listener, tasks, tm, dm, PRONTO_COOL_22)
    assert sent["spanned"] == {"temp": [22.0, 23.0]}


@pytest.mark.asyncio
async def test_a_matrix_change_warms_a_pinned_devices_index_again(
    tmp_path, fake_hass,
):
    """A repair signals matrix-changed, which drops the device's index;
    the same signal rebuilds it from the new file, so the next press has
    its group without waiting for a restart."""
    from custom_components.hair.matrix_store import write_matrix
    from custom_components.hair.websocket_api import _signal_matrix_changed

    from .test_websocket_api import _wire_triggers

    listener, store, _remote, tm, dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )
    _wire_triggers(fake_hass, store)
    fake_hass.data[DOMAIN]["entry-1"]["matrix_listener"] = listener
    listener.warm_index("dev-1")
    await _drain(tasks)
    before = listener._index_cache["dev-1"]

    repaired = _grouped_matrix()
    repaired.cells.append(ClimateCell(
        mode="cool", fan="auto", temp=25.0, pronto=PRONTO_COOL_22,
    ))
    write_matrix(tmp_path, "dev-1", repaired)
    dm._matrix = repaired
    _signal_matrix_changed(fake_hass, "dev-1")
    await _drain(tasks)

    after = listener._index_cache["dev-1"]
    assert after is not before
    assert {m[3] for g in after.groups.values() for m in g.members} == {
        22.0, 23.0, 25.0,
    }
    sent = await _press_and_send(listener, tasks, tm, dm, PRONTO_COOL_22)
    assert sent["spanned"] == {"temp": [22.0, 23.0, 25.0]}


@pytest.mark.asyncio
async def test_a_matrix_change_does_not_warm_an_unpinned_device(
    tmp_path, fake_hass,
):
    """On a Pi a large lattice is many seconds of an executor thread, so
    only a device some remote drives is rebuilt eagerly."""
    from custom_components.hair.websocket_api import _signal_matrix_changed

    from .test_websocket_api import _wire_triggers

    listener, store, _remote, _tm, _dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(), pinned=False,
    )
    _wire_triggers(fake_hass, store)
    fake_hass.data[DOMAIN]["entry-1"]["matrix_listener"] = listener

    _signal_matrix_changed(fake_hass, "dev-1")

    assert tasks == []


def _code_at(index, pronto):
    """The cell key the index answers for a code, or None."""
    identity = _identity(pronto)
    matched = index.match(
        identity.decoded_fingerprint, identity.fingerprint,
        identity.byte_hash,
    )
    return None if matched is None else matched[0].cell_key


@pytest.mark.asyncio
async def test_a_warm_never_stores_an_old_parse_under_the_new_files_hash(
    tmp_path,
):
    """An index built this run, then a cell's bytes rewritten on disk
    with no signal while this listener still holds the old parse, then
    a pin. The pin's warm must leave the warm index alone rather than
    rebuild it from that parse, so nothing old is stored under the new
    file's hash, which every later boot would believe: the restart
    finds the first build's hash, refuses it, and builds afresh. Once
    the change IS signalled, the build reads the new file."""
    from custom_components.hair.matrix_listener import _load_stored_index
    from custom_components.hair.matrix_store import write_matrix

    listener, _s, _r, _tm, _dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )
    listener.warm_index("dev-1")
    await _drain(tasks)
    built = listener._index_cache["dev-1"]
    old_parse = _grouped_matrix()
    listener._matrix_cache["dev-1"] = old_parse

    edited = _grouped_matrix()
    edited.cells[2].pronto = PRONTO_DEV_22
    write_matrix(tmp_path, "dev-1", edited)
    listener.warm_index("dev-1")  # the pin door

    # The warm index is left alone: no build, the same object.
    assert tasks == []
    assert listener._index_cache["dev-1"] is built
    # A restart refuses what is stored: its hash is the first file's.
    assert _load_stored_index(str(tmp_path), "dev-1", "C") is None

    # The edit signalled, as every writer now does: the index is
    # rebuilt from the file, and a restart reads that back.
    listener.invalidate("dev-1")
    listener.warm_index("dev-1")
    await _drain(tasks)
    assert _code_at(listener._index_cache["dev-1"], PRONTO_DEV_22) == (
        "cool/auto/24"
    )
    restarted = _load_stored_index(str(tmp_path), "dev-1", "C")
    assert restarted is not None
    assert _code_at(restarted, PRONTO_COOL_23) is None
    assert _code_at(restarted, PRONTO_DEV_22) == "cool/auto/24"


@pytest.mark.asyncio
async def test_a_build_reads_the_file_not_the_listeners_parse(tmp_path):
    """The other half of the same guard: a build that runs at all builds
    what is on disk."""
    from custom_components.hair.matrix_listener import _load_stored_index
    from custom_components.hair.matrix_store import write_matrix

    listener, _s, _r, _tm, _dm, _tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )
    listener._matrix_cache["dev-1"] = _grouped_matrix()
    edited = _grouped_matrix()
    edited.cells[2].pronto = PRONTO_DEV_22
    write_matrix(tmp_path, "dev-1", edited)

    await listener._async_build_index("dev-1")

    assert _code_at(listener._index_cache["dev-1"], PRONTO_DEV_22) == (
        "cool/auto/24"
    )
    assert _code_at(listener._index_cache["dev-1"], PRONTO_COOL_23) is None
    restarted = _load_stored_index(str(tmp_path), "dev-1", "C")
    assert _code_at(restarted, PRONTO_DEV_22) == "cool/auto/24"


@pytest.mark.asyncio
async def test_two_changes_during_one_build_end_on_the_second(tmp_path):
    """A build is in flight for change A when change B lands. B's warm
    is swallowed by the in-flight guard, so the build for A must notice
    it was overtaken: it neither caches nor writes, and builds again.
    The run ends on B, and a restart reads B back."""
    from custom_components.hair.matrix_listener import _load_stored_index
    from custom_components.hair.matrix_store import load_matrix, write_matrix

    listener, _s, _r, _tm, _dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )
    change_b = _grouped_matrix()
    change_b.cells[2].pronto = PRONTO_DEV_22
    executor = listener._hass.async_add_executor_job
    landed = []

    async def _job(func, *args):
        result = await executor(func, *args)
        if func is load_matrix and not landed:
            # A's file has been read; change B lands while A builds.
            landed.append(True)
            write_matrix(tmp_path, "dev-1", change_b)
            listener.invalidate("dev-1")
            listener.warm_index("dev-1")
        return result

    listener._hass.async_add_executor_job = _job
    change_a = _grouped_matrix()
    write_matrix(tmp_path, "dev-1", change_a)
    listener.invalidate("dev-1")
    listener.warm_index("dev-1")
    await _drain(tasks)

    assert landed
    index = listener._index_cache["dev-1"]
    assert _code_at(index, PRONTO_DEV_22) == "cool/auto/24"
    restarted = _load_stored_index(str(tmp_path), "dev-1", "C")
    assert restarted is not None
    assert _code_at(restarted, PRONTO_DEV_22) == "cool/auto/24"
    assert _code_at(restarted, PRONTO_COOL_23) is None


@pytest.mark.asyncio
async def test_a_torn_read_overtaken_by_its_writers_signal_builds_again(
    tmp_path,
):
    """A build reads the file while it is being rewritten and gets
    nothing back; the writer's signal lands meanwhile, and its warm is
    swallowed because the id is mid-build. The re-run is decided from
    the invalidation count, not from which line returned, so the index
    is built once the read finishes rather than at the next press."""
    from custom_components.hair.matrix_store import load_matrix

    listener, _s, _r, _tm, _dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )
    executor = listener._hass.async_add_executor_job
    torn = []

    async def _job(func, *args):
        if func is load_matrix and not torn:
            torn.append(True)
            listener.invalidate("dev-1")
            listener.warm_index("dev-1")  # swallowed: mid-build
            return None
        return await executor(func, *args)

    listener._hass.async_add_executor_job = _job
    listener.warm_index("dev-1")
    await _drain(tasks)

    assert torn
    assert listener._index_cache["dev-1"].groups
    assert listener._building == set()


@pytest.mark.asyncio
async def test_a_build_that_fails_after_an_invalidate_builds_again(tmp_path):
    """The same rule when the build raises instead."""
    from custom_components.hair.matrix_store import load_matrix

    listener, _s, _r, _tm, _dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )
    executor = listener._hass.async_add_executor_job
    failed = []

    async def _job(func, *args):
        if func is load_matrix and not failed:
            failed.append(True)
            listener.invalidate("dev-1")
            raise OSError("file busy")
        return await executor(func, *args)

    listener._hass.async_add_executor_job = _job
    listener.warm_index("dev-1")
    with pytest.raises(OSError):
        await tasks.pop(0)
    await _drain(tasks)

    assert listener._index_cache["dev-1"].groups


@pytest.mark.asyncio
async def test_the_dispatch_check_runs_no_group_pass(tmp_path):
    """The dispatch only asks whether the device has the state; the send
    resolves again. One group pass per press, not two."""
    listener, _s, _r, tm, dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )
    listener._index_cache["dev-1"] = build_cell_index(_grouped_matrix())
    calls = []
    real = listener._merged_group_send

    def _counted(*args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    listener._merged_group_send = _counted

    sent = await _press_and_send(listener, tasks, tm, dm, PRONTO_COOL_22)

    assert tm.dispatch_cell_retransmit.call_count == 1
    assert calls == ["dev-1"]
    assert sent["spanned"] == {"temp": [22.0, 23.0]}


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["cool", 3, ["dry"], RuntimeError])
async def test_a_bad_climate_state_costs_the_name_never_the_send(
    tmp_path, answer,
):
    """A provider answer that is not a dict, or anything that breaks the
    group pass, leaves the send as base: the representative's bytes,
    named as itself, with no group keys."""
    listener, _s, _r, tm, dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(),
    )
    listener._index_cache["dev-1"] = build_cell_index(_grouped_matrix())
    if answer is RuntimeError:
        def _broken(*_args, **_kwargs):
            raise RuntimeError("group pass broke")

        listener._merged_group_send = _broken
        dm.climate_state = lambda _device_id: {"temp": 22.0}
    else:
        dm.climate_state = lambda _device_id: answer

    sent = await _press_and_send(listener, tasks, tm, dm, PRONTO_COOL_22)

    assert dm.sends[-1][2] == PRONTO_COOL_22
    if answer is RuntimeError:
        assert "spanned" not in sent
        assert dm.sends[-1][1] == "cool / fan: auto / 23"
    else:
        # Not a state at all: the press is named as the range.
        assert sent["spanned"] == {"temp": [22.0, 23.0]}
        assert dm.sends[-1][1] == "cool / fan: auto / 22-23"


@pytest.mark.asyncio
async def test_a_flat_remote_pinned_to_a_matrix_device_warms_nothing(
    tmp_path, fake_hass,
):
    """Only a matrix remote's sends read a device's merged groups, so
    neither the pin door nor a matrix change builds an index for a
    device only a flat remote drives."""
    from custom_components.hair.websocket_api import (
        _signal_matrix_changed,
        ws_pin_trigger_remote_device,
    )

    from .test_websocket_api import _make_connection, _wire_triggers

    listener, store, remote, _tm, _dm, tasks = _bench(
        tmp_path, _grouped_matrix(), _grouped_matrix(), pinned=False,
    )
    remote.climate_matrix = False
    _wire_triggers(fake_hass, store)
    fake_hass.data[DOMAIN]["entry-1"]["matrix_listener"] = listener
    store.get_trigger_remote = MagicMock(return_value=remote)

    await ws_pin_trigger_remote_device(fake_hass, _make_connection(), {
        "id": 1, "type": "hair/trigger-remote/pin",
        "remote_id": "r1", "device_id": "dev-1",
    })
    assert remote.pinned_device_ids == ["dev-1"]
    _signal_matrix_changed(fake_hass, "dev-1")

    assert tasks == []
