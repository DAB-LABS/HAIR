"""The decode-trust pins (GH #134).

A decoder looking for a short addressed frame can find one inside a
long opaque payload by coincidence. v0.4.0 through v0.14.1 trusted
whatever it found and re-encoded from it, which on the reported case
turned an air conditioner state into a meaningless 99-timing frame.
Two adversarial reviews settled that re-encode-and-compare fails honest
captures and passes that false class, and that the discriminator that
works is frame coverage.

Every pin below locks one finding from those reviews. They are written
against the real doors wherever a door exists: the decoder, the
salvage, the two load backfills, the two transmit sites and the mint.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.hair.decoders import split_frames
from custom_components.hair.decoders.kaseikyo import KaseikyoCommand
from custom_components.hair.decoders.nec_recovery import salvage_decode
from custom_components.hair.decoders.rca import RCACommand
from custom_components.hair.decoders.symphony import SymphonyCommand
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.models import (
    CommandSource,
    IRCommand,
    IRDevice,
    UnknownSignal,
)
from custom_components.hair.protocol_decode import (
    decode_coverage,
    try_decode_identity,
)
from custom_components.hair.wig_format import parse_wig

_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None
_NEEDS_LIBRARY = pytest.mark.skipif(
    not _HAS_LIBRARY,
    reason=(
        "the NEC tier registers only with infrared-protocols installed; a "
        "green run without it is not coverage for this pin"
    ),
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Synthetic captures
# ---------------------------------------------------------------------------


def junk_state_frame(pairs: int = 60) -> list[int]:
    """A long opaque payload with no protocol in it.

    120 edges, which is the shape an air conditioner state blob has and
    the shape the false KASEIKYO48 match was found inside.
    """
    out: list[int] = []
    for i in range(pairs):
        out.append(600 if i % 3 else 500)
        out.append(-(1600 if i % 2 else 700))
    return out


def kaseikyo_frame(data: bytes = b"\x20\x80\x00\x00") -> list[int]:
    return KaseikyoCommand(address=0x2002, data=data).get_raw_timings()


def nec_frame(address: int = 0x04, command: int = 0x08) -> list[int]:
    """One clean NEC main frame, built by hand.

    Built here rather than through the library so the salvage pins run
    on the 3.12 leg, where nothing registers the NEC tier.
    """
    out = [9000, -4500]
    for byte in (address, 0x00, command, (~command) & 0xFF):
        for i in range(8):
            out.append(562)
            out.append(-1687 if (byte >> i) & 1 else -562)
    out.append(562)
    return out


# ---------------------------------------------------------------------------
# 1. The reported shape
# ---------------------------------------------------------------------------


class TestAStateBlobDoesNotCoverItsFalseDecode:
    """GH #134 itself: a real frame beside a state blob.

    BOTH GAP WIDTHS MATTER. The identity layer's own fingerprints
    truncate at about 27ms, so a 35ms interior gap is past the point
    where anything upstream of this can be trusted to have seen the
    second frame at all.
    """

    @pytest.mark.parametrize("gap_us", [8000, 35000])
    def test_the_verdict_is_false_at_either_gap(self, gap_us):
        blob = [*kaseikyo_frame(), -gap_us, *junk_state_frame()]
        identity = try_decode_identity(blob)
        assert identity is not None, "the false decode still happens"
        assert identity.protocol.startswith("KASEIKYO")
        assert identity.frames_total == 2
        assert identity.frames_explained == 1
        assert identity.covers_capture is False

    def test_the_frame_on_its_own_still_covers(self):
        """The other half: this must not start refusing honest codes."""
        identity = try_decode_identity(kaseikyo_frame())
        assert identity is not None
        assert identity.covers_capture is True

    def test_the_device_send_replays_the_stored_bytes(self):
        """Through the real gate, not by reading the source."""
        from custom_components.hair import device_manager as dm

        blob = [*kaseikyo_frame(), -8000, *junk_state_frame()]
        identity = try_decode_identity(blob)
        command = IRCommand(
            name="State", protocol="PRONTO", code="0000 006D 0000 0001",
            raw_timings=list(blob),
            decoded_protocol=identity.protocol,
            decoded_address=identity.address,
            decoded_command=identity.command,
            decoded_fingerprint=identity.fingerprint,
            decode_covers=identity.covers_capture,
        )
        # The one clause under test, read the way the send path reads it.
        assert command.decoded_fingerprint
        assert not command.tx_force_raw
        assert command.matrix_cell is None
        assert command.source != CommandSource.MATRIX
        assert command.decode_covers is False
        src = __import__("inspect").getsource(
            dm.DeviceManager.async_send_command
        )
        assert "and command.decode_covers is not False" in src

    def test_the_catalog_test_button_replays_them_too(self):
        from custom_components.hair import signal_monitor as sm

        src = __import__("inspect").getsource(sm.SignalMonitor.test_signal)
        assert "and signal.decode_covers is not False" in src


# ---------------------------------------------------------------------------
# 2 and 3. The two ways a vote can lie
# ---------------------------------------------------------------------------


class TestTheCarveOutIsBounded:
    """A voting decoder discards frames that disagree, and forgiving
    that is right for a preamble, a truncated tail or one jittered
    frame. It is not right for a state blob sitting beside two good
    frames, which is the same false decode wearing a different hat."""

    def test_two_good_symphony_frames_beside_two_junk_ones_do_not_cover(self):
        good = SymphonyCommand(
            data=0x555, nbits=12, repeat_count=1).get_raw_timings()
        blob = [
            *good, -9000, *junk_state_frame(), -9000,
            *junk_state_frame(),
        ]
        identity = try_decode_identity(blob)
        assert identity is not None
        assert identity.protocol.startswith("SYMPHONY")
        assert identity.frames_explained == 2
        assert identity.frames_total == 4
        assert identity.covers_capture is False

    def test_a_vendor_preamble_is_still_forgiven(self):
        """The carve-out's whole reason for existing, from the decoder's
        own test corpus: two preamble frames the vote discards."""
        preamble_a = SymphonyCommand(data=0x000, nbits=12).get_raw_timings()
        preamble_b = SymphonyCommand(data=0xFFF, nbits=12).get_raw_timings()
        button = SymphonyCommand(
            data=0xC00, nbits=12, repeat_count=4).get_raw_timings()
        identity = try_decode_identity(preamble_a + preamble_b + button)
        assert identity is not None
        assert identity.frames_explained < identity.frames_total
        assert identity.covers_capture is True


class TestFramesExplainedIsVotesNotFramesThatDecoded:
    """Two DIFFERENT parity-valid Kaseikyo frames in one capture.

    Both decode. Neither describes the other, and the winner explains
    one frame of two. Counting frames-that-decoded rather than votes
    would call this covered, which is how a blob of two unrelated
    states would walk through.
    """

    def test_the_loser_frame_is_not_explained(self):
        blob = [
            *kaseikyo_frame(b"\x20\x80\x00\x00"),
            -9000,
            *kaseikyo_frame(b"\x30\x81\x00\x00"),
        ]
        identity = try_decode_identity(blob)
        assert identity is not None
        assert identity.frames_total == 2
        assert identity.frames_explained == 1
        assert identity.covers_capture is False


# ---------------------------------------------------------------------------
# 4. The salvage bound
# ---------------------------------------------------------------------------


class TestSalvageWillNotReadAStateFrameAsNEC:
    """salvage_decode read the leader and exactly 32 data pairs and
    never asked whether the frame ended there. A 68-bit state frame
    offers a perfectly good first 32 bits, and one in 256 of them
    satisfies the complement check by chance.

    Direct calls: this runs on 3.12, where no NEC tier is registered.
    """

    def test_a_clean_frame_still_salvages(self):
        assert salvage_decode(nec_frame()) == (0x04, 0x08)

    def test_a_longer_frame_is_refused(self):
        long_frame = nec_frame()[:-1]
        for i in range(36):
            long_frame.append(562)
            long_frame.append(-1687 if i % 2 else -562)
        long_frame.append(562)
        assert salvage_decode(long_frame) is None

    def test_a_frame_that_never_ends_is_refused(self):
        """No trailer at all is not a frame, it is the start of one."""
        assert salvage_decode(nec_frame()[:-1]) is None

    def test_repeat_markers_after_the_frame_are_still_fine(self):
        """The v0.6.1 case is a held button, and a held NEC button
        sends markers. Refusing those would refuse the shape the
        salvage was written for."""
        held = [*nec_frame(), -40000, 9000, -2250, 562]
        assert salvage_decode(held) == (0x04, 0x08)


# ---------------------------------------------------------------------------
# 5 and 6. Truncation, and the corpora that must not move
# ---------------------------------------------------------------------------


class TestATruncatedTailDoesNotCover:
    def test_a_cut_final_frame_reads_uncovered(self):
        full = RCACommand(device=0xF, function=0x2A, repeat_count=1)
        timings = full.get_raw_timings()
        cut = [*timings, -8000, *timings[: len(timings) // 3]]
        identity = try_decode_identity(cut)
        assert identity is not None
        assert identity.protocol == "RCA"
        assert identity.covers_capture is False

    def test_and_the_row_still_transmits_its_stored_bytes(self):
        """Uncovered is not broken. The bytes are still the bytes."""
        full = RCACommand(device=0xF, function=0x2A, repeat_count=1)
        timings = full.get_raw_timings()
        cut = [*timings, -8000, *timings[: len(timings) // 3]]
        command = IRCommand(
            name="Cut", protocol="PRONTO", raw_timings=list(cut),
            decode_covers=decode_coverage(cut),
        )
        assert command.decode_covers is False
        assert command.raw_timings == list(cut)


class TestTheRepeatTrainCorporaStillCover:
    """The regression the bound exists to survive. Both corpora are
    real captures off real receivers, and both are honest."""

    def test_every_rca_forum_capture_covers(self):
        fixture = json.loads(
            (FIXTURES / "rca" / "forum-captures.json").read_text()
        )
        for index, capture in enumerate(fixture["captures"]):
            timings = ProntoCommand(capture["pronto"]).get_raw_timings()
            identity = try_decode_identity(timings)
            assert identity is not None, index
            assert identity.covers_capture is True, index

    def test_every_dreo_signal_that_decodes_covers(self):
        wig = parse_wig(
            (FIXTURES / "wigs"
             / "dreo-fan-dr-haf004s-perfect-fit.wig.json").read_text()
        ).wig
        seen = 0
        for signal in wig.signals:
            timings = ProntoCommand(signal.pronto).get_raw_timings()
            identity = try_decode_identity(timings)
            if identity is None:
                continue
            seen += 1
            assert identity.covers_capture is True, signal.alias
        assert seen >= 5

    def test_the_boundary_row_is_the_one_that_would_break_first(self):
        """Speed Down: repeat-voted, two frames of four decoded, and the
        two the vote discarded are the same frame jittered into extra
        edges. It is the row a tighter bound would refuse first, so it
        is pinned by name rather than left to the sweep above."""
        wig = parse_wig(
            (FIXTURES / "wigs"
             / "dreo-fan-dr-haf004s-perfect-fit.wig.json").read_text()
        ).wig
        code = next(
            s.pronto for s in wig.signals if s.alias == "Speed Down"
        )
        timings = ProntoCommand(code).get_raw_timings()
        identity = try_decode_identity(timings)
        assert identity is not None
        assert identity.frames_explained == 2
        assert identity.frames_total == 4
        assert identity.covers_capture is True
        # And the reason it is the boundary: the discarded frames carry
        # MORE marks than the winners, so an edge-count bound alone
        # would have refused them.
        frames = split_frames(timings, SymphonyCommand.FRAME_GAP_US)
        marks = sorted(sum(1 for v in f if v > 0) for f in frames)
        assert marks[0] != marks[-1]


# ---------------------------------------------------------------------------
# 7. The salvage regression
# ---------------------------------------------------------------------------


class TestASalvagedDecodeStillCovers:
    """The v0.6.1 shape: one data space jittered into the dead zone
    between the two legal NEC spaces, every other pulse in bounds, and
    the frame's own checksum holding. The strict decoder refuses it and
    the salvage reads it, and what it read is the whole capture."""

    @_NEEDS_LIBRARY
    def test_a_jittered_frame_salvages_and_covers(self):
        jittered = nec_frame()
        jittered[7] = -815
        identity = try_decode_identity(jittered)
        assert identity is not None
        assert identity.protocol == "NEC"
        assert identity.frames_total == 1
        assert identity.frames_explained == 1
        assert identity.covers_capture is True

    @_NEEDS_LIBRARY
    def test_its_repeat_markers_are_explained_too(self):
        jittered = nec_frame()
        jittered[7] = -815
        held = [*jittered, -40000, 9000, -2250, 562]
        identity = try_decode_identity(held)
        assert identity is not None
        assert identity.frames_total == 2
        assert identity.frames_explained == 2
        assert identity.covers_capture is True

    @_NEEDS_LIBRARY
    def test_the_strict_path_stays_unjudged(self):
        """Tier default: this repo cannot see the upstream decoder's
        vote count, so it says so rather than guessing. Unknown is
        trusted and is never persisted."""
        identity = try_decode_identity(nec_frame())
        assert identity is not None
        assert identity.protocol == "NEC"
        assert identity.covers_capture is None


# ---------------------------------------------------------------------------
# 8. The backfill
# ---------------------------------------------------------------------------


class TestALegacyStoreIsJudgedOnceAndNotAgain:
    """The rows already sitting in stores with false decodes are the
    reason the verdict is persisted at all."""

    def _false_command(self) -> IRCommand:
        blob = [*kaseikyo_frame(), -8000, *junk_state_frame()]
        identity = try_decode_identity(blob)
        assert identity is not None and identity.covers_capture is False
        return IRCommand(
            name="Legacy state", protocol="PRONTO",
            raw_timings=list(blob),
            decoded_protocol=identity.protocol,
            decoded_address=identity.address,
            decoded_command=identity.command,
            decoded_fingerprint=identity.fingerprint,
        )

    def test_one_load_judges_it_and_the_second_finds_nothing(self):
        from custom_components.hair.storage import HAIRStore

        device = IRDevice(name="Legacy")
        command = self._false_command()
        assert command.decode_covers is None, "the fixture starts unjudged"
        device.commands.append(command)

        store = HAIRStore.__new__(HAIRStore)
        store._data = {device.id: device}
        assert store._backfill_decoded_fields() is True
        assert command.decode_covers is False
        # Idempotent: a second load computes nothing, which is what
        # keeps this off the startup path forever.
        assert store._backfill_decoded_fields() is False

    def test_an_unjudgeable_row_is_left_alone(self):
        """Never persist could-not-derive. A row nothing can read stays
        absent, and absent is trusted."""
        from custom_components.hair.storage import HAIRStore

        device = IRDevice(name="Opaque")
        device.commands.append(IRCommand(
            name="Noise", protocol="PRONTO",
            raw_timings=junk_state_frame(),
            decoded_fingerprint="MADEUP:0x01:0x02",
        ))
        store = HAIRStore.__new__(HAIRStore)
        store._data = {device.id: device}
        store._backfill_decoded_fields()
        assert device.commands[0].decode_covers is None


# ---------------------------------------------------------------------------
# 9. Carriage
# ---------------------------------------------------------------------------


class TestTheVerdictRidesTheCarriageDataclasses:
    """Without these two the wig-adopt door and the Mirror rows stay
    open: both read their decoded fields off a carriage object rather
    than off the decoder."""

    def test_it_rides_normalized_signal(self):
        from custom_components.hair.models import CaptureResult
        from custom_components.hair.signal_monitor import normalize

        blob = [*kaseikyo_frame(), -8000, *junk_state_frame()]
        n = normalize(CaptureResult(
            protocol="PRONTO", code=None, raw_timings=list(blob),
            frequency=38000,
        ))
        assert n.decoded_fingerprint
        assert n.decode_covers is False

    def test_it_rides_wig_signal_identity(self):
        from custom_components.hair.wig_identity import WigSignalIdentity

        assert hasattr(WigSignalIdentity, "__dataclass_fields__")
        assert "decode_covers" in set(
            WigSignalIdentity.__dataclass_fields__
        )

    def test_the_adopt_door_carries_it_onto_the_command(self):
        from custom_components.hair.websocket_api import (
            _command_from_wig_signal,
        )

        ident = SimpleNamespace(
            pronto="0000 006D 0000 0001", raw_timings=[9000, -4500, 562],
            frequency=38000, fingerprint="SL:xx", byte_hash="abcd",
            decoded_protocol="KASEIKYO48", decoded_address=0x2002,
            decoded_command=0x20800000,
            decoded_fingerprint="KASEIKYO48:0x2002:0x20800000",
            decoded_extras=None, decode_covers=False,
        )
        sig = SimpleNamespace(
            alias="State", send_count=1, ditto_count=0,
            bypass_protocol=False,
        )
        command = _command_from_wig_signal(sig, ident, set(), {}, 1)
        assert command.decode_covers is False
        assert command.decoded_fingerprint == ident.decoded_fingerprint

    def test_a_signal_assign_copies_it_rather_than_re_deriving(self):
        from custom_components.hair.signal_monitor import (
            _apply_signal_provenance,
        )

        signal = UnknownSignal(
            fingerprint="SL:xx", code="0000 006D 0000 0001",
            decoded_fingerprint="KASEIKYO48:0x2002:0x1",
            decode_covers=False,
        )
        command = IRCommand(name="Assigned")
        _apply_signal_provenance(command, signal)
        assert command.decode_covers is False


# ---------------------------------------------------------------------------
# 10. The clone roster
# ---------------------------------------------------------------------------


class TestTheCloneRosterIsPinned:
    """A copy that drops a field is data loss nobody sees. The roster
    is derived from the record rather than hand-listed, and this holds
    the derivation."""

    def test_the_roster_is_every_field_but_the_two_a_copy_must_not_reuse(self):
        from custom_components.hair.models import (
            _CLONE_SKIPS,
            _KNOWN_COMMAND,
        )

        assert set(_CLONE_SKIPS) == {"id", "created_at"}
        roster = _KNOWN_COMMAND - _CLONE_SKIPS
        assert "decode_covers" in roster
        # The four the hand-written copy had already drifted past.
        for field in (
            "plucked_command_name", "matrix_cell", "comb_suspect",
            "comb_finding",
        ):
            assert field in roster

    def test_a_clone_carries_the_whole_roster_including_extra(self):
        from custom_components.hair.models import _CLONE_SKIPS, _KNOWN_COMMAND

        source = IRDevice(name="Source")
        command = IRCommand(
            name="Row", protocol="PRONTO", code="0000 006D 0000 0001",
            raw_timings=[9000, -4500], frequency=38000, repeat_count=2,
            send_count=3, byte_hash="abcd", decoded_protocol="NEC",
            decoded_address=1, decoded_command=2,
            decoded_fingerprint="NEC:0x0001:0x02",
            decoded_extras={"toggle": 1}, decode_covers=False,
            tx_force_raw=True, plucked_command_name="Vendor Power",
            matrix_cell={"mode": "cool", "fan": "high",
                         "swing": "off", "temp": 22.0},
            sent_state={"power": "on"}, comb_suspect=True,
            comb_finding="frame-shape",
        )
        command._extra = {"a_field_this_build_never_heard_of": 7}
        source.commands.append(command)

        clone = source.clone("Copy")
        copied = clone.commands[0]
        assert copied.id != command.id
        for field in _KNOWN_COMMAND - _CLONE_SKIPS:
            assert getattr(copied, field) == getattr(command, field), field
        assert copied._extra == {"a_field_this_build_never_heard_of": 7}

    def test_a_failed_matrix_copy_drops_the_porthole(self):
        """A porthole row points AT a lattice cell. Without the lattice
        it is a window onto nothing, and deleting one deletes a cell
        that is not there."""
        source = IRDevice(name="Source")
        source.commands.append(IRCommand(
            name="cool / high / 22",
            matrix_cell={"mode": "cool", "fan": "high",
                         "swing": "off", "temp": 22.0},
            sent_state={"power": "on"},
        ))
        kept = source.clone("Kept")
        assert kept.commands[0].matrix_cell is not None
        dropped = source.clone("Dropped", keep_matrix_cell=False)
        assert dropped.commands[0].matrix_cell is None
        # Only the porthole. The state stamp is a different fact and
        # stays.
        assert dropped.commands[0].sent_state == {"power": "on"}


# ---------------------------------------------------------------------------
# 11. The per-decoder census
# ---------------------------------------------------------------------------


class TestEveryLocalDecoderCountsItsOwnFrames:
    """The census is what the verdict is built on, so a decoder that
    reports it wrongly corrupts every verdict on that protocol.

    IT IS NOT ALWAYS repeat_count + 1, which is why it is stated rather
    than inferred: Sharp counts two frames per press, and Dyson and
    Nokia32 discard the vote count entirely.
    """

    def _built(self, command, repeats):
        cls = type(command)
        rebuilt = cls.from_raw_timings(command.get_raw_timings())
        assert rebuilt is not None
        return rebuilt

    @pytest.mark.parametrize("repeats", [0, 1, 3])
    def test_symphony_counts_its_votes(self, repeats):
        source = SymphonyCommand(
            data=0xC00, nbits=12, repeat_count=repeats + 1)
        rebuilt = self._built(source, repeats)
        assert rebuilt.frames_explained == repeats + 2
        assert rebuilt.frames_explained == rebuilt.repeat_count + 1

    @pytest.mark.parametrize("repeats", [0, 1, 3])
    def test_rca_counts_its_votes(self, repeats):
        source = RCACommand(device=0xF, function=0x2A, repeat_count=repeats)
        rebuilt = self._built(source, repeats)
        assert rebuilt.frames_explained == repeats + 1
        assert rebuilt.frames_explained == rebuilt.repeat_count + 1

    @pytest.mark.parametrize("repeats", [0, 1, 3])
    def test_kaseikyo_counts_votes_plus_its_repeat_markers(self, repeats):
        source = KaseikyoCommand(
            address=0x2002, data=b"\x20\x80\x00\x00", repeat_count=repeats)
        rebuilt = self._built(source, repeats)
        assert rebuilt.frames_explained == repeats + 1

    def test_sharp_counts_frames_and_not_presses(self):
        """Two frames per press. Reading repeat_count + 1 here would
        report one frame for a capture that explained two, and every
        Sharp verdict would come out false."""
        from custom_components.hair.decoders.sharp import SharpCommand

        source = SharpCommand(address=0x01, command=0x02)
        rebuilt = self._built(source, 0)
        assert rebuilt.frames_explained == 2
        assert rebuilt.repeat_count + 1 == 1

    def test_dyson_and_nokia32_report_a_census_they_do_not_store(self):
        """Both discard the vote count for repeat_count on purpose. The
        census is the thing that survives that."""
        from custom_components.hair.decoders.dyson import DysonCommand
        from custom_components.hair.decoders.nokia32 import Nokia32Command

        dyson = DysonCommand(device=1, function=2, counter=0)
        rebuilt = self._built(dyson, 0)
        assert rebuilt.frames_explained >= 1

        nokia = Nokia32Command(
            device=1, subdevice=2, function=3, extension=0, toggle=0)
        rebuilt = self._built(nokia, 0)
        assert rebuilt.frames_explained >= 1

    def test_every_local_decoder_declares_its_frame_gap(self):
        """The other seam. A decoder without it cannot be judged, and
        silently not being judged is how this bug lasted four minor
        versions."""
        from custom_components.hair.decoders import (
            dyson,
            kaseikyo,
            marantz_extended,
            nokia32,
            rc5,
            rc6,
            rca,
            samsung,
            sharp,
            sony,
            symphony,
        )

        pairs = [
            (dyson.DysonCommand, dyson._FRAME_GAP_US),
            (kaseikyo.KaseikyoCommand, kaseikyo._FRAME_GAP_US),
            (marantz_extended.MarantzExtendedCommand,
             marantz_extended._FRAME_GAP_US),
            (nokia32.Nokia32Command, nokia32._FRAME_GAP_US),
            (rc5.RC5Command, rc5._FRAME_GAP_US),
            (rc6.RC6Command, rc6._FRAME_GAP_US),
            (rca.RCACommand, rca._FRAME_GAP_US),
            (samsung.Samsung32Command, samsung._FRAME_GAP_US),
            (sharp.SharpCommand, sharp._FRAME_GAP_US),
            (sony.SonyCommand, sony._FRAME_GAP_US),
            (symphony.SymphonyCommand, symphony._FRAME_GAP_US),
        ]
        # Compared as maps rather than one at a time so a decoder that
        # declares the wrong constant names itself in the diff.
        exposed = {cls.__name__: cls.FRAME_GAP_US for cls, _ in pairs}
        declared = {cls.__name__: gap for cls, gap in pairs}
        assert exposed == declared
        # And RCA's is NOT the generic 8000 the others mostly use: its
        # header space is 4000us and a generic split shreds the frame.
        assert rca.RCACommand.FRAME_GAP_US == 6000


# ---------------------------------------------------------------------------
# The mint door's repair rule
# ---------------------------------------------------------------------------


class TestTheMirrorDoorRepairsWhatItCopies:
    """It used to copy a trigger's decoded_fingerprint and fill in none
    of the triple beside it, leaving a row claiming an identity nothing
    derived."""

    def test_all_five_are_derived_from_the_code(self):
        """A real code off a real wig, so the derivation is the one the
        send path would do rather than a shape built for the test."""
        from custom_components.hair.mint import mint_from_code

        wig = parse_wig(
            (FIXTURES / "wigs"
             / "dreo-fan-dr-haf004s-perfect-fit.wig.json").read_text()
        ).wig
        code = next(s.pronto for s in wig.signals if s.alias == "Power")
        command = mint_from_code(
            name="Trigger 1", code=code, protocol="PRONTO",
            byte_hash="from-the-trigger",
        )
        assert command.byte_hash == "from-the-trigger"
        # ALL FIVE OR NONE. The old door filled in the fingerprint
        # alone.
        assert command.decoded_fingerprint
        assert command.decoded_protocol
        assert command.decoded_address is not None
        assert command.decoded_command is not None
        assert command.decode_covers is True

    def test_a_fingerprint_it_can_reproduce_is_kept(self):
        from custom_components.hair.mint import mint_from_code

        wig = parse_wig(
            (FIXTURES / "wigs"
             / "dreo-fan-dr-haf004s-perfect-fit.wig.json").read_text()
        ).wig
        code = next(s.pronto for s in wig.signals if s.alias == "Power")
        derived = try_decode_identity(
            ProntoCommand(code).get_raw_timings())
        assert derived is not None
        command = mint_from_code(
            name="Trigger 1", code=code, protocol="PRONTO",
            claimed_fingerprint=derived.fingerprint,
        )
        assert command.decoded_fingerprint == derived.fingerprint

    def test_a_fingerprint_we_cannot_reproduce_is_discarded(self):
        from custom_components.hair.mint import mint_from_code

        command = mint_from_code(
            name="Trigger 1", code="0000 006D 0000 0001", protocol="PRONTO",
            byte_hash="from-the-trigger",
            claimed_fingerprint="NEC:0xdead:0xbe",
        )
        assert command.decoded_fingerprint is None
        assert command.decoded_protocol is None
        assert command.decoded_address is None
        assert command.decoded_command is None
        assert command.decode_covers is None
        # The hash is the one thing here that is not derivable, so it
        # is the one thing still copied.
        assert command.byte_hash == "from-the-trigger"

    def test_a_decode_free_mint_is_legal(self):
        from custom_components.hair.mint import mint_command

        command = mint_command(name="No code", code=None)
        assert command.decoded_fingerprint is None
        assert command.decode_covers is None
        assert command.send_count == 1


class TestTheRetiredCellMintIsExempt:
    def test_it_says_why_it_was_not_absorbed(self):
        import inspect

        from custom_components.hair import websocket_api

        doc = inspect.getdoc(websocket_api._mint_cell_rows) or ""
        assert "NOT ABSORBED INTO mint_command" in doc
