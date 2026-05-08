"""Safety + execution layer for keyboard actions in X4 Foundations."""
from __future__ import annotations

import time

from .brain import ProposedAction

SAFE_MODIFIERS: frozenset[str] = frozenset({"shift", "ctrl", "alt"})
SAFE_SINGLE_KEYS: frozenset[str] = frozenset(
    set("abcdefghijklmnopqrstuvwxyz0123456789")
    | {
        "tab", "enter", "space", "esc", "escape", "backspace", "delete",
        "up", "down", "left", "right",
        "home", "end", "page up", "page down", "pageup", "pagedown",
        "f1", "f2", "f3", "f4", "f5", "f6",
        "f7", "f8", "f9", "f10", "f11", "f12",
        "comma", "period", "minus", "plus", "equal",
        "/", ".", ",", "-", "=", ";", "'",
    }
)


def _normalize(key: str) -> str:
    return key.lower().strip().replace(" ", "")


def is_safe_key(key: str) -> bool:
    """A combo is safe if it uses only allowlisted modifiers + a known single key.

    Blocks Win key, Alt+F4, Ctrl+Alt+Del, Ctrl+Shift+Esc — anything that could
    destabilize the OS, kill the game, or open the Windows shell unexpectedly.
    """
    n = _normalize(key)
    if not n:
        return False
    if "win" in n or "windows" in n:
        return False
    if n in {"alt+f4", "ctrl+alt+del", "ctrl+alt+delete", "ctrl+shift+esc", "ctrl+shift+escape"}:
        return False
    parts = n.split("+")
    last = parts[-1]
    mods = parts[:-1]
    if any(m not in SAFE_MODIFIERS for m in mods):
        return False
    return last in SAFE_SINGLE_KEYS


def is_x4_foreground() -> bool:
    """True if the active foreground window is X4 Foundations."""
    try:
        import pygetwindow as gw

        win = gw.getActiveWindow()
    except Exception:
        return False
    if win is None:
        return False
    title = (getattr(win, "title", "") or "").lower()
    return "x4" in title or "foundations" in title


def execute_action(
    action: ProposedAction,
    *,
    dry_run: bool = False,
    require_x4_foreground: bool = True,
    inter_key_delay: float = 0.06,
) -> tuple[bool, str]:
    """Press the action's keys. Returns (success, message)."""
    bad = [k for k in action.keys if not is_safe_key(k)]
    if bad:
        return False, f"refused unsafe key(s): {bad}"
    if require_x4_foreground and not is_x4_foreground():
        return False, "X4 is not the foreground window"
    if dry_run:
        return True, f"dry-run: would press {list(action.keys)}"
    try:
        import keyboard
    except Exception as e:
        return False, f"keyboard module unavailable: {e}"
    for k in action.keys:
        keyboard.press_and_release(_normalize(k))
        time.sleep(inter_key_delay)
    return True, f"pressed {list(action.keys)}"
