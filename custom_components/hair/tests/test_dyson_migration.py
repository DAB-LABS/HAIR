"""The Dyson counter split, applied to rows already on disk.

THE ASSERTION THAT MATTERS IS A WIRE, NOT A TRIPLE. The migration exists
so a button somebody saved keeps sending the frame it always sent. A
test that only checked the numbers moved from (9, 0x10, 0) to
(9, 0x00, 1) would pass just as happily on a remap that landed on the
wrong button, so the real test re-encodes the migrated row and compares
the bits.
"""
from __future__ import annotations

import pytest

from custom_components.hair.const import (
    STORAGE_VERSION,
    STORAGE_VERSION_MINOR,
)
from custom_components.hair.decoders.dyson import DysonCommand
from custom_components.hair.dyson_migration import (
    migrate_device_store,
    migrate_row,
    migrate_signal_store,
    remap_fields,
)
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.storage import HAIRStore

#: The AM07 PowerToggle, as the old reader stored it and as the frame
#: layout puts it. Recomputed under the corrected split and confirmed
#: against the rendered waveform; the table is in ``decoders/dyson.py``.
OLD_POWER = {"function": 0x10, "counter": 0}
NEW_POWER = {"function": 0x00, "counter": 1}
POWER_WIRE = "100100000000010"


def _wire(device: int, function: int, counter: int) -> str:
    """The frame today's encoder builds for a triple."""
    timings = DysonCommand(
        device=device, function=function, counter=counter
    ).get_raw_timings()
    return "".join(
        "1" if -timings[3 + 2 * index] > 1100 else "0" for index in range(15)
    )


def _wire_under_the_old_split(device: int, function: int, counter: int) -> str:
    """The frame the PREVIOUS encoder built for the same triple.

    Written out here rather than imported, because the code it models no
    longer exists. It is four lines: the old packing put the function in
    the F byte's high six bits and the counter in its low two, and the
    fifteen bits went out LSB first as they still do.

    This is what makes the migration testable at all. Without it the
    test could only say the numbers changed; with it the test says the
    bits did not.
    """
    f_byte = ((function & 0x3F) << 2) | (counter & 0x3)
    bits = [(device >> i) & 1 for i in range(7)]
    bits += [(f_byte >> i) & 1 for i in range(8)]
    return "".join(str(bit) for bit in bits)


def _row(function: int, counter: int, address: int = 9) -> dict:
    return {
        "name": "Power",
        "decoded_protocol": "DYSON",
        "decoded_address": address,
        "decoded_command": function,
        "decoded_extras": {"counter": counter},
        "decoded_fingerprint": f"DYSON:{address:#06x}:{function:#04x}",
    }


class TestTheBijection:
    def test_every_pair_maps_to_a_distinct_pair(self):
        """Lossless, so nothing is thrown away and it is reversible."""
        outputs = {
            remap_fields(function, counter)
            for function in range(64)
            for counter in range(4)
        }
        assert len(outputs) == 64 * 4

    def test_the_documented_case(self):
        assert remap_fields(**OLD_POWER) == (
            NEW_POWER["function"], NEW_POWER["counter"]
        )

    def test_it_is_not_idempotent_which_is_why_it_is_version_gated(self):
        """Stated as a test so nobody moves this into the backfill chain.

        The load-time backfills are safe to re-run because doing them
        twice is doing them once. This is not, and a second application
        lands on a third, wrong button.
        """
        once = remap_fields(**OLD_POWER)
        twice = remap_fields(*once)
        assert twice != once
        assert _wire(9, *twice) != POWER_WIRE


class TestTheWire:
    def test_a_migrated_row_emits_the_frame_it_always_did(self):
        """The whole point of the migration, as bits.

        The stored row goes in as the old reader wrote it, the migration
        runs, and the frame today's encoder builds from the result is
        compared against the frame the old encoder built from the
        original. They have to be the same bits.
        """
        before = _wire_under_the_old_split(
            9, OLD_POWER["function"], OLD_POWER["counter"]
        )
        assert before == POWER_WIRE

        row = _row(OLD_POWER["function"], OLD_POWER["counter"])
        assert migrate_row(row) is True
        after = _wire(
            row["decoded_address"],
            row["decoded_command"],
            row["decoded_extras"]["counter"],
        )
        assert after == before == POWER_WIRE

    def test_without_the_migration_the_row_would_send_another_button(self):
        """The failure being prevented, measured rather than asserted.

        An unmigrated row is not merely mislabelled: run through the new
        encoder it is a different frame, so a saved Power button would
        transmit something else entirely.
        """
        unmigrated = _wire(9, OLD_POWER["function"], OLD_POWER["counter"])
        assert unmigrated != POWER_WIRE
        assert unmigrated == "100100000001000"
        differences = sum(
            1 for a, b in zip(unmigrated, POWER_WIRE, strict=True) if a != b
        )
        assert differences == 2

    @pytest.mark.parametrize(
        ("old_function", "old_counter", "wire"),
        [
            (0x10, 0, "100100000000010"),
            (0x1A, 2, "100100001010110"),
            (0x1F, 3, "100100011111110"),
            (0x15, 1, "100100010101010"),
            (0x17, 2, "100100001111010"),
            (0x1C, 3, "100100011001110"),
        ],
    )
    def test_every_am07_button_survives(self, old_function, old_counter, wire):
        """All six buttons, old encoder to migrated row, bit for bit."""
        assert _wire_under_the_old_split(9, old_function, old_counter) == wire
        row = _row(old_function, old_counter)
        assert migrate_row(row) is True
        assert _wire(
            9, row["decoded_command"], row["decoded_extras"]["counter"]
        ) == wire


class TestRowHandling:
    def test_the_fingerprint_is_recomputed(self):
        row = _row(0x10, 0)
        migrate_row(row)
        assert row["decoded_fingerprint"] == "DYSON:0x0009:0x00"

    def test_the_counter_never_reaches_the_fingerprint(self):
        """Press state is excluded from identity, before and after."""
        one = _row(0x10, 0)
        two = _row(0x10, 1)
        migrate_row(one)
        migrate_row(two)
        assert one["decoded_command"] != two["decoded_command"] or (
            one["decoded_fingerprint"] != two["decoded_fingerprint"]
        )
        assert "counter" not in one["decoded_fingerprint"]

    def test_a_row_of_another_protocol_is_untouched(self):
        row = {
            "decoded_protocol": "NEC",
            "decoded_address": 0x04,
            "decoded_command": 0x08,
            "decoded_fingerprint": "NEC:0x0004:0x08",
        }
        before = dict(row)
        assert migrate_row(row) is False
        assert row == before

    def test_a_row_missing_its_fields_is_left_alone(self):
        row = {"decoded_protocol": "DYSON"}
        assert migrate_row(row) is False

    def test_a_row_with_no_extras_takes_counter_zero(self):
        row = {
            "decoded_protocol": "DYSON",
            "decoded_address": 9,
            "decoded_command": 0x10,
        }
        assert migrate_row(row) is True
        assert row["decoded_command"] == 0x00
        assert row["decoded_extras"]["counter"] == 1


class TestStoreWalks:
    def test_the_device_store_walk_finds_nested_commands(self):
        data = {
            "devices": [
                {"name": "Fan", "commands": [_row(0x10, 0), _row(0x1A, 2)]},
                {"name": "TV", "commands": [
                    {"decoded_protocol": "NEC", "decoded_address": 1,
                     "decoded_command": 2},
                ]},
            ]
        }
        assert migrate_device_store(data) == 2
        assert data["devices"][0]["commands"][0]["decoded_command"] == 0x00
        assert data["devices"][1]["commands"][0]["decoded_command"] == 2

    def test_the_signal_store_walk_finds_both_shapes(self):
        data = {"devices": [{"signals": [_row(0x10, 0)]}],
                "signals": [_row(0x1A, 2)]}
        assert migrate_signal_store(data) == 2


class TestThroughTheStore:
    """The hook, not just the helper.

    Exercised through ``HAIRStore.async_load`` so the version gate, the
    walk and the write-back are all on the path a real upgrade takes.
    """

    async def test_an_old_store_migrates_once_and_persists(self, fake_hass):
        store = HAIRStore(fake_hass)
        device = IRDevice(
            name="Fan",
            commands=[IRCommand(
                name="Power",
                decoded_protocol="DYSON",
                decoded_address=9,
                decoded_command=0x10,
                decoded_extras={"counter": 0},
                decoded_fingerprint="DYSON:0x0009:0x10",
            )],
        )
        payload = {"devices": [device.to_dict()], "triggers": [],
                   "trigger_remotes": [], "trigger_drawer_name": "HAIR"}
        store._store.seed_stored(payload, version=STORAGE_VERSION,
                                 minor_version=1)

        await store.async_load()
        loaded = store.get_all_devices()[0]
        command = loaded.commands[0]
        assert (command.decoded_command, command.decoded_extras["counter"]) == (
            NEW_POWER["function"], NEW_POWER["counter"]
        )
        assert command.decoded_fingerprint == "DYSON:0x0009:0x00"
        assert _wire(9, command.decoded_command,
                     command.decoded_extras["counter"]) == POWER_WIRE

        # Written back, so the gate closes and the bijection cannot run
        # a second time on the next boot.
        assert store._store._stored_minor == STORAGE_VERSION_MINOR
        again = HAIRStore(fake_hass)
        again._store.seed_stored(store._store._data,
                                 version=STORAGE_VERSION,
                                 minor_version=STORAGE_VERSION_MINOR)
        await again.async_load()
        command2 = again.get_all_devices()[0].commands[0]
        assert command2.decoded_command == NEW_POWER["function"]
        assert _wire(9, command2.decoded_command,
                     command2.decoded_extras["counter"]) == POWER_WIRE

    async def test_a_current_store_is_not_migrated(self, fake_hass):
        store = HAIRStore(fake_hass)
        device = IRDevice(
            name="Fan",
            commands=[IRCommand(
                name="Power",
                decoded_protocol="DYSON",
                decoded_address=9,
                decoded_command=0x00,
                decoded_extras={"counter": 1},
                decoded_fingerprint="DYSON:0x0009:0x00",
            )],
        )
        payload = {"devices": [device.to_dict()], "triggers": [],
                   "trigger_remotes": [], "trigger_drawer_name": "HAIR"}
        store._store.seed_stored(payload, version=STORAGE_VERSION,
                                 minor_version=STORAGE_VERSION_MINOR)
        await store.async_load()
        command = store.get_all_devices()[0].commands[0]
        assert command.decoded_command == 0x00
        assert command.decoded_extras["counter"] == 1
