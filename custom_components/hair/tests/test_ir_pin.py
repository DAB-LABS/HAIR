"""The IR pin: infrared rows come out of the radio work unchanged.

Every code in the air-path fixtures, the field captures and the field
packs produces the same ``code``, ``byte_hash``, ``fingerprint``,
``norm_fingerprint``, device key, decoded fingerprint, planned sends,
``row_digest`` and stored records as it did at the base commit the
baseline names. See ``ir_pin_corpus.py`` for what a row is and
``tools/gen_ir_pin.py`` for how the baseline was made.

A failure prints the first differing row with everything HAIR now
derives from it, so the field that moved can be read off. Rows are
keyed by source and position: a fixture added later is reported, not
failed; a fixture that vanished fails.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from custom_components.hair.tests.ir_pin_corpus import corpus, identity_of, row_hash
from custom_components.hair.tests.leg import BASELINE_SUFFIX

BASELINE_PATH = (
    Path(__file__).parent / "fixtures" / f"ir-pin-v1{BASELINE_SUFFIX}.json.gz"
)


@pytest.fixture(scope="module")
def baseline() -> dict:
    with gzip.open(BASELINE_PATH, "rt", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def rows():
    return corpus()


def test_the_baseline_is_the_one_for_this_leg(baseline):
    assert baseline["leg"] == (BASELINE_SUFFIX or "lib")
    assert baseline["rows"] > 7000, "the baseline collapsed"


def test_the_corpus_covers_every_baseline_source(baseline, rows):
    walked = {item.source for item in rows}
    missing = sorted(set(baseline["sources"]) - walked)
    assert not missing, f"fixtures vanished from the walk: {missing}"
    for source, digests in baseline["sources"].items():
        count = sum(1 for item in rows if item.source == source)
        assert count == len(digests), (
            f"{source}: {count} codes walked, {len(digests)} in the baseline"
        )


def test_every_infrared_row_is_unchanged(baseline, rows):
    expected = baseline["sources"]
    new_sources: set[str] = set()
    for item in rows:
        digests = expected.get(item.source)
        if digests is None:
            new_sources.add(item.source)
            continue
        if row_hash(item) != digests[item.index]:
            pytest.fail(
                f"{item.key} ({item.path}, {item.kind}) changed since "
                f"{baseline['base']}; it now derives:\n"
                + json.dumps(identity_of(item), indent=1, sort_keys=True)
            )
    if new_sources:
        print(f"not in the baseline, not checked: {sorted(new_sources)}")


def test_the_pin_can_fail(rows, monkeypatch):
    """A one-character change to what the normalizer returns moves a row."""
    from custom_components.hair import signal_monitor

    item = next(r for r in rows if r.kind == "pronto")
    before = row_hash(item)
    real = signal_monitor.normalize

    def doctored(parsed):
        result = real(parsed)
        result.byte_hash = (result.byte_hash or "") + "x"
        return result

    monkeypatch.setattr(signal_monitor, "normalize", doctored)
    assert row_hash(item) != before
