"""Tests for Adopt Device (v0.8.1) and its riders.

Covers the wig-side linked-device matcher (zero / one / many, and the
stored pointer a matrix wig depends on), the content-hash identity
cache, and the SmartIR Base64 padding salvage.
"""
from __future__ import annotations

from custom_components.hair.identity import SignalIdentity
from custom_components.hair.models import IRDevice
from custom_components.hair.websocket_api import _wig_linked_devices
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
)
from custom_components.hair.wig_identity import (
    _IDENTITY_CACHE,
    wig_signal_identities,
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0040 0020 0040 0020"


def _wig(prontos: list[str]) -> Wig:
    return Wig(
        name="W",
        signals=[
            WigSignal(alias=f"S{i}", pronto=p)
            for i, p in enumerate(prontos)
        ],
    )


def _index_for(pronto: str, device_id: str, device_name: str):
    """Assignment-index entry matching ``pronto`` by identity."""
    ident = wig_signal_identities(_wig([pronto]))[0]
    assert ident is not None
    return (
        SignalIdentity(
            ident.decoded_fingerprint, ident.byte_hash, ident.fingerprint
        ),
        {"device_id": device_id, "device_name": device_name,
         "command_id": "c", "command_name": "Cmd"},
    )


class TestLinkedDevices:
    def test_zero(self):
        wig = _wig([PRONTO_A])
        assert _wig_linked_devices(wig, []) == []

    def test_one(self):
        wig = _wig([PRONTO_A, PRONTO_B])
        index = [_index_for(PRONTO_A, "d1", "Living Room")]
        linked = _wig_linked_devices(wig, index)
        assert linked == [
            {"device_id": "d1", "device_name": "Living Room"}
        ]

    def test_many_devices_one_wig(self):
        """Adopt twice (living room + bedroom): both chip up."""
        wig = _wig([PRONTO_A])
        index = [
            _index_for(PRONTO_A, "d1", "Living Room"),
            _index_for(PRONTO_A, "d2", "Bedroom"),
        ]
        linked = _wig_linked_devices(wig, index)
        assert {entry["device_id"] for entry in linked} == {"d1", "d2"}

    def test_no_duplicate_chips_for_multi_signal_match(self):
        wig = _wig([PRONTO_A, PRONTO_A])
        index = [_index_for(PRONTO_A, "d1", "Living Room")]
        assert len(_wig_linked_devices(wig, index)) == 1


class TestIdentityCache:
    def test_cache_hit_by_content_hash(self):
        _IDENTITY_CACHE.clear()
        wig = _wig([PRONTO_A])
        first = wig_signal_identities(wig)
        # Same signals in a DIFFERENT Wig object: cache must hit.
        again = wig_signal_identities(_wig([PRONTO_A]))
        assert again is first
        assert len(_IDENTITY_CACHE) == 1

    def test_invalid_pronto_yields_none_entry(self):
        _IDENTITY_CACHE.clear()
        wig = Wig(name="W", signals=[
            WigSignal(alias="Bad", pronto="not pronto"),
        ])
        # Bypass parse-time validation (hand-built Wig): the helper
        # must degrade to None, never raise.
        assert wig_signal_identities(wig) == [None]


class TestPaddingSalvage:
    def test_unpadded_base64_converts(self):
        """SmartIR census rider: valid packet, stripped '=' padding."""
        import base64

        from custom_components.hair.wig_adapters import (
            _broadlink_b64_to_pronto,
        )

        # A minimal Broadlink IR packet: type 0x26, repeat 0, length,
        # a plausible pulse train. 14 bytes total so the Base64 form
        # genuinely carries "=" padding to strip.
        pulses = bytes([0x26, 0x00, 0x0A, 0x00,
                        0x12, 0x24, 0x12, 0x12, 0x12, 0x24, 0x12, 0x12,
                        0x12, 0x24])
        b64 = base64.b64encode(pulses).decode()
        assert _broadlink_b64_to_pronto(b64) is not None
        stripped = b64.rstrip("=")
        assert stripped != b64  # the case under test
        assert _broadlink_b64_to_pronto(stripped) is not None

    def test_garbage_still_fails(self):
        from custom_components.hair.wig_adapters import (
            _broadlink_b64_to_pronto,
        )

        assert _broadlink_b64_to_pronto("!!!not base64!!!") is None


class TestAMatrixWigLinksByItsStoredPointer:
    """A matrix wig has NO FLAT SIGNALS. Its codes are lattice cells,
    and cells are not commands, so neither side of the identity match
    has anything to compare: the Samsung on the bench carries 0 signals
    and 750 cells.

    Every matrix wig therefore read as adopted by nobody, forever. The
    closet's linked chip stayed dark, the adopt popover never appeared,
    and the comb report went on offering ADOPT to a wig already sitting
    on a device (bench 2026-08-03).

    IRDevice.source_wig_id is the wig's UUID, written at adopt and never
    by hand. It is exact, already stored, and costs one comparison per
    device -- against deriving an identity for several hundred cells on
    both sides of a pairwise scan, on a call that runs every time the
    closet lists.
    """

    @staticmethod
    def _matrix_wig(wig_id: str | None) -> Wig:
        return Wig(
            name="AC",
            signals=[],
            wig_id=wig_id,
            climate=ClimateMatrix(
                min_temp=16,
                max_temp=30,
                off=PRONTO_A,
                cells=[ClimateCell(mode="cool", pronto=PRONTO_B, temp=20)],
            ),
        )

    @staticmethod
    def _device(device_id: str, name: str, source: str | None) -> IRDevice:
        return IRDevice(
            id=device_id, name=name, device_type="ac",
            source_wig_id=source,
        )

    def test_a_matrix_wig_finds_the_device_it_was_adopted_into(self):
        wig = self._matrix_wig("wig-1")
        devices = [self._device("d1", "Samsung AC", "wig-1")]
        assert _wig_linked_devices(wig, [], devices) == [
            {"device_id": "d1", "device_name": "Samsung AC"}
        ]

    def test_an_unadopted_matrix_wig_still_links_to_nothing(self):
        """The bug was that EVERY matrix wig read as unadopted. The fix
        must not make every matrix wig read as adopted."""
        wig = self._matrix_wig("wig-1")
        devices = [self._device("d1", "Someone else", "wig-2")]
        assert _wig_linked_devices(wig, [], devices) == []

    def test_a_wig_with_no_id_cannot_be_pointed_at(self):
        """Files written before v0.9.5 have no wig_id. A None on both
        sides must not match everything to everything."""
        wig = self._matrix_wig(None)
        devices = [self._device("d1", "Sniffed", None)]
        assert _wig_linked_devices(wig, [], devices) == []

    def test_many_devices_from_one_matrix_wig(self):
        """Adopt the lattice twice and both chip up, the same way the
        identity path already allows."""
        wig = self._matrix_wig("wig-1")
        devices = [
            self._device("d1", "Living Room", "wig-1"),
            self._device("d2", "Bedroom", "wig-1"),
        ]
        linked = _wig_linked_devices(wig, [], devices)
        assert {e["device_id"] for e in linked} == {"d1", "d2"}

    def test_the_two_paths_union_rather_than_shadow(self):
        """A flat wig adopted once and matched by identity somewhere
        else should report both, not whichever ran first."""
        wig = Wig(
            name="W",
            wig_id="wig-1",
            signals=[WigSignal(alias="S0", pronto=PRONTO_A)],
        )
        index = [_index_for(PRONTO_A, "d2", "Bedroom")]
        devices = [self._device("d1", "Living Room", "wig-1")]
        linked = _wig_linked_devices(wig, index, devices)
        assert {e["device_id"] for e in linked} == {"d1", "d2"}

    def test_the_old_signature_still_works(self):
        """hair_devices is optional, so every existing caller that
        passes two arguments keeps its identity-only behaviour."""
        wig = Wig(name="W", signals=[WigSignal(alias="S0", pronto=PRONTO_A)])
        index = [_index_for(PRONTO_A, "d1", "Living Room")]
        assert _wig_linked_devices(wig, index) == [
            {"device_id": "d1", "device_name": "Living Room"}
        ]
