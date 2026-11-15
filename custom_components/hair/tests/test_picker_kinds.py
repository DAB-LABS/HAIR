"""The pickers offer the kind of hardware the work uses (owner, 2026-11-14).

Radio work offers radio receivers and transmitters, infrared work
infrared ones, and work that holds both kinds, or nothing yet to tell
by, offers both. Selections of the other kind are dropped on save. Make
a Device from a Remote already did this (#269); every other caller now
does too, through ``media-kind.ts``.

The rule runs under node with the repo's TypeScript (skipped without the
toolchain); the wiring is pinned in the source and runs everywhere.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
DRIVER = Path(__file__).parent / "fixtures" / "media_kind_driver.mjs"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("mediakindjs")
    subprocess.run(
        [
            str(TSC), "src/media-kind.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER.read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout.strip().splitlines()[0])


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


def _tag(name: str, tag: str) -> str:
    """The attributes of the one ``<tag`` in a file, up to its first ``>``
    that closes an attribute list (``@closed=${() =>`` is the earliest
    arrow in every caller here, so the cut stops before it)."""
    flat = _flat(name)
    assert flat.count(f"<{tag}") == 1, (name, tag)
    return flat.split(f"<{tag}", 1)[1].split("@closed=", 1)[0]


def _kind_getter(flat: str) -> str:
    """The body of an Add dialog's ``_kind`` getter."""
    rest = flat.split("private get _kind(): Medium | null {", 1)[1]
    return rest.split("private async _create", 1)[0]


class TestTheRule:
    def test_one_kind_or_open(self, run):
        assert run["sole"] == ["rf", "ir", None, None, None, None]

    def test_a_devices_codes(self, run):
        # No medium is infrared; a climate matrix adds infrared to what
        # the rows hold, as the server's _media does.
        assert run["rows"] == ["rf", "ir", None, None, None, None, "ir", "ir"]

    def test_an_unknown_remote_is_infrared_unless_radio(self, run):
        assert run["unknown"] == ["rf", "ir", "ir", "ir"]

    def test_saving_drops_the_other_kind(self, run):
        assert run["keep_rf"] == ["radio_frequency.athom", "remote.legacy"]
        assert run["keep_ir"] == ["infrared.blaster", "remote.legacy"]
        assert run["keep_open"] == [
            "infrared.blaster", "radio_frequency.athom", "remote.legacy",
        ]

    def test_a_chip_of_the_other_kind_shows_only_while_on(self, run):
        assert run["lists"] == [False, True, True, True, True]

    def test_the_picker_media(self, run):
        assert run["media"] == [["rf"], ["ir"], None]


class TestMakeARemote:
    def test_the_dialog_offers_and_saves_its_kind(self):
        flat = _flat("ir-promote-remote-dialog.ts")
        assert "@property({ attribute: false }) public medium: Medium | null = null;" in flat
        picker = flat.split("<ir-receiver-picker", 1)[1].split("></ir-receiver-picker>", 1)[0]
        assert ".medium=${this.medium}" in picker
        assert flat.count("keepKind(this._receiverIds, this.medium, receiverIdMedium)") == 3
        # Nothing reaches the server unfiltered.
        bare = flat.replace("keepKind(this._receiverIds,", "")
        assert "this._receiverIds," not in bare
        assert "receiver_scope: this._receiverIds" not in bare

    @pytest.mark.parametrize("name", ["ir-signal-monitor.ts", "ir-pluck.ts", "ir-clips.ts"])
    def test_the_sniffer_plucker_and_clipper_pass_the_kind(self, name):
        attrs = _tag(name, "ir-promote-remote-dialog")
        assert ".medium=${this._promoteRemoteTarget.medium}" in attrs
        assert "medium: unknownKind(" in _flat(name)

    def test_a_wig_keeps_both_kinds(self):
        attrs = _tag("ir-wigs.ts", "ir-promote-remote-dialog")
        assert ".medium=" not in attrs
        # A wig from the Clipper's Closet half is open too.
        clips = _flat("ir-clips.ts")
        start = "this._promoteRemoteTarget = { wigFilename: f.filename,"
        wig = clips.split(start, 1)[1].split("};", 1)[0]
        assert "medium: null," in wig

    @pytest.mark.parametrize(
        "name",
        ["ir-signal-monitor.ts", "ir-pluck.ts", "ir-clips.ts", "ir-wigs.ts", "ir-device-list.ts"],
    )
    def test_every_caller_passes_hass(self, name):
        # Without it the receiver chips drew gray: the picker reads each
        # receiver's health from hass.states.
        assert ".hass=${this.hass}" in _tag(name, "ir-promote-remote-dialog")

    def test_a_device_passes_its_codes_kind(self):
        attrs = _tag("ir-device-list.ts", "ir-promote-remote-dialog")
        assert (
            ".medium=${rowsKind( this._makeRemoteSource.commands, "
            "!!this._makeRemoteSource.climate_matrix, )}"
        ) in attrs


class TestMakeADevice:
    @pytest.mark.parametrize("name", ["ir-signal-monitor.ts", "ir-pluck.ts", "ir-clips.ts"])
    def test_a_sniffer_clipper_or_plucker_row_passes_its_kind(self, name):
        # The owner's look at #270: Use, then Make Device, on a radio
        # Sniffer row listed every emitter.
        blocks = [
            b.split("</ir-promote-dialog>", 1)[0]
            for b in _flat(name).split("<ir-promote-dialog")[1:]
        ]
        rows = [b for b in blocks if ".sourceUnknownId=${this._promoteTarget.id}" in b]
        assert len(rows) == 1, name
        assert ".media=${mediaFor(unknownKind(this._promoteTarget.medium))}" in rows[0]

    def test_the_dialog_saves_only_its_kind(self):
        flat = _flat("ir-promote-dialog.ts")
        create = flat.split("private async _create", 1)[1].split("private _renderNeedsPress", 1)[0]
        assert (
            "const emitterIds = keepKind(this._emitterIds, soleKind(this.media), emitterMedium);"
        ) in create
        assert "if (emitterIds.length === 0) {" in create
        assert "this._emitterIds" not in create.split("const emitterIds", 1)[1].split(";", 1)[1]


class TestTheOtherDialogs:
    def test_duplicate_a_remote(self):
        flat = _flat("ir-duplicate-trigger-remote-dialog.ts")
        prop = "@property({ attribute: false }) public sourceMedia: Medium[] | null = null;"
        assert prop in flat
        assert ".medium=${soleKind(this.sourceMedia)}" in flat
        assert (
            "keepKind(this._receiverIds, soleKind(this.sourceMedia), receiverIdMedium)"
        ) in flat
        page = _flat("ir-device-list.ts")
        assert ".sourceMedia=${this._duplicateRemoteTarget.media ?? null}" in page

    def test_add_remote(self):
        flat = _flat("ir-add-trigger-remote-dialog.ts")
        kind = _kind_getter(flat)
        assert "if (this._dropMode) return null;" in kind
        assert (
            'if (this._activeTab === "device") return soleKind(this._pickedDevice?.media);'
        ) in kind
        assert "return this._pickedSourceRow?.medium ?? null;" in kind
        assert ".medium=${this._kind}" in flat
        assert (
            "const receiverIds = keepKind(this._receiverIds, this._kind, receiverIdMedium);"
        ) in flat
        assert flat.count("receiver_scope: receiverIds,") == 2
        assert "receiver_scope: this._receiverIds" not in flat

    def test_create_device(self):
        flat = _flat("ir-add-controlled-device-dialog.ts")
        kind = _kind_getter(flat)
        assert "if (this._dropMode || !this._pickedSourceRow) return null;" in kind
        assert "return soleKind(this.triggerRemotes.find((r) => r.id === id)?.media);" in kind
        assert "return this._pickedSourceRow.medium ?? null;" in kind
        assert ".media=${mediaFor(this._kind)}" in flat
        create = flat.split("private async _create", 1)[1].split("private ", 1)[0]
        assert (
            "const emitterIds = keepKind(this._emitterIds, this._kind, emitterMedium);"
        ) in create
        assert "if (emitterIds.length === 0) {" in create
        assert "this._emitterIds" not in create.split("const emitterIds", 1)[1].split(";", 1)[1]

    @pytest.mark.parametrize(
        "name", ["ir-add-trigger-remote-dialog.ts", "ir-add-controlled-device-dialog.ts"]
    )
    def test_source_rows_carry_their_kind(self, name):
        assert "medium: unknownKind(d.medium)," in _flat(name)
        assert "medium?: Medium;" in _flat("ir-source-picker.ts")


class TestTheHeaderChips:
    def test_a_remotes_receivers(self):
        rows = _flat("ir-device-list.ts").split("private _receiverRows(", 1)[1].split("/**", 1)[0]
        assert "const kind = soleKind(remote.media);" in rows
        assert (
            "listsInKind( r.entity_id, kind, receiverIdMedium, "
            "remote.receiver_scope.includes(r.entity_id), )"
        ) in rows

    def test_a_devices_emitters(self):
        flat = _flat("ir-device-detail.ts")
        assert "const kind = rowsKind(this.device.commands, !!this.device.climate_matrix);" in flat
        assert (
            "listsInKind(em.entity_id, kind, emitterMedium, value.includes(em.entity_id))"
        ) in flat
