"""The storage pluck: schema, placement, and re-pluck idempotency.

Commit 1 reads a store. This is what HAIR does with what it read.

Three things are being pinned here.

THE MECHANISM IS DECLARED, not inferred. A pluckable YAML now says
whether it is reached by replay or by reading its store, and schema v2
exists because ``service`` had to stop being required: a store reader
has nothing to put in one. A v1 file keeps loading untouched and reads
as replay.

PLACEMENT IS BY STORE COORDINATES. A plucked remote records which
integration, which store, and which subdevice it came out of, and those
three are how a second import finds the remote it already made.

RE-PLUCK IS THE SAME CALL. There is no separate refresh path to keep in
step: importing a store twice adds nothing, renames nothing, keeps every
alias, and reports what it found instead. The ticket asked for that to
be pinned rather than assumed, because "the tiered identity gives us
dedupe for free" is exactly the kind of thing that is true until it is
not.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol

from custom_components.hair import pluck
from custom_components.hair.learned_code_stores import (
    PROVIDERS_BY_INTEGRATION,
    discover_stores,
    read_store,
)
from custom_components.hair.pluckable_loader import (
    DEFAULT_MECHANISM,
    load_pluckables,
    validate_pluckable,
)
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore

from .test_learned_code_stores import (  # shared fixture builders
    BROADLINK_STORE,
    TUYA_STORE,
    _broadlink_code,
    _tuya_code,
    _write_store,
)

_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None
_needs_library = pytest.mark.skipif(
    not _HAS_LIBRARY,
    reason="infrared-protocols unavailable (requires Python 3.13+)",
)

PLUCKABLE_DIR = Path(__file__).parent.parent / "pluckable"
_TUYA_TAIL = 64464


def _nec_frame(address: int, command: int) -> list[int]:
    """A real 32-bit NEC frame, LSB first, so the decoder can name it.

    The wash needs something washable: a code the registry can decode
    transmits from canonical timings afterwards, and one it cannot stays
    raw. Both outcomes are correct, so the tests need one of each.
    """
    out = [9000, 4500]
    for byte in (address, ~address & 0xFF, command, ~command & 0xFF):
        for bit in range(8):
            out += [560, 1690 if (byte >> bit) & 1 else 560]
    out.append(560)
    return out


def _monitor(fake_hass) -> tuple[SignalMonitor, SignalStore]:
    store = SignalStore(fake_hass)
    store._loaded = True
    store.schedule_save = MagicMock()
    store.async_save = AsyncMock()
    hair = MagicMock()
    hair.get_all_devices = MagicMock(return_value=[])
    hair.get_device = MagicMock(return_value=None)
    hair.async_save = AsyncMock()
    hair.match_command = MagicMock(return_value=None)
    return SignalMonitor(fake_hass, store, hair), store


@pytest.fixture
def store_dir(tmp_path: Path) -> Path:
    """A Broadlink store and a Tuya store, both worth importing.

    Broadlink: one decodable NEC command, one toggle pair, one RF packet.
    Tuya: one decodable NEC command and one failed learn.
    """
    _write_store(
        tmp_path,
        BROADLINK_STORE,
        {
            "tv": {
                "power": _broadlink_code(_nec_frame(0x04, 0x08)),
                "mute": [
                    _broadlink_code([8900, -4400, 600, -600, 600]),
                    _broadlink_code([8900, -4400, 600, -1700, 600]),
                ],
            },
            "gate": {
                "open": _broadlink_code([400, -400, 400], type_byte=0xB2),
            },
        },
    )
    _write_store(
        tmp_path,
        TUYA_STORE,
        {
            "test_remote": {
                "power_button": _tuya_code([*_nec_frame(0x10, 0x20), _TUYA_TAIL]),
            },
            "candles": {
                "OFF": "AAAAAAAAAAAA",
            },
        },
    )
    return tmp_path


def _info(store_dir: Path, integration: str):
    return next(
        s for s in discover_stores(store_dir) if s.integration == integration
    )


async def _import(monitor, store_dir: Path, integration: str, name: str):
    info = _info(store_dir, integration)
    return await monitor.import_learned_store(
        integration=integration,
        store_id=info.store_id,
        friendly_name=name,
        kind=PROVIDERS_BY_INTEGRATION[integration].kind,
        codes=read_store(info),
    )


# ---------------------------------------------------------------------
# The pluckable schema
# ---------------------------------------------------------------------


class TestPluckableMechanism:
    def test_a_v1_file_still_loads_and_reads_as_replay(self):
        entry = validate_pluckable(
            {
                "schema_version": 1,
                "name": "Legacy",
                "integration": "legacy",
                "service": {
                    "domain": "legacy",
                    "name": "send",
                    "target_param": "entity_id",
                    "data": {"command": "{command_name}"},
                },
            }
        )
        assert entry["mechanism"] == DEFAULT_MECHANISM == "replay"

    def test_a_storage_entry_needs_no_service(self):
        entry = validate_pluckable(
            {
                "schema_version": 2,
                "name": "Broadlink",
                "integration": "broadlink",
                "mechanism": "storage",
                "store_provider": "broadlink",
            }
        )
        assert entry["mechanism"] == "storage"
        assert entry["store_provider"] == "broadlink"
        assert "service" not in entry

    def test_a_storage_entry_with_a_service_is_refused(self):
        with pytest.raises(vol.Invalid):
            validate_pluckable(
                {
                    "schema_version": 2,
                    "name": "Broadlink",
                    "integration": "broadlink",
                    "mechanism": "storage",
                    "store_provider": "broadlink",
                    "service": {
                        "domain": "broadlink",
                        "name": "send",
                        "target_param": "entity_id",
                        "data": {"command": "{command_name}"},
                    },
                }
            )

    def test_a_storage_entry_without_a_provider_is_refused(self):
        with pytest.raises(vol.Invalid):
            validate_pluckable(
                {
                    "schema_version": 2,
                    "name": "Broadlink",
                    "integration": "broadlink",
                    "mechanism": "storage",
                }
            )

    def test_a_replay_entry_without_a_service_is_refused(self):
        with pytest.raises(vol.Invalid):
            validate_pluckable(
                {
                    "schema_version": 2,
                    "name": "Nope",
                    "integration": "nope",
                    "mechanism": "replay",
                }
            )

    def test_an_unknown_mechanism_is_refused(self):
        with pytest.raises(vol.Invalid):
            validate_pluckable(
                {
                    "schema_version": 2,
                    "name": "Nope",
                    "integration": "nope",
                    "mechanism": "telepathy",
                    "store_provider": "nope",
                }
            )


class TestShippedRegistry:
    """The three entries HAIR ships, loaded from the real directory."""

    def test_all_three_load(self):
        registry = load_pluckables(PLUCKABLE_DIR)
        pairs = {(e["integration"], e["mechanism"]) for e in registry}
        assert ("tuya_local", "replay") in pairs
        assert ("tuya_local", "storage") in pairs
        assert ("broadlink", "storage") in pairs

    def test_tuya_local_ships_both_mechanisms_side_by_side(self):
        """The dedupe key is (integration, mechanism), not integration.

        Before this release one entry per integration was the rule, and
        under that rule the second Tuya file would have been skipped
        with a warning and the storage pluck would simply never appear.
        """
        registry = load_pluckables(PLUCKABLE_DIR)
        tuya = [e for e in registry if e["integration"] == "tuya_local"]
        assert len(tuya) == 2

    def test_storage_integrations_offers_exactly_the_store_readers(self):
        registry = load_pluckables(PLUCKABLE_DIR)
        assert set(pluck.storage_integrations(registry)) == {
            "broadlink",
            "tuya_local",
        }

    def test_list_vendors_ignores_storage_entries(self, fake_hass):
        """A storage pluckable has no service, so the replay discovery
        must not reach for one. It used to be safe to assume every entry
        had a service block; it is not any more."""
        fake_hass.services.has_service = MagicMock(return_value=False)
        registry = load_pluckables(PLUCKABLE_DIR)
        assert pluck.list_vendors(fake_hass, registry) == []


# ---------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------


class TestImportPlacement:
    async def test_one_remote_per_subdevice_named_for_the_store(
        self, fake_hass, store_dir
    ):
        monitor, store = _monitor(fake_hass)
        summary = await _import(monitor, store_dir, "broadlink", "Living Room RM4")

        assert summary["remotes"] == 1  # only "tv" has importable codes
        labels = sorted(d.label for d in store.get_all_devices())
        assert labels == ["Living Room RM4: tv"]

    async def test_the_remote_records_its_store_coordinates(
        self, fake_hass, store_dir
    ):
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")

        device = store.get_all_devices()[0]
        assert device.source == "plucked"
        assert device.store_integration == "broadlink"
        assert device.store_id == "a4cf12880e2f"
        assert device.store_subdevice == "tv"
        # Synthetic fingerprint: a live capture must never group in here.
        assert device.fingerprint.startswith("plucked:")
        # It is a store, not an entity. Nothing to point at.
        assert device.vendor_entity_id is None

    async def test_command_names_come_through_intact(
        self, fake_hass, store_dir
    ):
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")

        names = {s.plucked_command_name for s in store.get_all_devices()[0].signals}
        assert names == {"power", "mute", "mute (alt)"}

    async def test_the_name_is_also_the_alias_so_the_row_shows_it(
        self, fake_hass, store_dir
    ):
        """Bench find. The catalog row renders the alias and falls back
        to S/L diamonds, so a store import with no alias is a wall of
        anonymous rows even though every name arrived. The replay path
        seeds the alias from the name its dialog collects; a store read
        has no dialog, so it seeds at import."""
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")

        for signal in store.get_all_devices()[0].signals:
            assert signal.alias == signal.plucked_command_name
            assert signal.alias

    async def test_rf_and_failed_learns_are_counted_not_imported(
        self, fake_hass, store_dir
    ):
        monitor, _ = _monitor(fake_hass)
        broadlink = await _import(
            monitor, store_dir, "broadlink", "Living Room RM4"
        )
        assert broadlink["rf_receipted"] == 1
        assert broadlink["signals"] == 3

        monitor2, store2 = _monitor(fake_hass)
        tuya = await _import(monitor2, store_dir, "tuya_local", "IR Remote Garage")
        assert tuya["no_timings"] == 1
        assert tuya["signals"] == 1
        assert tuya["remotes"] == 1
        assert [d.label for d in store2.get_all_devices()] == [
            "IR Remote Garage: test_remote"
        ]

    async def test_toggle_pairs_are_counted_once_each(
        self, fake_hass, store_dir
    ):
        monitor, _ = _monitor(fake_hass)
        summary = await _import(
            monitor, store_dir, "broadlink", "Living Room RM4"
        )
        assert summary["toggle_pairs"] == 1

    @_needs_library
    async def test_a_decodable_code_is_washed_and_the_rest_kept_raw(
        self, fake_hass, store_dir
    ):
        """The wash, measured. A code the registry can name transmits
        from canonical timings afterwards; one it cannot stays raw, which
        is not a failure, just a code nothing here speaks."""
        monitor, store = _monitor(fake_hass)
        summary = await _import(
            monitor, store_dir, "broadlink", "Living Room RM4"
        )
        assert summary["washed"] == 1
        assert summary["kept_raw"] == 2
        assert summary["washed"] + summary["kept_raw"] == summary["signals"]

        power = next(
            s
            for s in store.get_all_devices()[0].signals
            if s.plucked_command_name == "power"
        )
        assert power.decoded_protocol == "NEC"
        # 0xFB04, not 0x04: the decoder reads the NEC address field as
        # the full 16 bits (address then its inverse), which is the
        # extended-NEC form and what HAIR has always stored. Asserted as
        # the real value rather than papered over, since the identity
        # this code files under is the thing being pinned.
        assert power.decoded_address == 0xFB04
        assert power.decoded_command == 0x08

    async def test_every_code_lands_as_a_plucked_row(
        self, fake_hass, store_dir
    ):
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")
        for signal in store.get_all_devices()[0].signals:
            assert signal.source == "plucked"
            assert signal.frequency == 38000


# ---------------------------------------------------------------------
# RE-PLUCK IDEMPOTENCY (ticket-mandated, both providers)
# ---------------------------------------------------------------------


class TestRePluckIdempotency:
    @pytest.mark.parametrize(
        ("integration", "name"),
        [("broadlink", "Living Room RM4"), ("tuya_local", "IR Remote Garage")],
    )
    async def test_a_second_import_adds_nothing_and_says_so(
        self, fake_hass, store_dir, integration, name
    ):
        monitor, store = _monitor(fake_hass)
        first = await _import(monitor, store_dir, integration, name)
        assert first["already_present"] == 0

        devices_before = len(store.get_all_devices())
        signals_before = sum(len(d.signals) for d in store.get_all_devices())

        second = await _import(monitor, store_dir, integration, name)

        assert len(store.get_all_devices()) == devices_before
        assert sum(len(d.signals) for d in store.get_all_devices()) == signals_before
        assert second["signals"] == first["signals"]
        assert second["already_present"] == second["signals"]
        assert second["remotes"] == first["remotes"]

    async def test_names_and_aliases_survive_a_re_pluck(
        self, fake_hass, store_dir
    ):
        """The point of the guard, stated as the user would state it: I
        renamed this button, do not undo that."""
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")

        device = store.get_all_devices()[0]
        device.label = "The Good Remote"
        signal = device.signals[0]
        signal.alias = "Big Red Button"
        signal_id = signal.id

        await _import(monitor, store_dir, "broadlink", "Living Room RM4")

        device = store.get_all_devices()[0]
        assert device.label == "The Good Remote"
        kept = device.get_signal_by_id(signal_id)
        assert kept is not None
        assert kept.alias == "Big Red Button"


# ---------------------------------------------------------------------
# The store record behind the Devices-tab row
# ---------------------------------------------------------------------


class TestPluckedStoreRecord:
    async def test_a_pluck_records_the_store(self, fake_hass, store_dir):
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")

        records = store.get_plucked_stores()
        assert len(records) == 1
        assert records[0]["integration"] == "broadlink"
        assert records[0]["store_id"] == "a4cf12880e2f"
        assert records[0]["friendly_name"] == "Living Room RM4"
        assert records[0]["kind"] == "Broadlink learned codes"
        assert records[0]["id"]
        assert records[0]["first_plucked"] == records[0]["last_plucked"]

    async def test_a_re_pluck_refreshes_rather_than_duplicates(
        self, fake_hass, store_dir
    ):
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")
        first = store.get_plucked_stores()[0]
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")

        records = store.get_plucked_stores()
        assert len(records) == 1
        assert records[0]["id"] == first["id"]
        assert records[0]["first_plucked"] == first["first_plucked"]

    async def test_forgetting_the_record_leaves_the_remotes_alone(
        self, fake_hass, store_dir
    ):
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")
        record_id = store.get_plucked_stores()[0]["id"]

        assert store.remove_plucked_store(record_id) is True
        assert store.get_plucked_stores() == []
        assert len(store.get_all_devices()) == 1
        assert store.get_all_devices()[0].signals

    def test_forgetting_something_that_is_not_there_is_false(self, fake_hass):
        _, store = _monitor(fake_hass)
        assert store.remove_plucked_store("nope") is False

    async def test_records_round_trip_through_the_payload(
        self, fake_hass, store_dir
    ):
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")
        payload = store._serialize()
        assert payload["plucked_stores"][0]["store_id"] == "a4cf12880e2f"


class TestStoreCoordinatesRoundTrip:
    async def test_a_saved_remote_comes_back_with_its_store(
        self, fake_hass, store_dir
    ):
        from custom_components.hair.models import UnknownDevice

        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "broadlink", "Living Room RM4")
        payload = store.get_all_devices()[0].to_dict()
        again = UnknownDevice.from_dict(payload)
        assert again.store_integration == "broadlink"
        assert again.store_id == "a4cf12880e2f"
        assert again.store_subdevice == "tv"
