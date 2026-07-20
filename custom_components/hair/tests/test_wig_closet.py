"""The closet in motion: store write/read/delete helpers, the combined
picker tree, wig materialization, merge-on-reimport, and the export
round-trip invariant (wigs.md sections 6, 7, 11).

test_wig_format.py owns the format contract; test_wig_store.py owns the
scan. This file covers everything Big Wig core layered on top.
"""
from __future__ import annotations

import json

import pytest

from custom_components.hair.code_library import (
    get_combined_tree,
    materialize_wig,
    parse_wig_id,
    wig_codebook_id,
)
from custom_components.hair.models import (
    IRCommand,
    IRDevice,
    UnknownDevice,
    UnknownSignal,
)
from custom_components.hair.wig_export import (
    build_wig_from_catalog,
    build_wig_from_device,
)
from custom_components.hair.wig_format import parse_wig, serialize_wig
from custom_components.hair.wig_store import (
    delete_wig,
    load_wig,
    read_wig_text,
    safe_wig_filename,
    wigs_dir,
    write_wig_text,
)

PRONTO = (
    "0000 006D 0006 0000 00E0 0070 0014 000D 0014 002E "
    "0014 000D 0014 000D 0014 0400"
)

WIG_TEXT = json.dumps({
    "format": "hair-wig/1",
    "name": "Foxtel IQ",
    "brand": "Foxtel",
    "signals": [
        {"alias": "Power", "pronto": PRONTO},
        {"alias": "Mute", "pronto": PRONTO.replace("002E", "002F"),
         "send_count": 3},
    ],
})


class TestStoreHelpers:
    def test_write_then_read_preserves_bytes(self, tmp_path):
        filename = write_wig_text(tmp_path, WIG_TEXT, "Foxtel IQ")
        assert filename == "foxtel-iq.wig.json"
        assert read_wig_text(tmp_path, filename) == WIG_TEXT

    def test_write_rejects_invalid(self, tmp_path):
        assert write_wig_text(tmp_path, "{}", "junk") is None
        assert not list(wigs_dir(tmp_path).glob("*"))

    def test_write_dodges_collisions(self, tmp_path):
        first = write_wig_text(tmp_path, WIG_TEXT, "Foxtel IQ")
        second = write_wig_text(tmp_path, WIG_TEXT, "Foxtel IQ")
        assert first == "foxtel-iq.wig.json"
        assert second == "foxtel-iq-2.wig.json"

    def test_unknown_keys_survive_write(self, tmp_path):
        data = json.loads(WIG_TEXT)
        data["fittings"] = [{"handle": "someone"}]
        filename = write_wig_text(tmp_path, json.dumps(data), "x")
        assert "fittings" in read_wig_text(tmp_path, filename)

    def test_delete(self, tmp_path):
        filename = write_wig_text(tmp_path, WIG_TEXT, "Foxtel IQ")
        assert delete_wig(tmp_path, filename) is True
        assert delete_wig(tmp_path, filename) is False
        assert read_wig_text(tmp_path, filename) is None

    def test_load_wig(self, tmp_path):
        filename = write_wig_text(tmp_path, WIG_TEXT, "Foxtel IQ")
        wig = load_wig(tmp_path, filename)
        assert wig is not None and wig.name == "Foxtel IQ"
        assert load_wig(tmp_path, "missing.wig.json") is None

    @pytest.mark.parametrize("bad", [
        "../evil.wig.json",
        "/etc/passwd",
        "sub/dir.wig.json",
        "..\\evil.wig.json",
        ".hidden.wig.json",
        "notawig.json",
        "plain.txt",
    ])
    def test_traversal_and_junk_names_refused(self, tmp_path, bad):
        assert safe_wig_filename(bad) is False
        assert load_wig(tmp_path, bad) is None
        assert read_wig_text(tmp_path, bad) is None
        assert delete_wig(tmp_path, bad) is False


class TestCombinedTree:
    def test_local_wigs_join_the_alphabet(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "custom_components.hair.code_library.get_tree",
            lambda: [{
                "brand": "foxtel", "label": "Foxtel",
                "codebooks": [{
                    "id": "m:FoxtelCode", "label": "Foxtel Box",
                    "functions": [], "source": "library",
                }],
            }],
        )
        write_wig_text(tmp_path, WIG_TEXT, "Foxtel IQ")
        unbranded = json.loads(WIG_TEXT)
        del unbranded["brand"]
        unbranded["name"] = "Mystery Remote"
        write_wig_text(tmp_path, json.dumps(unbranded), "Mystery Remote")

        tree = get_combined_tree(str(tmp_path))
        by_label = {b["label"]: b for b in tree}
        # Branded wig folded into the existing library brand row.
        foxtel = by_label["Foxtel"]
        sources = {c["source"] for c in foxtel["codebooks"]}
        assert sources == {"library", "local"}
        local = next(
            c for c in foxtel["codebooks"] if c["source"] == "local"
        )
        assert local["label"] == "Foxtel IQ"
        assert local["id"] == wig_codebook_id("foxtel-iq.wig.json")
        assert [f["name"] for f in local["functions"]] == ["Power", "Mute"]
        # Brandless wig lands in the Unbranded bucket.
        assert "Unbranded" in by_label

    def test_wig_id_round_trip(self):
        assert parse_wig_id(wig_codebook_id("a.wig.json")) == "a.wig.json"
        assert parse_wig_id("infrared_protocols.codes.lg:LGTVCode") is None


class TestMaterializeWig:
    def test_entries_are_fresh_decoded_and_carry_send_count(self, tmp_path):
        filename = write_wig_text(tmp_path, WIG_TEXT, "Foxtel IQ")
        entries = materialize_wig(
            str(tmp_path), wig_codebook_id(filename)
        )
        assert [e["name"] for e in entries] == ["Power", "Mute"]
        assert entries[0]["send_count"] == 1
        assert entries[1]["send_count"] == 3
        # Fresh decode fields are present (None is fine for a code no
        # decoder reads; the KEY must exist so import wires them).
        assert "decoded_fingerprint" in entries[0]
        # Pronto is normalized by the validator.
        assert entries[0]["code"].upper() == entries[0]["code"]

    def test_function_subset(self, tmp_path):
        filename = write_wig_text(tmp_path, WIG_TEXT, "Foxtel IQ")
        cb = wig_codebook_id(filename)
        entries = materialize_wig(str(tmp_path), cb, [f"{cb}:1"])
        assert [e["name"] for e in entries] == ["Mute"]

    def test_unknown_id_is_empty(self, tmp_path):
        assert materialize_wig(str(tmp_path), "wig:nope.wig.json") == []
        assert materialize_wig(str(tmp_path), "not-a-wig-id") == []


def _catalog_remote() -> UnknownDevice:
    device = UnknownDevice(label="Foxtel IQ", source="sniffed")
    device.signals.append(UnknownSignal(
        fingerprint="S1L2", protocol="PRONTO", code=PRONTO,
        alias="Power", send_count=2,
    ))
    device.signals.append(UnknownSignal(
        fingerprint="S3L4", protocol=None, code=None,
        raw_timings=[9000, -4500, 560, -560, 560, -1690, 560],
        frequency=38000, alias="",
    ))
    device.signals.append(UnknownSignal(
        fingerprint="S5L6", protocol=None, code=None, raw_timings=[],
        alias="Ghost",
    ))
    return device


class TestExport:
    def test_catalog_export_shapes_and_origin(self):
        build = build_wig_from_catalog(_catalog_remote())
        assert build.skipped == 1  # the codeless, timing-less ghost
        wig = build.wig
        assert wig.origin == "captured"
        assert wig.name == "Foxtel IQ"
        assert [s.alias for s in wig.signals] == ["Power", "Signal 2"]
        assert wig.signals[0].send_count == 2

    def test_clipped_and_plucked_origins(self):
        for source, origin in (
            ("manual", "clipped"), ("plucked", "plucked"),
        ):
            remote = _catalog_remote()
            remote.source = source
            assert build_wig_from_catalog(remote).wig.origin == origin

    def test_device_export(self):
        device = IRDevice(name="Living Room TV")
        device.commands.append(IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=PRONTO,
            send_count=4,
        ))
        device.commands.append(IRCommand(
            id="c2", name="", protocol=None, code=None, raw_timings=None,
        ))
        build = build_wig_from_device(device)
        assert build.skipped == 1
        assert build.wig.origin == "device"
        assert build.wig.name == "Living Room TV"
        assert build.wig.signals[0].alias == "Power"
        assert build.wig.signals[0].send_count == 4

    def test_empty_export_returns_none(self):
        device = UnknownDevice(label="Empty", source="sniffed")
        build = build_wig_from_catalog(device)
        assert build.wig is None

    def test_round_trip_invariant(self, tmp_path):
        """Export then import on a clean install yields identical aliases,
        normalized codes, and identities (wigs.md section 7)."""
        build = build_wig_from_catalog(_catalog_remote())
        text = serialize_wig(build.wig)
        result = parse_wig(text)
        assert result.ok
        filename = write_wig_text(tmp_path, text, build.wig.name)
        entries = materialize_wig(
            str(tmp_path), wig_codebook_id(filename)
        )
        assert [e["name"] for e in entries] == [
            s.alias for s in build.wig.signals
        ]
        assert entries[0]["send_count"] == 2
