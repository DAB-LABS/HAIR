"""Tests for pin bindings (signpost 4, Track 1: derivation).

The derived button map is what makes a pinned Remote drive a Device,
so the sharp edge here is not "does it map" but "does it ever map the
WRONG button". The byte_hash tests below are the load-bearing ones:
they pin the v0.5.8 rule into the pinning path, where a false match
would retransmit a sibling button rather than merely showing a stale
row in a list.
"""
from __future__ import annotations

import logging

import pytest

from custom_components.hair.identity import canonical_fingerprint
from custom_components.hair.models import (
    IRCommand,
    IRDevice,
    IRTrigger,
    TriggerRemote,
)
from custom_components.hair.pin_bindings import (
    bound_targets,
    build_device_index,
    derive_bindings,
    match_on_device,
    rederive_all_pinned,
    rederive_remote,
    rederive_remotes_for_device,
)
from custom_components.hair.storage import HAIRStore

_PRONTO_CODE = (
    "0000 006D 0006 0000 00E0 0070 0014 000D 0014 002E "
    "0014 000D 0014 000D 0014 0400"
)
_OTHER_PRONTO = (
    "0000 006D 0006 0000 00E0 0070 0014 002E 0014 000D "
    "0014 002E 0014 000D 0014 0400"
)


def _fp(code: str) -> str:
    """The fingerprint a stored row actually carries for this code.

    NOT ``signal_fingerprint(None, code, None)``, which is what this
    helper used to be. With no protocol stamp that hashes an EMPTY raw
    timing list and hands back one constant for every code, so both
    sides of the bare-fingerprint tests below met on a shared constant
    rather than on the code's own identity. GH #125 closed that in
    ``canonical_fingerprint``, which now reads an unstamped Pronto code
    as Pronto; this mirrors it, and is what the load-time backfill
    writes onto a legacy row.
    """
    return canonical_fingerprint(None, code, None)


class _FakeStore:
    """In-memory replacement for homeassistant.helpers.storage.Store."""

    def __init__(self, data=None):
        self._data = data

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


def _remote(store: HAIRStore, name: str, *pins: str) -> TriggerRemote:
    remote = TriggerRemote(name=name, pinned_device_ids=list(pins))
    store.add_trigger_remote(remote)
    return remote


def _trigger(store: HAIRStore, remote_id: str, name: str, **kw) -> IRTrigger:
    trigger = IRTrigger(name=name, trigger_remote_id=remote_id, **kw)
    store.add_trigger(trigger)
    return trigger


# ---------------------------------------------------------------------------
# Tier fidelity -- the same order and the same refusals as match_command
# ---------------------------------------------------------------------------


def test_decoded_identity_is_the_first_tier(fake_hass):
    """A decoded match wins even when the fingerprints disagree."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0xfb04:0x08")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    trig = _trigger(
        store, remote.id, "Power",
        decoded_fingerprint="NEC:0xfb04:0x08",
        signal_fingerprint="a-completely-different-fp",
    )

    assert derive_bindings(store, remote) == {
        dev.id: {trig.id: dev.commands[0].id}
    }


def test_composite_fingerprint_and_byte_hash_match(fake_hass):
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", code=_PRONTO_CODE, byte_hash="h1")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    trig = _trigger(
        store, remote.id, "Power",
        signal_fingerprint=_fp(_PRONTO_CODE), byte_hash="h1",
    )

    assert derive_bindings(store, remote)[dev.id] == {
        trig.id: dev.commands[0].id
    }


def test_byte_hash_alone_rescues_a_flipped_fingerprint(fake_hass):
    """Unified identity: a boundary protocol whose S/L fingerprint flips
    between captures still resolves through the hash-only tier."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", code=_PRONTO_CODE, byte_hash="h1")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    trig = _trigger(
        store, remote.id, "Power",
        signal_fingerprint="fp-from-the-other-side-of-the-boundary",
        byte_hash="h1",
    )

    assert derive_bindings(store, remote)[dev.id] == {
        trig.id: dev.commands[0].id
    }


def test_legacy_trigger_matches_a_legacy_command_on_the_bare_fingerprint(
    fake_hass,
):
    """Both sides hashless (pre-0.3.4): tier 3 is the only one that can
    fire, and it must still work or every old catalog stops mapping."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", code=_PRONTO_CODE)],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    trig = _trigger(
        store, remote.id, "Power", signal_fingerprint=_fp(_PRONTO_CODE),
    )

    assert derive_bindings(store, remote)[dev.id] == {
        trig.id: dev.commands[0].id
    }


def test_a_hash_miss_never_falls_through_to_a_hash_bearing_command(fake_hass):
    """THE regression guard. Two sub-threshold siblings share an S/L
    fingerprint and are separated only by byte_hash. A trigger whose hash
    matches neither must map to NOTHING -- not to whichever sibling the
    bare fingerprint happens to reach. Mapping it would make a pinned
    remote physically transmit the wrong button.
    """
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="Sony TV",
        commands=[
            IRCommand(name="One", code=_PRONTO_CODE, byte_hash="h1"),
            IRCommand(name="Two", code=_PRONTO_CODE, byte_hash="h2"),
        ],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    _trigger(
        store, remote.id, "Three",
        signal_fingerprint=_fp(_PRONTO_CODE), byte_hash="h3",
    )

    assert derive_bindings(store, remote)[dev.id] == {}


def test_sibling_triggers_map_to_their_own_commands(fake_hass):
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="Sony TV",
        commands=[
            IRCommand(name="One", code=_PRONTO_CODE, byte_hash="h1"),
            IRCommand(name="Two", code=_PRONTO_CODE, byte_hash="h2"),
        ],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    t1 = _trigger(
        store, remote.id, "One",
        signal_fingerprint=_fp(_PRONTO_CODE), byte_hash="h1",
    )
    t2 = _trigger(
        store, remote.id, "Two",
        signal_fingerprint=_fp(_PRONTO_CODE), byte_hash="h2",
    )

    assert derive_bindings(store, remote)[dev.id] == {
        t1.id: dev.commands[0].id,
        t2.id: dev.commands[1].id,
    }


def test_match_on_device_returns_none_for_an_empty_identity(fake_hass):
    index = build_device_index(IRDevice(name="Empty"))
    assert match_on_device(index, None, None, None) is None


# ---------------------------------------------------------------------------
# Many-to-many: per-trigger targeting emerges from content
# ---------------------------------------------------------------------------


def test_two_pinned_devices_split_the_buttons_by_content(fake_hass):
    """The bound doc's motivating case, in miniature: volume finds the
    soundbar, channel finds the TV, and neither needs a routing table."""
    store = HAIRStore(fake_hass)
    tv = IRDevice(
        name="TV",
        commands=[IRCommand(name="Channel Up", decoded_fingerprint="NEC:0x1:0x1")],
    )
    bar = IRDevice(
        name="Soundbar",
        commands=[IRCommand(name="Volume Up", decoded_fingerprint="NEC:0x2:0x2")],
    )
    store.add_device(tv)
    store.add_device(bar)
    remote = _remote(store, "Handset", tv.id, bar.id)
    chan = _trigger(
        store, remote.id, "Channel Up", decoded_fingerprint="NEC:0x1:0x1"
    )
    vol = _trigger(
        store, remote.id, "Volume Up", decoded_fingerprint="NEC:0x2:0x2"
    )

    bindings = derive_bindings(store, remote)
    assert bindings[tv.id] == {chan.id: tv.commands[0].id}
    assert bindings[bar.id] == {vol.id: bar.commands[0].id}


def test_a_pinned_device_sharing_nothing_keeps_an_empty_map(fake_hass):
    """Empty, not absent: the detail page has to tell "pinned, nothing
    matched" apart from "not pinned"."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="Unrelated",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x9:0x9")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    _trigger(store, remote.id, "Power", decoded_fingerprint="NEC:0x1:0x1")

    assert derive_bindings(store, remote) == {dev.id: {}}


def test_a_vanished_pinned_device_is_dropped_entirely(fake_hass):
    store = HAIRStore(fake_hass)
    remote = _remote(store, "Handset", "no-such-device")
    _trigger(store, remote.id, "Power", decoded_fingerprint="NEC:0x1:0x1")

    assert derive_bindings(store, remote) == {}


def test_only_this_remotes_triggers_are_mapped(fake_hass):
    """A trigger owned by another remote, or by the drawer, must not
    appear in this remote's map even when the content matches."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(dev)
    mine = _remote(store, "Mine", dev.id)
    theirs = _remote(store, "Theirs")
    ours = _trigger(store, mine.id, "Power", decoded_fingerprint="NEC:0x1:0x1")
    _trigger(store, theirs.id, "Power", decoded_fingerprint="NEC:0x1:0x1")
    store.add_trigger(
        IRTrigger(name="Drawer Power", decoded_fingerprint="NEC:0x1:0x1")
    )

    assert derive_bindings(store, mine)[dev.id] == {ours.id: dev.commands[0].id}


def test_disabled_triggers_are_still_mapped(fake_hass):
    """The retransmit rides the FIRE, and a disabled trigger never fires,
    so mapping it is harmless -- and keeps the stored map from churning
    every time someone toggles a checkbox."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    trig = _trigger(
        store, remote.id, "Power",
        decoded_fingerprint="NEC:0x1:0x1", enabled=False,
    )

    assert derive_bindings(store, remote)[dev.id] == {
        trig.id: dev.commands[0].id
    }


# ---------------------------------------------------------------------------
# Re-derivation
# ---------------------------------------------------------------------------


def test_rederive_reports_no_change_when_nothing_moved(fake_hass):
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    _trigger(store, remote.id, "Power", decoded_fingerprint="NEC:0x1:0x1")

    assert rederive_remote(store, remote) is True
    assert rederive_remote(store, remote) is False


def test_unpinning_drops_that_devices_map(fake_hass):
    """Unpin has to take the bindings with it, or a detached device keeps
    a live map pointing at it."""
    store = HAIRStore(fake_hass)
    tv = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    bar = IRDevice(
        name="Soundbar",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(tv)
    store.add_device(bar)
    remote = _remote(store, "Handset", tv.id, bar.id)
    _trigger(store, remote.id, "Power", decoded_fingerprint="NEC:0x1:0x1")
    rederive_remote(store, remote)
    assert set(remote.bindings) == {tv.id, bar.id}

    remote.pinned_device_ids.remove(bar.id)
    assert rederive_remote(store, remote) is True
    assert set(remote.bindings) == {tv.id}


def test_editing_a_command_rederives_every_remote_pinned_to_it(fake_hass):
    """The device-side hook: a command's identity changed, so the map is
    stale until this runs."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    trig = _trigger(store, remote.id, "Power", decoded_fingerprint="NEC:0x1:0x1")
    rederive_remote(store, remote)
    assert remote.bindings[dev.id] == {trig.id: dev.commands[0].id}

    dev.commands[0].decoded_fingerprint = "NEC:0xdead:0xbeef"
    assert rederive_remotes_for_device(store, dev.id) is True
    assert remote.bindings[dev.id] == {}


def test_a_device_nobody_pinned_rederives_nothing(fake_hass):
    store = HAIRStore(fake_hass)
    dev = IRDevice(name="TV", commands=[IRCommand(name="Power")])
    store.add_device(dev)
    _remote(store, "Handset")

    assert rederive_remotes_for_device(store, dev.id) is False


def test_rederive_all_pinned_skips_unpinned_remotes(fake_hass):
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(dev)
    pinned = _remote(store, "Pinned", dev.id)
    loose = _remote(store, "Loose")
    _trigger(store, pinned.id, "Power", decoded_fingerprint="NEC:0x1:0x1")
    _trigger(store, loose.id, "Power", decoded_fingerprint="NEC:0x1:0x1")

    assert rederive_all_pinned(store) is True
    assert pinned.bindings
    assert loose.bindings == {}


# ---------------------------------------------------------------------------
# The fire path's only read
# ---------------------------------------------------------------------------


def test_bound_targets_returns_every_pinned_device_with_a_mapping(fake_hass):
    store = HAIRStore(fake_hass)
    tv = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    bar = IRDevice(
        name="Soundbar",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(tv)
    store.add_device(bar)
    remote = _remote(store, "Handset", tv.id, bar.id)
    trig = _trigger(store, remote.id, "Power", decoded_fingerprint="NEC:0x1:0x1")
    rederive_remote(store, remote)

    assert sorted(bound_targets(store, remote.id, trig.id)) == sorted([
        (tv.id, tv.commands[0].id),
        (bar.id, bar.commands[0].id),
    ])


def test_bound_targets_is_empty_for_unmapped_and_unknown(fake_hass):
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x9:0x9")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    trig = _trigger(store, remote.id, "Power", decoded_fingerprint="NEC:0x1:0x1")
    rederive_remote(store, remote)

    assert bound_targets(store, remote.id, trig.id) == []
    assert bound_targets(store, "no-such-remote", trig.id) == []


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_bindings_survive_a_serialization_round_trip():
    remote = TriggerRemote(
        name="Handset",
        pinned_device_ids=["d1"],
        bindings={"d1": {"t1": "c1"}},
    )
    assert TriggerRemote.from_dict(remote.to_dict()).bindings == {
        "d1": {"t1": "c1"}
    }


def test_bindings_absent_from_an_older_store_read_as_empty():
    data = TriggerRemote(name="Handset").to_dict()
    del data["bindings"]
    assert TriggerRemote.from_dict(data).bindings == {}


@pytest.mark.parametrize(
    "raw",
    [
        {"d1": "not-a-dict"},
        {"d1": ["also", "wrong"]},
        {"d1": None},
    ],
)
def test_malformed_binding_entries_are_dropped(raw):
    """A hand-edited store must not put a non-mapping on the fire path."""
    data = TriggerRemote(name="Handset").to_dict()
    data["bindings"] = raw
    assert TriggerRemote.from_dict(data).bindings == {}


def test_binding_keys_and_values_are_coerced_to_strings():
    data = TriggerRemote(name="Handset").to_dict()
    data["bindings"] = {1: {2: 3}}
    assert TriggerRemote.from_dict(data).bindings == {"1": {"2": "3"}}


@pytest.mark.asyncio
async def test_load_backfills_pins_made_before_bindings_existed(fake_hass):
    """Signpost 3 shipped pin storage dark, so a store can hold pins with
    no map at all. The load-time backfill has to fill them, or those pins
    would drive nothing until the user happened to re-pin.
    """
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    trig = IRTrigger(
        name="Power",
        trigger_remote_id="tr1",
        decoded_fingerprint="NEC:0x1:0x1",
    )
    remote = TriggerRemote(id="tr1", name="Handset", pinned_device_ids=[dev.id])
    payload = {
        "devices": [dev.to_dict()],
        "triggers": [trig.to_dict()],
        "trigger_remotes": [remote.to_dict()],
    }
    payload["trigger_remotes"][0]["bindings"] = {}

    store = HAIRStore(fake_hass)
    store._store = _FakeStore(payload)
    await store.async_load()

    loaded = store.get_trigger_remote("tr1")
    assert loaded.bindings == {dev.id: {trig.id: dev.commands[0].id}}


@pytest.mark.asyncio
async def test_load_leaves_an_unpinned_remote_alone(fake_hass):
    remote = TriggerRemote(id="tr1", name="Handset")
    payload = {
        "devices": [],
        "triggers": [],
        "trigger_remotes": [remote.to_dict()],
    }

    store = HAIRStore(fake_hass)
    store._store = _FakeStore(payload)
    await store.async_load()

    assert store.get_trigger_remote("tr1").bindings == {}


# ---------------------------------------------------------------------------
# Dangling pins (0.10.1 item 8)
# ---------------------------------------------------------------------------
#
# Deleting a Device never removed its id from a Remote's
# pinned_device_ids, so the pin survived pointing at nothing. It stayed
# invisible because derivation SKIPS an id it cannot resolve: the remote
# sends nothing and cannot raise, while every surface that reads
# "pinned" off a non-empty list keeps saying it is pinned. The live test
# box carried four such ids across three remotes.


@pytest.mark.asyncio
async def test_load_drops_a_dangling_pin_and_keeps_the_valid_one(fake_hass):
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    trig = IRTrigger(
        name="Power",
        trigger_remote_id="tr1",
        decoded_fingerprint="NEC:0x1:0x1",
    )
    remote = TriggerRemote(
        id="tr1", name="Handset",
        pinned_device_ids=[dev.id, "gone-1"],
    )
    payload = {
        "devices": [dev.to_dict()],
        "triggers": [trig.to_dict()],
        "trigger_remotes": [remote.to_dict()],
    }

    store = HAIRStore(fake_hass)
    store._store = _FakeStore(payload)
    await store.async_load()

    loaded = store.get_trigger_remote("tr1")
    assert loaded.pinned_device_ids == [dev.id]
    assert set(loaded.bindings) == {dev.id}


@pytest.mark.asyncio
async def test_a_remote_with_only_dangling_pins_comes_back_unpinned(
    fake_hass, caplog
):
    """The four-ids case on the box: pinned to nothing, saying otherwise."""
    remote = TriggerRemote(
        id="tr1", name="Mitsubishi C56-RW5",
        pinned_device_ids=["e7a2a240", "d2406e7b"],
        bindings={"e7a2a240": {}},
    )
    payload = {
        "devices": [], "triggers": [], "trigger_remotes": [remote.to_dict()],
    }

    store = HAIRStore(fake_hass)
    store._store = _FakeStore(payload)
    with caplog.at_level(
        logging.INFO, logger="custom_components.hair.storage"
    ):
        await store.async_load()

    loaded = store.get_trigger_remote("tr1")
    assert loaded.pinned_device_ids == []
    assert loaded.bindings == {}
    assert "Dropped 2 dangling pin(s) from Remote 'Mitsubishi C56-RW5'" in (
        caplog.text
    )


@pytest.mark.asyncio
async def test_the_prune_writes_the_healed_store_once(fake_hass):
    """It folds into async_load's single save like the other backfills."""
    remote = TriggerRemote(
        id="tr1", name="Handset", pinned_device_ids=["gone-1"]
    )
    payload = {
        "devices": [], "triggers": [], "trigger_remotes": [remote.to_dict()],
    }
    store = HAIRStore(fake_hass)
    store._store = _FakeStore(payload)

    await store.async_load()

    saved = store._store._data["trigger_remotes"][0]
    assert saved["pinned_device_ids"] == []


@pytest.mark.asyncio
async def test_a_bindings_key_with_no_pin_is_residue_and_goes(fake_hass):
    dev = IRDevice(name="TV")
    remote = TriggerRemote(
        id="tr1", name="Handset", pinned_device_ids=[],
        bindings={dev.id: {"t1": "c1"}},
    )
    payload = {
        "devices": [dev.to_dict()], "triggers": [],
        "trigger_remotes": [remote.to_dict()],
    }
    store = HAIRStore(fake_hass)
    store._store = _FakeStore(payload)

    await store.async_load()

    assert store.get_trigger_remote("tr1").bindings == {}


@pytest.mark.asyncio
async def test_a_store_with_no_dangling_pins_is_not_rewritten(fake_hass):
    """The prune must not make every load a write."""
    dev = IRDevice(name="TV")
    remote = TriggerRemote(
        id="tr1", name="Handset", pinned_device_ids=[dev.id],
        bindings={dev.id: {}},
    )
    payload = {
        "devices": [dev.to_dict()], "triggers": [],
        "trigger_remotes": [remote.to_dict()],
    }
    store = HAIRStore(fake_hass)
    store._store = _FakeStore(payload)
    saved: list[dict] = []
    original = store._store.async_save

    async def _watch(data):
        saved.append(data)
        await original(data)

    store._store.async_save = _watch

    await store.async_load()

    assert saved == []


# ---------------------------------------------------------------------------
# The reverse direction: deleting a Remote (0.10.1 item 8, step 3)
# ---------------------------------------------------------------------------
#
# The device side deliberately stores NO pin of its own -- signpost 3's
# pin scope split keeps the link in exactly one place and derives the
# device view by scanning remotes -- so deleting a Remote takes the only
# copy of the link with it. The one device-side field that names a
# remote, IRDevice.source_remote_id, is a creation-door provenance stamp
# that nothing resolves; these pin both facts so a future reader does
# not have to re-derive them.


def test_deleting_a_remote_leaves_no_device_side_pin(fake_hass):
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        name="TV",
        commands=[IRCommand(name="Power", decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(dev)
    remote = _remote(store, "Handset", dev.id)
    _trigger(
        store, remote.id, "Power", decoded_fingerprint="NEC:0x1:0x1"
    )
    rederive_remote(store, remote)
    assert remote.bindings[dev.id]

    assert store.remove_trigger_remote(remote.id) is not None

    survivor = store.get_device(dev.id)
    assert survivor is not None
    # No field on the device names the gone remote, so nothing can
    # present as pinned the way pinned_device_ids did.
    assert survivor.source_remote_id is None
    assert bound_targets(store, remote.id, "any") == []


def test_a_source_remote_id_pointing_at_a_gone_remote_derives_nothing(
    fake_hass,
):
    """Provenance only: it is written at creation and never resolved."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(name="TV", source_remote_id="gone-remote")
    store.add_device(dev)

    assert rederive_all_pinned(store) is False
    assert store.get_device(dev.id).source_remote_id == "gone-remote"
    assert store.get_device(dev.id).to_dict()["source_remote_id"] == (
        "gone-remote"
    )
