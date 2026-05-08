from typing import Callable

class Hotkey:
    """Global push-to-talk hotkey. Suppresses OS auto-repeat while held."""

    def __init__(
        self,
        key: str,
        on_down: Callable[[], None],
        on_up: Callable[[], None],
    ):
        self._key = key
        self._on_down = on_down
        self._on_up = on_up
        self._pressed = False

    def start(self) -> None:
        import keyboard
        self._press_handle = keyboard.on_press_key(
            self._key, lambda _e: self._handle_down()
        )
        self._release_handle = keyboard.on_release_key(
            self._key, lambda _e: self._handle_up()
        )

    def stop(self) -> None:
        import keyboard
        for handle in (
            getattr(self, "_press_handle", None),
            getattr(self, "_release_handle", None),
        ):
            if handle is not None:
                try:
                    keyboard.unhook(handle)
                except Exception:
                    pass

    def _handle_down(self) -> None:
        if self._pressed:
            return
        self._pressed = True
        self._on_down()

    def _handle_up(self) -> None:
        if not self._pressed:
            return
        self._pressed = False
        self._on_up()
