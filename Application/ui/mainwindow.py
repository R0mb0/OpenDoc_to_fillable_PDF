from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QFileDialog, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class MainWindow(QMainWindow):
    def __init__(self, labels, language):
        super().__init__()
        self.labels = labels
        self.language = language
        self.setWindowTitle(self.labels["app_title"])
        self.setMinimumSize(900, 600)
        self.setStyleSheet("""
            QPushButton { border-radius: 12px; padding: 8px 16px; font-size: 16px; }
            QTableWidget { border-radius: 10px; font-size: 15px; }
            QLabel { font-size: 18px; }
        """)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        # Colonna 1: area documento
        doc_area = QVBoxLayout()
        doc_label = QLabel(self.labels["doc_area"])
        doc_label.setAlignment(Qt.AlignCenter)
        doc_area.addWidget(doc_label)
        doc_area.addStretch()
        # Colonna 2: titolo documento
        title_area = QVBoxLayout()
        title_label = QLabel(self.labels["table_title"])
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_area.addWidget(title_label)
        title_area.addStretch()
        # Colonna 3: pulsanti verticali
        tools_area = QVBoxLayout()
        self.upload_btn = QPushButton(self.labels["upload_btn"])
        self.upload_btn.clicked.connect(self.upload_files)
        tools_area.addWidget(self.upload_btn)
        tools_area.addStretch()
        # Switch lingua
        self.lang_switch = QComboBox()
        self.lang_switch.addItems(["IT", "EN"])
        self.lang_switch.setCurrentIndex(0 if self.language == "it" else 1)
        self.lang_switch.currentIndexChanged.connect(self.switch_language)
        tools_area.addWidget(self.lang_switch)
        # Switch tema (placeholder)
        self.theme_switch = QPushButton(self.labels["theme_btn"])
        tools_area.addWidget(self.theme_switch)
        # Tabella multi-documento
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([self.labels["doc_col"], self.labels["status_col"]])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("background: #f3f3fa; border-radius: 10px;")
        # Layout finale
        main_layout.addLayout(doc_area, 2)
        main_layout.addLayout(title_area, 1)
        main_layout.addLayout(tools_area, 1)
        main_layout.addWidget(self.table, 3)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.labels["upload_dialog"], "", "Documents (*.odt *.ods)")
        for f in files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f.split("/")[-1]))
            self.table.setItem(row, 1, QTableWidgetItem(self.labels["status_placeholder"]))

    def switch_language(self, idx):
        lang = "it" if idx == 0 else "en"
        # In prototipo: Messaggio fittizio; in futuro, ricarica tutte le label e aggiorna UI
        self.language = lang
        self.setWindowTitle(self.labels["app_title"])