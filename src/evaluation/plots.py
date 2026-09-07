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
        x="model",
        y=metric,
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
        rows=1,
        cols=2,
        subplot_titles=["Predicted vs. Actual", "Residual Distribution"],
    )

    # Subplot 1: Predicted vs. Actual
    fig.add_trace(
        go.Scatter(
            x=y_true,
            y=y_pred,
            mode="markers",
            marker=dict(size=3, opacity=0.3, color="#636EFA"),
            name="Predictions",
            hovertemplate=f"Actual: %{{x:.2f}} {unit}<br>Predicted: %{{y:.2f}} {unit}",
        ),
        row=1,
        col=1,
    )
    # Perfekte-Vorhersage-Linie
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    fig.add_trace(
        go.Scatter(
            x=[min_val, max_val],
            y=[min_val, max_val],
            mode="lines",
            line=dict(color="red", dash="dash"),
            name="Perfect Prediction",
        ),
        row=1,
        col=1,
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
        row=1,
        col=2,
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
    fig.add_trace(
        go.Scatter(
            x=y_true,
            y=y_pred,
            mode="markers",
            marker=dict(size=4, opacity=0.4, color="#636EFA"),
            hovertemplate=f"Actual: %{{x:.2f}} {unit}<br>Pred: %{{y:.2f}} {unit}",
        )
    )
    lim = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    fig.add_trace(
        go.Scatter(
            x=lim,
            y=lim,
            mode="lines",
            line=dict(color="red", dash="dash"),
            name="y = x",
        )
    )
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

    def normalize(series: pd.Series) -> pd.Series:
        return (series - series.min()) / (series.max() - series.min() + 1e-9)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name=f"Model A — Price ({metric})",
            x=models,
            y=normalize(df_price[metric]),
            marker_color="#636EFA",
            hovertemplate=f"Price {metric}: %{{customdata:.3f}}<extra></extra>",
            customdata=df_price[metric],
        )
    )
    fig.add_trace(
        go.Bar(
            name=f"Model B — Duration ({metric})",
            x=models,
            y=normalize(df_duration[metric]),
            marker_color="#EF553B",
            hovertemplate=f"Duration {metric}: %{{customdata:.3f}}<extra></extra>",
            customdata=df_duration[metric],
        )
    )
    fig.update_layout(
        barmode="group",
        title=f"Model A vs. Model B — {metric} (normalized)",
        yaxis_title=f"Normalized {metric}",
        xaxis_title="Model",
        height=420,
    )
    return fig
