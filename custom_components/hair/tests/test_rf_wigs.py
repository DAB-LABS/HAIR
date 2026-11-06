"""RF send round, T5: radio rows in wigs (hair-wig/5).

The contract is ``agent-exchange/rf-hear/rf-send-doors-addendum-b.md``:
a flat signal carries ``rf`` in place of ``pronto``, the file stamps /5
only when it holds one, the row digest reads the band and not the exact
Hz, and every infrared wig writes and hashes exactly what it did before
(pinned against the output of the commit before T5).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import rf_frames
from custom_components.hair.const import (
    MEDIUM_RF,
    RF_GAP_ASSUMED,
    RF_GAP_MEASURED,
    RF_PROTOCOL,
    CommandCategory,
    CommandSource,
)
from custom_components.hair.identity import canonical_fingerprint
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.tests.test_wig_format import PRONTO
from custom_components.hair.wig_format import (
    WIG_FORMAT_V3,
    WIG_FORMAT_V4,
    WIG_FORMAT_V5,
    Wig,
    WigRf,
    WigSignal,
    canonical_signals_json,
    is_radio_signal,
    parse_wig,
    rf_band,
    rf_row_digest,
    serialize_wig,
    signal_row_digest,
    wig_content_hash,
)

FIXTURES = Path(__file__).parent / "fixtures"
KEYFOB = FIXTURES / "rf" / "it104-keyfob-433.json"
PIN = FIXTURES / "rf_wig_ir_pin.json"


def _signed(edges):
    return [abs(v) if i % 2 == 0 else -abs(v) for i, v in enumerate(edges)]


@pytest.fixture(scope="module")
def keyfob():
    captures = json.loads(KEYFOB.read_text(encoding="utf-8"))["captures"]
    return rf_frames.analyze(_signed(captures[0]["pulses"]))


@pytest.fixture
def frame(keyfob):
    """The keyfob's one frame, without its gap, as a wig carries it."""
    values = list(keyfob.frame)
    while values and values[-1] < 0:
        values.pop()
    return values


def _radio_wig(frame, **rf) -> Wig:
    fields = {"frequency_hz": 433_920_000, "frame": frame, "frame_gap_us": 10_850}
    fields.update(rf)
    return Wig(
        name="Keyfob", wig_id="11111111-2222-3333-4444-555555555555",
        signals=[
            WigSignal("Power", PRONTO),
            WigSignal("Button 1", "", send_count=5, rf=WigRf(**fields)),
        ],
    )


def _file(frame, version=WIG_FORMAT_V5, **signal) -> str:
    sig = {
        "alias": "Button 1",
        "rf": {"frequency_hz": 433_920_000, "modulation": "ook",
               "frame": frame, "frame_gap_us": 10_850},
        "ditto_count": 0, "bypass_protocol": False,
    }
    sig.update(signal)
    return json.dumps({"format": version, "name": "Keyfob", "signals": [sig]})


class TestTheFile:
    def test_a_radio_wig_stamps_v5_and_round_trips(self, frame):
        text = serialize_wig(_radio_wig(frame))
        assert f'"format": "{WIG_FORMAT_V5}"' in text
        parsed = parse_wig(text)
        assert parsed.ok, parsed.errors
        radio = parsed.wig.signals[1]
        assert is_radio_signal(radio) and radio.pronto == ""
        assert radio.rf.frame == frame
        assert radio.rf.frame_gap_us == 10_850
        assert radio.send_count == 5
        assert serialize_wig(parsed.wig) == text

    def test_the_rf_object_is_written_in_reading_order(self, frame):
        data = json.loads(serialize_wig(_radio_wig(frame)))
        radio = data["signals"][1]
        assert "pronto" not in radio
        assert list(radio["rf"]) == [
            "frequency_hz", "modulation", "frame", "frame_gap_us",
        ]
        assert radio["ditto_count"] == 0 and radio["bypass_protocol"] is False

    def test_an_unknown_gap_is_written_as_null(self, frame):
        data = json.loads(serialize_wig(_radio_wig(frame, frame_gap_us=None)))
        assert data["signals"][1]["rf"]["frame_gap_us"] is None
        assert parse_wig(json.dumps(data)).ok

    def test_unknown_rf_keys_survive(self, frame):
        data = json.loads(_file(frame))
        data["signals"][0]["rf"]["future"] = {"x": 1}
        wig = parse_wig(json.dumps(data)).wig
        assert json.loads(serialize_wig(wig))["signals"][0]["rf"]["future"] == {"x": 1}

    def test_an_infrared_wig_never_stamps_v5(self):
        wig = Wig(name="TV", signals=[WigSignal("Power", PRONTO)])
        assert f'"format": "{WIG_FORMAT_V3}"' in serialize_wig(wig)

    def test_rf_under_v4_is_refused_with_the_version_it_needs(self, frame):
        result = parse_wig(_file(frame, version=WIG_FORMAT_V4))
        assert not result.ok
        assert any(WIG_FORMAT_V5 in error for error in result.errors)

    def test_a_signal_with_both_codes_is_refused(self, frame):
        result = parse_wig(_file(frame, pronto=PRONTO))
        assert not result.ok
        assert any("both pronto and rf" in error for error in result.errors)

    @pytest.mark.parametrize(
        ("rf", "fragment"),
        [
            ({"frequency_hz": 433.92}, "frequency_hz"),
            ({"frequency_hz": 500}, "frequency_hz"),
            ({"frame": []}, ".frame"),
            ({"frame": [350, 0, 350]}, ".frame"),
            ({"frame": [-350, 1050, -350]}, "start on a mark"),
            ({"frame": [350, 1050, -350]}, "alternate"),
            ({"modulation": "fsk"}, "'fsk'"),
            ({"frame_gap_us": -5}, "frame_gap_us"),
        ],
    )
    def test_a_bad_rf_object_is_refused_by_field(self, frame, rf, fragment):
        data = json.loads(_file(frame))
        data["signals"][0]["rf"].update(rf)
        result = parse_wig(json.dumps(data))
        assert not result.ok
        assert any(fragment in error for error in result.errors), result.errors

    @pytest.mark.parametrize("signal", [{"ditto_count": 1}, {"bypass_protocol": True}])
    def test_a_radio_signal_has_no_dittos_and_no_raw_pin(self, frame, signal):
        result = parse_wig(_file(frame, **signal))
        assert not result.ok
        assert any("ditto_count 0" in error for error in result.errors)

    def test_v6_is_still_refused_politely(self, frame):
        result = parse_wig(_file(frame, version="hair-wig/6"))
        assert not result.ok and len(result.errors) == 1
        assert "update HAIR" in result.errors[0]


class TestInfraredIsUntouched:
    """Every infrared wig writes and hashes what it did before T5: the
    pin is the commit before T5 (af1f15d) run over the same inputs."""

    @staticmethod
    def _current() -> dict:
        def sha(text: str) -> str:
            return hashlib.sha256(text.encode()).hexdigest()

        out: dict = {}
        for path in sorted(FIXTURES.rglob("*.wig.json")):
            wig = parse_wig(path.read_text(encoding="utf-8")).wig
            out[path.name] = [
                sha(serialize_wig(wig)), sha(canonical_signals_json(wig.signals)),
                wig_content_hash(wig), [signal_row_digest(s) for s in wig.signals],
            ]
        flat = Wig(
            name="TV", wig_id="11111111-2222-3333-4444-555555555555",
            brand="B", kind="tv",
            signals=[
                WigSignal("Power", PRONTO),
                WigSignal("Vol up", PRONTO, send_count=3, send_spacing_ms=110,
                          ditto_count=2),
                WigSignal("Raw", PRONTO, bypass_protocol=True, extra={"note": "x"}),
            ],
            extra={"zzz": 1},
        )
        out["synthetic-flat"] = [
            serialize_wig(flat), canonical_signals_json(flat.signals),
            wig_content_hash(flat), [signal_row_digest(s) for s in flat.signals],
        ]
        return out

    def test_fixtures_and_a_flat_wig_match_the_commit_before(self):
        pinned = json.loads(PIN.read_text(encoding="utf-8"))
        assert len(pinned) == 4
        assert self._current() == pinned


class TestTheDigest:
    def test_the_layout_is_the_contract(self, frame):
        recipe = "rf|433.9|ook|" + ",".join(str(v) for v in frame) + "|d0|b0"
        expected = hashlib.sha256(recipe.encode()).hexdigest()[:16]
        assert rf_row_digest(433_920_000, frame) == expected

    def test_the_band_and_not_the_hz(self, frame):
        assert rf_band(433_920_000) == rf_band(433_840_000) == "433.9"
        assert rf_band(315_000_000) == "315.0"
        assert rf_row_digest(433_920_000, frame) == rf_row_digest(433_840_000, frame)
        assert rf_row_digest(433_920_000, frame) != rf_row_digest(315_000_000, frame)

    @pytest.mark.parametrize(
        ("hz", "band"),
        [
            (433_920_000, "433.9"),
            (433_840_000, "433.9"),  # one handset, another receiver
            (434_050_000, "433.9"),
            (433_420_000, "433.4"),  # Somfy stays apart
            (433_700_000, "433.7"),  # near no centre: plain rounding
            (303_875_000, "303.9"),
            (315_120_000, "315.0"),
            (868_350_000, "868.4"),
            (27_145_000, "27.1"),
        ],
    )
    def test_the_band_snaps_to_the_centres_real_remotes_use(self, hz, band):
        assert rf_band(hz) == band

    def test_gap_alias_and_send_count_are_out(self, frame):
        one = _radio_wig(frame).signals[1]
        two = WigSignal(
            "Renamed", "", send_count=1,
            rf=WigRf(433_840_000, list(frame), frame_gap_us=None),
        )
        assert signal_row_digest(one) == signal_row_digest(two)

    def test_the_frame_is_in(self, frame):
        other = list(frame)
        other[1] -= 100
        assert rf_row_digest(433_920_000, frame) != rf_row_digest(433_920_000, other)

    def test_a_radio_digest_never_equals_an_infrared_one(self, frame):
        wig = _radio_wig(frame)
        assert signal_row_digest(wig.signals[0]) != signal_row_digest(wig.signals[1])

    def test_the_canonical_form_carries_the_band(self, frame):
        canon = json.loads(canonical_signals_json(_radio_wig(frame).signals))
        assert canon[1] == {
            "alias": "Button 1",
            "bypass_protocol": False,
            "ditto_count": 0,
            "rf": {"band": "433.9", "frame": frame, "modulation": "ook"},
        }
        # The exact Hz and the gap are not "the codes".
        assert wig_content_hash(_radio_wig(frame)) == wig_content_hash(
            _radio_wig(frame, frequency_hz=433_840_000, frame_gap_us=None)
        )


def _radio_command(keyfob, **fields) -> IRCommand:
    command = IRCommand(
        id="c1", name="Button 1", category=CommandCategory.CUSTOM,
        source=CommandSource.CAPTURED, protocol=RF_PROTOCOL, code=None,
        raw_timings=list(keyfob.frame),
    )
    command.medium = MEDIUM_RF
    command.rf_frequency_hz = 433_920_000
    command.rf_frame_gap_us = keyfob.gap_us
    command.rf_frame_gap_source = keyfob.gap_source
    command.rf_modulation = "OOK"
    command.send_count = 4
    for name, value in fields.items():
        setattr(command, name, value)
    return command


class TestExportAndAdopt:
    def _device(self, command) -> IRDevice:
        return IRDevice(
            id="dev1", name="Keyfob", device_type="other", commands=[command],
        )

    def test_export_splits_the_gap_off_the_frame(self, keyfob):
        from custom_components.hair.wig_export import wig_rf_of

        command = _radio_command(
            keyfob, raw_timings=[*keyfob.frame, -12_000],
            rf_frame_gap_us=12_000, rf_frame_gap_source=RF_GAP_MEASURED,
        )
        rf = wig_rf_of(command)
        assert rf.frame[-1] > 0 and -12_000 not in rf.frame
        assert rf.frame_gap_us == 12_000
        assert rf.modulation == "ook"

    def test_an_assumed_gap_is_not_written(self, keyfob):
        from custom_components.hair.wig_export import wig_rf_of

        frame = [v for v in keyfob.frame]
        while frame[-1] < 0:
            frame.pop()
        command = _radio_command(
            keyfob, raw_timings=frame, rf_frame_gap_source=RF_GAP_ASSUMED,
        )
        assert wig_rf_of(command).frame_gap_us is None

    def test_a_row_round_trips_through_a_wig_into_a_device(self, keyfob):
        from custom_components.hair.websocket_api import (
            _command_from_wig_signal,
        )
        from custom_components.hair.wig_export import build_wig_from_device
        from custom_components.hair.wig_identity import wig_signal_identities

        original = _radio_command(keyfob)
        built = build_wig_from_device(self._device(original))
        wig = parse_wig(serialize_wig(built.wig)).wig
        (ident,) = wig_signal_identities(wig)
        assert ident.medium == MEDIUM_RF
        command = _command_from_wig_signal(wig.signals[0], ident, set(), {}, 1)

        assert command.medium == MEDIUM_RF
        assert command.protocol == RF_PROTOCOL and command.code is None
        assert command.source == CommandSource.IMPORTED
        assert command.rf_frequency_hz == 433_920_000
        assert command.rf_frequency_source == "signal"
        assert command.rf_modulation == "OOK"
        assert command.send_count == 4
        assert command.repeat_count == 0
        fingerprint = canonical_fingerprint(RF_PROTOCOL, None, command.raw_timings)
        assert fingerprint == canonical_fingerprint(
            RF_PROTOCOL, None, original.raw_timings
        )
        assert fingerprint == ident.fingerprint
        assert command.byte_hash == ident.byte_hash == keyfob.frame_hash
        # Exported again, the row is the same row: claims survive adopt.
        again = build_wig_from_device(self._device(command)).wig.signals[0]
        assert signal_row_digest(again) == signal_row_digest(wig.signals[0])

    def test_a_measured_gap_travels_and_comes_back_measured(self, keyfob):
        from custom_components.hair.websocket_api import (
            _command_from_wig_signal,
        )
        from custom_components.hair.wig_identity import wig_rf_identity

        frame = list(keyfob.frame)
        while frame[-1] < 0:
            frame.pop()
        sig = WigSignal("B", "", rf=WigRf(433_920_000, frame, frame_gap_us=11_000))
        command = _command_from_wig_signal(sig, wig_rf_identity(sig.rf), set(), {}, 1)
        assert command.raw_timings[-1] == -11_000
        assert command.rf_frame_gap_us == 11_000
        assert command.rf_frame_gap_source == RF_GAP_MEASURED

        bare = WigSignal("B", "", rf=WigRf(433_920_000, frame))
        command = _command_from_wig_signal(bare, wig_rf_identity(bare.rf), set(), {}, 1)
        assert command.raw_timings[-1] > 0
        assert command.rf_frame_gap_source == RF_GAP_ASSUMED


class TestTheClipper:
    def _monitor(self, fake_hass):
        from custom_components.hair.signal_monitor import SignalMonitor
        from custom_components.hair.signal_store import SignalStore

        store = SignalStore(fake_hass)
        store._loaded = True
        store.schedule_save = MagicMock()
        store.async_save = AsyncMock()
        hair = MagicMock()
        hair.get_all_devices = MagicMock(return_value=[])
        return SignalMonitor(fake_hass, store, hair)

    @pytest.mark.asyncio
    async def test_a_radio_entry_becomes_a_radio_row(self, fake_hass, frame, keyfob):
        monitor = self._monitor(fake_hass)
        entry = {
            "name": "Button 1", "medium": "rf", "send_count": 3,
            "rf": {"frequency_hz": 433_920_000, "frame": frame,
                   "modulation": "ook", "frame_gap_us": 10_850},
        }
        infrared = {"name": "Power", "code": PRONTO, "send_count": 1}
        result = await monitor.import_manual_remote(
            "Keyfob", [infrared, entry, dict(entry, name="Again")],
            merge_existing=True,
        )
        assert result["imported"] == 2
        assert result["duplicates"] == 1
        radio = [s for s in monitor._signal_store.get_all_devices()[0].signals
                 if s.medium == MEDIUM_RF]
        assert len(radio) == 1
        row = radio[0]
        assert row.protocol == RF_PROTOCOL and row.code is None
        assert row.alias == "Button 1" and row.send_count == 3
        assert row.rf_frequency_hz == 433_920_000
        assert row.rf_frequency_source == "signal"
        assert row.raw_timings[-1] == -10_850
        assert row.fingerprint == canonical_fingerprint(
            RF_PROTOCOL, None, row.raw_timings
        )
        assert row.byte_hash == keyfob.frame_hash

    @pytest.mark.asyncio
    async def test_a_radio_entry_with_no_body_is_skipped(self, fake_hass):
        monitor = self._monitor(fake_hass)
        entry = {"name": "Junk", "medium": "rf",
                 "rf": {"frequency_hz": 433_920_000, "frame": [350, -350]}}
        result = await monitor.import_manual_remote("Junk", [entry])
        assert result["imported"] == 0 and result["skipped"] == 1


class TestKinds:
    def test_the_radio_kinds_are_on_the_list(self):
        from custom_components.hair.wig_format import KIND_BY_KEY

        assert KIND_BY_KEY["ceilingfan"].device_type == "fan"
        assert KIND_BY_KEY["outlet"].device_type == "switch"
        for key in ("doorbell", "gate", "sensor"):
            assert KIND_BY_KEY[key].device_type == "other"


class TestTheComb:
    def test_radio_rows_are_not_combed_and_not_lumped_together(self, frame):
        from custom_components.hair.wig_comb import _duplicate_label_findings

        other = list(frame)
        other[1] -= 200
        wig = Wig(name="Fobs", signals=[
            WigSignal("A", "", rf=WigRf(433_920_000, list(frame))),
            WigSignal("B", "", rf=WigRf(433_920_000, other)),
        ])
        # Two different radio codes have no Pronto between them, and must
        # not read as one payload under two names.
        assert _duplicate_label_findings(wig) == []
        wig.signals[1].rf = WigRf(433_920_000, list(frame))
        assert len(_duplicate_label_findings(wig)) == 1
