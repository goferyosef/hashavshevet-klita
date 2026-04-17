STYLESHEET = """
QMainWindow, QDialog {
    background-color: #F5F7FA;
}

QTabWidget::pane {
    border: 1px solid #D0D7E2;
    background: #FFFFFF;
    border-radius: 6px;
}

QTabBar::tab {
    background: #E8EDF5;
    color: #3A4A6B;
    padding: 8px 20px;
    font-size: 13px;
    font-family: Arial;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #1F4E79;
    color: #FFFFFF;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background: #C9D8EE;
}

QPushButton {
    background-color: #1F4E79;
    color: white;
    border: none;
    padding: 7px 18px;
    border-radius: 5px;
    font-size: 13px;
    font-family: Arial;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #2E6DA4;
}

QPushButton:pressed {
    background-color: #163A5F;
}

QPushButton:disabled {
    background-color: #A0B4C8;
}

QPushButton#btn_danger {
    background-color: #C0392B;
}
QPushButton#btn_danger:hover {
    background-color: #E74C3C;
}

QPushButton#btn_success {
    background-color: #1E8449;
}
QPushButton#btn_success:hover {
    background-color: #27AE60;
}

QPushButton#btn_secondary {
    background-color: #7F8C8D;
}
QPushButton#btn_secondary:hover {
    background-color: #95A5A6;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    border: 1px solid #BDC3C7;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    font-family: Arial;
    background: #FFFFFF;
    color: #2C3E50;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #2E6DA4;
}

QLabel {
    font-size: 13px;
    font-family: Arial;
    color: #2C3E50;
}

QLabel#section_title {
    font-size: 15px;
    font-weight: bold;
    color: #1F4E79;
}

QTableWidget {
    border: 1px solid #D0D7E2;
    gridline-color: #E8EDF5;
    font-size: 12px;
    font-family: Arial;
    selection-background-color: #D6E8F7;
    selection-color: #1F4E79;
}

QHeaderView::section {
    background-color: #1F4E79;
    color: white;
    padding: 6px;
    font-weight: bold;
    font-family: Arial;
    border: none;
}

QTextEdit {
    border: 1px solid #D0D7E2;
    border-radius: 4px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    background: #1C2833;
    color: #E8F8F5;
    padding: 6px;
}

QProgressBar {
    border: 1px solid #BDC3C7;
    border-radius: 4px;
    text-align: center;
    font-size: 11px;
    color: #2C3E50;
}

QProgressBar::chunk {
    background-color: #1F4E79;
    border-radius: 3px;
}

QCheckBox {
    font-size: 13px;
    font-family: Arial;
    color: #2C3E50;
    spacing: 6px;
}

QGroupBox {
    border: 1px solid #D0D7E2;
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px;
    font-size: 13px;
    font-family: Arial;
    color: #1F4E79;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 6px;
}
"""
