# Projektbericht LaTeX — Aufbau-Hinweise

## Kompilieren

```bash
# Empfohlen: mit latexmk
latexmk -pdf -biber main.tex

# Oder manuell:
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

## Ordnerstruktur

```
docs/report/
├── main.tex           ← Haupt-Dokument
├── references.bib     ← Literaturverzeichnis
├── figures/           ← Alle Abbildungen (PDF oder PNG)
│   ├── tud_logo.pdf
│   ├── workflow_overview.pdf      ← Ende-zu-Ende Pipeline (analog Fig. 1.1)
│   ├── shape_baujahr.pdf          ← Doppelplot Baujahr (Preis vs. Laufzeit)
│   └── ...
└── README.md          ← Diese Datei
```

## Mapping zum Referenzpapier (NLP Populismus)

| Referenz-Abschnitt | Unser Abschnitt | Anpassung |
|---|---|---|
| 1.1 Motivation | 1.1 Motivation | Kontext: Mietmarkt statt Bundestag |
| 1.2 Goals & Structure | 1.2 Ziele und Aufbau | Zwei ML-Pipelines statt NLP-Pipeline |
| 2.1 Domain Context | 2.1 Domänenkontext | Wohnungsmietmarkt statt Populismus-Diskurs |
| 2.2 Definition of Populism | 2.2 Theoretischer Rahmen | Hedonische Preistheorie + Time-on-Market |
| 2.3 Methodical Scope | 2.3 Methodischer Rahmen | IML vs. Black-Box, Skalierung |
| 3. Related Work | 3. Verwandte Arbeiten | Hedonik + ML + IML-Lit. |
| 4.1 Dataset (CPP-BT) | 4.1 Datensatz (RWI-GEO-RED) | Andere Quelle, gleiche Struktur |
| 4.2 Data Preparation | 4.2 Datenvorbereitung | Regression statt NLP-Preprocessing |
| 4.3 Relevance Classifier | **ENTFÄLLT** | Kein NLP-Filter nötig |
| 4.4 Labeling | **ENTFÄLLT** | Keine manuelle Annotation |
| 4.5 Class Imbalances | **ENTFÄLLT** | Regression, kein Klassenungleichgewicht |
| 4.6 Rule-based Features | → Feature Engineering | baujahr, etage etc. |
| 4.7 Models | 4.3 Modelle | 5 Klassen statt 5 Komplexitätsstufen |
| 4.8 Evaluation | 4.4 Evaluierungsmethodik | MAE/RMSE/R² statt F1/AUROC |
| 4.9 Hyperparameter | 4.5 Hyperparameter | Gleiche Logik |
| 4.10 Target Value | 4.6 Shape Function Analyse | UNSER Kernbeitrag |
| 5.x Results | 5.x Ergebnisse | Preis + Laufzeit separat |
| **NEU** | 5.4 Shape Function Vergleich | Wissenschaftlicher Kernbeitrag |
| 6.x Discussion | 6.x Diskussion | Gleiche Struktur |

## Wichtige TODO-Marker

Suche im main.tex nach `% TODO:` um alle offenen Stellen zu finden.
