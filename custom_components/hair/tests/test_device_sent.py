"""The climate card follows what HAIR sends (0.10.1 item 7, GH #105).

The contracts under test:

- ``device_manager._async_broadcast`` dispatches ``SIGNAL_DEVICE_SENT``
  exactly once per send, and ONLY when at least one emitter accepted it:
  a send that failed everywhere changed nothing on the unit.
- Coordinates travel structurally. Nothing parses a display name back
  into mode/fan/temp, so a STATE row minted from the card carries its
  cell in ``IRCommand.sent_state`` and a legacy one is stamped at setup
  by matching its Pronto against the device's CURRENT lattice.
- ``sent_state`` is NOT ``matrix_cell``. The second marks a porthole,
  and deleting a porthole deletes the lattice cell.
- The matrix entity follows a card SEND, a saved STATE row, a preset, a
  pinned retransmit and matrix off/on; the flat entity follows its
  mapped commands and moves nothing on an unmapped starred send.
- The entity ignores its own sends, so a service call writes state once.
- SENT ONLY: a heard-but-not-pinned matrix state never moves the card.
- The plug still has the last word on on/off, and an "off" verdict now
  clears the preset and the readout too.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import HVACMode

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import CommandSource, DeviceType
from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import EntityConfig, IRCommand, IRDevice
from custom_components.hair.power_monitor import SIGNAL_POWER_VERDICT
from custom_components.hair.send_signal import (
    ORIGIN_ENTITY,
    ORIGIN_MANAGER,
    SIGNAL_DEVICE_SENT,
    DeviceSent,
)
from custom_components.hair.storage import HAIRStore
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

# Real Pronto: the manager-level tests below go through build_command,
# which parses the hex, so readable tags would not survive the send.
P_OFF = "0000 006D 0002 0000 0020 0020 0040 0040"
P_ON = "0000 006D 0002 0000 0040 0040 0020 0020"
P_C_A_22 = "0000 006D 0002 0000 0020 0040 0020 0040"
P_C_A_23 = "0000 006D 0002 0000 0040 0020 0040 0020"
P_H_L_20 = "0000 006D 0002 0000 0060 0080 0060 0080"
P_STRANGER = "0000 006D 0002 0000 0080 0060 0080 0060"
STATE_ROW = "cool / fan: auto / 22"
CELL_22 = {"mode": "cool", "fan": "auto", "swing": None, "temp": 22.0}


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


def _matrix() -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool", "heat"],
        fan_modes=["auto", "low"],
        swing_modes=[],
        off=P_OFF,
        on=P_ON,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=P_C_A_22),
            ClimateCell(mode="cool", fan="auto", temp=23.0, pronto=P_C_A_23),
            ClimateCell(mode="heat", fan="low", temp=20.0, pronto=P_H_L_20),
        ],
    )


def _matrix_device(commands=None, starred=None) -> IRDevice:
    return IRDevice(
        id="dev-matrix",
        name="Living Room AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"],
        climate_matrix=True,
        commands=list(commands or []),
        entity_config=EntityConfig(
            platform="climate", starred=list(starred or [])
        ),
    )


def _flat_device(mapping=None, starred=None) -> IRDevice:
    return IRDevice(
        id="dev-flat",
        name="Bedroom AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"],
        commands=[
            IRCommand(
                id="c-off", name="Power Off",
                protocol="PRONTO", code=P_OFF,
            ),
            IRCommand(
                id="c-on", name="Power On", protocol="PRONTO", code=P_ON,
            ),
            IRCommand(
                id="c-cool", name="Mode: Cool",
                protocol="PRONTO", code=P_C_A_22,
            ),
            IRCommand(
                id="c-low", name="Fan: Low",
                protocol="PRONTO", code=P_C_A_23,
            ),
            IRCommand(
                id="c-24", name="Temp 24", protocol="PRONTO", code=P_H_L_20,
            ),
            IRCommand(
                id="c-sleep", name="Sleep",
                protocol="PRONTO", code=P_STRANGER,
            ),
        ],
        entity_config=EntityConfig(
            platform="climate",
            hvac_modes=["cool", "heat"],
            fan_modes=["auto", "low"],
            temperature_presets=[22, 24],
            command_mapping=dict(mapping or {}),
            starred=list(starred or []),
        ),
    )


async def _entity(device, matrix=None):
    """A climate entity wired up, with the manager mocked."""
    mgr = MagicMock()
    mgr.async_send_command = AsyncMock()
    mgr.async_send_matrix_cell = AsyncMock()
    mgr.async_get_matrix = AsyncMock(return_value=matrix)
    entity = HAIRClimateEntity(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    handlers: dict[str, object] = {}

    def _connect(hass_arg, signal, callback_fn):
        handlers[signal] = callback_fn
        return MagicMock()

    with patch(
        "custom_components.hair.climate.async_dispatcher_connect",
        side_effect=_connect,
    ):
        await entity.async_added_to_hass()
    return entity, mgr, handlers


def _sent(**kw) -> DeviceSent:
    kw.setdefault("device_id", "dev-matrix")
    return DeviceSent(**kw)


# ---------------------------------------------------------------------------
# The dispatch itself
# ---------------------------------------------------------------------------


@pytest.fixture
def manager(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        store._loaded = True
        factory = EntityFactory(fake_hass)
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(
                    return_value=MagicMock(id="ha-dev-1")
                ),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            yield DeviceManager(fake_hass, store, factory, "entry-1")


def _landing_manager(manager, *, land: bool = True):
    """Make the emitter loop land or fail, without touching the rest."""
    manager._hass.states.get = MagicMock(return_value=None)
    if land:
        return patch(
            "homeassistant.components.infrared.async_send_command",
            new=AsyncMock(),
        )
    return patch(
        "homeassistant.components.infrared.async_send_command",
        new=AsyncMock(side_effect=RuntimeError("no")),
    )


@pytest.mark.asyncio
async def test_a_landed_send_dispatches_once(manager):
    device = _flat_device()
    manager._store.add_device(device)
    sent: list[DeviceSent] = []

    with _landing_manager(manager), patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=lambda hass, signal, payload: sent.append(
            (signal, payload)
        ),
    ):
        await manager.async_send_command("dev-flat", "c-cool")

    assert len(sent) == 1
    signal, payload = sent[0]
    assert signal == SIGNAL_DEVICE_SENT
    assert payload.device_id == "dev-flat"
    assert payload.command_id == "c-cool"
    assert payload.command_name == "Mode: Cool"
    assert payload.origin == ORIGIN_MANAGER


@pytest.mark.asyncio
async def test_a_send_that_landed_nowhere_dispatches_nothing(manager):
    """No emitter accepted it, so nothing on the unit changed."""
    device = _flat_device()
    manager._store.add_device(device)
    sent: list = []

    with _landing_manager(manager, land=False), patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=lambda *a: sent.append(a),
    ), pytest.raises(RuntimeError):
        await manager.async_send_command("dev-flat", "c-cool")

    assert sent == []


@pytest.mark.asyncio
async def test_a_starred_command_says_so(manager):
    device = _flat_device(starred=["Sleep"])
    manager._store.add_device(device)
    sent: list = []

    with _landing_manager(manager), patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=lambda hass, signal, payload: sent.append(payload),
    ):
        await manager.async_send_command("dev-flat", "c-sleep")
        await manager.async_send_command("dev-flat", "c-cool")

    assert sent[0].starred is True
    assert sent[1].starred is False


@pytest.mark.asyncio
async def test_a_state_rows_coordinates_ride_its_send(manager):
    command = IRCommand(
        id="c-state", name=STATE_ROW, source=CommandSource.MATRIX,
        protocol="PRONTO", code=P_C_A_22, sent_state=dict(CELL_22),
    )
    device = _matrix_device([command])
    manager._store.add_device(device)
    sent: list = []

    with _landing_manager(manager), patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=lambda hass, signal, payload: sent.append(payload),
    ):
        await manager.async_send_command("dev-matrix", "c-state")

    assert sent[0].matrix_cell == CELL_22
    assert sent[0].power is None


@pytest.mark.asyncio
async def test_a_power_state_row_says_power_not_coordinates(manager):
    command = IRCommand(
        id="c-off", name="Off", source=CommandSource.MATRIX,
        protocol="PRONTO", code=P_OFF, sent_state={"power": "off"},
    )
    device = _matrix_device([command])
    manager._store.add_device(device)
    sent: list = []

    with _landing_manager(manager), patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=lambda hass, signal, payload: sent.append(payload),
    ):
        await manager.async_send_command("dev-matrix", "c-off")

    assert sent[0].power == "off"
    assert sent[0].matrix_cell is None


@pytest.mark.asyncio
async def test_a_matrix_cell_send_carries_what_the_caller_resolved(manager):
    device = _matrix_device()
    manager._store.add_device(device)
    sent: list = []

    with _landing_manager(manager), patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=lambda hass, signal, payload: sent.append(payload),
    ):
        await manager.async_send_matrix_cell(
            "dev-matrix", STATE_ROW, P_C_A_22, 1, cell=dict(CELL_22)
        )

    assert sent[0].matrix_cell == CELL_22
    assert sent[0].command_name == STATE_ROW
    assert sent[0].command_id is None


# ---------------------------------------------------------------------------
# The setup backfill
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_backfill_stamps_a_legacy_state_row(manager):
    command = IRCommand(
        id="c-state", name=STATE_ROW, source=CommandSource.MATRIX,
        protocol="PRONTO", code=P_C_A_22,
    )
    device = _matrix_device([command])
    manager._store.add_device(device)
    manager._matrix_cache["dev-matrix"] = _matrix()

    assert await manager.async_backfill_sent_states() == 1

    assert command.sent_state == CELL_22


@pytest.mark.asyncio
async def test_the_backfill_stamps_the_power_codes(manager):
    off = IRCommand(
        id="c-off", name="Off", source=CommandSource.MATRIX,
        protocol="PRONTO", code=P_OFF,
    )
    on = IRCommand(
        id="c-on", name="On", source=CommandSource.MATRIX,
        protocol="PRONTO", code=P_ON,
    )
    device = _matrix_device([off, on])
    manager._store.add_device(device)
    manager._matrix_cache["dev-matrix"] = _matrix()

    await manager.async_backfill_sent_states()

    assert off.sent_state == {"power": "off"}
    assert on.sent_state == {"power": "on"}


@pytest.mark.asyncio
async def test_the_backfill_leaves_an_unmatched_row_alone(manager):
    """A re-fit rewrote the lattice: the honest answer is no answer,
    and an unstamped row simply does not move the card."""
    command = IRCommand(
        id="c-state", name=STATE_ROW, source=CommandSource.MATRIX,
        protocol="PRONTO", code=P_STRANGER,
    )
    device = _matrix_device([command])
    manager._store.add_device(device)
    manager._matrix_cache["dev-matrix"] = _matrix()

    assert await manager.async_backfill_sent_states() == 0

    assert command.sent_state is None


@pytest.mark.asyncio
async def test_the_backfill_never_touches_a_porthole_row(manager):
    """A porthole is a view onto the cell; deleting one deletes the
    cell. It has no business gaining a second coordinate stamp."""
    command = IRCommand(
        id="c-hole", name="cool/auto/22", source=CommandSource.MATRIX,
        protocol="PRONTO", code=P_C_A_22, matrix_cell=dict(CELL_22),
    )
    device = _matrix_device([command])
    manager._store.add_device(device)
    manager._matrix_cache["dev-matrix"] = _matrix()

    await manager.async_backfill_sent_states()

    assert command.sent_state is None


@pytest.mark.asyncio
async def test_the_backfill_ignores_ordinary_commands(manager):
    command = IRCommand(id="c1", name="Power", protocol="PRONTO", code=P_OFF)
    device = _matrix_device([command])
    manager._store.add_device(device)
    manager._matrix_cache["dev-matrix"] = _matrix()

    await manager.async_backfill_sent_states()

    assert command.sent_state is None


@pytest.mark.asyncio
async def test_the_backfill_is_a_no_op_the_second_time(manager):
    command = IRCommand(
        id="c-state", name=STATE_ROW, source=CommandSource.MATRIX,
        protocol="PRONTO", code=P_C_A_22,
    )
    device = _matrix_device([command])
    manager._store.add_device(device)
    manager._matrix_cache["dev-matrix"] = _matrix()

    assert await manager.async_backfill_sent_states() == 1
    assert await manager.async_backfill_sent_states() == 0


# ---------------------------------------------------------------------------
# The matrix entity follows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_matrix_card_follows_a_cell_send():
    entity, _mgr, handlers = await _entity(_matrix_device(), _matrix())
    entity._hvac_mode = HVACMode.OFF
    entity._fan_mode = "low"

    handlers[SIGNAL_DEVICE_SENT](_sent(
        command_name=STATE_ROW, matrix_cell=dict(CELL_22)
    ))

    assert entity.hvac_mode == HVACMode.COOL
    assert entity.fan_mode == "auto"
    assert entity.target_temperature == 22.0
    assert entity.extra_state_attributes["matrix_cell"] == STATE_ROW
    entity.async_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_the_matrix_card_follows_power_off_and_on():
    entity, _mgr, handlers = await _entity(_matrix_device(), _matrix())
    entity._hvac_mode = HVACMode.HEAT

    handlers[SIGNAL_DEVICE_SENT](_sent(command_name="Off", power="off"))
    assert entity.hvac_mode == HVACMode.OFF
    assert entity.extra_state_attributes["matrix_cell"] == "Off"

    handlers[SIGNAL_DEVICE_SENT](_sent(command_name="On", power="on"))
    # The mode HAIR last sent, not a guess.
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.extra_state_attributes["matrix_cell"] == "On"


@pytest.mark.asyncio
async def test_a_send_with_no_coordinates_moves_no_dimension():
    entity, _mgr, handlers = await _entity(_matrix_device(), _matrix())
    entity._hvac_mode = HVACMode.COOL
    entity._fan_mode = "auto"
    entity._target_temperature = 22.0
    entity.async_write_ha_state.reset_mock()

    handlers[SIGNAL_DEVICE_SENT](_sent(command_name="Beep"))

    assert entity.hvac_mode == HVACMode.COOL
    assert entity.fan_mode == "auto"
    assert entity.target_temperature == 22.0
    # Nothing changed and no preset moved, so nothing is written.
    entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_a_starred_send_sets_the_preset_and_any_other_clears_it():
    device = _matrix_device(starred=[STATE_ROW])
    entity, _mgr, handlers = await _entity(device, _matrix())

    handlers[SIGNAL_DEVICE_SENT](_sent(
        command_name=STATE_ROW, matrix_cell=dict(CELL_22), starred=True
    ))
    assert entity.preset_mode == STATE_ROW

    handlers[SIGNAL_DEVICE_SENT](_sent(
        command_name="cool / fan: auto / 23",
        matrix_cell={
            "mode": "cool", "fan": "auto", "swing": None, "temp": 23.0,
        },
    ))
    assert entity.preset_mode is None


@pytest.mark.asyncio
async def test_the_entity_ignores_its_own_send():
    """The setter already wrote the state, with the exact cell in hand."""
    entity, _mgr, handlers = await _entity(_matrix_device(), _matrix())
    entity._hvac_mode = HVACMode.OFF
    entity.async_write_ha_state.reset_mock()

    handlers[SIGNAL_DEVICE_SENT](_sent(
        command_name=STATE_ROW, matrix_cell=dict(CELL_22),
        origin=ORIGIN_ENTITY,
    ))

    assert entity.hvac_mode == HVACMode.OFF
    entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_a_send_to_another_device_is_ignored():
    entity, _mgr, handlers = await _entity(_matrix_device(), _matrix())
    entity._hvac_mode = HVACMode.OFF
    entity.async_write_ha_state.reset_mock()

    handlers[SIGNAL_DEVICE_SENT](DeviceSent(
        device_id="someone-else", command_name=STATE_ROW,
        matrix_cell=dict(CELL_22),
    ))

    assert entity.hvac_mode == HVACMode.OFF
    entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_a_service_call_writes_state_once():
    """Own-origin sends must not double-apply through the handler."""
    entity, mgr, handlers = await _entity(_matrix_device(), _matrix())
    entity._fan_mode = "auto"
    entity.async_write_ha_state.reset_mock()

    await entity.async_set_hvac_mode(HVACMode.COOL)
    # The dispatch the manager would have raised, tagged as this
    # entity's own.
    kwargs = mgr.async_send_matrix_cell.await_args.kwargs
    handlers[SIGNAL_DEVICE_SENT](_sent(
        command_name=STATE_ROW, matrix_cell=kwargs["cell"],
        origin=kwargs["origin"],
    ))

    assert entity.async_write_ha_state.call_count == 1


# ---------------------------------------------------------------------------
# The flat entity follows
# ---------------------------------------------------------------------------


FLAT_MAPPING = {
    "turn_off": "Power Off",
    "turn_on": "Power On",
    "mode_cool": "Mode: Cool",
    "fan_low": "Fan: Low",
    "temp_24": "Temp 24",
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,check",
    [
        ("Mode: Cool", lambda e: e.hvac_mode == HVACMode.COOL),
        ("Fan: Low", lambda e: e.fan_mode == "low"),
        ("Temp 24", lambda e: e.target_temperature == 24.0),
    ],
)
async def test_the_flat_card_follows_a_mapped_command(name, check):
    device = _flat_device(FLAT_MAPPING)
    entity, _mgr, handlers = await _entity(device)

    handlers[SIGNAL_DEVICE_SENT](DeviceSent(
        device_id="dev-flat", command_name=name
    ))

    assert check(entity)


@pytest.mark.asyncio
async def test_the_flat_card_follows_power_off_and_on():
    device = _flat_device(FLAT_MAPPING)
    entity, _mgr, handlers = await _entity(device)
    entity._hvac_mode = HVACMode.COOL

    handlers[SIGNAL_DEVICE_SENT](DeviceSent(
        device_id="dev-flat", command_name="Power Off"
    ))
    assert entity.hvac_mode == HVACMode.OFF

    handlers[SIGNAL_DEVICE_SENT](DeviceSent(
        device_id="dev-flat", command_name="Power On"
    ))
    assert entity.hvac_mode == HVACMode.AUTO


@pytest.mark.asyncio
async def test_an_unmapped_starred_send_sets_the_preset_only():
    """mode0192's own suggestion for special-function presets."""
    device = _flat_device(FLAT_MAPPING, starred=["Sleep"])
    entity, _mgr, handlers = await _entity(device)
    entity._hvac_mode = HVACMode.COOL
    entity._fan_mode = "auto"

    handlers[SIGNAL_DEVICE_SENT](DeviceSent(
        device_id="dev-flat", command_name="Sleep", starred=True
    ))

    assert entity.preset_mode == "Sleep"
    assert entity.hvac_mode == HVACMode.COOL
    assert entity.fan_mode == "auto"


@pytest.mark.asyncio
async def test_an_unmapped_unstarred_send_moves_nothing():
    device = _flat_device(FLAT_MAPPING)
    entity, _mgr, handlers = await _entity(device)
    entity._hvac_mode = HVACMode.COOL
    entity.async_write_ha_state.reset_mock()

    handlers[SIGNAL_DEVICE_SENT](DeviceSent(
        device_id="dev-flat", command_name="Swing"
    ))

    assert entity.hvac_mode == HVACMode.COOL
    entity.async_write_ha_state.assert_not_called()


# ---------------------------------------------------------------------------
# Coexistence with the power sensor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_off_then_plug_off_is_one_off():
    """The plug agreeing with the send is a no-op verdict."""
    entity, _mgr, handlers = await _entity(_matrix_device(), _matrix())
    entity._hvac_mode = HVACMode.COOL

    handlers[SIGNAL_DEVICE_SENT](_sent(command_name="Off", power="off"))
    writes = entity.async_write_ha_state.call_count
    handlers[SIGNAL_POWER_VERDICT]("dev-matrix", "off")

    assert entity.hvac_mode == HVACMode.OFF
    # The verdict writes its own state; what matters is that the mode
    # did not bounce and the remembered mode is still the sent one.
    assert entity._last_active_hvac_mode == HVACMode.COOL
    assert entity.async_write_ha_state.call_count > writes


@pytest.mark.asyncio
async def test_a_send_on_the_unit_never_got_is_corrected_by_the_plug():
    entity, _mgr, handlers = await _entity(_matrix_device(), _matrix())
    entity._hvac_mode = HVACMode.OFF
    entity._last_active_hvac_mode = HVACMode.COOL

    handlers[SIGNAL_DEVICE_SENT](_sent(command_name="On", power="on"))
    assert entity.hvac_mode == HVACMode.COOL

    handlers[SIGNAL_POWER_VERDICT]("dev-matrix", "off")
    assert entity.hvac_mode == HVACMode.OFF


@pytest.mark.asyncio
async def test_a_plug_off_clears_the_preset_and_the_readout():
    device = _matrix_device(starred=[STATE_ROW])
    entity, _mgr, handlers = await _entity(device, _matrix())
    handlers[SIGNAL_DEVICE_SENT](_sent(
        command_name=STATE_ROW, matrix_cell=dict(CELL_22), starred=True
    ))
    assert entity.preset_mode == STATE_ROW

    handlers[SIGNAL_POWER_VERDICT]("dev-matrix", "off")

    assert entity.preset_mode is None
    assert entity.extra_state_attributes["matrix_cell"] == "Off"


@pytest.mark.asyncio
async def test_a_plug_on_restores_the_last_sent_mode():
    entity, _mgr, handlers = await _entity(_matrix_device(), _matrix())
    handlers[SIGNAL_DEVICE_SENT](_sent(
        command_name="heat / fan: low / 20",
        matrix_cell={
            "mode": "heat", "fan": "low", "swing": None, "temp": 20.0,
        },
    ))
    assert entity.hvac_mode == HVACMode.HEAT

    handlers[SIGNAL_POWER_VERDICT]("dev-matrix", "off")
    handlers[SIGNAL_POWER_VERDICT]("dev-matrix", "on")

    assert entity.hvac_mode == HVACMode.HEAT


@pytest.mark.asyncio
async def test_the_subscription_is_dropped_on_removal():
    entity, _mgr, _handlers = await _entity(_matrix_device(), _matrix())
    unsub = entity._device_sent_unsub
    assert unsub is not None

    await entity.async_will_remove_from_hass()

    unsub.assert_called_once()
    assert entity._device_sent_unsub is None


# ---------------------------------------------------------------------------
# SENT ONLY (the ruling, pinned)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_heard_state_on_an_unpinned_remote_dispatches_nothing():
    """The whole ruling in one test. "State changes should only happen
    when it's sent to a device, not when it's heard from one" -- a
    matrix Remote hearing the wall handset moves no card unless it is
    PINNED, and then it is the pinned SEND that does."""
    from custom_components.hair.matrix_listener import (
        MatrixListener,
        build_cell_index,
    )
    from custom_components.hair.models import TriggerRemote
    from custom_components.hair.wig_identity import wig_signal_identity

    lattice = ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0,
        modes=["cool"], fan_modes=["auto"], swing_modes=[],
        off="0000 006D 0002 0000 0020 0020 0040 0040",
        cells=[ClimateCell(
            mode="cool", fan="auto", temp=22.0,
            pronto="0000 006D 0002 0000 0020 0040 0020 0040",
        )],
    )
    remote = TriggerRemote(
        id="r1", name="Wall handset", climate_matrix=True,
        pinned_device_ids=[],
    )
    store = MagicMock()
    store.get_all_trigger_remotes = MagicMock(return_value=[remote])
    store.update_trigger_remote = MagicMock()
    store.async_save = AsyncMock()
    hass = MagicMock()
    hass.config.config_dir = "/config"
    hass.config.units.temperature_unit = "°C"
    hass.bus.async_fire = MagicMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
    listener = MatrixListener(hass, store)
    listener._index_cache["r1"] = build_cell_index(lattice)
    identity = wig_signal_identity(lattice.cells[0].pronto)
    dispatched: list = []

    with patch(
        "custom_components.hair.device_manager.async_dispatcher_send",
        side_effect=lambda *a: dispatched.append(a),
    ):
        heard = await listener.on_signal_captured(
            identity.fingerprint, identity.byte_hash,
            identity.decoded_fingerprint, None,
        )

    # It WAS heard -- LAST HEARD still updates, the event still fires.
    assert heard == ["r1"]
    # And nothing was sent, so no card moved.
    assert dispatched == []
