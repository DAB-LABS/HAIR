# M5Stack IR Unit

An infrared photoelectric sensor unit ready to be used with other devices from the
M5Stack ecosystem.

## Hardware

The infrared transceiver can be bought [here](https://shop.m5stack.com/products/ir-unit).
In the configuration files here it is used together with another device from M5Stack,
the [AtomS3 Lite](https://shop.m5stack.com/products/atoms3-lite-esp32s3-dev-kit).

## GPIO Map

| GPIO | Function |
|---|---|
| GPIO1 | IR Unit receiver |
| GPIO2 | IR Unit transmitter |
| GPIO35 | AtomS3 Lite RGB LED |
| GPIO41 | AtomS3 Lite Button |

## Flashing

1. Copy `m5stack-ir-unit-minimal.yaml` to your ESPHome config directory
2. Update the `substitutions` block with your preferred device name
3. Add required entries to your `secrets.yaml`
4. Flash via the ESPHome Dashboard or CLI

## Compatibility

| Component | Version |
|---|---|
| HAIR | 0.3.4 |
| HA Core | 2026.6.1 |
| ESPHome | 2026.5.3 |

## Variants

The "minimal" variant only contains the bare minimum to make the IR transceiver
available in Home Assistant.
The "full" variant shows the current state (idle, receiving, transmitting) with
the RGB LED of the AtomS3 Lite, and also exposes the push button to Home Assistant.
