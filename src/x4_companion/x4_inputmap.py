"""Parse X4 Foundations' inputmap.xml to extract real keyboard bindings.

X4 stores per-user input maps at:
    %USERPROFILE%\\Documents\\Egosoft\\X4\\<numeric-id>\\inputmap.xml

The XML lists each <action> / <state> id alongside one or more <source, code>
pairs. We only care about INPUT_SOURCE_KEYBOARD entries. The code values are
constants like INPUT_KEYCODE_M, INPUT_KEYCODE_RETURN_SHIFT, etc.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

KEYCODE_NAMES: dict[str, str] = {
    "ESCAPE": "esc",
    "RETURN": "enter",
    "DELETE": "delete",
    "TAB": "tab",
    "SPACE": "space",
    "BACK": "backspace",
    "LEFT": "left",
    "RIGHT": "right",
    "UP": "up",
    "DOWN": "down",
    "PRIOR": "page up",
    "NEXT": "page down",
    "HOME": "home",
    "END": "end",
    "ADD": "+",
    "SUBTRACT": "-",
    "DECIMAL": ".",
    "MULTIPLY": "*",
    "DIVIDE": "/",
    "INSERT": "insert",
}
for _i in range(1, 13):
    KEYCODE_NAMES[f"F{_i}"] = f"f{_i}"
for _i in range(10):
    KEYCODE_NAMES[f"NUMPAD{_i}"] = f"num {_i}"

_MOD_SUFFIXES = (
    ("_SHIFT", "shift"),
    ("_CONTROL", "ctrl"),
    ("_ALT", "alt"),
)


def _decode_keycode(code: str) -> str | None:
    if not code.startswith("INPUT_KEYCODE_"):
        return None
    rest = code[len("INPUT_KEYCODE_") :]
    mods: list[str] = []
    while True:
        matched = False
        for suffix, name in _MOD_SUFFIXES:
            if rest.endswith(suffix):
                mods.insert(0, name)
                rest = rest[: -len(suffix)]
                matched = True
                break
        if not matched:
            break
    base: str | None = None
    if rest in KEYCODE_NAMES:
        base = KEYCODE_NAMES[rest]
    elif len(rest) == 1 and (rest.isalpha() or rest.isdigit()):
        base = rest.lower()
    if base is None:
        return None
    if mods:
        return "+".join(mods) + "+" + base
    return base


def find_user_inputmap() -> Path | None:
    """Return the most likely path to the user's X4 inputmap.xml, or None."""
    base = Path.home() / "Documents" / "Egosoft" / "X4"
    if not base.exists():
        return None
    candidates: list[Path] = []
    for child in base.iterdir():
        if not child.is_dir():
            continue
        inputmap = child / "inputmap.xml"
        if inputmap.exists():
            candidates.append(inputmap)
    if not candidates:
        return None
    # Prefer the most recently modified profile
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def parse_inputmap(path: Path) -> dict[str, str]:
    """Return {INPUT_ACTION_XYZ: "keyboard combo"} for keyboard-only entries.

    If an action has multiple keyboard bindings we keep the simplest (shortest
    combo, breaking ties alphabetically) so the model has a single canonical
    key per action.
    """
    if not path.exists():
        return {}
    try:
        tree = ET.parse(str(path))
    except ET.ParseError:
        return {}
    candidates: dict[str, list[str]] = {}
    for elem in tree.getroot().iter():
        if elem.tag not in {"action", "state"}:
            continue
        if elem.get("source") != "INPUT_SOURCE_KEYBOARD":
            continue
        action_id = elem.get("id")
        code = elem.get("code")
        if not action_id or not code:
            continue
        decoded = _decode_keycode(code)
        if decoded is None:
            continue
        candidates.setdefault(action_id, []).append(decoded)

    bindings: dict[str, str] = {}
    for action, combos in candidates.items():
        combos.sort(key=lambda c: (len(c), c))
        bindings[action] = combos[0]
    return bindings


_HUMAN_PREFIXES = ("INPUT_ACTION_", "INPUT_STATE_")


def _humanize_action_id(action_id: str) -> str:
    rest = action_id
    for p in _HUMAN_PREFIXES:
        if rest.startswith(p):
            rest = rest[len(p) :]
            break
    return rest.replace("_", " ").title()


def format_bindings_markdown(bindings: dict[str, str]) -> str:
    """Render the bindings as a markdown bullet list for the system prompt."""
    if not bindings:
        return ""
    items = [(_humanize_action_id(aid), aid, key) for aid, key in bindings.items()]
    items.sort(key=lambda t: t[0])
    lines = ["- " + name + " — `" + key + "`" for name, _aid, key in items]
    return "\n".join(lines)


# Curated user-facing phrasings the model should map to specific X4 actions.
# Each tuple: (action_id, list of natural-language synonyms the user might say).
ACTION_SYNONYMS: list[tuple[str, list[str]]] = [
    ("INPUT_ACTION_OPEN_COCKPIT_MENU", [
        "open ship menu", "open pilot menu", "open cockpit menu",
        "ship menu", "pilot menu", "cockpit menu", "open the menu",
    ]),
    ("INPUT_ACTION_OPEN_MAP", [
        "open map", "open sector map", "show map", "the map",
    ]),
    ("INPUT_ACTION_OPEN_PROPERTY_MENU", [
        "open property", "property menu", "my property", "open my property",
    ]),
    ("INPUT_ACTION_OPEN_PLAYER_INVENTORY_MENU", [
        "open inventory", "open player inventory", "my inventory",
    ]),
    ("INPUT_ACTION_OPEN_DIPLOMACY_MENU", ["diplomacy", "open diplomacy"]),
    ("INPUT_ACTION_OPTIONSMENU", [
        "options", "settings", "open settings", "open options",
        "open game menu",
    ]),
    ("INPUT_ACTION_SAVEGAMEMENU", ["save", "save game", "save the game"]),
    ("INPUT_ACTION_LOADGAMEMENU", ["load", "load game"]),
    ("INPUT_ACTION_QUITGAMEMENU", ["quit", "exit to menu"]),
    ("INPUT_STATE_BOOST", ["boost", "speed boost", "fast forward briefly"]),
    ("INPUT_ACTION_TOGGLE_TRAVEL_MODE", [
        "travel mode", "engage travel", "go fast", "cruise",
    ]),
    ("INPUT_ACTION_TOGGLE_SCAN_MODE", [
        "scan mode", "scanner mode", "toggle scan",
    ]),
    ("INPUT_ACTION_TOGGLE_LONGRANGE_SCAN_MODE", [
        "long range scan", "lrs", "long range scanner",
    ]),
    ("INPUT_ACTION_SCAN_ACTION", ["scan", "scan target", "use scanner"]),
    ("INPUT_ACTION_DOCK_ACTION", [
        "dock", "dock with target", "fly through gate",
    ]),
    ("INPUT_ACTION_UNDOCK", ["undock", "depart"]),
    ("INPUT_ACTION_TOGGLE_AUTOPILOT", [
        "autopilot", "engage autopilot", "auto fly", "auto-pilot",
    ]),
    ("INPUT_ACTION_TARGET_NEXT_TARGET", ["target next", "next target", "cycle target"]),
    ("INPUT_ACTION_TARGET_NEXT_ENEMY", ["target enemy", "lock enemy", "next enemy"]),
    ("INPUT_ACTION_TARGET_VIEW", ["target view", "view target"]),
    ("INPUT_ACTION_COCKPIT_VIEW", ["cockpit view", "view cockpit", "first person view"]),
    ("INPUT_ACTION_TOGGLECOCKPIT", ["toggle cockpit", "hide cockpit", "show cockpit"]),
    ("INPUT_ACTION_PAUSE", ["pause", "pause game"]),
]


def format_synonym_table(bindings: dict[str, str]) -> str:
    """Render a 'natural-language → keyboard key' table from the user's actual
    bindings. Skips synonyms whose action has no keyboard binding (e.g.,
    DEPLOY_SATELLITE which is joystick-only by default)."""
    if not bindings:
        return ""
    lines: list[str] = []
    for action_id, synonyms in ACTION_SYNONYMS:
        key = bindings.get(action_id)
        if not key:
            continue
        joined = " / ".join(f'"{s}"' for s in synonyms)
        lines.append(f"- {joined} → `{key}`")
    return "\n".join(lines)
