# Contributing to HAIR

Thanks for your interest in contributing to HAIR. This document covers the basics.

## Getting Started

1. Fork the repository
2. Clone your fork and create a feature branch from `main`
3. Install development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test,lint]"
```

## Development

### Project Structure

```
custom_components/hair/
  __init__.py              # Integration setup, panel registration
  config_flow.py           # Config and options flows
  const.py                 # Constants, enums, event names
  models.py                # Data models (IRDevice, IRCommand)
  device_manager.py        # Device CRUD and TX orchestration
  signal_monitor.py        # Real-time IR signal listener
  signal_store.py          # Signal persistence and deduplication
  capture_orchestrator.py  # IR capture session management
  capture.py               # Capture provider abstraction
  entity_factory.py        # HA entity creation from devices
  command_templates.py     # Per-device-type command templates
  websocket_api.py         # WebSocket command handlers
  storage.py               # Persistent storage layer
  event_parser.py          # IR event parsing and fingerprinting
  ir_command.py            # ProntoCommand adapter for infrared platform
  diagnostics.py           # Config entry diagnostics
  button.py                # Button entity platform
  remote.py                # Remote entity platform
  media_player.py          # Media player entity platform
  climate.py               # Climate entity platform
  fan.py                   # Fan entity platform
  light.py                 # Light entity platform
  switch.py                # Switch entity platform
  cover.py                 # Cover entity platform (screens, shades)
  frontend/src/            # LitElement/TypeScript admin panel
  tests/                   # pytest test suite (383 tests)
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest custom_components/hair/tests/test_device_manager.py

# With verbose output
pytest -v
```

### Linting

```bash
ruff check .
```

### Frontend

The admin panel is built with LitElement and TypeScript. The compiled bundle lives at `frontend/dist/ha-panel-ir-devices.js`. Source files are in `frontend/src/`.

## Pull Requests

- Create a feature branch from `main` (e.g., `feature/my-change`)
- Keep PRs focused on a single change
- Include tests for new backend functionality
- Make sure `pytest` and `ruff check .` pass before opening a PR
- Write a clear PR description explaining what changed and why

## Bug Reports

Use the [GitHub issue tracker](https://github.com/DAB-LABS/HAIR/issues). Include:

- Your HA version
- HAIR version
- Steps to reproduce the issue
- Expected vs. actual behavior
- Relevant log output (Settings > System > Logs, filter for `hair`)

## Code Style

- Python: follow existing patterns, ruff handles formatting
- TypeScript: LitElement conventions, Lit decorators for properties
- Keep public-facing text (README, comments, UI copy) free of em-dashes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
