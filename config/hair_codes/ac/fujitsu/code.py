"""Fujitsu / General / O General air conditioners (ARRAH2E variant).

Covers what the O General AR-RCL1E remote and the Fujitsu AR-RAH2E,
AR-RAC1E, AR-RAE1E and AR-RCE1E remotes send. Timings, bit layout and
checksum here are the ones confirmed by real captures (see this project's
test suite).

.. warning::
   Only use this against a unit whose remote is known to be ARRAH2E
   compatible. A unit expecting a different Fujitsu variant (ARDB1, ARJW2,
   ARREB1E, ARRY4, ARREW4E) can lock up on an unexpected swing setting,
   recovering only via a physical power cycle. Those variants are not
   handled by this file.

THIS FILE IS THE TEMPLATE for adding a new company -- it's the simplest one.
Everything a company's code.py needs is right here: some constants, a
function that turns an ACState into raw timings, and a `Protocol` class with
one `encode()` method, ending in a `PROTOCOL = Protocol()` line.
"""

from __future__ import annotations

from infrared_protocols.core import ACState, FanSpeed, Mode, Packet, Swing

MIN_TEMP = 16
MAX_TEMP = 30
_TEMP_OFFSET = MIN_TEMP
_TEMP_STEP = 4  # the frame stores temperature in quarter-degrees

FREQUENCY_HZ = 38_000
# Not specified by any reference this was checked against -- unconfirmed.
DUTY_CYCLE = 0.5

HEADER_MARK_US = 3324
HEADER_SPACE_US = 1574
BIT_MARK_US = 448
ONE_SPACE_US = 1182
ZERO_SPACE_US = 390

_HEADER = [0x14, 0x63, 0x00, 0x10, 0x10]
_CMD_STATE = 0xFE
_CMD_TURN_OFF = 0x02
_PROTOCOL_VERSION = 0x30
_STATE_LENGTH = 16
_REST_LENGTH = _STATE_LENGTH - 7  # byte 6: bytes remaining after itself
_CHECKSUM_FROM = 7  # checksum covers bytes 7..14
_POWER_BIT = 0x01
_BYTE14 = 0x20  # unidentified, but fixed in every captured frame

_MODE_BITS = {
    Mode.AUTO: 0x0,
    Mode.COOL: 0x1,
    Mode.DRY: 0x2,
    Mode.FAN: 0x3,
    Mode.HEAT: 0x4,
}
_FAN_BITS = {
    FanSpeed.AUTO: 0x0,
    FanSpeed.HIGH: 0x1,
    FanSpeed.MEDIUM: 0x2,
    FanSpeed.LOW: 0x3,
    FanSpeed.QUIET: 0x4,
}
_SWING_BITS = {
    Swing.OFF: 0b00,
    Swing.VERTICAL: 0b01,
    Swing.HORIZONTAL: 0b10,
    Swing.BOTH: 0b11,
}


def _checksum(state_bytes: list[int]) -> int:
    return -sum(state_bytes[_CHECKSUM_FROM : _STATE_LENGTH - 1]) & 0xFF


def _build_state_bytes(state: ACState) -> list[int]:
    if not state.power:
        # Powering off is a short 7-byte frame carrying nothing else.
        return [*_HEADER, _CMD_TURN_OFF, ~_CMD_TURN_OFF & 0xFF]

    if not MIN_TEMP <= state.temperature <= MAX_TEMP:
        raise ValueError(f"temperature must be between {MIN_TEMP} and {MAX_TEMP} degC")

    temp_field = (state.temperature - _TEMP_OFFSET) * _TEMP_STEP
    state_bytes = [
        *_HEADER,
        _CMD_STATE,
        _REST_LENGTH,
        _PROTOCOL_VERSION,
        _POWER_BIT | (temp_field << 2),
        _MODE_BITS[state.mode],
        _FAN_BITS[state.fan] | (_SWING_BITS[state.swing] << 4),
        0x00,
        0x00,
        0x00,
        _BYTE14,
    ]
    state_bytes.append(_checksum(state_bytes))
    return state_bytes


def _timings_for(state_bytes: list[int]) -> list[int]:
    """Bytes go out least-significant-bit first."""
    timings = [HEADER_MARK_US, HEADER_SPACE_US]
    for byte in state_bytes:
        for i in range(8):
            timings.append(BIT_MARK_US)
            timings.append(ONE_SPACE_US if (byte >> i) & 1 else ZERO_SPACE_US)
    timings.append(BIT_MARK_US)
    return timings


class Protocol:
    """Turns an ACState into a Fujitsu ARRAH2E IR Packet."""

    name = "fujitsu"

    def encode(self, state: ACState) -> Packet:
        return Packet(_timings_for(_build_state_bytes(state)), FREQUENCY_HZ, DUTY_CYCLE)


PROTOCOL = Protocol()
