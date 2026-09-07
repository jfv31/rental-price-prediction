# Projektplan — GADA Topic 6
## „Preis und Nachfrageresonanz im deutschen Wohnungsmietmarkt"
### Interpretable ML auf dem RWI-GEO-RED Datensatz (ImmoScout24, 2007–2025)

> **Für:** Team-Präsentation & interne Abstimmung  
> **Datum:** Mai 2026  
> **Datenbasis:** RWI-GEO-RED v14, ~27,4 Mio. Wohnungsmiet-Inserate (WM_SUF)

---

## 1. Kernidee und wissenschaftliche Motivation

### Die zentrale Forschungsfrage

> *„Was bestimmt den Preis einer Mietwohnung — und sind es dieselben Faktoren, die sie schnell oder langsam vermietet werden lassen?"*

### Der Schlüsselbefund aus der Datenexploration

Eine erste Korrelationsanalyse auf ~20 Mio. bereinigten Inseraten zeigt:

| Zusammenhang | Pearson r |
|---|---|
| Kaltmiete/m² ↔ log(Laufzeittage) | **−0.136** |
| Kaltmiete/m² ↔ log(Hits) | **+0.062** |

**Interpretation:** Preis und Vermarktungsgeschwindigkeit sind nahezu unkorreliert. Teurere Wohnungen werden nicht automatisch schneller oder langsamer vermietet. Das bedeutet: **Beide Zielgrößen werden von einem unterschiedlichen Set an Merkmalen getrieben** — und genau das macht es interessant, beide gleichzeitig zu modellieren und zu vergleichen.

### Wissenschaftlicher Mehrwert

- Bisherige Immobilien-ML-Studien fokussieren fast ausschließlich auf Preisvorhersage
- Vermarktungsdauer als Proxy für **Marktliquidität** und **Nachfrageresonanz** ist deutlich weniger erforscht
- Die **Side-by-Side-Gegenüberstellung** von Shape Functions (IML) für beide Zielgrößen liefert einen genuinen analytischen Beitrag
- Direkter Bezug zur Kursliteratur: Zschech et al. (2025) — Inherently Interpretable Machine Learning

---

## 2. Datenbasis

### Datensatz

| Merkmal | Wert |
|---|---|
| Quelle | RWI-GEO-RED v14 (FDZ Ruhr / ImmobilienScout24) |
| Datei | `WM_SUF_ohneText.csv` |
| Gesamtgröße | ~8,7 GB, ~27,4 Mio. Zeilen |
| Zeitraum | 2007–2025 |
| Regionale Abdeckung | 413 Kreise, alle 16 Bundesländer |
| Marktabdeckung | ~50% des deutschen Online-Wohnungsmietmarkts |

### Verwendete Arbeitsmenge (nach Bereinigung)

Nach Filterung auf `dupID_gen = 0` (Erstinserate, keine Duplikate) und valide Preis-/Flächenwerte:

| Kennzahl | Wert |
|---|---|
| Bereinigte Inserate | ~20,4 Mio. |
| Kaltmiete/m² — Median | **7,24 €/m²** |
| Kaltmiete/m² — Spanne (P5–P95) | 4,32 € – 16,95 €/m² |
| Laufzeittage — Median | **14 Tage** |
| Laufzeittage — Spanne (P5–P95) | 1 – 92 Tage |
| Häufigste Wohnungsgrößen | 2 Zi. (34%), 3 Zi. (33%), 1 Zi. (11%) |
| Top-Bundesländer | NRW (23%), Sachsen (13%), Bayern (12%), BW (10%), Berlin (10%) |

### Wichtigste Feature-Qualität

| Feature | Vollständigkeit | Verwendung |
|---|---|---|
| `mietekalt`, `wohnflaeche`, `zimmeranzahl` | >99% | Zielgröße / Core-Feature |
| `laufzeittage` | ~100% | Zielgröße Modell 2 |
| `hits` | ~100% | Optionale Zielgröße / Feature |
| `balkon` | 91% | Feature (missing = eigene Kategorie) |
| `keller` | 86% | Feature |
| `aufzug` | 78% | Feature |
| `einbaukueche` | 80% | Feature |
| `etage` | 77% | Feature |
| `baujahr` | 64% | Feature mit Imputation |
| `blid`, `kid2019` | >99% | Regionale Features |
| `energieeffizienzklasse` | <10% (vor 2018) | **Nicht verwendet** (zu lückenhaft) |
| `anbieter` | 33% | **Nicht verwendet** (zu lückenhaft) |

---

## 3. Zwei Modelle — eine Pipeline

Das Projekt besteht aus zwei parallelen, methodisch identischen ML-Pipelines auf demselben Datensatz:

```
WM_SUF_ohneText.csv
        │
        ▼
  [Datenbereinigung & Feature Engineering]
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
  Modell A            Modell B          [Vergleich]
  Ziel: mietekalt/m²  Ziel: log(laufzeittage)
  "Was bestimmt       "Was bestimmt     Shape Functions
   den Preis?"         die Dauer?"      nebeneinander
```

### Zielgrößen

| | Modell A (Preis) | Modell B (Liquidität) |
|---|---|---|
| **Zielgröße** | `mietekalt / wohnflaeche` (€/m²) | `log(laufzeittage + 1)` |
| **Aufgabe** | Regression | Regression |
| **Transformation** | Keine / ggf. log | Log (rechtsschiefe Verteilung) |
| **Interpretation** | Erwarteter Mietpreis | Erwartete Vermarktungsdauer |

---

## 4. Feature Engineering

### Numerische Features

| Feature | Herkunft | Begründung |
|---|---|---|
| `wohnflaeche` | direkt | Primärer Größenindikator |
| `zimmeranzahl` | direkt | Struktur der Wohnung |
| `etage` | direkt | Lage im Gebäude |
| `anzahletagen` | direkt | Gebäudegröße als Kontext |
| `baujahr` | direkt + Imputation | Alterseffekt, DDR/Gründerzeit |
| `ajahr` | direkt | Zeittrend, Marktphase |
| `laufzeittage` | direkt (nur Modell A) | — |
| `mietekalt / wohnflaeche` | berechnet (nur Modell B) | — |

### Kategoriale Features (One-Hot / Ordinal)

| Feature | Kategorien | Hinweis |
|---|---|---|
| `balkon` | 0 / 1 / missing | Missing als eigene Kategorie |
| `keller` | 0 / 1 / missing | — |
| `aufzug` | 0 / 1 / missing | — |
| `einbaukueche` | 0 / 1 / missing | — |
| `heizungsart` | ~10 Kategorien | Ordinal kodierbar |
| `objektzustand` | ~8 Kategorien | Ordinal (Neubau > Gepflegt > Renovierungsbedarf) |
| `ausstattung` | 1–4 (Einfach/Normal/Gehoben/Luxus) | Ordinal, 53% fehlend |
| `blid` | 16 Bundesländer | Regionale Baseline |

### Duplikat-Filterung

- Nur `dupID_gen = 0` (Erstinserate) → ~20,4 Mio. Zeilen
- Entfernt Mehrfachinserate der gleichen Wohnung, die die zeitliche Abhängigkeit verzerren würden
- Für Modell B (Laufzeit) ist das besonders wichtig — nur das jeweils erste Inserat hat eine "echte" Vermarktungsdauer

---

## 5. ML-Modelle und Algo-Auswahl

Drei Modellkategorien werden für **beide** Zielgrößen identisch implementiert:

### Kategorie 1: Simple Baseline

| Modell | Library | Zweck |
|---|---|---|
| **Lineare Regression** | `scikit-learn` | Untere Benchmark-Grenze |
| **Decision Tree** | `scikit-learn` | Einfache Nicht-Linearität |

### Kategorie 2: Advanced Flexible (Black-Box)

| Modell | Library | Zweck |
|---|---|---|
| **XGBoost** | `xgboost` | Performance-Ceiling, SHAP-kompatibel |
| **LightGBM** | `lightgbm` | Schnellere Alternative zu XGBoost |
| **TabPFN** | `tabpfn` | Tabular Foundation Model (kursrelevant) |

### Kategorie 3: Advanced Interpretable ← Hauptfokus

| Modell | Library | Zweck |
|---|---|---|
| **EBM** (Explainable Boosting Machine) | `interpret` | GAM mit Interaktionstermen |
| **IGANN** | `igann` | GAM mit neuronalen Shape Functions |

> **Hinweis zu TabPFN:** Maximale Sample-Größe ~10k Zeilen → auf stratifiziertem Subsample trainieren.  
> **Hinweis zu IGANN/EBM:** Sind auf großen Datensätzen trainierbar, ggf. auf 1–2 Mio. Zeilen subsamplen je nach RAM.

### Post-hoc Erklärbarkeit (Kontrastfolie)

| Methode | Anwendung |
|---|---|
| **SHAP** (`shap` library) | Für XGBoost/LightGBM — Vergleich mit GAM Shape Functions |
| **SHAP Waterfall Plot** | Einzelne Wohnungserklärung in der App |
| **SHAP Beeswarm** | Globale Feature-Importance |

---

## 6. Evaluierung

### Metriken

| Metrik | Modell A (Preis) | Modell B (Laufzeit) |
|---|---|---|
| **MAE** | €/m² | Tage (nach Rücktransformation) |
| **RMSE** | €/m² | Tage |
| **R²** | Anteil erklärter Varianz | Anteil erklärter Varianz |

### Vorgehen

- **Train/Test Split:** 80/20, zeitlich stratifiziert (`ajahr` als Stratifizierungsvariable)
- Kein einfacher Random Split — verhindert Data Leakage über Zeit
- **Cross-Validation:** 5-Fold innerhalb des Trainingssets für Hyperparameter-Tuning
- **Vergleichstabelle:** Alle Modelle nebeneinander in einem Übersichts-DataFrame

---

## 7. Die Kernaussage: Shape Function Vergleich

Das wissenschaftliche Herzstück des Projekts ist die **Side-by-Side-Gegenüberstellung** der IGANN/EBM Shape Functions für beide Modelle:

```
Feature: baujahr

Modell A (Preis €/m²)          Modell B (Laufzeit log-Tage)
  ↑                               ↑
  │    ╭──╮                       │  ╭╮
  │   ╭╯  ╰╮                      │  ╯ ╰──────────╮
  │  ╭╯    ╰────────╮             │               ╰────
  │──╯               ╰──          │
  └─────────────────────→         └──────────────────→
  1900  1950  1980  2000          1900  1950  1980  2000

"Altbau und Neubau haben          "Neubauten werden schneller
 höhere Mietpreise"                vermietet als Altbauten"
```

**Fragen die so beantwortbar werden:**
- Ist die Einbauküche ein Preistreiber, ein Geschwindigkeitstreiber — oder beides?
- Macht ein Balkon die Wohnung teurer oder nur beliebter?
- Spielt die Etage für den Preis eine andere Rolle als für die Vermarktungsgeschwindigkeit?
- Hat das Baujahr einen anderen Effekt auf Preis vs. Nachfrage?

---

## 8. Streamlit App — Aufbau und Seiten

### Technischer Stack

| Komponente | Tool |
|---|---|
| App-Framework | **Streamlit** |
| Interaktive Plots | **Plotly** |
| ML-Modelle | `igann`, `interpret`, `xgboost`, `scikit-learn`, `shap` |
| Datenverarbeitung | `pandas`, `numpy` |
| Modell-Persistenz | `joblib` (pickle) |

### App-Struktur (3 Seiten)

#### Seite 1 — Modellvergleich & Performance

```
📊 Modellübersicht
├── Tabelle: MAE / RMSE / R² für alle 7 Modelle
│   → Modell A (Preis) und Modell B (Laufzeit) nebeneinander
├── Bar Chart: Modell-Ranking nach MAE
└── Kernaussage: "EBM erreicht 93% der XGBoost-Performance, 
                  ist aber vollständig erklärbar"
```

#### Seite 2 — Shape Function Explorer

```
🔍 Shape Functions (Interpretable ML)
├── Dropdown: Feature wählen (baujahr, wohnflaeche, etage, ...)
├── Toggle: Modell A (Preis) | Modell B (Laufzeit) | Beide
├── IGANN Shape Function Plot (Plotly, interaktiv mit Hover)
├── Vergleich: IGANN vs. SHAP-Values für XGBoost
│   → "Was sagt das interpretierbare Modell vs. die Post-hoc-Erklärung?"
└── Kernfrage: Sind die Shape Functions konsistent?
```

#### Seite 3 — Wohnungs-Simulator

```
🏠 Individuelle Wohnungsanalyse
├── Sidebar-Eingaben:
│   ├── Wohnfläche (m²): Slider
│   ├── Zimmeranzahl: Dropdown  
│   ├── Baujahr: Slider
│   ├── Etage: Dropdown
│   ├── Bundesland: Dropdown
│   └── Ausstattung: Checkboxen (Balkon, Keller, Aufzug, EBK)
│
├── Output Modell A (Preis):
│   ├── → "Erwartete Kaltmiete: 8,40 €/m² | 714 €/Monat"
│   └── → SHAP Waterfall Plot: "Warum dieser Preis?"
│
└── Output Modell B (Laufzeit):
    ├── → "Erwartete Vermarktungsdauer: ~11 Tage"
    └── → SHAP Waterfall Plot: "Warum so schnell/langsam?"
```

---

## 9. Projektstruktur (Ordner & Dateien)

```
GADA/
├── data/
│   ├── WM_SUF_ohneText.csv          ← Quelldaten (nicht versionieren!)
│   └── sample_wm_clean.parquet      ← Bereinigtes 1%-Sample für schnelle Iteration
│
├── notebooks/
│   ├── 01_data_exploration.ipynb    ← EDA, Missingness, Verteilungen
│   ├── 02_feature_engineering.ipynb ← Bereinigung, Encoding, Feature-Konstruktion
│   ├── 03_model_A_price.ipynb       ← Alle Modelle für Kaltmiete/m²
│   ├── 04_model_B_duration.ipynb    ← Alle Modelle für log(laufzeittage)
│   └── 05_shape_comparison.ipynb    ← Vergleich Shape Functions A vs. B
│
├── models/
│   ├── igann_price.joblib
│   ├── igann_duration.joblib
│   ├── xgb_price.joblib
│   └── xgb_duration.joblib
│
├── app/
│   ├── app.py                       ← Streamlit Haupt-App
│   ├── pages/
│   │   ├── 1_Modellvergleich.py
│   │   ├── 2_Shape_Explorer.py
│   │   └── 3_Wohnungs_Simulator.py
│   └── utils.py                     ← Lade-Funktionen, Hilfsfunktionen
│
├── Documentation/                   ← Vom FDZ geliefert (unverändert)
├── requirements.txt
└── README.md
```

---

## 10. Arbeitsaufteilung (Empfehlung für 3 Personen)

| Person | Verantwortungsbereich | Notebooks / Dateien |
|---|---|---|
| **Person A** | Datenpipeline + EDA + Feature Engineering | `01`, `02`, `sample_wm_clean.parquet` |
| **Person B** | Modelltraining + Evaluierung (beide Modelle) | `03`, `04`, alle `.joblib` Files |
| **Person C** | Streamlit App + Shape-Vergleich + Visualisierung | `05`, `app/` |

> **Wichtig:** Alle drei arbeiten gemeinsam an Notebook `05` (Shape-Vergleich) — das ist der inhaltliche Kern des Projekts und braucht gemeinsame Diskussion.

---

## 11. Zeitplan

| Phase | Zeitraum | Meilenstein |
|---|---|---|
| **Setup & EDA** | KW 20–21 (bis ~17. Mai) | Datenpipeline läuft, EDA-Notebook fertig |
| **1. Präsentation** | **19. Mai 2026** | EDA-Ergebnisse + erste Modelle zeigen |
| **Modelltraining** | KW 21–24 (bis ~14. Juni) | Alle 7 Modelle trainiert, Metriken dokumentiert |
| **Shape-Analyse** | KW 24–25 | Shape Functions verglichen, Kernaussagen formuliert |
| **2. Präsentation** | **23. Juni 2026** | Vollständige Modellergebnisse + erste App-Demo |
| **App + Bericht** | KW 25–28 | App finalisiert, Bericht ~20–25 Seiten |
| **Abgabe Bericht** | **17. Juli 2026, 23:30** | ZIP mit allem |
| **Abschlusspräsentation** | **21. Juli 2026** | 12–15 Min. Vortrag + App-Demo live |

---

## 12. Pakete & Setup

```bash
pip install pandas numpy scikit-learn xgboost lightgbm shap
pip install igann interpret
pip install streamlit plotly
pip install tabpfn
pip install joblib pyarrow  # für .parquet Sampling
```

> **RAM-Hinweis:** Die volle WM CSV (~8,7 GB) passt bei den meisten Laptops nicht komplett in den RAM. Wir arbeiten mit einem **stratifizierten 1%-Sample** (~200k Zeilen) für schnelle Iteration und trainieren finale Modelle auf einem 10%-Sample (~2 Mio. Zeilen) in einem einmaligen Lauf.

---

## 13. Anforderungen des Kurses — Abdeckung

| Anforderung (aus Kick-off) | Umsetzung in diesem Projekt |
|---|---|
| Einfache Modelle | Lineare Regression, Decision Tree ✅ |
| Advanced flexible Modelle | XGBoost, LightGBM, TabPFN ✅ |
| Advanced interpretierbare Modelle | IGANN, EBM ✅ |
| Post-hoc Erklärbarkeit | SHAP für XGBoost/LightGBM ✅ |
| Echte Daten, realer Use Case | RWI-GEO-RED, 20+ Mio. Inserate ✅ |
| Projektbericht ~20–35 Seiten | Geplant ✅ |
| Interim-Präsentationen | 19. Mai + 23. Juni ✅ |
| Software-/App-Deployment | Streamlit App ✅ |
| Systematischer Modellvergleich | Metriktabelle + Shape-Vergleich ✅ |
| Lessons Learned | Abschlusspräsentation ✅ |

---

## 14. Offene Punkte vor dem Start

- [ ] Python-Umgebung bei allen drei Teammitgliedern einrichten (`requirements.txt`)
- [ ] Daten auf allen Laptops verfügbar machen (oder gemeinsamer Netzlaufwerk-Zugriff)
- [ ] Rollen/Verantwortlichkeiten final absprechen
- [ ] Projektmanagement-Tool festlegen (GitHub Issues / Notion / Trello?)
- [ ] Sampling-Strategie festlegen: Soll der Sample Zeitraum 2007–2025 uniform abdecken? (Empfehlung: ja)

---

*Dokument erstellt: Mai 2026 | Datenquelle: RWI-GEO-RED v14, FDZ Ruhr*  
*Kurs: Gestaltungsansätze der Advanced Data Analytics — TU Dresden, SS 2026*
