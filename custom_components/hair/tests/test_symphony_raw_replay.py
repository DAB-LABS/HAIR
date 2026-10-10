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

from custom_components.hair.ir_command import (
    ProntoCommand,
    RawTimingsCommand,
    build_decoded_command,
)
from custom_components.hair.models import IRCommand, IRDevice, UnknownSignal
from custom_components.hair.protocol_decode import (
    _coverage,
    build_protocol_command,
    decode_coverage,
    get_spec,
    try_decode_identity,
)
from custom_components.hair.send_plan import build_like_send_path
from custom_components.hair.wig_format import parse_wig

from .test_capture_dittos import _monitor as _make_monitor
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
    identity = try_decode_identity(timings)
    assert identity is not None
    assert identity.protocol == "SYMPHONY12"
    return {
        "decoded_protocol": identity.protocol,
        "decoded_address": identity.address,
        "decoded_command": identity.command,
        "decoded_fingerprint": identity.fingerprint,
    }


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
    """Identity-only tiers are skipped by the coverage check, so a
    Symphony decode reports the same unjudged result GE-AC does."""

    def test_decode_coverage_is_unjudged(self):
        timings = ProntoCommand(_dreo()).get_raw_timings()
        assert decode_coverage(timings) is None

    def test_the_identity_carries_no_census(self):
        identity = try_decode_identity(
            ProntoCommand(_dreo()).get_raw_timings()
        )
        assert identity is not None
        assert identity.frames_total == 0
        assert identity.frames_explained == 0
        assert identity.covers_capture is None

    def test_coverage_returns_the_identity_only_result(self):
        spec = get_spec("SYMPHONY12")
        timings = ProntoCommand(_dreo()).get_raw_timings()
        cmd = spec.command_cls.from_raw_timings(timings)
        assert cmd is not None
        assert _coverage(spec, cmd, timings) == (0, 0, None)
        # The rule that answer comes from is the tier, nothing else: the
        # same spec on the rebuild tier is still judged.
        rebuild = dataclasses.replace(spec, tx_rebuild=True)
        assert _coverage(rebuild, cmd, timings)[2] is True


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

