# ui/mainwindow.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy, QFileDialog, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import json
import os
import shutil
import pathlib

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
        self.save_debounce_ms = 800
        # QTimer used for debounced autosave
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._perform_autosave)

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
        extra = """
        QPushButton { padding: 6px 10px; border-radius: 12px; }
        QPushButton#arrow_btn { min-width: 48px; min-height: 36px; padding: 0 8px; font-size: 14px; border-radius: 12px; }
        QPushButton.tool-button { min-width: 160px; min-height: 40px; font-size: 11px; border-radius: 12px; }
        QListWidget { border-radius: 8px; padding: 4px; background: #ffffff; }
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
                QListWidget { background: #ffffff; color: #111; }
            """
        else:
            base = """
                QMainWindow { background-color: #fafbfe; }
                QPushButton { background-color: #e2e8f0; color: #333; }
                QTextEdit { color: #111; background: #ffffff; }
                QLabel { color: #333; }
                QListWidget { background: #ffffff; color: #111; }
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
        self.upload_btn.setFont(QFont("Arial", 16))
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

        layout_cols = QHBoxLayout()

        # Colonna 1: Anteprima con barre di navigazione
        col_preview = QVBoxLayout()
        preview_bar = QHBoxLayout()
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

        # Colonna 3: Pulsanti verticali + lista documenti (compatta)
        col_tools = QVBoxLayout()
        btn_keys = ["btn_interpret", "btn_compile", "btn_back", "btn_delete", "btn_save"]
        btn_labels = [ self.labels.get(k, k) for k in btn_keys ]
        self.tool_buttons = []
        for lbl in btn_labels:
            b = QPushButton(lbl)
            b.setObjectName("tool_button")
            b.setProperty("class", "tool-button")
            b.setFixedWidth(160)
            b.setFixedHeight(40)
            b.setFont(QFont("Arial", 11))
            col_tools.addWidget(b)
            self.tool_buttons.append(b)
            col_tools.addSpacing(6)
        col_tools.addSpacing(10)

        self.docs_listwidget = QListWidget()
        self.docs_listwidget.setFixedWidth(220)
        self.docs_listwidget.setMinimumHeight(220)
        self.docs_listwidget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.docs_listwidget.itemSelectionChanged.connect(self.on_doc_selection_changed)
        col_tools.addWidget(self.docs_listwidget)

        layout_cols.addLayout(col_preview, 3)
        layout_cols.addLayout(col_title, 1)
        layout_cols.addLayout(col_tools, 1)
        self.layout_main.addLayout(layout_cols)

        if self.document_list:
            self.populate_doc_list()
            self.set_selected_index(0)
        else:
            self.page_indicator.setText("0/0")
            self.title_value.setText("")

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.labels.get("upload_dialog", "Seleziona documenti ODT/ODS"), "", "Documents (*.odt *.ods)")
        if files:
            # create work root if missing
            self.work_root.mkdir(parents=True, exist_ok=True)
            self.document_list = files
            # create per-document work folders and copy original
            for p in self.document_list:
                ppath = pathlib.Path(p)
                name = ppath.stem
                docdir = self.work_root / name
                docdir.mkdir(parents=True, exist_ok=True)
                # copy original if not already present
                dest_orig = docdir / ("input.orig" + ppath.suffix)
                if not dest_orig.exists():
                    try:
                        shutil.copy2(str(ppath), str(dest_orig))
                    except Exception:
                        pass
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

    def populate_doc_list(self):
        self.docs_listwidget.clear()
        for p in self.document_list:
            item = QListWidgetItem(os.path.basename(p))
            self.docs_listwidget.addItem(item)

    def set_selected_index(self, idx):
        if not self.document_list:
            return
        self.current_index = max(0, min(idx, len(self.document_list) - 1))
        basename = os.path.basename(self.document_list[self.current_index])
        self.title_value.setText(basename)
        self.page_indicator.setText(f"{self.current_index + 1}/{len(self.document_list)}")
        if self.docs_listwidget.count() > self.current_index:
            self.docs_listwidget.setCurrentRow(self.current_index)
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

    def _load_editable_for_current(self):
        # Load editable.txt if exists, else try to extract via odfpy if available, else placeholder
        epath = self._editable_path(self.current_index)
        if epath.exists():
            try:
                txt = epath.read_text(encoding="utf-8")
                self.preview_editor.blockSignals(True)
                self.preview_editor.setPlainText(txt)
                self.preview_editor.blockSignals(False)
                return
            except Exception:
                pass
        # Try odfpy extraction if available and original exists
        orig = self._orig_path(self.current_index)
        if orig.exists() and ODFPY_AVAILABLE and orig.suffix.lower() == ".odt":
            try:
                doc = odf_load(str(orig))
                paragraphs = []
                for p in doc.getElementsByType(odf_text.P):
                    text_content = ""
                    for n in p.childNodes:
                        if n.nodeType == n.TEXT_NODE:
                            text_content += n.data
                    if text_content.strip():
                        paragraphs.append(text_content)
                text_joined = "\n\n".join(paragraphs) if paragraphs else ""
                if text_joined.strip():
                    self.preview_editor.blockSignals(True)
                    self.preview_editor.setPlainText(text_joined)
                    self.preview_editor.blockSignals(False)
                    # also save to editable for persistence
                    try:
                        epath.parent.mkdir(parents=True, exist_ok=True)
                        epath.write_text(text_joined, encoding="utf-8")
                    except Exception:
                        pass
                    return
            except Exception:
                pass
        # Fallback placeholder
        self.preview_editor.blockSignals(True)
        self.preview_editor.setPlainText(f"{self.labels.get('preview_label','Anteprima')}\n\n{os.path.basename(self.document_list[self.current_index])}")
        self.preview_editor.blockSignals(False)

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

    # Preview editing / autosave logic
    def _on_preview_text_changed(self):
        # restart debounce timer on every change
        if self._save_timer.isActive():
            self._save_timer.stop()
        self._save_timer.start(self.save_debounce_ms)

    def _perform_autosave(self):
        # write preview content to editable.txt for current document
        try:
            idx = self.current_index
            epath = self._editable_path(idx)
            epath.parent.mkdir(parents=True, exist_ok=True)
            content = self.preview_editor.toPlainText()
            epath.write_text(content, encoding="utf-8")
            # show transient saved indicator
            self._show_saved_indicator()
        except Exception:
            pass

    def _show_saved_indicator(self):
        self.save_status_label.setText(self.labels.get("status_saved", "Salvato"))
        # clear after 1.4s
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
        if hasattr(self, "title_value") and self.document_list:
            self.set_selected_index(self.current_index)

    def toggle_theme(self):
        self.theme = "dark" if self.theme_toggle.isChecked() else "light"
        self.setStyleSheet(self.get_stylesheet())