"""
Berechnet Metriken für XGBoost + TabICLv2 und hängt sie an die metrics_model_*.csv an.
Ausführen aus dem Projekt-Root: python src/eval_new_models.py
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR  = os.path.join(ROOT, "models")
DATA_DIR    = os.path.join(ROOT, "data", "processed")

TEMPORAL_CUTOFF = 2022


def evaluate(name, y_true, y_pred):
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)
    print(f"  {name:20s}  MAE={mae:.4f}  RMSE={rmse:.4f}  R²={r2:.4f}")
    return {"Modell": name, "MAE": round(mae, 4), "RMSE": round(rmse, 4), "R²": round(r2, 4)}


def update_csv(path, new_rows):
    df = pd.read_csv(path)
    existing = set(df["Modell"].tolist())
    added = []
    for row in new_rows:
        if row["Modell"] not in existing:
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            added.append(row["Modell"])
        else:
            print(f"  '{row['Modell']}' bereits in {os.path.basename(path)} — übersprungen")
    df.to_csv(path, index=False)
    if added:
        print(f"  Hinzugefügt zu {os.path.basename(path)}: {added}")


def main():
    print("Lade Daten …")
    df = pd.read_parquet(os.path.join(DATA_DIR, "AUTO_final_enriched.parquet"))

    # Selbes Sample wie Notebooks (10% Index)
    idx_path = os.path.join(DATA_DIR, "sample_10pct_index.csv")
    if os.path.exists(idx_path):
        idx = pd.read_csv(idx_path, header=None, low_memory=False).iloc[:, 0]
        idx = pd.to_numeric(idx, errors="coerce").dropna().astype(int).values
        df  = df.loc[df.index.isin(idx)]
        print(f"  Sample: {len(df):,} Zeilen")

    mask_test = df["ajahr"] > TEMPORAL_CUTOFF

    # ------------------------------------------------------------------ #
    # Imputer laden (selbe Logik wie Notebooks)
    # ------------------------------------------------------------------ #
    cat_imp_price    = joblib.load(os.path.join(MODELS_DIR, "cat_imputer_price.joblib"))
    cat_imp_duration = joblib.load(os.path.join(MODELS_DIR, "cat_imputer_duration.joblib"))

    # ------------------------------------------------------------------ #
    # MODEL A — Preis (€/m²)
    # ------------------------------------------------------------------ #
    print("\n=== Model A — Price ===")
    TARGET_A = "mietepro_m2"
    df_a = df.dropna(subset=[TARGET_A]).copy()
    mask_test_a = df_a["ajahr"] > TEMPORAL_CUTOFF
    feature_cols = [c for c in df_a.columns if c not in [TARGET_A, "ajahr", "obid", "spell_id"]]
    X_a = df_a[feature_cols]
    y_a = df_a[TARGET_A]
    X_test_a, y_test_a = X_a[mask_test_a], y_a[mask_test_a]

    new_rows_a = []
    for model_name, joblib_file in [("XGBoost (tuned)", "xgb_price.joblib"),
                                     ("TabICLv2",        "tabicl_price.joblib")]:
        path = os.path.join(MODELS_DIR, joblib_file)
        if not os.path.exists(path):
            print(f"  {joblib_file} nicht gefunden — übersprungen")
            continue
        model = joblib.load(path)
        try:
            preds = model.predict(X_test_a)
        except Exception as e:
            print(f"  {model_name}: predict fehlgeschlagen ({e})")
            continue
        new_rows_a.append(evaluate(model_name, y_test_a, preds))

    if new_rows_a:
        update_csv(os.path.join(MODELS_DIR, "metrics_model_A.csv"), new_rows_a)

    # ------------------------------------------------------------------ #
    # MODEL B — Duration (days)
    # ------------------------------------------------------------------ #
    print("\n=== Model B — Duration ===")
    TARGET_B = "laufzeittage"
    df_b = df.dropna(subset=[TARGET_B]).copy()
    mask_test_b = df_b["ajahr"] > TEMPORAL_CUTOFF
    feature_cols_b = [c for c in df_b.columns if c not in [TARGET_B, "ajahr", "obid", "spell_id"]]
    X_b = df_b[feature_cols_b]
    y_b = df_b[TARGET_B]
    X_test_b, y_test_b = X_b[mask_test_b], y_b[mask_test_b]

    new_rows_b = []
    for model_name, joblib_file in [("XGBoost (tuned)", "xgb_duration.joblib"),
                                     ("TabICLv2",        "tabicl_duration.joblib")]:
        path = os.path.join(MODELS_DIR, joblib_file)
        if not os.path.exists(path):
            print(f"  {joblib_file} nicht gefunden — übersprungen")
            continue
        model = joblib.load(path)
        try:
            preds = model.predict(X_test_b)
        except Exception as e:
            print(f"  {model_name}: predict fehlgeschlagen ({e})")
            continue
        new_rows_b.append(evaluate(model_name, y_test_b, preds))

    if new_rows_b:
        update_csv(os.path.join(MODELS_DIR, "metrics_model_B.csv"), new_rows_b)

    print("\nFertig.")


if __name__ == "__main__":
    main()
