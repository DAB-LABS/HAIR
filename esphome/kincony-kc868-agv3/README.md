# KinCony KC868-AGv3

KinCony's ESP32-S3 IR and RF controller: a round-cornered puck with 7 IR tubes inside the box, an IR receiver, two IR extension cable ports, a 433 MHz RF sender and receiver, and a buzzer. Sold by [KinCony](https://www.kincony.com/esp32s3-smart-ir-rf-controller.html).

HAIR uses the IR side only. The config has been checked with `esphome config`; it has not yet been run on the hardware.

## Hardware

- Module: ESP32-S3-WROOM-1U N16R8 (16 MB flash, 8 MB PSRAM)
- Board definition: `esp32-s3-devkitc-1`, `variant: esp32s3`, esp-idf, `flash_size: 16MB`
- PSRAM is left out of the config: IR does not need it, and a wrong PSRAM mode stops the board booting.

## GPIO Map

From KinCony's pin definition, https://www.kincony.com/forum/showthread.php?tid=9468.

| GPIO | Function | In the config |
|---|---|---|
| GPIO47 | IR sender (the 7 IR tubes inside the box) | yes |
| GPIO1 | IR receiver (active-low: inverted, pull-up) | yes |
| GPIO43 | IR extension cable port 1 | commented out |
| GPIO44 | IR extension cable port 2 | commented out |
| GPIO2 | RF433 sender | no |
| GPIO9 | RF433 receiver | no |
| GPIO21 | Buzzer | no |
| GPIO11 / GPIO10 | I2C SDA / SCL | no |

The receiver settings (`inverted: true` with a pull-up) match the config Simon Says Home Assistant shows working on his unit in [Now IR Proxy is Easy with the Kincony IR Gateway and ESP Home!](https://www.youtube.com/watch?v=LqFLHZzLR54).

To use the extension ports, uncomment the two extra `remote_transmitter` entries and their `infrared:` entries in the YAML. GPIO43 and GPIO44 are the S3's UART0 pins; the S3's logger uses the USB port by default, so leave it there while the ports are in use.

## Flashing

1. Copy `kincony-kc868-agv3-minimal.yaml` to your ESPHome config directory
2. Update the `substitutions` block with your preferred device name
3. Add required entries to your `secrets.yaml` (see below)
4. Flash over USB-C via the ESPHome Dashboard or CLI the first time, OTA after that

## Required secrets.yaml entries

```yaml
api_encryption_key: "<your-api-encryption-key>"
ota_password: "<your-ota-password>"
wifi_ssid: "<your-wifi-ssid>"
wifi_password: "<your-wifi-password>"
ap_password: "<your-fallback-ap-password>"
```

## Compatibility

| Component | Version |
|---|---|
| HAIR | not yet run on hardware |
| HA Core | not yet run on hardware |
| ESPHome | 2026.9.1 (`esphome config` only) |

## Variants

Only the minimal variant is provided: IR TX on the internal tubes, IR RX, and the HA infrared platform entries. RF, buzzer and I2C are on the board but not configured.
