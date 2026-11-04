# CI constraints: one file per Home Assistant release

HAIR declares no infrared-protocols requirement in its manifest. At
runtime every install uses the version its Home Assistant release pins
in the `infrared` component. CI tests those exact versions, one leg per
file here, passed to pip with `-c`:

| Leg | File | Home Assistant | infrared-protocols |
|---|---|---|---|
| floor | `ha-2026.6.txt` | 2026.6, the oldest supported (`hacs.json`) | 5.6.1 |
| current | `ha-2026.10.txt` | 2026.10, the latest stable | 10.1.0 |
| next | `ha-next.txt` | core's dev branch, allowed to fail | 10.6.0 |

Each pin is read from `homeassistant/components/infrared/manifest.json`
at that release's tag. Each leg runs the Python version that release
requires (`requires-python` in core's `pyproject.toml`): 3.14 for every
release since 2026.4. No Home Assistant release runs on Python 3.13, so
no leg does.

When Home Assistant ships a stable release, the current leg moves to it
(rename the file to its version and update the pin) and next moves to
the new dev or beta pin. The floor moves with `hacs.json`, which
`docs/stability.md` says the release notes announce one release ahead.
