# Application/core/document_manager.py
from PyQt5.QtCore import QObject, pyqtSignal
import pathlib
import shutil
import os
import logging

logger = logging.getLogger("docconv")

class DocumentManager(QObject):
    """
    Gestisce la lista documenti, le cartelle di lavoro e i salvataggi 'editable.txt'.
    Emette segnali quando i documenti cambiano o cambia la selezione corrente.
    """
    documents_changed = pyqtSignal(list)    # list of original paths
    current_changed = pyqtSignal(int)       # current index

    def __init__(self, work_root: str = "work"):
        super().__init__()
        self.work_root = pathlib.Path(work_root)
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.documents = []   # list[str] paths to work-copies (preferred)
        self.current_index = -1

    def load_files(self, file_paths):
        """
        Copia gli originali in work/<basename>/input.orig<suffix>
        e popola self.documents con i percorsi delle copie (se possibile).
        Emite documents_changed e current_changed.
        """
        self.documents = []
        for p in file_paths:
            try:
                ppath = pathlib.Path(p)
                docdir = self.work_root / ppath.stem
                docdir.mkdir(parents=True, exist_ok=True)
                dest_orig = docdir / ("input.orig" + ppath.suffix)
                try:
                    shutil.copy2(str(ppath), str(dest_orig))
                    logger.info("Copied original '%s' -> '%s'", str(ppath), str(dest_orig))
                    chosen = str(dest_orig)
                except Exception as e:
                    # copy failed: log and fallback to original path
                    logger.warning("Failed to copy '%s' to workdir: %s. Will use original path.", str(ppath), str(e))
                    chosen = str(ppath)
                # store path (prefer the work copy)
                self.documents.append(chosen)
            except Exception as e:
                logger.exception("Unexpected error while preparing document %s: %s", p, e)

        self.current_index = 0 if self.documents else -1
        self.documents_changed.emit(self.documents)
        self.current_changed.emit(self.current_index)
        logger.debug("Loaded %d documents into DocumentManager", len(self.documents))

    def get_documents(self):
        return list(self.documents)

    def select(self, index: int):
        if 0 <= index < len(self.documents):
            self.current_index = index
            self.current_changed.emit(index)
            logger.debug("Selected document index %d", index)

    def get_current_path(self):
        if 0 <= self.current_index < len(self.documents):
            return self.documents[self.current_index]
        return None

    def workdir_for_current(self):
        """
        Returns the work directory (Path) for the current document.
        """
        cur = self.get_current_path()
        if not cur:
            return None
        p = pathlib.Path(cur)
        # if the path is the work copy (under work_root) its parent is the workdir.
        # otherwise, fallback to a work dir named after the stem.
        if str(self.work_root) in str(p.parent):
            return p.parent
        else:
            # create workdir under work_root based on original filename
            docdir = self.work_root / p.stem
            docdir.mkdir(parents=True, exist_ok=True)
            return docdir

    def editable_path_for_current(self):
        wd = self.workdir_for_current()
        if wd:
            return wd / "editable.txt"
        return None

    def save_editable_for_current(self, text: str):
        """
        Save provided text into editable.txt for current document.
        Returns True on success.
        """
        epath = self.editable_path_for_current()
        if not epath:
            logger.warning("save_editable_for_current called but no editable path available")
            return False
        try:
            epath.parent.mkdir(parents=True, exist_ok=True)
            epath.write_text(text, encoding="utf-8")
            logger.debug("Saved editable to %s (len=%d)", str(epath), len(text))
            return True
        except Exception as e:
            logger.exception("Failed to save editable for current: %s", e)
            return False

    def load_editable_for_current(self):
        """
        Return content of editable.txt if exists, else None.
        """
        epath = self.editable_path_for_current()
        if epath and epath.exists():
            try:
                txt = epath.read_text(encoding="utf-8")
                logger.debug("Loaded editable from %s (len=%d)", str(epath), len(txt))
                return txt
            except Exception as e:
                logger.exception("Failed to read editable: %s", e)
                return None
        return None

    def reset(self):
        """
        Optional: clears state (does not delete workdir so user can inspect files).
        """
        self.documents = []
        self.current_index = -1
        self.documents_changed.emit(self.documents)
        self.current_changed.emit(self.current_index)
        logger.info("DocumentManager reset called")