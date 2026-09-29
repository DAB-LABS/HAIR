"""A pinned remote re-sends power only on an exact match (GH #183).

Matching is tolerant on purpose, and showing what was heard can afford
to be. Switching a real air conditioner cannot: on 0.17.0 a Daikin
handset's leader hashed like an Off code that began with it, and a
pinned remote re-sent Off on every press. So a POWER hit crosses to the
pinned device only when the press is the remote's power code by exact
bytes -- the whole capture, or the setting frames of a family verified
for them. Any weaker route still records the hearing and sends nothing,
with one debug line saying why.

Ordinary cells are not gated here (owner ruling on #187); the report
says whether they should be.
"""
from __future__ import annotations

import pytest

from custom_components.hair.event_parser import EventParser
from custom_components.hair.identity import (
    TIER_BYTE_HASH,
    canonical_exact_hash,
    norm_fingerprint,
)
from custom_components.hair.matrix_listener import build_cell_index
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

from .test_a_leader_is_not_off import (
    _OFF_SETTINGS,
    _handset,
    _lattice,
    _split,
)
from .test_matrix_listener import (
    PRONTO_COOL_22,
    PRONTO_COOL_23,
    PRONTO_DEV_OFF,
    PRONTO_OFF,
    _identity,
    _pinned,
)

_LOGGER_NAME = "custom_components.hair.matrix_listener"
_WHY = "byte for byte"


async def _hear(listener, tasks, pronto, *, exact_from=None, **override):
    """The capture path, as signal_monitor drives it.

    ``exact_from`` is the code the exact hash is computed from, which is
    the capture itself unless a test needs the matcher and the bytes to
    disagree. ``override`` replaces identity fields to route a hit
    through a named tier.
    """
    identity = _identity(pronto)
    fields = {
        "signal_fingerprint": identity.fingerprint,
        "byte_hash": identity.byte_hash,
        "decoded_fingerprint": identity.decoded_fingerprint,
        "norm_fp": norm_fingerprint(identity.raw_timings),
        "decode_covers": identity.decode_covers,
    }
    fields.update(override)
    await listener.on_signal_captured(
        fields["signal_fingerprint"], fields["byte_hash"],
        fields["decoded_fingerprint"], None,
        fields["norm_fp"], fields["decode_covers"],
        exact_hash=canonical_exact_hash(exact_from or pronto),
    )
    while tasks:
        batch, tasks[:] = list(tasks), []
        for coro in batch:
            await coro


def _with_remote_matrix(listener, matrix):
    listener._matrix_cache["r1"] = matrix
    listener._index_cache["r1"] = build_cell_index(matrix)


def _why_lines(caplog) -> int:
    return sum(_WHY in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# The exact route still re-sends
# ---------------------------------------------------------------------------


class TestAnExactOffStillReSendsOff:

    @pytest.mark.asyncio
    async def test_the_remotes_own_off_code(self):
        listener, tm, dm, tasks = _pinned()

        await _hear(listener, tasks, PRONTO_OFF)
        await listener.async_send_pinned_cell("dev-1", "off")

        tm.dispatch_cell_retransmit.assert_called_once()
        assert dm.sends == [("dev-1", "Off", PRONTO_DEV_OFF, 1, True)]

    @pytest.mark.asyncio
    async def test_a_daikin_off_from_the_handset_with_a_new_clock(self):
        """Allowlisted: the settings frame is what has to agree. The
        clock frame differs from the one stored, as it always will."""
        matrix, _settings = _lattice()
        listener, tm, _dm, tasks = _pinned()
        _with_remote_matrix(listener, matrix)

        await _hear(listener, tasks, _handset(_OFF_SETTINGS))

        tm.dispatch_cell_retransmit.assert_called_once()
        assert tm.dispatch_cell_retransmit.call_args[0][2] == "off"

    @pytest.mark.asyncio
    async def test_the_settings_frame_alone_from_a_splitting_receiver(self):
        matrix, _settings = _lattice()
        listener, tm, _dm, tasks = _pinned()
        _with_remote_matrix(listener, matrix)

        await _hear(listener, tasks, _split(_handset(_OFF_SETTINGS))[-1])

        tm.dispatch_cell_retransmit.assert_called_once()


# ---------------------------------------------------------------------------
# Every weaker route records the hearing and sends nothing
# ---------------------------------------------------------------------------

# A power code with two different frames and nothing a field map reads,
# so it takes no setting-frame path: the byte hash, as identity, is its
# FIRST frame only. That is the #183 shape on a family #187 does not
# cover, and it is the one weak route that still exists after #187.
_TWO_FRAME_OFF = ("0000 006D 0004 0000 0020 0040 0020 0500"
                  " 0040 0020 0040 0600")
_SAME_FIRST_FRAME = ("0000 006D 0004 0000 0020 0040 0020 0500"
                     " 0060 0020 0060 0600")
# What a receiver that splits at the gap hands over first.
_FIRST_FRAME = "0000 006D 0002 0000 0020 0040 0020 0500"


def _two_frame_matrix() -> ClimateMatrix:
    # The cell must not share the Off code's first frame, or #178's
    # shared-key refusal takes the key away from both and nothing here
    # is heard at the byte-hash tier at all.
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0, modes=["cool"],
        fan_modes=["auto"], swing_modes=[], off=_TWO_FRAME_OFF,
        cells=[ClimateCell(mode="cool", fan="auto", temp=23.0,
                           pronto=PRONTO_COOL_23)],
    )


class TestAWeakOffHitSendsNothing:

    @pytest.mark.parametrize("press", [_SAME_FIRST_FRAME, _FIRST_FRAME])
    def test_the_premise_one_frame_of_several_is_a_byte_hash_hit(self, press):
        """If this stops holding, the tests below prove nothing: both
        presses must reach Off at the BYTE-HASH tier, the one that
        answered #183, with bytes that are not Off's."""
        identity = _identity(press)
        result = build_cell_index(_two_frame_matrix()).match(
            identity.decoded_fingerprint, identity.fingerprint,
            identity.byte_hash, norm_fingerprint(identity.raw_timings),
            identity.decode_covers,
        )
        assert result is not None
        hit, tier = result
        assert (hit.power, tier) == ("off", TIER_BYTE_HASH)
        assert canonical_exact_hash(press) != canonical_exact_hash(
            _TWO_FRAME_OFF)

    @pytest.mark.asyncio
    async def test_a_press_sharing_only_the_first_frame(self, caplog):
        listener, tm, dm, tasks = _pinned()
        _with_remote_matrix(listener, _two_frame_matrix())

        with caplog.at_level("DEBUG", logger=_LOGGER_NAME):
            await _hear(listener, tasks, _SAME_FIRST_FRAME)
        await listener.async_send_pinned_cell("dev-1", "off")

        # Heard, and shown as heard; not sent.
        assert listener._store.get_trigger_remote("r1").last_heard[
            "power"] == "off"
        assert tm.dispatch_cell_retransmit.call_count == 0
        assert dm.sends == []
        assert _why_lines(caplog) == 1

    @pytest.mark.asyncio
    async def test_the_first_frame_alone_from_a_splitting_receiver(
        self, caplog,
    ):
        listener, tm, _dm, tasks = _pinned()
        _with_remote_matrix(listener, _two_frame_matrix())

        with caplog.at_level("DEBUG", logger=_LOGGER_NAME):
            await _hear(listener, tasks, _FIRST_FRAME)

        assert tm.dispatch_cell_retransmit.call_count == 0
        assert _why_lines(caplog) == 1

    @pytest.mark.asyncio
    async def test_the_same_code_whole_is_exact_and_is_sent(self):
        """The other side of the two tests above, on the same lattice."""
        listener, tm, _dm, tasks = _pinned()
        _with_remote_matrix(listener, _two_frame_matrix())

        await _hear(listener, tasks, _TWO_FRAME_OFF)

        tm.dispatch_cell_retransmit.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tier", ["decoded", "normalized"])
    async def test_a_hit_through_a_tolerant_tier(self, tier, caplog):
        """Routed to Off by the tier alone, with bytes that are not
        Off's. The index is told the tier key directly so each tier is
        exercised on its own."""
        listener, tm, dm, tasks = _pinned()
        index = listener._index_cache["r1"]
        off_hit = index.bytehash[_identity(PRONTO_OFF).byte_hash]
        if tier == "decoded":
            index.decoded["NEC:0x1:0x2"] = off_hit
            override = {"decoded_fingerprint": "NEC:0x1:0x2",
                        "decode_covers": True}
        else:
            key = norm_fingerprint(_identity(PRONTO_OFF).raw_timings)
            assert key is not None
            override = {"norm_fp": key, "decoded_fingerprint": None}
        override.update({"byte_hash": None, "signal_fingerprint": None})

        with caplog.at_level("DEBUG", logger=_LOGGER_NAME):
            await _hear(listener, tasks, PRONTO_COOL_22, **override)
        await listener.async_send_pinned_cell("dev-1", "off")

        assert listener._store.get_trigger_remote("r1").last_heard[
            "power"] == "off"
        assert tm.dispatch_cell_retransmit.call_count == 0
        assert dm.sends == []
        assert _why_lines(caplog) == 1

    @pytest.mark.asyncio
    async def test_a_capture_path_that_passes_no_exact_hash(self):
        """Absent is never exact: an older caller cannot re-send power."""
        listener, tm, _dm, tasks = _pinned()
        identity = _identity(PRONTO_OFF)

        await listener.on_signal_captured(
            identity.fingerprint, identity.byte_hash,
            identity.decoded_fingerprint, None,
        )
        while tasks:
            batch, tasks[:] = list(tasks), []
            for coro in batch:
                await coro

        assert tm.dispatch_cell_retransmit.call_count == 0


class TestCellsAreNotGated:
    """Owner ruling on #187: the rule is for power codes only."""

    @pytest.mark.asyncio
    async def test_a_cell_hit_is_dispatched_as_before(self):
        listener, tm, _dm, tasks = _pinned()

        await _hear(listener, tasks, PRONTO_COOL_22, exact_from=PRONTO_OFF)

        tm.dispatch_cell_retransmit.assert_called_once()
        assert tm.dispatch_cell_retransmit.call_args[0][2] == "cool/auto/22"


class TestTheExactHash:

    def test_a_single_frame_code_hashes_as_its_byte_hash(self):
        for code in (PRONTO_OFF, PRONTO_COOL_22):
            assert (EventParser.pronto_exact_hash(code)
                    == EventParser.pronto_byte_hash(code))

    def test_an_allowlisted_code_hashes_its_setting_frames(self):
        press = _handset(_OFF_SETTINGS)
        assert (EventParser.pronto_exact_hash(press)
                == EventParser.pronto_byte_hash(press))

    def test_a_repeated_frame_says_nothing_new(self):
        frame = "0020 0040 0020 0040 0020"
        once = f"0000 006D 0003 0000 {frame} 0500"
        twice = f"0000 006D 0006 0000 {frame} 0500 {frame} 0600"
        assert (EventParser.pronto_exact_hash(twice)
                == EventParser.pronto_exact_hash(once))

    def test_every_frame_counts_otherwise(self):
        assert (EventParser.pronto_exact_hash(_TWO_FRAME_OFF)
                != EventParser.pronto_exact_hash(_SAME_FIRST_FRAME))
        assert (EventParser.pronto_byte_hash(_TWO_FRAME_OFF)
                == EventParser.pronto_byte_hash(_SAME_FIRST_FRAME))

    def test_it_survives_the_air_path(self):
        from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto

        for code in (_TWO_FRAME_OFF, _handset(_OFF_SETTINGS), PRONTO_OFF):
            command = ProntoCommand(code)
            air = raw_to_pronto(command.get_raw_timings(),
                                frequency=command.modulation)
            assert (EventParser.pronto_exact_hash(air)
                    == canonical_exact_hash(code)), code
