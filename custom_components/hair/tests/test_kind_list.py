"""Kind: one list, one dropdown.

Ruled 2026-09-16. Kind was free text with a suggestion list, and the
list was typed out in three places that had already drifted: a dead
Python tuple, a live TypeScript array, and a closet datalist that grew
itself from whatever anybody had typed. ``screen`` existed in the
device-type table and in neither suggestion list; the one bundled
real-world wig says ``airconditioner`` where the list said ``ac``.

Now there is one list, ``wig_format.KIND_LIST``, the panel reads it
over ``hair/wigs/kinds``, and every surface that edits kind draws the
same dropdown from it.

Two halves, and the second is the one that protects people's files:

- WRITES are gated. A save naming a word the list cannot place is
  refused, which reaches an old client or a hand-built payload rather
  than a person, since the dropdown cannot produce one.
- FILES ARE NEVER REWRITTEN. Whatever a wig says stays in it. The
  alias map places known spellings for display, an unplaceable word
  shows as Other beside the file's own value, and no read, no listing
  and no unrelated edit touches the bytes.

The frontend half reads the TypeScript, which is the house tactic
(test_polish_rulings.py's header has the reasoning); the backend half
runs.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN, DeviceType
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.websocket_api import (
    ws_wigs_kinds,
    ws_wigs_list,
    ws_wigs_save,
    ws_wigs_update,
)
from custom_components.hair.wig_format import (
    KIND_ALIAS,
    KIND_BY_KEY,
    KIND_LIST,
    Wig,
    WigSignal,
    kind_display,
    kind_slug,
    normalize_kind,
    serialize_wig,
)
from custom_components.hair.wig_store import ensure_wigs_dir, wigs_dir

SRC = Path(__file__).parent.parent / "frontend" / "src"
LOCALES = SRC / "locales"
LOCALE_NAMES = (
    "en", "de", "es", "fr", "it", "ja", "nl", "pl", "pt", "ru",
)
FIXTURES = Path(__file__).parent / "fixtures" / "wigs"
KOMECO = FIXTURES / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json"

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _locale(stem: str) -> dict:
    return json.loads((LOCALES / f"{stem}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------
# The list itself
# ---------------------------------------------------------------------


class TestTheListIsWellFormed:
    def test_every_key_is_unique_and_slug_shaped(self):
        """The key IS the stored value, so it has to survive the squash
        every other kind path already applies. A key that slugged to
        something else would store one word and match another."""
        keys = [entry.key for entry in KIND_LIST]
        assert len(keys) == len(set(keys))
        for key in keys:
            assert kind_slug(key) == key, key

    def test_every_device_type_exists(self):
        """A typo here seeds the adopt dialog with a type no dialog has
        an option for, and the person sees an empty picker with no idea
        why."""
        valid = {member.value for member in DeviceType}
        for entry in KIND_LIST:
            assert entry.device_type in valid, entry.key

    def test_every_label_key_matches_its_entry(self):
        for entry in KIND_LIST:
            assert entry.label_key == f"wigs.kind.{entry.key}"

    def test_other_is_a_real_entry_and_comes_last(self):
        """A device that fits no word has an answer on the list rather
        than an empty field. Last because it is the answer you reach
        for after reading the others."""
        assert "other" in KIND_BY_KEY
        assert KIND_LIST[-1].key == "other"

    def test_the_list_is_the_ruled_twenty_six_plus_other(self):
        assert len(KIND_LIST) == 27

    def test_every_alias_points_at_a_real_key(self):
        """An alias to nothing is worse than no alias: the value reads
        as unplaceable anyway, and the map says otherwise."""
        for spelling, key in KIND_ALIAS.items():
            assert kind_slug(spelling) == spelling, spelling
            assert key in KIND_BY_KEY, (spelling, key)

    def test_no_alias_shadows_a_list_key(self):
        """An alias whose own spelling is on the list would be read
        before the list and could quietly redirect a legitimate word."""
        for spelling in KIND_ALIAS:
            assert spelling not in KIND_BY_KEY, spelling


class TestNormalizeKind:
    def test_every_list_key_round_trips(self):
        for entry in KIND_LIST:
            assert normalize_kind(entry.key) == entry.key

    def test_every_alias_lands_on_its_key(self):
        for spelling, key in KIND_ALIAS.items():
            assert normalize_kind(spelling) == key

    def test_case_and_punctuation_squash_first(self):
        assert normalize_kind("Sound Bar") == "soundbar"
        assert normalize_kind("set-top box") == "settopbox"
        assert normalize_kind("Air Conditioner") == "ac"

    def test_a_word_the_list_does_not_have_is_none(self):
        """None is the honest answer, and the save handlers turn it
        into a refusal. "Ceiling Fan" squashes to ceilingfan, which is
        not the word "fan" and is not aliased to it -- guessing that it
        means a fan is how a vocabulary stops meaning anything."""
        assert normalize_kind("Ceiling Fan") is None
        assert normalize_kind("toaster") is None
        assert normalize_kind("projectorscreen") is None

    def test_nothing_is_none(self):
        assert normalize_kind("") is None
        assert normalize_kind("   ") is None
        assert normalize_kind(None) is None
        assert normalize_kind("!!!") is None


class TestKindDisplay:
    def test_a_list_key_selects_itself_with_no_raw(self):
        assert kind_display("soundbar") == ("soundbar", None)

    def test_an_alias_selects_its_key_with_no_raw(self):
        """The file says airconditioner and the dropdown says Air
        conditioner: the same thing in two spellings, so there is
        nothing to warn about and nothing to show beside it."""
        assert kind_display("airconditioner") == ("ac", None)
        assert kind_display("blinds") == ("windowcovering", None)

    def test_an_unplaceable_value_selects_other_and_keeps_the_word(self):
        assert kind_display("toaster") == ("other", "toaster")

    def test_no_kind_selects_nothing(self):
        """Not the same as Other. A wig nobody has described must not
        arrive in the editor pre-answered, or the next unrelated save
        writes a word nobody chose."""
        assert kind_display(None) == ("", None)
        assert kind_display("") == ("", None)


class TestTheExportSeedsOnlyWhatItIsSureOf:
    def _device(self, device_type: str) -> IRDevice:
        return IRDevice(
            name="Thing", device_type=device_type,
            commands=[IRCommand(
                name="On", protocol="PRONTO", code=PRONTO_A, repeat_count=0,
            )],
        )

    @pytest.mark.parametrize(
        ("device_type", "kind"),
        [("ac", "ac"), ("fan", "fan"), ("light", "light")],
    )
    def test_the_unmistakable_three_still_seed(self, device_type, kind):
        from custom_components.hair.wig_export import build_wig_from_device

        build = build_wig_from_device(self._device(device_type))
        assert build.wig is not None
        assert build.wig.kind == kind

    def test_a_screen_device_exports_with_no_kind(self):
        """A projection screen and a motorized blind are both SCREEN
        devices, and this table used to stamp "screen" on the blind.
        With windowcovering on the list the export cannot pick, so it
        says nothing and the dropdown asks."""
        from custom_components.hair.wig_export import build_wig_from_device

        build = build_wig_from_device(self._device("screen"))
        assert build.wig is not None
        assert build.wig.kind is None

    @pytest.mark.parametrize("device_type", ["media_player", "switch", "other"])
    def test_the_ambiguous_ones_still_say_nothing(self, device_type):
        from custom_components.hair.wig_export import build_wig_from_device

        build = build_wig_from_device(self._device(device_type))
        assert build.wig is not None
        assert build.wig.kind is None


# ---------------------------------------------------------------------
# The wire
# ---------------------------------------------------------------------


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.user.name = "dab"
    return conn


def _wire(hass, tmp_path, device=None):
    hass.config.config_dir = str(tmp_path)
    ensure_wigs_dir(tmp_path)
    store = MagicMock()
    store.get_device = MagicMock(
        side_effect=lambda did: device if device and did == device.id else None
    )
    store.get_all_devices = MagicMock(
        return_value=[device] if device else []
    )
    manager = MagicMock()
    manager.async_update_device = AsyncMock()
    hass.data[DOMAIN] = {
        "entry-1": {"store": store, "device_manager": manager}
    }
    return manager


def _closet_wig(tmp_path, wig, filename="thing.wig.json"):
    ensure_wigs_dir(tmp_path)
    path = wigs_dir(tmp_path) / filename
    path.write_text(serialize_wig(wig), encoding="utf-8")
    return path


def _wig(kind=None):
    return Wig(
        name="Thing", wig_id="u-1", kind=kind,
        signals=[WigSignal(alias="On", pronto=PRONTO_A)],
    )


async def _update(hass, tmp_path, **patch):
    conn = _conn()
    await ws_wigs_update(hass, conn, {
        "id": 1, "type": "hair/wigs/update",
        "filename": "thing.wig.json", **patch,
    })
    return conn.send_result.call_args.args[1]


class TestTheKindsCommand:
    @pytest.mark.asyncio
    async def test_it_serves_the_list_in_order(self, fake_hass):
        conn = _conn()
        ws_wigs_kinds(fake_hass, conn, {"id": 1, "type": "hair/wigs/kinds"})
        served = conn.send_result.call_args.args[1]["kinds"]
        assert [row["key"] for row in served] == [
            entry.key for entry in KIND_LIST
        ]
        assert served[0] == {
            "key": "tv",
            "device_type": "media_player",
            "label_key": "wigs.kind.tv",
        }

    @pytest.mark.asyncio
    async def test_every_label_key_it_serves_exists_in_every_locale(
        self, fake_hass
    ):
        """The panel translates what this hands it. A label key with no
        locale entry renders as the key itself, which is how a dropdown
        ends up reading "wigs.kind.dac"."""
        conn = _conn()
        ws_wigs_kinds(fake_hass, conn, {"id": 1, "type": "hair/wigs/kinds"})
        served = conn.send_result.call_args.args[1]["kinds"]
        for stem in LOCALE_NAMES:
            data = _locale(stem)
            for row in served:
                assert row["label_key"] in data, f"{stem}:{row['label_key']}"


class TestTheClosetEditorGatesWrites:
    @pytest.mark.asyncio
    async def test_a_list_key_saves(self, fake_hass, tmp_path):
        path = _closet_wig(tmp_path, _wig())
        _wire(fake_hass, tmp_path)
        result = await _update(fake_hass, tmp_path, kind="soundbar")
        assert result["success"] is True
        assert json.loads(path.read_text())["kind"] == "soundbar"

    @pytest.mark.asyncio
    async def test_an_alias_saves_as_its_key(self, fake_hass, tmp_path):
        """A write is a choice, so it lands on the list's word. This is
        the one place a spelling is folded into the file, and only
        because somebody just picked from the dropdown."""
        path = _closet_wig(tmp_path, _wig())
        _wire(fake_hass, tmp_path)
        result = await _update(fake_hass, tmp_path, kind="airconditioner")
        assert result["success"] is True
        assert json.loads(path.read_text())["kind"] == "ac"

    @pytest.mark.asyncio
    async def test_an_off_list_word_is_refused_and_the_file_is_untouched(
        self, fake_hass, tmp_path
    ):
        path = _closet_wig(tmp_path, _wig(kind="tv"))
        before = path.read_text()
        _wire(fake_hass, tmp_path)
        result = await _update(fake_hass, tmp_path, kind="toaster")
        assert result["success"] is False
        assert result["error_code"] == "invalid_kind"
        assert "toaster" in result["errors"][0]
        assert path.read_text() == before

    @pytest.mark.asyncio
    async def test_an_empty_string_clears_it(self, fake_hass, tmp_path):
        path = _closet_wig(tmp_path, _wig(kind="tv"))
        _wire(fake_hass, tmp_path)
        result = await _update(fake_hass, tmp_path, kind="")
        assert result["success"] is True
        assert "kind" not in json.loads(path.read_text())

    @pytest.mark.asyncio
    async def test_an_absent_kind_leaves_the_files_own_word_alone(
        self, fake_hass, tmp_path
    ):
        """THE ONE THAT PROTECTS THE FILE. The editor sends no kind at
        all unless somebody picked, so fixing the brand on a wig whose
        word the list cannot place leaves that word exactly where it
        was."""
        path = _closet_wig(tmp_path, _wig(kind="toaster"))
        _wire(fake_hass, tmp_path)
        result = await _update(fake_hass, tmp_path, brand="Testco")
        assert result["success"] is True
        saved = json.loads(path.read_text())
        assert saved["kind"] == "toaster"
        assert saved["brand"] == "Testco"


class TestTheSaveHandlerGatesWrites:
    def _device(self):
        return IRDevice(
            name="Speakers",
            commands=[IRCommand(
                name="On", protocol="PRONTO", code=PRONTO_A, repeat_count=0,
            )],
        )

    async def _save(self, fake_hass, device, **extra):
        conn = _conn()
        await ws_wigs_save(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/save", "device_id": device.id,
            "mode": "create", "name": "Bench", **extra,
        })
        return conn

    @pytest.mark.asyncio
    async def test_a_list_key_saves(self, fake_hass, tmp_path):
        device = self._device()
        _wire(fake_hass, tmp_path, device)
        conn = await self._save(fake_hass, device, kind="soundbar")
        result = conn.send_result.call_args.args[1]
        written = json.loads(
            (wigs_dir(tmp_path) / result["filename"]).read_text()
        )
        assert written["kind"] == "soundbar"

    @pytest.mark.asyncio
    async def test_an_alias_saves_as_its_key(self, fake_hass, tmp_path):
        device = self._device()
        _wire(fake_hass, tmp_path, device)
        conn = await self._save(fake_hass, device, kind="blinds")
        result = conn.send_result.call_args.args[1]
        written = json.loads(
            (wigs_dir(tmp_path) / result["filename"]).read_text()
        )
        assert written["kind"] == "windowcovering"

    @pytest.mark.asyncio
    async def test_an_off_list_word_is_refused_and_nothing_is_written(
        self, fake_hass, tmp_path
    ):
        device = self._device()
        _wire(fake_hass, tmp_path, device)
        conn = await self._save(fake_hass, device, kind="toaster")
        assert conn.send_error.called
        assert conn.send_error.call_args.args[1] == "invalid_kind"
        assert "toaster" in conn.send_error.call_args.args[2]
        assert list(wigs_dir(tmp_path).glob("*.wig.json")) == []


class TestTheKomecoFixtureIsLeftAlone:
    """The one bundled real-world wig says ``airconditioner``. It is a
    1,156-cell lattice several other suites are pinned to, and the
    point of the alias map is that a vocabulary change does not touch
    a byte of it."""

    @pytest.mark.asyncio
    async def test_it_lists_as_ac_without_being_rewritten(
        self, fake_hass, tmp_path
    ):
        ensure_wigs_dir(tmp_path)
        target = wigs_dir(tmp_path) / KOMECO.name
        original = KOMECO.read_bytes()
        target.write_bytes(original)
        _wire(fake_hass, tmp_path)

        conn = _conn()
        await ws_wigs_list(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/list",
        })
        rows = {
            row["filename"]: row
            for row in conn.send_result.call_args.args[1]["wigs"]
        }
        row = rows[KOMECO.name]
        # What the file says, and what the dropdown does with it.
        assert row["kind"] == "airconditioner"
        assert row["kind_key"] == "ac"
        assert row["kind_raw"] is None
        # And the file is the file.
        assert target.read_bytes() == original

    def test_the_fixture_still_says_what_it_always_said(self):
        assert json.loads(KOMECO.read_text())["kind"] == "airconditioner"


# ---------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------


class TestOneDropdownEverywhere:
    def test_the_closet_editor_renders_the_shared_field(self):
        text = _read("ir-wigs.ts")
        assert "renderKindField(" in text
        assert 'from "./ir-save-metadata-fields.js"' in text

    def test_the_save_dialogs_render_it_too(self):
        """The metadata form is shared by all three save routes, and
        kind joins it there rather than three times."""
        fields = _read("ir-save-metadata-fields.ts")
        assert "renderKindField(values, set)" in fields
        for name in (
            "ir-save-perfect-dialog.ts",
            "ir-save-new-dialog.ts",
            "ir-save-update-dialog.ts",
        ):
            text = _read(name)
            assert "renderMetadataFields(" in text, name
            assert "setKind:" in text, name
            assert "kind: this._kind," in text, name

    def test_the_options_come_from_the_wire(self):
        fields = _read("ir-save-metadata-fields.ts")
        block = fields.split("export function renderKindField", 1)[1]
        block = block.split("\n}", 1)[0]
        assert "values.kinds.map(" in block
        assert "t(entry.label_key)" in block
        assert "<select" in block

    def test_nothing_client_side_keeps_a_copy_of_the_words(self):
        """The drift this replaced was two hand-maintained arrays. A
        new word enters through KIND_LIST, so no TypeScript file may
        name one."""
        for name in (
            "ir-wigs.ts",
            "ir-wig-picker.ts",
            "ir-save-metadata-fields.ts",
        ):
            text = _read(name)
            assert "_kindSuggestions" not in text, name
            assert "wig-kind-suggestions" not in text, name
            assert '"settopbox"' not in text, name
            assert '"soundbar"' not in text, name

    def test_the_type_table_reads_the_list(self):
        """``_typeFromKind`` carried its own map, which is how "screen"
        came to exist there and in no suggestion list."""
        text = _read("ir-wigs.ts")
        block = text.split(
            "private _typeFromKind(kind: string | null | undefined): string {",
            1,
        )[1].split("\n    }", 1)[0]
        assert "this._kinds.find" in block
        assert "device_type" in block
        assert '"media_player"' not in block

    def test_an_untouched_dropdown_sends_no_kind(self):
        """Ruling 2 at the wire: the file keeps its word unless
        somebody picked a different one."""
        wigs = _read("ir-wigs.ts")
        assert "this._editKindTouched ? { kind: this._editKind } : {}" in wigs
        for name in (
            "ir-save-perfect-dialog.ts",
            "ir-save-new-dialog.ts",
            "ir-save-update-dialog.ts",
        ):
            assert "if (this._kindTouched) out.kind = this._kind;" in _read(
                name
            ), name

    def test_the_unplaceable_value_is_shown_not_hidden(self):
        fields = _read("ir-save-metadata-fields.ts")
        assert "wigs.editor.kind_file_value" in fields
        assert "values.kindRaw" in fields

    def test_the_picker_labels_through_the_locale(self):
        """It capitalised the stored word, which read "Settopbox" in
        every language."""
        text = _read("ir-wig-picker.ts")
        assert "_kindLabel(" in text
        assert "t(entry.label_key)" in text
        matcher = text.split("private _rowMatches", 1)[1].split(
            "\n    private", 1
        )[0]
        assert "this._kindLabel(wig)" in matcher


class TestTheLocalesCarryTheVocabulary:
    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_entry_has_a_label(self, locale):
        data = _locale(locale)
        for entry in KIND_LIST:
            assert entry.label_key in data, f"{locale}:{entry.label_key}"
            assert data[entry.label_key].strip(), entry.label_key

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_the_free_text_placeholder_is_retired(self, locale):
        """It prompted "tv, soundbar, candles..." into a box that no
        longer exists."""
        assert "wigs.editor.kind_placeholder" not in _locale(locale)

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_the_new_editor_copy_is_there(self, locale):
        data = _locale(locale)
        for key in (
            "wigs.editor.kind_unset",
            "wigs.editor.kind_file_value",
            "wigs.error.invalid_kind",
        ):
            assert key in data, f"{locale}:{key}"
        assert "{value}" in data["wigs.editor.kind_file_value"]
        assert "{value}" in data["wigs.error.invalid_kind"]


class TestTheDocumentPrintsTheList:
    """The format doc is what a wig author outside HAIR reads. A list
    that drifts from the code there is worse than no list, because it
    reads as authoritative."""

    def _doc(self) -> str:
        return (
            Path(__file__).parents[3] / "docs" / "wig-format.md"
        ).read_text(encoding="utf-8")

    def test_every_entry_has_a_row(self):
        doc = self._doc()
        labels = _locale("en")
        for entry in KIND_LIST:
            row = (
                f"| `{entry.key}` | {labels[entry.label_key]} "
                f"| `{entry.device_type}` |"
            )
            assert row in doc, row

    def test_it_says_files_are_never_rewritten(self):
        doc = self._doc()
        assert "Files are never rewritten" in doc
        assert "airconditioner" in doc
        assert "windowcovering" in doc
