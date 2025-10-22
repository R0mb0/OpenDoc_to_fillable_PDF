from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QTableWidgetItem, QHeaderView, QFileDialog,
    QTableWidget
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
        if self.theme == "dark":
            base = """
                QMainWindow { background-color: #21222e; }
                QPushButton { background-color: #333347; color: #fff; border-radius: 12px; padding: 8px 16px; font-size: 16px; }
                QTableWidget { background-color: #28293d; color: #fff; border-radius: 10px; font-size: 15px; }
                QLabel { color: #fff; font-size: 18px; }
                QHeaderView::section { background-color: #333347; color: #fff; }
            """
        else:
            base = """
                QMainWindow { background-color: #fafbfe; }
                QPushButton { background-color: #e2e8f0; color: #333; border-radius: 12px; padding: 8px 16px; font-size: 16px; }
                QTableWidget { background-color: #f3f3fa; color: #333; border-radius: 10px; font-size: 15px; }
                QLabel { color: #333; font-size: 18px; }
                QHeaderView::section { background-color: #e2e8f0; color: #333; }
            """
        return base + "\n" + qss_content

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
        self.upload_btn.setFixedHeight(40)
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
        self.prev_btn = QPushButton("<")
        self.next_btn = QPushButton(">")
        self.prev_btn.setFixedSize(36, 28)
        self.next_btn.setFixedSize(36, 28)
        self.prev_btn.clicked.connect(self.on_prev)
        self.next_btn.clicked.connect(self.on_next)
        self.page_indicator = QLabel("")
        self.page_indicator.setAlignment(Qt.AlignCenter)
        preview_bar.addWidget(self.prev_btn)
        preview_bar.addWidget(self.page_indicator)
        preview_bar.addWidget(self.next_btn)
        col_preview.addLayout(preview_bar)

        # Preview area (placeholder)
        self.preview_area = QLabel(self.labels.get("preview_label", "Anteprima"))
        self.preview_area.setAlignment(Qt.AlignCenter)
        self.preview_area.setStyleSheet("""
            QLabel { border-radius: 10px; background: rgba(255,255,255,0.03); padding: 12px; min-height: 360px; }
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
        # Vertical buttons (placeholders)
        btn_labels = [
            self.labels.get("btn_interpret", "Interpreta"),
            self.labels.get("btn_compile", "Compila"),
            self.labels.get("btn_back", "Torna indietro"),
            self.labels.get("btn_delete", "Cancella"),
            self.labels.get("btn_save", "Salva")
        ]
        self.tool_buttons = []
        for lbl in btn_labels:
            b = QPushButton(lbl)
            b.setFixedWidth(120)
            b.setFixedHeight(36)
            # Placeholder: no connected action (demo)
            col_tools.addWidget(b)
            self.tool_buttons.append(b)
        col_tools.addStretch()
        # Document list under buttons: compact selection list
        self.docs_listwidget = QListWidget()
        self.docs_listwidget.setMaximumWidth(260)
        self.docs_listwidget.itemSelectionChanged.connect(self.on_doc_selection_changed)
        col_tools.addWidget(self.docs_listwidget)

        # Assemble columns into layout
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

        # Update preview/title/button labels if layout present
        if hasattr(self, "title_value"):
            # update title label text
            # (the label widget showing the static "Titolo:" is not stored, but value updated)
            pass
        # Update button labels
        for i, btn in enumerate(getattr(self, "tool_buttons", [])):
            # map via keys order: btn_interpret, btn_compile, btn_back, btn_delete, btn_save
            key_map = ["btn_interpret", "btn_compile", "btn_back", "btn_delete", "btn_save"]
            k = key_map[i] if i < len(key_map) else None
            if k:
                btn.setText(self.labels.get(k, btn.text()))

    def toggle_theme(self):
        self.theme = "dark" if self.theme_toggle.isChecked() else "light"
        # Update style
        self.setStyleSheet(self.get_stylesheet())