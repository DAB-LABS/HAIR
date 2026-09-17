"""Generate the no-steal census baseline.

Committed beside the baseline it writes so the provenance of that file
is checkable rather than asserted: run this at the base commit, compare
the md5 against the one in the report, and the baseline is what it says
it is. Review round 1 asked for exactly this, having pointed out that a
baseline generated after the decoders land is byte-identical to one
generated before and nothing in the patch could tell them apart.

    python -m custom_components.hair.tests.tools.gen_decode_census

Writes ``tests/fixtures/decode-census-v0150.json`` with the base commit,
the library version the walk ran against, and one label per row.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from custom_components.hair.tests.census_corpus import census, sources
from custom_components.hair.tests.leg import BASELINE_SUFFIX

#: One baseline per CI leg. Without ``infrared_protocols`` there is no
#: strict NEC decoder, so every NEC row is unclaimed and a single shared
#: baseline would make the census assert nothing on that leg.
BASELINE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / f"decode-census-v0150{BASELINE_SUFFIX}.json"
)


def _git_head() -> str:
    """The commit the walk ran against.

    ``HAIR_CENSUS_BASE`` wins when set, because a build tree exported
    from a commit rather than cloned at it has a local hash that means
    nothing to a reader. Falls back to the working repo's HEAD.
    """
    override = os.environ.get("HAIR_CENSUS_BASE")
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _library_version() -> str:
    try:
        from importlib.metadata import version

        return f"infrared-protocols {version('infrared-protocols')}"
    except Exception:
        return "infrared-protocols absent"


def main() -> int:
    rows = census()
    walk = sources()
    payload = {
        "base_commit": _git_head(),
        "library": _library_version(),
        "row_count": len(rows),
        "source_count": len(walk),
        "sources": dict(sorted(walk.items())),
        "rows": dict(sorted(rows.items())),
    }
    BASELINE.write_text(
        json.dumps(payload, indent=1, sort_keys=False) + "\n", encoding="utf-8"
    )
    labels: dict[str, int] = {}
    for label in rows.values():
        labels[label] = labels.get(label, 0) + 1
    print(f"wrote {BASELINE}")
    print(f"  base_commit  {payload['base_commit']}")
    print(f"  library      {payload['library']}")
    print(f"  rows         {len(rows)} across {len(walk)} sources")
    for label, count in sorted(labels.items(), key=lambda kv: -kv[1]):
        print(f"  {label:<12} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
