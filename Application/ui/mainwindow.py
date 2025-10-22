from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QFileDialog
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
        # Slightly larger to match central button's rounded look
        self.setFixedSize(96, 34)
        # Load QSS for styling if available
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self._qss = f.read()
                # apply to the widget (also main stylesheet includes this file)
                # we still set it so the widget renders properly standalone
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
        self.setWindowTitle(self.labels.get("app_title", "Document Converter"))
        self.setMinimumSize(900, 600)
        self.setStyleSheet(self.get_stylesheet())
        self.init_ui()

    def get_stylesheet(self):
        # Include toggle qss content (if file exists) in returned string so toggles render nicely
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

        # Keep the label widgets as attributes so they can be updated reliably
        self.lang_label_widget = QLabel(self.labels.get("language_label", "Lingua:"))
        self.lang_label_widget.setFont(QFont("Arial", 11))
        # Language toggle shows IT or EN
        self.lang_toggle = ToggleSwitch(
            checked=(self.language == "en"),
            text_on="EN", text_off="IT"
        )
        self.lang_toggle.clicked.connect(self.toggle_language)

        self.theme_label_widget = QLabel(self.labels.get("theme_label", "Tema:"))
        self.theme_label_widget.setFont(QFont("Arial", 11))
        # Theme toggle uses distinct on/off text from labels (theme_on/theme_off)
        theme_on = self.labels.get("theme_on", "Scuro")
        theme_off = self.labels.get("theme_off", "Chiaro")
        self.theme_toggle = ToggleSwitch(
            checked=(self.theme == "dark"),
            text_on=theme_on,
            text_off=theme_off
        )
        self.theme_toggle.clicked.connect(self.toggle_theme)

        # Add widgets to top bar
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

    def show_table_layout(self):
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

        # Table layout (three columns + table)
        layout_cols = QHBoxLayout()
        # Colonna 1: area documento (placeholder)
        col_doc = QVBoxLayout()
        doc_label = QLabel(self.labels.get("doc_area", "Area Documento"))
        doc_label.setAlignment(Qt.AlignCenter)
        col_doc.addWidget(doc_label)
        col_doc.addStretch()

        # Colonna 2: titolo documento
        col_title = QVBoxLayout()
        title_label = QLabel(self.labels.get("table_title", "Documenti Caricati"))
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        col_title.addWidget(title_label)
        col_title.addStretch()

        # Colonna 3: pulsanti (upload rimane disponibile)
        col_tools = QVBoxLayout()
        col_tools.addWidget(self.upload_btn)
        col_tools.addStretch()

        # Tabella multi-documento
        self.table = QTableWidget(len(self.document_list), 2)
        self.table.setHorizontalHeaderLabels([self.labels.get("doc_col", "Documento"), self.labels.get("status_col", "Stato")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        for row, f in enumerate(self.document_list):
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(f)))
            self.table.setItem(row, 1, QTableWidgetItem(self.labels.get("status_placeholder", "In attesa")))

        # Layout finale
        layout_cols.addLayout(col_doc, 2)
        layout_cols.addLayout(col_title, 1)
        layout_cols.addLayout(col_tools, 1)
        layout_cols.addWidget(self.table, 3)
        self.layout_main.addLayout(layout_cols)

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.labels.get("upload_dialog", "Seleziona documenti ODT/ODS"), "", "Documents (*.odt *.ods)")
        if files:
            self.document_list = files
            self.show_table_layout()

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
        self.upload_btn.setText(self.labels.get("upload_btn", "Carica documenti"))

        # Update theme toggle labels if changed language
        theme_on = self.labels.get("theme_on", "Scuro")
        theme_off = self.labels.get("theme_off", "Chiaro")
        self.theme_toggle.text_on = theme_on
        self.theme_toggle.text_off = theme_off
        self.theme_toggle.update_text()

        # Update labels on top bar
        self.lang_label_widget.setText(self.labels.get("language_label", "Lingua:"))
        self.theme_label_widget.setText(self.labels.get("theme_label", "Tema:"))

        # Update table headers / placeholders if table exists
        if hasattr(self, "table"):
            self.table.setHorizontalHeaderLabels([self.labels.get("doc_col", "Documento"), self.labels.get("status_col", "Stato")])
            for row in range(self.table.rowCount()):
                self.table.setItem(row, 1, QTableWidgetItem(self.labels.get("status_placeholder", "In attesa")))

    def toggle_theme(self):
        self.theme = "dark" if self.theme_toggle.isChecked() else "light"
        # Update style
        self.setStyleSheet(self.get_stylesheet())