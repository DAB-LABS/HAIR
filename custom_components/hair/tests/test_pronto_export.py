"""The copy-path terminator (GH #144), and what it must not disturb.

Stored codes end in a zero-length trailing space. That is deliberate
and load-bearing: the constructor strip has been part of signal
identity since 0.9.8, and the transmit boundary re-adds a bounded
terminator on the way to the emitter. Nobody who only sends a code
notices. People who COPY one do, because the code they get has no
inter-frame gap at all and other tools read that as malformed.

So every surface that shows a code to a person for reading serves the
export form, and the storage form stays what it was.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_fingerprint,
    canonical_pronto,
)
from custom_components.hair.ir_command import (
    TERMINATOR_SPACE_US,
    ProntoCommand,
    pronto_for_export,
)
from custom_components.hair.models import (
    CommandSource,
    IRCommand,
    IRDevice,
    UnknownSignal,
)
from custom_components.hair.pronto_validator import validate_pronto
from custom_components.hair.wig_format import parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
_PRONTO_CLOCK_US = 0.241246


def _stored_code() -> str:
    """A real canonical code off a real wig, in the stored form."""
    wig = parse_wig(
        (FIXTURES / "wigs"
         / "dreo-fan-dr-haf004s-perfect-fit.wig.json").read_text()
    ).wig
    code = next(s.pronto for s in wig.signals if s.alias == "Power")
    canonical = canonical_pronto(code)
    assert canonical is not None
    return canonical


def _period_us(code: str) -> float:
    return int(code.split()[1], 16) * _PRONTO_CLOCK_US


class TestTheExportCarriesARealTerminator:
    def test_the_stored_form_ends_in_a_zero_gap(self):
        """The premise. If this ever stops being true the export helper
        is solving a problem that no longer exists."""
        assert _stored_code().split()[-1] == "0000"

    def test_the_export_ends_in_the_fifty_millisecond_word(self):
        stored = _stored_code()
        exported = pronto_for_export(stored)
        last = int(exported.split()[-1], 16)
        # Quantized to the carrier period, so compared as microseconds
        # rather than as a magic word: a different carrier is a
        # different word for the same 50ms.
        period = _period_us(stored)
        assert abs(round(last * period) - TERMINATOR_SPACE_US) < period

    def test_nothing_else_about_the_code_moves(self):
        stored = _stored_code()
        exported = pronto_for_export(stored)
        assert exported.split()[:-1] == stored.split()[:-1]
        assert len(exported.split()) == len(stored.split())

    def test_it_is_the_same_waveform(self):
        """Same parsed timings: the terminator is dropped again on the
        way in, which is what makes the round trip below possible."""
        stored = _stored_code()
        exported = pronto_for_export(stored)
        assert (
            ProntoCommand(exported).get_raw_timings()
            == ProntoCommand(stored).get_raw_timings()
        )

    def test_exporting_an_export_stacks_nothing(self):
        stored = _stored_code()
        once = pronto_for_export(stored)
        assert pronto_for_export(once) == once

    def test_an_oversized_stored_trailing_space_still_clamps(self):
        """The existing _normalize_trailing_space behaviour, reached
        through the export rather than restated: a captured Broadlink
        RM's ~102ms learning timeout comes out bounded."""
        stored = _stored_code()
        period = _period_us(stored)
        words = stored.split()
        words[-1] = f"{round(200_000 / period):04X}"
        oversized = " ".join(words)
        exported = pronto_for_export(oversized)
        last = int(exported.split()[-1], 16)
        assert abs(round(last * period) - TERMINATOR_SPACE_US) < period

    def test_a_code_that_will_not_parse_raises_rather_than_guesses(self):
        with pytest.raises(ValueError):
            pronto_for_export("not a pronto code")


class TestTheRoundTripKeepsTheIdentity:
    """THE LOAD-BEARING INVARIANT. A person copies a code out of the
    panel and pastes it back somewhere else in HAIR; that must land on
    the same signal, not a second one.

    What the paste doors guarantee is identity, not stored text: they
    compute the fingerprint and the byte hash on the canonical form and
    store the code exactly as pasted (identity.py's canonical-form
    block, and the comment at device_manager saying so). So the pins
    here hold identity, and the one below holds the text difference so
    that it is recorded rather than discovered.
    """

    def test_the_byte_hash_is_unchanged(self):
        stored = _stored_code()
        exported = pronto_for_export(stored)
        assert canonical_byte_hash(exported) == canonical_byte_hash(stored)

    def test_the_fingerprint_is_unchanged(self):
        stored = _stored_code()
        exported = pronto_for_export(stored)
        assert (
            canonical_fingerprint("PRONTO", exported, [])
            == canonical_fingerprint("PRONTO", stored, [])
        )

    def test_the_canonical_form_of_an_export_is_the_stored_form(self):
        """Byte-identical, which is what makes the paste a no-op
        everywhere identity is computed."""
        stored = _stored_code()
        assert canonical_pronto(pronto_for_export(stored)) == stored

    def test_the_paste_doors_validate_it_unchanged(self):
        """It survives the gate every paste goes through."""
        exported = pronto_for_export(_stored_code())
        result = validate_pronto(exported)
        assert result.valid
        assert result.normalized == exported

    def test_the_stored_text_of_a_pasted_export_keeps_the_terminator(self):
        """RECORDED, NOT WISHED AWAY. The doors store the code as
        pasted, so a pasted export differs from the stored form by
        exactly the terminator word and by nothing else. Identity is
        untouched, which is why this is a difference rather than a
        defect; it is pinned so that a later change to the doors is a
        deliberate change and not a surprise."""
        stored = _stored_code()
        exported = pronto_for_export(stored)
        as_stored_again = validate_pronto(exported).normalized
        assert as_stored_again != stored
        assert as_stored_again.split()[:-1] == stored.split()[:-1]
        assert canonical_byte_hash(as_stored_again) == canonical_byte_hash(
            stored)


class TestThePayloadsServeIt:
    """The surfaces are fed from to_dict, so the derivation lives there
    once rather than at each of them."""

    def test_a_command_payload_carries_the_export_form(self):
        stored = _stored_code()
        command = IRCommand(
            name="Power", protocol="PRONTO", code=stored,
            source=CommandSource.CAPTURED,
        )
        payload = command.to_dict()
        assert payload["code"] == stored
        assert payload["code_export"] == pronto_for_export(stored)

    def test_a_signal_payload_carries_it_too(self):
        stored = _stored_code()
        signal = UnknownSignal(
            fingerprint="SL:xx", protocol="PRONTO", code=stored)
        payload = signal.to_dict()
        assert payload["code"] == stored
        assert payload["code_export"] == pronto_for_export(stored)

    def test_it_is_derived_and_never_stored(self):
        """Same contract as sl_pattern: recomputed on every write and
        dropped on the way back in, so a stale one cannot outlive the
        code it described."""
        stored = _stored_code()
        command = IRCommand(name="Power", protocol="PRONTO", code=stored)
        payload = command.to_dict()
        payload["code_export"] = "0000 DEAD BEEF 0000"
        back = IRCommand.from_dict(payload)
        assert back.to_dict()["code_export"] == pronto_for_export(stored)
        assert "code_export" not in back._extra

        signal = UnknownSignal(
            fingerprint="SL:xx", protocol="PRONTO", code=stored)
        spayload = signal.to_dict()
        spayload["code_export"] = "0000 DEAD BEEF 0000"
        sback = UnknownSignal.from_dict(spayload)
        assert "code_export" not in sback._extra

    def test_a_row_with_nothing_to_export_says_nothing(self):
        """A non-Pronto row, and a row whose code will not parse. The
        surfaces fall back to code, which is what they showed before
        this existed."""
        raw = IRCommand(name="Raw", protocol="RAW", code="whatever")
        assert "code_export" not in raw.to_dict()
        broken = IRCommand(name="Broken", protocol="PRONTO", code="zzzz")
        assert "code_export" not in broken.to_dict()
        empty = IRCommand(name="Empty", protocol="PRONTO", code=None)
        assert "code_export" not in empty.to_dict()

    def test_a_copy_derives_its_own_rather_than_carrying_one(self):
        """The clone roster walks attributes, and a derived key has none.
        The copy asks the code again, which is the only way it can be
        right about a code the copy is free to change later."""
        stored = _stored_code()
        device = IRDevice(name="Source")
        device.commands.append(IRCommand(
            name="Power", protocol="PRONTO", code=stored,
        ))
        copy = device.clone("Copy")
        assert "code_export" not in copy.commands[0]._extra
        assert copy.commands[0].to_dict()["code_export"] == (
            pronto_for_export(stored))


class TestTheWigFileIsUntouched:
    """Wig text is bound by digests and Perfect Fit signatures. The
    export form must never reach it."""

    def test_wig_export_stays_canonical(self):
        from custom_components.hair.wig_export import build_wig_from_device

        stored = _stored_code()
        device = IRDevice(name="Dreo Fan")
        device.commands.append(IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=stored,
        ))

        wig = build_wig_from_device(device).wig
        assert wig.signals[0].pronto.split()[-1] == "0000"
        assert wig.signals[0].pronto.split()[-1] != pronto_for_export(
            stored).split()[-1]

    def test_the_format_doc_says_why(self):
        doc = (Path(__file__).parents[3] / "docs" / "wig-format.md").read_text(
            encoding="utf-8")
        assert "zero trailing gap by design" in doc
        assert "comes from the HAIR panel" in doc


class TestTheRepairNoteCarriesOnlyWhatItHas:
    """The tidy-up rider. A Use It Anyway on a press the reader could
    not read at all wrote three empty containers beside the
    attestation."""

    def _record(self, disagreed):
        from custom_components.hair.tangles import build_provenance

        # The builder reads exactly two things off these: whether the
        # lattice was readable, and which cell the finding was about.
        # An unreadable lattice is the case the rider is FOR, so that is
        # the one the stand-ins describe.
        lattice = SimpleNamespace(readable=False)
        row = SimpleNamespace(
            target=SimpleNamespace(key="heat_cool/medium/off/28"),
            classes=["off_by_one"],
        )
        return build_provenance(
            source="capture",
            prior_pronto=_stored_code(),
            lattice=lattice,
            row=row,
            tested=True,
            sends_fired=1,
            disagreed=disagreed,
        )

    def test_a_disagreement_with_content_keeps_every_key(self):
        record = self._record({
            "reads_as": {"temperature": 29.0},
            "claims": {"temperature": 25.0},
            "mismatches": ["temperature"],
        })
        note = record["reading_disagreed"]
        assert note["user_attested"] is True
        assert note["reads_as"] == {"temperature": 29.0}
        assert note["claims"] == {"temperature": 25.0}
        assert note["mismatches"] == ["temperature"]

    def test_an_empty_declaration_writes_only_the_attestation(self):
        record = self._record({
            "reads_as": {}, "claims": {}, "mismatches": [],
        })
        assert record["reading_disagreed"] == {"user_attested": True}

    def test_a_declaration_with_nothing_at_all_is_the_same(self):
        record = self._record({})
        assert record["reading_disagreed"] == {"user_attested": True}

    def test_a_partial_reading_keeps_the_half_it_has(self):
        record = self._record({
            "reads_as": {"temperature": 29.0}, "claims": {},
            "mismatches": [],
        })
        note = record["reading_disagreed"]
        assert note == {
            "user_attested": True, "reads_as": {"temperature": 29.0},
        }

    def test_no_declaration_writes_no_note_at_all(self):
        record = self._record(None)
        assert "reading_disagreed" not in record
