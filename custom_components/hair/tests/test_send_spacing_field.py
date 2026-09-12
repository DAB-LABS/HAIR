"""Where a row's send_spacing_ms comes from, and where it does not.

The field alone decides which send path a row takes, so what writes it
matters as much as what it means. Mint estimates today's cadence for a
row created here with send times above 1; adopt copies what the wig
carried and invents nothing; a matrix porthole never gets one at all
(send spacing, GH #151).
"""
from __future__ import annotations

import json

import pytest

from custom_components.hair.const import (
    SEND_AIR_TIME_MAX_MS,
    SEND_SPACING_MAX_MS,
    SEND_SPACING_MIN_MS,
)
from custom_components.hair.mint import mint_command
from custom_components.hair.models import (
    CommandSource,
    IRCommand,
    UnknownSignal,
    clone_command,
)
from custom_components.hair.wig_format import (
    canonical_signals_json,
    parse_wig,
    serialize_wig,
    signal_row_digest,
    signals_content_hash,
)

# The reporter's shape (GH #151): a clean 34-pair NEC frame of about
# 64.6ms whose last word is the receiver's 10ms idle tail.
AVBFR_PRONTO = (
    "0000 006D 0022 0000 014A 00A6 0013 0016 0013 0016 0013 0016 "
    "0013 0016 0013 0016 0013 0016 0013 0016 0013 0016 0013 003F "
    "0013 003F 0013 003F 0013 003F 0013 003F 0013 003F 0013 003F "
    "0013 003F 0013 003F 0013 0016 0013 003F 0013 0016 0013 0016 "
    "0013 0016 0013 003F 0013 0016 0013 0016 0013 003F 0013 0016 "
    "0013 003F 0013 003F 0013 003F 0013 0016 0013 003F 0013 017C"
)
# A long AC-style blob: 400ms of block, so ten sends cannot fit the cap.
LONG_RAW = [200_000, -100_000, 200_000]


def _wig(signals):
    return json.dumps({
        "format": "hair-wig/3",
        "name": "Amplificateur Pioneer",
        "signals": signals,
    })


class TestMintEstimates:
    def test_a_row_that_repeats_lands_where_an_old_row_lands(self):
        command = mint_command(
            name="Power", protocol="PRONTO", code=AVBFR_PRONTO, send_count=8
        )
        # Block 64.6ms + 50ms terminator + 60ms pipeline, rounded to 5.
        assert command.send_spacing_ms == 175

    def test_a_row_that_sends_once_has_nothing_to_space(self):
        command = mint_command(
            name="Power", protocol="PRONTO", code=AVBFR_PRONTO, send_count=1
        )
        assert command.send_spacing_ms is None

    def test_a_matrix_porthole_never_gets_one(self):
        command = mint_command(
            name="Cool 22", protocol="PRONTO", code=AVBFR_PRONTO,
            send_count=8, source=CommandSource.MATRIX,
        )
        assert command.send_spacing_ms is None

    def test_an_over_cap_estimate_leaves_the_row_old_style(self):
        # Ten sends of a 400ms block is 4s of air whatever the spacing.
        # A row born holding a value its own editor would refuse is
        # worse than a row that stays on today's path.
        command = mint_command(
            name="Blast", protocol=None, raw_timings=LONG_RAW, send_count=10
        )
        assert command.send_spacing_ms is None

    def test_the_estimate_is_measured_after_the_decode_is_stamped(self):
        # A decodable row sends re-encoded timings, so the estimate has
        # to be taken on the decoded block. Before apply_identity there
        # is no decoded block to measure.
        command = mint_command(
            name="Power", protocol="PRONTO", code=AVBFR_PRONTO, send_count=4
        )
        assert command.send_spacing_ms is not None
        assert command.send_spacing_ms >= SEND_SPACING_MIN_MS
        assert command.send_spacing_ms <= SEND_SPACING_MAX_MS

    def test_an_explicit_value_is_stored_as_given(self):
        command = mint_command(
            name="Power", protocol="PRONTO", code=AVBFR_PRONTO,
            send_count=8, send_spacing_ms=135,
        )
        assert command.send_spacing_ms == 135

    def test_estimate_off_means_no_value_invented(self):
        command = mint_command(
            name="Power", protocol="PRONTO", code=AVBFR_PRONTO,
            send_count=8, estimate_spacing=False,
        )
        assert command.send_spacing_ms is None


class TestTheRecord:
    def test_it_round_trips(self):
        command = IRCommand(name="Power", send_count=8, send_spacing_ms=135)
        assert IRCommand.from_dict(command.to_dict()).send_spacing_ms == 135

    def test_an_old_row_writes_no_key_at_all(self):
        # An untouched row's record stays byte-identical to what it was
        # before the field existed.
        assert "send_spacing_ms" not in IRCommand(name="Power").to_dict()

    def test_a_signal_round_trips_too(self):
        signal = UnknownSignal(fingerprint="fp", send_spacing_ms=250)
        assert UnknownSignal.from_dict(signal.to_dict()).send_spacing_ms == 250

    def test_an_unknown_signal_with_no_value_writes_no_key(self):
        assert "send_spacing_ms" not in UnknownSignal(
            fingerprint="fp"
        ).to_dict()

    def test_a_clone_carries_it(self):
        source = IRCommand(name="Power", send_count=8, send_spacing_ms=135)
        assert clone_command(source).send_spacing_ms == 135

    def test_it_is_on_both_rosters(self):
        from custom_components.hair.models import (
            _CLONE_SKIPS,
            _KNOWN_COMMAND,
            _KNOWN_SIGNAL,
        )

        assert "send_spacing_ms" in _KNOWN_COMMAND
        assert "send_spacing_ms" in _KNOWN_SIGNAL
        # A real attribute, so the clone walk copies it.
        assert "send_spacing_ms" not in _CLONE_SKIPS
        assert "send_spacing_ms" in _KNOWN_COMMAND - _CLONE_SKIPS

    def test_a_garbage_value_reads_back_as_absent(self):
        assert IRCommand.from_dict(
            {"name": "Power", "send_spacing_ms": "banana"}
        ).send_spacing_ms is None


class TestTheWigReader:
    def test_a_value_survives_the_round_trip(self):
        text = _wig([
            {"alias": "Power", "pronto": AVBFR_PRONTO,
             "send_count": 8, "send_spacing_ms": 135},
        ])
        wig = parse_wig(text).wig
        assert wig.signals[0].send_spacing_ms == 135
        again = parse_wig(serialize_wig(wig)).wig
        assert again.signals[0].send_spacing_ms == 135

    def test_the_reporters_wig_carries_none(self):
        # Three bypass NEC rows, send_count 4/4/8, no spacing key: this
        # is the file that arrived on GH #151.
        text = _wig([
            {"alias": "Sound Down", "pronto": AVBFR_PRONTO,
             "send_count": 4, "ditto_count": 0, "bypass_protocol": True},
            {"alias": "Sound Up", "pronto": AVBFR_PRONTO,
             "send_count": 4, "ditto_count": 0, "bypass_protocol": True},
            {"alias": "Power", "pronto": AVBFR_PRONTO,
             "send_count": 8, "ditto_count": 0, "bypass_protocol": True},
        ])
        wig = parse_wig(text).wig
        assert [s.send_spacing_ms for s in wig.signals] == [None, None, None]

    def test_a_row_without_a_value_writes_no_key(self):
        text = _wig([{"alias": "Power", "pronto": AVBFR_PRONTO}])
        assert "send_spacing_ms" not in serialize_wig(parse_wig(text).wig)

    @pytest.mark.parametrize(
        "bad", [True, "135", 1.5, 19, 1001, -5]
    )
    def test_a_bad_value_is_refused_not_coerced(self, bad):
        text = _wig([
            {"alias": "Power", "pronto": AVBFR_PRONTO,
             "send_count": 8, "send_spacing_ms": bad},
        ])
        result = parse_wig(text)
        assert result.wig is None
        assert any(
            "signals[0].send_spacing_ms" in e for e in result.errors
        ), result.errors

    @pytest.mark.parametrize("edge", [SEND_SPACING_MIN_MS, SEND_SPACING_MAX_MS])
    def test_the_bounds_themselves_are_accepted(self, edge):
        text = _wig([
            {"alias": "Power", "pronto": AVBFR_PRONTO,
             "send_count": 8, "send_spacing_ms": edge},
        ])
        assert parse_wig(text).wig.signals[0].send_spacing_ms == edge


class TestTheDigestsDoNotMove:
    def test_two_wigs_differing_only_in_spacing_are_the_same_codes(self):
        # OUT of every canonical form on purpose: what a spacing does to
        # the waveform depends on the importing house's blaster, and a
        # canonicalization contract cannot carry a platform-dependent
        # member. The cost is recorded rather than hidden: these two
        # dedupe as one file.
        plain = parse_wig(_wig([
            {"alias": "Power", "pronto": AVBFR_PRONTO, "send_count": 8},
        ])).wig
        spaced = parse_wig(_wig([
            {"alias": "Power", "pronto": AVBFR_PRONTO,
             "send_count": 8, "send_spacing_ms": 135},
        ])).wig
        assert canonical_signals_json(plain.signals) == (
            canonical_signals_json(spaced.signals)
        )
        assert signals_content_hash(plain.signals) == (
            signals_content_hash(spaced.signals)
        )
        assert signal_row_digest(plain.signals[0]) == (
            signal_row_digest(spaced.signals[0])
        )


class TestExport:
    def test_a_tuned_device_exports_its_spacing(self):
        from custom_components.hair.models import IRDevice
        from custom_components.hair.wig_export import build_wig_from_device

        device = IRDevice(name="Amplificateur Pioneer")
        device.commands.append(IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=AVBFR_PRONTO,
            send_count=8, send_spacing_ms=135,
        ))
        wig = build_wig_from_device(device).wig
        assert wig.signals[0].send_spacing_ms == 135

    def test_an_old_row_exports_nothing(self):
        from custom_components.hair.models import IRDevice
        from custom_components.hair.wig_export import build_wig_from_device

        device = IRDevice(name="Amplificateur Pioneer")
        device.commands.append(IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=AVBFR_PRONTO,
            send_count=8,
        ))
        wig = build_wig_from_device(device).wig
        assert wig.signals[0].send_spacing_ms is None


class TestTheAirCapIsTheOneFunction:
    def test_mint_and_the_cap_agree(self):
        from custom_components.hair.send_plan import (
            build_like_send_path,
            realised_air_ms,
        )

        command = mint_command(
            name="Power", protocol="PRONTO", code=AVBFR_PRONTO, send_count=8
        )
        air = realised_air_ms(
            build_like_send_path(command), 8, command.send_spacing_ms
        )
        assert air <= SEND_AIR_TIME_MAX_MS
