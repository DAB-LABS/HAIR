"""A cover's device class (GH #313).

A screen Device, and a Remote typed as a screen, can say what kind of
cover it is: awning, blind, curtain, shade (the default), shutter,
garage door or gate. Home Assistant takes the entity's icon and its open
and closed words from that. Nothing else about the cover changes.

- The choice is stored on the entity config, only once it is made, and
  read back tolerantly: an unknown value is no choice, which is shade.
- The cover entity reports the stored kind, shade without one.
- ``device/update`` takes it for a Device; ``trigger-remote/set-cover-
  class`` takes it for a screen Remote, saves, and the Remote's entity
  shows it at once. Each refuses an unknown kind and writes nothing.
- Make a Remote and Make a Device carry it across, as they carry a
  fan's speed cycle.
- The panel: a Cover card in each settings dialog, the rules in
  ``cover-class.ts`` (run under node), and the strings in every locale
  (Traditional Chinese has them in English until they are translated).
"""
from __future__ import annotations

import inspect
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.cover import CoverDeviceClass

from custom_components.hair import websocket_api
from custom_components.hair.const import DeviceType
from custom_components.hair.cover import HAIRCoverEntity
from custom_components.hair.models import (
    COVER_DEVICE_CLASS_DEFAULT,
    COVER_DEVICE_CLASSES,
    EntityConfig,
    IRCommand,
    IRDevice,
    IRTrigger,
)
from custom_components.hair.remote_state import REMOTE_SETTINGS_COPIED
from custom_components.hair.tests.test_entities import (
    _device,
    _manager,
    _patch_write_state,
)
from custom_components.hair.tests.test_remote_state import (
    PRONTO,
    _bench_with,
    _remote,
)
from custom_components.hair.tests.test_websocket_api import (
    _make_connection,
    _wire_hass,
)
from custom_components.hair.websocket_api import (
    ws_set_trigger_remote_cover_class,
    ws_update_device,
)

FRONTEND = Path(__file__).parent.parent / "frontend"
SRC = FRONTEND / "src"
LOCALES = SRC / "locales"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
DOOR = "hair/trigger-remote/set-cover-class"

KINDS = ("awning", "blind", "curtain", "shade", "shutter", "garage", "gate")


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------


class TestTheModel:
    def test_the_kinds_and_the_default(self):
        assert COVER_DEVICE_CLASSES == KINDS
        assert COVER_DEVICE_CLASS_DEFAULT == "shade"

    def test_every_kind_is_one_home_assistant_knows(self):
        for kind in COVER_DEVICE_CLASSES:
            assert CoverDeviceClass(kind).value == kind

    @pytest.mark.parametrize("kind", KINDS)
    def test_a_kind_survives_a_round_trip(self, kind):
        config = EntityConfig(platform="cover", cover_device_class=kind)
        data = config.to_dict()
        assert data["cover_device_class"] == kind
        assert EntityConfig.from_dict(data).cover_device_class == kind

    def test_no_choice_writes_nothing(self):
        config = EntityConfig(platform="cover")
        assert config.cover_device_class is None
        assert "cover_device_class" not in config.to_dict()

    @pytest.mark.parametrize("stored", ["door", "window", "Garage", "", 3, ["gate"]])
    def test_an_unknown_stored_value_reads_as_no_choice(self, stored):
        data = {"platform": "cover", "cover_device_class": stored}
        assert EntityConfig.from_dict(data).cover_device_class is None

    def test_it_is_a_known_key(self):
        """Not reported as an unknown key on load."""
        from custom_components.hair import models

        assert "cover_device_class" in models._KNOWN_ENTITY_CONFIG


# ---------------------------------------------------------------------------
# The entity
# ---------------------------------------------------------------------------


def _cover(kind=None) -> HAIRCoverEntity:
    config = EntityConfig(
        platform="cover",
        command_mapping={"open_cover": "Up", "close_cover": "Down"},
        cover_device_class=kind,
    )
    entity = HAIRCoverEntity(
        _device(device_type=DeviceType.SCREEN, entity_config=config), _manager()
    )
    _patch_write_state(entity)
    return entity


class TestTheEntity:
    def test_no_choice_is_a_shade(self):
        assert _cover().device_class == CoverDeviceClass.SHADE

    @pytest.mark.parametrize("kind", KINDS)
    def test_it_reports_the_chosen_kind(self, kind):
        assert _cover(kind).device_class == CoverDeviceClass(kind)

    def test_a_value_set_around_the_model_is_still_a_shade(self):
        entity = _cover()
        entity._device.entity_config.cover_device_class = "window"
        assert entity.device_class == CoverDeviceClass.SHADE

    def test_a_new_choice_shows_without_a_new_entity(self):
        entity = _cover()
        entity._device.entity_config.cover_device_class = "garage"
        assert entity.device_class == CoverDeviceClass.GARAGE

    def test_it_is_a_property_not_a_fixed_attribute(self):
        assert "_attr_device_class" not in vars(HAIRCoverEntity)
        assert isinstance(vars(HAIRCoverEntity)["device_class"], property)


# ---------------------------------------------------------------------------
# The Device door
# ---------------------------------------------------------------------------


def _screen_device(kind=None) -> IRDevice:
    return IRDevice(
        id="screen-1",
        name="Patio Screen",
        device_type=DeviceType.SCREEN,
        commands=[IRCommand(id="c1", name="Up", protocol="NEC", code="0x1")],
        entity_config=EntityConfig(
            platform="cover",
            command_mapping={"open_cover": "Up"},
            cover_device_class=kind,
        ),
    )


async def _update(fake_hass, device, **fields):
    manager = MagicMock()
    manager.get_device.return_value = device
    manager.async_update_device = AsyncMock(side_effect=lambda d: d)
    _wire_hass(fake_hass, manager=manager)
    conn = _make_connection()
    await ws_update_device(fake_hass, conn, {
        "id": 4, "type": "hair/device/update", "device_id": device.id, **fields,
    })
    return conn, manager


class TestTheDeviceDoor:
    @pytest.mark.asyncio
    async def test_it_sets_the_kind(self, fake_hass):
        device = _screen_device()
        conn, manager = await _update(fake_hass, device, cover_device_class="garage")
        conn.send_error.assert_not_called()
        assert device.entity_config.cover_device_class == "garage"
        manager.async_update_device.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_null_goes_back_to_shade(self, fake_hass):
        device = _screen_device("blind")
        conn, _ = await _update(fake_hass, device, cover_device_class=None)
        conn.send_error.assert_not_called()
        assert device.entity_config.cover_device_class is None

    @pytest.mark.asyncio
    async def test_leaving_it_out_keeps_it(self, fake_hass):
        device = _screen_device("awning")
        await _update(fake_hass, device, name="Patio Awning")
        assert device.entity_config.cover_device_class == "awning"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", ["window", "Shade", ""])
    async def test_an_unknown_kind_is_refused_and_nothing_is_written(
        self, fake_hass, value
    ):
        device = _screen_device("curtain")
        conn, manager = await _update(
            fake_hass, device, name="Renamed", cover_device_class=value,
        )
        conn.send_error.assert_called_once()
        assert conn.send_error.call_args[0][1] == "invalid_format"
        assert "awning, blind, curtain, shade" in conn.send_error.call_args[0][2]
        assert device.name == "Patio Screen"
        assert device.entity_config.cover_device_class == "curtain"
        manager.async_update_device.assert_not_awaited()

    def test_the_schema_takes_it(self):
        source = inspect.getsource(websocket_api)
        head = source[: source.index("async def ws_update_device(")]
        head = head[head.rindex("@websocket_api.require_admin"):]
        assert 'vol.Optional("cover_device_class"): vol.Any(str, None)' in head


# ---------------------------------------------------------------------------
# The Remote door
# ---------------------------------------------------------------------------


async def _screen_remote_bench(fake_hass, kind=None):
    remote = _remote("screen", {"open_cover": "t1"})
    remote.entity_config.cover_device_class = kind
    return await _bench_with(fake_hass, [remote])


class TestTheRemoteDoor:
    @pytest.mark.asyncio
    async def test_it_sets_saves_and_the_entity_shows_it(self, fake_hass):
        bench = await _screen_remote_bench(fake_hass)
        assert bench.state_entity("rem1").device_class == CoverDeviceClass.SHADE
        bench.store.async_save.reset_mock()
        conn = await bench.ws(
            ws_set_trigger_remote_cover_class, type=DOOR,
            remote_id="rem1", cover_device_class="gate",
        )
        conn.send_error.assert_not_called()
        result = conn.send_result.call_args[0][1]
        assert result["remote_id"] == "rem1"
        assert result["cover_device_class"] == "gate"
        stored = bench.store.get_trigger_remote("rem1")
        assert stored.entity_config.cover_device_class == "gate"
        bench.store.async_save.assert_awaited_once()
        entity = bench.state_entity("rem1")
        assert entity.device_class == CoverDeviceClass.GATE
        entity.async_write_ha_state.assert_called()

    @pytest.mark.asyncio
    async def test_null_goes_back_to_shade(self, fake_hass):
        bench = await _screen_remote_bench(fake_hass, "shutter")
        assert bench.state_entity("rem1").device_class == CoverDeviceClass.SHUTTER
        conn = await bench.ws(
            ws_set_trigger_remote_cover_class, type=DOOR,
            remote_id="rem1", cover_device_class=None,
        )
        conn.send_error.assert_not_called()
        assert conn.send_result.call_args[0][1]["cover_device_class"] is None
        assert bench.state_entity("rem1").device_class == CoverDeviceClass.SHADE

    @pytest.mark.asyncio
    async def test_an_unknown_kind_is_refused_unsaved(self, fake_hass):
        bench = await _screen_remote_bench(fake_hass, "blind")
        bench.store.async_save.reset_mock()
        conn = await bench.ws(
            ws_set_trigger_remote_cover_class, type=DOOR,
            remote_id="rem1", cover_device_class="window",
        )
        assert conn.send_error.call_args[0][1] == "invalid_format"
        bench.store.async_save.assert_not_awaited()
        stored = bench.store.get_trigger_remote("rem1")
        assert stored.entity_config.cover_device_class == "blind"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("device_type", [None, "fan", "light"])
    async def test_only_a_screen_remote_takes_one(self, fake_hass, device_type):
        bench = await _bench_with(fake_hass, [_remote(device_type)])
        bench.store.async_save.reset_mock()
        conn = await bench.ws(
            ws_set_trigger_remote_cover_class, type=DOOR,
            remote_id="rem1", cover_device_class="garage",
        )
        assert conn.send_error.call_args[0][1] == "invalid_format"
        assert "Only a screen Remote" in conn.send_error.call_args[0][2]
        bench.store.async_save.assert_not_awaited()
        stored = bench.store.get_trigger_remote("rem1")
        assert stored.entity_config.cover_device_class is None

    @pytest.mark.asyncio
    async def test_an_unknown_remote(self, fake_hass):
        bench = await _screen_remote_bench(fake_hass)
        conn = await bench.ws(
            ws_set_trigger_remote_cover_class, type=DOOR,
            remote_id="ghost", cover_device_class="gate",
        )
        assert conn.send_error.call_args[0][1] == "not_found"

    @pytest.mark.asyncio
    async def test_not_configured(self, fake_hass):
        conn = _make_connection()
        await ws_set_trigger_remote_cover_class(fake_hass, conn, {
            "id": 1, "type": DOOR, "remote_id": "rem1", "cover_device_class": None,
        })
        assert conn.send_error.call_args[0][1] == "not_configured"

    @pytest.mark.asyncio
    async def test_the_list_carries_it(self, fake_hass):
        bench = await _screen_remote_bench(fake_hass, "awning")
        conn = await bench.ws(
            websocket_api.ws_list_trigger_remotes, type="hair/trigger-remotes/list",
        )
        row = conn.send_result.call_args[0][1][0]
        assert row["cover_device_class"] == "awning"

    def test_it_is_registered_for_admins(self):
        source = inspect.getsource(websocket_api)
        assert (
            "async_register_command(hass, ws_set_trigger_remote_cover_class)" in source
        )
        head = source[: source.index("async def ws_set_trigger_remote_cover_class(")]
        head = head[head.rindex("@websocket_api.require_admin"):]
        assert 'f"{WS_PREFIX}/trigger-remote/set-cover-class"' in head
        assert 'vol.Required("cover_device_class"): vol.Any(str, None)' in head


# ---------------------------------------------------------------------------
# Make a Remote and Make a Device
# ---------------------------------------------------------------------------


class TestTheCopies:
    def test_make_a_device_copies_it(self):
        assert "cover_device_class" in REMOTE_SETTINGS_COPIED

    @pytest.mark.asyncio
    async def test_make_a_remote_from_a_screen_takes_its_kind(self, fake_hass):
        from custom_components.hair.websocket_api import ws_device_make_remote

        bench = await _bench_with(fake_hass)
        device = IRDevice(
            id="dev1", name="Garage", device_type=DeviceType.SCREEN,
            commands=[IRCommand(id="c1", name="Up", protocol="PRONTO", code=PRONTO)],
            entity_config=EntityConfig(
                command_mapping={"open_cover": "Up"}, cover_device_class="garage",
            ),
        )
        bench.store.add_device(device)
        bench.data["device_manager"] = MagicMock(get_device=bench.store.get_device)
        conn = await bench.ws(
            ws_device_make_remote, type="hair/device/make-remote",
            device_id="dev1", name="Garage Remote",
        )
        remote = bench.store.get_trigger_remote(conn.send_result.call_args[0][1]["id"])
        assert remote.entity_config.cover_device_class == "garage"
        assert remote.device_type == DeviceType.SCREEN
        assert bench.state_entity(remote.id).device_class == CoverDeviceClass.GARAGE

    @pytest.mark.asyncio
    async def test_make_a_device_from_a_screen_remote_takes_its_kind(self, fake_hass):
        from custom_components.hair.websocket_api import ws_trigger_remote_make_device

        remote = _remote("screen", {"open_cover": "t1"})
        remote.entity_config.cover_device_class = "curtain"
        bench = await _bench_with(fake_hass, [remote], [
            IRTrigger(id="t1", name="Open", trigger_remote_id="rem1",
                      protocol="PRONTO", code=PRONTO, signal_fingerprint="fp1"),
        ])
        created: list[IRDevice] = []
        manager = MagicMock()
        manager.async_create_device = AsyncMock(side_effect=created.append)
        manager.async_update_device = AsyncMock()
        manager._auto_map_command = MagicMock()
        bench.data["device_manager"] = manager
        with patch(
            "custom_components.hair.websocket_api._device_full",
            AsyncMock(return_value={}),
        ):
            conn = await bench.ws(
                ws_trigger_remote_make_device, type="hair/trigger-remote/make-device",
                remote_id="rem1", name="Bedroom Curtain", device_type="screen",
                emitter_entity_ids=[],
            )
        conn.send_error.assert_not_called()
        assert created[0].entity_config.cover_device_class == "curtain"


# ---------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _method(text: str, name: str) -> str:
    body = text[text.index(name):]
    return body[: body.index("\n    }\n")]


DEVICE_DIALOG = "ir-device-settings-dialog.ts"
REMOTE_DIALOG = "ir-trigger-remote-settings-dialog.ts"


class TestThePanel:
    def test_a_screen_gets_the_cover_card(self):
        text = _read(DEVICE_DIALOG)
        sections = text[text.index("export function settingsSections"):]
        sections = sections[: sections.index("return sections;")]
        assert 'if (device.device_type === "screen") {\n        sections.push("cover");' in (
            sections
        )

    def test_the_device_dialog_reads_and_saves_it(self):
        text = _read(DEVICE_DIALOG)
        first = _method(text, "firstUpdated(): void {")
        assert "this._coverClass = coverClassShown(config?.cover_device_class);" in first
        save = _method(text, "private async _save()")
        assert (
            'if (sections.includes("cover")) {\n'
            "            patch.cover_device_class = coverClassForSave(this._coverClass);"
        ) in save
        body = _method(text, "private _renderBody()")
        assert 't("devsettings.cover_title")' in body
        assert "t(coverClassLabelKey(this._coverClass))" in body

    def test_both_dialogs_share_the_field(self):
        for name in (DEVICE_DIALOG, REMOTE_DIALOG):
            text = _read(name)
            assert 'import { renderCoverClassField } from "./ir-cover-class-field.js";' in text
            assert "renderCoverClassField(" in text
        field = _read("ir-cover-class-field.ts")
        assert "COVER_DEVICE_CLASSES.map(" in field
        assert 't("devsettings.cover_class_label")' in field
        assert 't("devsettings.cover_class_help")' in field

    def test_the_remote_dialog_gets_the_card_for_a_screen(self):
        text = _read(REMOTE_DIALOG)
        has = _method(text, "private get _hasCover()")
        assert 'return this.remote.device_type === "screen";' in has
        assert 'class="card card-cover ${this._coverOpen ? "open" : ""}"' in text
        assert "?hidden=${!this._hasCover}" in text
        first = _method(text, "firstUpdated(): void {")
        assert "coverClassShown(this.remote.cover_device_class)" in first

    def test_the_remote_dialog_saves_it_and_refreshes(self):
        text = _read(REMOTE_DIALOG)
        save = _method(text, "private async _save()")
        assert "this.api.setTriggerRemoteCoverClass(" in save
        assert "coverClassForSave(this._coverClass)" in save
        assert 'new CustomEvent("remote-cover-changed", {' in save
        assert "@remote-cover-changed=${this._onRemoteChanged}" in _read(
            "ha-panel-ir-devices.ts"
        )

    def test_the_api_calls(self):
        api = _read("api.ts")
        call = _method(api, "setTriggerRemoteCoverClass(")
        assert f'"{DOOR}"' in call
        assert "cover_device_class: coverDeviceClass" in call
        update = api[api.index("updateDevice("):]
        update = update[: update.index("): Promise<IRDevice>")]
        assert "cover_device_class: CoverDeviceClass | null;" in update

    def test_the_panel_list_matches_the_backend(self):
        text = _read("cover-class.ts")
        block = text[text.index("export const COVER_DEVICE_CLASSES"):]
        block = block[: block.index("];")]
        listed = [part.strip().strip('",') for part in block.split("\n")[1:] if part.strip()]
        assert tuple(listed) == COVER_DEVICE_CLASSES
        assert (
            "export const COVER_DEVICE_CLASS_DEFAULT: CoverDeviceClass = "
            f'"{COVER_DEVICE_CLASS_DEFAULT}";'
        ) in text


toolchain = pytest.mark.skipif(
    not TSC.exists() or shutil.which("node") is None,
    reason="frontend toolchain not installed (node_modules / node)",
)

DRIVER = """
import {
    COVER_DEVICE_CLASSES, COVER_DEVICE_CLASS_DEFAULT,
    coverClassForSave, coverClassLabelKey, coverClassShown,
} from "./cover-class.js";

const shown = {};
for (const stored of [null, undefined, "", "garage", "shade", "window", "Gate"]) {
    shown[String(stored)] = coverClassShown(stored);
}
const saves = {};
for (const kind of COVER_DEVICE_CLASSES) saves[kind] = coverClassForSave(kind);
console.log(JSON.stringify({
    kinds: COVER_DEVICE_CLASSES, fallback: COVER_DEVICE_CLASS_DEFAULT,
    shown, saves, label: coverClassLabelKey("garage"),
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("coverclassjs")
    subprocess.run(
        [
            str(TSC), "src/cover-class.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


@toolchain
class TestTheRules:
    def test_the_kinds_match_the_backend(self, run):
        assert tuple(run["kinds"]) == COVER_DEVICE_CLASSES
        assert run["fallback"] == COVER_DEVICE_CLASS_DEFAULT

    def test_what_the_menu_shows(self, run):
        assert run["shown"] == {
            "null": "shade", "undefined": "shade", "": "shade",
            "garage": "garage", "shade": "shade",
            "window": "shade", "Gate": "shade",
        }

    def test_shade_saves_as_no_choice(self, run):
        assert run["saves"] == {kind: (None if kind == "shade" else kind) for kind in KINDS}

    def test_the_label_key(self, run):
        assert run["label"] == "devsettings.cover_class_garage"


# ---------------------------------------------------------------------------
# The strings
# ---------------------------------------------------------------------------

STRINGS = (
    "devsettings.cover_title",
    "devsettings.cover_class_label",
    "devsettings.cover_class_help",
    *(f"devsettings.cover_class_{kind}" for kind in KINDS),
)


class TestTheStrings:
    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_locale_has_them(self, path):
        strings = json.loads(path.read_text(encoding="utf-8"))
        for key in STRINGS:
            assert strings.get(key, "").strip(), (path.stem, key)

    def test_twelve_locales(self):
        assert len(list(LOCALES.glob("*.json"))) == 12

    def test_the_english(self):
        strings = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert strings["devsettings.cover_title"] == "Cover"
        assert strings["devsettings.cover_class_garage"] == "Garage door"
        assert strings["devsettings.cover_class_shade"] == "Shade"
