"""
Speichert und lädt Cross-Validation-Ergebnisse aus Optuna-Tuning.
Nutzbar für methodische Dokumentation im Beleg.
"""

import json
import os

import optuna
import pandas as pd


def save_cv_results(
    study: optuna.Study,
    model_name: str,
    target: str,
    output_dir: str,
) -> None:
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
                "model": model_name,
                "target": target,
                "best_value": study.best_value,
                "best_params": study.best_params,
                "n_trials": len(study.trials),
            },
            f,
            indent=2,
        )


def load_best_params(
    model_name: str,
    target: str,
    output_dir: str,
) -> dict | None:
    """Lädt gespeicherte Best-Params. Gibt None zurück wenn nicht gefunden."""
    path = os.path.join(output_dir, f"cv_{model_name}_{target}_best.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def load_cv_trials(
    model_name: str,
    target: str,
    output_dir: str,
) -> pd.DataFrame | None:
    """Lädt alle Trial-Ergebnisse als DataFrame. Gibt None zurück wenn nicht gefunden."""
    path = os.path.join(output_dir, f"cv_{model_name}_{target}_trials.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)
