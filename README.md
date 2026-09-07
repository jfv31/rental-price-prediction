Autoren: Hannes Forhoff, Jonathan Feil, Benno Ullrich

# GADA Projekt: Preis- und Nachfrageresonanz im deutschen Wohnungsmietmarkt

Dieses Repository enthält die Belegarbeit, Modellierung und Streamlit-App für das TU-Dresden-Projekt Gestaltungsansätze der Advanced Data Analytics (SS 2026). Ziel ist die Analyse zentraler Einflussfaktoren auf Mietpreis (Euro pro m2) und Vermarktungsdauer im deutschen Mietwohnungsmarkt auf Basis des RWI-GEO-RED Datensatzes.

## 1) Schnellzugriff für Prof. Zschech und wissenschaftliche Mitarbeitende

- Belegarbeit (PDF): [BelegPDF](BelegPDF)
- Einstieg in die App: [app/app.py](app/app.py)
- Startskript der App: [start.sh](start.sh)
- Python-Abhängigkeiten: [requirements.txt](requirements.txt)
- Notebooks: [notebooks](notebooks)
- Modellartefakte: [models](models)
- Datenablage: [data/raw](data/raw) (Inhalte nicht im Repository, siehe Abschnitt 7)

## 2) Belegarbeit

- Die Abgabe-PDF gehört in den Ordner [BelegPDF](BelegPDF).
- Aktuell enthält der Ordner nur eine Platzhalterdatei (.gitkeep), damit er im Git-Repository versioniert wird.

## 3) Voraussetzungen zum Start der App

Empfohlen:

- Python 3.11
- pip (aktuell)
- optional Git Bash unter Windows (für [start.sh](start.sh))

Installation:

python -m venv .venv
Windows PowerShell: .\.venv\Scripts\Activate.ps1
oder Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt

Wichtige Pakete aus [requirements.txt](requirements.txt):

- streamlit, plotly
- pandas, numpy, scikit-learn
- xgboost, lightgbm, interpret (EBM), igann
- optuna, joblib, pyarrow, shap

## 4) App starten und lokal hosten

Variante A (empfohlen):

bash start.sh
optional mit Port: bash start.sh --port 8502

Variante B (direkt über Streamlit):

streamlit run app/app.py --server.port 8501

Lokaler Zugriff im Browser:

http://localhost:8501

Optional für Zugriff im lokalen Netzwerk:

streamlit run app/app.py --server.address 0.0.0.0 --server.port 8501

## 5) Projektstruktur

### A. Ergebnis- und Präsentationsartefakte

- [BelegPDF](BelegPDF): finale schriftliche Belegarbeit als PDF
- [docs/report](docs/report): Report-Assets und LaTeX-Vorlagen

### B. Laufende Demo (App)

- [app/app.py](app/app.py): Hauptseite der Streamlit-App
- [app/pages](app/pages): Unterseiten
  - [app/pages/1_Model_Comparison.py](app/pages/1_Model_Comparison.py)
  - [app/pages/2_Shape_Explorer.py](app/pages/2_Shape_Explorer.py)
  - [app/pages/3_Apartment_Simulator.py](app/pages/3_Apartment_Simulator.py)
- [app/utils.py](app/utils.py): Laden von Modellen, Metriken und Shape-Daten

### C. Analyse- und Trainingspipeline

- [notebooks](notebooks): EDA, Feature Engineering, Modelltraining, Shape- und SHAP-Analysen
- [src](src): modularisierter Python-Code für Datenaufbereitung, Modelle und Evaluation
- [models](models): trainierte Modelle und Hyperparameter-Artefakte

### D. Daten

- [data/raw](data/raw): Ablage für die FDZ-Rohdaten (CSV) — Inhalte nicht im Repository
- [data/processed](data/processed): verarbeitete Daten und vorberechnete Shape-Artefakte — Inhalte nicht im Repository
- [immo-scraper](immo-scraper): Scraper-Skript für einzelne ImmoScout24-Exposés; erzeugte Rohdaten werden nicht versioniert

### E. Dokumentation und Planung

- [docs](docs): Projektplan und Report-Unterlagen
- [reports](reports): Ergebnisplots und LaTeX-Bestandteile
- [_bmad-output](_bmad-output): Planungs- und Implementierungsartefakte des Teams

## 6) Reproduzierbarkeit der Modelle

Für erneutes Training und Evaluation werden mindestens folgende Pakete benötigt:

- numpy==1.26.4 (wichtig für interpret/EBM-Kompatibilität)
- pandas, scikit-learn
- xgboost, lightgbm
- interpret==0.6.9, igann
- optuna, joblib, pyarrow, shap

Installation:

pip install -r requirements.txt

Typischer Ablauf:

1. Datenaufbereitung in [notebooks/01_Data_Loading.ipynb](notebooks/01_Data_Loading.ipynb), [notebooks/02.1_Feature_Engineering.ipynb](notebooks/02.1_Feature_Engineering.ipynb) und [notebooks/02.2_Spatial_Engineering.ipynb](notebooks/02.2_Spatial_Engineering.ipynb)
2. Modelltraining in [notebooks/03_model_A_price.ipynb](notebooks/03_model_A_price.ipynb) und [notebooks/04_model_B_duration.ipynb](notebooks/04_model_B_duration.ipynb)
3. Shape- und Erklärbarkeitsanalyse in [notebooks/05_shape_comparison.ipynb](notebooks/05_shape_comparison.ipynb), [notebooks/07_shap_analysis_price.ipynb](notebooks/07_shap_analysis_price.ipynb) und [notebooks/08_shap_analysis_duration.ipynb](notebooks/08_shap_analysis_duration.ipynb)
4. App-Prüfung über [app/app.py](app/app.py)

## 7) Hinweise zu großen Dateien und Git

- Große Rohdaten und Artefakte sind bewusst per .gitignore ausgefiltert.
- Platzhalterdateien (.gitkeep) in [data/raw](data/raw), [data/processed](data/processed) und [models](models) sind absichtlich vorhanden.
- Nicht im Repository enthalten sind außerdem die FDZ-Dokumentation zum RWI-GEO-RED (Weitergabe erfolgt über den Datennutzungsvertrag des FDZ Ruhr), gescrapte ImmoScout24-Seiteninhalte sowie Kursunterlagen des Lehrstuhls.
- Für Prof. Zschech und wissenschaftliche Mitarbeitende sind in der Regel das Repository sowie die Inhalte in [BelegPDF](BelegPDF) ausreichend.

## 8) Kontext

- Kurs: Gestaltungsansätze der Advanced Data Analytics (TU Dresden, SS 2026)
- Thema: Interpretable ML für Mietpreis und Vermarktungsdauer
- Datengrundlage: RWI-GEO-RED / ImmoScout24 Inserate
