"""A press whose code the file stores under several settings.

A file stores dry once per temperature with one code when the unit
ignores temperature in dry, and the cell index, which keeps the last
claimant of a shared key, answered every such press with the last of
those cells. The handset sent dry at 24; HAIR heard "dry / fan: auto /
30", a pinned unit's card moved its dial to 30, and the next cool from
Home Assistant went out at 30. The air always got the right bytes; the
card, the readout and the next send did not get the right setting.

The contracts under test, end to end through a real ``MatrixListener``
and a real climate entity:

- The bytes a pinned device is sent never change, for any press, any
  pairing and any state the entity could be in. The expected bytes are
  a golden written before the change (``merged_group_shapes``).
- The card keeps a dimension the press does not pin down only where
  the result is a cell that carries the code that went out, and keeps
  its temperature where the unit demonstrably ignores it.
- A send that cannot say which setting it was is named as the set it
  could be ("dry / fan: auto / 18-30"), so no "current" tile rings a
  setting nobody chose.
- The device's own group decides, never the remote's.

Every lattice here is synthetic or a committed fixture; see
``merged_group_shapes`` for how each was built.
"""
from __future__ import annotations

import itertools
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import HVACMode

from custom_components.hair import matrix_listener as _ml
from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DeviceType
from custom_components.hair.matrix_listener import MatrixListener, build_cell_index
from custom_components.hair.models import IRDevice, TriggerRemote
from custom_components.hair.send_signal import ORIGIN_ENTITY, ORIGIN_MANAGER, DeviceSent
from custom_components.hair.wig_climate import cell_display_name, spanned_display_name
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, cell_key

from . import merged_group_shapes as shapes
from .merged_group_shapes import (
    GOLDEN,
    golden_benches,
    press_identity,
    sent_row,
)

# ---------------------------------------------------------------------------
# A remote pinned to a device whose climate entity is live
# ---------------------------------------------------------------------------


class _Manager:
    """The device side: its lattice, its entity's provider, its sends.

    A pinned send is handed to the entity the way ``SIGNAL_DEVICE_SENT``
    hands it; the entity's own sends are recorded and not echoed, as
    the real dispatcher handler ignores them.
    """

    def __init__(self, matrix: ClimateMatrix) -> None:
        self.matrix = matrix
        self.sends: list[SimpleNamespace] = []
        self.entity: HAIRClimateEntity | None = None
        self._providers: dict = {}

    async def async_get_matrix(self, device_id):
        return self.matrix

    def register_climate_state(self, device_id, provider):
        self._providers[device_id] = provider

    def unregister_climate_state(self, device_id, provider):
        if self._providers.get(device_id) == provider:
            self._providers.pop(device_id, None)

    def climate_state(self, device_id):
        provider = self._providers.get(device_id)
        return None if provider is None else provider()

    async def async_send_matrix_cell(
        self, device_id, cell_name, pronto, send_count=1,
        heard_future=None, pinned=False, cell=None, power=None,
        origin=None,
    ):
        self.sends.append(SimpleNamespace(
            name=cell_name, pronto=pronto, send_count=send_count,
            pinned=pinned, cell=cell, power=power, origin=origin,
        ))
        if origin != ORIGIN_ENTITY and self.entity is not None:
            self.entity._handle_device_sent(DeviceSent(
                device_id=device_id, command_name=cell_name,
                matrix_cell=dict(cell) if cell else None, power=power,
                origin=origin or ORIGIN_MANAGER,
            ))


def _through_disk(index, tmp_path, owner: str):
    """The index as a restart reads it back: through JSON, on disk."""
    from custom_components.hair.matrix_store import (
        load_cell_index,
        write_cell_index,
    )

    payload = _ml._index_to_payload(index, "h1", "C")
    assert write_cell_index(tmp_path, owner, payload) is True
    restored = _ml._payload_to_index(load_cell_index(tmp_path, owner))
    assert restored is not None
    return restored


class _Pair:
    """A matrix remote pinned to one matrix device with a live entity."""

    def __init__(self, remote_matrix, device_matrix, remote_index,
                 device_index, *, provider: bool = True) -> None:
        self.remote = TriggerRemote(
            id="r1", name="Handset", climate_matrix=True,
            pinned_device_ids=["dev-1"],
        )
        store = MagicMock()
        store.get_all_trigger_remotes = MagicMock(return_value=[self.remote])
        store.update_trigger_remote = MagicMock()
        store.async_save = AsyncMock()
        device = MagicMock(id="dev-1", climate_matrix=True)
        device.name = "Unit"
        store.get_device = MagicMock(return_value=device)
        self.tasks: list = []
        hass = MagicMock()
        hass.config.config_dir = "/nonexistent-config"
        hass.config.units.temperature_unit = "°C"
        hass.async_create_task = MagicMock(side_effect=self.tasks.append)
        hass.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )
        self.hass = hass
        self.tm = MagicMock()
        self.tm.resolve_receiver_area = MagicMock(return_value=(None, None))
        self.tm.dispatch_cell_retransmit = MagicMock(return_value=True)
        self.manager = _Manager(device_matrix)
        if not provider:
            self.manager.climate_state = None
        self.listener = MatrixListener(hass, store, self.tm, self.manager)
        self.listener._matrix_cache["r1"] = remote_matrix
        self.listener._index_cache["r1"] = remote_index
        if device_index is not None:
            self.listener._index_cache["dev-1"] = device_index
        self.entity: HAIRClimateEntity | None = None

    async def add_entity(self) -> HAIRClimateEntity:
        entity = HAIRClimateEntity(IRDevice(
            id="dev-1", name="Unit", device_type=DeviceType.AC,
            emitter_entity_ids=["infrared.e"], climate_matrix=True,
        ), self.manager)
        entity.async_write_ha_state = MagicMock()
        entity.hass = MagicMock()
        entity.hass.config.units.temperature_unit = "°C"
        await entity.async_added_to_hass()
        self.entity = self.manager.entity = entity
        return entity

    def card(self, hvac, fan=None, swing=None, temp=None) -> None:
        entity = self.entity
        entity._hvac_mode = hvac
        entity._fan_mode = fan
        entity._swing_mode = swing
        entity._target_temperature = temp

    async def drain(self) -> None:
        while self.tasks:
            batch, self.tasks[:] = list(self.tasks), []
            for coro in batch:
                await coro

    async def press(self, pronto: str):
        """A handset press, heard and sent; the send, or None."""
        decoded, fp, bh, norm, covers = press_identity(pronto)
        self.tm.dispatch_cell_retransmit.reset_mock()
        await self.listener.on_signal_captured(
            fp, bh, decoded, None, norm, covers,
        )
        await self.drain()
        self.listener._recent_hits.clear()  # past the window: a new press
        if not self.tm.dispatch_cell_retransmit.called:
            return None
        key = self.tm.dispatch_cell_retransmit.call_args.args[2]
        before = len(self.manager.sends)
        await self.listener.async_send_pinned_cell("dev-1", key)
        await self.drain()
        return (
            self.manager.sends[before]
            if len(self.manager.sends) > before else None
        )


async def _pair(remote_matrix, device_matrix=None, *, from_disk=False,
                tmp_path=None, provider=True, device_index=...):
    """A ready pair: both indexes built, the device's through disk when
    asked, and the entity added (so its provider is registered)."""
    device_matrix = remote_matrix if device_matrix is None else device_matrix
    remote_index = build_cell_index(remote_matrix)
    if device_index is ...:
        device_index = (
            remote_index if device_matrix is remote_matrix
            else build_cell_index(device_matrix)
        )
        if from_disk:
            device_index = _through_disk(device_index, tmp_path, "dev-1")
    pair = _Pair(remote_matrix, device_matrix, remote_index, device_index,
                 provider=provider)
    await pair.add_entity()
    return pair


def _cell(matrix, mode, fan, swing, temp, cells=None):
    for cell in matrix.cells if cells is None else cells:
        if (cell.mode, cell.fan, cell.swing, cell.temp) == (
            mode, fan, swing, None if temp is None else float(temp)
        ):
            return cell
    raise KeyError((mode, fan, swing, temp))


def _every_name(matrix) -> set[str]:
    """Every concrete cell name the device card could ring as current."""
    return {cell_display_name(cell) for cell in matrix.cells}


# ---------------------------------------------------------------------------
# 1. The bytes never change: the golden, swept against every state
# ---------------------------------------------------------------------------


def _states(state: dict | None) -> list[dict | None]:
    """Every current state worth trying against one resolved send.

    For a send with a group: the product of each spanned dimension's
    values, None, an outsider and (for temperature) an off-grid value,
    which is where a wrong sibling step would show as mixed states;
    plus OFF. Without a group the provider is never consulted, so a
    handful of states proves it.
    """
    if state is None or "power" in state:
        return [None]
    coords = {dim: state.get(dim) for dim in ("mode", "fan", "swing", "temp")}
    spanned = state.get("spanned")
    if not spanned:
        return [None, dict(coords), {**coords, "mode": None}]
    axes = []
    for dim in ("mode", "fan", "swing", "temp"):
        if dim in spanned:
            values = [*spanned[dim], None, f"outsider-{dim}"]
            if dim == "temp":
                temps = [v for v in spanned[dim] if v is not None]
                values[-1] = (min(temps) if temps else 20.0) - 1.89
            axes.append(values)
        else:
            axes.append([coords[dim]])
    states: list[dict | None] = [None]
    for combo in itertools.product(*axes):
        states.append(dict(zip(("mode", "fan", "swing", "temp"), combo,
                               strict=True)))
    states.append({**coords, "mode": None})
    return states


@pytest.mark.asyncio
async def test_no_current_state_changes_the_bytes_a_pinned_device_is_sent():
    """The owner's rule as a test. Every row of the golden written at
    5e0bd0b2, before any of this existed, against the new code, under
    every state the device's entity could report."""
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["rows"]
    compared = resolved = 0
    differ: list = []
    for source, name, bench, pressed in golden_benches():
        column = golden[source][name]
        assert len(column) == len(pressed), (source, name)
        swept: dict = {}
        for position, cell in enumerate(pressed):
            heard = bench.hear(cell.pronto)
            key = None if heard is None else (id(heard[0]), heard[1])
            if key not in swept:
                first = await bench.resolve(heard, None)
                rows = {sent_row(first)}
                for state in _states(None if first is None else first[3]):
                    rows.add(sent_row(await bench.resolve(heard, state)))
                    resolved += 1
                swept[key] = rows
            compared += 1
            if swept[key] != {column[position]}:
                differ.append((source, name, position, column[position],
                               sorted(swept[key], key=str)))
    assert compared == json.loads(
        GOLDEN.read_text(encoding="utf-8"))["row_count"]
    assert resolved > compared
    assert differ == []


# ---------------------------------------------------------------------------
# 2. The #183 case: a dry press leaves the dial where the user put it
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("from_disk", [False, True])
async def test_a_dry_press_keeps_the_dial_and_the_next_cool_goes_out_there(
    from_disk, tmp_path,
):
    matrix = shapes.daikin_dry()
    pair = await _pair(matrix, from_disk=from_disk, tmp_path=tmp_path)
    pair.card(HVACMode.COOL, "auto", "off", 24.0)

    sent = await pair.press(shapes.daikin_dry_press("auto"))

    # The air gets the code it always got, the representative's bytes.
    assert sent.pronto == _cell(matrix, "dry", "auto", "off", 30).pronto
    # The send names the sibling at the card's temperature: the same
    # text, so the Mirror label names a code that really went out.
    assert sent.name == "dry / fan: auto / swing: off / 24"
    assert sent.cell["temp"] == 24.0
    entity = pair.entity
    assert entity.hvac_mode == HVACMode.DRY
    assert entity.fan_mode == "auto"
    assert entity.target_temperature == 24.0
    assert entity.extra_state_attributes["matrix_cell"] == sent.name

    await entity.async_set_hvac_mode(HVACMode.COOL)

    own = pair.manager.sends[-1]
    assert own.origin == ORIGIN_ENTITY
    assert own.name == "cool / fan: auto / swing: off / 24"
    assert own.pronto == _cell(matrix, "cool", "auto", "off", 24).pronto


@pytest.mark.asyncio
@pytest.mark.parametrize("from_disk", [False, True])
async def test_a_dial_below_the_dry_range_stays_put_after_a_restart_too(
    from_disk, tmp_path,
):
    """Cool at 16 is outside dry's 18-30. The unit ignores temperature
    in dry, so the dial stays at 16 and the next cool goes out at 16:
    ``temp_free``, which an index read back from JSON must still carry
    (its branches come back as lists)."""
    matrix = shapes.daikin_dry()
    pair = await _pair(matrix, from_disk=from_disk, tmp_path=tmp_path)
    pair.card(HVACMode.COOL, "auto", "off", 16.0)

    sent = await pair.press(shapes.daikin_dry_press("auto"))

    assert sent.cell["temp_free"] is True
    assert sent.name == "dry / fan: auto / swing: off / 18-30"
    assert pair.entity.hvac_mode == HVACMode.DRY
    assert pair.entity.target_temperature == 16.0
    await pair.entity.async_set_hvac_mode(HVACMode.COOL)
    assert pair.manager.sends[-1].name == "cool / fan: auto / swing: off / 16"


@pytest.mark.asyncio
async def test_a_press_the_file_stores_once_moves_the_card_as_it_always_did():
    matrix = shapes.daikin_dry()
    pair = await _pair(matrix)
    pair.card(HVACMode.DRY, "auto", "off", 24.0)
    cool_22 = _cell(matrix, "cool", "high", "off", 22)

    sent = await pair.press(cool_22.pronto)

    assert "spanned" not in sent.cell
    assert sent.name == "cool / fan: high / swing: off / 22"
    assert (pair.entity.hvac_mode, pair.entity.fan_mode,
            pair.entity.target_temperature) == (HVACMode.COOL, "high", 22.0)


# ---------------------------------------------------------------------------
# 3. The device's group decides, never the remote's
# ---------------------------------------------------------------------------


def _per_temperature_dry(fan_word: str, codes) -> ClimateMatrix:
    """Dry with a code of its own at every temperature, cool too."""
    cells = [
        ClimateCell(mode=mode, fan=fan_word, swing="off", temp=float(t),
                    pronto=next(codes))
        for mode in ("cool", "dry") for t in range(18, 31)
    ]
    return ClimateMatrix(
        min_temp=18.0, max_temp=30.0, modes=["cool", "dry"],
        fan_modes=[fan_word], swing_modes=["off"],
        off=shapes.daikin_dry().off, cells=cells,
    )


@pytest.mark.asyncio
async def test_a_group_only_the_device_has_does_not_move_the_dial():
    """The remote stores dry per temperature; the device file spells
    the fan "Auto", so the words miss, and stores every dry temperature
    with the code the handset sent, so the frame finds the device's
    representative at 30. The dial must not follow it there."""
    codes = (shapes.distinct_code(n) for n in itertools.count(900))
    remote = _per_temperature_dry("auto", codes)
    pressed = _cell(remote, "dry", "auto", "off", 24)
    device = _per_temperature_dry("Auto", codes)
    for cell in device.cells:
        if cell.mode == "dry":
            cell.pronto = pressed.pronto
    pair = await _pair(remote, device)
    pair.card(HVACMode.COOL, "Auto", "off", 24.0)

    sent = await pair.press(pressed.pronto)

    assert sent.pronto == pressed.pronto
    assert sent.cell["spanned"] == {"temp": [float(t) for t in range(18, 31)]}
    assert pair.entity.hvac_mode == HVACMode.DRY
    assert pair.entity.target_temperature == 24.0


@pytest.mark.asyncio
async def test_a_group_only_the_remote_has_lets_the_dial_follow_the_device():
    """The reverse: the remote's file stores dry as one code, the
    device's has a real code per temperature, and the device was sent
    its own dry 30. That unit may honour 30, so the card says 30."""
    remote = shapes.daikin_dry()
    codes = (shapes.distinct_code(n) for n in itertools.count(950))
    device = _per_temperature_dry("auto", codes)
    pair = await _pair(remote, device)
    pair.card(HVACMode.COOL, "auto", "off", 24.0)

    sent = await pair.press(shapes.daikin_dry_press("auto"))

    # The hearing still says what the remote's file knows...
    assert pair.remote.last_heard["cell_name"] == (
        "dry / fan: auto / swing: off / 18-30"
    )
    # ...and the send is the device's own cell, named as itself.
    assert sent.pronto == _cell(device, "dry", "auto", "off", 30).pronto
    assert "spanned" not in sent.cell
    assert sent.name == "dry / fan: auto / swing: off / 30"
    assert pair.entity.target_temperature == 30.0


# ---------------------------------------------------------------------------
# 4. A fan the group does not hold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_current_fan_outside_the_group_sends_todays_bytes():
    """The 1100 shape: dry auto, high, low and mid are one code across
    18-30, dry quiet is a code per temperature. The card's fan is quiet.
    Fan is a spanned dimension, but quiet is not one of its values, so
    nothing may go out as dry quiet: today's bytes go out, and the card
    shows the representative's fan."""
    matrix = shapes.shape_1100()
    pair = await _pair(matrix)
    pair.card(HVACMode.COOL, "quiet", None, 24.0)
    representative = _cell(matrix, "dry", "mid", None, 30)

    sent = await pair.press(_cell(matrix, "dry", "auto", None, 20).pronto)

    assert (sent.pronto, sent.send_count) == (
        representative.pronto, representative.send_count,
    )
    assert sent.name == "dry / fan: any / 18-30"
    assert pair.entity.fan_mode == "mid"
    assert pair.entity.target_temperature == 24.0
    assert pair.entity.hvac_mode == HVACMode.DRY


# ---------------------------------------------------------------------------
# 5. A code the file stores under two modes (Komeco PR-19)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def komeco():
    matrix = shapes.wig_matrix(shapes.KOMECO_WIGS[1])
    return matrix, build_cell_index(matrix)


@pytest.mark.asyncio
@pytest.mark.parametrize("swing", ["off", "vertical"])
@pytest.mark.parametrize("from_disk", [False, True])
@pytest.mark.parametrize(
    ("start", "ends"),
    [
        # OFF: a state code turns the card on, to the representative's
        # mode, since the card's own mode says nothing.
        (HVACMode.OFF, HVACMode.HEAT_COOL),
        # HEAT is not one of the group's modes: the card moves into it.
        (HVACMode.HEAT, HVACMode.HEAT_COOL),
        # COOL is one of them: the card stays.
        (HVACMode.COOL, HVACMode.COOL),
    ],
)
async def test_a_code_stored_under_two_modes(
    komeco, swing, from_disk, start, ends, tmp_path,
):
    """cool / medium / 25 and heat_cool / medium / 25 are one code at
    every swing. The ``off`` group is one text; the ``vertical`` group
    is two captures, so its members are not siblings of each other and
    the send keeps base's name."""
    matrix, index = komeco
    device_index = _through_disk(index, tmp_path, "dev-1") if from_disk else index
    pair = await _pair(matrix, device_index=device_index)
    pair.card(start, "medium", swing, 25.0)
    cool = _cell(matrix, "cool", "medium", swing, 25)
    heat_cool = _cell(matrix, "heat_cool", "medium", swing, 25)
    same_text = cool.pronto == heat_cool.pronto
    assert same_text is (swing == "off")

    sent = await pair.press(cool.pronto)

    assert sent.pronto == heat_cool.pronto
    assert sent.cell["spanned"] == {"mode": ["cool", "heat_cool"]}
    assert pair.entity.hvac_mode == ends
    assert pair.entity.fan_mode == "medium"
    assert pair.entity.swing_mode == swing
    assert pair.entity.target_temperature == 25.0
    if start == HVACMode.COOL and same_text:
        assert sent.name == f"cool / fan: medium / swing: {swing} / 25"
    elif start == HVACMode.COOL:
        assert sent.name == (
            f"cool|heat_cool / fan: medium / swing: {swing} / 25"
        )
    else:
        assert sent.name == (
            f"cool|heat_cool / fan: medium / swing: {swing} / 25"
        )


# ---------------------------------------------------------------------------
# 6. Groups that are not every combination of their values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("from_disk", [False, True])
async def test_a_non_product_group_never_leaves_the_card_on_another_code(
    from_disk, tmp_path,
):
    """The 2740 shape. dry / auto / 17 is inside the group's fans and
    inside its temperatures and is still a code of its own, so the card
    must not stay there."""
    matrix = shapes.shape_2740()
    pair = await _pair(matrix, from_disk=from_disk, tmp_path=tmp_path)
    pair.card(HVACMode.DRY, "auto", None, 17.0)

    sent = await pair.press(_cell(matrix, "dry", "level1", None, 20).pronto)

    entity = pair.entity
    landed = (entity._file_mode_for(entity.hvac_mode), entity.fan_mode,
              None, entity.target_temperature)
    assert landed != ("dry", "auto", None, 17.0)
    assert landed in {tuple(m) for m in sent.cell["members"]}


@pytest.mark.asyncio
@pytest.mark.parametrize("from_disk", [False, True])
async def test_a_group_covering_part_of_its_branch_moves_the_dial(
    from_disk, tmp_path,
):
    """The 1000 shape. heat / high / 18 and 19 are one code, the rest of
    heat / high is real, so the unit reads temperature there: a press
    of 18 with the card at 25 does not leave the dial at 25."""
    matrix = shapes.shape_1000()
    pair = await _pair(matrix, from_disk=from_disk, tmp_path=tmp_path)
    pair.card(HVACMode.HEAT, "high", None, 25.0)

    sent = await pair.press(_cell(matrix, "heat", "high", None, 18).pronto)

    assert sent.cell["temp_free"] is False
    assert pair.entity.target_temperature in (18.0, 19.0)
    assert pair.entity.target_temperature != 25.0


# ---------------------------------------------------------------------------
# 7. The provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_coalesced_send_reads_the_state_at_send_time():
    """The dispatcher can hold a send a moment. What the card is at when
    it goes out is what names it, not what it was at when heard."""
    matrix = shapes.daikin_dry()
    pair = await _pair(matrix)
    pair.card(HVACMode.COOL, "auto", "off", 24.0)
    decoded, fp, bh, norm, covers = press_identity(
        shapes.daikin_dry_press("auto")
    )
    await pair.listener.on_signal_captured(fp, bh, decoded, None, norm, covers)
    await pair.drain()
    key = pair.tm.dispatch_cell_retransmit.call_args.args[2]

    pair.entity._target_temperature = 21.0
    await pair.listener.async_send_pinned_cell("dev-1", key)

    assert pair.manager.sends[-1].name == "dry / fan: auto / swing: off / 21"
    assert pair.entity.target_temperature == 21.0


@pytest.mark.asyncio
async def test_with_no_provider_base_goes_out_named_as_the_range():
    """No entity has registered (disabled, or not added yet): the
    representative's bytes go out under the range name."""
    matrix = shapes.daikin_dry()
    pair = await _pair(matrix, provider=False)
    pair.manager.entity = None

    sent = await pair.press(shapes.daikin_dry_press("auto"))

    assert sent.pronto == _cell(matrix, "dry", "auto", "off", 30).pronto
    assert sent.cell["temp"] == 30.0
    assert sent.name == "dry / fan: auto / swing: off / 18-30"


# ---------------------------------------------------------------------------
# 8. A miss is named as one
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("card", "why"),
    [
        ((HVACMode.COOL, "auto", "off", 16.11), "off-grid: 61 F set while OFF"),
        ((HVACMode.COOL, "auto", "off", 16.0), "outside the group"),
    ],
)
@pytest.mark.parametrize("from_disk", [False, True])
async def test_a_send_that_cannot_name_its_setting_is_named_as_the_range(
    card, why, from_disk, tmp_path,
):
    matrix = shapes.daikin_dry()
    pair = await _pair(matrix, from_disk=from_disk, tmp_path=tmp_path)
    pair.card(*card)

    sent = await pair.press(shapes.daikin_dry_press("auto"))

    assert sent.name == "dry / fan: auto / swing: off / 18-30", why
    readout = pair.entity.extra_state_attributes["matrix_cell"]
    assert readout == sent.name
    # No tile on the device card is named that, so none rings current.
    assert readout not in _every_name(matrix)
    # And the dial is where the user left it: dry ignores temperature.
    assert pair.entity.target_temperature == card[3]


# ---------------------------------------------------------------------------
# 13. The "+ Trigger" door on a spanned press
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plus_trigger_on_a_spanned_press_mints_the_representative(
    fake_hass,
):
    """``last_heard`` keeps the representative's coordinates, so door 1
    resolves a real cell: the representative, whose code is the group's
    code, which is what a trigger needs to fire on any of them."""
    from custom_components.hair.websocket_api import (
        ws_trigger_remote_matrix_cell,
    )

    from .test_websocket_api import _make_connection, _wire_matrix_remote

    matrix = shapes.daikin_dry()
    pair = await _pair(matrix)
    await pair.press(shapes.daikin_dry_press("auto"))
    heard = pair.remote.last_heard
    assert heard["spanned"]
    _wire_matrix_remote(fake_hass, matrix)
    conn = _make_connection()

    await ws_trigger_remote_matrix_cell(fake_hass, conn, {
        "id": 1, "type": "hair/trigger-remote/matrix-cell",
        "remote_id": "tr-cell", "mode": heard["mode"], "fan": heard["fan"],
        "swing": heard["swing"], "temp": heard["temp"],
    })

    conn.send_error.assert_not_called()
    payload = conn.send_result.call_args[0][1]
    assert payload["pronto"] == _cell(matrix, "dry", "auto", "off", 30).pronto
    assert payload["pronto"] == _cell(matrix, "dry", "auto", "off", 18).pronto


# ---------------------------------------------------------------------------
# 17. A group in an extras lattice moves the readout only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_extras_press_with_a_group_names_its_range_and_leaves_the_dial():
    """Eco stores one code at three temperatures, on both sides. The
    send carries the group for its name; the main dial never follows an
    extras send, because its coordinates name another code there."""
    from .test_matrix_listener import (
        PRONTO_ECO_22,
        _device_matrix_with_extra_group,
        _matrix_with_extra_group,
    )

    pair = await _pair(
        _matrix_with_extra_group(), _device_matrix_with_extra_group(),
    )
    pair.card(HVACMode.COOL, "auto", None, 22.0)

    sent = await pair.press(PRONTO_ECO_22)

    assert sent.cell["lattice"] == "eco"
    assert sent.cell["spanned"] == {"temp": [22.0, 23.0, 24.0]}
    assert sent.name == "(eco) cool / fan: auto / 22"
    assert pair.entity.target_temperature == 22.0
    assert pair.entity.hvac_mode == HVACMode.COOL
    assert pair.entity.extra_state_attributes["matrix_cell"] == sent.name

    # With the card somewhere the eco group does not hold, the name says
    # the range, and still the dial does not move.
    pair.card(HVACMode.COOL, "auto", None, 26.0)
    sent = await pair.press(PRONTO_ECO_22)
    assert sent.name == "(eco) cool / fan: auto / 22-24"
    assert pair.entity.target_temperature == 26.0
    assert pair.entity.extra_state_attributes["matrix_cell"] == sent.name


# ---------------------------------------------------------------------------
# Families outside the read-bytes list, end to end
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pack", "card", "press", "expected"),
    [
        # MITSUBISHI144: dry stores one code across 16-31 per swing.
        ("MITSUBISHI144.json", (HVACMode.COOL, "auto", "auto", 24.0),
         ("dry", "auto", "auto", 20.0), ("auto", "auto", 24.0)),
        # TCL112: dry stores one code across five fans and 16-31.
        ("TCL112.json", (HVACMode.COOL, "low", "static", 24.0),
         ("dry", "auto", "static", 20.0), ("low", "static", 24.0)),
    ],
)
async def test_a_pack_outside_the_read_bytes_list(pack, card, press, expected):
    matrix = shapes.pack_matrix(pack)
    pair = await _pair(matrix)
    pair.card(*card)
    pressed = _cell(matrix, *press)

    sent = await pair.press(pressed.pronto)

    heard = pair.remote.last_heard
    representative = _cell(
        matrix, heard["mode"], heard["fan"], heard["swing"], heard["temp"],
    )
    assert (sent.pronto, sent.send_count) == (
        representative.pronto, representative.send_count,
    )
    assert pair.entity.hvac_mode == HVACMode.DRY
    assert (pair.entity.fan_mode, pair.entity.swing_mode,
            pair.entity.target_temperature) == expected
    assert sent.name == cell_display_name(
        _cell(matrix, "dry", *expected)
    )


# ---------------------------------------------------------------------------
# The name grammar
# ---------------------------------------------------------------------------


class TestTheRangeName:
    CELL = ClimateCell(mode="dry", fan="auto", swing="off", temp=30.0,
                       pronto="P")

    def _name(self, spanned, **kw):
        return spanned_display_name(self.CELL, spanned, **kw)

    def test_a_contiguous_temperature_is_a_range(self):
        temps = tuple(float(t) for t in range(18, 31))
        assert self._name({"temp": temps}) == (
            "dry / fan: auto / swing: off / 18-30"
        )

    def test_the_range_is_in_the_display_unit(self):
        assert self._name({"temp": (18.0, 19.0, 20.0)}, display_unit="F") == (
            "dry / fan: auto / swing: off / 64-68"
        )

    def test_a_gap_lists_the_values(self):
        assert self._name({"temp": (18.0, 19.0, 25.0)}) == (
            "dry / fan: auto / swing: off / 18|19|25"
        )

    def test_three_values_are_listed_and_more_are_any(self):
        assert self._name({"fan": ("auto", "high", "low")}) == (
            "dry / fan: auto|high|low / swing: off / 30"
        )
        assert self._name({"fan": ("auto", "high", "low", "mid")}) == (
            "dry / fan: any / swing: off / 30"
        )
        assert self._name({"mode": ("cool", "heat_cool")}) == (
            "cool|heat_cool / fan: auto / swing: off / 30"
        )

    def test_an_extras_name_keeps_its_lattice(self):
        assert self._name({"temp": (22.0, 23.0)}, lattice="eco") == (
            "(eco) dry / fan: auto / swing: off / 22-23"
        )

    def test_a_member_without_the_dimension_reads_as_a_dash(self):
        assert self._name({"swing": ("off", None)}) == (
            "dry / fan: auto / swing: off|- / 30"
        )

    def test_a_range_name_is_never_a_real_cell_name(self):
        """No vocabulary value contains "|" or is "any", and a range is
        not a number, so a range can never collide with a cell."""
        name = self._name({"temp": (18.0, 19.0)})
        assert name not in {
            cell_display_name(c) for c in shapes.daikin_dry().cells
        }
        assert cell_key(self.CELL) == "dry/auto/off/30"


# ---------------------------------------------------------------------------
# 16. The live lattice wins over an index that has not caught up
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_member_rewritten_in_place_is_not_where_the_card_lands():
    """``async_replace_cell`` rewrites a cell's bytes in place. Until the
    index is rebuilt it still lists that cell as a member, so the send
    checks every member against the live lattice: dry / auto / 24 now
    carries another code, so the card must not be left there."""
    import copy

    remote = shapes.daikin_dry()
    device = copy.deepcopy(remote)
    pair = await _pair(remote, device, device_index=build_cell_index(device))
    _cell(device, "dry", "auto", "off", 24).pronto = shapes.distinct_code(990)
    pair.card(HVACMode.COOL, "auto", "off", 24.0)

    sent = await pair.press(shapes.daikin_dry_press("auto"))

    assert sent.pronto == _cell(device, "dry", "auto", "off", 30).pronto
    assert ["dry", "auto", "off", 24.0] not in sent.cell["members"]
    assert sent.cell["temp_free"] is False
    assert pair.entity.target_temperature != 24.0
    landed = ("dry", "auto", "off", pair.entity.target_temperature)
    assert list(landed) in sent.cell["members"]


@pytest.mark.asyncio
async def test_a_removed_member_is_not_where_the_dial_stays():
    """Cells deleted or thinned out before the index caught up: a member
    coordinate with no live cell is dropped, and the branch is no
    longer wholly one code, so the dial does not stay on a removed
    temperature."""
    import copy

    remote = shapes.daikin_dry()
    device = copy.deepcopy(remote)
    pair = await _pair(remote, device, device_index=build_cell_index(device))
    device.cells = [
        c for c in device.cells
        if not (c.mode == "dry" and c.fan == "auto" and c.temp in (18, 19, 20))
    ]
    pair.card(HVACMode.COOL, "auto", "off", 19.0)

    sent = await pair.press(shapes.daikin_dry_press("auto"))

    assert sent.pronto == _cell(device, "dry", "auto", "off", 30).pronto
    assert sent.cell["temp_free"] is False
    assert pair.entity.target_temperature == 30.0
    assert sent.name == "dry / fan: auto / swing: off / 21-30"
