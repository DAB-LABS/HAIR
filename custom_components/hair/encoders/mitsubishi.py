"""Mitsubishi: the 16-bit format of Mitsubishi televisions and VCRs.

The IRP definition, from IrpProtocols.xml (the protocol database the
JP1 and DecodeIR community maintains), read for its facts only::

    {32.6k,300}<1,-3|1,-7>(D:8,F:8,1,-80)* [D:0..127,F:0..255]

- 32.6 kHz carrier and a 300 us unit.
- Pulse distance, least significant bit first: a 1-unit mark, then a
  3-unit space for 0 or a 7-unit space for 1.
- No leader: D in 8 bits, F in 8 bits, a closing mark, and an 80-unit
  (24 ms) lead-out.
- A held button repeats the whole frame. There is no checksum, which is
  why HAIR has no decoder for it (see the package docstring).

D is sent in 8 bits but defined only up to 127, so a larger D is
refused rather than sent.
"""
from __future__ import annotations

from typing import override

from ..decoders._base import Command
from . import bits_lsb, check_range, pulse_distance

_UNIT_US = 300
_MARK_US = _UNIT_US
_ZERO_US = 3 * _UNIT_US
_ONE_US = 7 * _UNIT_US
_LEADOUT_US = 80 * _UNIT_US
_MODULATION_HZ = 32600


class MitsubishiCommand(Command):
    """Mitsubishi IR command, encode only."""

    device: int
    function: int

    def __init__(
        self,
        *,
        device: int,
        function: int,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the command.

        :param device: D, 0 to 127
        :param function: F, 0 to 255
        """
        check_range("device", device, 127)
        check_range("function", function, 0xFF)
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.device = device
        self.function = function

    @override
    def get_raw_timings(self) -> list[int]:
        """One frame, and the frame again for each repeat."""
        bits = bits_lsb(self.device, 8) + bits_lsb(self.function, 8)
        frame = pulse_distance(bits, _MARK_US, _ZERO_US, _ONE_US)
        frame += [_MARK_US, -_LEADOUT_US]
        return frame * (1 + self.repeat_count)
