"""The no-steal census: the protocol pack's licence to sit where it does.

Three decoders that read the NEC1 frame shape arrive in one patch, two
of them high in the probe order. The argument that none of them takes a
frame belonging to something else is not an argument, it is this file:
a label recorded for every capture in the repo BEFORE they existed, and
asserted afterwards.

WHAT MAKES IT ABLE TO FAIL. Review round 1 found the first draft could
not: it asserted that rows which already had an identity kept it, and
filed rows that gained one under "informational". A new wrong identity
is the whole false-positive class, so that census would have reported
the thing it existed to catch and passed. Here:

- ``raw`` is a label. A row nothing decoded is recorded as ``raw``, and
  a row that was ``raw`` and is now claimed FAILS unless its fixture is
  on ``EXPECTED_CLAIMS`` below, by path and by the exact label.
- A row whose label changed between two protocols fails, always, with
  no allowlist. That is the must-not-change list expressed as a test.
- Rows are keyed by ``(source, index)``. A later phase adding fixtures
  must not read as every later row changing, so a key the baseline has
  never seen is reported and does not fail, while a key it has whose
  label moved always does.

THE BASELINE'S PROVENANCE IS CHECKABLE, not asserted. It was generated
by ``tests/tools/gen_decode_census.py`` run against a pristine checkout
of the base commit, which is recorded inside the file along with the
library version the walk ran against. Re-run that script at that commit
to reproduce it; a baseline reverse-engineered from the new behaviour
would not survive that.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.hair.tests.census_corpus import census, corpus, sources
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


def _baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _source_of(key: str) -> str:
    return key.rsplit("#", 1)[0]


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

    def test_baseline_records_its_own_provenance(self):
        data = _baseline()
        assert data["base_commit"], "the baseline does not say what it is of"
        assert data["row_count"] == len(data["rows"])


class TestNoSteal:
    """Every row's label, against the baseline."""

    def test_no_row_changes_protocol(self):
        """A row that decoded as X must still decode as X.

        No allowlist reaches this: a protocol moving to another protocol
        is a steal whatever the fixture, and it is the must-not-change
        list stated as an assertion.
        """
        base = _baseline()["rows"]
        now = census()
        moved = [
            (key, base[key], now[key])
            for key in base
            if key in now and base[key] != now[key] and base[key] != "raw"
        ]
        offenders = [
            row for row in moved
            if row[2] not in EXPECTED_CLAIMS.get(_source_of(row[0]), set())
        ]
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
        base = _baseline()["rows"]
        now = census()
        claimed = [
            (key, now[key])
            for key in base
            if key in now and base[key] == "raw" and now[key] != "raw"
        ]
        offenders = [
            (key, label) for key, label in claimed
            if label not in EXPECTED_CLAIMS.get(_source_of(key), set())
        ]
        assert not offenders, "\n".join(
            f"{key}: was unclaimed, now {label}" for key, label in offenders
        )

    def test_no_claimed_row_becomes_raw(self):
        """The opposite failure: a decoder that stopped reading a frame."""
        base = _baseline()["rows"]
        now = census()
        lost = [
            key for key in base
            if key in now and base[key] != "raw" and now[key] == "raw"
        ]
        assert not lost, "\n".join(f"{key}: {base[key]} -> raw" for key in lost)

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
                if _source_of(key) == source
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


class TestCensusCanFail:
    """The census is only a licence if it can refuse one.

    A test suite that has never seen its own failure mode is a suite
    that might be asserting nothing, which is precisely what round 1
    found the first draft doing.
    """

    def test_a_planted_steal_is_caught(self, monkeypatch):
        base = _baseline()["rows"]
        # Any claimed row will do. Not pinned to NEC: on the bare leg
        # there is no strict NEC decoder and no NEC row to plant on.
        victim = next(k for k, v in base.items() if v != "raw")
        decoy = "SAMSUNG32" if base[victim] != "SAMSUNG32" else "SONY12"

        planted = dict(census())
        planted[victim] = decoy
        monkeypatch.setattr(
            "custom_components.hair.tests.test_no_steal_census.census",
            lambda: planted,
        )
        with pytest.raises(AssertionError, match=f"-> {decoy}"):
            TestNoSteal().test_no_row_changes_protocol()

    def test_a_planted_false_positive_is_caught(self, monkeypatch):
        base = _baseline()["rows"]
        victim = next(
            k for k, v in base.items()
            if v == "raw" and _source_of(k) not in EXPECTED_CLAIMS
        )

        planted = dict(census())
        planted[victim] = "NEC42EXT"
        monkeypatch.setattr(
            "custom_components.hair.tests.test_no_steal_census.census",
            lambda: planted,
        )
        with pytest.raises(AssertionError, match="now NEC42EXT"):
            TestNoSteal().test_no_raw_row_becomes_claimed_off_the_allowlist()
