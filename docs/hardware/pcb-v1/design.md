# HAIR PCB v1 Design Document

**Status:** Locked design, schematic capture pending.
**Target fab:** JLCPCB single-pass SMT assembly.
**Target firmware:** ESPHome 2026.x with `ir_rf_proxy` infrared platform.

## 1. Overview

HAIR PCB v1 is a custom IR transceiver companion device for the HAIR Home Assistant integration. It replaces the ESP32-C3 dev kit prototype with a purpose-built board offering 360 degree IR coverage, integrated USB-C, and an RGB status indicator. The firmware remains pure ESPHome YAML; no custom C++ components are required.

The device is designed for surface mount only assembly with no through-hole parts, allowing JLCPCB to assemble it in a single SMT pass without a manual finishing step.

## 2. Form Factor

| Property | Value |
|---|---|
| Outline | Regular octagon |
| Flat-to-flat | ~53 mm |
| Vertex-to-vertex | ~58 mm |
| Side length | ~22 mm |
| Thickness | 1.6 mm FR4 (standard) |
| Mounting | Two 3 mm holes on the front face (back side adhesive optional) |

### 2.1 Side allocation

Eight rim sides, allocated as:

| Side | Component |
|---|---|
| 1 (back) | USB-C connector |
| 2 through 8 | IR LED, side firing, centered on the side edge |

LEDs sit at 45 degree intervals around the rim, covering 315 degrees of the perimeter directly. The remaining 90 degree slice points behind the cable, where adjacent LED cones still provide reduced intensity coverage from their plus or minus 60 degree half angles.

### 2.2 Face allocation

| Face | Contents |
|---|---|
| Front | TSMP58000 IR receiver (center), WS2812B RGB status LED (offset), spare GPIO test pads |
| Back | Blank surface for adhesive or screw mount, two mounting holes |

The front face is the "user facing" side. The device works in either install orientation (desk or ceiling) because the LED ring fires horizontally regardless of vertical orientation, and the user always points their remote at the receiver face.

## 3. Block: Power Input

### 3.1 USB-C

USB-C 2.0 only, 12 or 16 pin connector. Functions:

- VBUS to 5V rail
- GND
- D plus to GPIO19 (ESP32-C3 native USB)
- D minus to GPIO18 (ESP32-C3 native USB)
- CC1 with 5.1k pulldown to GND
- CC2 with 5.1k pulldown to GND

The 5.1k CC pulldowns are mandatory. They advertise the device as a USB Type-C power sink at the default 500 mA / 1.5 A capability. Without these resistors, USB-C to USB-C cables will not deliver power because the source has no indication that a sink is present.

The 24 pin "full feature" USB-C connector is overkill for this application. A 12 or 16 pin USB 2.0 connector is sufficient and significantly cheaper. The 6 pin USB-C variant must be avoided because it lacks CC pins.

### 3.2 ESD protection

USBLC6-2SC6 (SOT-23-6) provides bidirectional TVS protection on D+, D-, and the CC lines. Placed close to the USB-C connector, before any other USB net traces. Cost is approximately $0.10 and the part is widely stocked.

### 3.3 5V bulk capacitance

Two bulk caps on the 5V rail:

- 10 uF ceramic at the USB-C input, for input ripple smoothing
- 220 uF aluminum polymer near the LED ring, for absorbing burst current during IR transmit

The 220 uF cap is sized to absorb 7 LEDs at 150 mA pulsed (1050 mA peak burst) without significant droop on the 5V rail. Without this cap, the USB cable becomes the supply path for the burst, causing voltage sag and adding RF noise that the IR receiver will detect.

## 4. Block: Voltage Regulation

ME6211C33M5G LDO, SOT-23-5 package, 500 mA capacity, 200 mV dropout.

- Input: 5V from USB-C
- Output: 3.3V
- Input cap: 1 uF ceramic
- Output cap: 1 uF ceramic

The 3.3V rail powers the ESP32-C3 module, the TSMP58000 receiver, and pullups. WS2812B and IR LEDs are powered directly from 5V.

The AMS1117-3.3 mentioned in the original handoff doc was rejected in favor of the ME6211 because the AMS1117 has 1.3 V dropout (vs 200 mV) and dissipates roughly 600 mW at 350 mA, requiring thermal relief copper and running noticeably warm. The ME6211 runs cool with no special thermal considerations.

## 5. Block: MCU

### 5.1 Module

ESP32-C3-MINI-1, pre-certified FCC and CE module with built-in PCB antenna. Footprint and pinout per Espressif datasheet.

### 5.2 Decoupling

Per Espressif reference design at the module 3V3 supply pin:

- 10 uF ceramic
- 1 uF ceramic
- 100 nF ceramic

All placed within 5 mm of the supply pin, on the same side as the module.

### 5.3 EN and reset

- 10k pullup from EN to 3.3V
- 1 uF cap from EN to GND (debounce, clean power on reset)
- Tactile SMD switch from EN to GND, on board only (no enclosure access)

### 5.4 Boot strap

- 10k pullup from GPIO9 to 3.3V
- Tactile SMD switch from GPIO9 to GND, on board only

GPIO9 is the C3 boot mode strapping pin. It must be HIGH at reset for normal boot from flash. The pullup ensures this default. The button pulls it low for download mode access; users would only need this if the USB-Serial-JTAG path is unavailable for some reason.

### 5.5 Native USB programming

ESP32-C3 has a built in USB-Serial-JTAG peripheral on GPIO18 (D-) and GPIO19 (D+). No external USB to UART bridge chip (CH340, CP2102, etc.) is required. The USB-C D+ and D- nets route as a tight differential pair directly to GPIO18 and GPIO19.

For USB 2.0 Full Speed (12 Mbps) on a standard 2-layer 1.6 mm FR4 board, exact 90 ohm differential impedance is not critical. Length matching within 1 mm and trace width around 0.6 mm with 0.15 mm spacing is sufficient.

## 6. Block: IR Transmit

### 6.1 LED ring

Seven side firing SMD IR LEDs, 940 nm, one per perimeter side. Reference part is the Everlight IR15-21C class (plus or minus 60 degree half angle, 1 A peak pulsed, 100 mA continuous). Final part selection at order time based on JLCPCB basic parts availability; functional substitutes include Honglitronic HRP-1208WC-940, Kingbright side-emit IR variants, and Vishay TOPLED side-emit parts.

Each LED is positioned so its emission axis is perpendicular to the PCB edge (radially outward). The dome of the side firing package aligns flush with the PCB edge.

### 6.2 Current limit

Each LED has its own 22 ohm 0805 current limit resistor in series with its anode, anode tied to the 5V rail.

For Vf approximately 1.5 V at 150 mA pulsed: R_limit = (5 - 1.5) / 0.15 = 23.3 ohm, rounded to standard 22 ohm.

Per LED resistors are mandatory. LEDs in parallel without individual resistors share current unevenly due to forward voltage tolerance, causing one LED to run hotter and fail prematurely. This is a common amateur mistake.

### 6.3 MOSFET driver

AO3400 N-channel MOSFET, SOT-23 package, common drain configuration. The drain connects to all seven LED cathodes (sink common), the source connects to GND, and the gate is driven by GPIO4 through a 1k series resistor with a 10k gate to GND pulldown.

- 1k gate series limits inrush during high speed switching at the 38 kHz carrier
- 10k gate to GND pulldown keeps the MOSFET off (LEDs off) during boot, reset, and any GPIO float condition

The AO3400 was chosen over the 2N7002 mentioned in the original handoff doc because:

- Rds(on) approximately 30 m ohm vs the 2N7002's roughly 5 ohm
- Continuous current rating of 5.7 A vs 115 mA
- Same SOT-23 footprint and roughly $0.05 cost
- Negligible voltage drop across the FET means the LED sees the full 5V minus the 22 ohm drop, maximizing current consistency

### 6.4 Burst current budget

7 LEDs at 150 mA pulsed = 1050 mA peak instantaneous draw during a burst. This is within USB-C BC1.2 advertised capacity (1.5 A). The 220 uF bulk cap on the 5V rail near the LED ring absorbs the burst so the USB cable sees a smoothed average draw.

## 7. Block: IR Receive

### 7.1 Receiver

Vishay TSMP58000, wideband IR receiver. Chosen over the TSOP38238 because:

- Wider carrier frequency acceptance (covers 30 to 56 kHz, not locked to 38 kHz)
- No aggressive AGC that suppresses long IR bursts (a known problem with TSOP382xx series during learning)
- Specifically marketed for IR learning applications

Final part availability at LCSC and JLCPCB should be confirmed at order time. If the TSMP58000 is unavailable, the next-best wideband substitute is the TSMP4138 or TSOP31338. Plain TSOP38238 is a last resort.

### 7.2 Supply isolation (the critical detail)

The TSMP58000 is sensitive to noise on its supply pin. Without proper isolation, it will false trigger off:

- WiFi RF activity from the ESP32 module
- MOSFET switching during IR transmit
- Voltage droop on the 5V rail during LED bursts (even with the 220 uF cap)

Isolation circuit on the receiver's VS pin (sourced from 3.3V, not 5V):

```
3.3V rail ---R1 (100 ohm)---+--- VS (TSMP58000 pin 3)
                            |
                          C1 (4.7 uF ceramic)
                            |
                          C2 (100 nF ceramic)
                            |
                           GND
```

R1 plus C1 forms a low pass RC filter with corner around 338 Hz. Anything faster than that (WiFi, MOSFET, MCU activity) is attenuated by 20 dB per decade. The receiver draws approximately 1 mA, so R1 drops 100 mV across itself, leaving 3.2 V at the receiver. C2 is high frequency bypass placed immediately at the package.

This circuit is the single most-skipped detail in DIY IR learners. Skipping it produces a board that works in isolation but fails when its own IR ring fires.

### 7.3 Output pullup

The TSMP58000 output pin is active low (pulled low when carrier detected). A 47k external pullup to 3.3V ensures clean edges and removes dependency on the ESP32 internal pullup setting. The internal pullup remains enabled in the ESPHome config as a redundant fallback.

Output net routes to GPIO5.

### 7.4 Placement

The receiver lens points up through the front face of the enclosure. Place near the center of the front face for symmetric reception. The receiver is sensitive to direct IR from the TX LEDs, so the enclosure should have an opaque divider between the LED ring and the receiver lens cavity. The receiver pointing up while the LEDs fire horizontally provides geometric isolation, but enclosure design should not rely on that alone.

## 8. Block: Status LED

WS2812B addressable RGB LED, single pixel, mounted on the front face adjacent to the IR receiver.

- Supply: 5V (the WS2812B's nominal rail)
- Data input: 3.3V GPIO drive from GPIO6, no level shifter
- Footprint: standard 5050 SMD

The 3.3V data drive into a 5V powered WS2812B is marginal per the datasheet (Vih min is 0.7 x VDD = 3.5V) but works reliably on every WS2812B variant observed in practice. The fallback if a chip variant rejects 3.3V data is to swap in an SK6812, which is pin and footprint compatible and rated for 3.3V data.

ESPHome firmware controls the LED via the `esp32_rmt_led_strip` platform.

Suggested LED behavior in firmware:

| Color | State |
|---|---|
| Solid green dim | Connected and idle |
| Blue pulse | Receiving IR |
| White flash | Transmitting IR |
| Red | WiFi disconnect or fault |

Brightness defaults to roughly 5 percent so the LED is not blinding at night.

## 9. Block: Test Pads and Mounting

### 9.1 Test pads

Four 1.5 mm SMT test pads on the back side of the PCB inside the octagon:

| Pad | Net |
|---|---|
| TP1 | 3.3V |
| TP2 | GND |
| TP3 | GPIO7 (spare) |
| TP4 | GPIO10 (spare) |

These allow oscilloscope probing during debug and provide expansion points for users who want to add I2C peripherals (BME280, OLED, etc.) without modifying the PCB.

### 9.2 Mounting holes

Two 3 mm unplated mounting holes, diametrically opposite, positioned within the octagon outline at safe distances from copper. Used for screw mount installations; an adhesive pad on the back face is the alternative for non-permanent installs.

## 10. GPIO Assignment

| Function | Pin | Direction | Notes |
|---|---|---|---|
| IR TX MOSFET gate drive | GPIO4 | Output | Through 1k series, 10k gate pulldown |
| IR RX from TSMP output | GPIO5 | Input | Internal pullup enabled in firmware, 47k external pullup also present |
| WS2812B data | GPIO6 | Output | 3.3V drive into 5V WS2812B, no level shifter |
| Spare expansion | GPIO7 | (test pad) | Brought to TP3 |
| BOOT strap | GPIO9 | Input | 10k pullup to 3.3V, button to GND |
| Spare expansion | GPIO10 | (test pad) | Brought to TP4 |
| USB D- | GPIO18 | (USB) | Native USB-Serial-JTAG |
| USB D+ | GPIO19 | (USB) | Native USB-Serial-JTAG |

Strapping pin notes:

- GPIO2, GPIO8, GPIO9 are strapping pins on the ESP32-C3. GPIO9 is used here intentionally (for the BOOT button). GPIO2 and GPIO8 are not used in this design.

## 11. PCB Layout Guidance

### 11.1 Antenna keepout

The ESP32-C3-MINI-1 datasheet specifies a no-copper, no-trace keepout zone at the antenna corner of the module (roughly 6 mm clearance). Orient the module so the antenna corner points into the board interior, away from any LED, large copper pour, or USB-C metal shell. Do not run traces under the antenna keepout.

### 11.2 USB differential pair

Route D+ and D- as a tight pair with matched length and consistent width. On a 2 layer 1.6 mm FR4 board, 0.6 mm trace width with 0.15 mm spacing gives an acceptable approximation of 90 ohm differential impedance for USB 2.0 Full Speed. Keep the run short (less than 50 mm) and clear of other high speed signals.

### 11.3 Receiver supply isolation

Place R1 (100 ohm) and C1 (4.7 uF) physically between the LDO output and the receiver. C2 (100 nF) goes right at the receiver pin. The intent is that the RC filter sits in series with the receiver's supply tap, not as a parallel branch. Do not share VS routing with the WS2812B or the MCU module supply.

### 11.4 Ground plane

Continuous ground plane on the bottom layer under the module, receiver, and LED ring. Avoid splits or cutouts under the antenna or USB lines. The plane stitches the bypass caps to their respective IC grounds.

### 11.5 LED ring layout

Each LED footprint is centered on its octagon side with the emission axis aligned to the side normal. Each 22 ohm current limit resistor is placed immediately inboard of its LED, with the 5V trace running to the resistor and the cathode trace going to the MOSFET drain rail. Keep the cathode rail width adequate for 1 A pulsed draw (0.5 mm trace width is sufficient for short pulses).

### 11.6 220 uF bulk cap placement

Aluminum polymer cap placed in the center of the board between the LED ring and the MOSFET. Direct low impedance path to the MOSFET drain rail and to the 5V plane.

### 11.7 ESD protection placement

USBLC6-2 immediately at the USB-C connector. D+ and D- traces enter the ESD device first, then exit toward the module.

## 12. Pre-Fab Checklist

Before submitting Gerbers to JLCPCB:

1. Antenna keepout zone is clear of copper and traces
2. USB-C CC pulldowns present and correctly tied to GND
3. Receiver RC filter components physically grouped near the receiver
4. 220 uF polymer cap is near the LED ring, not near the LDO
5. Mounting holes have appropriate clearance from copper
6. All 7 LED footprints are oriented with emission axis aligned to the side
7. MOSFET gate has both the 1k series and the 10k pulldown
8. Boot and reset buttons are accessible from inside the enclosure (matching enclosure CAD)
9. Test pads are reachable with a standard probe
10. Silkscreen has component references only (no branding text on v1)
11. BOM CSV exported with LCSC part numbers populated
12. Pick and place file uses JLCPCB orientation conventions

## 13. Known Open Items

1. **Specific LCSC part numbers for the IR LED.** The Everlight IR15-21C is the reference part but JLCPCB stock should be verified at order time. Substitutes are functionally equivalent.

2. **TSMP58000 availability.** Vishay parts at LCSC can be intermittent. If unavailable, the design accepts TSMP4138 or TSOP31338 substitutes with no schematic change.

3. **Enclosure design.** A 3D-printable case is a separate work item. The PCB outline and mounting hole positions are fixed in this design; the case wraps around them.

4. **OTA password hardening.** The current `hair1.yaml` contains a plaintext OTA password literal. This is unrelated to the PCB but should be moved to `secrets.yaml` before the repo is made public.

5. **FCC / CE certification.** Using a pre-certified ESP32-C3-MINI-1 module covers the radio portion. End product certification for unintentional emitters and conducted emissions is a separate process the user can pursue if distributing the design commercially.

## 14. Approximate Cost

Rough order of magnitude for a 10 unit run at JLCPCB with full assembly:

| Line item | Approximate cost (USD) |
|---|---|
| PCB fabrication, 10 boards | 5 to 15 |
| SMT assembly, 10 boards, ~40 unique parts | 60 to 120 |
| Parts (BOM cost across 10 units) | 80 to 150 |
| Shipping (DHL standard) | 25 to 50 |
| **Total per board** | approximately 17 to 33 |

Per board cost drops significantly at 50+ units due to setup and panelization economies.
