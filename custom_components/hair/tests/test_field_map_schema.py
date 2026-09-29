"""Schema v0.5: every map must declare which frames carry settings.

`payload_frame` names the PRIMARY state block. It has been the only
statement a map could make about where its settings live, and it is
singular, so a consumer that reads it to decide which bytes decide what a
press does gets one frame and no warning that there might be another.
TCL112 is the family where that costs something real: its quiet flag sits
in frame 0, `silent` and `level1` differ in nothing else, and a
payload-frame-only identity hashes two different presses to one value.

`frame.setting_frames` is the statement. This file is what keeps it
honest, and it reads the YAML DOCUMENTS rather than the parsed maps on
purpose: `field_readers` normalizes a badly declared key so a bad map
never breaks a comb mid-run, which means the parsed object cannot fail
these assertions even when the document deserves to. The document is what
a deriver writes and what a reviewer reads, so the document is what gets
checked.

Nothing here decodes anything. It is a conformance test over a directory
of data files.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from custom_components.hair import field_readers as fr

MAPS_DIR = Path(fr.__file__).parent / "field_maps"


TIMING = {
    "classify": "space",
    "unit_mark_us": {"nominal": 500, "min": 300, "max": 700},
    "space_zero_us": {"nominal": 500, "min": 300, "max": 700},
    "space_one_us": {"nominal": 1600, "min": 701, "max": 2000},
    "header_mark_us": {"nominal": 4500, "min": 4000, "max": 5000},
    "header_space_us": {"nominal": 4500, "min": 4000, "max": 5000},
    "frame_gap_us": {"min": 8000},
}


def _documents() -> list[tuple[str, dict]]:
    out = []
    for path in sorted(MAPS_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(raw, dict), path.name
        out.append((path.name, raw))
    return out


DOCUMENTS = _documents()
IDS = [name for name, _ in DOCUMENTS]


def _frame(raw: dict) -> dict:
    frame = raw.get("frame")
    assert isinstance(frame, dict)
    return frame


class TestEveryMapDeclaresItsSettingFrames:
    """Declared, not defaulted.

    The key has a default of `[payload_frame]`, which is what keeps a
    v0.4 map readable. That default is for readers, not for authors: a
    map that has thought about which frames carry settings and a map that
    has not should not look the same on disk, and the superset check
    below has nothing to check on a map that stayed silent.
    """

    @pytest.mark.parametrize("name,raw", DOCUMENTS, ids=IDS)
    def test_the_key_is_present(self, name, raw):
        assert "setting_frames" in _frame(raw), name

    @pytest.mark.parametrize("name,raw", DOCUMENTS, ids=IDS)
    def test_it_is_a_list_of_ints(self, name, raw):
        declared = _frame(raw)["setting_frames"]
        assert isinstance(declared, list) and declared, name
        assert all(isinstance(index, int) for index in declared), name

    @pytest.mark.parametrize("name,raw", DOCUMENTS, ids=IDS)
    def test_the_payload_frame_comes_first(self, name, raw):
        """So a consumer that wants one frame still gets the right one."""
        frame = _frame(raw)
        assert frame["setting_frames"][0] == int(frame.get("payload_frame", 0) or 0), name

    @pytest.mark.parametrize("name,raw", DOCUMENTS, ids=IDS)
    def test_nothing_repeats(self, name, raw):
        declared = _frame(raw)["setting_frames"]
        assert len(set(declared)) == len(declared), name

    @pytest.mark.parametrize("name,raw", DOCUMENTS, ids=IDS)
    def test_every_index_names_a_real_frame(self, name, raw):
        frame = _frame(raw)
        layout = frame.get("frame_layout") or [frame.get("total_bits")]
        for index in frame["setting_frames"]:
            assert 0 <= index < len(layout), f"{name}: frame {index}"

    @pytest.mark.parametrize("name,raw", DOCUMENTS, ids=IDS)
    def test_it_covers_every_frame_a_field_names(self, name, raw):
        """The point of the key.

        `fields[].frame` has been per-field since v0.1, so a field can
        already sit anywhere. A field in a frame the map has not declared
        as setting-bearing is the exact bug this key exists to surface,
        and it is silent otherwise: the field is read correctly and every
        consumer that asked which frames matter was told the wrong thing.
        """
        declared = set(_frame(raw)["setting_frames"])
        used = {
            int(field.get("frame", 0) or 0)
            for field in (raw.get("fields") or [])
        }
        missing = sorted(used - declared)
        assert not missing, f"{name}: fields live in undeclared frames {missing}"


class TestTheReaderNormalizesWhatItIsGiven:
    """A bad document is salvaged rather than raising, and the salvage is
    defined rather than incidental, because `load_maps` promises that a
    bad map is skipped or repaired and never breaks a comb."""

    def _map(self, **frame_extra):
        raw = {
            "protocol_id": "TESTONLY",
            "frame": {
                "frame_layout": [16, 16, 16],
                "payload_frame": 1,
                "bit_order": "lsb_first",
                "timing": TIMING,
                **frame_extra,
            },
        }
        parsed = fr.parse_map(raw)
        assert parsed is not None
        return parsed

    def test_a_silent_map_gets_its_payload_frame(self):
        assert self._map().setting_frames == [1]

    def test_the_payload_frame_is_added_when_a_map_omits_it(self):
        assert self._map(setting_frames=[2]).setting_frames == [1, 2]

    def test_out_of_range_indices_are_dropped(self):
        assert self._map(setting_frames=[1, 9, 0]).setting_frames == [1, 0]

    def test_repeats_are_dropped(self):
        assert self._map(setting_frames=[1, 0, 1, 0]).setting_frames == [1, 0]

    def test_junk_is_dropped_rather_than_raising(self):
        assert self._map(setting_frames="frame one").setting_frames == [1]
        assert self._map(setting_frames=[None, "x", 0]).setting_frames == [1, 0]


class TestWhatTheKeyChangesForIdentification:
    """Behaviour-neutral on this directory, and that is an assertion
    rather than a hope.

    `_matches_repeat` is the one place a frame index decides whether a
    SHORT capture may be identified, and it now asks for every setting
    frame rather than for the payload frame alone. On every map here the
    two questions have the same answer: the only two maps whose settings
    span frames are TCL112 and GREE, neither declares a `frame_repeat`
    rule, and GREE's frames are 35 and 32 bits wide so it fails the
    equal-width test as well. Both short-capture paths were already
    closed, which is why this round changes no behaviour anywhere.
    """

    def test_which_maps_span_frames(self):
        """Pinned, because the answer was a surprise.

        TCL112 is the family the key was written for. GREE was found BY
        the conformance test above: it has carried its vane position in
        frame 1 with a payload frame of 0 since round two, and nothing
        could see that until a map had to state it.
        """
        spanning = {
            field_map.protocol_id: field_map.setting_frames
            for field_map in fr.load_maps()
            if len(field_map.setting_frames) > 1
        }
        assert spanning == {"GREE": [0, 1], "TCL112": [1, 0]}

    def test_no_map_that_spans_frames_also_claims_to_repeat(self):
        """The two claims contradict each other: a frame that repeats the
        payload carries nothing of its own. A map making both is wrong
        somewhere, and the reader takes the reading that does not licence
        dropping a frame."""
        for field_map in fr.load_maps():
            if len(field_map.setting_frames) > 1:
                assert not field_map.repeats_identically, field_map.protocol_id

    def test_the_repeat_guard_now_asks_about_every_setting_frame(self):
        """Constructed, because no shipped map has both shapes at once.

        Two frames of equal width, a ratified repeat rule, and a setting
        in the second frame: the capture that arrives holding only frame
        0 must NOT be identified, because the setting in frame 1 never
        came. Before v0.5 this returned True whenever the payload frame
        was present.
        """
        raw = {
            "protocol_id": "TESTONLY",
            "frame": {
                "frame_layout": [16, 16],
                "payload_frame": 0,
                "setting_frames": [0, 1],
                "bit_order": "lsb_first",
                "timing": TIMING,
            },
            "integrity": [{
                "type": "frame_repeat",
                "params": {"frame": 1, "equals": 0},
                "confidence": "ratified",
            }],
        }
        spanning = fr.parse_map(raw)
        assert spanning is not None
        assert not spanning.repeats_identically

        raw["frame"]["setting_frames"] = [0]
        plain = fr.parse_map(raw)
        assert plain is not None
        assert plain.repeats_identically
        assert fr._matches_repeat(plain, [[0] * 16])
