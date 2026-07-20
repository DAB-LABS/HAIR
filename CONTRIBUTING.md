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
  tests/                   # pytest test suite
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

## Contributing ESPHome configs

HAIR ships curated ESPHome IR configurations in [`esphome/`](esphome/). If you have a working IR setup on hardware not yet listed, we would love to include it. Copy the header template from `esphome/_template/header-template.yaml`, fill in every field, test against the listed HAIR/HA/ESPHome versions, and open a PR or post in the [HA Community forum thread](https://community.home-assistant.io/t/1010610). Full details in the [esphome/README.md](esphome/README.md).

## Adding a language

The HAIR panel is fully localizable. Adding a language is a two-file PR, and the test suite tells you when you are done.

### Translation status

| Language | Panel (`locales/`) | Config flow (`translations/`) | Status |
|---|---|---|---|
| English (en) | yes | yes | source |
| Spanish (es) | yes | yes | config flow reviewed (thanks @Waterbrain); panel dictionary is a programming-assistant draft, native reviewer wanted |
| French (fr) | yes | yes | programming-assistant draft, native reviewer wanted |
| Japanese (ja) | yes | yes | programming-assistant draft, native reviewer wanted |
| German (de) | yes | yes | programming-assistant draft, native reviewer wanted |
| Polish (pl) | yes | yes | programming-assistant draft, native reviewer wanted |
| Portuguese (pt, pt-BR) | yes | yes | programming-assistant draft (Brazilian-leaning), native reviewer wanted |
| Dutch (nl) | yes | yes | programming-assistant draft, native reviewer wanted |
| Italian (it) | yes | yes | programming-assistant draft, native reviewer wanted |
| Russian (ru) | yes | yes | programming-assistant draft, native reviewer wanted |

Assistant-drafted locales ship live on purpose: imperfect French beats English for a French user, and visible strings are the best way to find the person who will polish them. If that person is you, open a PR that corrects the values and flips the file's `_meta.review` marker to `reviewed by @yourhandle, <date>`. That marker is a real key in every panel dictionary (never rendered), so the parity tests force each locale to declare where it stands.

1. Copy `custom_components/hair/frontend/src/locales/en.json` to `locales/<lang>.json` (for example `de.json`) and translate the values only. Never change the keys. Set the `_meta.review` key to your status: `reviewed by @yourhandle, <date>` if you are a native speaker, or `Programming-assistant draft (<date>), not yet reviewed by a native speaker` if machine-assisted.
2. Copy `custom_components/hair/translations/en.json` to `translations/<lang>.json` and translate it the same way. This file covers the config flow and follows Home Assistant's nested format.
3. Wire the panel dictionary into `custom_components/hair/frontend/src/localize.ts`: add an import and a `DICTIONARIES` entry (two lines, the file header shows where).
4. Run `pytest custom_components/hair/tests/test_locales.py`. It checks key parity, `{placeholder}` parity, and brand names.

Rules that the tests enforce:

- Brand names (HAIR, Sniffer, Clipper, Plucker, Mirror, Tweezer) are proper nouns and are never translated. The sentence around them translates; the name rides through verbatim.
- `{placeholder}` tokens must survive exactly as written. Move them anywhere the grammar needs, but do not translate or drop them.
- Plural keys (`.one`, `.other`, and friends) follow [CLDR plural categories](https://cldr.unicode.org/index/cldr-spec/plural-rules). Match the key families en.json has; the panel picks the right category for your language at runtime via `Intl.PluralRules`.
- The `vocab.*` section holds command-template and action labels. These become stored command names when a user accepts a template, and the backend auto-maps them back to actions, so avoid giving two different vocab keys the same translation.

Translations should come from or be reviewed by a native speaker who uses Home Assistant in that language. Assistant-drafted translations are welcome as a starting point if they are marked as such in the PR.

To check for layout overflow before a translation exists, generate the padded pseudo-locale and load it: `python custom_components/hair/tests/util_pseudo_locale.py` (instructions in that file's docstring).

## Updating llms.txt

HAIR ships an `llms.txt` file in the repo root that gives AI assistants and
crawlers a curated summary of the project. It must remain consistent with the
README and CHANGELOG.

When to update `llms.txt`:

- Any PR that modifies `README.md` and changes user-facing features, capabilities,
  supported hardware, configuration, or documentation structure
- Any PR that adds a new feature, ships a roadmap item, or changes platform support
- Any PR that adds new device types, supported IR protocols, or capture providers
- Any PR that changes the Home Assistant version requirement

Rules:

- `llms.txt` must follow the [llmstxt.org spec](https://llmstxt.org/): H1, blockquote
  summary, body sections, H2 link sections, optional Optional section
- No em-dashes in `llms.txt`. Use double-hyphens (`--`), parentheses, or separate
  sentences instead
- Keep the file under 200 lines
- Every claim must be verifiable against the README or CHANGELOG

Releases:

- The pre-release checklist requires verifying `llms.txt` reflects all changes in
  this release's CHANGELOG entries before tagging.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
