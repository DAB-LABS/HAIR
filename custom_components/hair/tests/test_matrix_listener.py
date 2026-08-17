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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import DOMAIN, EVENT_STATE_HEARD
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


def _listener_ready(remote, store=None, trigger_manager=None):
    """A listener with the remote's index already built."""
    store = store or _store_with(remote)
    hass = _hass(store)
    listener = MatrixListener(hass, store, trigger_manager)
    listener._matrix_cache[remote.id] = _matrix()
    listener._index_cache[remote.id] = build_cell_index(_matrix())
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

    hit = index.match(
        identity.decoded_fingerprint, identity.fingerprint, identity.byte_hash
    )
    assert hit is not None
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

    hit = index.match(None, "a-fingerprint-from-another-capture",
                      identity.byte_hash)
    assert hit is not None
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

    hit = index.match(
        heard.decoded_fingerprint, heard.fingerprint, heard.byte_hash
    )
    assert hit is not None
    assert hit.cell_key == "cool/auto/22"


def test_index_keeps_the_file_form_too():
    """Both forms share one CellHit, so a paste of the stored code
    resolves to the same state a heard frame does."""
    index = build_cell_index(_matrix())
    filed = _identity(PRONTO_COOL_23)

    hit = index.match(
        filed.decoded_fingerprint, filed.fingerprint, filed.byte_hash
    )
    assert hit is not None
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
    listener._recent_hits["r1"] = 0.0
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

    async def async_get_matrix(self, device_id):
        return self._matrix

    async def async_send_matrix_cell(
        self, device_id, cell_name, pronto, send_count=1,
        heard_future=None, pinned=False,
    ):
        self.sends.append((device_id, cell_name, pronto, send_count, pinned))


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
        listener._recent_hits["r1"] = 0.0
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
    listener._recent_hits["r1"] = 0.0
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
    listener._recent_hits["r1"] = 0.0
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
    hit = restored.match(
        identity.decoded_fingerprint, identity.fingerprint, identity.byte_hash
    )
    assert hit is not None
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
    ).cell_key == "cool/auto/23"


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
