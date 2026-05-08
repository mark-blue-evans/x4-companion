from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QStyle

ICON_PATH = Path(__file__).parent / "data" / "icon.png"


class Tray(QSystemTrayIcon):
    quit_requested = Signal()

    def __init__(self, app: QApplication):
        if ICON_PATH.exists():
            icon = QIcon(str(ICON_PATH))
        else:
            icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        super().__init__(icon)
        self.setToolTip("X4 Companion")
        menu = QMenu()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.show()
