"""Where a newly minted command lands (owner ruling 2026-08-29).

Two pins, one for each half of the ruling: the panel's own mint puts
the command at the head of the list and it stays there through the
store, and every path that builds a device from a source whose order
means something keeps that order exactly.
"""

import pytest

from custom_components.hair.models import IRCommand, IRDevice


def _command(name: str) -> IRCommand:
    return IRCommand(name=name, code="0000 006D 0001 0000 0060 0018")


def _device(*names: str) -> IRDevice:
    device = IRDevice(name="Bench", device_type="media_player")
    for name in names:
        device.add_command(_command(name))
    return device


class TestMintPlacement:
    """The panel's mint lands where the person is looking."""

    def test_top_placement_puts_the_mint_first(self):
        device = _device("Power", "Volume Up", "Volume Down")
        device.add_command(_command("Mute"), placement="top")
        assert [c.name for c in device.commands] == [
            "Mute",
            "Power",
            "Volume Up",
            "Volume Down",
        ]

    def test_top_placement_on_an_empty_device(self):
        device = _device()
        device.add_command(_command("Power"), placement="top")
        assert [c.name for c in device.commands] == ["Power"]

    def test_a_mint_survives_a_store_round_trip(self):
        """First in the list, and still first once it has been through
        serialization -- the order is the stored order, not a render
        trick."""
        device = _device("Power", "Volume Up")
        device.add_command(_command("Mute"), placement="top")

        restored = IRDevice.from_dict(device.to_dict())

        assert [c.name for c in restored.commands] == [
            "Mute",
            "Power",
            "Volume Up",
        ]

    def test_a_name_collision_still_replaces_in_place(self):
        """A rename is not a mint. Replacing the command that already
        owns a name must not shuffle the list under someone who only
        edited that name."""
        device = _device("Power", "Volume Up", "Mute")
        replacement = _command("Volume Up")

        device.add_command(replacement, placement="top")

        assert [c.name for c in device.commands] == [
            "Power",
            "Volume Up",
            "Mute",
        ]
        assert device.get_command_by_name("Volume Up").id == replacement.id


class TestSourceOrderIsPreserved:
    """Everything that builds a device from a file keeps the file's
    order: default placement is append, and it stays append."""

    def test_default_placement_appends(self):
        device = _device("Power", "Volume Up")
        device.add_command(_command("Mute"))
        assert [c.name for c in device.commands] == [
            "Power",
            "Volume Up",
            "Mute",
        ]

    def test_a_device_built_from_a_wig_keeps_the_wigs_order(self):
        """The adopt path adds every signal in the wig's own order and
        passes no placement, so the device reads in file order."""
        wig_order = [
            "Power",
            "Mode",
            "Fan Up",
            "Fan Down",
            "Swing",
            "Timer",
        ]
        device = IRDevice(name="From a wig", device_type="ac")
        for name in wig_order:
            device.add_command(_command(name))

        assert [c.name for c in device.commands] == wig_order
        restored = IRDevice.from_dict(device.to_dict())
        assert [c.name for c in restored.commands] == wig_order

    @pytest.mark.parametrize("placement", ["append", "somethingelse"])
    def test_only_top_moves_a_command(self, placement):
        """Anything that is not "top" appends, so a caller that passes
        nothing and a caller that passes a value this code does not
        know behave the same safe way."""
        device = _device("Power", "Volume Up")
        device.add_command(_command("Mute"), placement=placement)
        assert device.commands[-1].name == "Mute"
