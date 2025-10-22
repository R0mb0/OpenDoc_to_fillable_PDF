# ui/mainwindow.py
"""
Lightweight MainWindow that wires DocumentManager, Extractor and PreviewEditor.
This file is intentionally minimal and delegates behavior to modules under core/ and ui/.
Replace the previous monolithic mainwindow.py with this one and keep expanding modules independently.
"""
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QFrame, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import json
import os

from core.document_manager import DocumentManager
from core import extractor
from ui.preview import PreviewEditor
from ui.widgets import ToggleSwitch, StyledButton

class MainWindow(QMainWindow):
    def __init__(self, labels, language, theme):
        super().__init__()
        self.labels = labels
        self.language = language
        self.theme = theme
        self.setWindowTitle(self.labels.get("app_title", "Document Converter"))
        self.setMinimumSize(900, 600)

        # core components
        self.docmgr = DocumentManager(work_root="work")

        # UI components
        self._build_ui()

        # connect signals
        self.docmgr.documents_changed.connect(self.on_documents_changed)
        self.docmgr.current_changed.connect(self.on_current_changed)
        # preview autosave callback will use docmgr.save_editable_for_current
        self.preview.set_autosave_callback(self._on_preview_autosave)

    def _build_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout_main = QVBoxLayout()
        self.central_widget.setLayout(self.layout_main)

        # top bar: language + theme toggles
        top = QHBoxLayout()
        self.lang_label = QLabel(self.labels.get("language_label", "Lingua:"))
        self.lang_toggle = ToggleSwitch(text_on="EN", text_off="IT", checked=(self.language=="en"))
        self.theme_label = QLabel(self.labels.get("theme_label", "Tema:"))
        self.theme_toggle = ToggleSwitch(text_on=self.labels.get("theme_on","Scuro"), text_off=self.labels.get("theme_off","Chiaro"), checked=(self.theme=="dark"))
        top.addWidget(self.lang_label)
        top.addWidget(self.lang_toggle)
        top.addSpacing(12)
        top.addWidget(self.theme_label)
        top.addWidget(self.theme_toggle)
        top.addStretch()
        self.layout_main.addLayout(top)

        # start area with central upload button
        self.start_box = QVBoxLayout()
        self.upload_btn = StyledButton(self.labels.get("upload_btn","Carica documenti"))
        self.upload_btn.setFont(QFont("Arial", 18))
        self.upload_btn.setFixedWidth(240)
        self.upload_btn.clicked.connect(self.on_upload_clicked)
        self.start_box.addStretch()
        self.start_box.addWidget(self.upload_btn, alignment=Qt.AlignCenter)
        self.start_box.addStretch()
        self.layout_main.addLayout(self.start_box)

        # preview area (kept but initially hidden until upload)
        self.main_area = QHBoxLayout()
        # Preview column
        preview_col = QVBoxLayout()
        preview_bar = QHBoxLayout()
        self.prev_btn = StyledButton("<")
        self.next_btn = StyledButton(">")
        self.page_label = QLabel("")
        preview_bar.addWidget(self.prev_btn)
        preview_bar.addWidget(self.page_label, stretch=1)
        preview_bar.addWidget(self.next_btn)
        preview_col.addLayout(preview_bar)

        self.preview_frame = QFrame()
        self.preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_layout = QVBoxLayout()
        self.preview = PreviewEditor()
        preview_layout.addWidget(self.preview)
        self.preview_frame.setLayout(preview_layout)
        preview_col.addWidget(self.preview_frame)
        self.main_area.addLayout(preview_col, 3)

        # title column
        title_col = QVBoxLayout()
        self.title_label = QLabel(self.labels.get("title_label","Titolo:"))
        self.title_value = QLabel("")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.title_value)
        title_col.addStretch()
        self.main_area.addLayout(title_col, 1)

        # tools column
        tools_col = QVBoxLayout()
        # placeholder tool buttons
        keys = ["btn_interpret","btn_compile","btn_back","btn_delete","btn_save"]
        for k in keys:
            b = StyledButton(self.labels.get(k,k))
            tools_col.addWidget(b)
        tools_col.addStretch()
        self.main_area.addLayout(tools_col, 1)

        # main_area is hidden until upload; add it but keep invisible
        self.layout_main.addLayout(self.main_area)
        self._set_main_area_visible(False)

    def _set_main_area_visible(self, visible: bool):
        for i in range(self.main_area.count()):
            item = self.main_area.itemAt(i)
            if item.layout():
                item.widget = None
                for j in range(item.layout().count()):
                    w = item.layout().itemAt(j).widget()
                    if w:
                        w.setVisible(visible)
            else:
                w = item.widget()
                if w:
                    w.setVisible(visible)

    def on_upload_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.labels.get("upload_dialog","Seleziona documenti ODT/ODS"), "", "Documents (*.odt *.ods)")
        if files:
            # delegate to DocumentManager
            self.docmgr.load_files(files)
            # hide start area and show main layout
            try:
                # remove upload widgets
                while self.start_box.count():
                    it = self.start_box.takeAt(0)
                    if it and it.widget():
                        it.widget().setParent(None)
            except Exception:
                pass
            self._set_main_area_visible(True)

    def on_documents_changed(self, docs):
        # update UI list/indicators; for this minimal wiring we set title to first doc name
        if docs:
            self.title_value.setText(os.path.basename(docs[0]))
            self.page_label.setText("1/{}".format(len(docs)))

    def on_current_changed(self, idx):
        # load current document via extractor and/or editable.txt and set preview text
        path = self.docmgr.get_current_path()
        if not path:
            return
        # first try editable saved content
        loaded = self.docmgr.load_editable_for_current()
        if loaded:
            self.preview.load_text(loaded)
            return
        # else try extractor (odfpy or unzip fallback)
        extracted = extractor.extract_text_from_odt(path)
        if extracted:
            self.preview.load_text(extracted)
            # persist extracted as editable for later
            try:
                self.docmgr.save_editable_for_current(extracted)
            except Exception:
                pass
            return
        # fallback placeholder
        self.preview.load_text(self.labels.get("preview_label","Anteprima") + "\n\n" + os.path.basename(path))

    def _on_preview_autosave(self, text):
        # called by PreviewEditor autosave callback: persist via DocumentManager
        try:
            self.docmgr.save_editable_for_current(text)
        except Exception:
            pass