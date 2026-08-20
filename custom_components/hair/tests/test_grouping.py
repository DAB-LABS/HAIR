"""Sniffer grouping: the Arris/candle collision (0.10.1 fast-follow item 4).

Both fixtures are REAL captures taken off the regression bench on
2026-08-17/18, pulled from a copy of the test box's Sniffer catalog:

* ``arris-power-air.json`` -- Arris Vip 2952 V2 Power, heard over air.
* ``candle-on-air.json`` -- the Amazon Candles "On" button, heard over
  air, from the group the Arris capture was misfiled into.

The group is ``91687033-93af-473a-8052-341c59e919ee``, promoted to the
"Amazon Candles" Remote. The Arris captures landed in it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.hair.const import (
    PRONTO_DEVICE_PREAMBLE_PAIRS,
    PRONTO_NEC_ADDRESS_PAIRS,
)
from custom_components.hair.event_parser import EventParser
from custom_components.hair.protocol_decode import try_decode_identity
from custom_components.hair.signal_monitor import normalize

FIXTURES = Path(__file__).parent / "fixtures" / "grouping"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class _Parsed:
    """The minimal shape ``normalize()`` reads off a capture."""

    def __init__(self, sig: dict) -> None:
        self.protocol = sig["protocol"]
        self.code = sig["code"]
        self.raw_timings = sig["raw_timings"]
        self.frequency = sig.get("frequency") or 38000


def _dev_fp(sig: dict) -> str:
    """The grouping key the Sniffer actually files on.

    Goes through ``normalize()`` rather than reimplementing it, so this
    test tracks the real path and flips the moment the grouping rule
    changes.
    """
    return normalize(_Parsed(sig)).dev_fp


def _branch(sig: dict) -> tuple[str, int, str]:
    """Return (branch, carrier word, preamble actually keyed on)."""
    words = EventParser._parse_pronto_words(sig["code"])
    sl = EventParser._pronto_sl_pattern(sig["code"])
    timings = words[4:]
    if timings and timings[0] >= 0x100:
        n = PRONTO_NEC_ADDRESS_PAIRS * 2
        return "nec-leader", words[1], sl[2 : 2 + n]
    n = PRONTO_DEVICE_PREAMBLE_PAIRS * 2
    return "generic", words[1], sl[:n]


@pytest.fixture
def arris() -> dict:
    return _load("arris-power-air.json")


@pytest.fixture
def candle() -> dict:
    return _load("candle-on-air.json")


def test_report_the_two_keys(arris, candle, capsys):
    """Diagnostic: print everything item 4 asked for. Always passes."""
    for label, sig in (("arris", arris), ("candle", candle)):
        branch, freq, preamble = _branch(sig)
        ident = try_decode_identity(sig["raw_timings"])
        print(f"\n[{label}]")
        print(f"  dev_fp    {_dev_fp(sig)}")
        print(f"  branch    {branch}")
        print(f"  carrier   {freq:04X}")
        print(f"  preamble  {preamble!r}")
        print(f"  decode    "
              f"{f'{ident.protocol}:{ident.address}:{ident.command}' if ident else None}")
    out = capsys.readouterr().out
    print(out)


def test_both_take_the_generic_branch(arris, candle):
    """Neither code has an NEC-style leader mark, so neither keys on an
    address byte. Both fall to the one-pair generic preamble."""
    a_branch, a_freq, a_pre = _branch(arris)
    c_branch, c_freq, c_pre = _branch(candle)
    assert a_branch == "generic"
    assert c_branch == "generic"
    assert a_freq == c_freq == 0x006D
    assert len(a_pre) == len(c_pre) == PRONTO_DEVICE_PREAMBLE_PAIRS * 2


def test_both_decode_to_different_devices(arris, candle):
    """The decoder can tell them apart even though the raw preamble cannot.

    This is the whole basis for decode-first grouping: the information
    needed to separate these two remotes is already computed, just not
    until after the grouping key has been chosen.
    """
    c_ident = try_decode_identity(candle["raw_timings"])
    assert c_ident is not None, "the candle capture should decode"
    assert str(c_ident.protocol).upper().startswith("RC5")

    a_ident = try_decode_identity(arris["raw_timings"])
    if a_ident is not None:
        assert (str(a_ident.protocol), str(a_ident.address)) != (
            str(c_ident.protocol), str(c_ident.address)
        ), "decoded identities must differ, or decode-first cannot help"


def test_arris_and_candle_do_not_share_a_group(arris, candle):
    """The collision item 4 was filed for.

    Before decode-first grouping both captures keyed on
    ``21ea38549b5f3a60`` (carrier 006D, preamble "SS") and the Arris
    codes filed under the Amazon Candles Remote. The candle capture
    decodes, so it now keys on its RC5 address instead; the Arris
    capture does not decode, so it keeps the raw-preamble key. They
    separate.
    """
    assert _dev_fp(arris) != _dev_fp(candle)
