import sys
import locale
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from ui.mainwindow import MainWindow

def detect_language():
    lang, _ = locale.getdefaultlocale()
    if lang and lang.startswith("it"):
        return "it"
    return "en"

def luminance_from_color(qcolor: QColor) -> float:
    # Perceived luminance (0..255)
    r = qcolor.red() / 255.0
    g = qcolor.green() / 255.0
    b = qcolor.blue() / 255.0
    # linearize sRGB
    def lin(c):
        return c/12.92 if c <= 0.04045 else (( (c+0.055)/1.055) ** 2.4)
    r_l = lin(r)
    g_l = lin(g)
    b_l = lin(b)
    # Rec. 709 luminance
    lum = 0.2126 * r_l + 0.7152 * g_l + 0.0722 * b_l
    # scale to 0..255
    return lum * 255

def detect_theme(app: QApplication) -> str:
    try:
        palette = app.palette()
        bg = palette.color(QPalette.Window)
        lum = luminance_from_color(bg)
        # threshold: if luminance lower than mid -> dark theme
        return "dark" if lum < 128 else "light"
    except Exception:
        return "light"

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
    theme = detect_theme(app)
    labels = load_labels(language)
    window = MainWindow(labels, language, theme)
    window.show()
    sys.exit(app.exec_())