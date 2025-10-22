# Application/ui/mainwindow.py
"""
MainWindow snella che si appoggia sui moduli core/ e ui/.
Ora applica un stylesheet basato sul tema (dark/light) e carica l'asset toggle_switch.qss.
Gestione toggle lingua/tema: i toggle sono collegati a toggle_language/toggle_theme
che aggiornano l'interfaccia al volo.
"""
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QFrame, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import json
import os
import logging
from pathlib import Path

from core.document_manager import DocumentManager
from core import extractor
from ui.preview import PreviewEditor
from ui.widgets import ToggleSwitch, StyledButton

logger = logging.getLogger("docconv")

class MainWindow(QMainWindow):
    def __init__(self, labels, language, theme):
        super().__init__()
        self.labels = labels
        self.language = language
        self.theme = theme
        self.setWindowTitle(self.labels.get("app_title", "Document Converter"))
        self.setMinimumSize(900, 600)

        # core components
        # keep work path under Application/work for consistency
        app_base = Path(__file__).resolve().parent.parent
        self.app_base = app_base
        self.assets_dir = app_base / "assets"
        self.lang_dir = app_base / "lang"
        self.docmgr = DocumentManager(work_root=str(app_base / "work"))

        # UI components
        self._build_ui()

        # connect signals
        self.docmgr.documents_changed.connect(self.on_documents_changed)
        self.docmgr.current_changed.connect(self.on_current_changed)
        # preview autosave callback will use docmgr.save_editable_for_current
        self.preview.set_autosave_callback(self._on_preview_autosave)

        # Ensure theme toggle texts reflect labels (if any)
        theme_on = self.labels.get("theme_on", "Scuro")
        theme_off = self.labels.get("theme_off", "Chiaro")
        self.theme_toggle.text_on = theme_on
        self.theme_toggle.text_off = theme_off
        self.theme_toggle.setText(self.theme_toggle.text_on if self.theme_toggle.isChecked() else self.theme_toggle.text_off)

        # Apply theme stylesheet
        try:
            self.apply_theme(self.theme)
            logger.info("Applied theme: %s", self.theme)
        except Exception:
            logger.exception("Failed to apply theme")

        logger.info("MainWindow initialized")

    def _build_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout_main = QVBoxLayout()
        self.central_widget.setLayout(self.layout_main)

        # top bar: language + theme toggles
        top = QHBoxLayout()
        self.lang_label = QLabel(self.labels.get("language_label", "Lingua:"))
        self.lang_label.setFont(QFont("Arial", 11))
        # lang toggle shows EN / IT (checked == EN)
        self.lang_toggle = ToggleSwitch(text_on="EN", text_off="IT", checked=(self.language=="en"))
        self.lang_toggle.clicked.connect(self.toggle_language)

        self.theme_label = QLabel(self.labels.get("theme_label", "Tema:"))
        self.theme_label.setFont(QFont("Arial", 11))
        self.theme_toggle = ToggleSwitch(
            text_on=self.labels.get("theme_on","Scuro"),
            text_off=self.labels.get("theme_off","Chiaro"),
            checked=(self.theme=="dark")
        )
        self.theme_toggle.clicked.connect(self.toggle_theme)

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

        # ensure navigation buttons are hidden until documents exist
        self.prev_btn.setVisible(False)
        self.next_btn.setVisible(False)

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
        # placeholder tool buttons (store references for language updates)
        keys = ["btn_interpret","btn_compile","btn_back","btn_delete","btn_save"]
        self.tool_buttons = []
        for k in keys:
            b = StyledButton(self.labels.get(k,k))
            tools_col.addWidget(b)
            self.tool_buttons.append((k, b))
        tools_col.addStretch()
        self.main_area.addLayout(tools_col, 1)

        # main_area is hidden until upload; add it but keep invisible
        self.layout_main.addLayout(self.main_area)
        self._set_main_area_visible(False)

    def _set_layout_visible_recursive(self, layout, visible: bool):
        """
        Recursively set visibility for all widgets inside a layout.
        This ensures nested layouts' widgets (like prev/next inside preview_bar)
        are also hidden/shown.
        """
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            # if the item is a layout, recurse
            child_layout = item.layout()
            if child_layout:
                self._set_layout_visible_recursive(child_layout, visible)
            else:
                w = item.widget()
                if w:
                    w.setVisible(visible)

    def _set_main_area_visible(self, visible: bool):
        # set visibility recursively for layouts inside main_area
        for i in range(self.main_area.count()):
            item = self.main_area.itemAt(i)
            if item is None:
                continue
            if item.layout():
                self._set_layout_visible_recursive(item.layout(), visible)
            else:
                w = item.widget()
                if w:
                    w.setVisible(visible)

    def apply_theme(self, theme: str):
        """
        Apply stylesheet for 'dark' or 'light'.
        Reads toggle qss from assets and composes a base stylesheet.
        """
        qss_content = ""
        try:
            qss_file = self.assets_dir / "toggle_switch.qss"
            if qss_file.exists():
                qss_content = qss_file.read_text(encoding="utf-8")
        except Exception:
            logger.exception("Failed reading toggle qss")

        if theme == "dark":
            base = """
                QMainWindow { background-color: #21222e; color: #fff; }
                QPushButton { background-color: #333347; color: #fff; border-radius: 12px; padding: 8px 16px; }
                QTextEdit { background-color: #f8f8fa; color: #111; border-radius: 8px; }
                QLabel { color: #fff; }
                QPushButton:hover { background-color: #3f4050; }
            """
        else:
            base = """
                QMainWindow { background-color: #fafbfe; color: #111; }
                QPushButton { background-color: #e2e8f0; color: #333; border-radius: 12px; padding: 8px 16px; }
                QTextEdit { background-color: #ffffff; color: #111; border-radius: 8px; }
                QLabel { color: #333; }
                QPushButton:hover { background-color: #edf2f7; }
            """
        full = base + "\n" + qss_content
        # apply to the window (could also apply to QApplication if desired)
        self.setStyleSheet(full)

    def load_labels_from_disk(self, language: str):
        """
        Load labels JSON from Application/lang and return dict.
        Fallback to labels_en.json if missing.
        """
        try:
            lf = self.lang_dir / f"labels_{language}.json"
            if not lf.exists():
                lf = self.lang_dir / "labels_en.json"
            return json.loads(lf.read_text(encoding="utf-8"))
        except Exception as e:
            logger.exception("Failed to load labels for language %s: %s", language, e)
            return {}

    def toggle_language(self):
        """
        Called when the lang toggle is clicked.
        Updates self.language, reloads labels, and refreshes UI texts.
        """
        # ToggleSwitch is checked==EN in our convention
        self.language = "en" if self.lang_toggle.isChecked() else "it"
        new_labels = self.load_labels_from_disk(self.language)
        if not new_labels:
            logger.warning("No labels found for language %s", self.language)
            return
        self.labels = new_labels
        # Update top labels and buttons
        self.lang_label.setText(self.labels.get("language_label", "Lingua:"))
        self.theme_label.setText(self.labels.get("theme_label", "Tema:"))
        if hasattr(self, "upload_btn") and self.upload_btn:
            self.upload_btn.setText(self.labels.get("upload_btn", "Carica documenti"))
        # Update tool button texts
        for key, btn in getattr(self, "tool_buttons", []):
            btn.setText(self.labels.get(key, btn.text()))
        # Update theme toggle texts if labels changed
        theme_on = self.labels.get("theme_on", "Scuro")
        theme_off = self.labels.get("theme_off", "Chiaro")
        self.theme_toggle.text_on = theme_on
        self.theme_toggle.text_off = theme_off
        # refresh displayed text on theme toggle according to its checked state
        try:
            self.theme_toggle.setText(self.theme_toggle.text_on if self.theme_toggle.isChecked() else self.theme_toggle.text_off)
        except Exception:
            pass
        # Update title label text (static)
        self.title_label.setText(self.labels.get("title_label", "Titolo:"))

    def toggle_theme(self):
        """
        Called when the theme toggle is clicked.
        Reads the toggle checked state and applies the selected theme.
        """
        self.theme = "dark" if self.theme_toggle.isChecked() else "light"
        try:
            self.apply_theme(self.theme)
            logger.info("Theme switched to %s via toggle", self.theme)
        except Exception:
            logger.exception("Failed to apply theme on toggle")

    def on_upload_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.labels.get("upload_dialog","Seleziona documenti ODT/ODS"), "", "Documents (*.odt *.ods)")
        if files:
            logger.info("User selected %d files", len(files))
            # delegate to DocumentManager
            self.docmgr.load_files(files)
            # hide start area and show main layout
            try:
                while self.start_box.count():
                    it = self.start_box.takeAt(0)
                    if it and it.widget():
                        it.widget().setParent(None)
            except Exception:
                logger.exception("Error while removing start widgets")
            # show main area (this will also show nested widgets via recursive helper)
            self._set_main_area_visible(True)

    def on_documents_changed(self, docs):
        # update UI list/indicators; for this minimal wiring we set title to first doc name
        if docs:
            self.title_value.setText(os.path.basename(docs[0]))
            self.page_label.setText("1/{}".format(len(docs)))
            logger.debug("Documents changed: %d entries", len(docs))
            # navigation buttons make sense only when documents exist: show/enable them
            self.prev_btn.setVisible(True)
            self.next_btn.setVisible(True)

    def on_current_changed(self, idx):
        # load current document via extractor and/or editable.txt and set preview text
        path = self.docmgr.get_current_path()
        if not path:
            return
        # first try editable saved content
        loaded = self.docmgr.load_editable_for_current()
        if loaded:
            logger.debug("Loaded editable content for index %d (len=%d)", idx, len(loaded))
            self.preview.load_text(loaded)
            return
        # else try extractor (odfpy or unzip fallback)
        extracted = extractor.extract_text_from_odt(path)
        if extracted:
            logger.info("Extracted text (len=%d) for %s", len(extracted), path)
            self.preview.load_text(extracted)
            # persist extracted as editable for later
            try:
                self.docmgr.save_editable_for_current(extracted)
            except Exception:
                logger.exception("Failed to persist extracted text")
            return
        # fallback placeholder
        self.preview.load_text(self.labels.get("preview_label","Anteprima") + "\n\n" + os.path.basename(path))
        logger.warning("No extracted content, showing placeholder for %s", path)

    def _on_preview_autosave(self, text):
        # called by PreviewEditor autosave callback: persist via DocumentManager
        try:
            ok = self.docmgr.save_editable_for_current(text)
            if ok:
                logger.debug("Autosaved editable for current doc (len=%d)", len(text))
            else:
                logger.warning("Autosave returned False")
        except Exception:
            logger.exception("Autosave failed")