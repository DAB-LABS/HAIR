"""Clipper and Plucker rows are file-sourced (owner ruling 2026-08-18).

Closing the gap the regression bench found over air: an Arris Power code
pasted through the Clipper was stamped "remote", exactly like a sniffed
row, so the receiver-tolerant tier was refused it. Its normalized
fingerprint matched the air capture exactly; nothing else did.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.hair.identity import (
    FILE_SOURCED_TRIGGER_ORIGINS,
    canonical_byte_hash,
    canonical_fingerprint,
    file_sourced_trigger,
    norm_fingerprint_of_code,
)
from custom_components.hair.models import IRTrigger, TriggerRemote, UnknownDevice
from custom_components.hair.signal_monitor import CATALOG_SOURCE_TRIGGER_ORIGIN
from custom_components.hair.storage import HAIRStore

FIXTURE = (
    Path(__file__).parent / "fixtures" / "air-path" / "arris-power-clip.json"
)


@pytest.fixture
def arris():
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def store():
    s = HAIRStore.__new__(HAIRStore)
    s._data = {}
    s._triggers = {}
    s._trigger_remotes = {}
    s._loaded = True
    return s


class _FakeSignalStore:
    def __init__(self, devices):
        self._devices = devices

    def get_all_devices(self):
        return self._devices


# ---------------------------------------------------------------------------
# The doors
# ---------------------------------------------------------------------------


class TestTheMintDoorStamps:
    """The promote door reads the catalog row's source.

    Every trigger mint door and what it writes:

    - signal_monitor.promote_to_remote -- the USE-as-a-Remote fork for all
      three catalog tabs. THE door this commit changes: it now maps
      UnknownDevice.source through CATALOG_SOURCE_TRIGGER_ORIGIN instead
      of hardcoding "remote".
    - websocket_api.ws_wig_make_remote -- "closet", unchanged.
    - websocket_api.ws_device_make_remote -- "device", unchanged; the
      source command decides.
    - websocket_api.ws_duplicate_trigger_remote -- copies the source
      trigger's origin, so clip and plucked propagate for free.
    - websocket_api.ws_create_trigger -- takes the origin the panel sends
      ("matrix" for the lattice doors). Not changed: a trigger created
      through this door on a Clipper-promoted Remote lands as "remote"
      and is repaired by the backfill on the next load.
    """

    def test_a_clipper_row_stamps_clip(self):
        assert CATALOG_SOURCE_TRIGGER_ORIGIN["manual"] == "clip"

    def test_a_plucker_row_stamps_plucked(self):
        assert CATALOG_SOURCE_TRIGGER_ORIGIN["plucked"] == "plucked"

    def test_a_sniffed_row_still_stamps_remote(self):
        assert CATALOG_SOURCE_TRIGGER_ORIGIN["sniffed"] == "remote"

    def test_an_unknown_source_falls_back_to_remote(self):
        """echo never reaches the door; the default must be the safe one."""
        assert CATALOG_SOURCE_TRIGGER_ORIGIN.get("echo", "remote") == "remote"


# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------


class TestThePredicate:
    def _trigger(self, store, origin):
        remote = TriggerRemote(name="R", origin="remote")
        store._trigger_remotes[remote.id] = remote
        t = IRTrigger(
            name="Power",
            signal_fingerprint="fp",
            protocol="PRONTO",
            code="0000 006D 0002 0000 0010 0010",
            trigger_remote_id=remote.id,
            origin=origin,
        )
        store._triggers[t.id] = t
        return t

    def test_clip_is_file_sourced(self, store):
        assert file_sourced_trigger(self._trigger(store, "clip"), store)

    def test_plucked_is_file_sourced(self, store):
        assert file_sourced_trigger(self._trigger(store, "plucked"), store)

    def test_remote_is_not(self, store):
        assert not file_sourced_trigger(self._trigger(store, "remote"), store)

    def test_the_vocabulary_is_the_ruled_one(self):
        assert set(FILE_SOURCED_TRIGGER_ORIGINS) == set(
            ("closet", "matrix", "clip", "plucked")
        )


# ---------------------------------------------------------------------------
# The backfill
# ---------------------------------------------------------------------------


class TestTheBackfill:
    def _setup(self, store, source):
        remote = TriggerRemote(name="Arris", origin="remote")
        store._trigger_remotes[remote.id] = remote
        t = IRTrigger(
            name="Power",
            signal_fingerprint="fp",
            protocol="PRONTO",
            code="0000 006D 0002 0000 0010 0010",
            trigger_remote_id=remote.id,
            origin="remote",
        )
        store._triggers[t.id] = t
        unknown = UnknownDevice(
            label="Arris", source=source, promoted_to_remote=remote.id
        )
        return t, _FakeSignalStore([unknown])

    def test_a_clipper_promote_is_restamped(self, store):
        t, sig = self._setup(store, "manual")
        assert store.backfill_catalog_trigger_origins(sig) is True
        assert t.origin == "clip"

    def test_a_plucker_promote_is_restamped(self, store):
        t, sig = self._setup(store, "plucked")
        assert store.backfill_catalog_trigger_origins(sig) is True
        assert t.origin == "plucked"

    def test_a_real_sniffed_promote_is_left_alone(self, store):
        t, sig = self._setup(store, "sniffed")
        assert store.backfill_catalog_trigger_origins(sig) is False
        assert t.origin == "remote"

    def test_it_does_not_touch_other_origins(self, store):
        t, sig = self._setup(store, "manual")
        t.origin = "closet"
        assert store.backfill_catalog_trigger_origins(sig) is False
        assert t.origin == "closet"

    def test_it_is_idempotent(self, store):
        t, sig = self._setup(store, "manual")
        assert store.backfill_catalog_trigger_origins(sig) is True
        assert store.backfill_catalog_trigger_origins(sig) is False
        assert t.origin == "clip"

    def test_an_unpromoted_row_changes_nothing(self, store):
        t, _ = self._setup(store, "manual")
        unknown = UnknownDevice(label="loose", source="manual")
        assert store.backfill_catalog_trigger_origins(
            _FakeSignalStore([unknown])
        ) is False
        assert t.origin == "remote"


# ---------------------------------------------------------------------------
# The bench fixture: the Arris row that could not hear itself
# ---------------------------------------------------------------------------


class TestTheArrisFixture:
    def _store_with(self, store, origin, arris):
        remote = TriggerRemote(name="Arris Vip 2952 V2 (1)", origin="remote")
        store._trigger_remotes[remote.id] = remote
        t = IRTrigger(
            name="Power",
            signal_fingerprint=arris["file"]["signal_fingerprint"],
            protocol="PRONTO",
            code=arris["file"]["pronto"],
            byte_hash=arris["file"]["byte_hash"],
            decoded_fingerprint=arris["file"]["decoded_fingerprint"],
            trigger_remote_id=remote.id,
            origin=origin,
        )
        store._triggers[t.id] = t
        return t

    def _air(self, arris):
        code = arris["air"]["pronto"]
        return (
            canonical_fingerprint("PRONTO", code, None),
            canonical_byte_hash(code),
            norm_fingerprint_of_code(code),
            code,
        )

    def test_the_air_form_moved_the_byte_hash_but_not_the_norm_fp(self, arris):
        """What the bench measured, restated as an assertion."""
        fp, bh, nfp, _ = self._air(arris)
        assert fp == arris["file"]["signal_fingerprint"]
        assert bh != arris["file"]["byte_hash"]
        assert nfp == norm_fingerprint_of_code(arris["file"]["pronto"])
        assert nfp is not None

    def test_as_shipped_it_matched_nothing(self, store, arris):
        """origin=remote: every tier misses and the press is lost."""
        self._store_with(store, arris["file"]["origin_as_shipped"], arris)
        fp, bh, nfp, code = self._air(arris)

        assert store.get_triggers_for_signal(
            "PRONTO", code, fp, bh, None, nfp
        ) == []

    def test_stamped_clip_it_matches_on_the_normalized_tier(self, store, arris):
        t = self._store_with(store, "clip", arris)
        fp, bh, nfp, code = self._air(arris)

        hits = store.get_triggers_for_signal("PRONTO", code, fp, bh, None, nfp)

        assert [h.id for h in hits] == [t.id]

    def test_and_still_needs_the_normalized_tier_to_do_it(self, store, arris):
        """Without norm_fp the clip row is no better off: the tier is what
        carries it, the origin only decides whether it is offered."""
        self._store_with(store, "clip", arris)
        fp, bh, _, code = self._air(arris)

        assert store.get_triggers_for_signal(
            "PRONTO", code, fp, bh, None, None
        ) == []
