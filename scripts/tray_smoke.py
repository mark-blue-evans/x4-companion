"""Manual smoke test for the system tray. Run on the Windows gaming PC."""
import sys
from PySide6.QtWidgets import QApplication
from x4_companion.tray import Tray

app = QApplication(sys.argv)
tray = Tray(app)
tray.quit_requested.connect(app.quit)
sys.exit(app.exec_())
