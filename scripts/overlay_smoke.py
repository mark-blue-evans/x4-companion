"""Manual smoke test for the overlay. Run on the Windows gaming PC."""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from x4_companion.overlay import Overlay

app = QApplication(sys.argv)
overlay = Overlay(fade_seconds=3)
overlay.show_text("hello — does this look right?")
QTimer.singleShot(5000, app.quit)
sys.exit(app.exec_())
