from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QFileDialog, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import json
import os

class MainWindow(QMainWindow):
    def __init__(self, labels, language):
        super().__init__()
        self.labels = labels
        self.language = language
        self.theme = "light"
        self.files_loaded = False
        self.document_list = []
        self.setWindowTitle(self.labels["app_title"])
        self.setMinimumSize(900, 600)
        self.setStyleSheet(self.get_stylesheet())
        self.init_ui()

    def get_stylesheet(self):
        if self.theme == "dark":
            return """
                QMainWindow { background-color: #21222e; }
                QPushButton { background-color: #333347; color: #fff; border-radius: 12px; padding: 8px 16px; font-size: 16px; }
                QTableWidget { background-color: #28293d; color: #fff; border-radius: 10px; font-size: 15px; }
                QLabel { color: #fff; font-size: 18px; }
                QHeaderView::section { background-color: #333347; color: #fff; }
            """
        else:
            return """
                QMainWindow { background-color: #fafbfe; }
                QPushButton { background-color: #e2e8f0; color: #333; border-radius: 12px; padding: 8px 16px; font-size: 16px; }
                QTableWidget { background-color: #f3f3fa; color: #333; border-radius: 10px; font-size: 15px; }
                QLabel { color: #333; font-size: 18px; }
                QHeaderView::section { background-color: #e2e8f0; color: #333; }
            """

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout_main = QVBoxLayout()
        self.central_widget.setLayout(self.layout_main)
        self.init_start_layout()

    def init_start_layout(self):
        # Clear layout
        for i in reversed(range(self.layout_main.count())):
            widget = self.layout_main.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Central upload button
        self.upload_btn = QPushButton(self.labels["upload_btn"])
        self.upload_btn.setFont(QFont("Arial", 18))
        self.upload_btn.clicked.connect(self.upload_files)
        self.upload_btn.setFixedWidth(260)
        self.upload_btn.setFixedHeight(40)
        # Toggles language and theme
        toggles_layout = QHBoxLayout()
        self.lang_toggle = QCheckBox("IT/EN")
        self.lang_toggle.setChecked(self.language == "en")
        self.lang_toggle.stateChanged.connect(self.toggle_language)
        self.theme_toggle = QCheckBox(self.labels["theme_btn"])
        self.theme_toggle.setChecked(False)
        self.theme_toggle.stateChanged.connect(self.toggle_theme)
        toggles_layout.addWidget(QLabel("Lingua:"))
        toggles_layout.addWidget(self.lang_toggle)
        toggles_layout.addWidget(QLabel("Tema:"))
        toggles_layout.addWidget(self.theme_toggle)
        toggles_layout.addStretch()
        # Layout
        self.layout_main.addStretch()
        self.layout_main.addWidget(self.upload_btn, alignment=Qt.AlignCenter)
        self.layout_main.addLayout(toggles_layout)
        self.layout_main.addStretch()

    def show_table_layout(self):
        # Clear layout
        for i in reversed(range(self.layout_main.count())):
            widget = self.layout_main.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Layout a tre colonne
        layout_cols = QHBoxLayout()
        # Colonna 1: area documento (placeholder)
        col_doc = QVBoxLayout()
        doc_label = QLabel(self.labels["doc_area"])
        doc_label.setAlignment(Qt.AlignCenter)
        col_doc.addWidget(doc_label)
        col_doc.addStretch()
        # Colonna 2: titolo documento
        col_title = QVBoxLayout()
        title_label = QLabel(self.labels["table_title"])
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        col_title.addWidget(title_label)
        col_title.addStretch()
        # Colonna 3: pulsanti (solo upload e toggle sempre visibili)
        col_tools = QVBoxLayout()
        col_tools.addWidget(self.upload_btn)
        col_tools.addWidget(QLabel("Lingua:"))
        col_tools.addWidget(self.lang_toggle)
        col_tools.addWidget(QLabel("Tema:"))
        col_tools.addWidget(self.theme_toggle)
        col_tools.addStretch()
        # Tabella multi-documento
        self.table = QTableWidget(len(self.document_list), 2)
        self.table.setHorizontalHeaderLabels([self.labels["doc_col"], self.labels["status_col"]])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        for row, f in enumerate(self.document_list):
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(f)))
            self.table.setItem(row, 1, QTableWidgetItem(self.labels["status_placeholder"]))
        # Layout finale
        layout_cols.addLayout(col_doc, 2)
        layout_cols.addLayout(col_title, 1)
        layout_cols.addLayout(col_tools, 1)
        layout_cols.addWidget(self.table, 3)
        self.layout_main.addLayout(layout_cols)

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.labels["upload_dialog"], "", "Documents (*.odt *.ods)")
        if files:
            self.document_list = files
            self.show_table_layout()

    def toggle_language(self, state):
        # Toggle IT/EN
        self.language = "en" if state == 2 else "it"
        labels_file = f"lang/labels_{self.language}.json"
        try:
            with open(labels_file, encoding="utf-8") as f:
                self.labels = json.load(f)
        except Exception:
            with open("lang/labels_en.json", encoding="utf-8") as f:
                self.labels = json.load(f)
        self.setWindowTitle(self.labels["app_title"])
        self.upload_btn.setText(self.labels["upload_btn"])
        self.theme_toggle.setText(self.labels["theme_btn"])
        if hasattr(self, "table"):
            self.table.setHorizontalHeaderLabels([self.labels["doc_col"], self.labels["status_col"]])
            for row in range(self.table.rowCount()):
                self.table.setItem(row, 1, QTableWidgetItem(self.labels["status_placeholder"]))

    def toggle_theme(self, state):
        # Toggle chiaro/scuro
        self.theme = "dark" if state == 2 else "light"
        self.setStyleSheet(self.get_stylesheet())