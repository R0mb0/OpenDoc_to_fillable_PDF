import sys
import locale
import json
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui.mainwindow import MainWindow

def detect_language():
    lang, _ = locale.getdefaultlocale()
    if lang and lang.startswith("it"):
        return "it"
    return "en"

def load_labels(language):
    try:
        with open(f"lang/labels_{language}.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        with open("lang/labels_en.json", encoding="utf-8") as f:
            return json.load(f)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    language = detect_language()
    labels = load_labels(language)
    window = MainWindow(labels, language)
    window.show()
    sys.exit(app.exec_())