"""What the Plucker tab can say about an install that has nothing.

The tab used to hide when nothing could be plucked right now, which
meant it hid hardest from the people it was built for: a Broadlink
owner who has only ever sent through HAIR has no replay vendor (there
is no such thing for Broadlink) and no codes file (Home Assistant
writes one only on a successful learn). Two false signals, no tab, no
explanation.

``list_sources`` answers the other question. Not "what can be plucked
now" but "what could this install ever pluck, and where does each route
stand today" -- so the empty card can say something true per source
instead of the tab vanishing.

Two properties are worth stating plainly, because both are easy to
break and neither is obvious from the shape of the data:

- COLLAPSED PER INTEGRATION. Tuya Local is registered twice, once per
  mechanism. A person has one Tuya Local, not two, so it is one entry
  carrying both.
- A PROVIDER APPEARS EVEN WHEN NOBODY HAS IT. No entities, no store, no
  config entry: it still lists, with ``loaded`` false. That is what
  lets an empty tab double as the feature's shop window.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hair import pluck
from custom_components.hair.learned_code_stores import PROVIDERS

REPLAY_TUYA = {
    "name": "Tuya Local",
    "integration": "tuya_local",
    "mechanism": "replay",
    "remote_feature_filter": "LEARN_COMMAND",
    "service": {
        "domain": "tuya_local",
        "name": "send_learned_ir_command",
        "target_param": "entity_id",
        "data": {"command": "{command_name}"},
    },
}
STORAGE_TUYA = {
    "name": "Tuya Local",
    "integration": "tuya_local",
    "mechanism": "storage",
    "store_provider": "tuya_local",
}
STORAGE_BROADLINK = {
    "name": "Broadlink",
    "integration": "broadlink",
    "mechanism": "storage",
    "store_provider": "broadlink",
}
REGISTRY = [REPLAY_TUYA, STORAGE_TUYA, STORAGE_BROADLINK]


def _entity(entity_id: str, platform: str, features: int = 1):
    entry = MagicMock()
    entry.entity_id = entity_id
    entry.platform = platform
    entry.supported_features = features
    entry.disabled_by = None
    entry.name = None
    entry.original_name = entity_id
    return entry


@pytest.fixture
def wired(fake_hass, tmp_path, monkeypatch):
    """A box with nothing: no services, no entities, no stores."""
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.config.components = set()
    fake_hass.services.has_service = MagicMock(return_value=False)
    registry = MagicMock()
    registry.entities = {}
    monkeypatch.setattr(
        "custom_components.hair.pluck.er.async_get",
        lambda _hass: registry,
    )
    monkeypatch.setattr(
        "custom_components.hair.pluck.discover_stores",
        lambda _config_dir: [],
    )
    return fake_hass, registry


def _by_integration(sources):
    return {source["integration"]: source for source in sources}


class TestTheShapeOfASource:
    @pytest.mark.asyncio
    async def test_tuya_local_is_one_entry_with_both_mechanisms(self, wired):
        """Registered twice, rendered once. The card says one line per
        source and Tuya Local is one source with two ways in."""
        hass, _registry = wired
        sources = _by_integration(await pluck.list_sources(hass, REGISTRY))
        assert len(sources) == 2
        tuya = sources["tuya_local"]
        assert tuya["mechanisms"] == ["replay", "storage"]
        assert tuya["name"] == "Tuya Local"
        assert set(tuya["ready"]) == {"replay", "storage"}

    @pytest.mark.asyncio
    async def test_broadlink_is_storage_only(self, wired):
        """Not an omission. remote.send_command transmits through the
        blaster's own hardware and cannot be aimed at the Tweezer, so
        Broadlink has no replay route to be ready or not ready."""
        hass, _registry = wired
        sources = _by_integration(await pluck.list_sources(hass, REGISTRY))
        broadlink = sources["broadlink"]
        assert broadlink["mechanisms"] == ["storage"]
        assert set(broadlink["ready"]) == {"storage"}

    @pytest.mark.asyncio
    async def test_sources_are_ordered(self, wired):
        hass, _registry = wired
        names = [s["name"] for s in await pluck.list_sources(hass, REGISTRY)]
        assert names == sorted(names, key=str.lower)


class TestWhatReadyMeans:
    @pytest.mark.asyncio
    async def test_an_empty_box_is_ready_nowhere(self, wired):
        hass, _registry = wired
        for source in await pluck.list_sources(hass, REGISTRY):
            assert not any(source["ready"].values()), source

    @pytest.mark.asyncio
    async def test_loaded_but_not_ready_is_the_reported_case(self, wired):
        """The bug in one line: the integration is right there, and
        there is still nothing to pluck. Both facts have to survive to
        the card, because the card's whole job is saying so."""
        hass, _registry = wired
        hass.config.components = {"broadlink"}
        sources = _by_integration(await pluck.list_sources(hass, REGISTRY))
        broadlink = sources["broadlink"]
        assert broadlink["loaded"] is True
        assert broadlink["ready"]["storage"] is False

    @pytest.mark.asyncio
    async def test_replay_is_ready_when_the_vendor_listing_would_list_it(
            self, wired):
        """The same test, through the same helper. A source that claims
        replay-ready while list_vendors omits the vendor would be two
        answers to one question."""
        hass, registry = wired
        hass.config.components = {"tuya_local"}
        hass.services.has_service = MagicMock(return_value=True)
        registry.entities = {
            "1": _entity("remote.tuya_blaster", "tuya_local"),
        }
        sources = _by_integration(await pluck.list_sources(hass, REGISTRY))
        assert sources["tuya_local"]["ready"]["replay"] is True
        assert sources["tuya_local"]["ready"]["storage"] is False
        assert [v["integration"] for v in pluck.list_vendors(hass, REGISTRY)] == [
            "tuya_local"
        ]

    @pytest.mark.asyncio
    async def test_an_entity_without_learn_support_is_not_ready(self, wired):
        """The feature filter is part of the vendor test, so it is part
        of this one."""
        hass, registry = wired
        hass.services.has_service = MagicMock(return_value=True)
        registry.entities = {
            "1": _entity("remote.tuya_blaster", "tuya_local", features=0),
        }
        sources = _by_integration(await pluck.list_sources(hass, REGISTRY))
        assert sources["tuya_local"]["ready"]["replay"] is False
        assert pluck.list_vendors(hass, REGISTRY) == []

    @pytest.mark.asyncio
    async def test_storage_is_ready_when_a_store_exists(self, wired,
                                                        monkeypatch):
        hass, _registry = wired
        info = MagicMock()
        info.integration = "broadlink"
        monkeypatch.setattr(
            "custom_components.hair.pluck.discover_stores",
            lambda _config_dir: [info],
        )
        sources = _by_integration(await pluck.list_sources(hass, REGISTRY))
        assert sources["broadlink"]["ready"]["storage"] is True
        assert sources["tuya_local"]["ready"]["storage"] is False

    @pytest.mark.asyncio
    async def test_one_mechanism_ready_leaves_the_other_alone(self, wired,
                                                             monkeypatch):
        """Tuya Local with a store but no live blaster: storage yes,
        replay no, one entry, both facts."""
        hass, _registry = wired
        hass.config.components = {"tuya_local"}
        info = MagicMock()
        info.integration = "tuya_local"
        monkeypatch.setattr(
            "custom_components.hair.pluck.discover_stores",
            lambda _config_dir: [info],
        )
        tuya = _by_integration(await pluck.list_sources(hass, REGISTRY))[
            "tuya_local"]
        assert tuya["ready"] == {"replay": False, "storage": True}


class TestTheShopWindow:
    @pytest.mark.asyncio
    async def test_a_provider_nobody_installed_still_lists(self, wired):
        """No entities, no store, no config entry -- and it still has a
        line on the card, because someone reading it may be deciding
        whether to go and install it."""
        hass, _registry = wired
        sources = _by_integration(
            await pluck.list_sources(hass, [REPLAY_TUYA, STORAGE_TUYA]))
        assert "broadlink" in sources
        broadlink = sources["broadlink"]
        assert broadlink["loaded"] is False
        assert broadlink["mechanisms"] == ["storage"]
        assert broadlink["ready"] == {"storage": False}

    @pytest.mark.asyncio
    async def test_every_store_provider_reaches_the_roll(self, wired):
        """Stated against the table itself rather than a hardcoded pair,
        so a provider added later cannot quietly go unlisted."""
        hass, _registry = wired
        sources = _by_integration(await pluck.list_sources(hass, []))
        for provider in PROVIDERS:
            assert provider.integration in sources

    @pytest.mark.asyncio
    async def test_a_provider_with_no_registry_entry_still_gets_a_name(
            self, wired):
        hass, _registry = wired
        sources = _by_integration(await pluck.list_sources(hass, []))
        assert sources["tuya_local"]["name"] == "Tuya Local"
        assert sources["broadlink"]["name"] == "Broadlink"

    @pytest.mark.asyncio
    async def test_the_registry_name_wins_over_the_derived_one(self, wired):
        hass, _registry = wired
        odd = dict(STORAGE_BROADLINK, name="Broadlink RM")
        sources = _by_integration(await pluck.list_sources(hass, [odd]))
        assert sources["broadlink"]["name"] == "Broadlink RM"
