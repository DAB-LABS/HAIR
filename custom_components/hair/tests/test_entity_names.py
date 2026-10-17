"""The device name said once (mobile pass, 2026-10-17).

The owner's phone showed a Mirror row "via KinCony AGv3 1 KinCony AGv3 1
TX": HA composes the friendly name as device name plus entity name, and
HAIR's shipped ESPHome configs name the transmitter
``${friendly_name} TX``, so the device name printed twice.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import entity_names
from custom_components.hair.entity_names import (
    collapse_doubled_device_name,
    entity_display_name,
)


@pytest.mark.parametrize(
    "friendly,device,expected",
    [
        # The owner's case, and the same shape on VM999's test emitters.
        ("KinCony AGv3 1 KinCony AGv3 1 TX", "KinCony AGv3 1", "KinCony AGv3 1 TX"),
        (
            "Garage Workbench IR Puck Garage Workbench IR Puck TX",
            "Garage Workbench IR Puck",
            "Garage Workbench IR Puck TX",
        ),
        ("Den Den", "Den", "Den"),
        # Said once already: untouched.
        ("KinCony AGv3 1 TX", "KinCony AGv3 1", "KinCony AGv3 1 TX"),
        ("Broadlink RM4 Pro", "Broadlink RM4 Pro", "Broadlink RM4 Pro"),
        # A repeated word that is not the device's name: untouched.
        ("Bora Bora Lamp", "Lamp", "Bora Bora Lamp"),
        ("Bora Bora Lamp IR", "Bora Bora Lamp", "Bora Bora Lamp IR"),
        # A device name that is only a prefix of a word: untouched.
        ("Den Denon TX", "Den", "Den Denon TX"),
        # Nothing to go on.
        ("Kitchen TX", None, "Kitchen TX"),
        ("Kitchen TX", "", "Kitchen TX"),
        ("", "Kitchen", ""),
    ],
)
def test_collapse(friendly, device, expected):
    assert collapse_doubled_device_name(friendly, device) == expected


def _hass(friendly: str | None):
    hass = MagicMock()
    state = None if friendly is None else MagicMock(attributes={"friendly_name": friendly})
    hass.states.get = MagicMock(return_value=state)
    return hass


def _registries(device_name: str | None, name_by_user: str | None = None, *, has_device=True):
    entry = MagicMock(device_id="dev1")
    device = MagicMock(name_by_user=name_by_user)
    # MagicMock reserves ``name`` in its constructor; set it afterwards.
    device.name = device_name
    ent_reg = MagicMock()
    ent_reg.async_get = MagicMock(return_value=entry)
    dev_reg = MagicMock()
    dev_reg.async_get = MagicMock(return_value=device if has_device else None)
    return (
        patch.object(entity_names.er, "async_get", return_value=ent_reg),
        patch.object(entity_names.dr, "async_get", return_value=dev_reg),
    )


def test_display_name_says_the_device_once():
    hass = _hass("KinCony AGv3 1 KinCony AGv3 1 TX")
    p1, p2 = _registries("KinCony AGv3 1")
    with p1, p2:
        assert entity_display_name(hass, "infrared.kincony_tx") == "KinCony AGv3 1 TX"


def test_display_name_uses_the_users_device_name():
    hass = _hass("Rack Rack TX")
    p1, p2 = _registries("KinCony AGv3 1", name_by_user="Rack")
    with p1, p2:
        assert entity_display_name(hass, "infrared.rack_tx") == "Rack TX"


def test_display_name_without_a_device_is_the_friendly_name():
    hass = _hass("KinCony AGv3 1 KinCony AGv3 1 TX")
    p1, p2 = _registries(None, has_device=False)
    with p1, p2:
        assert (
            entity_display_name(hass, "infrared.kincony_tx")
            == "KinCony AGv3 1 KinCony AGv3 1 TX"
        )


def test_display_name_without_a_state_is_the_entity_id():
    assert entity_display_name(_hass(None), "infrared.gone") == "infrared.gone"


def test_registry_trouble_falls_back_to_the_friendly_name():
    hass = _hass("KinCony AGv3 1 KinCony AGv3 1 TX")
    with patch.object(entity_names.er, "async_get", side_effect=RuntimeError("boom")):
        assert (
            entity_display_name(hass, "infrared.kincony_tx")
            == "KinCony AGv3 1 KinCony AGv3 1 TX"
        )


def test_the_mirror_label_path_uses_it():
    """``SignalMonitor._friendly_name`` builds every Mirror "via"."""
    from custom_components.hair.signal_monitor import SignalMonitor

    monitor = SignalMonitor.__new__(SignalMonitor)
    monitor._hass = _hass("KinCony AGv3 1 KinCony AGv3 1 TX")
    p1, p2 = _registries("KinCony AGv3 1")
    with p1, p2:
        assert monitor._friendly_name("infrared.kincony_tx") == "KinCony AGv3 1 TX"
