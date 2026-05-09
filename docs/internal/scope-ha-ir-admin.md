# HA IR Admin — Scope Document

**Project:** HA IR Admin
**Type:** Third-party Home Assistant Integration
**Status:** Planning
**Created:** 2026-05-08
**Author:** David Bailey

---

## Overview

HA IR Admin is a third-party Home Assistant integration that provides a unified admin interface for infrared (IR) device management. Built on HA's new native infrared platform (released in 2026.4), it acts as the management layer — enabling users to capture, organize, and manage IR commands through a polished UI.

No YAML required. Works with any IR proxy (ESPHome, Broadlink, etc.).

## Core Concept

HA IR Admin sits between the user and HA's IR platform. It doesn't replace the IR hardware integrations (Broadlink, ESPHome, etc.) — it complements them by providing the admin experience those integrations lack. Think of it like how the Z-Wave JS UI manages Z-Wave devices, but for IR.

## MVP Features

- **Device CRUD** — Create, read, update, and delete IR device profiles (TV, AC, soundbar, etc.)
- **Command Capture Flow** — Point-and-shoot IR learning with real-time feedback
- **Entity Creation** — Automatically create HA entities via the native IR platform
- **Admin UI** — Integrated into HA Settings, not a separate panel

## Design Principles

1. **Frictionless** — Every interaction should feel intuitive. Capture an IR command in 3 clicks or fewer.
2. **No YAML** — Everything through the UI. Config flows, not config files.
3. **Proxy-agnostic** — Works with any IR transmitter/receiver that HA supports.
4. **Native-first** — Built on HA's IR platform, not a parallel system.

## Target Users

- HA users with IR-controlled devices (TVs, ACs, soundbars, projectors, fans)
- Users migrating from Broadlink app, Switchbot, or Tuya IR hubs
- Users who want climate control (mini-splits, window ACs) in HA without YAML

## Technical Foundation

- Home Assistant 2026.4+ (IR platform dependency)
- Python 3.12+
- HA Frontend (LitElement-based admin panel)
- Works with: ESPHome IR, Broadlink, any future IR proxy

## Success Metrics

- Time to first IR command captured: < 60 seconds
- Zero YAML required for full setup
- Positive community reception on HA forums
- HACS adoption within first month

---

*This document defines the project scope. Detailed plans, architecture, and reviews are in sibling directories.*
