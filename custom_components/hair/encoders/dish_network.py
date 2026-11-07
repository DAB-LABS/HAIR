"""Dish Network: the IR format of Dish Network satellite receivers.

The IRP definition, from IrpProtocols.xml (the protocol database the
JP1 and DecodeIR community maintains), read for its facts only::

    {57.6k,406}<1,-7|1,-4>(1,-15,(F:-6,S:5,D:5,1,-15)+) [F:0..63,S:0..31,D:0..31]

- 57.6 kHz carrier and a 406 us unit.
- Pulse distance with the long space meaning 0: a 1-unit mark, then a
  7-unit space for 0 or a 4-unit space for 1.
- A 1-unit mark and a 15-unit space lead in, once. Then the frame: F in
  6 bits most significant first (the ``-6`` reverses IRP's default
  order), S in 5 bits and D in 5 bits least significant first, a
  closing mark and a 15-unit lead-out.
- The frame is sent at least once (``+``) and again while the button is
  held, so a repeat here is the frame again without the lead-in.
"""
from __future__ import annotations

from typing import override

from ..decoders._base import Command
from . import bits_lsb, bits_msb, check_range, pulse_distance

_UNIT_US = 406
_MARK_US = _UNIT_US
_ZERO_US = 7 * _UNIT_US
_ONE_US = 4 * _UNIT_US
_GAP_US = 15 * _UNIT_US
_MODULATION_HZ = 57600


class DishNetworkCommand(Command):
    """Dish Network IR command, encode only."""

    device: int
    subdevice: int
    function: int

    def __init__(
        self,
        *,
        device: int,
        subdevice: int,
        function: int,
        modulation: int = _MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the command.

        :param device: D, 0 to 31
        :param subdevice: S, 0 to 31
        :param function: F, 0 to 63
        """
        check_range("device", device, 31)
        check_range("subdevice", subdevice, 31)
        check_range("function", function, 63)
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.device = device
        self.subdevice = subdevice
        self.function = function

    @override
    def get_raw_timings(self) -> list[int]:
        """The lead-in, the frame, then the frame again for each repeat."""
        bits = [
            *bits_msb(self.function, 6),
            *bits_lsb(self.subdevice, 5),
            *bits_lsb(self.device, 5),
        ]
        frame = pulse_distance(bits, _MARK_US, _ZERO_US, _ONE_US)
        frame += [_MARK_US, -_GAP_US]
        return [_MARK_US, -_GAP_US] + frame * (1 + self.repeat_count)
