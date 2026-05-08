from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QApplication

class Overlay(QLabel):
    """Transparent always-on-top text panel that fades after `fade_seconds`."""

    def __init__(
        self,
        position: str = "top-right",
        opacity: float = 0.85,
        font_size: int = 16,
        fade_seconds: int = 30,
    ):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet(
            "QLabel {"
            "  background-color: rgba(0, 0, 0, 200);"
            "  color: white;"
            "  padding: 12px 16px;"
            "  border-radius: 8px;"
            f"  font-size: {font_size}px;"
            "}"
        )
        self.setWindowOpacity(opacity)
        self.setWordWrap(True)
        self.setMaximumWidth(420)
        self._position = position
        self._fade_seconds = fade_seconds
        self._fade_timer = QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self.hide)

    def show_text(self, text: str) -> None:
        self.setText(text)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._fade_timer.start(self._fade_seconds * 1000)

    def _reposition(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        margin = 24
        if self._position == "top-right":
            x = screen.right() - self.width() - margin
            y = screen.top() + margin
        elif self._position == "top-left":
            x = screen.left() + margin
            y = screen.top() + margin
        elif self._position == "bottom-left":
            x = screen.left() + margin
            y = screen.bottom() - self.height() - margin
        else:
            x = screen.right() - self.width() - margin
            y = screen.bottom() - self.height() - margin
        self.move(x, y)
