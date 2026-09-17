"""Which CI leg is running, for the handful of tests that must care.

HAIR runs its suite twice: once with ``infrared_protocols`` installed
and once without. Most tests do not notice, because the local decoders
in this package serve both ways. The strict NEC decoder is the
exception: it has no local polyfill, so on the bare leg the ``nec`` spec
is not registered at all and nothing decodes a 32-bit NEC frame.

That matters to the protocol pack in two places, and both are stated
here rather than re-derived in five modules:

- Assertions of the form "this frame decodes as NEC" are assertions
  about the library, not about the pack. On the bare leg the same frame
  is correctly unclaimed. What the pack promises on BOTH legs is the
  negative: an Apple gate refuses it, and no capture ever mints
  ``PIONEER``.
- The no-steal census is leg-dependent for the same reason, so there is
  a baseline per leg and each test reads the one matching where it runs.
  A single baseline would have made the census vacuous on the bare leg,
  where every NEC row is unclaimed and there is nothing left to protect.
"""
from __future__ import annotations

from custom_components.hair.protocol_decode import get_spec


def strict_nec_available() -> bool:
    """Is a strict NEC decoder registered in this environment?

    Computed from the live registry rather than from an import probe:
    what matters is whether the spec resolved, which is the thing every
    caller here actually depends on.
    """
    return get_spec("NEC") is not None


#: The suffix the census baseline for this leg carries.
BASELINE_SUFFIX = "" if strict_nec_available() else "-nolib"
