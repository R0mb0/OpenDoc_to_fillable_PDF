# Document Converter – Prototipo UI

## Struttura progetto

- `main.py` – entry point applicazione
- `ui/` – componenti UI custom (MainWindow)
- `lang/` – file JSON per labels IT/EN
- `assets/` – icone e immagini (non usati nel prototipo)
- `README.md` – istruzioni e note

## Avvio prototipo

1. Installare PyQt5:  
   `pip install PyQt5`
2. Eseguire:  
   `python main.py`

## Funzionalità implementate

- Layout a tre colonne responsive
- Tabella scrollabile multi-documento
- Grafica rotondeggiante, stile moderno
- Pulsante centrale “Carica documenti” con dialog multi-file
- Switch lingua IT/EN
- Switch tema (placeholder)

## Note

- Questo prototipo è la base per tutte le estensioni future (roadmap step 2+)
- Codice commentato e facilmente estendibile