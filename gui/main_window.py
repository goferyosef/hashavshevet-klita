import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QTabWidget

from gui.config_tab    import ConfigTab
from gui.suppliers_tab import SuppliersTab
from gui.run_tab        import RunTab
from gui.reports_tab   import ReportsTab

ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("קליטה לחשבשבת")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumSize(960, 680)
        self.resize(1100, 740)

        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.config_tab    = ConfigTab()
        self.suppliers_tab = SuppliersTab()
        self.run_tab       = RunTab(self.config_tab, self.suppliers_tab)
        self.reports_tab   = ReportsTab()

        self.tabs.addTab(self.run_tab,       "▶  הרצה")
        self.tabs.addTab(self.suppliers_tab, "👥  ספקים")
        self.tabs.addTab(self.config_tab,    "⚙  הגדרות")
        self.tabs.addTab(self.reports_tab,   "📊  דוחות")
