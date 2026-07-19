"""Tests for the hair-wig/1 format: parse, validate, serialize, hash.

The round-trip and canonicalization tests here are the format's real
contract: fittings (v0.7.x) will bind content hashes to the canonical
signals form, so its stability is load-bearing before any fitting
exists.
"""
from __future__ import annotations

import json

import pytest

from custom_components.hair.const import MAX_SEND_COUNT
from custom_components.hair.wig_format import (
    MAX_WIG_BYTES,
    WIG_FORMAT_V1,
    Wig,
    WigSignal,
    canonical_signals_json,
    parse_wig,
    serialize_wig,
    signals_content_hash,
    wig_filename,
)

# A real learned-code Pronto shape the validator accepts.
PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_LOWER = "0000 006d 0002 0000 0020 0040 0020 0040"


def _wig_dict(**overrides) -> dict:
    base = {
        "format": WIG_FORMAT_V1,
        "name": "Foxtel IQ",
        "brand": "Foxtel",
        "signals": [{"alias": "Power", "pronto": PRONTO}],
    }
    base.update(overrides)
    return base


def _parse(data: dict):
    return parse_wig(json.dumps(data))


class TestParseHappyPath:
    def test_minimal_wig(self):
        result = _parse({
            "format": WIG_FORMAT_V1,
            "name": "TV",
            "signals": [{"alias": "Power", "pronto": PRONTO}],
        })
        assert result.ok, result.errors
        assert result.wig.name == "TV"
        assert result.wig.brand is None
        assert result.wig.signals[0].alias == "Power"
        assert result.wig.signals[0].send_count == 1

    def test_full_wig(self):
        result = _parse(_wig_dict(
            model="IQ3",
            notes="bench",
            origin="captured",
            signals=[{"alias": "Power", "pronto": PRONTO, "send_count": 3}],
        ))
        assert result.ok
        assert result.wig.model == "IQ3"
        assert result.wig.origin == "captured"
        assert result.wig.signals[0].send_count == 3

    def test_send_count_clamped(self):
        result = _parse(_wig_dict(
            signals=[{"alias": "A", "pronto": PRONTO, "send_count": 99}]
        ))
        assert result.ok
        assert result.wig.signals[0].send_count == MAX_SEND_COUNT

    def test_unknown_keys_tolerated_and_preserved(self):
        result = _parse(_wig_dict(
            fittings=[{"handle": "someone"}],
            signals=[{"alias": "A", "pronto": PRONTO, "future_key": 7}],
        ))
        assert result.ok
        assert result.wig.extra["fittings"] == [{"handle": "someone"}]
        assert result.wig.signals[0].extra["future_key"] == 7


class TestParseRejections:
    def test_not_json(self):
        result = parse_wig("{not json")
        assert not result.ok
        assert "line 1" in result.errors[0]

    def test_not_an_object(self):
        assert not parse_wig("[1, 2]").ok

    def test_missing_format(self):
        result = _parse({"name": "X", "signals": []})
        assert not result.ok
        assert "format" in result.errors[0]

    def test_wrong_format_string(self):
        result = _parse(_wig_dict(format="smartir/1"))
        assert not result.ok

    def test_future_major_version_polite_refusal(self):
        result = _parse(_wig_dict(format="hair-wig/2"))
        assert not result.ok
        assert len(result.errors) == 1
        assert "update HAIR" in result.errors[0]

    def test_missing_name(self):
        result = _parse({
            "format": WIG_FORMAT_V1,
            "signals": [{"alias": "A", "pronto": PRONTO}],
        })
        assert not result.ok
        assert any("name" in e for e in result.errors)

    def test_empty_signals(self):
        result = _parse(_wig_dict(signals=[]))
        assert not result.ok
        assert any("signals" in e for e in result.errors)

    def test_signal_missing_alias_and_bad_pronto_both_reported(self):
        result = _parse(_wig_dict(signals=[
            {"pronto": "zzzz not pronto"},
            {"alias": "OK", "pronto": PRONTO},
        ]))
        assert not result.ok
        assert any("signals[0].alias" in e for e in result.errors)
        assert any("signals[0].pronto" in e for e in result.errors)

    def test_all_errors_reported_together(self):
        result = _parse({
            "format": WIG_FORMAT_V1,
            "name": "",
            "brand": 7,
            "signals": [{"alias": "", "pronto": ""}],
        })
        assert not result.ok
        assert len(result.errors) >= 3

    def test_bool_send_count_rejected(self):
        result = _parse(_wig_dict(
            signals=[{"alias": "A", "pronto": PRONTO, "send_count": True}]
        ))
        assert not result.ok

    def test_size_cap(self):
        big = json.dumps(_wig_dict(notes="x" * (MAX_WIG_BYTES + 100)))
        result = parse_wig(big)
        assert not result.ok
        assert "size cap" in result.errors[0]


class TestSerializeRoundTrip:
    def test_round_trip_preserves_everything(self):
        original = _parse(_wig_dict(
            model="IQ3",
            origin="converted:smartir",
            fittings=[{"handle": "tester", "date": "2026-07-19"}],
            signals=[
                {"alias": "Power", "pronto": PRONTO, "send_count": 2,
                 "future_key": "kept"},
            ],
        )).wig
        text = serialize_wig(original)
        again = parse_wig(text)
        assert again.ok, again.errors
        assert again.wig == original

    def test_serialized_shape(self):
        wig = Wig(name="TV", signals=[WigSignal("Power", PRONTO)])
        text = serialize_wig(wig)
        data = json.loads(text)
        assert list(data)[:2] == ["format", "name"]
        assert data["format"] == WIG_FORMAT_V1
        # send_count of 1 is the default and is omitted from files.
        assert "send_count" not in data["signals"][0]
        assert text.endswith("\n")


class TestCanonicalization:
    def test_formatting_differences_hash_identically(self):
        a = [WigSignal("Power", PRONTO, 1)]
        b = [WigSignal("Power", PRONTO_LOWER, 1)]
        assert signals_content_hash(a) == signals_content_hash(b)

    def test_code_change_changes_hash(self):
        a = [WigSignal("Power", PRONTO, 1)]
        changed = PRONTO[:-1] + "1"
        b = [WigSignal("Power", changed, 1)]
        assert signals_content_hash(a) != signals_content_hash(b)

    def test_alias_and_count_participate(self):
        base = [WigSignal("Power", PRONTO, 1)]
        renamed = [WigSignal("Power On", PRONTO, 1)]
        counted = [WigSignal("Power", PRONTO, 2)]
        hashes = {
            signals_content_hash(base),
            signals_content_hash(renamed),
            signals_content_hash(counted),
        }
        assert len(hashes) == 3

    def test_unknown_signal_keys_excluded(self):
        plain = [WigSignal("Power", PRONTO, 1)]
        decorated = [WigSignal("Power", PRONTO, 1, extra={"future": 1})]
        assert (
            signals_content_hash(plain) == signals_content_hash(decorated)
        )

    def test_canonical_form_is_stable(self):
        """Pin the exact canonical string: fittings bind to this."""
        canon = canonical_signals_json([WigSignal("Power", PRONTO, 1)])
        assert canon == (
            '[{"alias":"Power",'
            f'"pronto":"{PRONTO_LOWER}",'
            '"send_count":1}]'
        )


class TestFilenames:
    @pytest.mark.parametrize("name,expected", [
        ("Foxtel IQ", "foxtel-iq.wig.json"),
        ("  Living Room / TV!  ", "living-room-tv.wig.json"),
        ("日本語", "wig.wig.json"),
    ])
    def test_slugify(self, name, expected):
        assert wig_filename(name) == expected

    def test_collision_suffix(self):
        taken = {"tv.wig.json", "tv-2.wig.json"}
        assert wig_filename("TV", taken) == "tv-3.wig.json"
