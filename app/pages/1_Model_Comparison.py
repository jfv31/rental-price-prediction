import streamlit as st
import plotly.express as px
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import load_metrics, MODEL_REGISTRY, is_model_available, load_best_params

st.title("📊 Model Performance Comparison")

# Nur Modelle, die im Vergleich sichtbar sein sollen
COMPARISON_MODELS = [
    "Linear Regression",
    "XGBoost",
    "LightGBM",
    "TabICLv2",
    "EBM",
    "IGANN",
]


def _normalize_model_name(name: str) -> str:
    """Normalisiert Modellnamen für robusten Abgleich zwischen UI und Metriktabelle."""
    return name.lower().replace(" (tuned)", "").strip()

tab_price, tab_duration = st.tabs(["Model A — Price (€/m²)", "Model B — Duration (days)"])

for tab, target, label in [
    (tab_price,    "price",    "Rent Price (€/m²)"),
    (tab_duration, "duration", "Time-to-Let (days)"),
]:
    with tab:
        df_metrics = load_metrics(target)

        if df_metrics is None:
            st.warning("⏳ Coming Soon — Models not yet trained. Run Notebooks 03 & 04 first.")
        else:
            def highlight_best(s):
                """Hebt das beste Modell pro Spalte hervor: dunkelgrüner Hintergrund, weißer Text."""
                if s.name in ["MAE", "RMSE"]:
                    is_best = s == s.min()
                else:  # R²
                    is_best = s == s.max()
                return ["background-color: #1a6e38; color: #ffffff; font-weight: bold"
                        if v else "" for v in is_best]

            st.dataframe(
                df_metrics.style
                .apply(highlight_best, subset=["MAE", "RMSE", "R²"])
                .format({"MAE": "{:.3f}", "RMSE": "{:.3f}", "R²": "{:.3f}"})
            )

            fig = px.bar(
                df_metrics.reset_index(),
                x="Model", y="MAE",
                title=f"Model Ranking by MAE — {label}",
                labels={"MAE": f"MAE ({label})"},
                color="MAE", color_continuous_scale="RdYlGn_r",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Availability-Status aller Modelle anzeigen
        st.subheader("Model Availability")
        metrics_names = set()
        if df_metrics is not None:
            metrics_names = {_normalize_model_name(str(idx)) for idx in df_metrics.index.tolist()}

        cols = st.columns(len(COMPARISON_MODELS))
        for col, name in zip(cols, COMPARISON_MODELS):
            file_ready = is_model_available(name, target)
            metrics_ready = _normalize_model_name(name) in metrics_names
            available = file_ready or metrics_ready
            col.metric(name, "✅ Ready" if available else "⏳ Coming Soon")

        # Beste Hyperparameter anzeigen
        st.subheader("Optimal Hyperparameters")
        params_found = False
        for name in COMPARISON_MODELS:
            params = load_best_params(name, target)
            if params:
                params_found = True
                with st.expander(f"{name}"):
                    st.json(params)
        if not params_found:
            st.info("Keine best_params_*.json Dateien gefunden.")
