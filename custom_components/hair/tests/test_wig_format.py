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
    WIG_FORMAT_V2,
    Wig,
    WigSignal,
    canonical_cells_json,
    canonical_signals_json,
    cells_content_hash,
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
        # hair-wig/2 reads since Cold Cuts; 3 is the future now.
        result = _parse(_wig_dict(format="hair-wig/3"))
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


class TestIdentifiers:
    """The identifiers block (v0.8.0): product-identity anchors for
    hardware whose brand and model mean nothing (owner ruling
    2026-07-27). Any string-to-string pairs; blessed keys documented,
    not enforced."""

    def _text(self, identifiers) -> str:
        import json as _json

        return _json.dumps({
            "format": "hair-wig/1",
            "name": "Candles",
            "identifiers": identifiers,
            "signals": [{"alias": "Power", "pronto": PRONTO}],
        })

    def test_valid_identifiers_parse(self):
        result = parse_wig(self._text(
            {"fcc_id": "SUW74000BT", "upc": "812345678901"}
        ))
        assert result.ok
        assert result.wig.identifiers == {
            "fcc_id": "SUW74000BT", "upc": "812345678901",
        }

    def test_unblessed_keys_accepted(self):
        """Future anchors arrive without a format bump."""
        result = parse_wig(self._text({"gtin": "04012345678901"}))
        assert result.ok
        assert result.wig.identifiers == {"gtin": "04012345678901"}

    def test_non_object_rejected(self):
        result = parse_wig(self._text("FCC-123"))
        assert not result.ok
        assert any("identifiers" in e for e in result.errors)

    def test_non_string_value_rejected(self):
        result = parse_wig(self._text({"upc": 812345678901}))
        assert not result.ok
        assert any("identifiers.upc" in e for e in result.errors)

    def test_empty_object_parses_as_none(self):
        result = parse_wig(self._text({}))
        assert result.ok
        assert result.wig.identifiers is None

    def test_roundtrip_and_key_position(self):
        import json as _json

        result = parse_wig(self._text({"asin": "B0ABC12345"}))
        out = serialize_wig(result.wig)
        again = parse_wig(out)
        assert again.ok
        assert again.wig.identifiers == {"asin": "B0ABC12345"}
        # Serialized before signals, with the schema keys.
        keys = list(_json.loads(out).keys())
        assert keys.index("identifiers") < keys.index("signals")

    def test_absent_stays_absent(self):
        import json as _json

        text = _json.dumps({
            "format": "hair-wig/1", "name": "X",
            "signals": [{"alias": "A", "pronto": PRONTO}],
        })
        result = parse_wig(text)
        assert result.ok and result.wig.identifiers is None
        assert "identifiers" not in _json.loads(serialize_wig(result.wig))


class TestIdentifierMultiples:
    """Values may be one string or a list (owner ruling 2026-07-27:
    rebadged device families carry several UPCs for one device)."""

    def _text(self, identifiers) -> str:
        import json as _json

        return _json.dumps({
            "format": "hair-wig/1",
            "name": "Candles",
            "identifiers": identifiers,
            "signals": [{"alias": "Power", "pronto": PRONTO}],
        })

    def test_list_values_parse_and_roundtrip(self):
        import json as _json

        text = self._text({
            "upc": ["812345678901", "812345678902"],
            "fcc_id": "SUW74000BT",
        })
        result = parse_wig(text)
        assert result.ok
        assert result.wig.identifiers["upc"] == [
            "812345678901", "812345678902",
        ]
        again = _json.loads(serialize_wig(result.wig))
        assert again["identifiers"]["upc"] == [
            "812345678901", "812345678902",
        ]

    def test_empty_list_rejected(self):
        result = parse_wig(self._text({"upc": []}))
        assert not result.ok

    def test_list_with_non_string_rejected(self):
        result = parse_wig(self._text({"upc": ["ok", 5]}))
        assert not result.ok
        assert any("identifiers.upc" in e for e in result.errors)

    def test_identifier_values_helper_normalizes(self):
        from custom_components.hair.wig_format import identifier_values

        ids = {"upc": ["1", "2"], "fcc_id": "X"}
        assert identifier_values(ids, "upc") == ["1", "2"]
        assert identifier_values(ids, "fcc_id") == ["X"]
        assert identifier_values(ids, "asin") == []
        assert identifier_values(None, "upc") == []


class TestIdentifierInputParsing:
    """The WS layer's comma-splitting for dialog inputs."""

    def test_parse_forms(self):
        from custom_components.hair.websocket_api import (
            _parse_identifier_input,
        )

        assert _parse_identifier_input("") is None
        assert _parse_identifier_input("  ") is None
        assert _parse_identifier_input("SUW74000BT") == "SUW74000BT"
        assert _parse_identifier_input(
            "812345678901, 812345678902"
        ) == ["812345678901", "812345678902"]
        assert _parse_identifier_input(",a,") == "a"

    def test_apply_edits(self):
        from custom_components.hair.websocket_api import (
            _apply_identifier_edits,
        )

        wig = Wig(name="X", signals=[WigSignal(alias="A", pronto=PRONTO)],
                  identifiers={"fcc_id": "OLD", "custom": "kept"})
        _apply_identifier_edits(wig, {
            "fcc_id": "NEW", "upc": "1, 2", "asin": "",
        })
        assert wig.identifiers == {
            "fcc_id": "NEW", "custom": "kept", "upc": ["1", "2"],
        }
        # Clearing everything drops the block.
        _apply_identifier_edits(wig, {"fcc_id": "", "upc": ""})
        assert wig.identifiers == {"custom": "kept"}

    def test_absent_fields_untouched(self):
        from custom_components.hair.websocket_api import (
            _apply_identifier_edits,
        )

        wig = Wig(name="X", signals=[WigSignal(alias="A", pronto=PRONTO)],
                  identifiers={"upc": "1"})
        _apply_identifier_edits(wig, {"name": "whatever"})
        assert wig.identifiers == {"upc": "1"}


class TestKind:
    """The kind field (owner rulings 2026-07-27): what the device IS,
    squashed slug, set at signing or in the editor, feeds the
    generated-integration naming convention."""

    def test_kind_slug_squashes(self):
        from custom_components.hair.wig_format import kind_slug

        assert kind_slug("Sound Bar") == "soundbar"
        assert kind_slug("sound-bar") == "soundbar"
        assert kind_slug("Set-Top Box") == "settopbox"
        assert kind_slug("TV") == "tv"
        assert kind_slug("!!!") == ""

    def test_kind_roundtrip(self):
        import json as _json

        text = _json.dumps({
            "format": "hair-wig/1", "name": "Candles",
            "kind": "candles",
            "signals": [{"alias": "On", "pronto": PRONTO}],
        })
        result = parse_wig(text)
        assert result.ok and result.wig.kind == "candles"
        out = _json.loads(serialize_wig(result.wig))
        assert out["kind"] == "candles"
        keys = list(out.keys())
        assert keys.index("kind") < keys.index("signals")

    def test_kind_absent_stays_absent(self):
        import json as _json

        text = _json.dumps({
            "format": "hair-wig/1", "name": "X",
            "signals": [{"alias": "A", "pronto": PRONTO}],
        })
        result = parse_wig(text)
        assert result.ok and result.wig.kind is None
        assert "kind" not in _json.loads(serialize_wig(result.wig))

    def test_device_export_auto_stamps_unambiguous_kind(self):
        from custom_components.hair.const import DeviceType
        from custom_components.hair.models import IRCommand, IRDevice
        from custom_components.hair.wig_export import build_wig_from_device

        def _dev(dtype):
            return IRDevice(
                name="X", device_type=dtype,
                commands=[IRCommand(
                    id="c1", name="Power", protocol="PRONTO", code=PRONTO,
                )],
            )

        assert build_wig_from_device(_dev(DeviceType.FAN)).wig.kind == "fan"
        assert build_wig_from_device(_dev(DeviceType.AC)).wig.kind == "ac"
        # media_player is ambiguous (tv? soundbar?): no stamp, the
        # signing prompt asks the human.
        assert build_wig_from_device(
            _dev(DeviceType.MEDIA_PLAYER)
        ).wig.kind is None


class TestKindAtSigning:
    @pytest.mark.asyncio
    async def test_finish_sets_kind_once(self, fake_hass, tmp_path):
        from custom_components.hair.tests.test_wig_fitting import (
            _read_wig,
            _write_wig,
        )
        from custom_components.hair.wig_fitting import FittingManager

        fake_hass.config.config_dir = str(tmp_path)
        wigs = tmp_path / "hair" / "wigs"
        wigs.mkdir(parents=True)
        filename = _write_wig(wigs)
        manager = FittingManager(fake_hass, monitor=None)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_finish(
            filename, "dab", None, None, None, kind="Candles",
        )
        wig = _read_wig(wigs)
        assert wig.kind == "candles"  # slugged
        # A later finish with a different kind does NOT overwrite.
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_finish(
            filename, "dab", None, None, None, kind="fan",
        )
        assert _read_wig(wigs).kind == "candles"

    def test_share_strip_preserves_kind_and_identifiers(self):
        """Regression: shared_wig_text rebuilt the Wig without the
        v0.8.0 fields, silently dropping them on stripped shares."""
        import json as _json

        from custom_components.hair.tests.test_wig_fitting import (
            _complete_fitting,
            _wig,
        )
        from custom_components.hair.wig_fitting import shared_wig_text

        wig = _wig([_complete_fitting(_wig(), draft=True)])
        wig.kind = "candles"
        wig.identifiers = {"upc": "794969274724"}
        shared = _json.loads(shared_wig_text(wig))
        assert shared["kind"] == "candles"
        assert shared["identifiers"] == {"upc": "794969274724"}


class TestClimateUnit:
    """The climate block's temperature scale (unit ruling 2026-07-29).

    Machine keys stay file-native forever, so the unit is a FILE fact:
    parsed strictly, defaulted to "C" (the SmartIR corpus convention),
    serialized only when it earns its bytes, and hashed -- the same
    numbers on a different scale are different states.
    """

    def _matrix_wig(self, **climate_over) -> dict:
        climate = {
            "min_temp": 16,
            "max_temp": 30,
            "off": PRONTO,
            "cells": [
                {"mode": "cool", "fan": "auto", "temp": 22,
                 "pronto": PRONTO},
            ],
        }
        climate.update(climate_over)
        return {"format": WIG_FORMAT_V2, "name": "AC", "climate": climate}

    def test_absent_defaults_to_celsius(self):
        result = _parse(self._matrix_wig())
        assert result.ok, result.errors
        assert result.wig.climate.unit == "C"

    def test_fahrenheit_parses(self):
        result = _parse(self._matrix_wig(unit="F"))
        assert result.ok, result.errors
        assert result.wig.climate.unit == "F"

    @pytest.mark.parametrize("bad", ["K", "c", "f", "Celsius", 1, True])
    def test_only_the_two_letters_validate(self, bad):
        result = _parse(self._matrix_wig(unit=bad))
        assert not result.ok
        assert any("climate.unit" in e for e in result.errors)

    def test_serialize_omits_the_celsius_default(self):
        """A Celsius file stays byte-identical to its pre-unit self."""
        wig = _parse(self._matrix_wig()).wig
        assert '"unit"' not in serialize_wig(wig)

    def test_fahrenheit_round_trips(self):
        wig = _parse(self._matrix_wig(unit="F")).wig
        text = serialize_wig(wig)
        assert json.loads(text)["climate"]["unit"] == "F"
        again = parse_wig(text)
        assert again.ok and again.wig.climate.unit == "F"

    def test_unit_participates_in_the_cells_hash(self):
        """The format is unreleased, so the canonical form could still
        grow the unit without a hash migration; from here on it is
        frozen. A 22C lattice and a 22F lattice must never share a
        fitting ledger."""
        c = _parse(self._matrix_wig()).wig.climate
        f = _parse(self._matrix_wig(unit="F")).wig.climate
        assert '"unit":"C"' in canonical_cells_json(c)
        assert '"unit":"F"' in canonical_cells_json(f)
        assert cells_content_hash(c) != cells_content_hash(f)


# ---------------------------------------------------------------------------
# bypass_protocol (Highlights, GH #78)
# ---------------------------------------------------------------------------


class TestBypassProtocol:
    """Send these bytes verbatim, do not decode and re-encode them.

    The flag exists because a capture whose repeats are baked in has no
    way to declare itself: kno-te's Dreo Power code is a Symphony
    repeat-train, HAIR re-encodes it to one clean frame, and the fan
    ignores it. A device command could already say "send it raw"; a wig
    could not, so the intent died at export and his wig would have
    arrived broken for the next person.
    """

    def test_absent_flag_hashes_exactly_as_before(self):
        """THE test that protects every wig in the wild.

        A wig with nothing bypassed must produce the byte-identical
        canonical string it produced before the field existed, or every
        fitting signature ever written stops verifying at once. Pinned
        against a literal, not against a recomputation.
        """
        canon = canonical_signals_json([
            WigSignal(alias="Power", pronto=PRONTO),
            WigSignal(alias="Mode", pronto=PRONTO, send_count=3),
        ])
        assert canon == (
            f'[{{"alias":"Power","pronto":"{PRONTO_LOWER}","send_count":1}},'
            f'{{"alias":"Mode","pronto":"{PRONTO_LOWER}","send_count":3}}]'
        )
        assert "bypass_protocol" not in canon

    def test_explicit_false_hashes_the_same_as_absent(self):
        """Setting it to False is not a change to the wig."""
        plain = [WigSignal(alias="A", pronto=PRONTO)]
        explicit = [
            WigSignal(alias="A", pronto=PRONTO, bypass_protocol=False)
        ]
        assert signals_content_hash(plain) == signals_content_hash(explicit)

    def test_true_changes_the_hash(self):
        """It changes what transmits, so it must change identity --
        otherwise somebody could flip send behaviour after a wig was
        fitted and the signature would still verify."""
        plain = [WigSignal(alias="A", pronto=PRONTO)]
        bypassed = [
            WigSignal(alias="A", pronto=PRONTO, bypass_protocol=True)
        ]
        assert signals_content_hash(plain) != signals_content_hash(bypassed)
        assert "bypass_protocol" in canonical_signals_json(bypassed)

    def test_round_trip(self):
        wig = Wig(name="Dreo", signals=[
            WigSignal(alias="Power", pronto=PRONTO, bypass_protocol=True),
            WigSignal(alias="Mode", pronto=PRONTO),
        ])
        back = parse_wig(serialize_wig(wig)).wig
        assert back.signals[0].bypass_protocol is True
        assert back.signals[1].bypass_protocol is False

    def test_false_is_omitted_from_output(self):
        """So a wig with nothing bypassed is byte-identical on disk to
        one written before the field existed."""
        wig = Wig(name="Plain", signals=[WigSignal(alias="A", pronto=PRONTO)])
        assert "bypass_protocol" not in serialize_wig(wig)

    def test_it_does_not_fall_into_extra(self):
        """Parsed explicitly, so a round-trip cannot emit it twice."""
        wig = Wig(name="D", signals=[
            WigSignal(alias="A", pronto=PRONTO, bypass_protocol=True),
        ])
        back = parse_wig(serialize_wig(wig)).wig
        assert "bypass_protocol" not in back.signals[0].extra
        assert serialize_wig(back).count("bypass_protocol") == 1

    @pytest.mark.parametrize("bad", ["true", 1, 0, "yes", [], {}])
    def test_a_non_bool_is_refused_not_coerced(self, bad):
        """A truthy string would silently change both what the signal
        transmits and what it hashes to, so a wrong type has to be an
        error the writer can see rather than a value we guess at."""
        result = _parse(_wig_dict(signals=[{
            "alias": "A", "pronto": PRONTO, "bypass_protocol": bad,
        }]))
        assert not result.ok
        assert any("bypass_protocol" in e for e in result.errors)

    def test_true_and_false_are_both_accepted(self):
        for value in (True, False):
            result = _parse(_wig_dict(signals=[{
                "alias": "A", "pronto": PRONTO, "bypass_protocol": value,
            }]))
            assert result.ok, result.errors
            assert result.wig.signals[0].bypass_protocol is value

    def test_an_old_reader_round_trips_it(self):
        """Forward compatibility, documented in docs/wig-format.md. An
        older HAIR parses the unknown key into ``extra``, and
        ``_signal_out`` ends with ``out.update(sig.extra)``, so it
        preserves the flag rather than destroying it. That install
        transmits wrong, but its fitting reads as not matching rather
        than silently attesting a code it sent differently."""
        old_style = WigSignal(
            alias="A", pronto=PRONTO, extra={"bypass_protocol": True},
        )
        out = serialize_wig(Wig(name="D", signals=[old_style]))
        assert "bypass_protocol" in out
        assert parse_wig(out).wig.signals[0].bypass_protocol is True
