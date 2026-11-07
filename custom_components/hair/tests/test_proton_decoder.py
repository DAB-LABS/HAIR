"""Proton, and the unit that keeps it apart from GE-AC.

Every capture below is written by hand from the two definitions:
Proton's IRP ``{38k,500}<1,-1|1,-3>(16,-8,D:8,1,-8,F:8,1,^63m)+`` (LSB
first, 500us unit) and the library's GE-AC frame (9000/4500 leader,
562/562 and 562/1687 bits, MSB first, a 562/4500 stop and gap between
the bytes). Same layout, units 500 and 562.5us.
"""
from __future__ import annotations

import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.decoders.proton import (
    GEAC_UNIT_MIN_US,
    PROTON_UNIT_MAX_US,
    ProtonCommand,
    frame_unit_us,
)
from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_fingerprint,
)
from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
from custom_components.hair.protocol_decode import (
    build_protocol_command,
    get_spec,
    stored_identity_is_stale,
    try_decode_identity,
)
from custom_components.hair.tests.leg import ge_ac_decoder_available

GAP = -40000


def _proton(address: int, command: int, unit: float = 500) -> list[int]:
    """A Proton frame, LSB first, on ``unit``."""
    def bits(value: int) -> list[int]:
        out = []
        for i in range(8):
            out += [unit, -(3 * unit if (value >> i) & 1 else unit)]
        return out

    frame = [16 * unit, -8 * unit, *bits(address), unit, -8 * unit,
             *bits(command), unit]
    return [int(v) for v in frame]


def _geac(address: int, command: int, scale: float = 1.0) -> list[int]:
    """A GE-AC frame on the library's numbers, MSB first."""
    def bits(value: int) -> list[int]:
        out = []
        for i in range(8):
            out += [562, -(1687 if (value >> (7 - i)) & 1 else 562)]
        return out

    frame = [9000, -4500, *bits(address), 562, -4500, *bits(command), 562]
    return [int(v * scale) for v in frame]


def _futarque(code: int) -> list[int]:
    """The Futarque LIRC remote's own timings: pre_data 0x54, MSB first."""
    def bits(value: int) -> list[int]:
        out = []
        for i in range(8):
            out += [555, -(1436 if (value >> (7 - i)) & 1 else 439)]
        return out

    return [8048, -3898, *bits(0x54), 570, -3890, *bits(code), 555]


def _reversed(byte: int) -> int:
    return int(f"{byte:08b}"[::-1], 2)


def _jitter(timings: list[int], rng: random.Random, model: str) -> list[int]:
    out = []
    for value in timings:
        size, mark = abs(value), value > 0
        if model == "tsop":
            size = size + rng.randint(0, 150) if mark else size - rng.randint(0, 150)
        elif model == "agc":
            size = size * rng.uniform(0.83, 0.95) if mark else size * rng.uniform(1.0, 1.12)
        elif model == "broadlink":
            tick = 1_000_000 / 32_768
            size = round(size / tick) * tick
        out.append(int(size) if mark else -int(size))
    return out


def _label(timings: list[int]) -> str:
    identity = try_decode_identity(timings)
    return identity.protocol if identity else "raw"


# ---------------------------------------------------------------------------
# 1. Proton itself
# ---------------------------------------------------------------------------


class TestEncodeDecode:
    def test_every_value_round_trips(self):
        for address in range(256):
            for command in range(256):
                timings = ProtonCommand(address=address, command=command).get_raw_timings()
                decoded = ProtonCommand.from_raw_timings(timings)
                assert (decoded.address, decoded.command) == (address, command)

    def test_the_encoder_is_the_irp(self):
        assert ProtonCommand(address=0x2A, command=0x0E).get_raw_timings() == (
            _proton(0x2A, 0x0E)
        )

    def test_a_held_press_repeats_on_the_63ms_period(self):
        timings = ProtonCommand(address=1, command=2, repeat_count=2).get_raw_timings()
        frame = _proton(1, 2)
        assert timings[: len(frame)] == frame
        assert sum(abs(v) for v in timings[: len(frame) + 1]) == 63000
        decoded = ProtonCommand.from_raw_timings(timings)
        assert decoded.repeat_count == 2
        identity = try_decode_identity(timings)
        assert identity.covers_capture is True

    @pytest.mark.parametrize("field", ["address", "command"])
    def test_fields_are_bounds_checked(self, field):
        kwargs = {"address": 0, "command": 0, field: 0x100}
        with pytest.raises(ValueError):
            ProtonCommand(**kwargs)

    def test_the_fingerprint_is_pinned(self):
        assert try_decode_identity(_proton(0xDD, 0xFF)).fingerprint == (
            "PROTON:0x00dd:0xff"
        )

    def test_the_encoder_matches_the_librarys(self):
        """The package rule, where the library ships ProtonCommand (9.1.0+)."""
        upstream = pytest.importorskip("infrared_protocols.commands.proton")
        rng = random.Random(91)
        for _ in range(200):
            a, c = rng.randrange(256), rng.randrange(256)
            ours = ProtonCommand(address=a, command=c)
            theirs = upstream.ProtonCommand(address=a, command=c)
            assert ours.get_raw_timings() == theirs.get_raw_timings()
            assert ours.modulation == theirs.modulation


class TestTheUnit:
    def test_the_two_nominal_units(self):
        assert frame_unit_us(_proton(0x2A, 0x0E), 6) == 500
        assert abs(frame_unit_us(_geac(0x54, 0x70), 6) - 562.5) < 1

    def test_the_windows_leave_a_gap(self):
        assert 500 < PROTON_UNIT_MAX_US < GEAC_UNIT_MIN_US < 562.5

    @pytest.mark.parametrize("model", ["none", "tsop", "agc", "broadlink"])
    def test_jittered_proton_reads_as_proton(self, model):
        rng = random.Random(len(model))
        for _ in range(400):
            a, c = rng.randrange(256), rng.randrange(256)
            identity = try_decode_identity(_jitter(_proton(a, c), rng, model))
            assert identity is not None, model
            assert (identity.protocol, identity.address, identity.command) == (
                "PROTON", a, c,
            )

    @pytest.mark.parametrize("model", ["none", "tsop", "agc", "broadlink"])
    def test_jittered_ge_ac_is_never_proton(self, model):
        rng = random.Random(len(model) + 7)
        for _ in range(400):
            a, c = rng.randrange(256), rng.randrange(256)
            timings = _jitter(_geac(a, c), rng, model)
            assert ProtonCommand.from_raw_timings(timings) is None
            identity = try_decode_identity(timings)
            if ge_ac_decoder_available():
                assert (identity.protocol, identity.address, identity.command) == (
                    "GEAC", a, c,
                )
            else:
                assert identity is None or identity.protocol != "PROTON"

    def test_a_frame_between_the_windows_is_read_by_neither(self):
        between = _geac(0x54, 0x70, scale=530 / 562.5)
        assert PROTON_UNIT_MAX_US < frame_unit_us(between, 6) < GEAC_UNIT_MIN_US
        assert ProtonCommand.from_raw_timings(between) is None
        assert try_decode_identity(between) is None

    def test_the_futarque_shape_is_proton(self):
        for code in (0x70, 0xA8, 0xF0, 0x00):
            timings = [*_futarque(code), GAP, *_futarque(code)]
            identity = try_decode_identity(timings)
            assert (identity.protocol, identity.address, identity.command) == (
                "PROTON", 0x2A, _reversed(code),
            )

    def test_the_librarys_proton_decoder_takes_ge_ac_frames(self):
        """The overlap the unit check exists for, pinned where it is."""
        upstream = pytest.importorskip("infrared_protocols.commands.proton")
        assert upstream.ProtonCommand.from_raw_timings(_geac(0x54, 0x70)) is not None


class TestGeAcStaysOffProton:
    def test_proton_frames_are_never_ge_ac_on_any_leg(self):
        rng = random.Random(6)
        for _ in range(400):
            a, c = rng.randrange(256), rng.randrange(256)
            assert _label(_proton(a, c)) == "PROTON"

    def test_the_librarys_ge_ac_decoder_still_takes_them_alone(self):
        """Why HAIR checks GE-AC's decode: the library's class, called
        directly, still reads a Proton frame."""
        upstream = pytest.importorskip("infrared_protocols.commands.general_electric")
        assert upstream.GEACCommand.from_raw_timings(_proton(0x2A, 0x0E)) is not None

    def test_ge_ac_frames_still_read_as_ge_ac(self):
        if not ge_ac_decoder_available():
            pytest.skip("no GE-AC decoder on this leg")
        assert try_decode_identity(_geac(0x54, 0x70)).fingerprint == "GEAC:0x0054:0x70"


# ---------------------------------------------------------------------------
# 2. The registry and transmit
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_it_is_local_and_identity_only(self):
        spec = get_spec("PROTON")
        assert spec.source == "local"
        assert spec.command_cls is ProtonCommand
        assert spec.tx_rebuild is False

    def test_a_proton_row_sends_its_stored_code(self):
        assert build_protocol_command("PROTON", 0x2A, 0x0E) is None

    def test_an_imported_proton_row_is_not_bypassed(self):
        from custom_components.hair.wig_adapters import _triple_reproduces

        timings = _futarque(0x70)
        assert _triple_reproduces(raw_to_pronto(timings), timings) is True


# ---------------------------------------------------------------------------
# 3. Rows stored as GE-AC
# ---------------------------------------------------------------------------


#: What the library's GE-AC decoder made of the Futarque Mute button.
OLD_GEAC = ("GEAC", 0x54, 0x70, "GEAC:0x0054:0x70")
MUTE = [*_futarque(0x70), GAP, *_futarque(0x70)]


def _code(timings: list[int]) -> str:
    return raw_to_pronto([*timings, -60000], frequency=38000)


def _heard(timings: list[int]) -> tuple:
    code = _code(timings)
    identity = try_decode_identity(ProntoCommand(code).get_raw_timings())
    return (
        canonical_fingerprint("PRONTO", code, None),
        canonical_byte_hash(code),
        identity.fingerprint if identity else None,
    )


def _stamp(row, reading) -> None:
    row.decoded_protocol, row.decoded_address, row.decoded_command, \
        row.decoded_fingerprint = reading
    row.decode_covers = None


class _FakeBacking:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


async def _load(devices, triggers):
    from custom_components.hair.storage import HAIRStore

    backing = _FakeBacking()
    backing._data = {
        "devices": [d.to_dict() for d in devices], "triggers": triggers,
    }
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(side_effect=lambda f, *a: f(*a))
    with patch(
        "custom_components.hair.storage._HAIRDeviceStore",
        lambda *a, **k: backing,
    ):
        store = HAIRStore(hass)
        await store.async_load()
    return store


def _trigger(trigger_id: str, timings: list[int], decoded: str) -> dict:
    code = _code(timings)
    return {
        "id": trigger_id, "name": trigger_id,
        "signal_fingerprint": canonical_fingerprint("PRONTO", code, None),
        "byte_hash": canonical_byte_hash(code),
        "decoded_fingerprint": decoded, "protocol": "PRONTO", "code": code,
    }


def test_the_old_reading_is_stale_and_a_true_ge_ac_one_is_not():
    assert stored_identity_is_stale(OLD_GEAC[3], MUTE)
    assert not stored_identity_is_stale("GEAC:0x0054:0x70", _geac(0x54, 0x70))


def test_a_true_ge_ac_row_keeps_its_identity_where_nothing_decodes_it():
    """Without the library's GE-AC decoder a genuine GE-AC row decodes to
    nothing, and that is not a reason to clear it."""
    with patch(
        "custom_components.hair.protocol_decode.get_spec",
        side_effect=lambda label: None if label == "GEAC" else get_spec(label),
    ), patch(
        "custom_components.hair.protocol_decode.try_decode_identity",
        return_value=None,
    ):
        assert not stored_identity_is_stale("GEAC:0x0054:0x70", _geac(0x54, 0x70))


@pytest.mark.asyncio
async def test_a_command_and_a_trigger_stored_as_ge_ac_become_proton():
    from custom_components.hair.models import IRCommand, IRDevice

    device = IRDevice(name="Futarque")
    mute = IRCommand(name="Mute", protocol="PRONTO", code=_code(MUTE))
    _stamp(mute, OLD_GEAC)
    device.commands.append(mute)
    store = await _load([device], [_trigger("t_mute", MUTE, OLD_GEAC[3])])

    loaded = store._data[device.id].commands[0]
    assert loaded.decoded_fingerprint == "PROTON:0x002a:0x0e"
    assert loaded.decoded_protocol == "PROTON"
    trigger = store.get_trigger("t_mute")
    assert trigger.decoded_fingerprint == "PROTON:0x002a:0x0e"
    exit_press = [*_futarque(0xA8), GAP, *_futarque(0xA8)]
    assert trigger in store.get_triggers_for_signal(None, None, *_heard(MUTE))
    assert trigger not in store.get_triggers_for_signal(
        None, None, *_heard(exit_press)
    )
    # Asking again changes nothing.
    assert store._clear_stale_identities() is False


@pytest.mark.asyncio
async def test_a_true_ge_ac_command_is_untouched():
    from custom_components.hair.models import IRCommand, IRDevice

    timings = [*_geac(0x54, 0x70), GAP, *_geac(0x54, 0x70)]
    device = IRDevice(name="GE AC")
    row = IRCommand(name="Cool", protocol="PRONTO", code=_code(timings))
    _stamp(row, OLD_GEAC)
    device.commands.append(row)
    store = await _load([device], [])
    loaded = store._data[device.id].commands[0]
    assert loaded.decoded_fingerprint == "GEAC:0x0054:0x70"
    assert store._clear_stale_identities() is False


def test_a_sniffer_row_stored_as_ge_ac_becomes_proton():
    from custom_components.hair.models import UnknownDevice, UnknownSignal
    from custom_components.hair.signal_store import _transform_loaded

    code = _code(MUTE)
    signal = UnknownSignal(
        id="s1", protocol="PRONTO", code=code,
        fingerprint=canonical_fingerprint("PRONTO", code, None),
        byte_hash=canonical_byte_hash(code), alias="Mute", hit_count=3,
    )
    _stamp(signal, OLD_GEAC)
    device = UnknownDevice(label="Futarque")
    device.signals = [signal]
    devices, _dismissed, dirty = _transform_loaded(
        {"devices": [device.to_dict()], "dismissed": []}
    )
    row = next(iter(devices.values())).signals[0]
    assert dirty is True
    assert row.decoded_fingerprint == "PROTON:0x002a:0x0e"
    assert (row.alias, row.hit_count) == ("Mute", 3)
