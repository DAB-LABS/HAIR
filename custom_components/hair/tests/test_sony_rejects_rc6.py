"""The Sony decoder checks every space against 1T, so RC-6 is not Sony.

SIRC sends every space at 1T (600us); its data is in the marks. Until
this was checked, a space only had to sit in a 240..1200us sanity range,
so an RC-6 frame (888us leader space, 444 and 888us half-bits) holding
12, 15 or 20 marks read as Sony, and Sony probes ahead of RC-6. Mode 0
lost 6,324 of its 65,536 pairs that way, D=0 F=1 among them.

Rows stored under the wrong reading are read again on load
(``REJUDGED_LABELS`` in protocol_decode); the last section covers that.
"""
from __future__ import annotations

import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.decoders.sony import SonyCommand
from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_fingerprint,
)
from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
from custom_components.hair.protocol_decode import (
    REJUDGED_LABELS,
    get_spec,
    stored_identity_is_stale,
    try_decode_identity,
)

#: What the old Sony reading gave RC-6 D=0 for F=1, 2, 3, 4, 6, 7, 8, 12
#: and 28 others: one identity for 36 buttons.
OLD_READING = ("SONY20", 0, 0, "SONY20:0x0000:0x00")


def _rc6(address: int, command: int, **kwargs) -> list[int]:
    return list(
        get_spec("RC6").command_cls(
            address=address, command=command, **kwargs
        ).get_raw_timings()
    )


def _sony(address: int, bits: int, command: int, repeats: int = 0) -> list[int]:
    return SonyCommand(
        address=address, address_bits=bits, command=command, repeat_count=repeats
    ).get_raw_timings()


def _fingerprint(timings: list[int]) -> str | None:
    identity = try_decode_identity(timings)
    return identity.fingerprint if identity else None


def _jitter(timings: list[int], rng: random.Random, model: str) -> list[int]:
    out = []
    for value in timings:
        size, mark = abs(value), value > 0
        if size < 4000:
            if model == "tsop":
                size = size + rng.randint(0, 150) if mark else size - rng.randint(0, 150)
            elif model == "agc":
                size = size * rng.uniform(0.83, 0.95) if mark else size * rng.uniform(1.0, 1.12)
            else:
                size = size * rng.uniform(0.8, 1.2)
        out.append(int(size) if mark else -int(size))
    return out


# ---------------------------------------------------------------------------
# 1. RC-6 reads as RC-6
# ---------------------------------------------------------------------------


class TestRC6IsNotSony:
    @pytest.mark.parametrize("toggle", [0, 1])
    def test_device_zero_every_function(self, toggle):
        for command in range(256):
            identity = try_decode_identity(_rc6(0, command, mode=0, toggle=toggle))
            assert identity.protocol == "RC6", command
            assert (identity.address, identity.command) == (0, command)

    @pytest.mark.parametrize("toggle", [0, 1])
    def test_a_seeded_sample_of_every_pair(self, toggle):
        """The full sweep is in the report; it takes about 8s a pass."""
        rng = random.Random(6000 + toggle)
        for _ in range(2000):
            address, command = rng.randrange(256), rng.randrange(256)
            identity = try_decode_identity(
                _rc6(address, command, mode=0, toggle=toggle)
            )
            assert identity.protocol == "RC6", (address, command)
            assert (identity.address, identity.command) == (address, command)

    def test_mce_was_never_affected_and_still_is_not(self):
        rng = random.Random(800)
        for _ in range(500):
            address, command = rng.randrange(128), rng.randrange(256)
            identity = try_decode_identity(
                _rc6(address, command, mode=6, customer=0x800F, toggle=0)
            )
            assert identity.protocol == "RC6"

    @pytest.mark.parametrize("command", [1, 12])
    def test_the_reported_pairs_are_pinned(self, command):
        assert _fingerprint(_rc6(0, command, mode=0, toggle=0)) == (
            f"RC6:0x0000:{command:#04x}:m0"
        )

    def test_the_sony_decoder_alone_refuses_an_rc6_frame(self):
        assert SonyCommand.from_raw_timings(_rc6(0, 1, mode=0, toggle=0)) is None

    def test_an_irdb_rc6_row_is_stored_as_rc6_and_not_bypassed(self):
        from custom_components.hair import irdb_csv
        from custom_components.hair.wig_adapters import _triple_reproduces

        timings = list(irdb_csv.build("RC6", 0, -1, 12).get_raw_timings())
        pronto = raw_to_pronto(timings, frequency=36000)
        assert _fingerprint(timings) == "RC6:0x0000:0x0c:m0"
        assert _triple_reproduces(pronto, timings) is True


# ---------------------------------------------------------------------------
# 2. The check itself
# ---------------------------------------------------------------------------


def _with_space(index: int, value: int) -> list[int]:
    """A SONY15 frame with the space at ``index`` (1-based pair) changed."""
    frame = _sony(0x97, 8, 0x27)[:-1]
    frame[2 * index - 1] = -value
    return frame


class TestTheSpaceCheck:
    @pytest.mark.parametrize("space", [360, 840])
    def test_the_window_edges_decode(self, space):
        assert _fingerprint(_with_space(5, space)) == "SONY15:0x0097:0x27"

    @pytest.mark.parametrize("space", [355, 845, 888, 1200])
    def test_outside_the_window_does_not(self, space):
        assert SonyCommand.from_raw_timings(_with_space(5, space)) is None

    def test_the_space_after_the_leader_is_checked(self):
        assert SonyCommand.from_raw_timings(_with_space(1, 888)) is None

    def test_the_last_space_is_checked(self):
        assert SonyCommand.from_raw_timings(_with_space(15, 888)) is None

    def test_the_marks_keep_their_wide_test(self):
        """A 1T mark read long or a 2T mark read short still classifies."""
        frame = _sony(0x97, 8, 0x27)[:-1]
        frame[2] = 940  # bit 0 is a 1: its 2T mark read short
        frame[8] = 860  # bit 3 is a 0: its 1T mark read long
        assert _fingerprint(frame) == "SONY15:0x0097:0x27"


class TestJitteredSonyStillDecodes:
    @pytest.mark.parametrize("model", ["tsop", "agc", "symmetric"])
    @pytest.mark.parametrize("bits", [5, 8, 13])
    def test_every_width(self, model, bits):
        rng = random.Random(bits * 31 + len(model))
        for _ in range(300):
            address, command = rng.randrange(1 << bits), rng.randrange(128)
            identity = try_decode_identity(
                _jitter(_sony(address, bits, command, repeats=2), rng, model)
            )
            assert identity is not None
            assert identity.protocol == f"SONY{7 + bits}"
            assert (identity.address, identity.command) == (address, command)


# ---------------------------------------------------------------------------
# 3. Rows stored under the old reading
# ---------------------------------------------------------------------------


def _code(timings: list[int], hz: int = 36000) -> str:
    return raw_to_pronto([*timings, -90000], frequency=hz)


def _heard(timings: list[int], hz: int = 36000) -> tuple:
    code = _code(timings, hz)
    identity = try_decode_identity(ProntoCommand(code).get_raw_timings())
    return (
        canonical_fingerprint("PRONTO", code, None),
        canonical_byte_hash(code),
        identity.fingerprint if identity else None,
    )


def _stamped(command, reading) -> None:
    protocol, address, value, fingerprint = reading
    command.decoded_protocol = protocol
    command.decoded_address = address
    command.decoded_command = value
    command.decoded_fingerprint = fingerprint
    command.decode_covers = True


#: A SIRC frame whose every space is 880us: inside the old sanity range,
#: outside 1T, and nothing else reads it. Its old reading is what the
#: Sony fields say.
LONG_SPACES = [v if v > 0 else -880 for v in _sony(0x97, 8, 0x27)[:-1]]
LONG_SPACES_READING = ("SONY15", 0x97, 0x27, "SONY15:0x0097:0x27")


class _FakeBacking:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


async def _load(devices: list, triggers: list):
    from custom_components.hair.storage import HAIRStore

    backing = _FakeBacking()
    backing._data = {
        "devices": [device.to_dict() for device in devices],
        "triggers": triggers,
    }
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    with patch(
        "custom_components.hair.storage._HAIRDeviceStore",
        lambda *a, **k: backing,
    ):
        store = HAIRStore(hass)
        await store.async_load()
    return store


def _trigger(trigger_id: str, timings: list[int], decoded: str | None) -> dict:
    code = _code(timings)
    return {
        "id": trigger_id,
        "name": trigger_id,
        "signal_fingerprint": canonical_fingerprint("PRONTO", code, None),
        "byte_hash": canonical_byte_hash(code),
        "decoded_fingerprint": decoded,
        "protocol": "PRONTO",
        "code": code,
    }


def test_the_sony_labels_are_rejudged():
    # GEAC joined in 1.2 (test_proton_decoder); no other label may.
    assert {"SONY12", "SONY15", "SONY20", "GEAC"} == REJUDGED_LABELS


def test_the_old_reading_is_stale_and_a_true_sony_one_is_not():
    assert stored_identity_is_stale(OLD_READING[3], _rc6(0, 1, mode=0, toggle=0))
    sony = _sony(0x97, 8, 0x27)
    assert not stored_identity_is_stale("SONY15:0x0097:0x27", sony)
    # Another label is never asked again, whatever it holds.
    assert not stored_identity_is_stale("RC5:0x0005:0x35", sony)
    # Nothing to decode, nothing to judge.
    assert not stored_identity_is_stale(OLD_READING[3], None)


@pytest.mark.asyncio
async def test_a_device_command_is_read_again_and_sends_rc6():
    from custom_components.hair.models import IRCommand, IRDevice
    from custom_components.hair.send_plan import build_like_send_path

    device = IRDevice(name="Philips TV")
    power = IRCommand(name="Power", protocol="PRONTO",
                      code=_code(_rc6(0, 1, mode=0, toggle=0)))
    _stamped(power, OLD_READING)
    device.commands.append(power)

    store = await _load([device], [])
    loaded = store._data[device.id].commands[0]
    assert loaded.decoded_fingerprint == "RC6:0x0000:0x01:m0"
    assert loaded.decoded_protocol == "RC6"
    assert loaded.decode_covers is True
    built = build_like_send_path(loaded)
    assert isinstance(built, get_spec("RC6").command_cls)
    assert _fingerprint(list(built.get_raw_timings())) == "RC6:0x0000:0x01:m0"
    # Idempotent: asking again changes nothing.
    assert store._clear_stale_identities() is False
    assert store._backfill_decoded_fields() is False


@pytest.mark.asyncio
async def test_a_trigger_is_read_again_and_fires_on_its_own_button_only():
    own = _rc6(0, 1, mode=0, toggle=0)
    sibling = _rc6(0, 2, mode=0, toggle=0)
    store = await _load([], [_trigger("t_power", own, OLD_READING[3])])
    trigger = store.get_trigger("t_power")
    assert trigger.decoded_fingerprint == "RC6:0x0000:0x01:m0"

    # Before: the sibling carried the same old identity and fired it.
    assert trigger.matches_signal(*_heard(own)) is True
    assert trigger not in store.get_triggers_for_signal(None, None, *_heard(sibling))
    assert trigger in store.get_triggers_for_signal(None, None, *_heard(own))


@pytest.mark.asyncio
async def test_a_true_sony_command_and_trigger_are_untouched():
    from custom_components.hair.models import IRCommand, IRDevice

    sony = _sony(0x97, 8, 0x27)
    device = IRDevice(name="Bravia")
    mute = IRCommand(name="Mute", protocol="PRONTO", code=_code(sony, 40000))
    _stamped(mute, ("SONY15", 0x97, 0x27, "SONY15:0x0097:0x27"))
    device.commands.append(mute)
    store = await _load(
        [device], [_trigger("t_mute", sony, "SONY15:0x0097:0x27")]
    )
    loaded = store._data[device.id].commands[0]
    assert loaded.decoded_fingerprint == "SONY15:0x0097:0x27"
    assert store.get_trigger("t_mute").decoded_fingerprint == "SONY15:0x0097:0x27"
    assert store._clear_stale_identities() is False


@pytest.mark.asyncio
async def test_an_identity_nothing_gives_any_more_is_cleared():
    """The row sends its stored code, and its trigger still matches."""
    from custom_components.hair.models import IRCommand, IRDevice
    from custom_components.hair.send_plan import build_like_send_path

    assert try_decode_identity(LONG_SPACES) is None
    device = IRDevice(name="Odd Sony")
    row = IRCommand(name="Input", protocol="PRONTO", code=_code(LONG_SPACES, 40000))
    _stamped(row, LONG_SPACES_READING)
    device.commands.append(row)
    store = await _load(
        [device], [_trigger("t_input", LONG_SPACES, LONG_SPACES_READING[3])]
    )

    loaded = store._data[device.id].commands[0]
    assert loaded.decoded_fingerprint is None
    assert loaded.decoded_protocol is None
    assert loaded.decode_covers is None
    assert not isinstance(build_like_send_path(loaded), SonyCommand)

    trigger = store.get_trigger("t_input")
    assert trigger.decoded_fingerprint is None
    assert trigger in store.get_triggers_for_signal(
        None, None, *_heard(LONG_SPACES)
    )
    assert trigger.matches_signal(*_heard(LONG_SPACES)) is True
    assert trigger not in store.get_triggers_for_signal(
        None, None, *_heard(_sony(0x97, 8, 0x26), 40000)
    )


def test_a_sniffer_row_is_read_again_and_keeps_its_own_button():
    from custom_components.hair.models import UnknownDevice, UnknownSignal
    from custom_components.hair.signal_store import _transform_loaded

    own = _rc6(0, 1, mode=0, toggle=0)
    code = _code(own)
    device = UnknownDevice(label="Philips TV")
    signal = UnknownSignal(
        id="s1", protocol="PRONTO", code=code,
        fingerprint=canonical_fingerprint("PRONTO", code, None),
        byte_hash=canonical_byte_hash(code),
        alias="Power / Volume", hit_count=9,
    )
    _stamped(signal, OLD_READING)
    device.signals = [signal]

    devices, _dismissed, dirty = _transform_loaded(
        {"devices": [device.to_dict()], "dismissed": []}
    )
    loaded = next(iter(devices.values()))
    row = loaded.signals[0]
    assert dirty is True
    assert row.decoded_fingerprint == "RC6:0x0000:0x01:m0"
    assert row.decode_covers is True
    assert (row.alias, row.hit_count) == ("Power / Volume", 9)
    assert loaded.get_signal(*_heard(own)) is row
    assert loaded.get_signal(*_heard(_rc6(0, 2, mode=0, toggle=0))) is None

    # A second load has nothing to do.
    _devices, _dismissed, dirty = _transform_loaded(
        {"devices": [loaded.to_dict()], "dismissed": []}
    )
    assert dirty is False
