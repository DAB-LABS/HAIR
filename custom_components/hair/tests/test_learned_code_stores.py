"""Reading learned IR codes at rest out of another integration's store.

The Plucker's second mechanism (0.10.3). Broadlink and Tuya Local both
keep every code the user ever learned in a file under ``.storage``, and
both use the same shape: an HA Store envelope around ``subdevice ->
command name -> code``. HAIR reads them, never writes them, and turns
each code into an ordinary named signal.

Every fixture here is synthesized, so nothing in this file carries a
provenance question, but each one is SHAPED on something the probe
actually found on the test box (``import-probe-report.md`` and the
coding plan's fixture list): the Tuya store's 64464 us capture-timeout
tail, its three-frame code with ~19.4 ms gaps, its nine-byte failed
learn, and the payload whose first duration is 806 us.

TWO OF THESE TESTS ARE PINS, not coverage.

``TestAntiMisroutePin`` is the headline. A Tuya plaintext array starting
at 806 us encodes as bytes ``26 03``, and 0x26 is the Broadlink IR type
byte, so HAIR's Broadlink parser ACCEPTS that payload and returns
silently wrong timings. The store reader must never let it near that
parser -- not because it sniffs better, but because it does not sniff at
all: the filename says which integration wrote the code, and that is the
whole routing decision. The test asserts the true timings, and asserts
the Broadlink decoder was never called.

``TestTwoDoorsIdentityPin`` is the other half. The same physical
Broadlink packet reaches HAIR through a SmartIR file and through the
user's own learn history, and those two doors must agree on the code AND
on its identity, or the same button files as two rows. They agree
because they run one function, not two implementations of one spec.
"""
from __future__ import annotations

import base64
import json
import struct
from pathlib import Path

import pytest

from custom_components.hair import learned_code_stores as lcs
from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_fingerprint,
)
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.learned_code_stores import (
    RECEIPT_NO_TIMINGS,
    RECEIPT_RF,
    RECEIPT_UNREADABLE,
    discover_stores,
    read_store,
)
from custom_components.hair.wig_adapters import _smartir_code_to_pronto

# One Broadlink tick, the same 2^-15 s the shared decoder uses. Declared
# here only to BUILD fixtures; the reader never re-declares it (see the
# two-doors pin, which is what enforces that).
_TICK_US = 1_000_000 / 32_768

BROADLINK_STORE = "broadlink_remote_a4cf12880e2f_codes"
TUYA_STORE = "tuya_local_remote_eb6383fed1128526f7zzwf_codes"


# ---------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------


def _broadlink_packet(timings_us: list[int], *, type_byte: int = 0x26) -> bytes:
    """A Broadlink packet carrying these microsecond durations.

    Durations over 255 ticks use the ``0x00`` plus big-endian-pair
    escape, which is how a real RM writes a leader mark or a frame gap.
    """
    payload = bytearray()
    for value in timings_us:
        ticks = max(1, round(abs(value) / _TICK_US))
        if ticks > 255:
            payload += bytes([0x00, (ticks >> 8) & 0xFF, ticks & 0xFF])
        else:
            payload.append(ticks)
    header = bytes(
        [type_byte, 0x00, len(payload) & 0xFF, (len(payload) >> 8) & 0xFF]
    )
    return header + bytes(payload)


def _broadlink_code(timings_us: list[int], *, type_byte: int = 0x26) -> str:
    return base64.b64encode(
        _broadlink_packet(timings_us, type_byte=type_byte)
    ).decode("ascii")


def _tuya_code(durations: list[int]) -> str:
    """Base64 of a plain little-endian uint16 array, Tuya Local's form."""
    return base64.b64encode(
        struct.pack("<" + "H" * len(durations), *durations)
    ).decode("ascii")


# A textbook NEC-shaped burst: 9006/4399 leader then 560 us units, the
# shape the probe found on the real store's ``test_remote/power_button``.
def _nec_shaped() -> list[int]:
    out = [9006, 4399]
    for bit in (1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1):
        out += [560, 1690 if bit else 560]
    out.append(560)
    return out


# Every stored Tuya code ends on the learn window's own timeout gap.
_TUYA_TAIL = 64464


def _write_store(root: Path, name: str, data: dict) -> Path:
    storage = root / ".storage"
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / name
    path.write_text(
        json.dumps(
            {"version": 1, "minor_version": 1, "key": name, "data": data},
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_flags(root: Path, name: str, data: dict) -> Path:
    return _write_store(root, name, data)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """A config directory holding one store of each kind, plus junk.

    Broadlink store: a single-code command, a toggle pair, an RF packet,
    a packet with an escaped long duration, an unknown first byte, and a
    ``_flags`` sibling.

    Tuya store: an NEC-shaped array, a three-frame array with ~19.4 ms
    gaps, THE MISROUTE PAYLOAD, and a nine-byte failed learn. Every code
    ends on the 64464 us capture-timeout gap except the failed learn,
    which never got that far.
    """
    _write_store(
        tmp_path,
        BROADLINK_STORE,
        {
            "tv": {
                "power": _broadlink_code([9000, -4500, 560, -560, 560]),
                "mute": [
                    _broadlink_code([8900, -4400, 600, -600, 600]),
                    _broadlink_code([8900, -4400, 600, -1700, 600]),
                ],
            },
            "gate": {
                "open": _broadlink_code([400, -400, 400], type_byte=0xB2),
                "junk": base64.b64encode(
                    bytes([0x99, 0x00, 0x02, 0x00, 0x10, 0x10])
                ).decode("ascii"),
            },
        },
    )
    _write_flags(tmp_path, "broadlink_remote_a4cf12880e2f_flags", {"tv": 1})
    _write_store(
        tmp_path,
        TUYA_STORE,
        {
            "test_remote": {
                "power_button": _tuya_code([*_nec_shaped(), _TUYA_TAIL]),
            },
            "candles": {
                # Three frames, ~19.4 ms between them, the shape the
                # probe's ``candles/ON`` has.
                "ON": _tuya_code(
                    [560, 560, 560, 19400] * 3 + [560, _TUYA_TAIL]
                ),
                # THE MISROUTE PAYLOAD. First duration 806 us packs as
                # bytes 26 03, which the Broadlink parser accepts.
                "pwr_on": _tuya_code(
                    [806, 806, 806, 1600, 806, 806, 806, _TUYA_TAIL]
                ),
                # Nine bytes of near-zero from a learn that never
                # completed. A real one of these was on the box.
                "OFF": base64.b64encode(b"\x00" * 9).decode("ascii"),
            },
        },
    )
    _write_store(tmp_path, "tuya_local_remote_eb6383fed1128526f7zzwf_flags", {})
    return tmp_path


@pytest.fixture
def corrupt_dir(tmp_path: Path) -> Path:
    """One unreadable store per prefix, beside one healthy store."""
    storage = tmp_path / ".storage"
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "broadlink_remote_deadbeef0001_codes").write_text(
        "{not json at all", encoding="utf-8"
    )
    (storage / "tuya_local_remote_broken_codes").write_text(
        json.dumps({"version": 1, "key": "x", "data": "not a mapping"}),
        encoding="utf-8",
    )
    _write_store(
        tmp_path,
        BROADLINK_STORE,
        {"tv": {"power": _broadlink_code([9000, -4500, 560, -560, 560])}},
    )
    return tmp_path


def _by_name(codes, name):
    return next(c for c in codes if c.command_name == name)


# ---------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------


class TestDiscoverStores:
    def test_finds_both_prefixes_with_counts(self, config_dir):
        stores = discover_stores(config_dir)
        assert [s.integration for s in stores] == ["broadlink", "tuya_local"]

        broadlink = stores[0]
        assert broadlink.store_id == "a4cf12880e2f"
        assert broadlink.subdevices == 2
        # power, mute, open, junk -- four command names.
        assert broadlink.codes == 4
        # Packets, not names: the toggle pair is two IR packets.
        assert broadlink.ir_codes == 3
        assert broadlink.rf_codes == 1
        assert broadlink.parse_error is None

        tuya = stores[1]
        assert tuya.store_id == "eb6383fed1128526f7zzwf"
        assert tuya.subdevices == 2
        assert tuya.codes == 4
        assert tuya.rf_codes == 0

    def test_flags_siblings_are_not_listed_as_stores(self, config_dir):
        paths = [Path(s.path).name for s in discover_stores(config_dir)]
        assert all(p.endswith("_codes") for p in paths)

    def test_corrupt_store_is_reported_not_raised(self, corrupt_dir):
        stores = discover_stores(corrupt_dir)
        broken = [s for s in stores if s.parse_error]
        healthy = [s for s in stores if not s.parse_error]
        assert len(broken) == 2
        assert all(s.parse_error == "Could not read this file" for s in broken)
        # One bad store never removes a good one from the list.
        assert len(healthy) == 1
        assert healthy[0].store_id == "a4cf12880e2f"

    def test_missing_storage_directory_is_empty_not_an_error(self, tmp_path):
        assert discover_stores(tmp_path / "nowhere") == []

    def test_to_dict_falls_back_to_the_store_id_for_a_name(self, config_dir):
        payload = discover_stores(config_dir)[0].to_dict()
        assert payload["friendly_name"] == "a4cf12880e2f"
        assert payload["error"] is None


# ---------------------------------------------------------------------
# THE ANTI-MISROUTE PIN
# ---------------------------------------------------------------------


class TestAntiMisroutePin:
    """A Tuya payload the Broadlink parser would happily misread.

    ``26 03`` is 806 us little-endian AND the Broadlink IR type byte.
    The reader must produce 806, and must not have asked the Broadlink
    decoder anything.
    """

    def test_the_payload_really_is_ambiguous(self):
        """Guard the fixture itself: prove the hazard is real.

        If this ever stops being true the pin below stops proving
        anything, so it is asserted rather than assumed.
        """
        code = _tuya_code([806, 806, 806, 1600, 806, 806, 806, _TUYA_TAIL])
        packet = base64.b64decode(code)
        assert packet[0] == 0x26
        assert packet[1] == 0x03
        # And the Broadlink door does NOT refuse it -- it converts it.
        from custom_components.hair.wig_adapters import (
            broadlink_packet_to_pronto,
        )

        assert broadlink_packet_to_pronto(packet) is not None

    def test_tuya_store_code_imports_as_its_true_timings(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "tuya_local"
        )
        code = _by_name(read_store(info), "pwr_on")
        assert code.receipt is None
        # The true array, marks positive and spaces negative, with the
        # capture-timeout gap dropped.
        assert code.timings == [806, -806, 806, -1600, 806, -806, 806]
        assert code.timings[0] == 806

    def test_the_broadlink_decoder_is_never_called_for_a_tuya_store(
        self, config_dir, monkeypatch
    ):
        calls: list[str] = []

        def _tripwire(value):
            calls.append(value)
            raise AssertionError(
                "the Broadlink decoder was handed a Tuya store payload"
            )

        monkeypatch.setattr(lcs, "broadlink_b64_to_pronto", _tripwire)
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "tuya_local"
        )
        codes = read_store(info)
        assert calls == []
        assert _by_name(codes, "pwr_on").timings[0] == 806

    def test_a_broadlink_store_still_routes_to_the_broadlink_decoder(
        self, config_dir, monkeypatch
    ):
        """The mirror image: routing is by store, in both directions."""
        seen: list[str] = []
        real = lcs.broadlink_b64_to_pronto

        def _spy(value):
            seen.append(value)
            return real(value)

        monkeypatch.setattr(lcs, "broadlink_b64_to_pronto", _spy)
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "broadlink"
        )
        read_store(info)
        assert seen, "the Broadlink store did not reach the Broadlink decoder"


# ---------------------------------------------------------------------
# THE TWO-DOORS IDENTITY PIN
# ---------------------------------------------------------------------


class TestTwoDoorsIdentityPin:
    """One physical code, two import doors, one identity.

    A code learned on a Broadlink years ago can reach HAIR either as
    base64 inside a SmartIR file or straight out of the user's own
    ``.storage``. If the two doors used different tick constants -- the
    thing the ticket was worried about -- the same button would land in
    two identity bins and file as two rows. They do not, because both
    call one function.
    """

    def test_same_packet_same_pronto_same_identity(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "broadlink"
        )
        plucked = _by_name(read_store(info), "power")

        raw_value = json.loads(
            (Path(info.path)).read_text(encoding="utf-8")
        )["data"]["tv"]["power"]
        smartir_pronto, reason = _smartir_code_to_pronto(raw_value, "base64")

        assert reason is None
        assert smartir_pronto is not None

        # The code itself, byte for byte.
        assert plucked.pronto == smartir_pronto

        # The timings behind it.
        store_timings = plucked.timings
        smartir_timings = list(ProntoCommand(smartir_pronto).get_raw_timings())
        assert store_timings == smartir_timings
        assert store_timings[0] == pytest.approx(9000, abs=40)

        # And the identity HAIR would file it under, both tiers.
        assert canonical_fingerprint(
            "PRONTO", plucked.pronto, []
        ) == canonical_fingerprint("PRONTO", smartir_pronto, [])
        assert canonical_byte_hash(plucked.pronto) == canonical_byte_hash(
            smartir_pronto
        )


# ---------------------------------------------------------------------
# Payload behaviour
# ---------------------------------------------------------------------


class TestBroadlinkPayloads:
    def test_rf_codes_are_receipted_never_imported(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "broadlink"
        )
        code = _by_name(read_store(info), "open")
        assert code.pronto is None
        assert code.receipt_kind == RECEIPT_RF
        assert "RF" in code.receipt
        # House rule: no em-dashes in anything a user can read. The
        # codepoint is spelled out so this file does not contain one.
        assert "--" in code.receipt
        assert "\u2014" not in code.receipt

    def test_unknown_first_byte_is_receipted_with_the_byte(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "broadlink"
        )
        code = _by_name(read_store(info), "junk")
        assert code.pronto is None
        assert code.receipt_kind == RECEIPT_UNREADABLE
        assert "0x99" in code.receipt

    def test_toggle_pair_imports_both_packets_under_one_base_name(
        self, config_dir
    ):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "broadlink"
        )
        codes = read_store(info)
        first = _by_name(codes, "mute")
        alt = _by_name(codes, "mute (alt)")
        assert first.base_command_name == alt.base_command_name == "mute"
        assert first.is_toggle_alt is False
        assert alt.is_toggle_alt is True
        assert first.pronto and alt.pronto
        assert first.pronto != alt.pronto
        assert lcs.count_toggle_pairs(codes) == 1

    def test_an_escaped_long_duration_survives_the_round_trip(self):
        """A leader mark is over 255 ticks, so it rides the escape."""
        value = _broadlink_code([9000, -4500, 560, -560, 560])
        pronto = lcs.broadlink_b64_to_pronto(value)
        timings = list(ProntoCommand(pronto).get_raw_timings())
        assert timings[0] == pytest.approx(9000, abs=40)
        assert timings[1] == pytest.approx(-4500, abs=40)

    def test_carrier_is_assumed_and_recorded_as_assumed(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "broadlink"
        )
        code = _by_name(read_store(info), "power")
        assert code.frequency == 38000
        assert code.carrier_assumed is True


class TestTuyaPayloads:
    def test_the_capture_timeout_tail_is_stripped(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "tuya_local"
        )
        code = _by_name(read_store(info), "power_button")
        assert _TUYA_TAIL not in [abs(t) for t in code.timings]
        # Ends on a mark, like every other code in HAIR.
        assert code.timings[-1] > 0
        assert code.timings[0] == 9006
        assert code.timings[1] == -4399

    def test_multi_frame_codes_pass_through_whole(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "tuya_local"
        )
        code = _by_name(read_store(info), "ON")
        gaps = [t for t in code.timings if t == -19400]
        assert len(gaps) == 3, "the inter-frame gaps were eaten"

    def test_a_failed_learn_receipts_instead_of_importing(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "tuya_local"
        )
        code = _by_name(read_store(info), "OFF")
        assert code.pronto is None
        assert code.receipt_kind == RECEIPT_NO_TIMINGS
        assert code.receipt == "no usable timings"

    def test_carrier_is_assumed_and_recorded_as_assumed(self, config_dir):
        info = next(
            s for s in discover_stores(config_dir) if s.integration == "tuya_local"
        )
        code = _by_name(read_store(info), "power_button")
        assert code.frequency == 38000
        assert code.carrier_assumed is True


class TestReadOnly:
    """HAIR never writes to another integration's store. Ever."""

    def test_reading_leaves_every_byte_and_every_mtime_alone(self, config_dir):
        storage = config_dir / ".storage"
        before = {
            p.name: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(storage.iterdir())
        }
        for info in discover_stores(config_dir):
            read_store(info)
        after = {
            p.name: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(storage.iterdir())
        }
        assert after == before

    def test_a_store_that_vanished_between_list_and_read_is_empty(
        self, config_dir
    ):
        info = discover_stores(config_dir)[0]
        Path(info.path).unlink()
        assert read_store(info) == []
