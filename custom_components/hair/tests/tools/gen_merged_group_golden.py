"""Generate the merged-group bytes golden.

The owner's rule for the merged-group dial is that nothing it adds may
change what a pinned device transmits for any press. A comparison
against bytes computed by the new code would be circular, so the
expected bytes are written here, once, at the commit BEFORE the change,
and committed beside the generator that wrote them. Run it again on any
later commit and diff: an unchanged file is the proof, and the test in
``test_merged_group_dial.py`` checks the same rows against every
current state a climate entity could report.

    python custom_components/hair/tests/tools/gen_merged_group_golden.py
    python custom_components/hair/tests/tools/gen_merged_group_golden.py --check

Run by path from the repository root, not with ``-m``: the package
imports Home Assistant, which is not installed where the suite runs,
and the repository's ``conftest.py`` has to stub it before anything
under ``custom_components.hair`` is imported. ``-m`` would import the
package first.

Every field pack, both Komeco wigs, and the synthesized shapes in
``merged_group_shapes``, each pressed cell by cell through the real
``MatrixListener._async_resolve_device_cell`` on four pairings: the
same file, a second file whose every timing word is moved, a device
lattice with every other temperature removed, and an extras lattice.
One row per press: the sha256 of the normalized Pronto that went out
and its send count, or null when nothing would be sent.

``--check`` writes nothing and exits non-zero when the rows differ from
the committed file, printing how many were compared and which differ.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import conftest  # noqa: E402,F401  (the Home Assistant stubs, as pytest loads them)
from custom_components.hair.tests.merged_group_shapes import (  # noqa: E402
    GOLDEN,
    dump,
    golden_rows,
)


def _git_head() -> str:
    override = os.environ.get("HAIR_GOLDEN_BASE")
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _flatten(rows: dict) -> dict[tuple, str | None]:
    return {
        (source, name, index): row
        for source, by_pairing in rows.items()
        for name, column in by_pairing.items()
        for index, row in enumerate(column)
    }


def main(argv: list[str]) -> int:
    rows = asyncio.run(golden_rows())
    flat = _flatten(rows)
    if "--check" in argv:
        committed = _flatten(
            json.loads(GOLDEN.read_text(encoding="utf-8"))["rows"]
        )
        differ = sorted(
            key for key in set(flat) | set(committed)
            if flat.get(key, "missing") != committed.get(key, "missing")
        )
        print(f"compared {len(committed)} committed rows against "
              f"{len(flat)} generated: {len(differ)} differ")
        for key in differ[:20]:
            print("  ", key, committed.get(key, "missing"), "->",
                  flat.get(key, "missing"))
        return 1 if differ else 0
    payload = {
        "base_commit": _git_head(),
        "row_count": len(flat),
        "rows": rows,
    }
    GOLDEN.write_text(dump(payload), encoding="utf-8")
    sent = sum(1 for row in flat.values() if row is not None)
    print(f"wrote {len(flat)} rows ({sent} sent, {len(flat) - sent} "
          f"nothing sent) to {GOLDEN}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
