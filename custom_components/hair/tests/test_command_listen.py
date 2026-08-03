"""Listen, repointed to the command editor.

Replace moved out of the fitting dialog and into command edit on device
detail (v0.9.5). Listening itself is context-free -- it hears whatever
the room emits and hands back one Pronto -- so the two callers share a
body and differ only in the event names they emit. That sharing is the
thing worth pinning: the behaviours below are the ones a caller could
silently lose by re-implementing rather than reusing.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.hair.const import DOMAIN, MIRROR_DEVICE_FP
from custom_components.hair.websocket_api import ws_command_listen

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


class _Monitor:
    def __init__(self) -> None:
        self.subscribers: list = []

    def subscribe(self, cb) -> None:
        self.subscribers.append(cb)

    def unsubscribe(self, cb) -> None:
        if cb in self.subscribers:
            self.subscribers.remove(cb)

    def emit(self, summary) -> None:
        for cb in list(self.subscribers):
            cb(summary)


def _signal(code=PRONTO, protocol="PRONTO", decoded_fp="NEC:0x1:0x2"):
    signal = MagicMock()
    signal.code = code
    signal.protocol = protocol
    signal.decoded_fingerprint = decoded_fp
    signal.decoded_protocol = "NEC"
    signal.heard_by = ["infrared.living_room"]
    return signal


def _store(signal):
    store = MagicMock()
    device = MagicMock()
    device.get_signal_by_id = MagicMock(return_value=signal)
    store.get_device = MagicMock(return_value=device)
    return store


def _summary(device_fp="dev-1"):
    return {
        "device_id": "dev-1",
        "device_fingerprint": device_fp,
        "signal_id": "sig-1",
        "protocol": "PRONTO",
        "code": PRONTO,
    }


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_event = MagicMock()
    conn.send_error = MagicMock()
    conn.subscriptions = {}
    return conn


def _arm(fake_hass, monitor, signal=None):
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": MagicMock(),
        "signal_monitor": monitor,
        "signal_store": _store(signal if signal else _signal()),
    }}
    conn = _conn()
    ws_command_listen(
        fake_hass, conn, {"id": 7, "type": "hair/command/listen"}
    )
    return conn


def test_a_heard_code_comes_back_on_the_command_channel(fake_hass):
    """Its own event names. The command editor and the fitting dialog
    can be open at once during the release that carries both, and a
    shared name would cross their wires."""
    monitor = _Monitor()
    conn = _arm(fake_hass, monitor)
    assert conn.send_result.call_args.args[1] == {"listening": True}

    monitor.emit(_summary())
    event = conn.send_event.call_args.args[1]
    assert event["type"] == "command_capture"
    assert event["pronto"] == PRONTO
    assert event["protocol"] == "NEC"


def test_mirror_rows_never_resolve_it(fake_hass):
    """The subscriber feed carries HAIR's OWN sends. Without the filter,
    pressing TEST on the command being replaced would drop HAIR's own
    transmission into the box as the remote's press."""
    monitor = _Monitor()
    conn = _arm(fake_hass, monitor)
    monitor.emit(_summary(device_fp=MIRROR_DEVICE_FP))
    conn.send_event.assert_not_called()
    assert monitor.subscribers


def test_a_rough_capture_still_lands_in_the_box(fake_hass):
    """Warn-and-allow. The amber line says it decoded to nothing; the
    person decides whether to keep it."""
    monitor = _Monitor()
    conn = _arm(fake_hass, monitor, _signal(decoded_fp=None))
    monitor.emit(_summary())
    event = conn.send_event.call_args.args[1]
    assert event["type"] == "command_capture"
    assert event["decoded"] is False


def test_a_capture_with_no_pronto_keeps_listening(fake_hass):
    monitor = _Monitor()
    conn = _arm(fake_hass, monitor, _signal(code=None, protocol=None))
    monitor.emit(_summary())
    conn.send_event.assert_not_called()
    assert monitor.subscribers


def test_the_window_closes_after_one(fake_hass):
    monitor = _Monitor()
    conn = _arm(fake_hass, monitor)
    monitor.emit(_summary())
    monitor.emit(_summary())
    assert conn.send_event.call_count == 1
    assert monitor.subscribers == []
    assert 7 not in conn.subscriptions


def test_timeout_says_so_on_the_command_channel(fake_hass):
    monitor = _Monitor()
    conn = _arm(fake_hass, monitor)
    _delay, on_timeout = fake_hass.loop.call_later.call_args.args
    on_timeout()
    assert conn.send_event.call_args.args[1] == {
        "type": "command_listen_timeout",
    }
    assert monitor.subscribers == []


def test_an_unconfigured_install_refuses(fake_hass):
    fake_hass.data = {}
    conn = _conn()
    ws_command_listen(
        fake_hass, conn, {"id": 7, "type": "hair/command/listen"}
    )
    assert conn.send_error.call_args.args[1] == "not_configured"
