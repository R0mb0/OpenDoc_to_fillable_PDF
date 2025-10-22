# OpenDoc_to_fillable_PDF

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/7eafbf7310214fb4b19728161fd402b3)](https://app.codacy.com/gh/R0mb0/OpenDoc_to_fillable_PDF/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/R0mb0/OpenDoc_to_fillable_PDF)
[![Open Source Love svg3](https://badges.frapsoft.com/os/v3/open-source.svg?v=103)](https://github.com/R0mb0/OpenDoc_to_fillable_PDF)
[![MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/license/mit)
[![Donate](https://img.shields.io/badge/PayPal-Donate%20to%20Author-blue.svg)](http://paypal.me/R0mb0)

Convert ODT/ODS documents into fillable PDFs with this modern Python desktop application. Multi-document management, simplified editing, step-by-step conversion via LaTeX, navigable preview, auto-save, responsive UI, and multi-language support (IT/EN). Designed for digitizing forms and business document workflows.





---

# Dipendenze del progetto — Document Converter

Questo file raccoglie tutte le dipendenze (runtime, opzionali e di sviluppo) necessarie per eseguire e sviluppare l'applicazione Document Converter, con suggerimenti per versioni, comandi di installazione e note su dipendenze di sistema (TeX, librerie native).

> Nota: i nomi indicati sono i pacchetti Python installabili via pip, salvo dove specificato altrimenti. Alcuni componenti (es. pdflatex) sono programmi di sistema e vanno installati tramite il package manager della piattaforma.

---

## Requisiti minimi consigliati
- Python 3.11+ (consigliato Python 3.11 o 3.12)
- pip (ultima versione)
- virtualenv / venv per ambiente isolato

Esempio rapido:
```bash
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows
pip install --upgrade pip
```

---

## Dipendenze runtime (necessarie per la maggior parte delle funzionalità)
- PyQt5 — GUI
  - pip package: `PyQt5`
  - Suggerimento versione: `PyQt5>=5.15,<6`
- odfpy — estrazione/lettura ODT/ODS (opzionale ma usata per estrazione testo)
  - `odfpy>=1.4.1`
- Jinja2 — template LaTeX
  - `Jinja2>=3.0`
- Pygments — syntax highlighting (per editor LaTeX)
  - `Pygments>=2.11`
- PyPDF2 (alternativa leggera per manipolazione PDF)
  - `PyPDF2>=3.0`
- PyMuPDF (fitz) — rendering PDF avanzato (opzionale ma consigliato per preview grafico)
  - `PyMuPDF>=1.22.0`
- requests (se occorrono chiamate di rete future)
  - `requests>=2.28`

---

## Dipendenze di sistema (non pip)
- pdflatex / TeX Live (o MiKTeX su Windows)
  - Necessario per la compilazione LaTeX → PDF
  - Linux (Debian/Ubuntu): `sudo apt install texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-fonts-extra`
  - Windows: installare MiKTeX o TeX Live
  - macOS: MacTeX via pkg o Homebrew (`brew install --cask mactex` oppure `brew install basictex` + pacchetti)
- (Linux) pacchetti GUI richiesti da Qt: es. `libxcb`, `libxkbcommon-x11` — dipende dalla distro

---

## Opzionali (funzionalità avanzate)
- PyMuPDF (già citato) — rendering PDF nelle preview
- python-docx (se si aggiunge supporto DOCX)
  - `python-docx>=0.8.11`
- watchdog — monitoraggio file più avanzato (opzionale)
  - `watchdog>=2.1.0`

---

## Dipendenze per sviluppo / test / linting
- pytest — testing
  - `pytest>=7.0`
- black — formattazione codice
  - `black>=24.0`
- isort — ordinamento import
  - `isort>=5.10`
- flake8 — linting
  - `flake8>=6.0`
- mypy — type checking (opzionale)
  - `mypy>=1.9`
- pre-commit — hook per lint/format
  - `pre-commit>=3.0`
- tox (opzionale) — test matrix
  - `tox>=4.0`

---

## Packaging e distribuzione
- PyInstaller — per creare eseguibili
  - `pyinstaller>=5.0`
- (Opzionale) briefcase / cx_Freeze se preferisci alternative

---

## Suggerimento per files di requisiti (esempi)

requirements.txt (runtime principale)
```text
PyQt5>=5.15,<6
odfpy>=1.4.1
Jinja2>=3.0
Pygments>=2.11
PyPDF2>=3.0
# opzionali:
# PyMuPDF>=1.22.0
# requests>=2.28
```

requirements-optional.txt (funzionalità opzionali)
```text
PyMuPDF>=1.22.0
python-docx>=0.8.11
watchdog>=2.1.0
```

requirements-dev.txt (tooling)
```text
pytest>=7.0
black>=24.0
isort>=5.10
flake8>=6.0
mypy>=1.9
pre-commit>=3.0
tox>=4.0
```

Installazione rapida:
```bash
# ambiente virtuale attivo
pip install -r requirements.txt
# installa opzionali
pip install -r requirements-optional.txt
# installa tooling
pip install -r requirements-dev.txt
```

---

## Esempio di "extras" in pyproject.toml / setup.cfg (opzionale)
Se usi `pyproject.toml` / setuptools, puoi esporre extras come:
- `pip install .[dev]`
- `pip install .[pdf]`

Esempio minimale (pyproject/setup.cfg): dichiarare extras `pdf`, `dev`, `odf`.

---

## Note su compatibilità e problemi noti
- PyQt5 su alcune distribuzioni Linux richiede pacchetti nativi (X11/Wayland related) — se l'app non parte, controllare i messaggi d'errore e installare i dev packages richiesti dalla distro.
- Detection tema OS:
  - Windows: il codice usa la registry key `AppsUseLightTheme` (nessuna dipendenza extra).
  - macOS: si interroga `defaults` (comando di sistema).
  - Su alcune combinazioni Qt + OS la palette Qt può non riflettere il tema OS: in quei casi fornisci la piattaforma/Qt version per diagnostica.
- PyMuPDF non è compatibile con tutte le versioni CPython; se incontrassi problemi compila la wheel o installa la versione compatibile.

---

## Raccomandazioni pratiche
- Usare un ambiente virtuale dedicato per il progetto (venv/virtualenv/conda).
- Pinnare versioni per release stabili (es. `PyQt5==5.15.7`) prima di build/packaging.
- Tenere separati `requirements.txt` (runtime) e `requirements-dev.txt`.
- Documentare nel README come installare TeX (pdflatex) perché è requisito esterno importante.
- Considerare l'uso di un file `constraints.txt` in CI per riproducibilità.

---

## Esempio di script di setup rapido (shell)
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# opzionale:
pip install -r requirements-optional.txt
pip install -r requirements-dev.txt
```

---

Se vuoi, posso:
- Generare automaticamente i file `requirements.txt`, `requirements-dev.txt` e `requirements-optional.txt` e committarli nella repo.
- Preparare una sezione da aggiungere al README con istruzioni di installazione per Windows/macOS/Linux (incluso come installare TeX).
- Fornire suggerimenti di version pin per ogni pacchetto prima di creare una prima release/PR.

Dimmi quale opzione preferisci e procedo.

