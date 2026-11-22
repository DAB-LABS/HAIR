"""Tests for the wig closet folder and scan."""
from __future__ import annotations

import copy
import json
import os
import threading

import pytest

from custom_components.hair import wig_store
from custom_components.hair.wig_format import WIG_FORMAT_V1
from custom_components.hair.wig_store import (
    clear_scan_cache,
    delete_wig,
    ensure_wigs_dir,
    forget_wig,
    load_wig,
    scan_wigs,
    wigs_dir,
    write_wig_text,
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
        # Cap raised to 16 MB for Cold Cuts matrix wigs.
        (d / "huge.wig.json").write_text(
            "x" * 16_100_000, encoding="utf-8"
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


@pytest.fixture
def parse_count(monkeypatch):
    """Count the files the scan actually parses."""
    calls: list[str] = []
    real = wig_store.parse_wig

    def counting(text):
        calls.append(text)
        return real(text)

    monkeypatch.setattr(wig_store, "parse_wig", counting)
    clear_scan_cache()
    yield calls
    clear_scan_cache()




class TestScanCache:
    def test_unchanged_files_are_not_parsed_again(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        _write_wig(d, "b.wig.json", name="B")
        first = scan_wigs(tmp_path)
        second = scan_wigs(tmp_path)
        assert len(parse_count) == 2
        assert [w.wig for w in second.wigs] == [w.wig for w in first.wigs]
        assert second.wigs[0].wig is first.wigs[0].wig

    def test_a_changed_file_is_parsed_again(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        scan_wigs(tmp_path)
        _write_wig(d, "a.wig.json", name="A longer name")
        scan = scan_wigs(tmp_path)
        assert [w.wig.name for w in scan.wigs] == ["A longer name"]
        assert len(parse_count) == 2

    def test_same_size_new_mtime_is_parsed_again(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="AAA")
        scan_wigs(tmp_path)
        path = d / "a.wig.json"
        st = path.stat()
        _write_wig(d, "a.wig.json", name="BBB")
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
        scan = scan_wigs(tmp_path)
        assert [w.wig.name for w in scan.wigs] == ["BBB"]

    def test_new_and_removed_files_follow_the_folder(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        _write_wig(d, "b.wig.json", name="B")
        scan_wigs(tmp_path)
        (d / "a.wig.json").unlink()
        _write_wig(d, "c.wig.json", name="C")
        scan = scan_wigs(tmp_path)
        assert [w.wig.name for w in scan.wigs] == ["B", "C"]
        assert set(wig_store._SCAN_CACHE[d]) == {"b.wig.json", "c.wig.json"}

    def test_a_fixed_invalid_file_becomes_valid(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        (d / "a.wig.json").write_text("{broken", encoding="utf-8")
        assert len(scan_wigs(tmp_path).invalid) == 1
        _write_wig(d, "a.wig.json", name="Fixed")
        scan = scan_wigs(tmp_path)
        assert scan.invalid == []
        assert [w.wig.name for w in scan.wigs] == ["Fixed"]

    def test_forget_covers_a_rewrite_inside_one_tick(
        self, tmp_path, parse_count, monkeypatch
    ):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="AAA")
        scan_wigs(tmp_path)
        path = d / "a.wig.json"
        old = wig_store._stamp(path)
        _write_wig(d, "a.wig.json", name="BBB")
        # A rewrite of the same size inside one timestamp tick leaves the
        # stat as it was; the stat alone can't see it...
        monkeypatch.setattr(wig_store, "_stamp", lambda p: old)
        assert [w.wig.name for w in scan_wigs(tmp_path).wigs] == ["AAA"]
        # ...so HAIR's writers forget the file they wrote.
        forget_wig(tmp_path, "a.wig.json")
        assert [w.wig.name for w in scan_wigs(tmp_path).wigs] == ["BBB"]

    def test_write_and_delete_forget_their_file(self, tmp_path, parse_count):
        text = json.dumps({
            "format": WIG_FORMAT_V1,
            "name": "TV",
            "signals": [{"alias": "Power", "pronto": PRONTO}],
        })
        filename = write_wig_text(tmp_path, text, "TV")
        d = wigs_dir(tmp_path)
        scan_wigs(tmp_path)
        assert filename in wig_store._SCAN_CACHE[d]
        assert delete_wig(tmp_path, filename)
        assert filename not in wig_store._SCAN_CACHE[d]
        assert scan_wigs(tmp_path).wigs == []

    def test_an_unreadable_file_is_tried_again(
        self, tmp_path, parse_count, monkeypatch
    ):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        real = type(d).read_text

        def refuse(self, *args, **kwargs):
            raise OSError("busy")

        monkeypatch.setattr(type(d), "read_text", refuse)
        scan = scan_wigs(tmp_path)
        assert "could not read file" in scan.invalid[0].errors[0]
        monkeypatch.setattr(type(d), "read_text", real)
        assert [w.wig.name for w in scan_wigs(tmp_path).wigs] == ["A"]

    def test_a_file_changed_while_read_is_not_kept(
        self, tmp_path, parse_count, monkeypatch
    ):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        real = wig_store._stamp
        stamps = iter([(1, 1, 1), (2, 2, 2)])
        monkeypatch.setattr(wig_store, "_stamp", lambda path: next(stamps))
        scan_wigs(tmp_path)
        assert "a.wig.json" not in wig_store._SCAN_CACHE[d]
        monkeypatch.setattr(wig_store, "_stamp", real)
        scan_wigs(tmp_path)
        assert len(parse_count) == 2

    def test_scans_at_once_parse_each_file_once(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        for i in range(5):
            _write_wig(d, f"w{i}.wig.json", name=f"W{i}")
        results = []
        threads = [
            threading.Thread(target=lambda: results.append(scan_wigs(tmp_path)))
            for _ in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(parse_count) == 5
        assert all(len(r.wigs) == 5 for r in results)

    def test_load_wig_is_its_own_copy(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        scanned = scan_wigs(tmp_path).wigs[0].wig
        loaded = load_wig(tmp_path, "a.wig.json")
        assert loaded == scanned and loaded is not scanned
        loaded.name = "changed"
        assert scan_wigs(tmp_path).wigs[0].wig.name == "A"

    def test_a_copy_keeping_mtime_is_still_seen(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="AAA")
        scan_wigs(tmp_path)
        path = d / "a.wig.json"
        st = path.stat()
        _write_wig(d, "a.wig.json", name="BBB")
        # As cp -p or rsync -t would leave it: same size, same mtime,
        # same inode. The change time still moves.
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
        assert [w.wig.name for w in scan_wigs(tmp_path).wigs] == ["BBB"]

    def test_readers_leave_scanned_wigs_unchanged(self, tmp_path, parse_count):
        """Every caller of scan_wigs only reads what it gets, because the
        cache shares it. Run each reader over a scan and compare."""
        from custom_components.hair.code_library import get_combined_tree
        from custom_components.hair.tests.test_wig_closet import (
            MATRIX_WIG_TEXT,
        )
        from custom_components.hair.wig_climate import matrix_summary
        from custom_components.hair.wig_comb import receipt_summary
        from custom_components.hair.wig_fitting import claims_summary
        from custom_components.hair.wig_format import (
            cells_content_hash,
            wig_content_hash,
        )

        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        (d / "m.wig.json").write_text(MATRIX_WIG_TEXT, encoding="utf-8")
        scanned = scan_wigs(tmp_path).wigs
        assert any(w.wig.climate is not None for w in scanned)
        before = copy.deepcopy([w.wig for w in scanned])
        for loaded in scanned:
            wig = loaded.wig
            claims_summary(wig, None)
            receipt_summary(wig)
            wig_content_hash(wig)
            if wig.climate is not None:
                matrix_summary(wig.climate)
                cells_content_hash(wig.climate)
        get_combined_tree(str(tmp_path))
        assert [w.wig for w in scan_wigs(tmp_path).wigs] == before

    def test_a_removed_folder_empties_the_cache(self, tmp_path, parse_count):
        d = ensure_wigs_dir(tmp_path)
        _write_wig(d, "a.wig.json", name="A")
        scan_wigs(tmp_path)
        (d / "a.wig.json").unlink()
        d.rmdir()
        assert scan_wigs(tmp_path).wigs == []
        assert d not in wig_store._SCAN_CACHE
