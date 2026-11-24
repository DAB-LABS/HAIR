"""Radio codes plucked out of a learned-code store.

A Broadlink RM4 Pro stores a learned radio code whole, its header with
the carrier included, and an older RM pro stores the 4-byte 0xB2 and
0xD7 types. Both now land as radio rows on the sub-device's plucked
remote, written as a Clipper paste of the same code is written. A
rolling code lands too, filed by its fixed part, and is never sent.

Tuya Local writes a radio code as "rf:" and its hub's own study string,
which HAIR cannot read; it is set aside as radio, never read as IR.

Every code here is synthetic, in the layout each store uses.
"""
from __future__ import annotations

import base64

from custom_components.hair.learned_code_stores import (
    RECEIPT_RF,
    decode_tuya_local_code,
    discover_stores,
    read_store,
)
from custom_components.hair.rf_send import rolling_row
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _capture as _kl_capture

from .test_learned_code_stores import BROADLINK_STORE, TUYA_STORE, _tuya_code, _write_store
from .test_learned_store_ws import _result, _wire
from .test_pluck_ghost_doors import BROADLINK_ID, _import, _list, _remote, _store
from .test_rf_paste_rm4_header import _capture, _four_byte, _frame, _ticks

TUYA_ID = "eb6383fed1128526f7zzwf"


def _b64(packet: bytes) -> str:
    return base64.b64encode(packet).decode("ascii")


def _rm4_of(timings: list[int], type_byte: int, khz: int) -> str:
    body = khz.to_bytes(4, "little") + _ticks(timings) + bytes([0, 0x05, 0xDC])
    return _b64(bytes([type_byte, 0xC0]) + len(body).to_bytes(2, "little") + body)


def _keeloq_press(hopping: int) -> list[int]:
    return _kl_capture(_kl_bits(hopping=hopping), words=4)


def _store_with(tmp_path, subdevices: dict) -> None:
    _write_store(tmp_path, BROADLINK_STORE, subdevices)


class TestTheReader:
    def test_an_rm4_capture_is_a_radio_code_at_any_carrier(self, tmp_path):
        _store_with(tmp_path, {"plug": {
            "off_315": _b64(_capture(0x78, 315_000)),
            "off_433": _b64(_capture(0xB1, 433_920)),
            "off_433_42": _b64(_capture(0xB0, 433_420)),
        }})
        (info,) = [s for s in discover_stores(tmp_path) if s.integration == "broadlink"]
        assert (info.ir_codes, info.rf_codes) == (0, 3)
        codes = read_store(info)
        assert all(c.radio and c.pronto is None and c.receipt is None for c in codes)
        assert all(c.rf_code for c in codes)

    def test_a_four_byte_radio_code_reads_too(self, tmp_path):
        _store_with(tmp_path, {"gate": {"open": _b64(_four_byte(0xB2, 3, _frame() * 4))}})
        (info,) = [s for s in discover_stores(tmp_path) if s.integration == "broadlink"]
        (code,) = read_store(info)
        assert code.radio

    def test_infrared_beside_radio_is_still_infrared(self, tmp_path):
        from .test_learned_code_stores import _broadlink_code

        _store_with(tmp_path, {"mixed": {
            "power": _broadlink_code([9000, -4500, 560, -560, 560]),
            "gate": _b64(_capture(0xB1, 433_920)),
        }})
        (info,) = [s for s in discover_stores(tmp_path) if s.integration == "broadlink"]
        assert (info.ir_codes, info.rf_codes) == (1, 1)
        by_name = {c.command_name: c for c in read_store(info)}
        assert by_name["power"].imported and not by_name["power"].radio
        assert by_name["gate"].radio and not by_name["gate"].imported


class TestTheImport:
    async def test_radio_lands_on_the_sub_devices_remote(self, fake_hass, tmp_path):
        from .test_learned_code_stores import _broadlink_code

        _store_with(tmp_path, {"mixed": {
            "power": _broadlink_code([9000, -4500, 560, -560, 560]),
            "plug_off": _b64(_capture(0x78, 315_000)),
        }})
        store = _wire(fake_hass, tmp_path)
        summary = _result(await _import(fake_hass, BROADLINK_ID, "mixed"))
        assert (summary["remotes"], summary["signals"]) == (1, 2)
        radio = (summary["rf_imported"], summary["rf_rolling"], summary["rf_receipted"])
        assert radio == (1, 0, 0)
        assert summary["washed"] + summary["kept_raw"] == 1  # infrared only
        (device,) = store.get_all_devices()
        radio = next(s for s in device.signals if s.medium == "rf")
        assert radio.alias == "plug_off"
        assert radio.plucked_command_name == "plug_off"
        assert radio.source == "plucked"
        assert (radio.rf_frequency_hz, radio.rf_frequency_source) == (315_000_000, "signal")
        assert radio.code is None and radio.raw_timings

    async def test_a_plucked_row_is_the_same_row_a_paste_makes(self, fake_hass, tmp_path):
        """The identity a Clipper paste of the same code would have."""
        from custom_components.hair import rf_paste

        code = _b64(_capture(0xB1, 433_920))
        _store_with(tmp_path, {"plug": {"on": code}})
        store = _wire(fake_hass, tmp_path)
        await _import(fake_hass, BROADLINK_ID, "plug")
        (device,) = store.get_all_devices()
        (row,) = device.signals
        pasted = rf_paste.validate(code)
        assert (row.fingerprint, row.byte_hash) == (pasted["fingerprint"], pasted["frame_hash"])

    async def test_a_second_pluck_adds_nothing(self, fake_hass, tmp_path):
        _store_with(tmp_path, {"plug": {"off": _b64(_capture(0xB1, 433_920))}})
        store = _wire(fake_hass, tmp_path)
        await _import(fake_hass, BROADLINK_ID, "plug")
        second = _result(await _import(fake_hass, BROADLINK_ID, "plug"))
        assert second["already_present"] == second["signals"] == 1
        assert sum(len(d.signals) for d in store.get_all_devices()) == 1

    async def test_a_rolling_code_lands_and_is_never_sent(self, fake_hass, tmp_path):
        _store_with(tmp_path, {"gate": {
            "open": _rm4_of(_keeloq_press(0x0BADF00D), 0xB1, 433_920),
        }})
        store = _wire(fake_hass, tmp_path)
        summary = _result(await _import(fake_hass, BROADLINK_ID, "gate"))
        assert (summary["rf_imported"], summary["rf_rolling"]) == (1, 1)
        (device,) = store.get_all_devices()
        (row,) = device.signals
        assert row.decoded_fingerprint  # filed by its fixed part
        assert rolling_row(row) is not None

    async def test_two_presses_of_one_rolling_button_are_one_row(self, fake_hass, tmp_path):
        """A toggle pair learned as two presses of the same button has two
        hopping codes and one fixed part: one row, the second already there."""
        _store_with(tmp_path, {"gate": {"open": [
            _rm4_of(_keeloq_press(1), 0xB1, 433_920),
            _rm4_of(_keeloq_press(0x12345678), 0xB1, 433_920),
        ]}})
        store = _wire(fake_hass, tmp_path)
        summary = _result(await _import(fake_hass, BROADLINK_ID, "gate"))
        assert (summary["signals"], summary["already_present"]) == (2, 1)
        assert sum(len(d.signals) for d in store.get_all_devices()) == 1

    async def test_a_radio_only_sub_device_is_a_remote_now(self, fake_hass, tmp_path):
        _store_with(tmp_path, {"plug": {"off": _b64(_capture(0x78, 315_000))}})
        store = _wire(fake_hass, tmp_path)
        summary = _result(await _import(fake_hass, BROADLINK_ID, "plug"))
        assert summary["remotes"] == 1
        assert [d.store_subdevice for d in store.get_all_devices()] == ["plug"]


class TestTuyaLocal:
    def test_an_rf_code_is_set_aside_never_read_as_infrared(self):
        """Read as IR, ``rf:`` plus a plain timing array came out as a
        nonsense code: base64 decoding skips the colon and shifts the rest."""
        ir = _tuya_code([9000, 4500] + [560, 560, 560, 1690] * 16 + [560, 40000])
        pronto, timings, receipt, kind = decode_tuya_local_code("rf:" + ir)
        assert (pronto, timings, kind) == (None, [], RECEIPT_RF)
        assert "Tuya radio" in receipt
        assert decode_tuya_local_code(ir)[0] is not None

    async def test_it_counts_as_radio_and_lands_nothing(self, fake_hass, tmp_path):
        _write_store(tmp_path, TUYA_STORE, {"fan": {
            "on": "rf:" + _tuya_code([400, 800] * 30),
        }})
        _wire(fake_hass, tmp_path)
        fan = _remote(_store(await _list(fake_hass), TUYA_ID), "fan")
        assert (fan["ir_codes"], fan["rf_codes"]) == (0, 1)
        summary = _result(await _import(fake_hass, TUYA_ID, "fan"))
        assert (summary["signals"], summary["rf_receipted"]) == (0, 1)
