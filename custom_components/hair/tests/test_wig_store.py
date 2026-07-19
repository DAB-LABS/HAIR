"""Tests for the wig closet folder and scan."""
from __future__ import annotations

import json

from custom_components.hair.wig_format import WIG_FORMAT_V1
from custom_components.hair.wig_store import (
    ensure_wigs_dir,
    scan_wigs,
    wigs_dir,
)

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


def _write_wig(directory, filename, name="TV", **overrides):
    data = {
        "format": WIG_FORMAT_V1,
        "name": name,
        "signals": [{"alias": "Power", "pronto": PRONTO}],
    }
    data.update(overrides)
    (directory / filename).write_text(json.dumps(data), encoding="utf-8")


class TestFolder:
    def test_dir_layout(self, tmp_path):
        assert wigs_dir(tmp_path) == tmp_path / "hair" / "wigs"

    def test_ensure_creates_and_is_idempotent(self, tmp_path):
        path = ensure_wigs_dir(tmp_path)
        assert path.is_dir()
        assert ensure_wigs_dir(tmp_path) == path


class TestScan:
    def test_missing_folder_scans_empty(self, tmp_path):
        scan = scan_wigs(tmp_path)
        assert scan.wigs == [] and scan.invalid == []

    def test_valid_and_invalid_separated(self, tmp_path):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "good.wig.json", name="Good")
        (d / "bad.wig.json").write_text("{broken", encoding="utf-8")
        scan = scan_wigs(tmp_path)
        assert [w.wig.name for w in scan.wigs] == ["Good"]
        assert len(scan.invalid) == 1
        assert scan.invalid[0].path.name == "bad.wig.json"
        assert scan.invalid[0].errors

    def test_only_wig_suffix_scanned(self, tmp_path):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "real.wig.json")
        (d / "notes.txt").write_text("not a wig", encoding="utf-8")
        (d / "other.json").write_text("{}", encoding="utf-8")
        scan = scan_wigs(tmp_path)
        assert len(scan.wigs) == 1 and scan.invalid == []

    def test_deterministic_name_order(self, tmp_path):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "b.wig.json", name="B")
        _write_wig(d, "a.wig.json", name="A")
        scan = scan_wigs(tmp_path)
        assert [w.wig.name for w in scan.wigs] == ["A", "B"]

    def test_oversize_file_rejected_without_read(self, tmp_path):
        d = ensure_wigs_dir(tmp_path)
        (d / "huge.wig.json").write_text(
            "x" * 1_100_000, encoding="utf-8"
        )
        scan = scan_wigs(tmp_path)
        assert scan.wigs == []
        assert "size cap" in scan.invalid[0].errors[0]

    def test_one_bad_file_never_hides_the_rest(self, tmp_path):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        (d / "m.wig.json").write_text("{broken", encoding="utf-8")
        _write_wig(d, "z.wig.json", name="Z")
        scan = scan_wigs(tmp_path)
        assert [w.wig.name for w in scan.wigs] == ["A", "Z"]
        assert len(scan.invalid) == 1
