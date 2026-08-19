"""Models round-trip unknown keys (0.10.1 item 2).

WHAT HAPPENED, from the 0.10.0 regression bench. Bisecting on the live
store, a build from before Track M rewrote the trigger-remote store on
every trigger fire and dropped ``climate_matrix`` and ``last_heard``
from every remote, because its own ``to_dict`` did not know them. Three
matrix remotes came back as flat remotes on the release build and had to
be repaired from backup. HACS lets a user redownload an older release in
two clicks, so this is a path real installs take.

The guard: every model keeps the keys its parser did not consume and
writes them back last. It cannot repair a store already damaged, and it
cannot help against a field an older build actively rewrites -- what it
does is stop the older build from being the REASON a newer field
disappeared.

The forgetful case is the one this has to survive long-term: a field
added in six months, wired into to_dict and from_dict, and not added to
the model's declared key set. It would then round-trip twice, once
through its own attribute and once through _extra, and the two copies
would drift. ``test_every_written_key_is_declared`` fails the moment
that happens.
"""
from __future__ import annotations

import json

import pytest

from custom_components.hair.models import (
    _KNOWN_CATALOG_DEVICE,
    _KNOWN_COMMAND,
    _KNOWN_DEVICE,
    _KNOWN_ENTITY_CONFIG,
    _KNOWN_REMOTE,
    _KNOWN_SIGNAL,
    _KNOWN_TRIGGER,
    EntityConfig,
    IRCommand,
    IRDevice,
    IRTrigger,
    TriggerRemote,
    UnknownDevice,
    UnknownSignal,
)

# Every model that carries the guard, with the declared key set the
# forgetful-case test measures its to_dict against.
MODELS = [
    pytest.param(IRCommand, _KNOWN_COMMAND, id="IRCommand"),
    pytest.param(EntityConfig, _KNOWN_ENTITY_CONFIG, id="EntityConfig"),
    pytest.param(IRDevice, _KNOWN_DEVICE, id="IRDevice"),
    pytest.param(IRTrigger, _KNOWN_TRIGGER, id="IRTrigger"),
    pytest.param(TriggerRemote, _KNOWN_REMOTE, id="TriggerRemote"),
    pytest.param(UnknownSignal, _KNOWN_SIGNAL, id="UnknownSignal"),
    pytest.param(UnknownDevice, _KNOWN_CATALOG_DEVICE, id="UnknownDevice"),
]


@pytest.mark.parametrize("model,known", MODELS)
def test_two_unknown_keys_survive_parse_and_serialize(model, known):
    payload = model().to_dict()
    payload["a_field_from_the_future"] = {"nested": [1, 2, 3]}
    payload["another_one"] = "hello"

    written = model.from_dict(dict(payload)).to_dict()

    assert written["a_field_from_the_future"] == {"nested": [1, 2, 3]}
    assert written["another_one"] == "hello"


@pytest.mark.parametrize("model,known", MODELS)
def test_a_round_trip_is_byte_for_byte(model, known):
    payload = model().to_dict()
    payload["future"] = ["a", {"b": 1}, None]

    once = model.from_dict(dict(payload)).to_dict()
    twice = model.from_dict(dict(once)).to_dict()

    assert json.dumps(once, sort_keys=True) == json.dumps(
        twice, sort_keys=True
    )


@pytest.mark.parametrize("model,known", MODELS)
def test_nothing_known_lands_in_extra(model, known):
    parsed = model.from_dict(model().to_dict())
    assert parsed._extra == {}


@pytest.mark.parametrize("model,known", MODELS)
def test_every_written_key_is_declared(model, known):
    """The forgetful case: a new field wired into to_dict and from_dict
    but never added to the declared set would round-trip twice, once as
    its own attribute and once through _extra, and the two would drift.
    """
    assert set(model().to_dict()) <= set(known)


@pytest.mark.parametrize("model,known", MODELS)
def test_a_known_key_in_extra_never_shadows_the_field(model, known):
    """Belt for a hand-edited store: _extra is written with setdefault,
    so the parsed attribute always wins."""
    obj = model.from_dict(model().to_dict())
    key = sorted(obj.to_dict())[0]
    obj._extra[key] = "poison"

    assert obj.to_dict()[key] != "poison"


@pytest.mark.parametrize("model,known", MODELS)
def test_extra_is_not_part_of_equality(model, known):
    """Two records differing only in keys neither build understands are
    the same record; every "did anything change" check in HAIR would
    otherwise start reporting changes it cannot describe."""
    payload = model().to_dict()
    plain = model.from_dict(dict(payload))
    future = model.from_dict({**payload, "future": 1})

    assert future._extra == {"future": 1}
    assert plain == future


class TestTheRemoteThatWasDamaged:
    """The exact shape of the bisect finding, run forwards."""

    def test_an_older_parser_keeps_the_fields_it_does_not_know(self):
        from custom_components.hair.models import _with_extra

        current = TriggerRemote(
            id="tr1", name="Bedroom AC", climate_matrix=True,
            last_heard={"cell_key": "cool/auto/23", "at": "2026-08-18"},
        ).to_dict()
        # The older build, modelled honestly: its parser consumed only
        # the keys it knew, and its to_dict wrote only those back. The
        # guard is the one line it gains.
        older = _KNOWN_REMOTE - {"climate_matrix", "last_heard"}
        extra = {k: v for k, v in current.items() if k not in older}
        its_own_output = {k: v for k, v in current.items() if k in older}
        assert "climate_matrix" not in its_own_output

        rewritten = _with_extra(its_own_output, extra)

        assert rewritten["climate_matrix"] is True
        assert rewritten["last_heard"]["cell_key"] == "cool/auto/23"
        # And the release build reads its remote back whole.
        assert TriggerRemote.from_dict(rewritten).climate_matrix is True


class TestNestedModels:
    def test_a_command_inside_a_device_keeps_its_own_extra(self):
        device = IRDevice(name="TV", commands=[IRCommand(name="Power")])
        payload = device.to_dict()
        payload["commands"][0]["future_command_field"] = 7

        written = IRDevice.from_dict(payload).to_dict()

        assert written["commands"][0]["future_command_field"] == 7

    def test_an_entity_config_inside_a_device_keeps_its_own_extra(self):
        payload = IRDevice(name="TV").to_dict()
        payload["entity_config"]["future_config_field"] = "x"

        written = IRDevice.from_dict(payload).to_dict()

        assert written["entity_config"]["future_config_field"] == "x"

    def test_a_signal_inside_a_catalog_remote_keeps_its_own_extra(self):
        remote = UnknownDevice(
            fingerprint="grp", signals=[UnknownSignal(fingerprint="s1")]
        )
        payload = remote.to_dict()
        payload["signals"][0]["future_signal_field"] = [1]

        written = UnknownDevice.from_dict(payload).to_dict()

        assert written["signals"][0]["future_signal_field"] == [1]


class TestClonesCarryIt:
    def test_a_device_clone_carries_every_layer(self):
        payload = IRDevice(
            name="TV", commands=[IRCommand(name="Power")]
        ).to_dict()
        payload["future_device_field"] = 1
        payload["commands"][0]["future_command_field"] = 2
        payload["entity_config"]["future_config_field"] = 3

        clone = IRDevice.from_dict(payload).clone("TV copy")

        assert clone._extra["future_device_field"] == 1
        assert clone.commands[0]._extra["future_command_field"] == 2
        assert clone.entity_config._extra["future_config_field"] == 3

    def test_a_remote_clone_carries_it(self):
        payload = TriggerRemote(name="Handset").to_dict()
        payload["future_remote_field"] = "keep me"

        clone = TriggerRemote.from_dict(payload).clone("Handset copy")

        assert clone._extra["future_remote_field"] == "keep me"

    def test_a_clone_gets_its_own_dict(self):
        payload = TriggerRemote(name="Handset").to_dict()
        payload["future"] = "x"
        source = TriggerRemote.from_dict(payload)

        clone = source.clone("copy")
        clone._extra["future"] = "changed"

        assert source._extra["future"] == "x"


def test_the_derived_sl_pattern_is_never_captured():
    """to_dict DERIVES it from the code on every write, so capturing it
    would let a stale pattern outlive the code it described."""
    signal = UnknownSignal(
        fingerprint="s1", protocol="PRONTO",
        code="0000 006D 0002 0000 0020 0040 0020 0040",
    )
    payload = signal.to_dict()
    assert "sl_pattern" in payload

    parsed = UnknownSignal.from_dict(payload)

    assert "sl_pattern" not in parsed._extra
