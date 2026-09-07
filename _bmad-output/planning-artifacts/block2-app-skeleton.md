# Planungsartefakt: Block 2 — App-Skeleton
## Streamlit App (3 Seiten)

> **Erstellt:** Mai 2026  
> **Verantwortlich (Implementierung):** Amelia (Dev Agent)  
> **Zuständig (Planung):** Hannes  
> **Abhängigkeiten:** Block 1 (Notebooks 03/04) liefert `.joblib` Modelle & vorberechnete Artefakte  
> **Deployment:** Nur lokal (kein Cloud-Deployment)  
> **UI-Sprache:** Englisch

---

## 1. Technischer Stack

| Komponente | Tool | Version (Empfehlung) |
|---|---|---|
| App-Framework | `streamlit` | >=1.35 |
| Interaktive Plots | `plotly` | >=5.0 |
| Modell-Erklärbarkeit | `shap` | >=0.45 |
| Modell-Persistenz | `joblib` | Standard |
| Datenverarbeitung | `pandas`, `numpy` | Standard |

---

## 2. Projektstruktur (App-Ordner)

```
app/
├── app.py                        ← Haupt-Entry-Point (Landing Page)
├── utils.py                      ← Zentrale Lade- und Hilfsfunktionen
└── pages/
    ├── 1_Modellvergleich.py      ← Seite 1: Model Performance Overview
    ├── 2_Shape_Explorer.py       ← Seite 2: Shape Function Explorer
    └── 3_Wohnungs_Simulator.py   ← Seite 3: Apartment Simulator

models/                           ← Gespeicherte Modelle (aus Notebooks 03/04)
├── igann_price.joblib
├── igann_duration.joblib
├── ebm_price.joblib
├── ebm_duration.joblib
├── xgb_price.joblib
├── xgb_duration.joblib
├── lgbm_price.joblib
├── lgbm_duration.joblib
├── tabpfn_price.joblib
├── tabpfn_duration.joblib
├── linear_price.joblib
├── linear_duration.joblib
├── dtree_price.joblib
└── dtree_duration.joblib

data/
└── processed/
    ├── metrics_model_A.csv       ← Vorberechnete Metriken (aus Notebook 03)
    ├── metrics_model_B.csv       ← Vorberechnete Metriken (aus Notebook 04)
    ├── shapes_igann_price.parquet    ← Vorberechnete Shape Functions
    ├── shapes_igann_duration.parquet
    ├── shapes_ebm_price.parquet
    └── shapes_ebm_duration.parquet
```

---

## 3. utils.py — Zentrale Ladefunktionen

```python
# app/utils.py
import joblib
import pandas as pd
import os

# ============================================================
# PFAD-KONFIGURATION — hier anpassen falls Struktur abweicht
# ============================================================
MODELS_DIR  = os.path.join(os.path.dirname(__file__), "..", "models")
DATA_DIR    = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

MODEL_REGISTRY = {
    "Linear Regression":  ("linear_price.joblib",   "linear_duration.joblib"),
    "Decision Tree":      ("dtree_price.joblib",     "dtree_duration.joblib"),
    "XGBoost":            ("xgb_price.joblib",       "xgb_duration.joblib"),
    "LightGBM":           ("lgbm_price.joblib",      "lgbm_duration.joblib"),
    "TabPFN":             ("tabpfn_price.joblib",     "tabpfn_duration.joblib"),
    "EBM":                ("ebm_price.joblib",        "ebm_duration.joblib"),
    "IGANN":              ("igann_price.joblib",      "igann_duration.joblib"),
}

SHAPE_REGISTRY = {
    ("IGANN", "price"):    "shapes_igann_price.parquet",
    ("IGANN", "duration"): "shapes_igann_duration.parquet",
    ("EBM",   "price"):    "shapes_ebm_price.parquet",
    ("EBM",   "duration"): "shapes_ebm_duration.parquet",
}


def load_model(model_name: str, target: str):
    """
    Lädt ein gespeichertes Modell. Gibt None zurück wenn nicht gefunden.
    target: "price" oder "duration"
    """
    idx = 0 if target == "price" else 1
    filename = MODEL_REGISTRY[model_name][idx]
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        return None  # Caller zeigt "Coming Soon"
    return joblib.load(path)


def load_metrics(target: str) -> pd.DataFrame | None:
    """Lädt vorberechnete Metriktabelle. Gibt None zurück wenn nicht gefunden."""
    filename = f"metrics_model_{'A' if target == 'price' else 'B'}.csv"
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, index_col="Modell")


def load_shape_data(model_name: str, target: str, feature: str) -> pd.DataFrame | None:
    """
    Lädt vorberechnete Shape-Function-Daten für ein Feature.
    Gibt None zurück wenn nicht gefunden.
    """
    filename = SHAPE_REGISTRY.get((model_name, target))
    if not filename:
        return None
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    if feature not in df["feature"].unique():
        return None
    return df[df["feature"] == feature]


def is_model_available(model_name: str, target: str) -> bool:
    """Prüft ob eine Modelldatei existiert."""
    idx = 0 if target == "price" else 1
    filename = MODEL_REGISTRY[model_name][idx]
    return os.path.exists(os.path.join(MODELS_DIR, filename))
```

---

## 4. app.py — Landing Page

```python
# app/app.py
import streamlit as st

st.set_page_config(
    page_title="GADA — Rental Market Analysis",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 German Rental Market — Interpretable ML Analysis")
st.markdown("""
**GADA Project | TU Dresden SS 2026**

This app explores what drives rental prices and time-to-let in the German housing market
using the RWI-GEO-RED dataset (~20M listings, ImmoScout24, 2007–2025).

### Pages
- **Model Comparison** — Performance overview across all 7 models
- **Shape Explorer** — Compare IGANN & EBM shape functions for price vs. duration
- **Apartment Simulator** — Get predictions and explanations for a custom apartment

> Use the sidebar to navigate between pages.
""")

st.info("Navigate using the sidebar on the left.")
```

---

## 5. Seite 1 — Model Comparison (`1_Modellvergleich.py`)

### Layout-Struktur:

```
[Tab: Price Model A] [Tab: Duration Model B]
├── Metriktabelle (MAE / RMSE / R²) — aus metrics_model_X.csv
├── Bar Chart: Modelle nach MAE sortiert (Plotly)
└── Hinweis: Fehlende Modelle = "Coming Soon" Banner
```

### Skeleton-Code:

```python
# app/pages/1_Modellvergleich.py
import streamlit as st
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import load_metrics, MODEL_REGISTRY, is_model_available

st.title("📊 Model Performance Comparison")

tab_price, tab_duration = st.tabs(["Model A — Price (€/m²)", "Model B — Duration (days)"])

for tab, target, label in [
    (tab_price,    "price",    "Rent Price (€/m²)"),
    (tab_duration, "duration", "Time-to-Let (days)"),
]:
    with tab:
        df_metrics = load_metrics(target)

        if df_metrics is None:
            st.warning("⏳ Coming Soon — Models not yet trained.")
        else:
            st.dataframe(
                df_metrics.style
                .highlight_min(subset=["MAE", "RMSE"], color="#d4edda")
                .highlight_max(subset=["R²"],           color="#d4edda")
                .format({"MAE": "{:.3f}", "RMSE": "{:.3f}", "R²": "{:.3f}"})
            )

            fig = px.bar(
                df_metrics.reset_index(),
                x="Modell", y="MAE",
                title=f"Model Ranking by MAE — {label}",
                labels={"MAE": f"MAE ({label})", "Modell": "Model"},
                color="MAE", color_continuous_scale="RdYlGn_r",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Availability-Status aller Modelle anzeigen
        st.subheader("Model Availability")
        cols = st.columns(len(MODEL_REGISTRY))
        for col, name in zip(cols, MODEL_REGISTRY):
            available = is_model_available(name, target)
            col.metric(name, "✅ Ready" if available else "⏳ Coming Soon")
```

---

## 6. Seite 2 — Shape Explorer (`2_Shape_Explorer.py`)

### Layout-Struktur:

```
[Feature Dropdown] [Model Toggle: IGANN | EBM | Both] [Target Toggle: Price | Duration | Both]
├── Shape Function Plot (Plotly, interaktiv)
│   → Wenn "Both Models": zwei Linien überlagert
│   → Wenn "Both Targets": zwei Subplots nebeneinander
└── Hinweis: "Coming Soon" wenn .parquet nicht vorhanden
```

### Skeleton-Code:

```python
# app/pages/2_Shape_Explorer.py
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import load_shape_data

st.title("🔍 Shape Function Explorer")

st.markdown("""
Compare how each feature affects **rental price** and **time-to-let**
according to interpretable models (IGANN and EBM).
""")

col1, col2, col3 = st.columns(3)

# TODO: Feature-Liste aus Notebook 02 übernehmen
FEATURES_PLACEHOLDER = ["wohnflaeche", "zimmeranzahl", "baujahr", "etage", "balkon", "keller"]

with col1:
    selected_feature = st.selectbox("Feature", FEATURES_PLACEHOLDER)
with col2:
    selected_models = st.multiselect("Model", ["IGANN", "EBM"], default=["IGANN", "EBM"])
with col3:
    selected_targets = st.multiselect("Target", ["price", "duration"], default=["price", "duration"])

if not selected_models or not selected_targets:
    st.warning("Please select at least one model and one target.")
    st.stop()

# Subplot-Grid: eine Spalte pro Target
fig = make_subplots(
    rows=1,
    cols=len(selected_targets),
    subplot_titles=[f"{'Price (€/m²)' if t == 'price' else 'Duration (days)'}" for t in selected_targets],
    shared_yaxes=False,
)

colors = {"IGANN": "#636EFA", "EBM": "#EF553B"}
any_data = False

for col_idx, target in enumerate(selected_targets, start=1):
    for model_name in selected_models:
        df_shape = load_shape_data(model_name, target, selected_feature)
        if df_shape is not None:
            any_data = True
            fig.add_trace(
                go.Scatter(
                    x=df_shape["x"],
                    y=df_shape["y"],
                    mode="lines",
                    name=f"{model_name} — {'Price' if target == 'price' else 'Duration'}",
                    line=dict(color=colors[model_name]),
                    hovertemplate=f"{selected_feature}: %{{x}}<br>Effect: %{{y:.3f}}<extra>{model_name}</extra>",
                ),
                row=1, col=col_idx,
            )

if not any_data:
    st.warning("⏳ Coming Soon — Shape function data not yet computed. Run Notebooks 03 & 04 first.")
else:
    fig.update_layout(height=450, title_text=f"Shape Functions — {selected_feature}")
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Shape functions show the marginal effect of each feature, holding all others constant. "
    "IGANN uses neural network-based shapes; EBM uses boosted regression trees."
)
```

> **Hinweis für Notebook 03/04:** Shape-Daten müssen als `.parquet` mit Spalten `feature`, `x`, `y` exportiert werden.  
> Beispiel-Export-Code (am Ende von Notebook 03/04 hinzufügen):
> ```python
> # Shape-Export für Streamlit App
> shape_records = []
> for feature in FEATURE_COLS:
>     x_vals, y_vals = igann_model.get_shape_function(feature)  # API je nach IGANN-Version prüfen
>     for x, y in zip(x_vals, y_vals):
>         shape_records.append({"feature": feature, "x": x, "y": y})
> pd.DataFrame(shape_records).to_parquet("data/processed/shapes_igann_price.parquet", index=False)
> ```

---

## 7. Seite 3 — Apartment Simulator (`3_Wohnungs_Simulator.py`)

### Layout-Struktur:

```
Sidebar:
├── Living Area (m²): Slider
├── Rooms: Dropdown
├── Year Built: Slider
├── Floor: Dropdown
├── Federal State: Dropdown
└── Amenities: Checkboxes (Balcony, Basement, Elevator, Built-in Kitchen)

Main Area:
├── [Dropdown: Select Model] — alle 7 Modelle, Coming Soon wenn fehlt
├── Col 1 — Model A Output:
│   ├── "Expected Rent: 8.40 €/m² | 714 €/month"
│   └── SHAP Waterfall Plot
└── Col 2 — Model B Output:
    ├── "Expected Time-to-Let: ~11 days"
    └── SHAP Waterfall Plot
```

### Skeleton-Code:

```python
# app/pages/3_Wohnungs_Simulator.py
import streamlit as st
import numpy as np
import pandas as pd
import shap
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import load_model, MODEL_REGISTRY, is_model_available

st.title("🏠 Apartment Simulator")
st.markdown("Configure an apartment and get price & time-to-let predictions with explanations.")

# ── Sidebar Inputs ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Apartment Configuration")

    living_area = st.slider("Living Area (m²)", 20, 200, 70)
    rooms       = st.selectbox("Number of Rooms", [1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6], index=4)
    year_built  = st.slider("Year Built", 1900, 2024, 1990)
    floor       = st.selectbox("Floor", list(range(0, 15)), index=2)
    federal_state = st.selectbox("Federal State", [
        "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen",
        "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen",
        "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen",
        "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"
    ])
    st.subheader("Amenities")
    has_balcony = st.checkbox("Balcony")
    has_basement = st.checkbox("Basement")
    has_elevator = st.checkbox("Elevator")
    has_kitchen = st.checkbox("Built-in Kitchen")

    selected_model = st.selectbox(
        "Model",
        [name for name in MODEL_REGISTRY],
    )

# ── Verfügbarkeits-Check ────────────────────────────────────────────────────
price_available    = is_model_available(selected_model, "price")
duration_available = is_model_available(selected_model, "duration")

if not price_available and not duration_available:
    st.warning(f"⏳ Coming Soon — {selected_model} models not yet trained.")
    st.stop()

# ── Feature-Vektor bauen ─────────────────────────────────────────────────────
# TODO: Spaltenreihenfolge & Namen aus Notebook 02 anpassen
input_dict = {
    "wohnflaeche":   living_area,
    "zimmeranzahl":  rooms,
    "baujahr":       year_built,
    "etage":         floor,
    "balkon":        int(has_balcony),
    "keller":        int(has_basement),
    "aufzug":        int(has_elevator),
    "einbaukueche":  int(has_kitchen),
    # TODO: blid / Bundesland-Encoding aus Notebook 02 übernehmen
}
X_input = pd.DataFrame([input_dict])

# ── Predictions & Output ─────────────────────────────────────────────────────
col_price, col_duration = st.columns(2)

for col, target, label, unit, transform in [
    (col_price,    "price",    "Rental Price",    "€/m²",  lambda x: x),
    (col_duration, "duration", "Time-to-Let",     "days",  np.expm1),
]:
    with col:
        st.subheader(f"Model A — {label}" if target == "price" else f"Model B — {label}")
        model = load_model(selected_model, target)

        if model is None:
            st.info(f"⏳ Coming Soon — {selected_model} ({target}) not yet trained.")
            continue

        pred_raw = model.predict(X_input)[0]
        pred = transform(pred_raw)

        if target == "price":
            monthly = pred * living_area
            st.metric("Expected Rent", f"{pred:.2f} {unit}", f"≈ €{monthly:.0f}/month")
        else:
            st.metric("Expected Time-to-Let", f"{pred:.0f} {unit}")

        # SHAP Waterfall (nur für SHAP-kompatible Modelle — XGBoost, LightGBM)
        if selected_model in ["XGBoost", "LightGBM"]:
            try:
                explainer   = shap.Explainer(model)
                shap_values = explainer(X_input)
                # Plotly Waterfall aus SHAP-Werten
                shap_df = pd.DataFrame({
                    "feature": X_input.columns,
                    "value":   shap_values.values[0],
                }).sort_values("value", key=abs, ascending=False).head(8)

                fig = go.Figure(go.Waterfall(
                    name="SHAP",
                    orientation="h",
                    measure=["relative"] * len(shap_df),
                    y=shap_df["feature"],
                    x=shap_df["value"],
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                ))
                fig.update_layout(title="Feature Contributions (SHAP)", height=300)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.caption(f"SHAP not available: {e}")
        else:
            st.caption(f"Feature contributions are embedded in the {selected_model} shape functions (see Shape Explorer).")
```

---

## 8. Graceful Fallback — Zusammenfassung

Amelia soll **überall** wo Modelle oder Daten fehlen folgenden Ansatz verwenden:

| Situation | UI-Verhalten |
|---|---|
| `.joblib` Datei fehlt | `st.warning("⏳ Coming Soon — Model not yet trained.")` |
| `.parquet` Shape-Daten fehlen | `st.warning("⏳ Coming Soon — Shape data not yet computed.")` |
| `.csv` Metriken fehlen | `st.warning("⏳ Coming Soon — Run Notebooks 03 & 04 first.")` |
| Modell geladen, aber Prediction schlägt fehl | `st.error("Prediction failed: {e}")` — kein Crash |

> **Ziel:** Die App startet und ist navigierbar auch wenn noch kein einziges Modell trainiert wurde.

---

## 9. Abhängigkeiten von Block 1 (Notebooks 03/04)

| Artefakt | Erzeugt von | Benötigt von App-Seite |
|---|---|---|
| `models/*.joblib` | Notebooks 03/04 | Seite 3 (Simulator) |
| `metrics_model_A.csv` | Notebook 03 | Seite 1 |
| `metrics_model_B.csv` | Notebook 04 | Seite 1 |
| `shapes_igann_price.parquet` | Notebook 03 | Seite 2 |
| `shapes_igann_duration.parquet` | Notebook 04 | Seite 2 |
| `shapes_ebm_price.parquet` | Notebook 03 | Seite 2 |
| `shapes_ebm_duration.parquet` | Notebook 04 | Seite 2 |
| Feature-Liste & Encoding | Notebook 02 | Alle Seiten (TODO-Marker) |

---

## 10. Entscheidungslog (für Beleg)

| Entscheidung | Gewählt | Begründung |
|---|---|---|
| Datenarchitektur | Hybrid: pre-computed für Seiten 1&2, live inference für Seite 3 | Seiten 1&2 brauchen keine Echtzeit-Inference; Seite 3 muss auf individuelle Eingaben reagieren |
| Fehlende Modelle | Graceful "Coming Soon" Fallback | App soll schon vor Modelltraining navigierbar sein |
| Shape Explorer | IGANN + EBM, beide Targets, vorberechnetes `.parquet` | Ladezeit-Optimierung; IGANN shape API kann langsam sein |
| Simulator Modellauswahl | Alle 7 Modelle + Dropdown | Direkter Vergleich für Präsentation |
| SHAP im Simulator | Nur für XGBoost/LightGBM | SHAP nicht nativ für IGANN/EBM/TabPFN; Shape Explorer übernimmt diese Rolle |
| Deployment | Nur lokal | Keine Cloud-Anforderungen, kein Secrets-Management nötig |
| UI-Sprache | Englisch | Einheitlich für internationale Lesbarkeit |

---

*Artefakt-Status: **Bereit für Implementierung** durch Amelia (Dev Agent)*  
*Nächster Schritt: Block 3 (Evaluierungsframework) oder direkt Amelia mit Block 1 + Block 2 beauftragen*
