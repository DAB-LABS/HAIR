"""Adapter layer for parsing ESPHome IR events.

Isolates the rest of HAIR from the ESPHome ``ir_rf_proxy`` event format,
which is marked experimental and may change.  If the event payload
shape evolves, only this module needs updating.
"""
from __future__ import annotations

import hashlib
import logging
import math
from typing import Any

from .const import (
    DEFAULT_CARRIER_FREQUENCY,
    SIGNAL_RAW_FINGERPRINT_LEN,
    SIGNAL_RAW_QUANTIZE_BIN_US,
)
from .models import CaptureResult

_LOGGER = logging.getLogger(__name__)


class EventParser:
    """Parse ``esphome.remote_received`` events into ``CaptureResult``."""

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    @staticmethod
    def parse(event_data: dict[str, Any]) -> CaptureResult | None:
        """Convert raw event data to a ``CaptureResult``.

        Returns ``None`` if the event cannot be meaningfully parsed
        (e.g. empty payload).
        """
        if not event_data:
            return None

        protocol = event_data.get("protocol")
        code = event_data.get("code")
        raw = event_data.get("raw") or event_data.get("raw_timings") or []
        frequency = int(event_data.get("frequency", DEFAULT_CARRIER_FREQUENCY))
        confidence = float(event_data.get("confidence", 1.0))

        # Must have at least a decoded code or raw timings.
        if not code and not raw:
            return None

        return CaptureResult(
            protocol=str(protocol) if protocol else None,
            code=str(code) if code else None,
            raw_timings=list(raw),
            frequency=frequency,
            confidence=confidence,
        )

    @staticmethod
    def is_nec_repeat(event_data: dict[str, Any]) -> bool:
        """Return True if event is a NEC repeat frame (no new data).

        NEC remotes send the full code once, then flood short repeat
        frames while the button is held.  A repeat frame has no ``code``
        and very short raw timings (just the 9ms burst + 2.25ms space).
        """
        protocol = (event_data.get("protocol") or "").upper()
        if protocol != "NEC":
            return False
        # Repeat frame: protocol=NEC but no code/command, or explicit
        # repeat flag from ESPHome.
        if event_data.get("repeat", False):
            return True
        if not event_data.get("code") and not event_data.get("command"):
            raw = event_data.get("raw") or event_data.get("raw_timings") or []
            # A NEC repeat frame is ~4 pulses (9000, -2250, 560, -560).
            if len(raw) <= 6:
                return True
        return False

    @staticmethod
    def extract_device_address(
        protocol: str | None, code: str | None
    ) -> str | None:
        """Extract the device-address portion from a decoded protocol.

        Returns the address as a hex string, or ``None`` if the protocol
        is not recognised or the code cannot be parsed.

        Supported protocols and their code formats (from ESPHome):
        - NEC:     ``0xAACC`` (AA = address, CC = command)  -- 16-bit
                   ``0xAAAACCCC`` (extended NEC) -- 32-bit
        - Samsung: ``0xCCCC`` with separate ``address`` field, or
                   ``0xAACCCC`` -- first byte is custom code
        - Sony:    address is in upper bits of the code
        - RC5:     5-bit address in bits 10-6 of ``0x1ACC``
        - RC6:     similar to RC5
        """
        if not protocol or not code:
            return None

        proto_upper = protocol.upper()

        try:
            value = int(code, 0)  # auto-detect base (0x hex, etc.)
        except (ValueError, TypeError):
            return None

        if proto_upper == "NEC":
            if value <= 0xFFFF:
                # Standard NEC: upper byte is address.
                return f"0x{(value >> 8) & 0xFF:02X}"
            # Extended NEC (32-bit): upper 16 bits are address.
            return f"0x{(value >> 16) & 0xFFFF:04X}"

        if proto_upper == "SAMSUNG" or proto_upper == "SAMSUNG36":
            if value <= 0xFFFF:
                return f"0x{(value >> 8) & 0xFF:02X}"
            return f"0x{(value >> 16) & 0xFFFF:04X}"

        if proto_upper in ("SONY", "SIRC"):
            # Sony 12-bit: 7-bit command + 5-bit address.
            # Sony 15-bit: 7-bit command + 8-bit address.
            # Sony 20-bit: 7-bit command + 13-bit address.
            return f"0x{(value >> 7) & 0x1FFF:04X}"

        if proto_upper in ("RC5", "RC6"):
            # RC5: toggle(1) + address(5) + command(6) = 12 bits.
            return f"0x{(value >> 6) & 0x1F:02X}"

        return None

    @staticmethod
    def signal_fingerprint(
        protocol: str | None,
        code: str | None,
        raw_timings: list[int] | None,
    ) -> str:
        """Compute a stable fingerprint for a signal.

        For decoded protocols: ``hash(protocol + code)``.
        For raw-only: quantize timings to bins, truncate, and hash.
        """
        if protocol and code:
            payload = f"{protocol.upper()}:{code}"
            return hashlib.sha256(payload.encode()).hexdigest()[:16]

        return EventParser._raw_fingerprint(raw_timings or [])

    @staticmethod
    def device_fingerprint(
        protocol: str | None,
        device_address: str | None,
        raw_timings: list[int] | None,
    ) -> str:
        """Compute a grouping fingerprint for a device.

        For decoded protocols with an address: ``hash(protocol + address)``.
        Otherwise: use a coarsened raw timing hash (first 16 values only,
        to capture the preamble/header which is shared across all buttons
        on the same remote).
        """
        if protocol and device_address:
            payload = f"DEV:{protocol.upper()}:{device_address}"
            return hashlib.sha256(payload.encode()).hexdigest()[:16]

        # Fallback: hash just the preamble (first 16 timings).
        return EventParser._raw_fingerprint(
            (raw_timings or [])[:16], prefix="DEV"
        )

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _raw_fingerprint(
        timings: list[int],
        prefix: str = "RAW",
    ) -> str:
        """Quantize raw timings to bins and hash.

        1. Quantize to nearest ``SIGNAL_RAW_QUANTIZE_BIN_US`` (50 us).
        2. Truncate to first ``SIGNAL_RAW_FINGERPRINT_LEN`` (64) values.
        3. SHA-256, take first 16 hex chars.
        """
        bin_size = SIGNAL_RAW_QUANTIZE_BIN_US
        max_len = SIGNAL_RAW_FINGERPRINT_LEN

        quantized = []
        for t in timings[:max_len]:
            sign = 1 if t >= 0 else -1
            q = round(abs(t) / bin_size) * bin_size * sign
            quantized.append(q)

        payload = f"{prefix}:{quantized}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
