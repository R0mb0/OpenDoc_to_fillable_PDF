# core/document_manager.py
from PyQt5.QtCore import QObject, pyqtSignal
import pathlib
import shutil
import os

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
        self.documents = []   # list[str] original selected paths
        self.current_index = -1

    def load_files(self, file_paths):
        """
        Copia gli originali in work/<basename>/input.orig<suffix>
        e popola self.documents con i percorsi originali (per UI).
        Emite documents_changed e current_changed.
        """
        self.documents = []
        for p in file_paths:
            ppath = pathlib.Path(p)
            docdir = self.work_root / ppath.stem
            docdir.mkdir(parents=True, exist_ok=True)
            dest_orig = docdir / ("input.orig" + ppath.suffix)
            try:
                if not dest_orig.exists():
                    shutil.copy2(str(ppath), str(dest_orig))
            except Exception:
                # best-effort copy; leave original path if copy fails
                pass
            # store the path to the copied original (work copy) for later extract
            self.documents.append(str(dest_orig) if dest_orig.exists() else str(ppath))
        self.current_index = 0 if self.documents else -1
        self.documents_changed.emit(self.documents)
        self.current_changed.emit(self.current_index)

    def get_documents(self):
        return list(self.documents)

    def select(self, index: int):
        if 0 <= index < len(self.documents):
            self.current_index = index
            self.current_changed.emit(index)

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
        # workdir is parent (we copied into work/<basename>/input.orig...)
        return p.parent

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
            return False
        try:
            epath.parent.mkdir(parents=True, exist_ok=True)
            epath.write_text(text, encoding="utf-8")
            return True
        except Exception:
            return False

    def load_editable_for_current(self):
        """
        Return content of editable.txt if exists, else None.
        """
        epath = self.editable_path_for_current()
        if epath and epath.exists():
            try:
                return epath.read_text(encoding="utf-8")
            except Exception:
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