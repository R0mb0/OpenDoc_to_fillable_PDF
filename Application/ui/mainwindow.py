from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import json
import os

class ToggleSwitch(QPushButton):
    # Custom toggle-switch widget (Material/iOS style)
    def __init__(self, checked=False, text_on="", text_off="", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.text_on = text_on
        self.text_off = text_off
        self.update_text()
        self.setFixedSize(60, 28)
        self.setStyleSheet(open("assets/toggle_switch.qss").read())
        self.clicked.connect(self.update_text)

    def update_text(self):
        self.setText(self.text_on if self.isChecked() else self.text_off)

class MainWindow(QMainWindow):
    def __init__(self, labels, language, theme):
        super().__init__()
        self.labels = labels
        self.language = language
        self.theme = theme
        self.document_list = []
        self.setWindowTitle(self.labels["app_title"])
        self.setMinimumSize(900, 600)
        self.setStyleSheet(self.get_stylesheet())
        self.init_ui()

    def get_stylesheet(self):
        # Apply additional QSS for toggle-switch
        qss_toggle = open("assets/toggle_switch.qss").read()
        if self.theme == "dark":
            return f"""
                QMainWindow {{ background-color: #21222e; }}
                QPushButton {{ background-color: #333347; color: #fff; border-radius: 12px; padding: 8px 16px; font-size: 16px; }}
                QTableWidget {{ background-color: #28293d; color: #fff; border-radius: 10px; font-size: 15px; }}
                QLabel {{ color: #fff; font-size: 18px; }}
                QHeaderView::section {{ background-color: #333347; color: #fff; }}
            {qss_toggle}
            """
        else:
            return f"""
                QMainWindow {{ background-color: #fafbfe; }}
                QPushButton {{ background-color: #e2e8f0; color: #333; border-radius: 12px; padding: 8px 16px; font-size: 16px; }}
                QTableWidget {{ background-color: #f3f3fa; color: #333; border-radius: 10px; font-size: 15px; }}
                QLabel {{ color: #333; font-size: 18px; }}
                QHeaderView::section {{ background-color: #e2e8f0; color: #333; }}
            {qss_toggle}
            """

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout_main = QVBoxLayout()
        self.central_widget.setLayout(self.layout_main)
        self.init_top_bar()
        self.init_start_layout()

    def init_top_bar(self):
        # Sticky top bar for theme/language toggles
        self.top_bar = QHBoxLayout()
        self.top_bar.setAlignment(Qt.AlignLeft)
        self.lang_toggle = ToggleSwitch(
            checked=(self.language == "en"),
            text_on="EN", text_off="IT"
        )
        self.lang_toggle.clicked.connect(self.toggle_language)
        self.theme_toggle = ToggleSwitch(
            checked=(self.theme == "dark"),
            text_on=self.labels["theme_toggle"], text_off=self.labels["theme_btn"]
        )
        self.theme_toggle.clicked.connect(self.toggle_theme)
        self.top_bar.addWidget(QLabel(self.labels["language_label"]))
        self.top_bar.addWidget(self.lang_toggle)
        self.top_bar.addSpacing(16)
        self.top_bar.addWidget(QLabel(self.labels["theme_label"]))
        self.top_bar.addWidget(self.theme_toggle)
        self.top_bar.addStretch()
        self.layout_main.addLayout(self.top_bar)

    def init_start_layout(self):
        # Central upload button only
        self.start_layout = QVBoxLayout()
        self.upload_btn = QPushButton(self.labels["upload_btn"])
        self.upload_btn.setFont(QFont("Arial", 18))
        self.upload_btn.clicked.connect(self.upload_files)
        self.upload_btn.setFixedWidth(260)
        self.upload_btn.setFixedHeight(40)
        self.start_layout.addStretch()
        self.start_layout.addWidget(self.upload_btn, alignment=Qt.AlignCenter)
        self.start_layout.addStretch()
        self.layout_main.addLayout(self.start_layout)

    def show_table_layout(self):
        # Remove start layout
        while self.layout_main.count() > 1:
            layout_item = self.layout_main.takeAt(1)
            if layout_item.layout():
                for i in reversed(range(layout_item.layout().count())):
                    w = layout_item.layout().itemAt(i).widget()
                    if w: w.setParent(None)
        # Table layout
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
        # Colonna 3: pulsanti
        col_tools = QVBoxLayout()
        col_tools.addWidget(self.upload_btn)
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

    def toggle_language(self):
        self.language = "en" if self.lang_toggle.isChecked() else "it"
        labels_file = f"lang/labels_{self.language}.json"
        try:
            with open(labels_file, encoding="utf-8") as f:
                self.labels = json.load(f)
        except Exception:
            with open("lang/labels_en.json", encoding="utf-8") as f:
                self.labels = json.load(f)
        self.setWindowTitle(self.labels["app_title"])
        self.upload_btn.setText(self.labels["upload_btn"])
        self.theme_toggle.text_on = self.labels["theme_toggle"]
        self.theme_toggle.text_off = self.labels["theme_btn"]
        self.theme_toggle.update_text()
        if hasattr(self, "table"):
            self.table.setHorizontalHeaderLabels([self.labels["doc_col"], self.labels["status_col"]])
            for row in range(self.table.rowCount()):
                self.table.setItem(row, 1, QTableWidgetItem(self.labels["status_placeholder"]))
        # Aggiorna i label sulla barra
        self.top_bar.itemAt(0).widget().setText(self.labels["language_label"])
        self.top_bar.itemAt(3).widget().setText(self.labels["theme_label"])

    def toggle_theme(self):
        self.theme = "dark" if self.theme_toggle.isChecked() else "light"
        self.setStyleSheet(self.get_stylesheet())