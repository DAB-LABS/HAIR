"""Generate the merged-group bytes golden, both columns.

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
    python custom_components/hair/tests/tools/gen_merged_group_golden.py --append

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

TWO COLUMNS. ``merged-group-golden.json`` presses each cell's file
text. ``merged-group-golden-captures.json`` presses each cell the way a
receiver hands it over (``merged_group_shapes.capture_rows``: the air
model of ``test_read_bytes_identity``, whole and split at the map's
gap), for every source where a read key forms. A file code finds its
cell through the composite key before the read key or the normalized
tier is ever asked, so only the second column sees a change to how
those two tiers answer.

``--check`` writes nothing and exits non-zero when the rows of either
column differ from the committed files, printing how many were compared
and which differ. ``--append`` writes only the rows of sources a
committed column does not have yet, leaving every committed row as it
is, and records the commit it ran at for those sources; a column with
no committed file is written whole.
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
    CAPTURE_GOLDEN,
    GOLDEN,
    capture_rows,
    dump,
    golden_rows,
)

#: Each column: its committed file and what generates its rows.
COLUMNS = (
    ("files", GOLDEN, golden_rows),
    ("captures", CAPTURE_GOLDEN, capture_rows),
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


def _check(label: str, path: Path, rows: dict) -> int:
    flat = _flatten(rows)
    committed = _flatten(
        json.loads(path.read_text(encoding="utf-8"))["rows"]
    )
    differ = sorted(
        key for key in set(flat) | set(committed)
        if flat.get(key, "missing") != committed.get(key, "missing")
    )
    print(f"{label}: compared {len(committed)} committed rows against "
          f"{len(flat)} generated: {len(differ)} differ")
    for key in differ[:20]:
        print("  ", key, committed.get(key, "missing"), "->",
              flat.get(key, "missing"))
    return len(differ)


def _write(label: str, path: Path, rows: dict, append: bool) -> None:
    head = _git_head()
    payload: dict = {"base_commit": head, "rows": rows}
    if append and path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        added = sorted(set(rows) - set(payload["rows"]))
        for source in added:
            payload["rows"][source] = rows[source]
            payload.setdefault("appended", {})[source] = head
        print(f"{label}: appended {len(added)} sources {added}")
    flat = _flatten(payload["rows"])
    payload["row_count"] = len(flat)
    path.write_text(dump(payload), encoding="utf-8")
    sent = sum(1 for row in flat.values() if row is not None)
    print(f"{label}: wrote {len(flat)} rows ({sent} sent, "
          f"{len(flat) - sent} nothing sent) to {path}")


def main(argv: list[str]) -> int:
    differ = 0
    for label, path, generate in COLUMNS:
        rows = asyncio.run(generate())
        if "--check" in argv:
            differ += _check(label, path, rows)
        else:
            _write(label, path, rows, append="--append" in argv)
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
