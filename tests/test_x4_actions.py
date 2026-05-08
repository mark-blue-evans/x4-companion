import pytest

from x4_companion.brain import ProposedAction
from x4_companion.x4_actions import (
    execute_action,
    is_safe_key,
    is_x4_foreground,
)


@pytest.mark.parametrize(
    "key",
    [
        "1", "m", "tab", "enter", "shift+1", "ctrl+s", "alt+f1",
        "F4",  # F4 alone is fine, only Alt+F4 is dangerous
        "page up", "Home", "right",
    ],
)
def test_safe_keys_pass(key):
    assert is_safe_key(key) is True


@pytest.mark.parametrize(
    "key",
    [
        "alt+f4", "ALT+F4", "ctrl+alt+del", "win+r", "windows+l",
        "ctrl+shift+esc", "super+1", "fn+f1",
        "",  # empty
        "asdfsomeunknownkey",
    ],
)
def test_unsafe_keys_blocked(key):
    assert is_safe_key(key) is False


def test_execute_action_refuses_unsafe_keys(monkeypatch):
    monkeypatch.setattr(
        "x4_companion.x4_actions.is_x4_foreground", lambda: True
    )
    action = ProposedAction(name="Bad", keys=("alt+f4",), explanation="don't")
    ok, msg = execute_action(action)
    assert ok is False
    assert "unsafe" in msg.lower()


def test_execute_action_refuses_when_x4_not_foreground(monkeypatch):
    monkeypatch.setattr(
        "x4_companion.x4_actions.is_x4_foreground", lambda: False
    )
    action = ProposedAction(name="Open Map", keys=("m",))
    ok, msg = execute_action(action)
    assert ok is False
    assert "foreground" in msg.lower()


def test_execute_action_dry_run_does_not_press(monkeypatch):
    monkeypatch.setattr(
        "x4_companion.x4_actions.is_x4_foreground", lambda: True
    )
    pressed: list[str] = []

    def fake_press_and_release(key):
        pressed.append(key)

    fake_keyboard = type("kb", (), {"press_and_release": staticmethod(fake_press_and_release)})
    monkeypatch.setattr("builtins.__import__", lambda name, *a, **kw: fake_keyboard if name == "keyboard" else __import__(name, *a, **kw))

    action = ProposedAction(name="Open Map", keys=("m",))
    ok, msg = execute_action(action, dry_run=True)
    assert ok is True
    assert "dry-run" in msg
    assert pressed == []


def test_execute_action_presses_keys_when_safe_and_foreground(monkeypatch):
    pressed: list[str] = []

    class _FakeKeyboard:
        @staticmethod
        def press_and_release(key):
            pressed.append(key)

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, *a, **kw):
        if name == "keyboard":
            return _FakeKeyboard
        return real_import(name, *a, **kw)

    import builtins
    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(
        "x4_companion.x4_actions.is_x4_foreground", lambda: True
    )
    monkeypatch.setattr(
        "x4_companion.x4_actions.time.sleep", lambda _s: None
    )

    action = ProposedAction(name="Deploy sat", keys=("shift+1", "1"))
    ok, msg = execute_action(action)
    assert ok is True, msg
    assert pressed == ["shift+1", "1"]
