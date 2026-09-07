# Planungsartefakt: Block 1 — Modellierungsrahmen
## Notebooks 03 & 04 (Modell A: Preis | Modell B: Laufzeit)

> **Erstellt:** Mai 2026  
> **Verantwortlich (Implementierung):** Amelia (Dev Agent)  
> **Zuständig (Planung):** Hannes  
> **Abhängigkeiten:** Notebook 02 liefert bereinigtes Feature-Set als `.parquet`  
> **Ziel:** Beide Notebooks sind nach diesem Plan direkt implementierbar — ohne Rückfragen

---

## 1. Kontext & Zielgrößen

Zwei parallele, strukturell identische ML-Pipelines auf dem gleichen Datensatz (`WM_SUF_ohneText.csv`):

| | Notebook 03 — Modell A | Notebook 04 — Modell B |
|---|---|---|
| **Zielgröße** | `mietekalt / wohnflaeche` (€/m²) | `log(laufzeittage + 1)` |
| **Aufgabe** | Regression | Regression |
| **Hinweis** | Zielgröße direkt berechenbar | Log-Transformation wegen Rechtsschieffe |

---

## 2. Notebook-Struktur (Mirror-Pattern)

**Beide Notebooks 03 und 04 folgen exakt dieser Zellstruktur:**

```
01. [MD]  Titel & Kontext
02. [PY]  Imports & Konfiguration (inkl. RUN_FINAL-Schalter)
03. [PY]  Daten laden & Sampling
04. [PY]  Zielgröße definieren & transformieren
05. [PY]  Train/Test-Split
06. [PY]  Baseline-Modelle (Linear Regression, Decision Tree)
07. [PY]  Advanced Flexible Modelle (XGBoost, LightGBM)
08. [PY]  TabPFN (mit eigenem Sub-Sample ≤10.000 Zeilen)
09. [PY]  EBM (Explainable Boosting Machine)
10. [PY]  IGANN
11. [PY]  Hyperparameter-Tuning (Optuna — XGBoost, LightGBM, EBM)
12. [PY]  Modell-Evaluierung & Vergleichstabelle
13. [PY]  Modelle speichern (joblib)
14. [MD]  Erkenntnisse & Notizen für den Beleg
```

---

## 3. Sampling-Strategie & RUN_FINAL-Schalter

### Implementierung (ganz oben in Zelle 02):

```python
# ============================================================
# KONFIGURATION — hier zentral anpassen
# ============================================================
RUN_FINAL = False  # True = 10%-Sample (finale Modelle), False = 1%-Sample (Entwicklung)

SAMPLE_FRAC_DEV   = 0.01   # ~200k Zeilen — schnelle Iteration
SAMPLE_FRAC_FINAL = 0.10   # ~2 Mio. Zeilen — finale Modelle für Abgabe
RANDOM_STATE      = 42
# ============================================================
```

### Sampling-Logik (Zelle 03):

```python
sample_frac = SAMPLE_FRAC_FINAL if RUN_FINAL else SAMPLE_FRAC_DEV

df = pd.read_parquet("data/processed/wm_clean.parquet")

# Stratifiziert nach ajahr für proportionale Jahres-Abdeckung
df_sample = (
    df.groupby("ajahr", group_keys=False)
    .apply(lambda x: x.sample(frac=sample_frac, random_state=RANDOM_STATE))
    .reset_index(drop=True)
)
```

> **Entscheidung:** Das Sampling wird in Notebooks 03/04 selbst implementiert.  
> Notebook 02 liefert nur das bereinigte `.parquet` — kein Sample.

---

## 4. Train/Test-Split

### Entscheidung: Stratifiziert-Random (nicht harter Zeitschnitt)

**Begründung:** Der `ajahr`-stratifizierte Split stellt sicher, dass alle Jahre proportional in Train und Test vertreten sind. Ein harter Zeitschnitt (alle Jahre < X = Train) würde neuere Markttrends ausschließen.

### Implementierung:

```python
from sklearn.model_selection import train_test_split

X = df_sample.drop(columns=[TARGET_COL])
y = df_sample[TARGET_COL]

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.20,
    random_state=RANDOM_STATE,
    stratify=df_sample["ajahr"]  # Jahres-Proportionen erhalten
)
```

> **Dokumentation für Beleg:** Im Methodenteil erwähnen, dass ein echtes temporales Out-of-Sample-Split (z.B. Test = 2023–2025) die externe Validität erhöhen würde, aber für diesen Kurskontext der stratifizierte Random Split gewählt wurde.

---

## 5. Modelle — Überblick & Libraries

| Kategorie | Modell | Library | Tuning |
|---|---|---|---|
| Baseline | Lineare Regression | `sklearn` | Nein |
| Baseline | Decision Tree | `sklearn` | Nein |
| Advanced Flexible | XGBoost | `xgboost` | ✅ Optuna |
| Advanced Flexible | LightGBM | `lightgbm` | ✅ Optuna |
| Advanced Flexible | TabPFN | `tabpfn` | Nein (Sonderfall, s. §6) |
| Advanced Interpretable | EBM | `interpret` | ✅ Optuna |
| Advanced Interpretable | IGANN | `igann` | Manuell (s. §7) |

---

## 6. TabPFN — Sonderbehandlung

### Hintergrund & Limitation

TabPFN (Tabular Prior-data Fitted Networks) ist ein Tabular Foundation Model. Es hat eine **harte Obergrenze von 10.000 Trainingspunkten** und ist nicht für große Datensätze ausgelegt.

### Implementierung:

```python
# TabPFN braucht eigenes Sub-Sample — unabhängig vom RUN_FINAL-Schalter
TABPFN_MAX_ROWS = 10_000

X_train_tabpfn = X_train.sample(n=min(TABPFN_MAX_ROWS, len(X_train)), random_state=RANDOM_STATE)
y_train_tabpfn = y_train.loc[X_train_tabpfn.index]

from tabpfn import TabPFNRegressor
tabpfn_model = TabPFNRegressor()
tabpfn_model.fit(X_train_tabpfn, y_train_tabpfn)
# Evaluation auf dem vollen X_test
```

### Dokumentation für Beleg (Pflicht):

> *"TabPFN wurde auf einem zufälligen Sub-Sample von 10.000 Trainingsbeispielen trainiert, da das Modell architekturbedingt auf diese Größe limitiert ist (Hollmann et al., 2022). Die Evaluation erfolgte auf dem vollständigen Testset. Diese Limitation schränkt die Vergleichbarkeit mit den übrigen Modellen ein und sollte bei der Interpretation der Metriken berücksichtigt werden."*

---

## 7. Hyperparameter-Tuning (Optuna)

### Tuning-Scope

| Modell | Tuning | Methode |
|---|---|---|
| XGBoost | ✅ | Optuna Bayesian Search |
| LightGBM | ✅ | Optuna Bayesian Search |
| EBM | ✅ | Optuna Bayesian Search |
| IGANN | ⚙️ Manuell | Nach Bedarf je nach Zeit & Rechenleistung |

### Optuna-Grundstruktur (für alle drei tuningfähigen Modelle gleich):

```python
import optuna
from sklearn.model_selection import cross_val_score

def objective_xgb(trial):
    params = {
        "n_estimators":     trial.suggest_int("n_estimators", 100, 1000),
        "max_depth":        trial.suggest_int("max_depth", 3, 10),
        "learning_rate":    trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "random_state":     RANDOM_STATE,
    }
    model = XGBRegressor(**params)
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring="neg_mean_absolute_error")
    return scores.mean()

study = optuna.create_study(direction="maximize")
study.optimize(objective_xgb, n_trials=50)  # n_trials je nach Rechenzeit anpassen
best_params_xgb = study.best_params
```

> **Hinweis:** `n_trials=50` ist ein guter Startpunkt. Bei Zeitdruck auf 20–30 reduzieren.  
> **CV:** 5-Fold innerhalb des Trainingssets — kein Zugriff auf Testdaten.

### IGANN — Manuelle Parameter-Strategie:

```python
# IGANN-Hyperparameter werden manuell gesetzt
# Ausgangspunkt: Paper-Empfehlungen (Kruse et al., 2023)
# Anpassung nach Bedarf je nach Trainingszeit und Ergebnissen
# Alle gesetzten Werte und Begründungen hier dokumentieren:

igann_params = {
    "task":          "regression",
    "n_hid":         256,       # Hidden layer size — Paper-Default
    "n_estimators":  3000,      # Anzahl Boostingrunden
    "boost_rate":    0.1,       # Analog zu learning_rate
    "elm_scale":     1.0,
    "random_state":  RANDOM_STATE,
    # Ggf. anpassen: n_hid, n_estimators, boost_rate
}
```

---

## 8. Evaluierungsmetriken

### Metriken für beide Modelle:

```python
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import numpy as np

def evaluate_model(name, y_true, y_pred, target="preis"):
    """
    Berechnet MAE, RMSE, R² und gibt ein dict zurück.
    Für Modell B (Laufzeit): y_pred ist in log-Skala → Rücktransformation vor Ausgabe.
    """
    if target == "duration":
        # Rücktransformation: log(x+1) → x
        y_true_orig = np.expm1(y_true)
        y_pred_orig = np.expm1(y_pred)
    else:
        y_true_orig, y_pred_orig = y_true, y_pred

    return {
        "Modell":  name,
        "MAE":     mean_absolute_error(y_true_orig, y_pred_orig),
        "RMSE":    root_mean_squared_error(y_true_orig, y_pred_orig),
        "R²":      r2_score(y_true_orig, y_pred_orig),
    }
```

### Vergleichstabelle (Ende jedes Notebooks):

```python
import pandas as pd

results = []
# Nach jedem Modell: results.append(evaluate_model("XGBoost", y_test, y_pred_xgb))

df_results = pd.DataFrame(results).set_index("Modell").sort_values("MAE")
df_results.to_csv(f"models/metrics_model_{'A' if NOTEBOOK == 'A' else 'B'}.csv")
display(df_results.style.highlight_min(subset=["MAE", "RMSE"], color="lightgreen")
                        .highlight_max(subset=["R²"], color="lightgreen"))
```

---

## 9. Modell-Persistenz

```python
import joblib
import os

os.makedirs("models", exist_ok=True)

# Naming-Convention: {algo}_{zielgröße}.joblib
# Beispiele:
joblib.dump(igann_model,   "models/igann_price.joblib")     # Notebook 03
joblib.dump(xgb_model,     "models/xgb_price.joblib")
joblib.dump(igann_model,   "models/igann_duration.joblib")  # Notebook 04
joblib.dump(xgb_model,     "models/xgb_duration.joblib")

# Zusätzlich: Best-Params aus Optuna sichern
import json
with open("models/best_params_xgb_price.json", "w") as f:
    json.dump(best_params_xgb, f, indent=2)
```

---

## 10. Offene Abhängigkeiten (von Notebook 02)

Folgende Punkte liefern die Kollegen — Amelia muss hier Platzhalter setzen:

| Was fehlt noch | Platzhalter-Strategie |
|---|---|
| Finale Feature-Liste | `FEATURE_COLS = [...]  # TODO: aus Notebook 02 übernehmen` |
| Encoding-Entscheidungen | Annahme: kategoriale Spalten sind bereits encoded |
| Pfad zum `.parquet` | `DATA_PATH = "data/processed/wm_clean.parquet"  # TODO: anpassen` |
| Spaltenname für `ajahr` | Annahme: bleibt `ajahr` — ggf. anpassen |

---

## 11. Entscheidungslog (für Beleg)

| Entscheidung | Gewählt | Begründung |
|---|---|---|
| Train/Test-Split | Stratifiziert-random, 80/20, `ajahr` | Proportionale Jahresabdeckung |
| Sampling | 1% Dev / 10% Final, RUN_FINAL-Schalter | Iterative Entwicklung ohne RAM-Überlastung |
| TabPFN-Sampling | Separates ≤10k Sub-Sample | Architektur-Limitation des Modells |
| Tuning XGB/LGBM/EBM | Optuna Bayesian Search, 5-Fold CV | Effizienteres Tuning als Grid Search |
| Tuning IGANN | Manuell, nach Zeitbedarf | Hohe Rechenzeit, Paper-Empfehlungen als Ausgangspunkt |
| Notebook-Struktur | Mirror-Pattern 03 ≡ 04 | Vergleichbarkeit für Shape-Analyse in Notebook 05 |
| Modell-Persistenz | `joblib` mit Naming-Convention | Direkte Verwendbarkeit in Streamlit-App |

---

*Artefakt-Status: **Bereit für Implementierung** durch Amelia (Dev Agent)*  
*Nächster Schritt: Block 2 (App-Skeleton) oder direkt Amelia mit diesem Dokument beauftragen*
