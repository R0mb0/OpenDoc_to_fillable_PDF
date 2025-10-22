# ui/preview.py
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QFont

class PreviewEditor(QTextEdit):
    """
    QTextEdit with debounced autosave signalling and simple API.
    Emits:
    - text_modified: whenever user modifies (immediate)
    - text_saved: when autosave completes
    """
    text_modified = pyqtSignal()
    text_saved = pyqtSignal()

    def __init__(self, parent=None, autosave_ms: int = 800):
        super().__init__(parent)
        self._autosave_ms = autosave_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_autosave)
        self.textChanged.connect(self._on_text_changed)
        self._current_save_callback = None  # callback to call on autosave (function(text))
        self.setFont(QFont("Arial", 12))
        self.setAcceptRichText(False)

    def _on_text_changed(self):
        self._timer.start(self._autosave_ms)
        self.text_modified.emit()

    def _on_autosave(self):
        if self._current_save_callback:
            try:
                self._current_save_callback(self.toPlainText())
                self.text_saved.emit()
            except Exception:
                pass

    def set_autosave_callback(self, cb):
        """
        cb: callable that receives a single argument (text: str) and performs save.
        """
        self._current_save_callback = cb

    def load_text(self, text: str):
        self.blockSignals(True)
        self.setPlainText(text)
        self.blockSignals(False)

    def force_save_now(self):
        # stop timer and save immediately
        if self._timer.isActive():
            self._timer.stop()
        if self._current_save_callback:
            try:
                self._current_save_callback(self.toPlainText())
                self.text_saved.emit()
            except Exception:
                pass