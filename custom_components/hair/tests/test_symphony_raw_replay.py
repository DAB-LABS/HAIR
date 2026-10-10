"""Symphony transmits what was captured.

Symphony is identity-only for transmit, the same tier GE-AC is on. The
decoder still names the button, and that name still serves matching,
pin bindings and the Mirror; it is never used to rebuild the signal.

The rebuild was not faithful on the air. Every encoded frame ended on
two consecutive spaces, which an emitter that pairs timings as
mark/space turns into a 6.88 ms carrier burst, and it sent one frame
where real remotes send four to ten and some lead with two preamble
frames the rebuild dropped. The captured signal has none of those
problems, so until the encoder is fixed the captured signal is what
goes out.

The real capture used throughout is kno-te's Dreo Power code from the
perfect-fit wig: the one the raw pin (GH #78) was first written for.
"""
from __future__ import annotations

import dataclasses
from itertools import pairwise
from pathlib import Path
from unittest.mock import AsyncMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.decoders.symphony import SymphonyCommand
from custom_components.hair.identity import TIER_DECODED, SignalIdentity
from custom_components.hair.ir_command import (
    ProntoCommand,
    RawTimingsCommand,
    build_decoded_command,
)
from custom_components.hair.models import IRCommand, IRDevice, UnknownSignal
from custom_components.hair.protocol_decode import (
    _REGISTRATIONS,
    _coverage,
    build_protocol_command,
    decode_coverage,
    get_spec,
    try_decode_identity,
)
from custom_components.hair.send_plan import build_like_send_path
from custom_components.hair.wig_format import parse_wig

from .test_capture_dittos import _monitor as _make_monitor
from .test_decode_coverage import junk_state_frame
from .test_multi_emitter_resilience import manager  # noqa: F401  (fixture)

FIXTURES = Path(__file__).parent / "fixtures"


def _dreo(alias: str = "Power") -> str:
    wig = parse_wig(
        (FIXTURES / "wigs"
         / "dreo-fan-dr-haf004s-perfect-fit.wig.json").read_text()
    ).wig
    return next(s.pronto for s in wig.signals if s.alias == alias)


def _alternates(timings: list[int]) -> bool:
    """Mark, space, mark, space: no two neighbours share a sign."""
    return all(
        (a > 0) != (b > 0) for a, b in pairwise(timings)
    )


def _decoded_fields(timings: list[int]) -> dict:
    """The fields a mint door stamps, verdict included.

    The Dreo capture covers, so every send-path row below carries
    ``decode_covers=True`` and passes the send gate's verdict clause:
    what stops the rebuild is the tier, not the verdict.
    """
    identity = try_decode_identity(timings)
    assert identity is not None
    assert identity.protocol == "SYMPHONY12"
    assert identity.covers_capture is True
    return {
        "decoded_protocol": identity.protocol,
        "decoded_address": identity.address,
        "decoded_command": identity.command,
        "decoded_fingerprint": identity.fingerprint,
        "decode_covers": identity.covers_capture,
    }


def _two_good_frames_beside_junk() -> list[int]:
    """Two good Symphony frames beside two state-blob frames: the shape
    the coverage carve-out refuses (test_decode_coverage)."""
    good = SymphonyCommand(
        data=0x555, nbits=12, repeat_count=1).get_raw_timings()
    return [
        *good, -9000, *junk_state_frame(), -9000, *junk_state_frame(),
    ]


class TestTheRegistry:
    def test_the_label_still_resolves(self):
        """Identity-only, not unregistered: the decoder still runs."""
        assert get_spec("SYMPHONY12").key == "symphony"

    def test_build_protocol_command_returns_none(self):
        assert build_protocol_command("SYMPHONY12", 0, 0xD81) is None
        assert build_protocol_command("SYMPHONY8", 0, 0x81) is None

    def test_build_decoded_command_returns_none(self):
        assert build_decoded_command("SYMPHONY12", 0, 0xD81) is None
        assert (
            build_decoded_command("SYMPHONY12", 0, 0xD81, repeat_count=3)
            is None
        )


class TestTheIdentityIsUnchanged:
    """The decoder, its vote and its fingerprint are untouched."""

    def test_the_dreo_power_code_still_names_its_button(self):
        timings = ProntoCommand(_dreo()).get_raw_timings()
        identity = try_decode_identity(timings)
        assert identity is not None
        assert identity.fingerprint == "SYMPHONY12:0x0000:0xd81"


class TestTheCoverageHelper:
    """Symphony is still judged, identity-only or not.

    A verdict gates matching as well as transmit: a non-covering decode
    is not a matching tier (owner ruling 2026-09-29). Replaying the
    capture on the air does not change what a press is heard as, so the
    coverage check judges every tier whose decoder carries a census.
    """

    def test_a_covering_capture_is_judged_true(self):
        timings = ProntoCommand(_dreo()).get_raw_timings()
        identity = try_decode_identity(timings)
        assert identity is not None
        assert identity.covers_capture is True
        assert identity.frames_total == identity.frames_explained == 8
        assert decode_coverage(timings) is True

    def test_two_good_frames_beside_junk_are_judged_false(self):
        blob = _two_good_frames_beside_junk()
        identity = try_decode_identity(blob)
        assert identity is not None
        assert identity.protocol.startswith("SYMPHONY")
        assert identity.frames_explained == 2
        assert identity.frames_total == 4
        assert identity.covers_capture is False

    def test_a_non_covering_decode_is_not_a_matching_tier(self):
        """The trigger a real press minted, and a capture that holds the
        same two frames beside a state blob. They share a decoded
        fingerprint, and the decoded tier must not answer for it."""
        good = SymphonyCommand(data=0x555, nbits=12, repeat_count=3)
        press = try_decode_identity(good.get_raw_timings())
        blob = try_decode_identity(_two_good_frames_beside_junk())
        assert press is not None and blob is not None
        assert press.covers_capture is True
        assert blob.fingerprint == press.fingerprint
        trigger = SignalIdentity(
            press.fingerprint, "bh-press", "fp-press",
            decode_covers=press.covers_capture,
        )
        heard = SignalIdentity(
            blob.fingerprint, "bh-blob", "fp-blob",
            decode_covers=blob.covers_capture,
        )
        assert heard.match_tier(trigger) is None
        # The same capture with a covering verdict would have matched
        # on the decoded tier: the verdict is what keeps it out.
        trusted = dataclasses.replace(heard, decode_covers=None)
        assert trusted.match_tier(trigger) == TIER_DECODED

    def test_the_verdict_never_brings_the_rebuild_back(self):
        for timings in (
            ProntoCommand(_dreo()).get_raw_timings(),
            _two_good_frames_beside_junk(),
        ):
            identity = try_decode_identity(timings)
            assert identity is not None
            assert identity.covers_capture in (True, False)
            assert build_protocol_command(
                identity.protocol, identity.address, identity.command,
            ) is None
            assert build_decoded_command(
                identity.protocol, identity.address, identity.command,
            ) is None


class TestAnIdentityOnlyTierWithoutACensusStaysUnjudged:
    """GE-AC, the other identity-only tier, is served only by the
    upstream library's class, and only HAIR's local decoders record how
    many frames they explained. An instance with no census is rule 2's
    case whatever its tier, so judging identity-only tiers leaves GE-AC
    exactly where it was."""

    def test_geac_has_no_local_decoder(self):
        row = next(r for r in _REGISTRATIONS if r[0] == "geac")
        assert row[3] is None  # no local module: upstream class only
        assert row[4] is False  # identity-only

    def test_an_instance_without_a_census_is_unjudged(self):
        class _UpstreamShape:
            FRAME_GAP_US = 8000  # even a declared gap is not enough

        spec = dataclasses.replace(
            get_spec("SYMPHONY12"), key="no-census",
            command_cls=_UpstreamShape, tx_rebuild=False,
        )
        timings = ProntoCommand(_dreo()).get_raw_timings()
        assert _coverage(spec, _UpstreamShape(), timings) == (0, 0, None)

    @pytest.mark.skipif(
        get_spec("GEAC") is None,
        reason="GE-AC needs an upstream library that ships it",
    )
    def test_the_live_geac_spec_is_unjudged(self):
        spec = get_spec("GEAC")
        assert spec.tx_rebuild is False
        cmd = spec.construct(spec.command_cls, "GEAC", 0x01, 0x02, None)
        if cmd is None:
            pytest.skip("GE-AC class does not construct from a triple")
        timings = list(cmd.get_raw_timings())
        decoded = spec.command_cls.from_raw_timings(timings)
        assert decoded is not None
        assert _coverage(spec, decoded, timings) == (0, 0, None)


class TestTheSendPathReplaysTheCapture:
    def test_build_like_send_path_builds_the_capture(self):
        code = _dreo()
        timings = ProntoCommand(code).get_raw_timings()
        row = IRCommand(
            name="Power", protocol="PRONTO", code=code,
            **_decoded_fields(timings),
        )
        built = build_like_send_path(row)
        assert isinstance(built, ProntoCommand)
        assert built.get_raw_timings() == timings

    @pytest.mark.asyncio
    async def test_a_device_command_sends_its_captured_pronto(
        self, manager  # noqa: F811
    ):
        code = _dreo()
        timings = ProntoCommand(code).get_raw_timings()
        cmd = IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=code,
            **_decoded_fields(timings),
        )
        dev = IRDevice(
            name="Fan", emitter_entity_ids=["infrared.e"], commands=[cmd]
        )
        manager._store.add_device(dev)
        ir_send = AsyncMock()
        with patch.object(_infrared_mod, "async_send_command", ir_send):
            await manager.async_send_command(dev.id, "c1")
        ir_send.assert_called_once()
        sent = ir_send.call_args.args[2]
        inner = sent._inner
        assert isinstance(inner, ProntoCommand)
        assert inner.get_raw_timings() == timings
        # What the emitter is handed alternates mark and space all the
        # way through, terminator included.
        assert _alternates(sent.get_raw_timings())

    @pytest.mark.asyncio
    async def test_a_raw_only_command_sends_its_captured_timings(
        self, manager  # noqa: F811
    ):
        timings = ProntoCommand(_dreo()).get_raw_timings()
        cmd = IRCommand(
            id="c1", name="Power", raw_timings=list(timings),
            **_decoded_fields(timings),
        )
        dev = IRDevice(
            name="Fan", emitter_entity_ids=["infrared.e"], commands=[cmd]
        )
        manager._store.add_device(dev)
        ir_send = AsyncMock()
        with patch.object(_infrared_mod, "async_send_command", ir_send):
            await manager.async_send_command(dev.id, "c1")
        inner = ir_send.call_args.args[2]._inner
        assert isinstance(inner, RawTimingsCommand)
        assert inner.get_raw_timings() == timings

    @pytest.mark.asyncio
    async def test_the_catalog_test_button_sends_the_captured_pronto(
        self, fake_hass
    ):
        code = _dreo()
        timings = ProntoCommand(code).get_raw_timings()
        sig = UnknownSignal(
            id="s1", fingerprint="fp-1", protocol="PRONTO", code=code,
            **_decoded_fields(timings),
        )
        monitor, _ = _make_monitor(fake_hass, sig)
        ir_send = AsyncMock()
        with patch.object(_infrared_mod, "async_send_command", ir_send):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"]
        ir_send.assert_called_once()
        sent = ir_send.call_args.args[2]
        inner = getattr(sent, "_inner", sent)
        assert isinstance(inner, ProntoCommand)
        assert inner.get_raw_timings() == timings
        assert _alternates(sent.get_raw_timings())

