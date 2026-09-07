import joblib
import pandas as pd
import os

# ============================================================
# PFAD-KONFIGURATION — hier anpassen falls Struktur abweicht
# ============================================================
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

MODEL_REGISTRY = {
    "Linear Regression": ("lr_price.joblib",      "lr_duration.joblib"),
    "Decision Tree":     ("dt_price.joblib",      "dt_duration.joblib"),
    "XGBoost":           ("xgb_price.joblib",     "xgb_duration.joblib"),
    "LightGBM":          ("lgbm_price.joblib",    "lgbm_duration.joblib"),
    "TabICLv2":          ("tabicl_price.joblib",  "tabicl_duration.joblib"),
    "TabPFN":            ("tabpfn_price.joblib",  "tabpfn_duration.joblib"),
    "EBM":               ("ebm_price.joblib",     "ebm_duration.joblib"),
    "IGANN":             ("igann_price.joblib",   "igann_duration.joblib"),
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
        return None
    return joblib.load(path)


def load_model_safe(model_name: str, target: str):
    """Wie load_model, aber mit verständlicher Fehlermeldung bei unbekanntem model_name."""
    if model_name not in MODEL_REGISTRY:
        raise KeyError(f"Unbekanntes Modell '{model_name}'. Verfügbar: {list(MODEL_REGISTRY.keys())}")
    return load_model(model_name, target)


def load_metrics(target: str) -> "pd.DataFrame | None":
    """Lädt vorberechnete Metriktabelle. Gibt None zurück wenn nicht gefunden."""
    filename = f"metrics_model_{'A' if target == 'price' else 'B'}.csv"
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, index_col="Modell")
    df.index.name = "Model"
    return df


def load_shape_data(model_name: str, target: str, feature: str) -> "pd.DataFrame | None":
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


BEST_PARAMS_FILES = {
    ("XGBoost",  "price"):    "best_params_xgb_price.json",
    ("XGBoost",  "duration"): "best_params_xgb_duration.json",
    ("LightGBM", "price"):    "best_params_lgbm_price.json",
    ("LightGBM", "duration"): "best_params_lgbm_duration.json",
    ("EBM",      "price"):    "best_params_ebm_price.json",
    ("EBM",      "duration"): "best_params_ebm_duration.json",
    ("IGANN",    "price"):    "best_params_igann_price.json",
    ("IGANN",    "duration"): "best_params_igann_duration.json",
}


def load_best_params(model_name: str, target: str) -> "dict | None":
    """Lädt gespeicherte Hyperparameter. Gibt None zurück wenn nicht vorhanden."""
    import json
    filename = BEST_PARAMS_FILES.get((model_name, target))
    if not filename:
        return None
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
