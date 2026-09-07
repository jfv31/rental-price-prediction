# Planungsartefakt: Block 3 — Evaluierungsframework
## src/evaluation/ Modul

> **Erstellt:** Mai 2026  
> **Verantwortlich (Implementierung):** Amelia (Dev Agent)  
> **Zuständig (Planung):** Hannes  
> **Abhängigkeiten:** Block 1 (Notebooks 03/04) nutzt dieses Modul; Block 2 (App) importiert daraus  
> **Bestehender Code:** `src/evaluation/metrics.py` existiert bereits — Amelia erweitert, überschreibt nicht

---

## 1. Modulstruktur (Zielzustand)

```
src/evaluation/
├── __init__.py          ← Exports zentralisieren
├── metrics.py           ← Bereits vorhanden — erweitern
├── plots.py             ← Neu erstellen
└── cv_results.py        ← Neu erstellen
```

---

## 2. `metrics.py` — Erweiterungen zum bestehenden Code

> **Wichtig für Amelia:** Bestehende Funktionen (`regression_metrics`, `metrics_table`, `backtransform_duration`) **nicht anfassen** — nur ergänzen.

### Was fehlt noch:

```python
# Ergänzungen an src/evaluation/metrics.py
import json
import os
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --- Bestehende Funktionen bleiben unverändert ---
# regression_metrics(), metrics_table(), backtransform_duration()

# --- NEU: Wrapper mit automatischer Rücktransformation ---
def evaluate_model(
    name: str,
    y_true,
    y_pred,
    target: str = "price",  # "price" oder "duration"
) -> dict:
    """
    Berechnet MAE, RMSE, R² inkl. Rücktransformation für Modell B (Laufzeit).
    Wrapper um regression_metrics() mit target-awareness.
    
    Dokumentation für Beleg:
        Modell B (duration): Zielgröße ist log(laufzeittage+1).
        Metriken werden auf der rücktransformierten Skala (Tage) berechnet
        um Interpretierbarkeit zu gewährleisten.
    """
    if target == "duration":
        y_true_orig = backtransform_duration(np.array(y_true))
        y_pred_orig = backtransform_duration(np.array(y_pred))
    else:
        y_true_orig, y_pred_orig = np.array(y_true), np.array(y_pred)

    result = regression_metrics(y_true_orig, y_pred_orig, label=name)
    result["target"] = target
    return result


def save_metrics(results: list[dict], path: str) -> None:
    """Speichert Metriktabelle als CSV (für App + Beleg)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    metrics_table(results).to_csv(path)


def load_metrics(path: str) -> pd.DataFrame | None:
    """Lädt gespeicherte Metriktabelle. Gibt None zurück wenn nicht gefunden."""
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, index_col="model")
```

---

## 3. `plots.py` — Neu erstellen

Alle Plotting-Funktionen sind **framework-agnostisch exportierbar** (Plotly Figures), damit sie in Notebooks, der App und für den Beleg (als PNG-Export) gleichermaßen nutzbar sind.

```python
# src/evaluation/plots.py
"""
Wiederverwendbare Evaluierungs-Plots für Notebooks, Streamlit-App und Beleg.
Alle Funktionen geben Plotly-Figure-Objekte zurück.
Export als PNG: fig.write_image("output.png")  (erfordert kaleido)
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_metrics_bar(
    df_metrics: pd.DataFrame,
    metric: str = "MAE",
    title: str = None,
) -> go.Figure:
    """
    Balkendiagramm: Modell-Ranking nach gewählter Metrik.
    
    Args:
        df_metrics: DataFrame mit Modellen als Index, Metriken als Spalten
        metric: "MAE", "RMSE" oder "R2"
        title: Optionaler Titel
    """
    df = df_metrics.reset_index().sort_values(metric, ascending=(metric != "R2"))
    fig = px.bar(
        df,
        x="model", y=metric,
        title=title or f"Model Ranking — {metric}",
        color=metric,
        color_continuous_scale="RdYlGn_r" if metric != "R2" else "RdYlGn",
        labels={"model": "Model", metric: metric},
    )
    fig.update_layout(showlegend=False)
    return fig


def plot_residuals(
    y_true,
    y_pred,
    model_name: str = "",
    target: str = "price",
) -> go.Figure:
    """
    Residuenplot: Predicted vs. Actual + Fehlerverteilung (2 Subplots).
    Standard-Analysewerkzeug — erweiterbar um Subgruppen-Analyse (s. Hinweis).
    
    Erweiterungspunkt (Zukunft):
        Subgruppen-Analyse über zusätzliches `groups`-Parameter:
        def plot_residuals(y_true, y_pred, ..., groups=None, group_col=None)
        → Plot nach Bundesland, Baujahrzehnt, Preisklasse aufzählbar
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    residuals = y_true - y_pred

    unit = "€/m²" if target == "price" else "days"

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Predicted vs. Actual", "Residual Distribution"],
    )

    # Subplot 1: Predicted vs. Actual
    fig.add_trace(
        go.Scatter(
            x=y_true, y=y_pred,
            mode="markers",
            marker=dict(size=3, opacity=0.3, color="#636EFA"),
            name="Predictions",
            hovertemplate=f"Actual: %{{x:.2f}} {unit}<br>Predicted: %{{y:.2f}} {unit}",
        ),
        row=1, col=1,
    )
    # Perfekte-Vorhersage-Linie
    min_val, max_val = min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())
    fig.add_trace(
        go.Scatter(
            x=[min_val, max_val], y=[min_val, max_val],
            mode="lines",
            line=dict(color="red", dash="dash"),
            name="Perfect Prediction",
        ),
        row=1, col=1,
    )

    # Subplot 2: Residuenverteilung
    fig.add_trace(
        go.Histogram(
            x=residuals,
            nbinsx=60,
            marker_color="#EF553B",
            name="Residuals",
            hovertemplate="Residual: %{x:.2f}<br>Count: %{y}",
        ),
        row=1, col=2,
    )

    fig.update_xaxes(title_text=f"Actual ({unit})", row=1, col=1)
    fig.update_yaxes(title_text=f"Predicted ({unit})", row=1, col=1)
    fig.update_xaxes(title_text=f"Residual ({unit})", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=2)
    fig.update_layout(
        title_text=f"Residual Analysis — {model_name}",
        height=400,
        showlegend=False,
    )
    return fig


def plot_actual_vs_predicted(
    y_true,
    y_pred,
    model_name: str = "",
    target: str = "price",
    sample_n: int = 5_000,
) -> go.Figure:
    """
    Scatter: Actual vs. Predicted — auf Sample für Performance.
    Direkt nutzbar als eigenständige Abbildung für den Beleg.
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    if len(y_true) > sample_n:
        idx = np.random.choice(len(y_true), sample_n, replace=False)
        y_true, y_pred = y_true[idx], y_pred[idx]

    unit = "€/m²" if target == "price" else "days"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=y_true, y=y_pred,
        mode="markers",
        marker=dict(size=4, opacity=0.4, color="#636EFA"),
        hovertemplate=f"Actual: %{{x:.2f}} {unit}<br>Pred: %{{y:.2f}} {unit}",
    ))
    lim = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    fig.add_trace(go.Scatter(
        x=lim, y=lim,
        mode="lines",
        line=dict(color="red", dash="dash"),
        name="y = x",
    ))
    fig.update_layout(
        title=f"Actual vs. Predicted — {model_name}",
        xaxis_title=f"Actual ({unit})",
        yaxis_title=f"Predicted ({unit})",
        height=420,
    )
    return fig


def plot_metrics_comparison(
    df_price: pd.DataFrame,
    df_duration: pd.DataFrame,
    metric: str = "MAE",
) -> go.Figure:
    """
    Grouped Bar Chart: Modell A (Preis) vs. Modell B (Laufzeit) nebeneinander.
    Kernabbildung für Beleg und Seite 1 der App.
    Normalisiert auf [0,1] für Vergleichbarkeit unterschiedlicher Einheiten.
    """
    models = df_price.index.tolist()

    def normalize(series):
        return (series - series.min()) / (series.max() - series.min() + 1e-9)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=f"Model A — Price ({metric})",
        x=models,
        y=normalize(df_price[metric]),
        marker_color="#636EFA",
        hovertemplate=f"Price {metric}: %{{customdata:.3f}}<extra></extra>",
        customdata=df_price[metric],
    ))
    fig.add_trace(go.Bar(
        name=f"Model B — Duration ({metric})",
        x=models,
        y=normalize(df_duration[metric]),
        marker_color="#EF553B",
        hovertemplate=f"Duration {metric}: %{{customdata:.3f}}<extra></extra>",
        customdata=df_duration[metric],
    ))
    fig.update_layout(
        barmode="group",
        title=f"Model A vs. Model B — {metric} (normalized)",
        yaxis_title=f"Normalized {metric}",
        xaxis_title="Model",
        height=420,
    )
    return fig
```

---

## 4. `cv_results.py` — Neu erstellen

```python
# src/evaluation/cv_results.py
"""
Speichert und lädt Cross-Validation-Ergebnisse aus Optuna-Tuning.
Nutzbar für methodische Dokumentation im Beleg.
"""

import json
import os
import pandas as pd
import optuna


def save_cv_results(study: optuna.Study, model_name: str, target: str, output_dir: str) -> None:
    """
    Exportiert Optuna-Study-Ergebnisse als JSON und CSV.
    
    Erzeugte Dateien:
        {output_dir}/cv_{model_name}_{target}_trials.csv   ← alle Trials
        {output_dir}/cv_{model_name}_{target}_best.json    ← beste Parameter
    
    Verwendung im Beleg:
        Tabelle aus *_trials.csv zeigt Konvergenzverhalten des Tunings.
        *_best.json dokumentiert finale Hyperparameter reproduzierbar.
    """
    os.makedirs(output_dir, exist_ok=True)
    base = f"cv_{model_name}_{target}"

    # Alle Trials als CSV
    df_trials = study.trials_dataframe()
    df_trials.to_csv(os.path.join(output_dir, f"{base}_trials.csv"), index=False)

    # Beste Parameter als JSON
    with open(os.path.join(output_dir, f"{base}_best.json"), "w") as f:
        json.dump(
            {
                "model":       model_name,
                "target":      target,
                "best_value":  study.best_value,
                "best_params": study.best_params,
                "n_trials":    len(study.trials),
            },
            f,
            indent=2,
        )


def load_best_params(model_name: str, target: str, output_dir: str) -> dict | None:
    """Lädt gespeicherte Best-Params. Gibt None zurück wenn nicht gefunden."""
    path = os.path.join(output_dir, f"cv_{model_name}_{target}_best.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def load_cv_trials(model_name: str, target: str, output_dir: str) -> pd.DataFrame | None:
    """Lädt alle Trial-Ergebnisse als DataFrame. Gibt None zurück wenn nicht gefunden."""
    path = os.path.join(output_dir, f"cv_{model_name}_{target}_trials.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)
```

---

## 5. `__init__.py` — Zentrale Exports

```python
# src/evaluation/__init__.py
from .metrics import (
    regression_metrics,
    metrics_table,
    backtransform_duration,
    evaluate_model,
    save_metrics,
    load_metrics,
)
from .plots import (
    plot_metrics_bar,
    plot_residuals,
    plot_actual_vs_predicted,
    plot_metrics_comparison,
)
from .cv_results import (
    save_cv_results,
    load_best_params,
    load_cv_trials,
)

__all__ = [
    # metrics
    "regression_metrics", "metrics_table", "backtransform_duration",
    "evaluate_model", "save_metrics", "load_metrics",
    # plots
    "plot_metrics_bar", "plot_residuals", "plot_actual_vs_predicted",
    "plot_metrics_comparison",
    # cv
    "save_cv_results", "load_best_params", "load_cv_trials",
]
```

---

## 6. Verwendung in Notebooks 03 & 04

```python
# Typische Nutzung am Ende eines Modelltrainings in Notebook 03/04
from src.evaluation import evaluate_model, save_metrics, plot_residuals, save_cv_results

# Nach jedem Modell-Training:
results = []
results.append(evaluate_model("XGBoost", y_test, y_pred_xgb, target="price"))
results.append(evaluate_model("IGANN",   y_test, y_pred_igann, target="price"))
# ... alle 7 Modelle

# Speichern für App (Seite 1) und Beleg
save_metrics(results, "data/processed/metrics_model_A.csv")

# Residuenplots (für Beleg + Notebook-Dokumentation)
fig_residuals = plot_residuals(y_test, y_pred_xgb, model_name="XGBoost", target="price")
fig_residuals.show()
# Export als PNG für Beleg:
# fig_residuals.write_image("docs/report/figures/residuals_xgb_price.png")

# CV-Ergebnisse aus Optuna speichern
save_cv_results(study_xgb, model_name="xgb", target="price", output_dir="models/")
```

---

## 7. Verwendung in der Streamlit-App

```python
# In app/utils.py — Ergänzung (delegiert an src.evaluation)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.evaluation import load_metrics, plot_metrics_bar, plot_metrics_comparison

# Seite 1 kann direkt importieren:
# from src.evaluation import plot_metrics_bar, plot_metrics_comparison
```

---

## 8. Output-Dateien (Übersicht)

| Datei | Erzeugt durch | Genutzt von |
|---|---|---|
| `data/processed/metrics_model_A.csv` | Notebook 03 → `save_metrics()` | App Seite 1, Beleg |
| `data/processed/metrics_model_B.csv` | Notebook 04 → `save_metrics()` | App Seite 1, Beleg |
| `models/cv_xgb_price_best.json` | Notebook 03 → `save_cv_results()` | Beleg (Hyperparameter-Tabelle) |
| `models/cv_xgb_price_trials.csv` | Notebook 03 → `save_cv_results()` | Beleg (Konvergenzkurve) |
| `models/cv_lgbm_price_best.json` | Notebook 03 | Beleg |
| `models/cv_ebm_price_best.json` | Notebook 03 | Beleg |
| *(analog für `_duration`)* | Notebook 04 | Beleg |

---

## 9. Erweiterungspunkte (explizit dokumentiert für Zukunft)

| Erweiterung | Wo | Wie |
|---|---|---|
| Subgruppen-Residuenanalyse (nach Bundesland, Baujahrzehnt, Preisklasse) | `plots.py → plot_residuals()` | `groups`-Parameter ergänzen |
| Kalibrierungsplots (Predicted Distribution vs. Actual Distribution) | `plots.py` | neue Funktion `plot_calibration()` |
| Feature Importance Plots (für Linear/DTree/XGB) | `plots.py` | neue Funktion `plot_feature_importance()` |

---

## 10. Entscheidungslog (für Beleg)

| Entscheidung | Gewählt | Begründung |
|---|---|---|
| Modul-Ort | `src/evaluation/` | Zentraler Import-Punkt für Notebooks, App und Beleg-Exports |
| Plot-Framework | Plotly | Einheitlich mit App; PNG-Export für Beleg via `kaleido` |
| Residuenanalyse-Tiefe | Standard (2 Subplots) + explizite Erweiterungspunkte | Ausreichend für Kursanforderungen; Subgruppen-Analyse als dokumentierter nächster Schritt |
| CV-Ergebnisse | Vollständig exportiert (JSON + CSV) | Reproduzierbarkeit & Beleg-Dokumentation der Hyperparameter |
| Bestehender Code | Erhalten, nur ergänzt | `regression_metrics()`, `metrics_table()`, `backtransform_duration()` bleiben unverändert |

---

*Artefakt-Status: **Bereit für Implementierung** durch Amelia (Dev Agent)*  
*Alle drei Blöcke (Block 1, 2, 3) sind vollständig geplant — Amelia kann jetzt beauftragt werden*
