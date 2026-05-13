# Toupee v1 Schematic Net List

Every electrical net in the Toupee with each connected pin. Use this as the source of truth when capturing the schematic.

## Component inventory

| Ref | Part | Description |
|---|---|---|
| U1 | ME6211C33M5G | 3.3V LDO |
| U2 | TSMP58000 | IR receiver |
| U3 | WS2812B | RGB status LED |
| Q1 | AO3400 | TX MOSFET |
| D1 | IR15-21C class | North IR LED (side firing 940 nm) |
| D2 | IR15-21C class | East IR LED |
| D3 | IR15-21C class | West IR LED |
| R1 | 18 ohm 0805 | D1 current limit |
| R2 | 18 ohm 0805 | D2 current limit |
| R3 | 18 ohm 0805 | D3 current limit |
| R6 | 100 ohm 0603 | TSMP supply isolation series |
| R7 | 1k 0603 | MOSFET gate series |
| R8 | 10k 0603 | MOSFET gate pulldown |
| R9 | 47k 0603 | TSMP output pullup |
| C1 | 100 uF polymer | 5V bulk near LED ring |
| C2 | 1 uF 0603 | LDO input |
| C3 | 1 uF 0603 | LDO output |
| C5 | 4.7 uF 0805 | TSMP supply post RC |
| C6 | 100 nF 0402 | TSMP HF bypass |
| C8 | 100 nF 0402 | WS2812B local decoupling |
| J1 | 1x5 pin header | Host connection |

Note: C4 and C7 are reserved for future use (alignment with HAIR puck numbering convention; not populated on v1).

## Power and ground nets

### Net: VBUS_5V

5V rail from the host through pin 1 of J1.

| Connection | Pin |
|---|---|
| J1 | Pin 1 (5V) |
| C1 | + |
| C2 | + (LDO input cap) |
| U1 | Pin 1 (VIN) |
| R1 | Pin 1 (anode side of D1) |
| R2 | Pin 1 (anode side of D2) |
| R3 | Pin 1 (anode side of D3) |
| U3 | VDD (pin 4 typical for WS2812B 5050) |

### Net: VCC_3V3

LDO output rail. Powers only the receiver supply chain and its pullup.

| Connection | Pin |
|---|---|
| U1 | Pin 5 (VOUT) |
| C3 | + (LDO output cap) |
| R6 | Pin 1 (input side of TSMP supply isolation) |
| R9 | Pin 1 (top of TSMP output pullup) |

### Net: VCC_3V3_RX

Filtered 3.3V to the TSMP58000 supply pin only.

| Connection | Pin |
|---|---|
| R6 | Pin 2 (output of isolation R) |
| C5 | + |
| C6 | + |
| U2 | Pin 3 (VS) |

### Net: GND

Ground, common to all blocks.

| Connection | Pin |
|---|---|
| J1 | Pin 2 (GND) |
| U1 | Pin 2 (GND) |
| U2 | Pin 2 (GND) |
| U3 | GND (pin 3 typical for WS2812B 5050) |
| Q1 | Pin 2 (source) |
| C1 | Negative |
| C2 | Negative |
| C3 | Negative |
| C5 | Negative |
| C6 | Negative |
| C8 | Negative |
| R8 | Pin 2 (gate pulldown to GND) |

## Host signal nets

### Net: TX_IN

Host GPIO driving the MOSFET gate, entering through header pin 3.

| Connection | Pin |
|---|---|
| J1 | Pin 3 (TX_IN) |
| R7 | Pin 1 |

### Net: TX_GATE

MOSFET gate node, between gate series resistor and pulldown.

| Connection | Pin |
|---|---|
| R7 | Pin 2 |
| R8 | Pin 1 |
| Q1 | Pin 1 (gate) |

### Net: IR_LED_CATHODE_BUS

Common cathode bus from the three IR LEDs to the MOSFET drain.

| Connection | Pin |
|---|---|
| D1 | Cathode |
| D2 | Cathode |
| D3 | Cathode |
| Q1 | Pin 3 (drain) |

### Per LED anode nets

| Net | Connections |
|---|---|
| D1_ANODE | R1 pin 2, D1 anode |
| D2_ANODE | R2 pin 2, D2 anode |
| D3_ANODE | R3 pin 2, D3 anode |

(R1 to R3 pin 1 are on VBUS_5V.)

### Net: RX_OUT

TSMP receiver output to host through header pin 4.

| Connection | Pin |
|---|---|
| U2 | Pin 1 (OUT) |
| R9 | Pin 2 |
| J1 | Pin 4 (RX_OUT) |

### Net: LED_DIN

Host GPIO driving the WS2812B data input through header pin 5.

| Connection | Pin |
|---|---|
| J1 | Pin 5 (LED_DIN) |
| U3 | DIN (pin 2 typical for WS2812B 5050) |
| C8 | + (local decoupling reference, see note) |

Note: C8 is the WS2812B's VDD decoupling cap, not on the data line. It physically sits next to U3 between VDD and GND. Listed here only because it shares physical placement with the data line routing.

### Net: WS2812_DOUT

WS2812B data out, unused on this board.

| Connection | Pin |
|---|---|
| U3 | DOUT (pin 1 typical for WS2812B 5050) |
| (leave floating) | |

## Summary

Total nets: 11

| Category | Net count |
|---|---|
| Power and ground | 4 (VBUS_5V, VCC_3V3, VCC_3V3_RX, GND) |
| IR TX | 5 (TX_IN, TX_GATE, IR_LED_CATHODE_BUS, 3x anode nets) |
| IR RX | 1 (RX_OUT) |
| Status LED | 1 (LED_DIN) |

## KiCad capture order

1. Drop and connect the 5-pin header (J1) and label the 5 nets entering from it
2. Add the LDO (U1) with its input and output caps
3. Add the MOSFET (Q1) with gate resistor (R7), gate pulldown (R8), source to GND
4. Add the three IR LEDs (D1-D3) with their current limit resistors (R1-R3)
5. Add the bulk cap (C1) on the 5V rail
6. Add the receiver (U2), supply isolation chain (R6, C5, C6), output pullup (R9)
7. Add the WS2812B (U3) with its decoupling cap (C8)
8. Run ERC
9. Export BOM and compare against `bom.csv`
