"""GH #108: a code with no burst in it is no identity, not a crash.

lluisd imported a SmartIR file for a Cecotec ForceClima 12650 on a
UFO-R11. The file declares ``commandsEncoding: "Raw"``, which in SmartIR
means a decimal timing list, but the values are Tuya base64. HAIR's raw
branch scraped the digits out of that base64 and called them
microseconds, which rounded to a Pronto whose every burst pair is zero:
a code that parses, transmits nothing, and matches nothing.

Then ``canonical_edges`` met it. Stripping the trailing zeros left an
empty list, zero is even, and the "drop the trailing space" pop raised
IndexError from inside the identity layer. That took out
``_rebuild_command_index`` (so Make Device never saved, which is why his
repair rows vanished on restart) and ``_assignment_index`` (so the
Sniffer and every other tab answered "unknown error").

Three rules are pinned here:

1. Degenerate input is answered, not raised on.
2. One unreadable command costs itself, never the whole catalog walk.
3. An unconvertible cell is skipped with a receipt, never invented.

The fixture is his file's real cells, verbatim.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_edges,
    canonical_fingerprint,
    canonical_pronto,
    degenerate_pronto,
    norm_fingerprint,
    norm_fingerprint_of_code,
)
from custom_components.hair.models import IRCommand, IRDevice

FIXTURES = Path(__file__).parent / "fixtures" / "gh108"

# What his file's cells became on the way in, before the receipt rule
# below stopped them. Kept as literals because these exact strings are
# what reached canonical_edges in the field.
DEGENERATE_PRONTO = (
    "0000 006D 0002 0000 0000 0000 0000 0000",
    "0000 006D 0003 0000 0000 0000 0000 0000 0000 0000",
    "0000 006D 0004 0000 0000 0000 0000 0000 0000 0000 0000 0000",
    "0000 006D 000E 0000" + " 0000" * 28,
)
HEALTHY_PRONTO = (
    "0000 006D 0022 0000 0156 00AB 0015 0040 0015 0015 0015 0040 "
    "0015 0015 0015 0040 0015 0015 0015 0040 0015 0015 0015 0040 "
    "0015 0015 0015 0040 0015 0015 0015 0040 0015 0015 0015 0040 "
    "0015 0689"
)


@pytest.fixture
def cells() -> dict:
    return json.loads((FIXTURES / "gh108_cells.json").read_text())["cells"]


# ------------------------------------------------------ 1. no more crash


class TestDegenerateInputIsAnswered:
    @pytest.mark.parametrize(
        "timings",
        [
            [],
            [0],
            [0, 0],
            [0, 0, 0, 0],
            [0] * 14,
        ],
    )
    def test_canonical_edges_returns_empty_instead_of_raising(self, timings):
        """The exact line from the traceback: identity.py canonical_edges."""
        assert canonical_edges(list(timings)) == []
        assert canonical_edges(list(timings), signed=True) == []

    def test_canonical_edges_still_strips_a_real_trailing_space(self):
        """The strip this function exists for is untouched."""
        assert canonical_edges([560, -560, 560, -9000]) == [560, 560, 560]

    @pytest.mark.parametrize("code", DEGENERATE_PRONTO)
    def test_every_identity_helper_answers_none_for_a_burstless_code(
        self, code
    ):
        assert degenerate_pronto(code) is True
        assert norm_fingerprint_of_code(code) is None
        assert canonical_pronto(code) is None
        assert canonical_byte_hash(code) is None
        # Empty, not a hash of the text: an all-zero code that hashed
        # would collide with every other all-zero code and match nothing
        # on the air.
        assert canonical_fingerprint("PRONTO", code, None) == ""

    def test_norm_fingerprint_answers_none_for_all_zero_timings(self):
        assert norm_fingerprint([0, 0, 0, 0]) is None

    def test_a_healthy_code_still_has_an_identity(self):
        assert degenerate_pronto(HEALTHY_PRONTO) is False
        assert canonical_fingerprint("PRONTO", HEALTHY_PRONTO, None)
        assert canonical_byte_hash(HEALTHY_PRONTO)

    def test_the_real_cells_now_read_instead_of_crashing(self, cells):
        """His actual payloads, through the door they came in by.

        They are Tuya containers, and HAIR reads them now
        (test_tuya_ir.py). What this file still owns is the promise that
        whatever comes back is answered rather than raised on.
        """
        from custom_components.hair.wig_adapters import (
            _smartir_code_to_pronto,
        )

        for label, value in cells.items():
            pronto, reason = _smartir_code_to_pronto(value, "raw")
            assert reason is None, f"{label}: {reason}"
            assert pronto, f"{label} produced no code"
            assert degenerate_pronto(pronto) is False, label


# --------------------------------------------- 2. one row, not the walk


def _store():
    from custom_components.hair.storage import HAIRStore

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    store = HAIRStore(hass)
    store._data = {}
    store._triggers = {}
    store._trigger_remotes = {}
    return store


def _device_with_a_poisoned_command() -> IRDevice:
    device = IRDevice(id="dev-1", name="Cecotec ForceClima 12650")
    device.commands = [
        IRCommand(
            id="c-good", name="Power", protocol="PRONTO", code=HEALTHY_PRONTO
        ),
        IRCommand(
            id="c-bad", name="cool low 16", protocol="PRONTO",
            code=DEGENERATE_PRONTO[0],
        ),
        IRCommand(
            id="c-good-2", name="Mode", protocol="PRONTO",
            code=HEALTHY_PRONTO,
        ),
    ]
    return device


class TestOneBadCommandDoesNotStopTheWalk:
    def test_the_command_index_builds_around_a_raising_command(
        self, monkeypatch, caplog
    ):
        """Fix 1 means nothing raises today. Fix 2 is what holds if
        something ever does again, so the failure is injected."""
        import custom_components.hair.identity as identity_module

        real = identity_module.canonical_fingerprint

        def explode(protocol, code, raw_timings):
            if code == DEGENERATE_PRONTO[0]:
                raise IndexError("pop from empty list")
            return real(protocol, code, raw_timings)

        monkeypatch.setattr(identity_module, "canonical_fingerprint", explode)

        store = _store()
        device = _device_with_a_poisoned_command()
        store._data = {device.id: device}

        with caplog.at_level("WARNING"):
            store._rebuild_command_index()

        # The healthy commands are indexed and matchable.
        fp = real("PRONTO", HEALTHY_PRONTO, None)
        assert store._idx_fp_bytehash.get((fp, None)) is not None
        # One warning, naming the device and the command.
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
        assert "cool low 16" in warnings[0].message
        assert "c-bad" in warnings[0].message
        assert "Cecotec ForceClima 12650" in warnings[0].message

    def test_the_assignment_index_builds_around_a_raising_command(
        self, monkeypatch, caplog
    ):
        import custom_components.hair.websocket_api as ws

        real = ws.canonical_fingerprint

        def explode(protocol, code, raw_timings):
            if code == DEGENERATE_PRONTO[0]:
                raise IndexError("pop from empty list")
            return real(protocol, code, raw_timings)

        monkeypatch.setattr(ws, "canonical_fingerprint", explode)
        device = _device_with_a_poisoned_command()

        with caplog.at_level("WARNING"):
            index = ws._assignment_index([device])

        # Both healthy commands are in; the poisoned one is not; the
        # handler returned instead of raising, which is the whole point.
        assert index is not None
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
        assert "c-bad" in warnings[0].message

    def test_the_pin_map_builds_around_a_raising_command(
        self, monkeypatch, caplog
    ):
        import custom_components.hair.identity as identity_module
        from custom_components.hair.pin_bindings import build_device_index

        real = identity_module.canonical_fingerprint

        def explode(protocol, code, raw_timings):
            if code == DEGENERATE_PRONTO[0]:
                raise IndexError("pop from empty list")
            return real(protocol, code, raw_timings)

        monkeypatch.setattr(identity_module, "canonical_fingerprint", explode)
        device = _device_with_a_poisoned_command()

        with caplog.at_level("WARNING"):
            index = build_device_index(device)

        assert index is not None
        assert any(r.levelname == "WARNING" for r in caplog.records)

    def test_the_load_time_backfills_survive_a_poisoned_command(self):
        """The real store path: no raise, and the healthy rows still get
        their canonical identity."""
        store = _store()
        device = _device_with_a_poisoned_command()
        store._data = {device.id: device}

        store._backfill_byte_hash()
        store._backfill_canonical_identity()
        store._rebuild_command_index()

        good = next(c for c in device.commands if c.id == "c-good")
        assert good.byte_hash
        bad = next(c for c in device.commands if c.id == "c-bad")
        assert bad.byte_hash is None


# ------------------------------------------- 3. skipped, never invented


class TestUnconvertibleCellsAreSkippedWithReceipts:
    def test_base64_that_no_reader_understands_is_refused(self):
        """The GH #108 rule, on input no reader claims.

        His own cells are Tuya and read now; this is base64 of bytes
        that are neither a Broadlink packet nor a Tuya container, which
        is what "encoded as something HAIR cannot read" looks like.
        """
        import base64

        from custom_components.hair.wig_adapters import (
            _smartir_code_to_pronto,
        )

        junk = base64.b64encode(bytes(range(0x40, 0x60))).decode()
        pronto, reason = _smartir_code_to_pronto(junk, "raw")
        assert pronto is None
        assert "not a decimal timing list" in reason

    def test_a_genuine_raw_timing_list_still_converts(self):
        from custom_components.hair.wig_adapters import (
            _smartir_code_to_pronto,
        )

        pronto, reason = _smartir_code_to_pronto(
            "9000, 4500, 560, 560, 560, 1690, 560, 560", "raw"
        )
        assert reason is None
        assert pronto and pronto.startswith("0000 ")

    def test_an_all_zero_timing_list_is_refused(self):
        from custom_components.hair.wig_adapters import (
            _smartir_code_to_pronto,
        )

        pronto, reason = _smartir_code_to_pronto("0, 0, 0, 0", "raw")
        assert pronto is None
        assert reason == "no usable timings"

    def test_his_whole_file_produces_no_invented_codes(self):
        """End to end on the real file: nothing carries an empty burst.

        The file imports now (test_tuya_ir.py owns the counts). What
        this asserts is the invariant that survived the feature: every
        code that reaches a device has something in it.
        """
        from custom_components.hair import wig_adapters

        text = (FIXTURES / "cecotec-forceclima-12650.json").read_text()
        assert wig_adapters.sniff_format(text) == "smartir_climate"
        result = wig_adapters.convert(text, "cecotec.json")
        for wig in result.wigs:
            for cell in (wig.climate.cells if wig.climate else []):
                assert degenerate_pronto(cell.pronto) is False
            for signal in wig.signals or []:
                assert degenerate_pronto(signal.pronto) is False
