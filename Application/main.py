import sys
import locale
import json
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from utils.logging import setup_logger
import logging

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
        return c/12.92 if c <= 0.04045 else (((c+0.055)/1.055) ** 2.4)
    r_l = lin(r)
    g_l = lin(g)
    b_l = lin(b)
    # Rec. 709 luminance
    lum = 0.2126 * r_l + 0.7152 * g_l + 0.0722 * b_l
    return lum * 255

def detect_theme(app: QApplication) -> str:
    """
    Platform-aware theme detection:
      - Windows: read registry AppsUseLightTheme (0 = dark, 1 = light)
      - macOS: defaults read AppleInterfaceStyle (Dark)
      - Fallback: Qt palette luminance
    """
    try:
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if val == 1 else "dark"
            except Exception:
                # fallback to palette
                pass
        elif sys.platform == "darwin":
            try:
                p = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True)
                if p.returncode == 0 and "Dark" in p.stdout:
                    return "dark"
            except Exception:
                pass
        # fallback: Qt palette luminance
        try:
            palette = app.palette()
            bg = palette.color(QPalette.Window)
            lum = luminance_from_color(bg)
            return "dark" if lum < 128 else "light"
        except Exception:
            return "light"
    except Exception:
        return "light"

def load_labels(language):
    base = Path(__file__).resolve().parent
    lang_file = base / "lang" / f"labels_{language}.json"
    if not lang_file.exists():
        lang_file = base / "lang" / "labels_en.json"
    try:
        return json.loads(lang_file.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads((base / "lang" / "labels_en.json").read_text(encoding="utf-8"))
        except Exception:
            return {}

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Setup logger (writes to Application/work/debug.log)
    setup_logger(work_root=str(Path(__file__).resolve().parent / "work"))
    logger = logging.getLogger("docconv")
    logger.info("Starting application")

    language = detect_language()
    theme = detect_theme(app)
    labels = load_labels(language)

    # Import mainwindow after logger and labels ready
    from ui.mainwindow import MainWindow

    window = MainWindow(labels, language, theme)
    window.show()
    logger.info("Main window shown (language=%s theme=%s)", language, theme)
    sys.exit(app.exec_())