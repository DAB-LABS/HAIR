"""JVC: decode, encode, the probe order, and what the first load changes.

The protocol is the public IRP ``{38k,525}<1,-1|1,-3>(16,-8,(D:8,F:8,1,-45)+)``:
an 8400/4200 leader on the first frame only, sixteen bits LSB first (D,
then F), a stop mark, and a 23.6ms leadout. Every capture below is built
from those fields; none is copied from anywhere.
"""
from __future__ import annotations

import random
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.decoders.jvc import JVCCommand
from custom_components.hair.decoders.kaseikyo import KaseikyoCommand
from custom_components.hair.decoders.nec42 import NEC42Command
from custom_components.hair.decoders.pioneer import PioneerCommand
from custom_components.hair.decoders.rc5 import RC5Command
from custom_components.hair.decoders.rc6 import RC6Command
from custom_components.hair.decoders.rca import RCACommand
from custom_components.hair.decoders.samsung import Samsung32Command
from custom_components.hair.decoders.sharp import SharpCommand
from custom_components.hair.decoders.sony import SonyCommand
from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_fingerprint,
)
from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
from custom_components.hair.protocol_decode import (
    _ensure_registry,
    build_protocol_command,
    get_spec,
    try_decode_identity,
)

LEADOUT = -23625
GAP = -40000
SRC = Path(__file__).parents[1] / "frontend" / "src"
ADAPTERS = Path(__file__).parent / "fixtures" / "adapters"


def _bits(value: int, width: int, mark: int, zero: int, one: int) -> list[int]:
    """Pulse-distance bits, LSB first."""
    out: list[int] = []
    for i in range(width):
        out.extend((mark, -(one if (value >> i) & 1 else zero)))
    return out


def _jvc_frame(address: int, command: int, *, leader: bool = True) -> list[int]:
    body = [*_bits(address | (command << 8), 16, 525, 525, 1575), 525]
    return [8400, -4200, *body] if leader else body


def _nec_frame(address: int, command: int, *, complement: bool = True) -> list[int]:
    """An NEC1 frame on NEC's own timings, built here so both legs have it."""
    second = (~address & 0xFF) if complement else 0x00
    value = address | (second << 8) | (command << 16) | ((~command & 0xFF) << 24)
    return [9000, -4500, *_bits(value, 32, 560, 560, 1690), 560]


def _press(address: int, command: int, repeats: int = 0) -> list[int]:
    out = _jvc_frame(address, command)
    for _ in range(repeats):
        out.extend((LEADOUT, *_jvc_frame(address, command, leader=False)))
    return out


def _jitter(timings: list[int], rng: random.Random, marks=(-60, 120),
            spaces=(-120, 60)) -> list[int]:
    """Receiver-shaped noise: marks stretched, spaces shortened."""
    out = []
    for value in timings:
        lo, hi = marks if value > 0 else spaces
        out.append(value + rng.randint(lo, hi) * (1 if value > 0 else -1))
    return out


def _code(timings: list[int]) -> str:
    """The Pronto the send path would store for these timings."""
    return raw_to_pronto(list(timings), frequency=38000)


# ---------------------------------------------------------------------------
# 1. Encode and decode
# ---------------------------------------------------------------------------


class TestEncodeDecode:
    def test_every_value_of_both_fields_round_trips(self):
        for address in range(256):
            for command in range(256):
                timings = JVCCommand(address=address, command=command).get_raw_timings()
                decoded = JVCCommand.from_raw_timings(timings)
                assert decoded is not None, (address, command)
                assert (decoded.address, decoded.command) == (address, command)
                assert decoded.repeat_count == 0

    def test_the_encoder_is_the_irp(self):
        assert JVCCommand(address=0x03, command=0x17).get_raw_timings() == (
            _jvc_frame(0x03, 0x17)
        )

    @pytest.mark.parametrize("repeats", [0, 1, 3])
    def test_repeats_are_headerless_frames(self, repeats):
        timings = JVCCommand(
            address=0xA5, command=0x5A, repeat_count=repeats
        ).get_raw_timings()
        assert timings == _press(0xA5, 0x5A, repeats)
        assert len(timings) == 35 + 34 * repeats
        assert timings.count(8400) == 1

    @pytest.mark.parametrize("field", ["address", "command"])
    @pytest.mark.parametrize("value", [-1, 0x100])
    def test_fields_are_bounds_checked(self, field, value):
        kwargs = {"address": 0, "command": 0, field: value}
        with pytest.raises(ValueError):
            JVCCommand(**kwargs)

    def test_the_fingerprint_is_pinned(self):
        identity = try_decode_identity(_jvc_frame(0xDD, 0xFF))
        assert identity.protocol == "JVC"
        assert identity.fingerprint == "JVC:0x00dd:0xff"
        assert identity.extras is None


class TestDirtyCaptures:
    def test_jittered_presses(self):
        rng = random.Random(20261103)
        for _ in range(500):
            address, command = rng.randrange(256), rng.randrange(256)
            identity = try_decode_identity(_jitter(_jvc_frame(address, command), rng))
            assert identity is not None
            assert (identity.protocol, identity.address, identity.command) == (
                "JVC", address, command,
            )

    def test_a_held_press_votes_and_covers(self):
        rng = random.Random(7)
        capture = _jitter(_press(0x03, 0x17, repeats=4), rng)
        decoded = JVCCommand.from_raw_timings(capture)
        assert decoded.repeat_count == 4
        assert decoded.frames_explained == 5
        identity = try_decode_identity(capture)
        assert identity.fingerprint == "JVC:0x0003:0x17"
        assert identity.covers_capture is True

    def test_a_merged_capture_is_split_at_the_leadout(self):
        """Frames that arrive in one capture are read one by one."""
        tight = [*_jvc_frame(3, 0x17), -10500, *_jvc_frame(3, 0x17, leader=False)]
        decoded = JVCCommand.from_raw_timings(tight)
        assert (decoded.repeat_count, decoded.frames_explained) == (1, 2)

    def test_two_buttons_in_one_capture_take_the_majority_and_do_not_cover(self):
        capture = [
            *_press(3, 0x17, repeats=2), GAP, *_press(3, 0x18),
        ]
        identity = try_decode_identity(capture)
        assert identity.fingerprint == "JVC:0x0003:0x17"
        assert identity.covers_capture is False

    def test_the_trailing_leadout_and_idle_are_ignored(self):
        identity = try_decode_identity([*_press(9, 9, repeats=1), LEADOUT, -90000])
        assert identity.fingerprint == "JVC:0x0009:0x09"
        assert identity.covers_capture is True


class TestTheLeaderIsRequired:
    def test_a_leaderless_capture_decodes_to_nothing(self):
        frame = _jvc_frame(3, 0x17, leader=False)
        assert JVCCommand.from_raw_timings(frame) is None
        assert JVCCommand.from_raw_timings([*frame, LEADOUT, *frame]) is None

    def test_a_press_missing_its_first_frame_decodes_to_nothing(self):
        held = _press(3, 0x17, repeats=3)
        assert try_decode_identity(held[36:]) is None

    def test_headerless_frames_count_behind_a_leader(self):
        decoded = JVCCommand.from_raw_timings(_press(3, 0x17, repeats=2))
        assert decoded.frames_explained == 3


class TestRejects:
    @pytest.mark.parametrize("bits", [15, 17, 32])
    def test_a_frame_of_any_other_length(self, bits):
        frame = [8400, -4200, *_bits(0x1234, bits, 525, 525, 1575), 525]
        assert JVCCommand.from_raw_timings(frame) is None

    @pytest.mark.parametrize("space", [-900, -1000, -1100])
    def test_a_space_in_the_dead_zone(self, space):
        frame = _jvc_frame(0, 0)
        frame[3] = space
        assert JVCCommand.from_raw_timings(frame) is None

    def test_a_missing_stop_mark(self):
        assert JVCCommand.from_raw_timings(_jvc_frame(3, 0x17)[:-1]) is None

    @pytest.mark.parametrize("mark,space", [(6000, -4200), (8400, -3000),
                                            (11000, -4200), (8400, -5500)])
    def test_a_leader_off_its_windows(self, mark, space):
        frame = _jvc_frame(3, 0x17)
        frame[0], frame[1] = mark, space
        assert JVCCommand.from_raw_timings(frame) is None


class TestTheCutFinalFrame:
    def _cut(self, timings: int) -> list[int]:
        return [*_press(3, 0x17, repeats=2), LEADOUT,
                *_jvc_frame(3, 0x17, leader=False)[:timings]]

    def test_a_cut_final_frame_is_explained_but_does_not_vote(self):
        decoded = JVCCommand.from_raw_timings(self._cut(21))
        assert decoded.repeat_count == 2
        assert decoded.frames_explained == 4
        assert try_decode_identity(self._cut(21)).covers_capture is True

    def test_fewer_than_eight_bits_is_not_explained(self):
        decoded = JVCCommand.from_raw_timings(self._cut(15))
        assert decoded.frames_explained == 3

    def test_a_cut_frame_that_disagrees_is_not_explained(self):
        other = _jvc_frame(0xFC, 0x17, leader=False)[:21]
        capture = [*_press(3, 0x17, repeats=2), LEADOUT, *other]
        assert JVCCommand.from_raw_timings(capture).frames_explained == 3

    def test_a_lone_cut_frame_decodes_to_nothing(self):
        assert JVCCommand.from_raw_timings(_jvc_frame(3, 0x17)[:23]) is None


# ---------------------------------------------------------------------------
# 2. The probe order
# ---------------------------------------------------------------------------


def _others() -> list:
    return [spec for spec in _ensure_registry() if spec.key != "jvc"]


class TestNoEarlierProtocolTakesJVC:
    def test_jittered_presses_are_claimed_by_no_other_spec(self):
        rng = random.Random(16)
        captures = [
            _jitter(_press(rng.randrange(256), rng.randrange(256),
                           repeats=rng.randrange(3)), rng)
            for _ in range(300)
        ]
        for spec in _others():
            for capture in captures:
                assert spec.command_cls.from_raw_timings(list(capture)) is None, (
                    spec.key
                )

    def test_jvc_sits_after_geac_and_before_tdc38(self):
        keys = [spec.key for spec in _ensure_registry()]
        assert keys.index("jvc") == keys.index("tdc38") - 1
        if "geac" in keys:
            assert keys.index("geac") < keys.index("jvc")

    def test_it_is_local_and_rebuilds(self):
        spec = get_spec("JVC")
        assert spec.source == "local"
        assert spec.tx_rebuild is True
        assert spec.command_cls is JVCCommand


def _families() -> dict[str, list[int]]:
    kaseikyo = KaseikyoCommand(
        address=0x2002, data=bytes([0x00, 0x10, 0x3D])
    ).get_raw_timings()
    return {
        "nec": _nec_frame(0x04, 0x08),
        "nec_no_complement": _nec_frame(0x04, 0x08, complement=False),
        "samsung32": Samsung32Command(address=7, command=2).get_raw_timings(),
        "sharp": SharpCommand(address=1, command=0x31).get_raw_timings(),
        "kaseikyo": kaseikyo,
        "pioneer": PioneerCommand(address=0xA5, command=0x1C).get_raw_timings(),
        "nec42": NEC42Command(address=0x1234, command=0x56).get_raw_timings(),
        "rca": RCACommand(device=0xA, function=0x54).get_raw_timings(),
        "sony": SonyCommand(address=1, address_bits=5, command=21).get_raw_timings(),
        "rc5": RC5Command(address=5, command=0x35).get_raw_timings(),
        "rc6": RC6Command(address=4, command=0x0C).get_raw_timings(),
        # Mitsubishi's 16-bit frame: no leader, 300us marks, 900/2100
        # spaces. The documented near neighbour of a headerless JVC frame.
        "mitsubishi_like": [*_bits(0x4747, 16, 300, 900, 2100), 300],
        # GE-AC's sixteen bits, split by a 4.5ms space.
        "geac_like": [9000, -4500, *_bits(0x5A, 8, 562, 562, 1687), 562, -4500,
                      *_bits(0x3C, 8, 562, 562, 1687), 562],
    }


class TestJVCTakesNoOtherFamily:
    @pytest.mark.parametrize("family", sorted(_families()))
    def test_a_frame_and_a_held_press(self, family):
        frame = _families()[family]
        assert JVCCommand.from_raw_timings(list(frame)) is None
        assert JVCCommand.from_raw_timings([*frame, GAP, *frame, GAP, *frame]) is None

    def test_a_16_bit_frame_on_nec_timing_reads_as_jvc(self):
        """JVC-shaped, so JVC is the right reading: the census allowlist."""
        frame = [9000, -4500, *_bits(0x8020, 16, 560, 560, 1690), 560]
        identity = try_decode_identity(frame)
        assert identity.fingerprint == "JVC:0x0020:0x80"

    def test_known_limit_an_nec_capture_cut_after_sixteen_bits(self):
        """A KNOWN LIMIT, pinned so a change to it is a decision.

        An NEC1 capture that ends exactly after its sixteenth bit, on
        the mark that opens the seventeenth, is a leader, sixteen
        pulse-distance bits and a mark: a JVC frame. Nothing in the
        timings tells the two apart, so it reads as JVC, with NEC's
        address as D and its complement as F.
        """
        cut = _nec_frame(0x04, 0x08)[: 2 + 32 + 1]
        identity = try_decode_identity(cut)
        assert identity.fingerprint == "JVC:0x0004:0xfb"

    def test_the_lirc_rows_the_census_allowlists(self):
        from custom_components.hair.wig_adapters import convert

        result = convert((ADAPTERS / "lirc_four_remotes.lircd.conf").read_text())
        labels = {
            try_decode_identity(ProntoCommand(sig.pronto).get_raw_timings()).protocol
            for wig in result.wigs for sig in wig.signals
        }
        assert labels == {"JVC"}


# ---------------------------------------------------------------------------
# 3. Transmit
# ---------------------------------------------------------------------------


def test_a_decoded_row_rebuilds_to_its_own_identity():
    command = build_protocol_command("JVC", 0xDD, 0xFF)
    assert isinstance(command, JVCCommand)
    rebuilt = try_decode_identity(command.get_raw_timings())
    assert rebuilt.fingerprint == "JVC:0x00dd:0xff"


def test_an_out_of_range_identity_does_not_rebuild():
    assert build_protocol_command("JVC", 0x100, 0x16) is None
    assert build_protocol_command("JVC", 0x03, 0x100) is None


def test_a_rendered_code_reproduces_from_its_triple():
    from custom_components.hair.wig_adapters import _triple_reproduces

    rng = random.Random(38)
    for _ in range(200):
        timings = JVCCommand(
            address=rng.randrange(256), command=rng.randrange(256)
        ).get_raw_timings()
        code = _code(timings)
        assert _triple_reproduces(code, ProntoCommand(code).get_raw_timings())


def test_the_ditto_count_rides_on_the_rebuild():
    from custom_components.hair.ir_command import build_decoded_command

    command = build_decoded_command("JVC", 3, 0x17, repeat_count=2)
    assert command.get_raw_timings() == _press(3, 0x17, repeats=2)


def test_the_ditto_knob_offers_jvc():
    text = (SRC / "ir-tx-knobs.ts").read_text(encoding="utf-8")
    match = re.search(
        r"DITTO_PROTOCOLS: ReadonlySet<string> = new Set\(\[(.*?)\]\)",
        text, re.S,
    )
    assert match, "DITTO_PROTOCOLS moved; this test reads it by shape"
    assert set(re.findall(r'"([A-Z0-9]+)"', match.group(1))) == {
        "NEC", "APPLE", "JVC",
    }


# ---------------------------------------------------------------------------
# 4. The first load after the upgrade
# ---------------------------------------------------------------------------


def _heard(timings: list[int]) -> tuple[str, str | None, str | None]:
    """What a press carries: S/L, byte hash, decoded."""
    code = _code(timings)
    identity = try_decode_identity(ProntoCommand(code).get_raw_timings())
    return (
        canonical_fingerprint("PRONTO", code, None),
        canonical_byte_hash(code),
        identity.fingerprint if identity else None,
    )


class _FakeBacking:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.mark.asyncio
async def test_a_trigger_stored_before_the_decoder_fires_on_its_own_button_only():
    from custom_components.hair.storage import HAIRStore

    power = _jvc_frame(0x03, 0x17)
    code = _code(power)
    backing = _FakeBacking()
    backing._data = {
        "devices": [],
        "triggers": [{
            "id": "t_power",
            "name": "Deck power",
            "signal_fingerprint": canonical_fingerprint("PRONTO", code, None),
            "byte_hash": canonical_byte_hash(code),
            "protocol": "PRONTO",
            "code": code,
        }],
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

    trigger = store.get_trigger("t_power")
    assert trigger.decoded_fingerprint == "JVC:0x0003:0x17"

    def fires(timings):
        return trigger in store.get_triggers_for_signal(None, None, *_heard(timings))

    rng = random.Random(3)
    assert fires(power)
    assert fires(_jitter(power, rng))
    assert fires(_press(0x03, 0x17, repeats=3))
    assert not fires(_jvc_frame(0x03, 0x18))
    assert not fires(_jvc_frame(0x04, 0x17))


def test_a_sniffer_row_gains_its_identity_on_load():
    from custom_components.hair.models import UnknownDevice, UnknownSignal
    from custom_components.hair.signal_store import _transform_loaded

    code = _code(_jvc_frame(0x03, 0x17))
    device = UnknownDevice(label="Deck")
    device.signals = [
        UnknownSignal(
            id="s1", protocol="PRONTO", code=code,
            fingerprint=canonical_fingerprint("PRONTO", code, None),
            byte_hash=canonical_byte_hash(code),
            alias="Power", hit_count=4,
        )
    ]
    devices, _dismissed, dirty = _transform_loaded(
        {"devices": [device.to_dict()], "dismissed": []}
    )
    loaded = next(iter(devices.values()))
    row = loaded.signals[0]
    assert dirty is True
    assert row.decoded_fingerprint == "JVC:0x0003:0x17"
    assert row.decode_covers is True
    assert (row.alias, row.hit_count) == ("Power", 4)
    assert loaded.get_signal(*_heard(_press(0x03, 0x17, repeats=2))) is row
    assert loaded.get_signal(*_heard(_jvc_frame(0x03, 0x18))) is None


def test_a_device_command_gains_its_identity_on_load():
    from custom_components.hair.models import IRCommand, IRDevice
    from custom_components.hair.storage import HAIRStore

    device = IRDevice(name="Deck")
    device.commands.append(
        IRCommand(name="Stop", protocol="PRONTO", code=_code(_jvc_frame(0x03, 0x02)))
    )
    store = HAIRStore.__new__(HAIRStore)
    store._data = {device.id: device}
    assert store._backfill_decoded_fields() is True
    command = device.commands[0]
    assert command.decoded_fingerprint == "JVC:0x0003:0x02"
    assert command.decode_covers is True
    assert store._backfill_decoded_fields() is False
