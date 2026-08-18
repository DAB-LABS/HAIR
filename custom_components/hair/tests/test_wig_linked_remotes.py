"""Tests for _wig_linked_remotes (signpost 3, Track 2 item 4).

The remote-side sibling of test_wig_adopt.py's TestLinkedDevices /
TestAMatrixWigLinksByItsStoredPointer / TestPointerWinsOverIdentity --
same fixtures, same shape, TriggerRemote.source_wig_id standing in for
IRDevice.source_wig_id.
"""
from __future__ import annotations

from custom_components.hair.identity import SignalIdentity
from custom_components.hair.models import TriggerRemote
from custom_components.hair.websocket_api import _wig_linked_remotes
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
)
from custom_components.hair.wig_identity import wig_signal_identities

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


def _index_for(pronto: str, remote_id: str, remote_name: str):
    ident = wig_signal_identities(_wig([pronto]))[0]
    assert ident is not None
    return (
        SignalIdentity(
            ident.decoded_fingerprint, ident.byte_hash, ident.fingerprint
        ),
        {"remote_id": remote_id, "remote_name": remote_name},
    )


class TestLinkedRemotes:
    def test_zero(self):
        wig = Wig(name="W", signals=[])
        assert _wig_linked_remotes(wig, []) == []

    def test_one(self):
        wig = Wig(name="W", signals=[WigSignal(alias="S0", pronto=PRONTO_A)])
        index = [_index_for(PRONTO_A, "tr1", "Living Room Remote")]
        linked = _wig_linked_remotes(wig, index)
        assert linked == [
            {"remote_id": "tr1", "remote_name": "Living Room Remote"}
        ]

    def test_no_duplicate_chips_for_multi_signal_match(self):
        wig = Wig(
            name="W",
            signals=[
                WigSignal(alias="S0", pronto=PRONTO_A),
                WigSignal(alias="S1", pronto=PRONTO_A),
            ],
        )
        index = [_index_for(PRONTO_A, "tr1", "Living Room Remote")]
        assert len(_wig_linked_remotes(wig, index)) == 1


class TestAMatrixWigLinksByItsStoredPointer:
    """Mirrors test_wig_adopt.py's device-side fixture exactly: a
    matrix wig has no flat signals, so a remote made from one (its
    depth-0 extras aside) may have nothing to identity-match with --
    the stored pointer is what lets it still chip."""

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
    def _remote(remote_id: str, name: str, source: str | None) -> TriggerRemote:
        return TriggerRemote(id=remote_id, name=name, source_wig_id=source)

    def test_a_matrix_wig_finds_the_remote_it_was_made_from(self):
        wig = self._matrix_wig("wig-1")
        remotes = [self._remote("tr1", "Samsung AC Remote", "wig-1")]
        assert _wig_linked_remotes(wig, [], remotes) == [
            {"remote_id": "tr1", "remote_name": "Samsung AC Remote"}
        ]

    def test_an_unmade_matrix_wig_still_links_to_nothing(self):
        wig = self._matrix_wig("wig-1")
        remotes = [self._remote("tr1", "Someone else", "wig-2")]
        assert _wig_linked_remotes(wig, [], remotes) == []

    def test_a_wig_with_no_id_cannot_be_pointed_at(self):
        wig = self._matrix_wig(None)
        remotes = [self._remote("tr1", "Sniffed", None)]
        assert _wig_linked_remotes(wig, [], remotes) == []

    def test_many_remotes_from_one_matrix_wig(self):
        wig = self._matrix_wig("wig-1")
        remotes = [
            self._remote("tr1", "Living Room", "wig-1"),
            self._remote("tr2", "Bedroom", "wig-1"),
        ]
        linked = _wig_linked_remotes(wig, [], remotes)
        assert {e["remote_id"] for e in linked} == {"tr1", "tr2"}

    def test_the_two_paths_union_rather_than_shadow(self):
        wig = Wig(
            name="W", wig_id="wig-1",
            signals=[WigSignal(alias="S0", pronto=PRONTO_A)],
        )
        index = [_index_for(PRONTO_A, "tr2", "Bedroom")]
        remotes = [self._remote("tr1", "Living Room", "wig-1")]
        linked = _wig_linked_remotes(wig, index, remotes)
        assert {e["remote_id"] for e in linked} == {"tr1", "tr2"}


class TestPointerWinsOverIdentity:
    """Mirrors test_wig_adopt.py's device-side punch-list item 7
    exactly: a remote with a stored source_wig_id chips ONLY the wig
    it points to."""

    def test_a_pointed_remote_does_not_chip_a_different_wig_by_identity(
        self,
    ):
        other_wig = Wig(
            name="Other", wig_id="wig-2",
            signals=[WigSignal(alias="S0", pronto=PRONTO_A)],
        )
        index = [_index_for(PRONTO_A, "tr1", "Living Room")]
        remotes = [
            TriggerRemote(id="tr1", name="Living Room", source_wig_id="wig-1")
        ]
        assert _wig_linked_remotes(other_wig, index, remotes) == []

    def test_a_pointed_remote_still_chips_its_own_wig(self):
        wig = Wig(name="W", wig_id="wig-1", signals=[])
        remotes = [
            TriggerRemote(id="tr1", name="Living Room", source_wig_id="wig-1")
        ]
        assert _wig_linked_remotes(wig, [], remotes) == [
            {"remote_id": "tr1", "remote_name": "Living Room"}
        ]

    def test_an_unpointed_remote_still_chips_by_identity(self):
        wig = Wig(
            name="W", wig_id="wig-2",
            signals=[WigSignal(alias="S0", pronto=PRONTO_A)],
        )
        index = [_index_for(PRONTO_A, "tr2", "Bedroom")]
        remotes = [
            TriggerRemote(id="tr2", name="Bedroom", source_wig_id=None)
        ]
        assert _wig_linked_remotes(wig, index, remotes) == [
            {"remote_id": "tr2", "remote_name": "Bedroom"}
        ]

    def test_a_pointed_remote_and_an_unpointed_remote_both_evaluated(self):
        wig = Wig(
            name="W", wig_id="wig-2",
            signals=[WigSignal(alias="S0", pronto=PRONTO_A)],
        )
        index = [
            _index_for(PRONTO_A, "tr1", "Living Room"),
            _index_for(PRONTO_A, "tr2", "Bedroom"),
        ]
        remotes = [
            TriggerRemote(id="tr1", name="Living Room", source_wig_id="wig-1"),
            TriggerRemote(id="tr2", name="Bedroom", source_wig_id=None),
        ]
        linked = _wig_linked_remotes(wig, index, remotes)
        assert linked == [{"remote_id": "tr2", "remote_name": "Bedroom"}]
