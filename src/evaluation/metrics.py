import os

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(y_true, y_pred, label: str = "") -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return {"model": label, "MAE": round(mae, 4), "RMSE": round(rmse, 4), "R2": round(r2, 4)}


def metrics_table(results: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(results).set_index("model")


def backtransform_duration(log_pred: np.ndarray) -> np.ndarray:
    return np.expm1(log_pred)


# --- NEU: Wrapper mit automatischer Rücktransformation ---

def evaluate_model(
    name: str,
    y_true,
    y_pred,
    target: str = "price",
) -> dict:
    """
    Berechnet MAE, RMSE, R² inkl. Rücktransformation für Modell B (Laufzeit).
    Wrapper um regression_metrics() mit target-awareness.

    Modell B (duration): Zielgröße ist log(laufzeittage+1).
    Metriken werden auf der rücktransformierten Skala (Tage) berechnet,
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
