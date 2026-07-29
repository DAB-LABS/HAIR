"""RF receiver detection for the infrared platform (GH #72).

Combined RF/IR hardware (Athom's RF IR Remote and other ESPHome
``ir_rf_proxy`` builds) can expose its RF receivers as ``infrared``
platform receiver entities. HAIR subscribes to every receiver in the
domain, so an RF receiver feeds ambient radio chatter straight into
the unknown-signal store: the GH #72 install accumulated 104k
undecodable signals and 500 phantom remotes in 33 hours that way.
HAIR captures IR only; RF support is roadmapped as an explicit opt-in.

Discriminator (verified against HA 2026.7.2 core source, 2026-07-29):
there is no honest attribute. Core ``InfraredReceiverEntity`` exposes
only ``device_class: receiver`` and a timestamp state; the ESPHome
integration receives ``InfraredInfo.receiver_frequency`` from the
device but drops it (no state attribute, no registry capability). That
leaves registry naming, per the ir_rf_proxy convention where the
firmware's object ids (``ir_proxy_receiver`` / ``rf_proxy_receiver``)
land verbatim in the ESPHome unique_id (``<mac>-infrared-<object_id>``).

Matching rules, chosen against real false-positive traps:

- Only the registry ``unique_id`` and ``original_name`` are consulted.
  Both are integration-assigned and survive renames. The entity_id and
  friendly name are user-editable AND poisoned by device names: the
  test bench's IR receiver is friendly-named "Athom RF IR Remote 1 IR
  Proxy Receiver", so any name-based match would disable the exact
  hardware this guard protects.
- A field reads as RF when it carries an ``rf`` token WITHOUT an
  ``ir`` token. A field claiming both (hypothetical combined
  ``rf_ir_receiver``) keeps its subscription: it claims IR, and a
  wrongly-dropped IR receiver is a silent capture outage while a
  wrongly-kept RF receiver is now only cap-bounded noise.
- The ``infrared`` domain marker present in every ESPHome unique_id is
  NOT an IR claim; only a bare ``ir`` token is, otherwise nothing
  could ever read as RF.
"""
from __future__ import annotations

import re

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


def _reads_as_rf(field: str | None) -> bool:
    # isinstance rather than truthiness: registry stubs in tests (and
    # any misbehaving integration) may carry non-string fields, which
    # must read as "no claim", never as an error.
    if not isinstance(field, str) or not field:
        return False
    tokens = set(_TOKEN_SPLIT.split(field.lower()))
    return "rf" in tokens and "ir" not in tokens


@callback
def is_rf_receiver(hass: HomeAssistant, entity_id: str) -> bool:
    """Return True when a receiver entity reads as RF-only.

    Unknown entities and registry lookup failures return False: the
    guard must never cost a genuine IR receiver its subscription, and
    an RF receiver that slips through is bounded by the signal caps.
    """
    try:
        entry = er.async_get(hass).async_get(entity_id)
    except Exception:  # registry not ready / test stub
        return False
    if entry is None:
        return False
    return _reads_as_rf(entry.unique_id) or _reads_as_rf(
        entry.original_name
    )


@callback
def partition_receivers(
    hass: HomeAssistant, entity_ids: list[str]
) -> tuple[list[str], list[str]]:
    """Split receiver entity ids into ``(ir_ids, rf_ids)``, order kept."""
    ir_ids: list[str] = []
    rf_ids: list[str] = []
    for entity_id in entity_ids:
        (rf_ids if is_rf_receiver(hass, entity_id) else ir_ids).append(
            entity_id
        )
    return ir_ids, rf_ids
