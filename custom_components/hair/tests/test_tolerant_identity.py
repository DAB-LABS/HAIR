"""The lowest identity tier, end to end, on the air-path captures.

Where ``test_norm_fingerprint.py`` proves the value itself, this proves
who is allowed to use it: a trigger or command whose bytes never came
through a receiver, and nobody else. The captures and code sets are the
bench's own -- see ``fixtures/air-path/README.md``.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.hair.const import CommandCategory, CommandSource
from custom_components.hair.identity import (
    file_sourced_command,
    file_sourced_trigger,
    norm_fingerprint_of_code,
)
from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
from custom_components.hair.models import (
    CaptureResult,
    IRCommand,
    IRDevice,
    IRTrigger,
    TriggerRemote,
)
from custom_components.hair.signal_monitor import normalize
from custom_components.hair.storage import HAIRStore
from custom_components.hair.wig_identity import wig_signal_identity

AIR = Path(__file__).parent / "fixtures" / "air-path"


def air_code(name: str) -> str:
    return (AIR / f"{name}.pronto").read_text(encoding="utf-8").strip()


def air_captures(code: str, transmitter: str | None = None) -> list[dict]:
    with gzip.open(AIR / "captures.csv.gz", "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(io.StringIO(fh.read())))
    return [
        r for r in rows
        if r["code"] == code
        and (transmitter is None or r["transmitter"] == transmitter)
    ]


def heard(row: dict):
    """One capture, normalized exactly as the Sniffer normalizes it."""
    values = json.loads(row["timings_us"])
    raw = [v if i % 2 == 0 else -abs(v) for i, v in enumerate(values)]
    return normalize(
        CaptureResult(
            protocol="PRONTO",
            code=raw_to_pronto(raw, frequency=38000),
            raw_timings=raw,
            frequency=38000,
        )
    )


def stretched(code: str, factor: float = 1.15) -> str:
    """The same shape at a different speed: a different waveform."""
    words = code.split()
    return " ".join(
        words[:4] + [f"{round(int(w, 16) * factor):04X}" for w in words[4:]]
    )


@pytest.fixture
def store():
    store = HAIRStore(MagicMock())
    store._loaded = True
    return store


def wig_trigger(code: str, name: str, remote_id: str, origin: str = "closet"):
    """A trigger as ws_wig_make_remote mints one: identity from the file."""
    identity = wig_signal_identity(code)
    assert identity is not None
    return IRTrigger(
        name=name,
        signal_fingerprint=identity.fingerprint,
        protocol="PRONTO",
        code=identity.pronto,
        byte_hash=identity.byte_hash,
        decoded_fingerprint=identity.decoded_fingerprint,
        trigger_remote_id=remote_id,
        origin=origin,
    )


# --- the trigger tier ------------------------------------------------------


def test_a_wig_minted_trigger_fires_on_a_real_press(store):
    """The failure this exists to fix, on the bench's own captures.

    Sixteen ACER triggers sat on a Remote and never fired. The file's
    byte hash is not what a receiver hands back: every capture below
    misses the trigger on the tiers above, and lands on it through the
    normalized one.
    """
    remote = TriggerRemote(name="ACER", origin="closet")
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("F1"), "Power", remote.id)
    store._triggers[trigger.id] = trigger

    rows = air_captures("F1")
    assert len(rows) == 4
    for row in rows:
        signal = heard(row)
        if row["transmitter"] != "inject":
            assert not trigger.matches_signal(
                signal.sig_fp, signal.byte_hash, signal.decoded_fingerprint
            )
        matched = store.get_triggers_for_signal(
            "PRONTO", signal.code, signal.sig_fp, signal.byte_hash,
            signal.decoded_fingerprint, signal.norm_fp,
        )
        assert [t.id for t in matched] == [trigger.id], row["first_seen"]


def test_the_tier_is_not_reached_without_it(store):
    """Called the old way, the same press still misses.

    The tier is opt-in per call site, so a caller that has not been
    threaded through cannot start matching by accident.
    """
    remote = TriggerRemote(name="ACER", origin="closet")
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("F1"), "Power", remote.id)
    store._triggers[trigger.id] = trigger

    signal = heard(air_captures("F1", "esphome")[0])
    assert store.get_triggers_for_signal(
        "PRONTO", signal.code, signal.sig_fp, signal.byte_hash,
        signal.decoded_fingerprint,
    ) == []


def test_two_file_sourced_triggers_of_one_shape_fire_neither(store):
    """One press must not run two buttons' automations."""
    remote = TriggerRemote(name="ACER", origin="closet")
    store._trigger_remotes[remote.id] = remote
    first = wig_trigger(air_code("F1"), "Power", remote.id)
    second = wig_trigger(stretched(air_code("F1")), "Power (twin)", remote.id)
    store._triggers[first.id] = first
    store._triggers[second.id] = second
    assert norm_fingerprint_of_code(first.code) == norm_fingerprint_of_code(
        second.code
    )

    signal = heard(air_captures("F1", "esphome")[0])
    assert store.get_triggers_for_signal(
        "PRONTO", signal.code, signal.sig_fp, signal.byte_hash,
        signal.decoded_fingerprint, signal.norm_fp,
    ) == []


def test_a_capture_that_decoded_never_reaches_the_trigger_tier(store):
    remote = TriggerRemote(name="ACER", origin="closet")
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("F1"), "Power", remote.id)
    store._triggers[trigger.id] = trigger

    signal = heard(air_captures("F1", "esphome")[0])
    assert store.get_triggers_for_signal(
        "PRONTO", signal.code, signal.sig_fp, signal.byte_hash,
        "NEC:0x0007:0x02", signal.norm_fp,
    ) == []


# --- who counts as file-sourced -------------------------------------------


def test_the_closet_door_is_file_sourced(store):
    remote = TriggerRemote(name="ACER", origin="closet")
    store._trigger_remotes[remote.id] = remote
    assert file_sourced_trigger(
        wig_trigger(air_code("F1"), "Power", remote.id), store
    )


def test_a_lattice_remotes_own_rows_are_file_sourced(store):
    """A trigger saved from a matrix card carries the DIALOG's origin.

    Track M's "+ Trigger" and the LAST HEARD row both create through the
    ordinary trigger dialog, so the door says "manual" while the bytes
    came out of a lattice file. The owning Remote is what knows.
    """
    remote = TriggerRemote(name="Bench Handset", climate_matrix=True)
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("C1"), "Cool 23", remote.id, origin="manual")
    assert file_sourced_trigger(trigger, store)


def test_a_state_trigger_is_file_sourced(store):
    """Track M's own "+ Trigger" stamps origin="matrix" from the panel.

    Found on the bench: the Bench Matrix Handset's two triggers carry
    it, and the door that writes it is the frontend rather than any of
    the Python mint doors, which is why the first reading of the mint
    doors missed it.
    """
    remote = TriggerRemote(name="Bench Handset", climate_matrix=True)
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("C1"), "Cool 23", remote.id, origin="matrix")
    assert file_sourced_trigger(trigger, store)
    # And on a Remote that is no longer a lattice, the origin still says
    # where the bytes came from.
    orphan = wig_trigger(air_code("C1"), "Cool 23", "gone", origin="matrix")
    assert file_sourced_trigger(orphan, store)


def test_the_drawer_is_not_file_sourced(store):
    """A trigger typed into the drawer's own dialog is nobody's file."""
    trigger = wig_trigger(air_code("F1"), "Power", "", origin="manual")
    trigger.trigger_remote_id = None
    assert not file_sourced_trigger(trigger, store)


def test_a_sniffer_promoted_remote_is_not_file_sourced(store):
    """origin="remote" is a catalog remote, and the catalog is the air.

    Clipper and Plucker rows are file-sourced in truth and share this
    origin value, so they miss the tier: the vocabulary has four values
    and the panel paints all four, so widening it is a frontend change
    rather than something to guess at here.
    """
    remote = TriggerRemote(name="Sniffed remote", origin="remote")
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("F1"), "Power", remote.id, origin="remote")
    assert not file_sourced_trigger(trigger, store)


def test_a_device_minted_trigger_asks_the_command(store):
    """origin="device" defers to the row the trigger was cut from."""
    adopted = IRDevice(name="ACER TV", source_wig_id="wig-1")
    learned = IRDevice(name="Sniffed TV")
    for device in (adopted, learned):
        command = CaptureResult(
            protocol="PRONTO",
            code=air_code("F1"),
            raw_timings=ProntoCommand(air_code("F1")).get_raw_timings(),
        ).to_command("Power", CommandCategory.CUSTOM)
        device.commands.append(command)
        store._data[device.id] = device

    def trigger_for(device: IRDevice) -> IRTrigger:
        return IRTrigger(
            name="Power",
            signal_fingerprint="fp",
            protocol="PRONTO",
            code=air_code("F1"),
            source_device_id=device.id,
            source_command_id=device.commands[0].id,
            origin="device",
        )

    assert file_sourced_trigger(trigger_for(adopted), store)
    assert not file_sourced_trigger(trigger_for(learned), store)


# --- who counts as file-sourced, command side ------------------------------


def test_a_stamped_command_is_file_sourced():
    assert file_sourced_command(IRCommand(source=CommandSource.IMPORTED))
    assert file_sourced_command(IRCommand(source=CommandSource.MATRIX))
    assert file_sourced_command(IRCommand(source=CommandSource.DATABASE))
    assert not file_sourced_command(IRCommand(source=CommandSource.CAPTURED))


def test_a_plucked_command_is_file_sourced():
    """It was replayed by a vendor integration and never crossed air."""
    assert file_sourced_command(IRCommand(plucked_command_name="power"))


def test_an_adopted_device_answers_for_its_older_rows():
    """The upgrade path: a wig adopted before the doors stamped anything.

    Only for rows carrying no decoded identity -- a decoded row already
    matches on tier 1 and has no use for this one.
    """
    device = IRDevice(name="ACER TV", source_wig_id="wig-1")
    undecoded = IRCommand(name="Power", code=air_code("F1"))
    decoded = IRCommand(
        name="Mute", code=air_code("D1"), decoded_fingerprint="SAMSUNG32:0:1"
    )
    assert file_sourced_command(undecoded, device)
    assert not file_sourced_command(decoded, device)
    assert not file_sourced_command(undecoded, IRDevice(name="Sniffed TV"))


# --- the command tier ------------------------------------------------------


def adopted_device(code: str, name: str = "Power") -> IRDevice:
    """A device as Adopt Device mints one from a wig."""
    identity = wig_signal_identity(code)
    assert identity is not None
    device = IRDevice(name="ACER TV", source_wig_id="wig-1")
    command = CaptureResult(
        protocol="PRONTO",
        code=identity.pronto,
        raw_timings=list(identity.raw_timings),
        frequency=identity.frequency,
    ).to_command(name, CommandCategory.CUSTOM)
    command.source = CommandSource.IMPORTED
    command.byte_hash = identity.byte_hash
    command.decoded_fingerprint = identity.decoded_fingerprint
    device.commands.append(command)
    return device


def test_a_wig_adopted_command_is_recognized_on_a_real_press(store):
    """A device adopted from a wig, and the real remote in someone's hand."""
    device = adopted_device(air_code("F1"))
    store._data[device.id] = device
    store._rebuild_command_index()
    ref = (device.id, device.commands[0].id)

    for row in air_captures("F1", "esphome") + air_captures("F1", "broadlink"):
        signal = heard(row)
        assert store.match_command(
            signal.decoded_fingerprint, signal.sig_fp, signal.byte_hash
        ) is None
        assert store.match_command(
            signal.decoded_fingerprint, signal.sig_fp, signal.byte_hash,
            signal.norm_fp,
        ) == ref


def test_a_learned_command_is_not_offered_the_tier(store):
    """The same code on a device nobody adopted from a file."""
    device = adopted_device(air_code("F1"))
    device.source_wig_id = None
    device.commands[0].source = CommandSource.CAPTURED
    store._data[device.id] = device
    store._rebuild_command_index()

    signal = heard(air_captures("F1", "esphome")[0])
    assert store.match_command(
        signal.decoded_fingerprint, signal.sig_fp, signal.byte_hash,
        signal.norm_fp,
    ) is None


def test_two_file_commands_of_one_shape_match_neither(store):
    device = adopted_device(air_code("F1"))
    twin = adopted_device(stretched(air_code("F1")), name="Power (twin)")
    device.commands.append(twin.commands[0])
    store._data[device.id] = device
    store._rebuild_command_index()

    signal = heard(air_captures("F1", "esphome")[0])
    assert store.match_command(
        signal.decoded_fingerprint, signal.sig_fp, signal.byte_hash,
        signal.norm_fp,
    ) is None


def test_a_wig_trigger_binds_to_the_same_wigs_command(store):
    """Pinning, across the file-to-file gap.

    A Remote made from a wig and a Device adopted from the same wig
    hold identities computed from one file. Neither is what the air
    would produce, and until this tier the pin map came back empty for
    every undecoded row.
    """
    from custom_components.hair.pin_bindings import derive_bindings

    device = adopted_device(air_code("F1"))
    store._data[device.id] = device
    remote = TriggerRemote(
        name="ACER", origin="closet", pinned_device_ids=[device.id]
    )
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("F1"), "Power", remote.id)
    store._triggers[trigger.id] = trigger

    bindings = derive_bindings(store, remote)
    assert bindings == {device.id: {trigger.id: device.commands[0].id}}


def test_a_learned_trigger_binds_to_nothing_through_the_tier(store):
    """Same shapes, no file on either side, no binding."""
    from custom_components.hair.pin_bindings import derive_bindings

    device = adopted_device(air_code("F1"))
    device.source_wig_id = None
    device.commands[0].source = CommandSource.CAPTURED
    store._data[device.id] = device
    remote = TriggerRemote(
        name="Sniffed", origin="remote", pinned_device_ids=[device.id]
    )
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(
        stretched(air_code("F1")), "Power", remote.id, origin="remote"
    )
    store._triggers[trigger.id] = trigger

    assert derive_bindings(store, remote) == {device.id: {}}


# --- the guards ------------------------------------------------------------


def test_a_receiver_learned_trigger_never_matches_on_the_tier_alone(store):
    """The v0.5.8 lesson, restated as a rule with teeth.

    The same code, the same capture, the same normalized value -- and no
    match, because this trigger's bytes came off the air and its own
    tiers already work. Handing it this one would re-collapse the
    sibling buttons the byte hash exists to separate.
    """
    remote = TriggerRemote(name="Sniffed remote", origin="remote")
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("F1"), "Power", remote.id, origin="remote")
    store._triggers[trigger.id] = trigger

    for row in air_captures("F1", "esphome"):
        signal = heard(row)
        assert signal.norm_fp == norm_fingerprint_of_code(trigger.code)
        assert store.get_triggers_for_signal(
            "PRONTO", signal.code, signal.sig_fp, signal.byte_hash,
            signal.decoded_fingerprint, signal.norm_fp,
        ) == []


def test_two_sony_buttons_still_separate_through_the_decoded_tier(store):
    """The collision the tier would cause if it were ever reached.

    Sony encodes bits in mark width, so a whole keypad shares one S/L
    fingerprint AND one normalized fingerprint. Every one of those
    buttons decodes, so the decoded tier answers first and the question
    never gets that far -- and if the library were absent, the
    ambiguity rule drops the lot rather than picking one.
    """
    from custom_components.hair.tests.test_bytehash_identity import (
        SONY_BLUE,
        SONY_RED,
    )

    assert norm_fingerprint_of_code(SONY_RED) == norm_fingerprint_of_code(
        SONY_BLUE
    )

    remote = TriggerRemote(name="Sony (from a wig)", origin="closet")
    store._trigger_remotes[remote.id] = remote
    red = wig_trigger(SONY_RED, "Red", remote.id)
    blue = wig_trigger(SONY_BLUE, "Blue", remote.id)
    store._triggers[red.id] = red
    store._triggers[blue.id] = blue

    identity = wig_signal_identity(SONY_RED)
    assert identity is not None
    if identity.decoded_fingerprint:
        # The decoded tier answers, and answers with one button.
        matched = store.get_triggers_for_signal(
            "PRONTO", identity.pronto, identity.fingerprint,
            identity.byte_hash, identity.decoded_fingerprint,
            norm_fingerprint_of_code(SONY_RED),
        )
        assert [t.id for t in matched] == [red.id]
    # With or without the decoder, the shared normalized value alone
    # never fires either button.
    assert store.get_triggers_for_signal(
        "PRONTO", None, "a-fingerprint-from-another-capture", "no-hash",
        None, norm_fingerprint_of_code(SONY_RED),
    ) == []


def test_the_cell_index_resolves_c1_to_its_coordinates():
    """The rehearsal's 1.1, as a test: cool/auto/23 from a real press."""
    from custom_components.hair.matrix_listener import build_cell_index
    from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

    matrix = ClimateMatrix(
        min_temp=16.0, max_temp=30.0, precision=1.0,
        modes=["cool", "heat"], fan_modes=["auto", "low"], swing_modes=[],
        off=None,
        cells=[
            ClimateCell(
                mode="cool", fan="auto", temp=23.0, pronto=air_code("C1")
            ),
            ClimateCell(
                mode="heat", fan="low", temp=20.0, pronto=air_code("C2")
            ),
        ],
    )
    index = build_cell_index(matrix)
    for row in air_captures("C1", "esphome"):
        signal = heard(row)
        matched = index.match(
            signal.decoded_fingerprint, signal.sig_fp, signal.byte_hash,
            signal.norm_fp,
        )
        assert matched is not None
        assert matched[0].cell_key == "cool/auto/23"
        assert matched[0].mode == "cool"
        assert matched[0].fan == "auto"
        assert matched[0].temp == 23.0


# --- one press, one fire (owner ruling 2026-08-18) -------------------------


def trigger_manager_for(store):
    from custom_components.hair.trigger_manager import TriggerManager

    hass = MagicMock()
    hass.bus = MagicMock()
    return TriggerManager(hass, store)


def press_frames(store, manager, code_name: str, transmitter: str = "esphome"):
    """Feed both frames of one real press at the trigger manager."""
    fired = []
    for row in air_captures(code_name, transmitter)[:2]:
        signal = heard(row)
        fired.append(
            manager.on_signal_captured(
                signal.sig_fp, "PRONTO", signal.code, None,
                "infrared.athom_rx", signal.byte_hash,
                signal.decoded_fingerprint, signal.norm_fp,
            )
        )
    return fired


def test_one_press_of_a_two_frame_code_fires_a_trigger_once(store):
    """The bench's finding A on the trigger side, closed.

    Measured before the fix: one press fired the state trigger twice,
    and a three-press hold fired it four times. The listener and the
    trigger now use one number, so the state and the automation agree
    about what a press was.
    """
    remote = TriggerRemote(name="Bench Handset", climate_matrix=True)
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("C1"), "Cool 23", remote.id, origin="matrix")
    store._triggers[trigger.id] = trigger
    manager = trigger_manager_for(store)

    fired = press_frames(store, manager, "C1")

    assert [len(f) for f in fired] == [1, 0]


def test_a_receiver_learned_row_keeps_the_tighter_window(store):
    """The wider window is scoped, not global.

    A captured button's repeat frames are what the 100 ms window was
    sized for, and a fast double-press of an ordinary button must still
    count twice.
    """
    from custom_components.hair.identity import is_multi_frame_code

    remote = TriggerRemote(name="Sniffed remote", origin="remote")
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("C1"), "Something", remote.id, origin="remote")
    store._triggers[trigger.id] = trigger
    manager = trigger_manager_for(store)

    assert is_multi_frame_code(trigger.code)
    assert not manager._is_multi_frame_file_row(trigger)


def test_a_single_frame_file_row_keeps_the_tighter_window(store):
    """Only multi-frame codes need the wider one: F1 is one frame."""
    from custom_components.hair.identity import is_multi_frame_code

    remote = TriggerRemote(name="ACER", origin="closet")
    store._trigger_remotes[remote.id] = remote
    trigger = wig_trigger(air_code("F1"), "Power", remote.id)
    store._triggers[trigger.id] = trigger
    manager = trigger_manager_for(store)

    assert not is_multi_frame_code(trigger.code)
    assert not manager._is_multi_frame_file_row(trigger)
