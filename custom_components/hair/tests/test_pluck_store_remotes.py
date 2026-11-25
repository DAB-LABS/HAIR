"""Plucker: "+ Pluck signal" is only for remotes that can replay by name.

Plucking a signal replays one command by name through a remote's vendor
entity and appliance. A blaster made on the Plucker tab has both. A
remote read from a learned-code store (Broadlink, Tuya Local,
OpenIRBlaster) has neither, so the button used to open, find no vendor
integration for the remote and say "This blaster's integration is not
available right now", which blames the wrong thing.

What is pinned here:

- the panel offers "+ Pluck signal" only on a remote with
  ``source == "plucked"``, a vendor entity and an appliance
  (``canPluckByName``), run under node where the toolchain is present
  and read as text everywhere;
- the server refuses a plucked signal onto a store remote with a plain
  reason and adds nothing, while a blaster still takes one.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from .test_learned_store_pluck import (
    _import,
    _monitor,
    store_dir,  # noqa: F401  (fixture)
)

FRONTEND = Path(__file__).parent.parent / "frontend"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

_PRONTO = "0000 006D 0002 0000 0010 0010 0010 0010"


class TestTheServer:
    async def test_a_store_remote_refuses_a_plucked_signal(
        self, fake_hass, store_dir  # noqa: F811
    ):
        monitor, store = _monitor(fake_hass)
        await _import(monitor, store_dir, "tuya_local", "IR Remote Garage")
        remote = next(
            d for d in store.get_all_devices() if d.store_subdevice == "test_remote"
        )
        before = len(remote.signals)

        result = await monitor.create_plucked_signal(remote.id, _PRONTO, "x")

        assert result["success"] is False
        assert result["code"] == "store_remote"
        assert "learned-code store" in result["error"]
        assert "not available" not in result["error"]
        assert len(store.get_device(remote.id).signals) == before

    async def test_a_blaster_still_takes_one(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        blaster = await monitor.create_plucked_blaster(
            "remote.ir_remote_garage", "candles", "Candles"
        )
        result = await monitor.create_plucked_signal(blaster.id, _PRONTO, "on")
        assert result["success"] is True
        assert len(store.get_device(blaster.id).signals) == 1


class TestThePanelAsText:
    """CI runs without node_modules, so the gate is also read as text."""

    def test_the_button_renders_only_behind_the_rule(self):
        src = (FRONTEND / "src" / "ir-pluck.ts").read_text(encoding="utf-8")
        start = src.index("private _renderExpanded(")
        block = src[start:src.index("no-signals-row", start)]
        gate = block.index("canPluckByName(device)")
        assert gate < block.index('t("pluck.pluck_signal")')
        assert block.count("create-signal-btn") == 1

    def test_the_rule_lives_in_api_ts(self):
        src = (FRONTEND / "src" / "api.ts").read_text(encoding="utf-8")
        assert "export function canPluckByName(" in src


DRIVER = """
import { canPluckByName } from "./api.js";

console.log(JSON.stringify({
    blaster: canPluckByName({
        source: "plucked", vendor_entity_id: "remote.x", appliance: "candles",
    }),
    store_remote: canPluckByName({
        source: "plucked", vendor_entity_id: null, appliance: null,
    }),
    no_appliance: canPluckByName({
        source: "plucked", vendor_entity_id: "remote.x", appliance: "",
    }),
    sniffed: canPluckByName({
        source: "sniffed", vendor_entity_id: "remote.x", appliance: "candles",
    }),
    nullish: canPluckByName(null),
}));
"""


@pytest.fixture(scope="module")
def rule(tmp_path_factory):
    if not TSC.exists() or shutil.which("node") is None:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("pluckname")
    subprocess.run(
        [
            str(TSC), "src/api.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


class TestTheRule:
    def test_a_blaster_can(self, rule):
        assert rule["blaster"] is True

    def test_a_store_remote_cannot(self, rule):
        assert rule["store_remote"] is False

    def test_it_needs_the_appliance_too(self, rule):
        assert rule["no_appliance"] is False

    def test_only_plucked_remotes(self, rule):
        assert rule["sniffed"] is False
        assert rule["nullish"] is False
