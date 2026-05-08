from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

ICON_PATH = Path(__file__).parent / "data" / "icon.png"


class Tray(QSystemTrayIcon):
    quit_requested = Signal()
    brain_changed = Signal(str)

    def __init__(
        self,
        app: QApplication,
        brain_options: list[tuple[str, str]] | None = None,
        active_brain: str | None = None,
    ):
        if ICON_PATH.exists():
            icon = QIcon(str(ICON_PATH))
        else:
            icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        super().__init__(icon)
        self.setToolTip("X4 Companion")

        menu = QMenu()

        if brain_options:
            brain_menu = menu.addMenu("Brain")
            group = QActionGroup(menu)
            group.setExclusive(True)
            for key, label in brain_options:
                action = QAction(label, group)
                action.setCheckable(True)
                if key == active_brain:
                    action.setChecked(True)
                action.triggered.connect(
                    lambda _checked, k=key: self.brain_changed.emit(k)
                )
                brain_menu.addAction(action)
            menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.show()
