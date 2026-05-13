# HAIR PCB v1 Schematic Net List

This document lists every electrical net in the design with each connected pin. Use it as the source of truth when capturing the schematic in KiCad (or any other EDA tool).

## Reference designator key

| Prefix | Type |
|---|---|
| U | Integrated circuit / module |
| Q | Transistor / MOSFET |
| D | Diode / LED |
| R | Resistor |
| C | Capacitor |
| J | Connector |
| SW | Switch |
| TP | Test pad |
| H | Mounting hole |

## Component inventory

| Ref | Part | Description |
|---|---|---|
| U1 | ESP32-C3-MINI-1 | MCU module |
| U2 | ME6211C33M5G | 3.3V LDO |
| U3 | USBLC6-2SC6 | USB ESD protection |
| U4 | TSMP58000 | IR receiver |
| U5 | WS2812B | RGB status LED |
| Q1 | AO3400 | TX MOSFET |
| D1 to D7 | IR15-21C class | IR LEDs, side firing 940 nm |
| R1 to R7 | 22 ohm 0805 | IR LED current limit |
| R8 | 1k 0603 | MOSFET gate series |
| R9 | 10k 0603 | MOSFET gate pulldown |
| R10 | 100 ohm 0603 | TSMP supply isolation series |
| R11 | 47k 0603 | TSMP output pullup |
| R12 | 10k 0603 | EN pullup |
| R13 | 10k 0603 | GPIO9 (BOOT) pullup |
| R14 | 5.1k 0603 | USB-C CC1 pulldown |
| R15 | 5.1k 0603 | USB-C CC2 pulldown |
| C1 | 10 uF 0805 | 5V input bulk |
| C2 | 220 uF polymer | 5V LED ring bulk |
| C3 | 1 uF 0603 | LDO input |
| C4 | 1 uF 0603 | LDO output |
| C5 | 10 uF 0805 | Module 3.3V bulk |
| C6 | 1 uF 0603 | Module 3.3V mid |
| C7 | 100 nF 0402 | Module 3.3V HF |
| C8 | 1 uF 0603 | EN debounce cap |
| C9 | 4.7 uF 0805 | TSMP supply bulk (post RC) |
| C10 | 100 nF 0402 | TSMP HF bypass |
| C11 | 100 nF 0402 | WS2812B local decoupling |
| J1 | USB Type-C 12 or 16 pin | USB connector |
| SW1 | SMD tactile | RESET |
| SW2 | SMD tactile | BOOT |
| TP1 | SMT pad | 3.3V test point |
| TP2 | SMT pad | GND test point |
| TP3 | SMT pad | GPIO7 spare |
| TP4 | SMT pad | GPIO10 spare |
| H1, H2 | Non plated 3 mm hole | Mounting |

## Power and ground nets

### Net: VBUS_5V

USB-C input, becomes the 5V rail after the connector.

| Connection | Pin |
|---|---|
| J1 | VBUS (pins A4, A9, B4, B9 on 24 pin; or VBUS pins on 12 / 16 pin variant) |
| C1 | + |
| C2 | + |
| U2 | Pin 1 (VIN) |
| C3 | + |
| D1 anode side of R1 | (R1 pin 1) |
| D2 anode side of R2 | (R2 pin 1) |
| D3 anode side of R3 | (R3 pin 1) |
| D4 anode side of R4 | (R4 pin 1) |
| D5 anode side of R5 | (R5 pin 1) |
| D6 anode side of R6 | (R6 pin 1) |
| D7 anode side of R7 | (R7 pin 1) |
| U5 | VDD (pin 4 typical for WS2812B 5050) |

### Net: VCC_3V3

LDO output, main 3.3V rail.

| Connection | Pin |
|---|---|
| U2 | Pin 5 (VOUT) |
| C4 | + |
| C5 | + |
| C6 | + |
| C7 | + |
| U1 | 3V3 supply pins per ESP32-C3-MINI-1 datasheet |
| R10 | Pin 1 (input side of TSMP supply isolation) |
| R11 | Pin 1 (output pullup top) |
| R12 | Pin 1 (EN pullup top) |
| R13 | Pin 1 (BOOT pullup top) |
| TP1 | (test pad) |

### Net: VCC_3V3_RX

Filtered 3.3V rail to the TSMP58000 supply pin only. Comes from R10 to C9 to C10, isolated from VCC_3V3.

| Connection | Pin |
|---|---|
| R10 | Pin 2 (output of isolation R) |
| C9 | + |
| C10 | + |
| U4 | Pin 3 (VS) |

### Net: GND

Ground plane, common to all blocks.

| Connection | Pin |
|---|---|
| J1 | GND (pins A1, A12, B1, B12 on 24 pin; or GND pins on 12 / 16 pin variant) |
| J1 | Shield pins (S1 through S4 if present) |
| U2 | Pin 2 (GND) |
| U3 | Pin 2 (GND) |
| U1 | GND pins per ESP32-C3-MINI-1 datasheet |
| U4 | Pin 2 (GND) |
| U5 | GND (pin 3 typical for WS2812B 5050) |
| Q1 | Pin 2 (source) |
| All caps | Negative side or ground pin |
| R9 | Pin 2 (gate pulldown to GND) |
| R14 | Pin 2 |
| R15 | Pin 2 |
| C8 | Negative (EN debounce cap to GND) |
| SW1 | Pin connected to GND (RESET button) |
| SW2 | Pin connected to GND (BOOT button) |
| TP2 | (test pad) |

## USB nets

### Net: USB_DP

USB-C D plus, routed as differential pair with USB_DM.

| Connection | Pin |
|---|---|
| J1 | A6 and B6 (USB-C D plus, both orientations) |
| U3 | I/O pin for D plus per USBLC6-2 datasheet |
| U1 | GPIO19 |

### Net: USB_DM

USB-C D minus.

| Connection | Pin |
|---|---|
| J1 | A7 and B7 (USB-C D minus, both orientations) |
| U3 | I/O pin for D minus per USBLC6-2 datasheet |
| U1 | GPIO18 |

### Net: USB_CC1

USB-C configuration channel 1.

| Connection | Pin |
|---|---|
| J1 | A5 (CC1) |
| R14 | Pin 1 |

### Net: USB_CC2

USB-C configuration channel 2.

| Connection | Pin |
|---|---|
| J1 | B5 (CC2) |
| R15 | Pin 1 |

## IR TX nets

### Net: IR_TX_GATE

ESP32 drive signal to MOSFET gate.

| Connection | Pin |
|---|---|
| U1 | GPIO4 |
| R8 | Pin 1 |

### Net: IR_TX_GATE_FET

MOSFET gate node (after series R, before pulldown junction).

| Connection | Pin |
|---|---|
| R8 | Pin 2 |
| R9 | Pin 1 |
| Q1 | Pin 1 (gate) |

### Net: IR_LED_CATHODE_BUS

Common cathode bus from all 7 IR LEDs to the MOSFET drain.

| Connection | Pin |
|---|---|
| D1 | Cathode |
| D2 | Cathode |
| D3 | Cathode |
| D4 | Cathode |
| D5 | Cathode |
| D6 | Cathode |
| D7 | Cathode |
| Q1 | Pin 3 (drain) |

### Per LED nets (anode side of each LED to its current limit resistor output)

| Net | Connections |
|---|---|
| LED1_A | R1 pin 2, D1 anode |
| LED2_A | R2 pin 2, D2 anode |
| LED3_A | R3 pin 2, D3 anode |
| LED4_A | R4 pin 2, D4 anode |
| LED5_A | R5 pin 2, D5 anode |
| LED6_A | R6 pin 2, D6 anode |
| LED7_A | R7 pin 2, D7 anode |

(R1 to R7 pin 1 is on VBUS_5V, see power nets above.)

## IR RX nets

### Net: IR_RX

Receiver output to MCU.

| Connection | Pin |
|---|---|
| U4 | Pin 1 (OUT) |
| R11 | Pin 2 |
| U1 | GPIO5 |

## Status LED nets

### Net: WS2812_DIN

Data input to the WS2812B from the MCU.

| Connection | Pin |
|---|---|
| U1 | GPIO6 |
| U5 | DIN (pin 2 typical for WS2812B 5050) |
| C11 | + (local decoupling for the LED) |

### Net: WS2812_DOUT

WS2812B data out, unused but exposed for future chaining.

| Connection | Pin |
|---|---|
| U5 | DOUT (pin 1 typical for WS2812B 5050) |
| (no other connection, leave floating) | |

## MCU control nets

### Net: NRST

Reset signal to the ESP32-C3 EN pin.

| Connection | Pin |
|---|---|
| U1 | EN |
| R12 | Pin 2 |
| C8 | Positive |
| SW1 | Pin connected to EN (RESET button) |

### Net: BOOT

Boot mode strap on GPIO9.

| Connection | Pin |
|---|---|
| U1 | GPIO9 |
| R13 | Pin 2 |
| SW2 | Pin connected to GPIO9 (BOOT button) |

## Expansion test pad nets

### Net: SPARE_GPIO7

| Connection | Pin |
|---|---|
| U1 | GPIO7 |
| TP3 | (test pad) |

### Net: SPARE_GPIO10

| Connection | Pin |
|---|---|
| U1 | GPIO10 |
| TP4 | (test pad) |

## Summary

Total nets: approximately 22

| Category | Net count |
|---|---|
| Power and ground | 4 |
| USB | 4 |
| IR TX | 10 (1 gate, 1 gate-FET node, 1 cathode bus, 7 anode nets) |
| IR RX | 1 |
| Status LED | 2 |
| MCU control | 2 |
| Expansion | 2 |

## Capture order recommended for KiCad

1. Drop and wire the ESP32-C3-MINI-1 module
2. Add the LDO and 3.3V net, decoupling caps
3. Add the USB-C connector, CC pulldowns, ESD device, D plus and D minus pair
4. Add the BOOT and RESET buttons with pullups and debounce cap
5. Add the MOSFET, gate network, current limit resistor array, LED ring
6. Add the receiver with RC filter, decoupling, output pullup
7. Add the WS2812B with local decoupling cap
8. Add test pads
9. Run ERC, fix any unconnected pins or duplicated net names
10. Generate the BOM and compare against `bom.csv` in this directory
