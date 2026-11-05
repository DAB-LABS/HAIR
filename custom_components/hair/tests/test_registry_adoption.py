"""A library decoder is used only after HAIR has adopted it.

The registry used to take the bundled library's class for a protocol the
moment it gained ``from_raw_timings``. Now it takes it only when the
protocol is on ``ADOPTED_UPSTREAM_DECODERS``; otherwise HAIR keeps its
own decoder. These tests stand a library decoder up where none exists
yet (a stub module in ``sys.modules``, so they run on every leg) and
check that it is ignored until listed.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from custom_components.hair import protocol_decode
from custom_components.hair.protocol_decode import (
    _REGISTRATIONS,
    ADOPTED_UPSTREAM_DECODERS,
    UPSTREAM_ADOPTED,
    UPSTREAM_NONE,
    UPSTREAM_NOT_ADOPTED,
    build_protocol_command,
    get_spec,
    held_back_upstream_decoders,
    registered_protocols,
    try_decode_identity,
)

ROOT_CONFTEST = Path(__file__).parents[3] / "conftest.py"

#: Protocols HAIR decodes itself that the library's draft decoders cover,
#: by registry key, upstream module and class.
LOCAL_WITH_UPSTREAM_PATH = [
    ("sony", "infrared_protocols.commands.sony", "SonyCommand"),
    ("rc6", "infrared_protocols.commands.rc6", "RC6Command"),
    ("samsung32", "infrared_protocols.commands.samsung", "Samsung32Command"),
    ("rc5", "infrared_protocols.commands.rc5", "RC5Command"),
]


@pytest.fixture(autouse=True)
def _fresh_registry():
    protocol_decode._reset_registry_for_tests()
    yield
    protocol_decode._reset_registry_for_tests()


def _install(monkeypatch, module_name: str, **classes) -> types.ModuleType:
    """Put a stub module, and any missing parent, into ``sys.modules``."""
    parts = module_name.split(".")
    for depth in range(1, len(parts)):
        parent = ".".join(parts[:depth])
        if parent not in sys.modules:
            monkeypatch.setitem(sys.modules, parent, types.ModuleType(parent))
    module = types.ModuleType(module_name)
    for name, cls in classes.items():
        setattr(module, name, cls)
    monkeypatch.setitem(sys.modules, module_name, module)
    return module


def _claims_everything(class_name: str) -> type:
    """A library class whose decoder accepts any capture at all."""

    class Greedy:
        def __init__(self, **fields):
            self.__dict__.update(fields)
            self.modulation = 38000
            self.repeat_count = 0

        @classmethod
        def from_raw_timings(cls, timings):
            return cls(address=0x1F, address_bits=5, command=0x7F,
                       toggle=0, mode=0, customer=None)

        def get_raw_timings(self):
            return [600, -600]

    Greedy.__name__ = class_name
    return Greedy


def _adopt(monkeypatch, *keys: str) -> None:
    monkeypatch.setattr(
        protocol_decode, "ADOPTED_UPSTREAM_DECODERS",
        ADOPTED_UPSTREAM_DECODERS | set(keys),
    )


def _sony_capture() -> list[int]:
    from custom_components.hair.decoders.sony import SonyCommand

    return SonyCommand(address=0x97, address_bits=8, command=0x27).get_raw_timings()


# ---------------------------------------------------------------------------
# 1. A library decoder appears
# ---------------------------------------------------------------------------


class TestALibraryDecoderAppears:
    @pytest.mark.parametrize("key,module,name", LOCAL_WITH_UPSTREAM_PATH)
    def test_it_is_not_used_until_listed(self, monkeypatch, key, module, name):
        stub = _claims_everything(name)
        _install(monkeypatch, module, **{name: stub})

        spec = next(s for s in protocol_decode._ensure_registry() if s.key == key)
        assert spec.command_cls is not stub
        assert spec.source == "local"
        assert spec.upstream_decoder == UPSTREAM_NOT_ADOPTED
        assert key in held_back_upstream_decoders()

    @pytest.mark.parametrize("key,module,name", LOCAL_WITH_UPSTREAM_PATH)
    def test_listing_it_switches(self, monkeypatch, key, module, name):
        stub = _claims_everything(name)
        _install(monkeypatch, module, **{name: stub})
        _adopt(monkeypatch, key)

        spec = next(s for s in protocol_decode._ensure_registry() if s.key == key)
        assert spec.command_cls is stub
        assert spec.source == "upstream"
        assert spec.upstream_decoder == UPSTREAM_ADOPTED
        assert key not in held_back_upstream_decoders()

    def test_held_back_sony_decodes_as_hair_does(self, monkeypatch):
        """The danger the list guards against, and that it is guarded."""
        _install(monkeypatch, "infrared_protocols.commands.sony",
                 SonyCommand=_claims_everything("SonyCommand"))
        assert try_decode_identity(_sony_capture()).fingerprint == (
            "SONY15:0x0097:0x27"
        )

    def test_adopted_greedy_sony_would_re_identify_stored_rows(self, monkeypatch):
        """Why adoption needs a parity check: listed, it takes over."""
        _install(monkeypatch, "infrared_protocols.commands.sony",
                 SonyCommand=_claims_everything("SonyCommand"))
        _adopt(monkeypatch, "sony")
        assert try_decode_identity(_sony_capture()).fingerprint != (
            "SONY15:0x0097:0x27"
        )

    def test_encode_follows_decode(self, monkeypatch):
        """A held-back protocol is rebuilt with the class that decoded it."""
        from custom_components.hair.decoders.sony import SonyCommand

        _install(monkeypatch, "infrared_protocols.commands.sony",
                 SonyCommand=_claims_everything("SonyCommand"))
        built = build_protocol_command("SONY15", 0x97, 0x27)
        assert type(built) is SonyCommand
        assert built.get_raw_timings() == _sony_capture()


class TestABaseClassDecoder:
    def test_a_from_raw_timings_on_the_base_class_switches_nothing(self, monkeypatch):
        """If the library's base Command grew the method, every class
        would look like a decoder. None of HAIR's protocols may move."""

        class Base:
            @classmethod
            def from_raw_timings(cls, timings):
                raise NotImplementedError

        for _key, module, name in LOCAL_WITH_UPSTREAM_PATH:
            _install(monkeypatch, module, **{name: type(name, (Base,), {})})

        listing = {row["protocol"]: row for row in registered_protocols()}
        for key, _module, _name in LOCAL_WITH_UPSTREAM_PATH:
            assert listing[key]["source"] == "local"
        assert try_decode_identity(_sony_capture()).fingerprint == (
            "SONY15:0x0097:0x27"
        )


# ---------------------------------------------------------------------------
# 2. The list
# ---------------------------------------------------------------------------


class TestTheList:
    def test_it_holds_nec_and_ge_ac(self):
        assert frozenset({"nec", "geac"}) == ADOPTED_UPSTREAM_DECODERS

    def test_every_upstream_only_registration_is_listed(self):
        """A protocol with no local decoder is only ever served by the
        library, so leaving it off the list would unregister it."""
        upstream_only = {
            key for key, upstream, _name, local, *_ in _REGISTRATIONS
            if upstream is not None and local is None
        }
        assert upstream_only <= ADOPTED_UPSTREAM_DECODERS

    def test_every_listed_key_is_registered_with_an_upstream_path(self):
        upstream_keys = {
            key for key, upstream, *_ in _REGISTRATIONS if upstream is not None
        }
        assert upstream_keys >= ADOPTED_UPSTREAM_DECODERS

    def test_unlisted_and_no_local_decoder_means_not_registered(self, monkeypatch):
        monkeypatch.setattr(
            protocol_decode, "ADOPTED_UPSTREAM_DECODERS", frozenset({"nec"})
        )
        _install(monkeypatch, "infrared_protocols.commands.general_electric",
                 GEACCommand=_claims_everything("GEACCommand"))
        assert get_spec("GEAC") is None

    def test_the_listed_ones_are_used_where_the_library_decodes(self, monkeypatch):
        _install(monkeypatch, "infrared_protocols.commands.general_electric",
                 GEACCommand=_claims_everything("GEACCommand"))
        spec = get_spec("GEAC")
        assert spec.source == "upstream"
        assert spec.upstream_decoder == UPSTREAM_ADOPTED


# ---------------------------------------------------------------------------
# 3. What this leg's library actually offers
# ---------------------------------------------------------------------------


class TestThisLeg:
    def test_every_row_says_what_the_library_offered(self):
        for row in registered_protocols():
            assert row["upstream_decoder"] in (
                UPSTREAM_ADOPTED, UPSTREAM_NOT_ADOPTED, UPSTREAM_NONE,
            ), row
            assert (row["source"] == "upstream") == (
                row["upstream_decoder"] == UPSTREAM_ADOPTED
            ), row

    def test_no_library_decoder_is_waiting_for_a_decision(self):
        """If this fails, the installed library has gained a decoder HAIR
        does not use. Nothing is broken: HAIR keeps its own. Run the
        parity census for that protocol and either list it in
        ADOPTED_UPSTREAM_DECODERS or record why not, then update this."""
        assert held_back_upstream_decoders() == []

    def test_the_run_summary_names_the_registry(self, request):
        hook = next(
            plugin for plugin in request.config.pluginmanager.get_plugins()
            if getattr(plugin, "__file__", None)
            and Path(plugin.__file__).resolve() == ROOT_CONFTEST.resolve()
        ).pytest_terminal_summary
        lines: list[str] = []
        hook(types.SimpleNamespace(write_line=lines.append))
        assert len(lines) == 1
        assert lines[0].startswith("HAIR registry: upstream ")
        assert lines[0].endswith("library decoders held back: none")
