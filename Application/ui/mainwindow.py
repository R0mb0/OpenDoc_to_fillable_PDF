from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy, QFileDialog, QTableWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import json
import os

class ToggleSwitch(QPushButton):
    """
    Toggle implemented as a checkable QPushButton with custom QSS.
    Shows a short label for ON/OFF (text_on/text_off) and styled as rounded pill.
    """
    def __init__(self, checked=False, text_on="", text_off="", qss_path="assets/toggle_switch.qss", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.text_on = text_on
        self.text_off = text_off
        self.setObjectName("toggle_switch")
        self.setFixedSize(96, 34)
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self._qss = f.read()
                self.setStyleSheet(self._qss)
        except Exception:
            self._qss = ""
        self.setFont(QFont("Arial", 10, QFont.Bold))
        self.update_text()
        self.clicked.connect(self.update_text)

    def update_text(self):
        self.setText(self.text_on if self.isChecked() else self.text_off)


class MainWindow(QMainWindow):
    def __init__(self, labels, language, theme):
        super().__init__()
        self.labels = labels
        self.language = language
        self.theme = theme  # "light" or "dark"
        self.document_list = []
        self.current_index = 0
        self.setWindowTitle(self.labels.get("app_title", "Document Converter"))
        self.setMinimumSize(900, 600)
        self.setStyleSheet(self.get_stylesheet())
        self.init_ui()

    def get_stylesheet(self):
        qss_content = ""
        try:
            with open("assets/toggle_switch.qss", "r", encoding="utf-8") as f:
                qss_content = f.read()
        except Exception:
            qss_content = ""
        # Add some button-specific styles to avoid clipping and give consistent padding
        extra = """
        QPushButton { padding: 6px 10px; border-radius: 12px; }
        QPushButton#arrow_btn { min-width: 44px; min-height: 36px; padding: 0 6px; font-size: 14px; }
        QPushButton.tool-button { min-width: 140px; min-height: 40px; font-size: 13px; }
        QListWidget { border-radius: 8px; padding: 4px; }
        QLabel.preview-area { border-radius: 12px; padding: 16px; }
        """
        if self.theme == "dark":
            base = """
                QMainWindow { background-color: #21222e; }
                QPushButton { background-color: #333347; color: #fff; }
                QTableWidget { background-color: #28293d; color: #fff; }
                QLabel { color: #fff; }
            """
        else:
            base = """
                QMainWindow { background-color: #fafbfe; }
                QPushButton { background-color: #e2e8f0; color: #333; }
                QTableWidget { background-color: #f3f3fa; color: #333; }
                QLabel { color: #333; }
            """
        return base + extra + "\n" + qss_content

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout_main = QVBoxLayout()
        self.central_widget.setLayout(self.layout_main)
        self.init_top_bar()
        self.init_start_layout()

    def init_top_bar(self):
        # Sticky top bar for theme/language toggles (top-left)
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setAlignment(Qt.AlignLeft)

        self.lang_label_widget = QLabel(self.labels.get("language_label", "Lingua:"))
        self.lang_label_widget.setFont(QFont("Arial", 11))
        self.lang_toggle = ToggleSwitch(
            checked=(self.language == "en"),
            text_on="EN", text_off="IT"
        )
        self.lang_toggle.clicked.connect(self.toggle_language)

        self.theme_label_widget = QLabel(self.labels.get("theme_label", "Tema:"))
        self.theme_label_widget.setFont(QFont("Arial", 11))
        theme_on = self.labels.get("theme_on", "Scuro")
        theme_off = self.labels.get("theme_off", "Chiaro")
        self.theme_toggle = ToggleSwitch(
            checked=(self.theme == "dark"),
            text_on=theme_on,
            text_off=theme_off
        )
        self.theme_toggle.clicked.connect(self.toggle_theme)

        top_bar_layout.addWidget(self.lang_label_widget)
        top_bar_layout.addWidget(self.lang_toggle)
        top_bar_layout.addSpacing(12)
        top_bar_layout.addWidget(self.theme_label_widget)
        top_bar_layout.addWidget(self.theme_toggle)
        top_bar_layout.addStretch()

        self.layout_main.addLayout(top_bar_layout)

    def init_start_layout(self):
        # Central upload button only (toggles remain sticky up-left)
        self.start_layout = QVBoxLayout()
        self.upload_btn = QPushButton(self.labels.get("upload_btn", "Carica documenti"))
        self.upload_btn.setFont(QFont("Arial", 18))
        self.upload_btn.clicked.connect(self.upload_files)
        self.upload_btn.setFixedWidth(260)
        self.upload_btn.setFixedHeight(44)
        self.start_layout.addStretch()
        self.start_layout.addWidget(self.upload_btn, alignment=Qt.AlignCenter)
        self.start_layout.addStretch()
        self.layout_main.addLayout(self.start_layout)

    def show_app_layout_after_upload(self):
        # Remove start layout items (but keep top bar which is index 0)
        while self.layout_main.count() > 1:
            item = self.layout_main.takeAt(1)
            if item is None:
                break
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                for i in reversed(range(item.layout().count())):
                    w = item.layout().itemAt(i).widget()
                    if w:
                        w.setParent(None)

        # Three-column layout: Preview | Titolo | Tools + Document list
        layout_cols = QHBoxLayout()

        # Colonna 1: Anteprima con barre di navigazione
        col_preview = QVBoxLayout()
        preview_bar = QHBoxLayout()
        # Arrow buttons (bigger, better padding)
        self.prev_btn = QPushButton("<")
        self.prev_btn.setObjectName("arrow_btn")
        self.next_btn = QPushButton(">")
        self.next_btn.setObjectName("arrow_btn")
        self.prev_btn.setFixedSize(48, 36)
        self.next_btn.setFixedSize(48, 36)
        self.prev_btn.setFont(QFont("Arial", 14))
        self.next_btn.setFont(QFont("Arial", 14))
        self.prev_btn.clicked.connect(self.on_prev)
        self.next_btn.clicked.connect(self.on_next)
        self.page_indicator = QLabel("")
        self.page_indicator.setAlignment(Qt.AlignCenter)
        self.page_indicator.setFixedHeight(28)
        preview_bar.addWidget(self.prev_btn)
        preview_bar.addWidget(self.page_indicator, stretch=1)
        preview_bar.addWidget(self.next_btn)
        col_preview.addLayout(preview_bar)

        # Preview area (placeholder) — now expanding and large
        self.preview_area = QLabel(self.labels.get("preview_label", "Anteprima"))
        self.preview_area.setObjectName("preview_area")
        self.preview_area.setProperty("class", "preview-area")
        self.preview_area.setAlignment(Qt.AlignCenter)
        self.preview_area.setMinimumHeight(360)
        self.preview_area.setMinimumWidth(520)
        self.preview_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # subtle style to look like preview pane
        self.preview_area.setStyleSheet("""
            QLabel#preview_area { border-radius: 12px; background: rgba(255,255,255,0.02); padding: 16px; min-height: 360px; }
        """)
        col_preview.addWidget(self.preview_area)
        col_preview.addStretch()

        # Colonna 2: Titolo
        col_title = QVBoxLayout()
        title_label = QLabel(self.labels.get("title_label", "Titolo:"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.title_value = QLabel("")  # will show document title
        self.title_value.setFont(QFont("Arial", 14))
        col_title.addWidget(title_label)
        col_title.addWidget(self.title_value)
        col_title.addStretch()

        # Colonna 3: Pulsanti verticali + lista documenti (compatta)
        col_tools = QVBoxLayout()
        # Vertical buttons (placeholders) — bigger so text fits
        btn_keys = ["btn_interpret", "btn_compile", "btn_back", "btn_delete", "btn_save"]
        btn_labels = [ self.labels.get(k, k) for k in btn_keys ]
        self.tool_buttons = []
        for lbl in btn_labels:
            b = QPushButton(lbl)
            b.setObjectName("tool_button")
            b.setProperty("class", "tool-button")
            b.setFixedWidth(160)
            b.setFixedHeight(42)
            b.setFont(QFont("Arial", 12))
            # Placeholder: no connected action (demo)
            col_tools.addWidget(b)
            self.tool_buttons.append(b)
            col_tools.addSpacing(6)
        col_tools.addSpacing(10)
        # Document list under buttons: bigger and fixed width
        self.docs_listwidget = QListWidget()
        self.docs_listwidget.setFixedWidth(220)
        self.docs_listwidget.setMinimumHeight(220)
        self.docs_listwidget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.docs_listwidget.itemSelectionChanged.connect(self.on_doc_selection_changed)
        col_tools.addWidget(self.docs_listwidget)

        # Assemble columns into layout with good stretch factors
        layout_cols.addLayout(col_preview, 3)
        layout_cols.addLayout(col_title, 1)
        layout_cols.addLayout(col_tools, 1)
        self.layout_main.addLayout(layout_cols)

        # Initialize selection
        if self.document_list:
            self.populate_doc_list()
            self.set_selected_index(0)
        else:
            self.page_indicator.setText("0/0")
            self.title_value.setText("")

    def populate_doc_list(self):
        self.docs_listwidget.clear()
        for p in self.document_list:
            item = QListWidgetItem(os.path.basename(p))
            self.docs_listwidget.addItem(item)

    def set_selected_index(self, idx):
        if not self.document_list:
            return
        self.current_index = max(0, min(idx, len(self.document_list) - 1))
        # update UI: title, preview placeholder, selection in list
        basename = os.path.basename(self.document_list[self.current_index])
        self.title_value.setText(basename)
        self.preview_area.setText(f"{self.labels.get('preview_label','Anteprima')}\n\n{basename}")
        self.page_indicator.setText(f"{self.current_index + 1}/{len(self.document_list)}")
        # select item in listwidget
        if self.docs_listwidget.count() > self.current_index:
            self.docs_listwidget.setCurrentRow(self.current_index)

    def on_doc_selection_changed(self):
        row = self.docs_listwidget.currentRow()
        if row >= 0:
            self.set_selected_index(row)

    def on_prev(self):
        if self.document_list:
            self.set_selected_index((self.current_index - 1) % len(self.document_list))

    def on_next(self):
        if self.document_list:
            self.set_selected_index((self.current_index + 1) % len(self.document_list))

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.labels.get("upload_dialog", "Seleziona documenti ODT/ODS"), "", "Documents (*.odt *.ods)")
        if files:
            self.document_list = files
            # Hide central upload button as requested
            try:
                self.upload_btn.setParent(None)
            except Exception:
                pass
            # Show the app layout after upload
            self.show_app_layout_after_upload()

    def toggle_language(self):
        # Toggle IT/EN
        self.language = "en" if self.lang_toggle.isChecked() else "it"
        labels_file = f"lang/labels_{self.language}.json"
        try:
            with open(labels_file, encoding="utf-8") as f:
                self.labels = json.load(f)
        except Exception:
            with open("lang/labels_en.json", encoding="utf-8") as f:
                self.labels = json.load(f)

        # Update UI texts
        self.setWindowTitle(self.labels.get("app_title", "Document Converter"))
        # upload button text if it's still present
        if hasattr(self, "upload_btn") and self.upload_btn is not None:
            self.upload_btn.setText(self.labels.get("upload_btn", "Carica documenti"))

        # Update theme toggle labels if changed language
        theme_on = self.labels.get("theme_on", "Scuro")
        theme_off = self.labels.get("theme_off", "Chiaro")
        self.theme_toggle.text_on = theme_on
        self.theme_toggle.text_off = theme_off
        self.theme_toggle.update_text()

        # Update top bar labels
        self.lang_label_widget.setText(self.labels.get("language_label", "Lingua:"))
        self.theme_label_widget.setText(self.labels.get("theme_label", "Tema:"))

        # Update button labels and preview/title if layout present
        btn_keys = ["btn_interpret", "btn_compile", "btn_back", "btn_delete", "btn_save"]
        for i, btn in enumerate(getattr(self, "tool_buttons", [])):
            k = btn_keys[i] if i < len(btn_keys) else None
            if k:
                btn.setText(self.labels.get(k, btn.text()))

        if hasattr(self, "title_value") and self.document_list:
            # refresh title and preview texts if necessary
            self.set_selected_index(self.current_index)

    def toggle_theme(self):
        self.theme = "dark" if self.theme_toggle.isChecked() else "light"
        # Update style
        self.setStyleSheet(self.get_stylesheet())