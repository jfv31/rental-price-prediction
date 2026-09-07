# Implementation Artifact: Preprocessing-Pipeline & Imputation-Architektur
## GADA Topic 6 — Wohnungsmietmarkt (RWI-GEO-RED v14)

> **Erstellt:** Mai 2026  
> **Architektur-Verantwortung:** Winston (Architect Agent)  
> **Implementierung:** Amelia (Dev Agent)  
> **Status:** ✅ Bereit zur Implementierung — alle Entscheidungen getroffen  
> **Priorität:** Voraussetzung für Notebooks 03, 04 und 05

---

## 1. Kontext & Ausgangssituation

### Was bereits existiert
| Datei | Status | Hinweis |
|---|---|---|
| `data/processed/AUTO_final_enriched.parquet` | ✅ Vorhanden | 833.985 Zeilen, 52 Spalten — Output von Notebook 02 |
| `src/data/preprocessing.py` | ⚠️ Veraltet | `FEATURE_COLS` ist Platzhalter-Liste, muss komplett ersetzt werden |
| `notebooks/03_model_A_price.ipynb` | ⚠️ Partiell | Implementiert, aber falscher DATA_PATH + fehlende Imputation |
| `notebooks/04_model_B_duration.ipynb` | ⚠️ Partiell | Wie Notebook 03 |
| `notebooks/05_shape_comparison.ipynb` | ❌ Leer | Erst nach 03+04 implementieren — **hier ignorieren** |

### Was Notebook 02 bereits geleistet hat
Notebook 02 hat alle FDZ-Missing-Codes (z.B. `-7`, `-5`) in echte `NaN`-Werte umgewandelt und alle Engineering-Schritte durchgeführt. Das Parquet enthält daher:
- Keine negativen Missing-Codes mehr
- Alle engineered Features bereits vorhanden (`alter_bauwerk`, `hat_parkplatz`, usw.)
- Alle Spalten bereits in maschinell lesbaren Float/Int-Typen (keine String-Kategorien außer `ergg_1km` und `freiab` — beide werden nicht als Features genutzt)

**Wichtig:** Amelia muss Notebook 02 nicht kennen oder ändern. Die Pipeline beginnt bei der fertigen Parquet-Datei.

---

## 2. Architektur-Entscheidung (final, nicht mehr diskutieren)

### Entscheidung: Ein Parquet, Imputation nach Train/Test-Split

**Abgelehnte Alternative:** Zwei separate Parquets (NaN-Parquet für Baummodelle, imputed Parquet für IGANN/LR/EBM/TabPFN).

**Gewählte Architektur:**
```
AUTO_final_enriched.parquet
           │
           ▼
    Filter + FEATURE_COLS
           │
           ▼
   stratifizierter Split (nach ajahr)
      /           \
 X_train          X_test
      │                │
      ├──► X_train_tree (NaN bleibt) ──►XGBoost,LightGBM
      │
      └──► SimpleImputer.fit(X_train)
           X_train_imputed──► IGANN, LinReg, EBM, TabPFN
           SimpleImputer.transform(X_test)
           X_test_imputed
```

**Begründung der Entscheidung:**
1. **Kein Imputation-Leakage**: `SimpleImputer` wird ausschließlich auf `X_train` gefittet und dann auf `X_test` angewendet — der Testset "sieht" kein Trainingswissen
2. **Konsistente Testmenge**: Beide Modellgruppen werden auf demselben `X_test` evaluiert (nicht zwei verschiedenen)  
3. **Kein Synchronisationsproblem**: Eine einzige Parquet-Datei ist die einzige Source of Truth
4. **Wartbarkeit**: Preprocessing-Logik bleibt zentral in `preprocessing.py`

---

## 3. Vollständige Spaltenanalyse des Parquets

```
AUTO_final_enriched.parquet — 52 Spalten
```

### 3.1 Zielvariablen (NICHT in FEATURE_COLS)
| Spalte | Rolle | Anmerkung |
|---|---|---|
| `mietepro_m2` | **TARGET_PRICE** (Modell A) | Direkt vorhanden, kein Recalculate nötig |
| `laufzeittage` | **TARGET_DURATION Basis** (Modell B) | `log1p()` im Notebook anwenden |
| `mietekalt` | Raw-Basis für mietepro_m2 | Nur zur Verifikation, nicht als Feature |

### 3.2 Identifikatoren (NICHT in FEATURE_COLS)
| Spalte | Begründung |
|---|---|
| `obid` | Primärschlüssel, kein Prädiktor |

### 3.3 Data-Leakage-Spalten (NICHT in FEATURE_COLS)
| Spalte | Begründung |
|---|---|
| `ejahr` | Enddatum der Anzeige — bei Inseraterstellung unbekannt |
| `emonat` | Enddatum der Anzeige — bei Inseraterstellung unbekannt |

### 3.4 Technisch unbrauchbar (NICHT in FEATURE_COLS)
| Spalte | Dtype | Begründung |
|---|---|---|
| `ergg_1km` | str | 50.043 unique String-Werte (Gitterkoordinaten wie "4032_3109"), keine ordinale Semantik |

### 3.5 Roh-Features ohne eigenständigen Informationswert (NICHT in FEATURE_COLS)
Diese Spalten sind im Parquet noch enthalten, wurden aber durch engineered Features ersetzt:
| Roh-Spalte | Ersetzt durch | Entfernen aus Feature-Matrix |
|---|---|---|
| `baujahr` | `alter_bauwerk` | ✅ Ja |
| `parkplatzpreis` | `parkplatz` (sauberer Binary) | ✅ Ja |
| `hat_parkplatz` | `parkplatz` | ✅ Ja (61.9% NaN, unklar) |
| `letzte_modernisierung` | `wurde_modernisiert` | ✅ Ja |
| `ev_kennwert` | `hat_energieausweis` | ✅ Ja |
| `freiab` | `freiab_monate` | ✅ Ja (String, 5.5% NaN) |

> **Hinweis zu `hat_parkplatz`:** Diese Spalte hat 61.9% NaN und wurde als redundant zu `parkplatz` (0% NaN, sauberer Binary) identifiziert. `parkplatz` direkt verwenden.

---

## 4. Finale FEATURE_COLS (39 Features — copy-paste-ready)

```python
# ============================================================
# FEATURE_COLS — finale Liste für AUTO_final_enriched.parquet
# Winston / Mai 2026 — verifiziert gegen alle 52 Parquet-Spalten
# ============================================================

# --- Numerisch (kontinuierlich, einige mit NaN) ---
NUMERICAL_FEATURES = [
    "wohnflaeche",       # 0.0% NaN  — Kerngröße, muss vorhanden sein
    "zimmeranzahl",      # 0.0% NaN
    "alter_bauwerk",     # 0.0% NaN  — ajahr - baujahr (bereits in Parquet)
    "completeness_score",# 0.0% NaN  — Datenqualitäts-Signal
    "dist_transit",      # 0.0% NaN  — räumlich
    "dens_transit",      # 0.0% NaN  — räumlich
    "dist_supermarket",  # 0.0% NaN  — räumlich
    "dens_supermarket",  # 0.0% NaN  — räumlich
    "dist_park",         # 0.0% NaN  — räumlich
    "dens_park",         # 0.0% NaN  — räumlich
    "dist_to_center",    # 0.0% NaN  — räumlich
    "etage",             # 17.5% NaN — NaN bleibt für Baummodelle
    "anzahletagen",      # 36.0% NaN — NaN bleibt für Baummodelle
    "schlafzimmer",      # 42.7% NaN — NaN bleibt für Baummodelle
    "badezimmer",        # 28.2% NaN — NaN bleibt für Baummodelle
    "freiab_monate",     # 15.7% NaN — NaN bleibt für Baummodelle
]

# --- Ordinal/Nominal (als Float/Int im Parquet, einige mit NaN) ---
CATEGORICAL_FEATURES = [
    "objektzustand",          # 25.9% NaN
    "heizungsart",            # 16.8% NaN
    "ausstattung",            # 48.1% NaN
    "energieeffizienzklasse", # 88.6% NaN  — hohe Missingness dokumentieren!
    "kategorie_Wohnung",      # 27.6% NaN
    "kid2019",                # 0.0% NaN   — Kreisschlüssel (402 Klassen)
    "blid",                   # 0.0% NaN   — Bundesland (16 Klassen)
    "erg_amd",                # 29.1% NaN  — Arbeitsmarktregion
    "ajahr",                  # 0.0% NaN   — Jahr der Inseraterstellung (Markttrend)
    "amonat",                 # 0.0% NaN   — Monat (Saisonalität)
]

# --- Binär (0/1 Integer, alle 0% NaN) ---
BINARY_FEATURES = [
    "balkon",
    "einbaukueche",
    "keller",
    "aufzug",
    "garten",
    "gaestewc",
    "parkplatz",
    "rollstuhlgerecht",
    "foerderung",
    "denkmalobjekt",
    "haustier_erlaubt",
    "wurde_modernisiert",  # 0% NaN — engineered Binary
    "hat_energieausweis",  # 0% NaN — engineered Binary
]

# --- Kombinierte Liste für sklearn/Modell-Input ---
FEATURE_COLS = NUMERICAL_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES
# → 16 + 10 + 13 = 39 Features total

# --- Features MIT NaN (relevant für Imputation-Entscheidung) ---
FEATURES_WITH_NAN = [
    # Numerical NaN
    "etage", "anzahletagen", "schlafzimmer", "badezimmer", "freiab_monate",
    # Categorical NaN
    "objektzustand", "heizungsart", "ausstattung",
    "energieeffizienzklasse", "kategorie_Wohnung", "erg_amd",
]
# Binary-Features: alle 0% NaN → kein Imputation-Bedarf

# --- Zielvariablen ---
TARGET_PRICE    = "mietepro_m2"      # Direkter Wert im Parquet (€/m²)
TARGET_DURATION = "log_laufzeittage" # Wird im Notebook berechnet: log1p(laufzeittage)
```

> **Hinweis zu `ajahr` und `amonat`:** Obwohl `ajahr` für den Train/Test-Split genutzt wird (Stratifizierung), bleibt es auch in der Feature-Matrix, da es Markttrend-Informationen trägt. Das ist methodisch korrekt — beim Split wählen wir eine stratifizierte Zufallsstichprobe (nicht eine temporale Aufteilung), sodass kein Leakage entsteht.

> **Hinweis zu `energieeffizienzklasse`:** 88.6% NaN im 5%-Sample. Im vollen Datensatz möglicherweise höher befüllt. Im Modell behalten, aber in der Diskussion dokumentieren. Baummodelle tolerieren die hohe Missingness nativ.

---

## 5. Imputation-Architektur (vollständiger Code)

### 5.1 Konzept
```
X_train (mit NaN)
    │
    ├──► Baummodelle (XGBoost, LightGBM)
    │    └── X_train direkt, NaN wird von Modell intern verarbeitet
    │
    └──► SimpleImputer.fit_transform(X_train[FEATURES_WITH_NAN])
         └── X_train_imputed — für IGANN, LinReg, EBM, TabPFN
             SimpleImputer.transform(X_test[FEATURES_WITH_NAN])
             └── X_test_imputed
```

**Imputation-Strategie pro Feature-Typ:**
| Feature-Gruppe | Strategie | Begründung |
|---|---|---|
| Numerisch mit NaN (`etage`, `badezimmer`, usw.) | `median` | Robust gegen Ausreißer |
| Kategorial/Ordinal mit NaN (`objektzustand`, usw.) | `most_frequent` | Erhält die dominante Klasse |
| Binär | Kein Imputer nötig | Alle 0% NaN |

### 5.2 Vollständiger Imputation-Code-Block (in Notebooks 03 & 04 einfügen)

Dieser Block kommt **direkt nach dem Train/Test-Split**:

```python
# ============================================================
# IMPUTATION — nach Train/Test-Split (kein Leakage möglich)
# ============================================================
from sklearn.impute import SimpleImputer
from src.data.preprocessing import FEATURES_WITH_NAN, NUMERICAL_FEATURES, CATEGORICAL_FEATURES

# Numerische NaN-Features
NUM_NAN_COLS = [c for c in NUMERICAL_FEATURES if c in FEATURES_WITH_NAN]
# Kategoriale NaN-Features
CAT_NAN_COLS = [c for c in CATEGORICAL_FEATURES if c in FEATURES_WITH_NAN]

# Imputer-Objekte (fit NUR auf X_train)
num_imputer = SimpleImputer(strategy="median")
cat_imputer = SimpleImputer(strategy="most_frequent")

# ---- Gruppe 1: Baummodelle — kein Imputer ----
X_train_tree = X_train.copy()
X_test_tree  = X_test.copy()

# ---- Gruppe 2: IGANN, LinReg, EBM, TabPFN — imputiert ----
X_train_imp = X_train.copy()
X_test_imp  = X_test.copy()

# Numerisch: fit auf Train, transform auf Train + Test
X_train_imp[NUM_NAN_COLS] = num_imputer.fit_transform(X_train[NUM_NAN_COLS])
X_test_imp[NUM_NAN_COLS]  = num_imputer.transform(X_test[NUM_NAN_COLS])

# Kategorial: fit auf Train, transform auf Train + Test
X_train_imp[CAT_NAN_COLS] = cat_imputer.fit_transform(X_train[CAT_NAN_COLS])
X_test_imp[CAT_NAN_COLS]  = cat_imputer.transform(X_test[CAT_NAN_COLS])

print("Imputation abgeschlossen.")
print(f"  X_train_tree NaN: {X_train_tree.isna().sum().sum()}")
print(f"  X_train_imp  NaN: {X_train_imp.isna().sum().sum()}")   # muss 0 sein
print(f"  X_test_imp   NaN: {X_test_imp.isna().sum().sum()}")    # muss 0 sein
```

### 5.3 Modell-zu-Datenpfad Matrix

| Modell | Input X_train | Input X_test | NaN-Toleranz |
|---|---|---|---|
| `LinearRegression` | `X_train_imp` | `X_test_imp` | ❌ kein NaN |
| `DecisionTreeRegressor` | `X_train_tree` | `X_test_tree` | ✅ NaN möglich |
| `XGBRegressor` | `X_train_tree` | `X_test_tree` | ✅ NaN möglich |
| `LGBMRegressor` | `X_train_tree` | `X_test_tree` | ✅ NaN möglich |
| `TabPFNRegressor` | `X_train_imp` | `X_test_imp` | ❌ kein NaN |
| `ExplainableBoostingRegressor` (EBM) | `X_train_imp` | `X_test_imp` | ❌ kein NaN |
| `IGANN` | `X_train_imp` | `X_test_imp` | ❌ kein NaN |

---

## 6. Implementierungsschritte (für Amelia — chronologisch ausführen)

### Schritt 1: `src/data/preprocessing.py` komplett ersetzen

Die aktuelle Datei hat einen veralteten `FEATURE_COLS`-Platzhalter. Die Datei muss wie folgt aussehen:

```python
# src/data/preprocessing.py
# Zentrales Feature-Registry für GADA-Topic-6-Pipeline
# Verifiziert gegen AUTO_final_enriched.parquet (52 Spalten, 833.985 Zeilen)
# Winston — Mai 2026

import pandas as pd
import numpy as np

# ============================================================
# FEATURE-GRUPPEN
# ============================================================

NUMERICAL_FEATURES = [
    "wohnflaeche",
    "zimmeranzahl",
    "alter_bauwerk",
    "completeness_score",
    "dist_transit",
    "dens_transit",
    "dist_supermarket",
    "dens_supermarket",
    "dist_park",
    "dens_park",
    "dist_to_center",
    "etage",
    "anzahletagen",
    "schlafzimmer",
    "badezimmer",
    "freiab_monate",
]

CATEGORICAL_FEATURES = [
    "objektzustand",
    "heizungsart",
    "ausstattung",
    "energieeffizienzklasse",
    "kategorie_Wohnung",
    "kid2019",
    "blid",
    "erg_amd",
    "ajahr",
    "amonat",
]

BINARY_FEATURES = [
    "balkon",
    "einbaukueche",
    "keller",
    "aufzug",
    "garten",
    "gaestewc",
    "parkplatz",
    "rollstuhlgerecht",
    "foerderung",
    "denkmalobjekt",
    "haustier_erlaubt",
    "wurde_modernisiert",
    "hat_energieausweis",
]

FEATURE_COLS = NUMERICAL_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES

FEATURES_WITH_NAN = [
    "etage",
    "anzahletagen",
    "schlafzimmer",
    "badezimmer",
    "freiab_monate",
    "objektzustand",
    "heizungsart",
    "ausstattung",
    "energieeffizienzklasse",
    "kategorie_Wohnung",
    "erg_amd",
]

TARGET_PRICE    = "mietepro_m2"
TARGET_DURATION = "log_laufzeittage"

# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def load_parquet(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Gibt X (Feature-Matrix) aus dem fertig-enriched Parquet zurück."""
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Fehlende Spalten im Parquet: {missing}")
    return df[FEATURE_COLS].copy()


def prepare_target_price(df: pd.DataFrame) -> pd.Series:
    """Gibt y für Modell A zurück (mietepro_m2 — bereits im Parquet)."""
    return df[TARGET_PRICE].copy()


def prepare_target_duration(df: pd.DataFrame) -> pd.Series:
    """Gibt y für Modell B zurück (log1p von laufzeittage)."""
    return np.log1p(df["laufzeittage"]).rename(TARGET_DURATION)


def stratified_sample(df: pd.DataFrame, frac: float, seed: int = 42) -> pd.DataFrame:
    """Stratifizierter Sample nach ajahr (Erhalt der Jahresverteilung)."""
    return (
        df.groupby("ajahr", group_keys=False)
        .apply(lambda x: x.sample(frac=frac, random_state=seed))
        .reset_index(drop=True)
    )
```

### Schritt 2: DATA_PATH in Notebooks 03 und 04 korrigieren

In beiden Notebooks ist aktuell folgender (falscher) Pfad gesetzt:
```python
DATA_PATH = '../data/processed/wm_clean.parquet'  # ← FALSCH
```

Ersetzen durch:
```python
DATA_PATH = '../data/processed/AUTO_final_enriched.parquet'  # ← KORREKT
```

**Genaue Position:** Zelle 02 (Imports & Konfiguration), im Konfigurations-Block direkt nach dem `RUN_FINAL`-Schalter.

### Schritt 3: Notebooks 03 und 04 — Zielgröße und Features laden

Den Daten-Ladeblock in Zelle 03/04 ersetzen durch:

```python
from src.data.preprocessing import (
    load_parquet, prepare_features, prepare_target_price,
    prepare_target_duration, stratified_sample, FEATURE_COLS
)

# Daten laden
df_full = load_parquet(DATA_PATH)
print(f"Geladene Zeilen: {len(df_full):,} | Spalten: {df_full.shape[1]}")

# Sampling (RUN_FINAL-Schalter aus Zelle 02)
frac = SAMPLE_FRAC_FINAL if RUN_FINAL else SAMPLE_FRAC_DEV
df = stratified_sample(df_full, frac=frac, seed=RANDOM_STATE)
print(f"Stichprobe ({frac*100:.0f}%): {len(df):,} Zeilen")

# Features und Zielgröße extrahieren
X = prepare_features(df)

# [NUR Notebook 03]: Modell A — Preis
y = prepare_target_price(df)

# [NUR Notebook 04]: Modell B — Laufzeit
y = prepare_target_duration(df)

print(f"Feature-Matrix: {X.shape} | NaN-Anteil: {X.isna().mean().mean()*100:.1f}%")
```

### Schritt 4: Imputation-Block nach Train/Test-Split einfügen

**Position:** Direkt nach dem Train/Test-Split (nach `X_train, X_test, y_train, y_test = train_test_split(...)`).

Den vollständigen Code aus **Abschnitt 5.2** einfügen.

### Schritt 5: Modell-Aufrufe auf korrekten X_train/X_test umstellen

Nach dem Imputation-Block muss jeder Modell-Aufruf die richtige Datengruppe nutzen:

```python
# ---- Linear Regression (Gruppe 2: imputiert) ----
lr = LinearRegression()
lr.fit(X_train_imp, y_train)
evaluate_model(lr, X_test_imp, y_test, name="LinearRegression")

# ---- Decision Tree (Gruppe 1: Baummodell, NaN ok) ----
dt = DecisionTreeRegressor(max_depth=8, random_state=RANDOM_STATE)
dt.fit(X_train_tree, y_train)
evaluate_model(dt, X_test_tree, y_test, name="DecisionTree")

# ---- XGBoost (Gruppe 1: NaN nativ) ----
xgb_model = XGBRegressor(
    n_estimators=500, learning_rate=0.05, max_depth=6,
    random_state=RANDOM_STATE, enable_categorical=False
)
xgb_model.fit(X_train_tree, y_train)
evaluate_model(xgb_model, X_test_tree, y_test, name="XGBoost_default")

# ---- LightGBM (Gruppe 1: NaN nativ) ----
lgbm_model = LGBMRegressor(
    n_estimators=500, learning_rate=0.05, num_leaves=63,
    random_state=RANDOM_STATE, verbose=-1
)
lgbm_model.fit(X_train_tree, y_train)
evaluate_model(lgbm_model, X_test_tree, y_test, name="LightGBM_default")

# ---- TabPFN (Gruppe 2: imputiert, Sub-Sample ≤ 10.000) ----
TABPFN_MAX = 10_000
idx = np.random.default_rng(RANDOM_STATE).choice(len(X_train_imp), size=min(TABPFN_MAX, len(X_train_imp)), replace=False)
tabpfn = TabPFNRegressor(device="cpu")
tabpfn.fit(X_train_imp.iloc[idx], y_train.iloc[idx])
evaluate_model(tabpfn, X_test_imp, y_test, name="TabPFN")

# ---- EBM (Gruppe 2: imputiert) ----
ebm = ExplainableBoostingRegressor(random_state=RANDOM_STATE)
ebm.fit(X_train_imp, y_train)
evaluate_model(ebm, X_test_imp, y_test, name="EBM_default")

# ---- IGANN (Gruppe 2: imputiert) ----
igann = IGANN(task="regression", n_hid=10, n_estimators=3000, random_state=RANDOM_STATE)
igann.fit(X_train_imp, y_train)
evaluate_model(igann, X_test_imp, y_test, name="IGANN_default")
```

### Schritt 6: Optuna-Tuning — Datenpfad prüfen

Im Optuna-Block muss `X_train_imp` für EBM genutzt werden (falls Tuning via Cross-Validation):
```python
# Optuna Objective für EBM
def objective_ebm(trial):
    ...
    model = ExplainableBoostingRegressor(...)
    scores = cross_val_score(model, X_train_imp, y_train, ...)  # ← X_train_imp!
    return scores.mean()
```

XGBoost- und LightGBM-Objectives nutzen `X_train_tree`.

### Schritt 7: Modell-Speicherung — Imputer mitspeichern

**Wichtig:** Die `SimpleImputer`-Objekte müssen zusammen mit den Modellen gespeichert werden, damit die App später Predictions machen kann:

```python
import joblib
from pathlib import Path

MODELS_DIR = Path("../models")
MODELS_DIR.mkdir(exist_ok=True)

# Imputer speichern (einmalig, gilt für alle Gruppe-2-Modelle)
joblib.dump(num_imputer, MODELS_DIR / "num_imputer_price.joblib")   # Nb 03
joblib.dump(cat_imputer, MODELS_DIR / "cat_imputer_price.joblib")   # Nb 03
# Nb 04: "_duration" Suffix statt "_price"

# Modelle speichern (wie bisher)
joblib.dump(lr,         MODELS_DIR / "lr_price.joblib")
joblib.dump(dt,         MODELS_DIR / "dt_price.joblib")
joblib.dump(xgb_tuned,  MODELS_DIR / "xgb_price.joblib")
joblib.dump(lgbm_tuned, MODELS_DIR / "lgbm_price.joblib")
joblib.dump(tabpfn,     MODELS_DIR / "tabpfn_price.joblib")
joblib.dump(ebm_tuned,  MODELS_DIR / "ebm_price.joblib")
joblib.dump(igann,      MODELS_DIR / "igann_price.joblib")
```

---

## 7. Verifikations-Checkliste (nach Implementierung)

Amelia soll nach jedem Schritt folgende Checks ausführen:

### Nach Schritt 1 (preprocessing.py)
```python
# In Python-Shell ausführen:
from src.data.preprocessing import FEATURE_COLS, FEATURES_WITH_NAN
assert len(FEATURE_COLS) == 39, f"Erwartet 39, got {len(FEATURE_COLS)}"
assert "mietepro_m2" not in FEATURE_COLS
assert "ejahr" not in FEATURE_COLS
assert "ergg_1km" not in FEATURE_COLS
assert all(c in FEATURE_COLS for c in FEATURES_WITH_NAN)
print("✅ preprocessing.py korrekt")
```

### Nach Schritt 4 (Imputation)
```python
assert X_train_imp.isna().sum().sum() == 0, "X_train_imp hat noch NaN!"
assert X_test_imp.isna().sum().sum() == 0,  "X_test_imp hat noch NaN!"
assert X_train_tree.isna().sum().sum() > 0,  "X_train_tree sollte NaN haben"
print("✅ Imputation korrekt")
```

### Nach vollständigem Notebook-Durchlauf
```python
from pathlib import Path
expected = [
    "lr_price.joblib", "dt_price.joblib", "xgb_price.joblib",
    "lgbm_price.joblib", "tabpfn_price.joblib", "ebm_price.joblib",
    "igann_price.joblib", "num_imputer_price.joblib", "cat_imputer_price.joblib"
]
missing = [f for f in expected if not Path(f"../models/{f}").exists()]
assert not missing, f"Fehlende Modell-Dateien: {missing}"
print("✅ Alle Modelle gespeichert")
```

---

## 8. Kritische Hinweise für die Implementierung

1. **`enable_categorical=False` bei XGBoost**: Alle Kategorien sind bereits als Int/Float codiert → kein `enable_categorical` nötig. XGBoost würde sonst bei Float-Kategorien Fehler werfen.

2. **LightGBM `verbose=-1`**: Ohne diesen Parameter produziert LightGBM extrem viel Output in Notebooks.

3. **`energie_effizienzklasse` im IGANN/EBM**: Mit 88.6% NaN → nach Imputation wird `most_frequent` die dominante Klasse einsetzen. Das verzerrt die Shape Function für dieses Feature. In Notebook 05 darauf hinweisen.

4. **`kid2019` mit 402 Klassen**: EBM und IGANN können damit umgehen, aber Trainingszeit steigt. XGBoost/LightGBM (Gruppe 1) haben damit keine Probleme.

5. **TabPFN Sub-Sample**: Maximal 10.000 Zeilen fürs Training. TabPFN-Evaluation trotzdem auf dem vollen `X_test_imp`. Die Differenz zwischen Trainings- und Testgröße ist bei Foundation Models normal.

6. **Shape Export (am Notebook-Ende)**: Die Zellen für Shape-Export (IGANN + EBM) sind bereits in Notebooks 03 und 04 vorhanden — sie müssen auf `X_train_imp` referenzieren, nicht auf `X_train`. Prüfen und ggf. anpassen.

---

## 9. Was NICHT in diesem Artefakt abgedeckt ist

| Thema | Status | Wo dokumentiert |
|---|---|---|
| Notebook 05 (Shape Comparison) | ⏳ Zurückgestellt | Erst nach 03+04 — separates Artefakt |
| Streamlit App | ✅ Skeleton fertig | `app/utils.py`, `app/pages/` |
| `app/utils.py` — Imputer laden | ⚠️ Noch nicht implementiert | Folgt nach Modelltraining |
| Optuna Hyperparameter-Räume | 📋 Im block1-artefakt | `_bmad-output/planning-artifacts/block1-modellierungsrahmen.md` |
| Evaluation-Metriken | ✅ Fertig | `src/evaluation/metrics.py` |

---

*Artefakt-Version: 1.0 | Erstellt von Winston (Architect Agent) | Mai 2026*  
*Nächster Agent: Amelia (Dev Agent) — implementiert Schritte 1–7 in dieser Reihenfolge*
