"""Tests for multi-emitter send resilience (GH #65, rvgfox).

The contract under test, from the fix scope in
community-feedback/github-issue-65-rvgfox.md:

- One emitter failing never blocks the others and never fails the
  command when at least one (emitter, frame) landed -- regardless of
  where the dead unit sits in the list.
- Every emitter failing raises the honest "all unavailable" message,
  not the raw driver string.
- The RC-5 toggle / Dyson counter advance fires on "at least one send
  landed" (a logical press happened), exactly once -- not on "loop
  finished without raising", which desynced state when a late emitter
  failed after the device already got the frame.
- Emitters whose HA state is unavailable are pre-skipped (unknown is
  never-used, not down -- GH #83); the
  send-time guard remains the backstop.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.storage import HAIRStore


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.fixture
def manager(fake_hass):
    fake_hass.states.get = MagicMock(return_value=None)
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


def _dyson_device(emitters: list[str]) -> IRDevice:
    """A device whose command carries the Dyson mod-4 counter."""
    cmd = IRCommand(
        id="c1",
        name="Power",
        protocol="PRONTO",
        code="0000 006D 0002 0000 0020 0040 0020 0040",
        decoded_protocol="DYSON",
        decoded_address=9,
        decoded_command=1,
        decoded_fingerprint="DYSON:0x9:0x1",
        decoded_extras={"counter": 2},
    )
    return IRDevice(name="Fan", emitter_entity_ids=emitters, commands=[cmd])


def _failing_sender(dead: set[str]) -> AsyncMock:
    """An ir_send stub that raises for the given emitter ids."""

    async def _send(hass, emitter_id, ir_cmd):
        if emitter_id in dead:
            raise RuntimeError(
                f"Not connected to {emitter_id} @ 192.168.1.75!"
            )

    return AsyncMock(side_effect=_send)


_BDC = "custom_components.hair.ir_command.build_decoded_command"


def _decoded_stub():
    """A minimal decoded-command stand-in. A bare object() no longer
    suffices: the broadcast path reads modulation/repeat_count to
    build the terminated wire copy (GH #98, TerminatedCommand)."""

    class _Stub:
        modulation = 38000
        repeat_count = 0

        def get_raw_timings(self):
            return [100]

    return _Stub()


class TestPartialFailure:
    @pytest.mark.asyncio
    async def test_second_emitter_dead_still_succeeds(self, manager):
        """rvgfox's actual case: Broadlink fires, Athom raises after."""
        dev = _dyson_device(["infrared.broadlink", "infrared.athom"])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.athom"})
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")  # no raise
        sent_to = [c.args[1] for c in ir_send.call_args_list]
        assert "infrared.broadlink" in sent_to

    @pytest.mark.asyncio
    async def test_first_emitter_dead_does_not_block_second(self, manager):
        """Order independence: a dead unit first in the list must not
        stop the live one behind it (consequence #2 in the report)."""
        dev = _dyson_device(["infrared.athom", "infrared.broadlink"])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.athom"})
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")
        sent_to = [c.args[1] for c in ir_send.call_args_list]
        assert "infrared.broadlink" in sent_to

    @pytest.mark.asyncio
    async def test_partial_failure_advances_counter_exactly_once(
        self, manager
    ):
        """Consequence #3: the Dyson counter must advance when the
        device already got the frame from a live emitter."""
        dev = _dyson_device(["infrared.broadlink", "infrared.athom"])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.athom"})
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")
        assert dev.commands[0].decoded_extras["counter"] == 3

    @pytest.mark.asyncio
    async def test_flaky_emitter_dropped_from_later_frames(self, manager):
        """A failed emitter is not retried across send_count frames."""
        dev = _dyson_device(["infrared.broadlink", "infrared.athom"])
        dev.commands[0].send_count = 3
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.athom"})
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")
        athom_calls = [
            c for c in ir_send.call_args_list
            if c.args[1] == "infrared.athom"
        ]
        broadlink_calls = [
            c for c in ir_send.call_args_list
            if c.args[1] == "infrared.broadlink"
        ]
        assert len(athom_calls) == 1
        assert len(broadlink_calls) == 3


class TestTotalFailure:
    @pytest.mark.asyncio
    async def test_all_emitters_dead_raises_honest_message(self, manager):
        dev = _dyson_device(["infrared.a", "infrared.b"])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.a", "infrared.b"})
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()), \
                pytest.raises(RuntimeError, match="All emitters for Fan"):
            await manager.async_send_command(dev.id, "c1")

    @pytest.mark.asyncio
    async def test_total_failure_does_not_advance_counter(self, manager):
        """No frame landed = no logical press = counter untouched."""
        dev = _dyson_device(["infrared.a", "infrared.b"])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.a", "infrared.b"})
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()), pytest.raises(RuntimeError):
            await manager.async_send_command(dev.id, "c1")
        assert dev.commands[0].decoded_extras["counter"] == 2

    @pytest.mark.asyncio
    async def test_toggle_not_flipped_on_total_failure(self, manager):
        cmd = IRCommand(
            id="c1", name="Power", protocol="PRONTO",
            code="0000 006D 0002 0000 0020 0040 0020 0040",
            decoded_protocol="RC5", decoded_address=0, decoded_command=1,
            decoded_fingerprint="RC5:0x0:0x1",
            decoded_extras={"toggle": 0},
        )
        dev = IRDevice(name="TV", emitter_entity_ids=["infrared.a"],
                       commands=[cmd])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.a"})
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()), pytest.raises(RuntimeError):
            await manager.async_send_command(dev.id, "c1")
        assert cmd.decoded_extras["toggle"] == 0


class TestPreSkip:
    @pytest.mark.asyncio
    async def test_known_unavailable_emitter_never_attempted(
        self, manager, fake_hass
    ):
        dev = _dyson_device(["infrared.down", "infrared.up"])
        manager._store.add_device(dev)

        def _state(entity_id):
            if entity_id == "infrared.down":
                return MagicMock(state="unavailable")
            return MagicMock(state="idle")

        fake_hass.states.get = MagicMock(side_effect=_state)
        ir_send = _failing_sender(set())
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")
        sent_to = [c.args[1] for c in ir_send.call_args_list]
        assert sent_to == ["infrared.up"]

    @pytest.mark.asyncio
    async def test_all_known_unavailable_raises_before_sending(
        self, manager, fake_hass
    ):
        dev = _dyson_device(["infrared.down"])
        manager._store.add_device(dev)
        fake_hass.states.get = MagicMock(
            return_value=MagicMock(state="unavailable")
        )
        ir_send = AsyncMock()
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                pytest.raises(RuntimeError, match="All emitters for Fan"):
            await manager.async_send_command(dev.id, "c1")
        ir_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_never_used_emitter_is_attempted_not_skipped(
        self, manager, fake_hass
    ):
        """GH #83 (Lilian877 + Warpshock): an infrared emitter's state
        is its last-send timestamp -- "unknown" until the FIRST send.
        Pre-skipping "unknown" therefore made a fresh install unable to
        ever send its first command: every emitter skipped, "All
        emitters unavailable" on a clean setup. Never-used must be
        attempted; only "unavailable" is down."""
        dev = _dyson_device(["infrared.brand_new"])
        manager._store.add_device(dev)
        fake_hass.states.get = MagicMock(
            return_value=MagicMock(state="unknown")
        )
        ir_send = _failing_sender(set())
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")
        sent_to = [c.args[1] for c in ir_send.call_args_list]
        assert sent_to == ["infrared.brand_new"]

    @pytest.mark.asyncio
    async def test_mixed_unknown_and_unavailable_sends_via_unknown(
        self, manager, fake_hass
    ):
        """The fresh blaster carries the send while the dead one stays
        skipped -- GH #65 resilience and the GH #83 fix, together."""
        dev = _dyson_device(["infrared.down", "infrared.brand_new"])
        manager._store.add_device(dev)

        def _state(entity_id):
            if entity_id == "infrared.down":
                return MagicMock(state="unavailable")
            return MagicMock(state="unknown")

        fake_hass.states.get = MagicMock(side_effect=_state)
        ir_send = _failing_sender(set())
        with patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")
        sent_to = [c.args[1] for c in ir_send.call_args_list]
        assert sent_to == ["infrared.brand_new"]


_PN = "homeassistant.components.persistent_notification"


class TestDegradeNotification:
    """GH #65 rider (v0.8.1): a skipped or failed emitter raises one
    persistent notification (stable id, replace-not-stack), and an
    emitter that answers again dismisses its own."""

    @pytest.mark.asyncio
    async def test_partial_failure_notifies_per_dead_emitter(self, manager):
        import homeassistant.components.persistent_notification as pn

        dev = _dyson_device(["infrared.broadlink", "infrared.athom"])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.athom"})
        with patch.object(pn, "async_create") as create, \
                patch.object(pn, "async_dismiss") as dismiss, \
                patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")
        assert create.call_count == 1
        kwargs = create.call_args.kwargs
        assert kwargs["notification_id"] == (
            "hair_emitter_down_infrared.athom"
        )
        assert "infrared.athom" in create.call_args.args[1]
        assert "Fan" in create.call_args.args[1]
        # The live emitter self-heals its (possibly stale) notice.
        dismissed = [c.args[1] for c in dismiss.call_args_list]
        assert "hair_emitter_down_infrared.broadlink" in dismissed
        assert "hair_emitter_down_infrared.athom" not in dismissed

    @pytest.mark.asyncio
    async def test_total_failure_notifies_every_emitter(self, manager):
        import homeassistant.components.persistent_notification as pn

        dev = _dyson_device(["infrared.a", "infrared.b"])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.a", "infrared.b"})
        with patch.object(pn, "async_create") as create, \
                patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()), \
                pytest.raises(RuntimeError):
            await manager.async_send_command(dev.id, "c1")
        ids = {
            c.kwargs["notification_id"] for c in create.call_args_list
        }
        assert ids == {
            "hair_emitter_down_infrared.a",
            "hair_emitter_down_infrared.b",
        }

    @pytest.mark.asyncio
    async def test_pre_skipped_unavailable_emitter_notifies(
        self, manager, fake_hass
    ):
        import homeassistant.components.persistent_notification as pn

        dev = _dyson_device(["infrared.down"])
        manager._store.add_device(dev)
        state = MagicMock(state="unavailable")
        state.attributes = {"friendly_name": "Bedroom Blaster"}
        fake_hass.states.get = MagicMock(return_value=state)
        with patch.object(pn, "async_create") as create, \
                patch.object(_infrared_mod, "async_send_command", AsyncMock()), \
                pytest.raises(RuntimeError):
            await manager.async_send_command(dev.id, "c1")
        assert create.call_count == 1
        assert "Bedroom Blaster" in create.call_args.args[1]

    @pytest.mark.asyncio
    async def test_clean_send_no_notification_only_dismiss(self, manager):
        import homeassistant.components.persistent_notification as pn

        dev = _dyson_device(["infrared.broadlink"])
        manager._store.add_device(dev)
        with patch.object(pn, "async_create") as create, \
                patch.object(pn, "async_dismiss") as dismiss, \
                patch.object(
                    _infrared_mod, "async_send_command", AsyncMock()
                ), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")
        create.assert_not_called()
        dismissed = [c.args[1] for c in dismiss.call_args_list]
        assert dismissed == ["hair_emitter_down_infrared.broadlink"]

    @pytest.mark.asyncio
    async def test_notification_failure_never_breaks_the_send(self, manager):
        """The guard rail: a broken notification layer must not turn a
        landed send into an error."""
        import homeassistant.components.persistent_notification as pn

        dev = _dyson_device(["infrared.broadlink", "infrared.athom"])
        manager._store.add_device(dev)
        ir_send = _failing_sender({"infrared.athom"})
        with patch.object(
                    pn, "async_create",
                    side_effect=RuntimeError("notification bus down"),
                ), \
                patch.object(_infrared_mod, "async_send_command", ir_send), \
                patch(_BDC, return_value=_decoded_stub()):
            await manager.async_send_command(dev.id, "c1")  # no raise


class TestTrailingTerminator:
    """GH #98: the broadcast path hands the emitter a wire copy whose
    timing array ends on the bounded terminator space, while the
    stored command's own parse stays stripped (identity-stable)."""

    @pytest.mark.asyncio
    async def test_broadcast_sends_terminated_wire_copy(self, manager):
        from custom_components.hair.ir_command import (
            TERMINATOR_SPACE_US,
            TerminatedCommand,
        )

        cmd = IRCommand(
            id="c1",
            name="Power",
            protocol="PRONTO",
            code="0000 006D 0002 0000 0020 0100 0020 0100",
        )
        dev = IRDevice(
            name="TV",
            emitter_entity_ids=["infrared.rm4pro"],
            commands=[cmd],
        )
        manager._store.add_device(dev)
        ir_send = AsyncMock()
        with patch.object(_infrared_mod, "async_send_command", ir_send):
            await manager.async_send_command(dev.id, "c1")

        sent_cmd = ir_send.call_args_list[0].args[2]
        assert isinstance(sent_cmd, TerminatedCommand)
        wire = sent_cmd.get_raw_timings()
        assert wire[-1] == -TERMINATOR_SPACE_US
        assert all(w > 0 or -w <= 0xFFFF for w in wire)
