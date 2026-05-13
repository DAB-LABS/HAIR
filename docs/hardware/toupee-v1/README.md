# Toupee v1 Design Package

The Toupee is a small IR transceiver breakout for users who already have an ESP32 host (dev kit, custom board, breadboard project). It provides the TX, RX, and a status LED on a compact board that plugs into any host with three GPIOs and 5V.

Think of it as the minimum-viable HAIR hardware: just the IR parts, no MCU, no USB.

## What's in here

| File | Purpose |
|---|---|
| `design.md` | Full design document. Form factor, block walkthrough, header pinout, layout guidance. Read this first. |
| `schematic-nets.md` | Net-by-net connection list for KiCad schematic capture. |
| `bom.csv` | Bill of materials with LCSC part numbers where confirmed. |
| `block-diagram.svg` | Visual block diagram. |
| `esphome-snippet.yaml` | Reference ESPHome config block. Paste into your host's config and adjust GPIO numbers to match your wiring. |

## Status

Design locked, schematic capture and PCB layout pending. Same JLCPCB single SMT pass target as the full puck (`docs/hardware/pcb-v1/`).

## Design constraints honored

- Single SMT pass, all components on the top face
- Self-contained on 5V input via onboard ME6211 LDO (no need for host 3.3V rail)
- 25 mm square target board size
- 3 IR LEDs on three perimeter sides (north, east, west), header on south side
- TSMP58000 wideband receiver in the center of the top face
- WS2812B RGB status LED adjacent to the receiver
- 5-pin 0.1 inch header for host connection

## Pinout (5-pin header on south edge)

| Pin | Net | Direction | Notes |
|---|---|---|---|
| 1 | 5V | input | LED supply, LDO input, WS2812 supply |
| 2 | GND | input | Common ground |
| 3 | TX_IN | input from host | Host GPIO drives MOSFET gate |
| 4 | RX_OUT | output to host | TSMP receiver output (open drain, 47k pulled up to 3.3V on board) |
| 5 | LED_DIN | input from host | Host GPIO drives WS2812 data |

## Coverage

Three IR LEDs at 90 degree spacing (north, east, west sides) with plus or minus 60 degree half angle give roughly 240 to 300 degrees of usable coverage. The gap points south, toward the host connection, which is the direction you would not aim IR anyway.

## How it pairs with HAIR

HAIR discovers any ESPHome device with the `infrared` platform configured. Build a host (ESP32-C3 dev kit, ESP32-S3, generic ESP32) with the Toupee wired to your chosen GPIOs, configure ESPHome using `esphome-snippet.yaml` as a starting point, and HAIR will pick it up alongside any other proxies in your install.
