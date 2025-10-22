# ui/mainwindow.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSizePolicy, QFileDialog, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import json
import os
import shutil
import pathlib
import zipfile
import xml.etree.ElementTree as ET
import logging
import traceback

# Optional odfpy import for basic text extraction from .odt
try:
    from odf.opendocument import load as odf_load
    from odf import text as odf_text
    ODFPY_AVAILABLE = True
except Exception:
    ODFPY_AVAILABLE = False


class ToggleSwitch(QPushButton):
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
        self.work_root = pathlib.Path("work")
        self.work_root.mkdir(parents=True, exist_ok=True)  # ensure exists early for logging
        self.save_debounce_ms = 800
        # QTimer used for debounced autosave
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._perform_autosave)

        # setup logger (console + file work/debug.log)
        self._setup_logger()

        self.setWindowTitle(self.labels.get("app_title", "Document Converter"))
        self.setMinimumSize(900, 600)
        self.setStyleSheet(self.get_stylesheet())
        self.init_ui()
        self.logger.info("MainWindow initialized. odfpy_available=%s", ODFPY_AVAILABLE)

    def _setup_logger(self):
        self.logger = logging.getLogger("docconv")
        self.logger.setLevel(logging.DEBUG)
        # avoid duplicate handlers on re-import
        if not self.logger.handlers:
            fh = logging.FileHandler(self.work_root / "debug.log", encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            fh.setFormatter(fmt)
            ch.setFormatter(fmt)
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def _log(self, level, msg, *args):
        # convenience wrapper
        if level == "info":
            self.logger.info(msg, *args)
        elif level == "debug":
            self.logger.debug(msg, *args)
        elif level == "error":
            self.logger.error(msg, *args)
        else:
            self.logger.info(msg, *args)

    def get_stylesheet(self):
        qss_content = ""
        try:
            with open("assets/toggle_switch.qss", "r", encoding="utf-8") as f:
                qss_content = f.read()
        except Exception:
            qss_content = ""
        extra = """
        QPushButton { padding: 8px 12px; border-radius: 12px; }
        QPushButton#arrow_btn { min-width: 48px; min-height: 40px; padding: 0 10px; font-size: 18px; border-radius: 12px; }
        QPushButton.tool-button { min-width: 150px; min-height: 44px; font-size: 15px; border-radius: 14px; padding: 8px 12px; }
        QTextEdit#preview_editor { border-radius: 12px; background: #ffffff; padding: 12px; }
        QLabel.preview-area-placeholder { color: rgba(0,0,0,0.6); }
        QLabel#save_status { font-size: 11px; color: #8fb; padding-left: 6px; }
        """
        if self.theme == "dark":
            base = """
                QMainWindow { background-color: #21222e; }
                QPushButton { background-color: #333347; color: #fff; }
                QTextEdit { color: #222; background: #fefefe; }
                QLabel { color: #fff; }
            """
        else:
            base = """
                QMainWindow { background-color: #fafbfe; }
                QPushButton { background-color: #e2e8f0; color: #333; }
                QTextEdit { color: #111; background: #ffffff; }
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

        # small save-status label (empty until saved)
        self.save_status_label = QLabel("")
        self.save_status_label.setObjectName("save_status")
        top_bar_layout.addWidget(self.save_status_label)

        top_bar_layout.addStretch()
        self.layout_main.addLayout(top_bar_layout)

    def init_start_layout(self):
        self.start_layout = QVBoxLayout()
        self.upload_btn = QPushButton(self.labels.get("upload_btn", "Carica documenti"))
        self.upload_btn.setFont(QFont("Arial", 18))
        self.upload_btn.clicked.connect(self.upload_files)
        self.upload_btn.setFixedWidth(240)
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

        layout_cols = QHBoxLayout()

        # Colonna 1: Anteprima con barre di navigazione
        col_preview = QVBoxLayout()
        preview_bar = QHBoxLayout()
        self.prev_btn = QPushButton("<")
        self.prev_btn.setObjectName("arrow_btn")
        self.next_btn = QPushButton(">")
        self.next_btn.setObjectName("arrow_btn")
        self.prev_btn.setFixedSize(48, 40)
        self.next_btn.setFixedSize(48, 40)
        self.prev_btn.setFont(QFont("Arial", 18))
        self.next_btn.setFont(QFont("Arial", 18))
        self.prev_btn.clicked.connect(self.on_prev)
        self.next_btn.clicked.connect(self.on_next)
        self.page_indicator = QLabel("")
        self.page_indicator.setAlignment(Qt.AlignCenter)
        self.page_indicator.setFixedHeight(28)
        preview_bar.addWidget(self.prev_btn)
        preview_bar.addWidget(self.page_indicator, stretch=1)
        preview_bar.addWidget(self.next_btn)
        col_preview.addLayout(preview_bar)

        # Preview frame with QTextEdit inside (editable)
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("preview_frame")
        self.preview_frame.setStyleSheet("QFrame#preview_frame { border-radius: 12px; }")
        self.preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_editor = QTextEdit()
        self.preview_editor.setObjectName("preview_editor")
        self.preview_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_editor.setAcceptRichText(False)  # plain text editing for now
        self.preview_editor.textChanged.connect(self._on_preview_text_changed)

        # placeholder initial content
        self.preview_editor.setPlainText(f"{self.labels.get('preview_label','Anteprima')}\n\n")
        preview_layout.addWidget(self.preview_editor)
        self.preview_frame.setLayout(preview_layout)
        self.preview_frame.setMinimumHeight(360)
        self.preview_frame.setMinimumWidth(520)
        col_preview.addWidget(self.preview_frame)
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

        # Colonna 3: Pulsanti verticali (rimosso pannello lista a destra)
        col_tools = QVBoxLayout()
        btn_keys = ["btn_interpret", "btn_compile", "btn_back", "btn_delete", "btn_save"]
        btn_labels = [ self.labels.get(k, k) for k in btn_keys ]
        self.tool_buttons = []
        for lbl in btn_labels:
            b = QPushButton(lbl)
            b.setObjectName("tool_button")
            b.setProperty("class", "tool-button")
            b.setFixedWidth(150)
            b.setFixedHeight(44)
            b.setFont(QFont("Arial", 15))
            col_tools.addWidget(b)
            self.tool_buttons.append(b)
            col_tools.addSpacing(8)
        col_tools.addStretch()

        layout_cols.addLayout(col_preview, 3)
        layout_cols.addLayout(col_title, 1)
        layout_cols.addLayout(col_tools, 1)
        self.layout_main.addLayout(layout_cols)

        # Initialize selection and content
        if self.document_list:
            self.set_selected_index(0)
        else:
            self.page_indicator.setText("0/0")
            self.title_value.setText("")

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.labels.get("upload_dialog", "Seleziona documenti ODT/ODS"), "", "Documents (*.odt *.ods)")
        if files:
            self._log("info", "User selected %d files", len(files))
            # create work root if missing (already created in __init__, but ensure)
            self.work_root.mkdir(parents=True, exist_ok=True)
            self.document_list = files
            # create per-document work folders and copy original
            for p in self.document_list:
                try:
                    ppath = pathlib.Path(p)
                    name = ppath.stem
                    docdir = self.work_root / name
                    docdir.mkdir(parents=True, exist_ok=True)
                    # copy original if not already present
                    dest_orig = docdir / ("input.orig" + ppath.suffix)
                    if not dest_orig.exists():
                        shutil.copy2(str(ppath), str(dest_orig))
                        self._log("info", "Copied original '%s' -> '%s'", str(ppath), str(dest_orig))
                    else:
                        self._log("debug", "Original already exists: %s", str(dest_orig))
                    # log size and existence
                    try:
                        self._log("debug", "dest_orig.exists=%s size=%s", dest_orig.exists(), dest_orig.stat().st_size if dest_orig.exists() else "n/a")
                    except Exception:
                        self._log("debug", "Could not stat dest_orig")
                except Exception as e:
                    self._log("error", "Error copying file %s: %s", p, str(e))
                    self._log("debug", traceback.format_exc())

            # remove central upload UI
            try:
                while self.start_layout.count():
                    it = self.start_layout.takeAt(0)
                    if it and it.widget():
                        it.widget().setParent(None)
                self.start_layout.setParent(None)
                delattr(self, "start_layout")
            except Exception:
                try:
                    self.upload_btn.setParent(None)
                except Exception:
                    pass
            self.show_app_layout_after_upload()

    def set_selected_index(self, idx):
        if not self.document_list:
            return
        self.current_index = max(0, min(idx, len(self.document_list) - 1))
        basename = os.path.basename(self.document_list[self.current_index])
        self.title_value.setText(basename)
        self.page_indicator.setText(f"{self.current_index + 1}/{len(self.document_list)}")
        # load editable content for this document
        self._load_editable_for_current()

    def _doc_workdir(self, index):
        ppath = pathlib.Path(self.document_list[index])
        return self.work_root / ppath.stem

    def _editable_path(self, index):
        return self._doc_workdir(index) / "editable.txt"

    def _orig_path(self, index):
        p = pathlib.Path(self.document_list[index])
        return self._doc_workdir(index) / ("input.orig" + p.suffix)

    def _extract_text_from_odt_by_unzip(self, odt_path):
        """
        Fallback extractor: unzip the .odt and parse content.xml with ElementTree,
        collecting text:p contents. Returns the extracted plain text or None.
        """
        try:
            with zipfile.ZipFile(str(odt_path), 'r') as z:
                self._log("debug", "Zip namelist: %s", z.namelist())
                if 'content.xml' not in z.namelist():
                    self._log("error", "content.xml not in odt archive")
                    return None
                with z.open('content.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    # namespace for text
                    ns = {'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
                    paragraphs = []
                    for p in root.findall('.//text:p', ns):
                        # Collect text including nested spans
                        parts = []
                        if p.text and p.text.strip():
                            parts.append(p.text)
                        for node in p:
                            if node.text and node.text.strip():
                                parts.append(node.text)
                            if node.tail and node.tail.strip():
                                parts.append(node.tail)
                        paragraph = ''.join(parts).strip()
                        if paragraph:
                            paragraphs.append(paragraph)
                    if paragraphs:
                        self._log("debug", "Extracted %d paragraphs from content.xml", len(paragraphs))
                        return '\n\n'.join(paragraphs)
        except Exception as e:
            self._log("error", "Exception while extracting by unzip: %s", str(e))
            self._log("debug", traceback.format_exc())
            return None
        return None

    def _load_editable_for_current(self):
        """
        Load editable content into preview_editor:
         - if editable.txt exists, load it
         - else if original exists:
            - try odfpy extraction (if available)
            - else unzip and parse content.xml (fallback)
         - otherwise show placeholder
        Saves extracted text into editable.txt for persistence.
        """
        if not self.document_list:
            self._log("debug", "_load_editable_for_current called but no document_list")
            return
        epath = self._editable_path(self.current_index)
        self._log("debug", "Looking for editable at: %s", str(epath))
        if epath.exists():
            try:
                txt = epath.read_text(encoding="utf-8")
                self._log("info", "Loaded editable.txt for index %d (len=%d)", self.current_index, len(txt))
                self.preview_editor.blockSignals(True)
                self.preview_editor.setPlainText(txt)
                self.preview_editor.blockSignals(False)
                return
            except Exception as e:
                self._log("error", "Error reading editable.txt: %s", str(e))
                self._log("debug", traceback.format_exc())

        orig = self._orig_path(self.current_index)
        self._log("debug", "Original path: %s exists=%s", str(orig), orig.exists())
        extracted_text = None

        # Try odfpy first (if installed)
        if orig.exists() and ODFPY_AVAILABLE and orig.suffix.lower() == ".odt":
            try:
                self._log("debug", "Trying odfpy extraction for %s", str(orig))
                doc = odf_load(str(orig))
                paragraphs = []
                for p in doc.getElementsByType(odf_text.P):
                    text_content = ""
                    for n in p.childNodes:
                        try:
                            if getattr(n, "nodeType", None) == n.TEXT_NODE:
                                text_content += n.data
                            elif hasattr(n, "toString"):
                                text_content += str(n.toString())
                            elif hasattr(n, "data"):
                                text_content += str(n.data)
                        except Exception:
                            try:
                                text_content += str(n)
                            except Exception:
                                pass
                    if text_content.strip():
                        paragraphs.append(text_content.strip())
                if paragraphs:
                    extracted_text = "\n\n".join(paragraphs)
                    self._log("info", "odfpy extracted %d paragraphs", len(paragraphs))
            except Exception as e:
                self._log("error", "odfpy extraction failed: %s", str(e))
                self._log("debug", traceback.format_exc())
                extracted_text = None

        # Fallback: unzip and parse content.xml directly (works even if odfpy missing)
        if extracted_text is None and orig.exists() and orig.suffix.lower() == ".odt":
            self._log("debug", "Attempting fallback unzip parsing for %s", str(orig))
            extracted_text = self._extract_text_from_odt_by_unzip(orig)
            if extracted_text:
                self._log("info", "Fallback unzip extraction succeeded (len=%d)", len(extracted_text))
            else:
                self._log("warning", "Fallback unzip extraction returned no content")

        # If we have extracted text, populate editor and save
        if extracted_text:
            try:
                self.preview_editor.blockSignals(True)
                self.preview_editor.setPlainText(extracted_text)
                self.preview_editor.blockSignals(False)
                # persist to editable.txt
                try:
                    epath.parent.mkdir(parents=True, exist_ok=True)
                    epath.write_text(extracted_text, encoding="utf-8")
                    self._log("debug", "Saved extracted text to %s", str(epath))
                except Exception as e:
                    self._log("error", "Failed to save extracted text: %s", str(e))
                    self._log("debug", traceback.format_exc())
                return
            except Exception as e:
                self._log("error", "Error populating preview editor: %s", str(e))
                self._log("debug", traceback.format_exc())

        # Final fallback: placeholder with filename
        try:
            self.preview_editor.blockSignals(True)
            self.preview_editor.setPlainText(f"{self.labels.get('preview_label','Anteprima')}\n\n{os.path.basename(self.document_list[self.current_index])}")
            self.preview_editor.blockSignals(False)
            self._log("info", "Showed placeholder in preview")
        except Exception as e:
            self._log("error", "Error setting placeholder: %s", str(e))
            self._log("debug", traceback.format_exc())

    def on_prev(self):
        if self.document_list:
            self.set_selected_index((self.current_index - 1) % len(self.document_list))

    def on_next(self):
        if self.document_list:
            self.set_selected_index((self.current_index + 1) % len(self.document_list))

    # Preview editing / autosave logic
    def _on_preview_text_changed(self):
        if self._save_timer.isActive():
            self._save_timer.stop()
        self._save_timer.start(self.save_debounce_ms)

    def _perform_autosave(self):
        try:
            idx = self.current_index
            epath = self._editable_path(idx)
            epath.parent.mkdir(parents=True, exist_ok=True)
            content = self.preview_editor.toPlainText()
            epath.write_text(content, encoding="utf-8")
            self._show_saved_indicator()
            self._log("debug", "Autosaved editable.txt for index %d (len=%d)", idx, len(content))
        except Exception as e:
            self._log("error", "Autosave failed: %s", str(e))
            self._log("debug", traceback.format_exc())

    def _show_saved_indicator(self):
        self.save_status_label.setText(self.labels.get("status_saved", "Salvato"))
        QTimer.singleShot(1400, lambda: self.save_status_label.setText(""))

    def toggle_language(self):
        self.language = "en" if self.lang_toggle.isChecked() else "it"
        labels_file = f"lang/labels_{self.language}.json"
        try:
            with open(labels_file, encoding="utf-8") as f:
                self.labels = json.load(f)
        except Exception:
            with open("lang/labels_en.json", encoding="utf-8") as f:
                self.labels = json.load(f)
        self.setWindowTitle(self.labels.get("app_title", "Document Converter"))
        if hasattr(self, "upload_btn") and self.upload_btn is not None:
            self.upload_btn.setText(self.labels.get("upload_btn", "Carica documenti"))
        theme_on = self.labels.get("theme_on", "Scuro")
        theme_off = self.labels.get("theme_off", "Chiaro")
        self.theme_toggle.text_on = theme_on
        self.theme_toggle.text_off = theme_off
        self.theme_toggle.update_text()
        self.lang_label_widget.setText(self.labels.get("language_label", "Lingua:"))
        self.theme_label_widget.setText(self.labels.get("theme_label", "Tema:"))
        # update buttons & content if present
        btn_keys = ["btn_interpret", "btn_compile", "btn_back", "btn_delete", "btn_save"]
        for i, btn in enumerate(getattr(self, "tool_buttons", [])):
            k = btn_keys[i] if i < len(btn_keys) else None
            if k:
                btn.setText(self.labels.get(k, btn.text()))
        if self.document_list:
            self.set_selected_index(self.current_index)

    def toggle_theme(self):
        self.theme = "dark" if self.theme_toggle.isChecked() else "light"
        self.setStyleSheet(self.get_stylesheet())