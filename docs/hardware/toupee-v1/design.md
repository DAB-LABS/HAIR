# Toupee v1 Design Document

**Status:** Design locked, schematic capture pending.
**Target fab:** JLCPCB single SMT pass.
**Target firmware:** ESPHome on the user's existing ESP32 host.

## 1. Overview

The Toupee is a compact IR transceiver breakout for users who already own an ESP32. It carries the IR LED ring, IR receiver, status LED, MOSFET driver, and a small LDO, then exposes a 5-pin header for the host to provide 5V and three GPIOs (TX, RX, LED data).

Compared to the full HAIR puck at `docs/hardware/pcb-v1/`, the Toupee removes:

- The ESP32-C3 module
- USB-C connector and ESD protection
- USB-Serial-JTAG programming circuit
- BOOT and RESET buttons
- The full 7-LED ring (replaced with a 3-LED arc)
- Mounting holes and octagonal outline

It retains everything that has to be on a per-IR board: the LED driver, the receiver with its critical RC supply isolation, the bulk cap for burst absorption, and the addressable status LED.

## 2. Form Factor

| Property | Value |
|---|---|
| Outline | Square |
| Side length | 25 mm target |
| Thickness | 1.6 mm FR4 (standard) |
| Component side | Top only, single SMT pass |
| Mounting | Header pins double as mechanical support on a breadboard; no separate mounting holes on v1 |

### 2.1 Component layout

```
                North edge (IR LED north)
        +----------------------------------+
        |                                  |
        |  [LDO]                  [MOSFET] |
West    |                                  | East
LED  ---|        [TSMP58000]               |--- LED
        |        [WS2812B]                 |
        |                                  |
        |  [100uF bulk]      [RX filter]   |
        |                                  |
        +----------------------------------+
                South edge (5-pin header)
```

If routing on a 25 mm square proves tight during PCB layout, expanding to 27 or 28 mm is acceptable. The 25 mm target is chosen so the board lines up naturally with standard 25 mm breadboard rows and 3D-printed enclosures.

### 2.2 IR coverage

Three side-firing IR LEDs at north, east, and west sides, each firing radially outward with a plus or minus 60 degree half angle:

| LED | Coverage cone |
|---|---|
| North (D1) | -60 to +60 deg (north arc) |
| East (D2) | 30 to 150 deg (east arc) |
| West (D3) | 210 to 330 deg (west arc) |

Total usable coverage spans roughly 240 to 300 degrees of azimuth. The gap from 150 to 210 degrees points south, toward the header, which is the direction you would not aim IR anyway because that is where the host wires exit.

## 3. Block: Header

5-pin 0.1 inch (2.54 mm) male pin header on the south edge of the board. Silkscreen labels each pin.

| Pin | Net | Description |
|---|---|---|
| 1 | 5V | Host supply (4.5 to 5.5 V acceptable) |
| 2 | GND | Common ground |
| 3 | TX_IN | Logic input from host GPIO, drives MOSFET gate through 1k series |
| 4 | RX_OUT | Open drain output from TSMP receiver, 47k pullup to 3.3V on board |
| 5 | LED_DIN | Logic input from host GPIO, drives WS2812B data line |

Logic levels: 3.3V host GPIO drives MOSFET gate and WS2812 data fine. RX_OUT is referenced to the on-board 3.3V rail (from the LDO), so the host sees logic levels between 0 and 3.3V. This is compatible with any 3.3V GPIO MCU. If used with a 5V MCU like an Arduino, an external level shifter or the host's input tolerance must be considered.

## 4. Block: LDO

ME6211C33M5G (SOT-23-5), 500 mA, 200 mV dropout.

- Input: 5V from header
- Output: 3.3V to the TSMP58000 supply (via RC filter) and to the receiver's output pullup
- Input cap: 1 uF ceramic
- Output cap: 1 uF ceramic

The LDO is sized for the receiver's tiny draw (about 1 to 5 mA) plus the 47k pullup leakage. The bulk of the board's current draw is on the unregulated 5V rail (LEDs and WS2812B), so the LDO sees almost no load and runs cold.

## 5. Block: IR Transmit

### 5.1 LEDs

Three side-firing SMD IR LEDs, 940 nm, plus or minus 60 degree half angle. Reference part: Everlight IR15-21C or stocked equivalent (same family as the full puck).

Placement: one LED centered on each of the north, east, and west edges, with the dome aligned flush to the PCB edge and emission axis perpendicular to that edge.

### 5.2 Current limit

Each LED has its own 18 ohm 0805 resistor in series with its anode, anode tied to the 5V rail.

For Vf approximately 1.5 V at 200 mA pulsed: R_limit = (5 - 1.5) / 0.2 = 17.5 ohm, rounded to standard 18 ohm.

Per-LED resistors are mandatory for current sharing. See `docs/hardware/pcb-v1/design.md` Section 6 for the rationale.

### 5.3 MOSFET driver

AO3400 N-channel MOSFET, SOT-23. Same circuit as the full puck:

- Gate driven from TX_IN through 1k series resistor (R7)
- 10k gate to GND pulldown (R8) ensures the LEDs are off when the host GPIO is high impedance (boot, reset, unprogrammed state)
- Source to GND
- Drain to common cathode bus of D1, D2, D3

### 5.4 Burst current

3 LEDs at 200 mA pulsed = 600 mA peak burst. 100 uF aluminum polymer cap on 5V absorbs the burst so the host's 5V rail does not sag.

## 6. Block: IR Receive

Vishay TSMP58000 wideband IR receiver, mounted in the center of the top face with the lens facing up.

### 6.1 Supply isolation

The receiver is sensitive to noise on its supply pin, especially noise from the LED ring bursts and any switching noise on the 5V rail. The standard RC filter from the puck design is retained verbatim:

```
3.3V (from LDO) ---R6 (100 ohm)---+--- VS (TSMP pin 3)
                                  |
                                C5 (4.7 uF)
                                  |
                                C6 (100 nF)
                                  |
                                 GND
```

Low pass corner around 338 Hz. Without this filter the receiver false-triggers off its own TX bursts. Single most important detail on the board.

### 6.2 Output pullup

47k 0603 resistor from the TSMP output pin to the on-board 3.3V rail. Provides a clean rising edge and references the output to a known logic level. The host's internal pullup can be left disabled or enabled; the external pullup dominates.

The output net routes to header pin 4 (RX_OUT).

### 6.3 Lens visibility

The TSMP58000 lens points up out of the package. The Toupee is designed to be installed with the receiver visible to the room (no enclosure cover, or a transparent IR window over the receiver if enclosed).

## 7. Block: Status LED

WS2812B addressable RGB, single pixel, mounted on the top face immediately adjacent to the TSMP58000 receiver. 5V supply, 3.3V GPIO data drive.

- 100 nF 0402 local decoupling cap (C8)
- Data in from header pin 5 (LED_DIN)
- Data out left floating (no chaining on this board)

Same 3.3V into 5V chip caveat as the full puck. SK6812 is a footprint-compatible fallback if a particular WS2812B variant rejects the 3.3V data.

## 8. Block: Bulk Capacitance

100 uF aluminum polymer cap (C1) on the 5V rail, placed physically between the header and the LED ring. Provides the burst current for the 600 mA pulsed draw without the host's 5V rail seeing it as a sharp transient.

## 9. Component Inventory

Approximately 18 placements, all SMT, all on the top face.

| Block | Components |
|---|---|
| LDO | U1 (ME6211), C2 (1 uF in), C3 (1 uF out) |
| IR TX | D1-D3 (IR LEDs), R1-R3 (18 ohm), Q1 (AO3400), R7 (1k gate), R8 (10k gate pulldown), C1 (100 uF polymer) |
| IR RX | U2 (TSMP58000), R6 (100 ohm), C5 (4.7 uF), C6 (100 nF), R9 (47k pullup) |
| Status LED | U3 (WS2812B), C8 (100 nF) |
| Connector | J1 (5-pin header) |

Reference designator key:

- U = IC / module
- Q = MOSFET
- D = LED
- R = resistor
- C = capacitor
- J = header

See `bom.csv` for full parts list with LCSC part numbers.

## 10. Host Pin Requirements

The host ESP32 (or other 3.3V MCU) needs:

- One 5V supply pin capable of sourcing roughly 700 mA peak (most dev kits provide this from their USB connector)
- One GND pin
- One GPIO for TX_IN (output, driven at the carrier frequency, 38 kHz typical)
- One GPIO for RX_OUT (input, can use internal pullup as redundant fallback)
- One GPIO for LED_DIN (output, RMT-capable on ESP32; ESPHome's `esp32_rmt_led_strip` platform requires this)

ESP32-C3 candidate GPIOs for these three signals: GPIO4 (TX), GPIO5 (RX), GPIO6 (LED). Non-strapping pins. Same layout as the puck.

ESP32 or ESP32-S3 candidate GPIOs: any non-strapping GPIO with RMT capability for the LED line.

See `esphome-snippet.yaml` for a starter ESPHome config.

## 11. PCB Layout Guidance

### 11.1 Critical placements

- 100 ohm and 4.7 uF receiver isolation parts go physically between the LDO output and the TSMP supply pin, not in parallel
- 100 nF HF bypass for the receiver goes immediately at the package
- 100 uF polymer bulk cap goes between the LED ring and the MOSFET, not near the LDO

### 11.2 Routing notes

- 5V trace from header to the three LED anodes needs to handle 600 mA pulsed; use 0.5 mm minimum trace width
- Common cathode bus from the three LEDs to the MOSFET drain similarly needs 0.5 mm
- WS2812 data trace should be short (less than 15 mm) and not cross the high current LED bus
- Receiver output trace to header should run on the opposite side of the board from the LED switching nodes if possible

### 11.3 Ground plane

Continuous ground plane on the bottom layer under everything. No splits, no cutouts. Stitching vias around the receiver and the bulk cap.

### 11.4 LED edge alignment

Each IR LED footprint must be centered on its respective edge with the emission axis perpendicular to that edge. The dome aligns flush to the PCB outline so it is not blocked by an enclosure wall.

## 12. Pre-Fab Checklist

1. Three LED footprints aligned to north, east, west edges
2. 5-pin header on south edge, silkscreen pin labels
3. Receiver RC filter components physically grouped near the receiver
4. 100 uF polymer cap near the LED ring
5. WS2812B data trace under 15 mm long and not crossing LED bus
6. Ground plane is continuous under the receiver and the module
7. BOM CSV exported and compared against `bom.csv`
8. Pick and place file uses JLCPCB orientation conventions
9. No silkscreen branding on v1 (component references only)

## 13. Known Open Items

1. Verify LCSC stock of TSMP58000 and the chosen side firing IR LED before submitting the order. Substitutes are noted in `bom.csv`.
2. Decide on enclosure design: bare PCB on breadboard, custom 3D printed shell, or no enclosure. Probably "no enclosure" for v1 since this is a breakout board.
3. The 5-pin header could be a right-angle variant if users prefer the cable to exit horizontally rather than vertically. Both footprints are 0.1 inch pitch and interchangeable.

## 14. Approximate Cost

| Line item | Approximate (USD) |
|---|---|
| PCB fabrication, 10 boards | 5 to 10 |
| SMT assembly, 10 boards, ~18 unique parts | 30 to 60 |
| Parts (BOM cost across 10 units) | 30 to 50 |
| Shipping (DHL standard) | 25 to 50 |
| **Total per board** | approximately 9 to 17 |

Significantly cheaper than the full puck because there are half as many parts and no ESP32 module on the BOM.
