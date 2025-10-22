# ui/widgets.py
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class ToggleSwitch(QPushButton):
    """
    Simple toggle implemented with checkable QPushButton.
    Shows different text for on/off and sets pointing-hand cursor.
    """
    def __init__(self, text_on="ON", text_off="OFF", checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.text_on = text_on
        self.text_off = text_off
        self.setText(self.text_on if checked else self.text_off)
        self.clicked.connect(self._on_toggle)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Arial", 10))

    def _on_toggle(self):
        self.setText(self.text_on if self.isChecked() else self.text_off)

class StyledButton(QPushButton):
    """
    Button wrapper that sets pointing-hand cursor and a default font.
    """
    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Arial", 13))