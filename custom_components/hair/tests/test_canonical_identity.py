"""One authoritative identity form: the wire Pronto (2026-08-17 ruling).

The bug this file guards against: a Pronto that came out of a FILE and
the same code coming back off a RECEIVER are different strings, because
``ProntoCommand`` strips the trailing space on the way to raw timings
(the 0.9.8 identity rule) and every capture is rebuilt through
``raw_to_pronto``. Identity hashed from file text therefore never
matched a real press -- measured at 121 of 943 closet flat signals and
23 of 272 wig-adopted device commands, all undecoded.

What must stay true:

- identity is computed on the canonical form, everywhere;
- canonicalization is idempotent, so the load-time backfill is a no-op
  from the second boot;
- the stored Pronto TEXT is never rewritten, so a wig's claim digests
  cannot move.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.event_parser import EventParser
from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_fingerprint,
    canonical_pronto,
)
from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
from custom_components.hair.models import IRCommand, IRDevice, IRTrigger
from custom_components.hair.tests.test_identity_tail_strip import (
    _legacy_byte_hash,
    _legacy_fingerprint,
)

# A code whose trailing word is a real inter-frame gap: the shape every
# AC frame and half the closet has.
FILED = "0000 006D 0002 0000 0020 0040 0020 09BC"
# One already in wire form.
WIRED = "0000 006D 0002 0000 0020 0040 0020 0000"


def _off_the_air(code: str) -> tuple[str, str | None]:
    """The (fingerprint, byte_hash) a receiver would hand HAIR."""
    command = ProntoCommand(code)
    raw = command.get_raw_timings()
    wire = raw_to_pronto(raw, frequency=command.modulation)
    return (
        EventParser.signal_fingerprint("PRONTO", wire, raw),
        EventParser.pronto_byte_hash(wire),
    )


def test_the_trailing_gap_really_does_move_the_identity():
    """The premise, and GH #125 inverted it on purpose.

    Until v0.12.1 this asserted the opposite: that the trailing gap word
    DID move the identity. That was true, and it was the whole reason
    the canonical form existed -- hash the file text and a real press
    could never match it. The unified strip took the tail out of both
    hash walks, so the file's gap word, a receiver's own silence and
    ``raw_to_pronto``'s padded zero now hash identically and the
    divergence is gone at the source rather than worked around.

    Kept rather than deleted, because it is still the first assertion
    that fails if the strip is ever removed. The old behaviour is
    asserted underneath, against the pre-strip walk, so the history is
    not just a docstring claim.
    """
    naive_fp = EventParser.signal_fingerprint("PRONTO", FILED, None)
    naive_hash = EventParser.pronto_byte_hash(FILED)
    heard_fp, heard_hash = _off_the_air(FILED)

    assert naive_fp == heard_fp
    assert naive_hash == heard_hash

    # And it really did move before: the pre-strip walk still says so.
    assert _legacy_byte_hash(FILED) != _legacy_byte_hash(canonical_pronto(FILED))
    assert _legacy_fingerprint(FILED) != _legacy_fingerprint(
        canonical_pronto(FILED)
    )


def test_canonical_identity_matches_what_comes_off_the_air():
    heard_fp, heard_hash = _off_the_air(FILED)

    assert canonical_fingerprint("PRONTO", FILED, None) == heard_fp
    assert canonical_byte_hash(FILED) == heard_hash


def test_canonicalization_is_idempotent():
    once = canonical_pronto(FILED)
    assert once is not None
    assert canonical_pronto(once) == once
    assert canonical_fingerprint("PRONTO", once, None) == (
        canonical_fingerprint("PRONTO", FILED, None)
    )


def test_a_wire_form_code_is_left_alone():
    assert canonical_fingerprint("PRONTO", WIRED, None) == (
        EventParser.signal_fingerprint("PRONTO", WIRED, None)
    )


def test_non_pronto_protocols_pass_straight_through():
    assert canonical_fingerprint("NEC", "0x20DF10EF", None) == (
        EventParser.signal_fingerprint("NEC", "0x20DF10EF", None)
    )


def test_an_unreadable_code_degrades_to_the_old_answer():
    assert canonical_pronto("not a pronto code") is None
    assert canonical_fingerprint("PRONTO", "not a pronto code", None) == (
        EventParser.signal_fingerprint("PRONTO", "not a pronto code", None)
    )
    assert canonical_pronto(None) is None


def test_wig_signal_identity_hashes_the_wire_form_but_keeps_the_text():
    """The mint doors read this helper, so this is where the fix lands
    for adopt, USE-as-a-Remote, fitting and direct-to-device at once."""
    from custom_components.hair.wig_identity import wig_signal_identity

    identity = wig_signal_identity(FILED)
    heard_fp, heard_hash = _off_the_air(FILED)

    assert identity is not None
    assert identity.fingerprint == heard_fp
    assert identity.byte_hash == heard_hash
    # The code a caller stores, and a person reads, is unchanged.
    assert identity.pronto.split() == FILED.split()


def test_claim_digests_do_not_move():
    """The reason the stored text is never rewritten: a wig's claims
    bind the code as written, and every signed fitting depends on it."""
    from custom_components.hair.wig_format import row_digest

    before = row_digest(FILED, 0, False)
    canonical_fingerprint("PRONTO", FILED, None)
    canonical_byte_hash(FILED)
    assert row_digest(FILED, 0, False) == before
    # And the wire text would hash differently, which is exactly why.
    assert row_digest(canonical_pronto(FILED), 0, False) != before


# ---------------------------------------------------------------------------
# The load-time backfill
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backfill_repoints_stored_commands_and_triggers(hass_store):
    """A pre-0.12.1 store, moved onto the wire form on the first load.

    Seeded with WIRED and its PRE-STRIP hash, which is what an install
    upgrading into this release actually carries. Note the code: FILED
    ends on a real inter-frame gap, and the gap break already excluded
    that word, so a gap-tailed row is one of the twelve-in-853 whose
    identity GH #125 does not move. It would seed nothing stale and the
    test would pass vacuously. The zero tail is the class that moves,
    and it is 838 of the 853.
    """
    store = hass_store
    heard_fp, heard_hash = _off_the_air(WIRED)
    stale_hash = _legacy_byte_hash(WIRED)
    stale_fp = _legacy_fingerprint(WIRED)
    assert stale_hash != heard_hash
    assert stale_fp != heard_fp

    device = IRDevice(id="dev-1", name="Adopted")
    device.commands = [
        IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=WIRED,
            byte_hash=stale_hash,
        )
    ]
    store._data = {"dev-1": device}
    store._triggers = {
        "t1": IRTrigger(
            id="t1", name="Power", protocol="PRONTO", code=WIRED,
            signal_fingerprint=stale_fp,
            byte_hash=stale_hash,
        )
    }

    assert store._backfill_canonical_identity() is True
    assert device.commands[0].byte_hash == heard_hash
    assert store._triggers["t1"].byte_hash == heard_hash
    assert store._triggers["t1"].signal_fingerprint == heard_fp
    # The stored code text is untouched.
    assert device.commands[0].code == WIRED
    assert store._triggers["t1"].code == WIRED
    # Idempotent: a second boot changes nothing.
    assert store._backfill_canonical_identity() is False


@pytest.mark.asyncio
async def test_backfill_makes_the_matcher_recognize_a_real_press(hass_store):
    """The bench case, in a test: a wig-adopted undecoded command is
    found by ``match_command`` when the handset is actually pressed."""
    store = hass_store
    heard_fp, heard_hash = _off_the_air(FILED)

    device = IRDevice(id="dev-1", name="Adopted")
    device.commands = [
        IRCommand(
            id="c1", name="Power", protocol="PRONTO", code=FILED,
            byte_hash=EventParser.pronto_byte_hash(FILED),
        )
    ]
    store._data = {"dev-1": device}
    store._triggers = {}

    store._backfill_canonical_identity()
    store._rebuild_command_index()

    assert store.match_command(None, heard_fp, heard_hash) == ("dev-1", "c1")


def test_catalog_rows_are_repointed_at_load():
    """Clipper and Plucker rows, hashed from the code as pasted.

    Zero-tailed and seeded pre-strip, for the reason given on the
    command backfill above: the row has to be genuinely stale for the
    migration to have work to do.
    """
    from custom_components.hair.models import UnknownDevice, UnknownSignal
    from custom_components.hair.signal_store import _transform_loaded

    heard_fp, heard_hash = _off_the_air(WIRED)
    device = UnknownDevice(label="Clipped")
    device.signals = [
        UnknownSignal(
            id="s1", protocol="PRONTO", code=WIRED,
            fingerprint=_legacy_fingerprint(WIRED),
            byte_hash=_legacy_byte_hash(WIRED),
        )
    ]
    raw = {"devices": [device.to_dict()], "dismissed": []}

    devices, _dismissed, dirty = _transform_loaded(raw)

    signal = next(iter(devices.values())).signals[0]
    assert signal.fingerprint == heard_fp
    assert signal.byte_hash == heard_hash
    assert signal.code == WIRED
    assert dirty is True
@pytest.fixture
def hass_store():
    from custom_components.hair.storage import HAIRStore

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    store = HAIRStore(hass)
    store._data = {}
    store._triggers = {}
    store._trigger_remotes = {}
    return store
