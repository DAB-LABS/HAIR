# HAIR PCB v1 Design Package

This directory holds the v1 PCB design for the HAIR companion hardware: a custom IR transceiver puck that runs ESPHome and pairs with the HAIR Home Assistant integration.

## What's in here

| File | Purpose |
|---|---|
| `design.md` | Full design document. Form factor, block-by-block walkthrough, GPIO map, layout guidance, pre-fab checklist. Read this first. |
| `schematic-nets.md` | Net-by-net connection list. Every pin of every part and which net it joins. Use this when capturing in KiCad. |
| `bom.csv` | Bill of materials with reference designators, footprints, and LCSC part numbers where confirmed. |
| `block-diagram.svg` | Visual block diagram of the design. |
| `hair1.yaml` | PCB-ready ESPHome firmware config (GPIO4/5/6 + WS2812B status LED). Apply when the v1 board is built. The active `esphome/hair1.yaml` at the repo root remains the dev-kit prototype config. |

## Status

This is a design package, not a complete fabrication package. Producing the actual fabrication files requires:

1. Schematic capture in KiCad (or another EDA tool) following `schematic-nets.md`
2. PCB layout following the guidance in `design.md` Section 7
3. Generation of Gerbers, drill files, pick-and-place, and BOM in JLCPCB's expected formats
4. JLCPCB part availability verification for the parts flagged as "confirm at order time"

A follow-up session will handle steps 1 through 4.

## Firmware

The PCB v1 GPIO map differs from the C3 dev kit prototype. The PCB-ready ESPHome config is at `docs/hardware/pcb-v1/hair1.yaml` and contains:

- IR TX moved from GPIO9 to GPIO4 (GPIO9 is a strapping pin)
- IR RX moved from GPIO8 to GPIO5
- WS2812B status LED added on GPIO6

Apply this config (copy or symlink into the ESPHome dashboard) once the v1 board is in hand. The active `esphome/hair1.yaml` remains the dev-kit prototype version and is unchanged.

## Design constraints honored

These were the constraints set during the design conversation:

- Single SMT pass at JLCPCB, no hand soldering
- USB-C only, no barrel jack
- 360 degree IR coverage via perimeter LED ring
- TSMP58000 wideband receiver
- WS2812B RGB status LED
- BOOT and RESET buttons accessible only when enclosure is opened
- Test pads for two spare GPIOs plus power
- Two mounting holes
- No silkscreen branding (component references only)
