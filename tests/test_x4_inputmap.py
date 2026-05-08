from pathlib import Path

import pytest

from x4_companion.x4_inputmap import (
    _decode_keycode,
    _humanize_action_id,
    format_bindings_markdown,
    parse_inputmap,
)


@pytest.mark.parametrize(
    "code, expected",
    [
        ("INPUT_KEYCODE_M", "m"),
        ("INPUT_KEYCODE_1", "1"),
        ("INPUT_KEYCODE_RETURN", "enter"),
        ("INPUT_KEYCODE_RETURN_SHIFT", "shift+enter"),
        ("INPUT_KEYCODE_M_SHIFT", "shift+m"),
        ("INPUT_KEYCODE_E_SHIFT", "shift+e"),
        ("INPUT_KEYCODE_H_CONTROL", "ctrl+h"),
        ("INPUT_KEYCODE_F3", "f3"),
        ("INPUT_KEYCODE_TAB", "tab"),
        ("INPUT_KEYCODE_ESCAPE", "esc"),
        ("INPUT_KEYCODE_PRIOR", "page up"),
        ("INPUT_KEYCODE_NUMPAD4", "num 4"),
    ],
)
def test_decode_keycode(code, expected):
    assert _decode_keycode(code) == expected


@pytest.mark.parametrize(
    "code",
    ["INPUT_XBUTTON_22", "INPUT_KEYCODE_GIBBERISH", "garbage", ""],
)
def test_decode_keycode_unknown_returns_none(code):
    assert _decode_keycode(code) is None


def test_humanize_action_id():
    assert _humanize_action_id("INPUT_ACTION_OPEN_MAP") == "Open Map"
    assert _humanize_action_id("INPUT_ACTION_TOGGLE_TRAVEL_MODE") == "Toggle Travel Mode"
    assert _humanize_action_id("INPUT_STATE_BOOST") == "Boost"


def test_parse_inputmap_real_subset(tmp_path: Path):
    p = tmp_path / "inputmap.xml"
    p.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<inputmap version="185" id="102">
  <action id="INPUT_ACTION_OPEN_COCKPIT_MENU" source="INPUT_SOURCE_KEYBOARD" code="INPUT_KEYCODE_RETURN"/>
  <action id="INPUT_ACTION_OPEN_MAP" source="INPUT_SOURCE_KEYBOARD" code="INPUT_KEYCODE_M"/>
  <action id="INPUT_ACTION_OPEN_MAP" source="INPUT_SOURCE_COMPASSMENU" code="INPUT_COMPASSMENU_5"/>
  <action id="INPUT_ACTION_DOCK_ACTION" source="INPUT_SOURCE_KEYBOARD" code="INPUT_KEYCODE_D_SHIFT"/>
  <action id="INPUT_ACTION_DEPLOY_SATELLITE" source="INPUT_SOURCE_JOYBUTTONS" code="INPUT_XBUTTON_52"/>
  <state id="INPUT_STATE_BOOST" source="INPUT_SOURCE_KEYBOARD" code="INPUT_KEYCODE_TAB"/>
  <action id="INPUT_ACTION_TOGGLE_TRAVEL_MODE" source="INPUT_SOURCE_KEYBOARD" code="INPUT_KEYCODE_1_SHIFT"/>
  <action id="INPUT_ACTION_OPTIONSMENU" source="INPUT_SOURCE_KEYBOARD" code="INPUT_KEYCODE_DELETE"/>
  <action id="INPUT_ACTION_OPTIONSMENU" source="INPUT_SOURCE_KEYBOARD" code="INPUT_KEYCODE_ESCAPE"/>
  <action id="INPUT_ACTION_OPTIONSMENU" source="INPUT_SOURCE_KEYBOARD" code="INPUT_KEYCODE_O_SHIFT"/>
</inputmap>
""",
        encoding="utf-8",
    )
    bindings = parse_inputmap(p)
    assert bindings["INPUT_ACTION_OPEN_COCKPIT_MENU"] == "enter"
    assert bindings["INPUT_ACTION_OPEN_MAP"] == "m"
    assert bindings["INPUT_ACTION_DOCK_ACTION"] == "shift+d"
    assert bindings["INPUT_STATE_BOOST"] == "tab"
    assert bindings["INPUT_ACTION_TOGGLE_TRAVEL_MODE"] == "shift+1"
    # joybutton-only actions are skipped entirely
    assert "INPUT_ACTION_DEPLOY_SATELLITE" not in bindings
    # Multiple keyboard bindings -> shortest wins (esc is 3 chars, delete 6)
    assert bindings["INPUT_ACTION_OPTIONSMENU"] == "esc"


def test_parse_inputmap_empty_when_missing(tmp_path: Path):
    assert parse_inputmap(tmp_path / "missing.xml") == {}


def test_format_bindings_markdown():
    md = format_bindings_markdown(
        {
            "INPUT_ACTION_OPEN_MAP": "m",
            "INPUT_ACTION_OPEN_COCKPIT_MENU": "enter",
            "INPUT_STATE_BOOST": "tab",
        }
    )
    assert "- Boost — `tab`" in md
    assert "- Open Cockpit Menu — `enter`" in md
    assert "- Open Map — `m`" in md
