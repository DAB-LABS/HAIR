"""The no-steal census: the protocol pack's licence to sit where it does.

Three decoders that read the NEC1 frame shape arrive in one patch, two
of them high in the probe order. The argument that none of them takes a
frame belonging to something else is not an argument, it is this file:
a label recorded for every capture in the repo BEFORE they existed, and
asserted afterwards.

WHAT MAKES IT ABLE TO FAIL. Review round 1 found the first draft could
not: it asserted that rows which already had an identity kept it, and
filed rows that gained one under "informational". Review round 2 found
the second draft could be walked around: a decoder planted ahead of
strict NEC stole every NEC row, and renaming the two fixtures that hold
most of them plus adding one line to the four modules that hold the rest
moved every stolen row to a key the baseline had never seen, which was
"new" and therefore not a failure. Here:

- ``raw`` is a label. A row nothing decoded is recorded as ``raw``, and
  a row that was ``raw`` and is now claimed FAILS unless its fixture is
  on ``EXPECTED_CLAIMS`` below, by path and by the exact label.
- A row whose label changed between two protocols fails, with the same
  allowlist and nothing wider: the one entry exists because the Apple
  fixture's rows genuinely move from NEC to APPLE.
- Rows are keyed by ``(source, index)``. A later phase adding fixtures
  must not read as every later row changing, so a key the baseline has
  never seen is reported and does not fail, while a key it has whose
  label moved always does.
- A KEY THAT VANISHES FAILS unless ``RETIRED_KEYS`` names it with a
  reason. Inline rows are keyed by module plus a digest of their
  content, so editing a test cannot orphan its rows; fixture rows are
  keyed by path, so a rename is noticed.
- The round 2 attack is a self-test at the bottom of this file, run
  against a doctored copy of the corpus with the planted decoder
  registered. It has to fail the census, on both legs.

THE BASELINE'S PROVENANCE IS CHECKABLE, not asserted. It was generated
by ``tests/tools/gen_decode_census.py`` run against a pristine checkout
of the base commit, which is recorded inside the file along with the
library version the walk ran against. Re-run that script at that commit
to reproduce it; a baseline reverse-engineered from the new behaviour
would not survive that.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from custom_components.hair.tests.census_corpus import (
    ROOT_CONFTEST,
    TESTS,
    census,
    corpus,
    lost_rows,
    moved_rows,
    newly_claimed_rows,
    source_of,
    sources,
    vanished_rows,
)
from custom_components.hair.tests.leg import BASELINE_SUFFIX

#: The baseline for the leg this run is on. See ``tests/leg.py``: the
#: strict NEC decoder has no local polyfill, so the two legs decode
#: different corpora and one shared baseline would be vacuous on the
#: bare one.
BASELINE_PATH = (
    Path(__file__).parent / "fixtures" / f"decode-census-v0150{BASELINE_SUFFIX}.json"
)

#: The ONLY places a row is allowed to go from unclaimed, or from one
#: protocol to another, and exactly what it is allowed to become.
#:
#: By fixture path and expected label, nothing wider. A family name here
#: is a statement that the pack is meant to claim this file, and every
#: entry needs a reason a reader can check.
EXPECTED_CLAIMS: dict[str, set[str]] = {
    # The eight parsed lines of the repo's Apple remote fixture. They
    # read as NEC before the pack for a reason that was a bug: the
    # Flipper NECext builder threw the file's fourth byte away and wrote
    # the complement of the third in its place, so what HAIR stored was
    # a frame the remote never sends. With the byte kept, the rows are
    # what the file always said they were. Their address is 0x87EE and
    # their parity rule holds, which is what APPLE requires.
    "adapters:flipper_parsed_Apple_TV_Gen3_v2.ir": {"APPLE"},
}

#: Baseline keys that are allowed to be absent from the walk, each with
#: the reason. A fixture deleted or renamed on purpose goes here by its
#: old key; nothing else does. Empty means every baseline row is still
#: walked, which is the state this file is in.
RETIRED_KEYS: dict[str, str] = {}


def _baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


class TestCensusCorpus:
    """The walk itself, before anything is asserted about labels."""

    def test_the_corpus_is_not_empty_and_has_no_duplicate_keys(self):
        rows = corpus()
        assert len(rows) > 3000, "the corpus collapsed; the walk is broken"
        keys = [row.key for row in rows]
        assert len(keys) == len(set(keys))

    def test_the_walk_covers_fixtures_and_inline_captures_and_adapters(self):
        """All three halves are present.

        Named because each was missed by an earlier draft: the plan's
        corpus listed four test modules where the repo has dozens, and
        the first census here walked file bytes only, so a Flipper
        ``parsed`` line -- which has no timings until a builder renders
        one -- was invisible.
        """
        walked = sources()
        assert any(s.startswith("fixtures/") for s in walked)
        assert any(s.startswith("TEST:") for s in walked)
        assert any(s.startswith("adapters:") for s in walked)
        inline = [s for s in walked if s.startswith("TEST:")]
        assert len(inline) >= 18, (
            f"only {len(inline)} test modules contributed inline captures; "
            "the review counted at least 18 carrying NEC-shaped leaders"
        )

    def test_inline_keys_survive_a_shifted_line(self, tmp_path):
        """The keying rule from round 2, stated as a test.

        Copy one module that carries inline NEC captures, put a line
        above everything, and every one of its rows keeps its key.
        """
        from custom_components.hair.tests.census_corpus import _inline_rows

        original = TESTS / "test_event_parser.py"
        before = {row.key for row in _inline_rows(original)}
        assert before, "the module chosen for this test carries no rows"
        shifted = tmp_path / original.name
        shifted.write_text(
            "# a line that moves everything below it\n"
            + original.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        after = {row.key for row in _inline_rows(shifted)}
        assert after == before

    def test_baseline_records_its_own_provenance(self):
        data = _baseline()
        assert data["base_commit"], "the baseline does not say what it is of"
        assert data["row_count"] == len(data["rows"])


class TestNoSteal:
    """Every row's label, against the baseline."""

    def test_no_row_changes_protocol(self):
        """A row that decoded as X must still decode as X.

        The allowlist reaches this only by fixture path and exact label,
        because the Apple fixture's rows genuinely move from NEC to
        APPLE; anywhere else a protocol moving to another protocol is a
        steal, and it is the must-not-change list stated as an assertion.
        """
        offenders = moved_rows(_baseline()["rows"], census(), EXPECTED_CLAIMS)
        assert not offenders, "\n".join(
            f"{key}: {was} -> {is_now}" for key, was, is_now in offenders
        )

    def test_no_raw_row_becomes_claimed_off_the_allowlist(self):
        """The false-positive class, asserted rather than reported.

        A row nothing could read, that a new decoder now reads, is what
        a decoder finding a frame inside a blob looks like. Allowed only
        where a fixture is named above and only for the label named
        with it.
        """
        offenders = newly_claimed_rows(
            _baseline()["rows"], census(), EXPECTED_CLAIMS
        )
        assert not offenders, "\n".join(
            f"{key}: was unclaimed, now {label}" for key, label in offenders
        )

    def test_no_claimed_row_becomes_raw(self):
        """The opposite failure: a decoder that stopped reading a frame."""
        base = _baseline()["rows"]
        lost = lost_rows(base, census())
        assert not lost, "\n".join(f"{key}: {base[key]} -> raw" for key in lost)

    def test_no_baseline_row_vanishes_from_the_walk(self, capsys):
        """A row the walk no longer finds is a row nobody is checking.

        This is the assertion round 2 found missing. A renamed fixture
        or a retired module takes its rows out of every comparison
        above, so the absence itself has to fail, unless the key is
        retired by name in ``RETIRED_KEYS`` with a reason, in which case
        the retirement is printed rather than hidden.
        """
        base = _baseline()["rows"]
        now = census()
        retired = sorted(k for k in RETIRED_KEYS if k in base and k not in now)
        if retired:
            print(f"census: {len(retired)} retired row(s)")
            for key in retired:
                print(f"  retired {key}: {RETIRED_KEYS[key]}")
        stale = sorted(k for k in RETIRED_KEYS if k in now)
        assert not stale, (
            "RETIRED_KEYS names rows the walk still finds; drop the entries: "
            + ", ".join(stale)
        )
        vanished = vanished_rows(base, now, RETIRED_KEYS)
        assert not vanished, (
            f"{len(vanished)} baseline row(s) are no longer walked and are "
            "not retired by name:\n" + "\n".join(vanished[:20])
        )

    def test_every_allowlisted_fixture_actually_changed(self):
        """The allowlist cannot rot into a blanket permission.

        An entry naming a fixture that no longer changes is an entry
        nobody is checking, so it has to be deleted rather than left to
        widen quietly.

        "Changed" covers two shapes, because the two legs see this
        differently. With the library the Apple fixture's rows existed
        before and moved from NEC to APPLE. Without it, the old NECext
        builder needed the library and produced nothing, so the same
        rows are absent from that leg's baseline and ARRIVE rather than
        move. Both are the pack doing what it said; a fixture where
        neither happens is an allowlist entry with nothing behind it.
        """
        base = _baseline()["rows"]
        now = census()
        for source, labels in EXPECTED_CLAIMS.items():
            changed = {
                now[key]
                for key in now
                if source_of(key) == source
                and base.get(key) != now[key]
            }
            assert changed, (
                f"{source} is allowlisted but nothing there changed"
            )
            assert changed <= labels, (
                f"{source} changed to {changed - labels}, not allowlisted"
            )

    def test_new_rows_are_reported_not_failed(self, capsys):
        """A fixture added later is news, not a regression."""
        base = _baseline()["rows"]
        now = census()
        added = sorted(key for key in now if key not in base)
        if added:
            print(f"census: {len(added)} row(s) new since the baseline")
            for key in added[:20]:
                print(f"  new {key} -> {now[key]}")
        assert True


# ---------------------------------------------------------------------------
# The census is only a licence if it can refuse one
# ---------------------------------------------------------------------------


class _EvilCommand:
    """The round 2 attack decoder: claims every complement-valid NEC frame.

    Built on the verbatim reader so it works on both legs, and gated on
    the complement so it takes exactly the rows strict NEC owns, which
    is the steal the census exists to catch. Registered AHEAD of ``nec``
    by the self-test and nowhere else.
    """

    @classmethod
    def from_raw_timings(cls, timings):
        from custom_components.hair.decoders.nec_variant import (
            NECNoComplementCommand,
        )

        got = NECNoComplementCommand.from_raw_timings(timings)
        if got is None or not got.complement_holds:
            return None
        return got


def _plant_evil_ahead_of_nec(monkeypatch) -> None:
    from custom_components.hair import protocol_decode

    entry = (
        "evil", None, "_EvilCommand", __name__, True,
        lambda cmd: ("EVIL", int(cmd.address), int(cmd.command), None),
        lambda cls, label, address, command, extras: None,
        ("EVIL",),
    )
    monkeypatch.setattr(
        protocol_decode, "_REGISTRATIONS",
        (entry, *protocol_decode._REGISTRATIONS),
    )
    protocol_decode._reset_registry_for_tests()


#: The two fixtures and four modules the round 2 attack touched. They
#: are the ones that hold the corpus's NEC rows, which is why the attack
#: chose them; if the corpus moves, move these with it.
ATTACK_RENAMES = (
    ("fixtures/nec_test_fixtures.json", "fixtures/nec_test_fixtures_v2.json"),
    (
        "fixtures/adapters/girr_irscrutinizer_export.girr",
        "fixtures/adapters/girr_irscrutinizer_export_v2.girr",
    ),
)
ATTACK_EDITS = (
    "test_event_parser.py",
    "test_send_spacing_doors.py",
    "test_send_spacing_field.py",
    "test_wig_identity.py",
)


def _doctored_corpus(tmp_path: Path) -> dict[str, Path]:
    """A copy of the corpus with the round 2 attack's file changes applied."""
    tests = tmp_path / "tests"
    shutil.copytree(
        TESTS, tests, ignore=shutil.ignore_patterns("__pycache__", "tools")
    )
    conftest = tmp_path / "conftest.py"
    shutil.copy(ROOT_CONFTEST, conftest)
    for old, new in ATTACK_RENAMES:
        assert (tests / old).is_file(), f"{old} is gone; update ATTACK_RENAMES"
        (tests / old).rename(tests / new)
    for name in ATTACK_EDITS:
        path = tests / name
        assert path.is_file(), f"{name} is gone; update ATTACK_EDITS"
        path.write_text(
            "# one line, above everything\n" + path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return {
        "fixtures": tests / "fixtures",
        "tests": tests,
        "root_conftest": conftest,
    }


class TestCensusCanFail:
    """A test suite that has never seen its own failure mode is a suite
    that might be asserting nothing, which is precisely what rounds 1
    and 2 found the earlier drafts doing."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self):
        from custom_components.hair import protocol_decode

        yield
        protocol_decode._reset_registry_for_tests()

    def test_a_planted_decoder_alone_is_caught(self, monkeypatch):
        """Registry-level, not dict-level: the walk has to see it."""
        base = _baseline()["rows"]
        _plant_evil_ahead_of_nec(monkeypatch)
        now = census()
        stolen = [k for k, v in now.items() if v == "EVIL"]
        assert stolen, "the planted decoder claimed nothing; the plant is broken"
        offenders = moved_rows(base, now, EXPECTED_CLAIMS) + newly_claimed_rows(
            base, now, EXPECTED_CLAIMS
        )
        assert offenders, "a decoder stole rows and the census did not fail"

    def test_the_round_2_attack_is_caught(self, tmp_path, monkeypatch):
        """The whole attack: planted decoder, two renames, four edits.

        Against the second draft this passed 10 of 10, because every
        stolen row had moved to a key the baseline had never seen. Now
        the renamed fixtures' rows VANISH (their old keys are gone and
        not retired) and the edited modules' rows keep their keys and so
        show as MOVED or newly claimed. Either alone fails the census;
        both are asserted so neither guard can rot without notice.
        """
        base = _baseline()["rows"]
        _plant_evil_ahead_of_nec(monkeypatch)
        now = census(**_doctored_corpus(tmp_path))

        vanished = vanished_rows(base, now, RETIRED_KEYS)
        assert vanished, "the renamed fixtures' rows should have vanished"
        assert any(source_of(k) == "fixtures/nec_test_fixtures.json" for k in vanished)

        stolen_inline = [
            k for k, v in now.items() if v == "EVIL" and k.startswith("TEST:")
        ]
        assert stolen_inline, "the edited modules' rows were not walked"
        assert all(k in base for k in stolen_inline), (
            "an edited module's rows changed key; inline keys must not "
            "depend on line numbers"
        )
        offenders = moved_rows(base, now, EXPECTED_CLAIMS) + newly_claimed_rows(
            base, now, EXPECTED_CLAIMS
        )
        assert offenders, "the stolen inline rows did not fail the census"

    def test_a_planted_false_positive_is_caught(self):
        base = _baseline()["rows"]
        victim = next(
            k for k, v in base.items()
            if v == "raw" and source_of(k) not in EXPECTED_CLAIMS
        )
        planted = dict(base)
        planted[victim] = "NEC42EXT"
        assert newly_claimed_rows(base, planted, EXPECTED_CLAIMS) == [
            (victim, "NEC42EXT")
        ]

    def test_a_retired_key_is_not_a_failure_and_a_stale_one_is(self):
        base = {"fixtures/gone.json#/a": "NEC", "fixtures/kept.json#/b": "NEC"}
        now = {"fixtures/kept.json#/b": "NEC"}
        assert vanished_rows(base, now, {}) == ["fixtures/gone.json#/a"]
        assert vanished_rows(
            base, now, {"fixtures/gone.json#/a": "deleted on purpose"}
        ) == []
