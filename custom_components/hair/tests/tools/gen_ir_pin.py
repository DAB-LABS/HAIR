"""Generate the IR pin baseline.

Committed beside the baseline it writes so its provenance is checkable:
run this at the base commit with ``tests/ir_pin_corpus.py`` copied in
(it uses only APIs that exist there), on each leg, and compare the md5
against the one in the report.

    python -m custom_components.hair.tests.tools.gen_ir_pin

Writes ``tests/fixtures/ir-pin-v1.json.gz`` (``-nolib`` on the bare
leg) with the base commit, the library version, and one digest per row.
``HAIR_PIN_BASE`` names the commit when the tree was exported rather
than cloned.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
from pathlib import Path

from custom_components.hair.tests.ir_pin_corpus import pin
from custom_components.hair.tests.leg import BASELINE_SUFFIX

BASELINE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / f"ir-pin-v1{BASELINE_SUFFIX}.json.gz"
)


def _git_head() -> str:
    override = os.environ.get("HAIR_PIN_BASE")
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
        return "none"


def main() -> None:
    rows = pin()
    body = {
        "base": _git_head(),
        "library": _library_version() if not BASELINE_SUFFIX else "none",
        "leg": BASELINE_SUFFIX or "lib",
        "rows": sum(len(v) for v in rows.values()),
        "sources": rows,
    }
    text = json.dumps(body, sort_keys=True, indent=0, separators=(",", ":"))
    data = gzip.compress(text.encode("utf-8"), mtime=0)
    BASELINE.write_bytes(data)
    print(BASELINE.name, body["rows"], "rows", hashlib.md5(data).hexdigest())


if __name__ == "__main__":
    main()
