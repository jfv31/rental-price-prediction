"""
Feature-Importance-Analyse für AUTO_final_enriched.parquet
===========================================================
Analysiert alle relevanten Features gegenüber beiden Targets:
  - mietepro_m2     (Mietpreis pro m²)
  - log_laufzeittage (log-transformierte Inseratsdauer)

Methoden:
  1. Deskriptive Statistiken & Missingness
  2. Pearson- / Spearman-Korrelation mit den Targets
  3. Mutual Information (sklearn)
  4. LightGBM-Gain-Importance (schnell, ohne Hyperparameter-Tuning)
  5. SHAP-Summary (TreeExplainer, Stichprobe 10k Zeilen)

Ergebnisse werden unter _bmad-output/test-artifacts/feature_importance/ abgelegt.

Aufruf:
  python src/data/feature_importance_analysis.py
  (Arbeitsverzeichnis = Projekt-Root)
"""

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # kein interaktives Fenster nötig
import matplotlib.pyplot as plt
import lightgbm as lgb
import shap
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import OrdinalEncoder

warnings.filterwarnings("ignore")

# ── Pfade ────────────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).resolve().parents[2]
DATA_PATH     = PROJECT_ROOT / "data" / "processed" / "AUTO_final_enriched.parquet"
OUTPUT_DIR    = PROJECT_ROOT / "_bmad-output" / "test-artifacts" / "feature_importance"

# ── Feature-Listen (aus src/data/preprocessing.py) ───────────────────────────
NUMERICAL_FEATURES = [
    "wohnflaeche", "zimmeranzahl", "alter_bauwerk", "completeness_score",
    "dist_transit", "dens_transit", "dist_supermarket", "dens_supermarket",
    "dist_park", "dens_park", "dist_to_center", "etage", "anzahletagen",
    "schlafzimmer", "badezimmer", "freiab_monate",
]
CATEGORICAL_FEATURES = [
    "objektzustand", "heizungsart", "ausstattung", "energieeffizienzklasse",
    "kategorie_Wohnung", "blid", "erg_amd", "ajahr", "amonat",
]
BINARY_FEATURES = [
    "balkon", "einbaukueche", "keller", "aufzug", "garten", "gaestewc",
    "parkplatz", "rollstuhlgerecht", "foerderung", "denkmalobjekt",
    "haustier_erlaubt", "wurde_modernisiert", "hat_energieausweis",
]
FEATURE_COLS  = NUMERICAL_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES
TARGET_PRICE    = "mietepro_m2"
TARGET_DURATION = "log_laufzeittage"

SHAP_SAMPLE_N = 10_000
LGBM_PARAMS   = {
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_child_samples": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}

# ─────────────────────────────────────────────────────────────────────────────

def setup_output() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def load_data() -> pd.DataFrame:
    print(f"Lade Daten: {DATA_PATH}")
    df = pd.read_parquet(DATA_PATH)
    print(f"  Shape: {df.shape}")
    # log_laufzeittage erzeugen falls nicht vorhanden
    if TARGET_DURATION not in df.columns and "laufzeittage" in df.columns:
        df[TARGET_DURATION] = np.log1p(df["laufzeittage"])
    return df


def compute_descriptives(df: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Missingness + Basis-Deskriptivstatistik je Feature."""
    print("Berechne deskriptive Statistiken …")
    records = []
    for col in FEATURE_COLS:
        if col not in df.columns:
            continue
        s = df[col]
        n_miss  = s.isna().sum()
        n_total = len(s)
        dtype   = str(s.dtype)
        record  = {
            "feature":     col,
            "dtype":       dtype,
            "n_total":     n_total,
            "n_missing":   n_miss,
            "pct_missing": round(n_miss / n_total * 100, 2),
            "n_unique":    s.nunique(),
        }
        if col in NUMERICAL_FEATURES + BINARY_FEATURES:
            record.update({
                "mean":   round(s.mean(), 4),
                "std":    round(s.std(), 4),
                "min":    s.min(),
                "p25":    s.quantile(0.25),
                "median": s.median(),
                "p75":    s.quantile(0.75),
                "max":    s.max(),
            })
        records.append(record)

    desc_df = pd.DataFrame(records)
    path = out / "descriptives.csv"
    desc_df.to_csv(path, index=False)
    print(f"  → {path}")
    return desc_df


def compute_correlations(df: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Pearson- & Spearman-Korrelation aller numerischen + binären Features mit Targets."""
    print("Berechne Korrelationen …")
    num_cols = [c for c in NUMERICAL_FEATURES + BINARY_FEATURES if c in df.columns]
    rows = []
    for col in num_cols:
        for target in [TARGET_PRICE, TARGET_DURATION]:
            if target not in df.columns:
                continue
            sub = df[[col, target]].dropna()
            pearson  = sub[col].corr(sub[target], method="pearson")
            spearman = sub[col].corr(sub[target], method="spearman")
            rows.append({
                "feature":  col,
                "target":   target,
                "pearson":  round(pearson,  4),
                "spearman": round(spearman, 4),
                "n_valid":  len(sub),
            })

    corr_df = pd.DataFrame(rows)
    path = out / "correlations.csv"
    corr_df.to_csv(path, index=False)
    print(f"  → {path}")
    return corr_df


def _encode_for_mi(df: pd.DataFrame) -> pd.DataFrame:
    """Ordinal-encodiert kategorische Spalten für MI-Berechnung."""
    X = df[FEATURE_COLS].copy()
    cat_cols = [c for c in CATEGORICAL_FEATURES if c in X.columns]
    if cat_cols:
        enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        X[cat_cols] = enc.fit_transform(X[cat_cols].astype(str))
    # NaN → Median (MI braucht vollständige Daten)
    for c in X.columns:
        if X[c].isna().any():
            fill = X[c].median() if X[c].dtype.kind in "biufc" else -1
            X[c] = X[c].fillna(fill)
    return X


def compute_mutual_information(df: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Mutual Information der Features gegenüber beiden Targets."""
    print("Berechne Mutual Information …")
    X = _encode_for_mi(df)
    rows = []
    for target in [TARGET_PRICE, TARGET_DURATION]:
        if target not in df.columns:
            continue
        y = df[target].fillna(df[target].median())
        mi = mutual_info_regression(X, y, random_state=42, n_jobs=-1)
        for feat, val in zip(FEATURE_COLS, mi):
            if feat in X.columns:
                rows.append({"feature": feat, "target": target, "mutual_info": round(val, 6)})

    mi_df = pd.DataFrame(rows)
    path = out / "mutual_information.csv"
    mi_df.to_csv(path, index=False)
    print(f"  → {path}")
    return mi_df


def _build_lgbm_dataset(df: pd.DataFrame, target: str):
    """Bereitet X/y für LightGBM vor – behält kategorische Spalten als category dtype."""
    available_feats = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available_feats].copy()
    for c in CATEGORICAL_FEATURES:
        if c in X.columns:
            X[c] = X[c].astype("category")
    y = df[target]
    mask = y.notna()
    return X[mask], y[mask], available_feats


def compute_lgbm_importance(df: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Trainiert LightGBM (gain-Importance) für beide Targets."""
    print("Trainiere LightGBM für Feature-Importance …")
    rows = []
    for target in [TARGET_PRICE, TARGET_DURATION]:
        if target not in df.columns:
            continue
        X, y, feats = _build_lgbm_dataset(df, target)
        model = lgb.LGBMRegressor(**LGBM_PARAMS)
        model.fit(X, y)

        imp_gain  = model.booster_.feature_importance(importance_type="gain")
        imp_split = model.booster_.feature_importance(importance_type="split")
        # normiert auf [0, 1]
        gain_norm  = imp_gain  / (imp_gain.sum()  + 1e-9)
        split_norm = imp_split / (imp_split.sum() + 1e-9)

        for feat, g, s, gr, sr in zip(feats, imp_gain, imp_split, gain_norm, split_norm):
            rows.append({
                "feature":          feat,
                "target":           target,
                "importance_gain":  round(float(g),  4),
                "importance_split": round(float(s),  4),
                "gain_norm":        round(float(gr), 6),
                "split_norm":       round(float(sr), 6),
            })

        # Plot speichern
        _plot_lgbm_importance(feats, gain_norm, target, out)

    lgbm_df = pd.DataFrame(rows)
    path = out / "lgbm_importance.csv"
    lgbm_df.to_csv(path, index=False)
    print(f"  → {path}")
    return lgbm_df


def _plot_lgbm_importance(feats, gain_norm, target: str, out: Path):
    order = np.argsort(gain_norm)[-20:]  # Top 20
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh([feats[i] for i in order], [gain_norm[i] for i in order], color="#4C72B0")
    ax.set_xlabel("Gain-Importance (normiert)")
    ax.set_title(f"LightGBM Top-20 Feature Importance\nTarget: {target}")
    ax.tick_params(axis="y", labelsize=9)
    plt.tight_layout()
    safe_target = target.replace("/", "_")
    path = out / f"lgbm_importance_{safe_target}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  → {path}")


def compute_shap(df: pd.DataFrame, out: Path) -> pd.DataFrame:
    """SHAP TreeExplainer auf 10k-Stichprobe für beide Targets."""
    print(f"Berechne SHAP-Werte (Stichprobe n={SHAP_SAMPLE_N:,}) …")
    rows = []
    sample = df.sample(n=min(SHAP_SAMPLE_N, len(df)), random_state=42)

    for target in [TARGET_PRICE, TARGET_DURATION]:
        if target not in df.columns:
            continue
        X, y, feats = _build_lgbm_dataset(sample, target)
        model = lgb.LGBMRegressor(**LGBM_PARAMS)
        model.fit(X, y)

        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        mean_abs    = np.abs(shap_values).mean(axis=0)
        mean_abs_norm = mean_abs / (mean_abs.sum() + 1e-9)

        for feat, val, val_norm in zip(feats, mean_abs, mean_abs_norm):
            rows.append({
                "feature":        feat,
                "target":         target,
                "shap_mean_abs":  round(float(val),      6),
                "shap_norm":      round(float(val_norm), 6),
            })

        # SHAP Summary Plot
        _plot_shap_summary(X, shap_values, feats, target, out)

    shap_df = pd.DataFrame(rows)
    path = out / "shap_importance.csv"
    shap_df.to_csv(path, index=False)
    print(f"  → {path}")
    return shap_df


def _plot_shap_summary(X, shap_values, feats, target: str, out: Path):
    fig, ax = plt.subplots(figsize=(10, 8))
    order    = np.argsort(np.abs(shap_values).mean(axis=0))[-20:]
    mean_abs = np.abs(shap_values).mean(axis=0)
    ax.barh([feats[i] for i in order], [mean_abs[i] for i in order], color="#DD8452")
    ax.set_xlabel("Mean |SHAP| (rohe Einheit)")
    ax.set_title(f"SHAP Top-20 Feature Importance\nTarget: {target}")
    ax.tick_params(axis="y", labelsize=9)
    plt.tight_layout()
    safe_target = target.replace("/", "_")
    path = out / f"shap_importance_{safe_target}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  → {path}")


def build_combined_ranking(mi_df, lgbm_df, shap_df, out: Path):
    """Erstellt ein kombiniertes Ranking über alle Methoden (z-score-normiert)."""
    print("Erstelle kombiniertes Ranking …")
    combined_rows = []

    for target in [TARGET_PRICE, TARGET_DURATION]:
        mi_sub   = mi_df[mi_df["target"] == target].set_index("feature")["mutual_info"]
        lgbm_sub = lgbm_df[lgbm_df["target"] == target].set_index("feature")["gain_norm"]
        shap_sub = shap_df[shap_df["target"] == target].set_index("feature")["shap_norm"]

        all_feats = sorted(set(mi_sub.index) | set(lgbm_sub.index) | set(shap_sub.index))
        df_rank = pd.DataFrame(index=all_feats)
        df_rank["mi"]   = mi_sub.reindex(all_feats, fill_value=0)
        df_rank["lgbm"] = lgbm_sub.reindex(all_feats, fill_value=0)
        df_rank["shap"] = shap_sub.reindex(all_feats, fill_value=0)

        # Min-Max-Normierung je Methode, dann mitteln
        for col in ["mi", "lgbm", "shap"]:
            rng = df_rank[col].max() - df_rank[col].min()
            df_rank[f"{col}_scaled"] = (df_rank[col] - df_rank[col].min()) / (rng + 1e-9)

        df_rank["combined_score"] = df_rank[["mi_scaled", "lgbm_scaled", "shap_scaled"]].mean(axis=1)
        df_rank["rank"]           = df_rank["combined_score"].rank(ascending=False).astype(int)
        df_rank["target"]         = target
        df_rank["feature"]        = df_rank.index
        combined_rows.append(df_rank.reset_index(drop=True))

    combined = pd.concat(combined_rows, ignore_index=True)
    cols_out  = ["rank", "feature", "target", "mi_scaled", "lgbm_scaled", "shap_scaled", "combined_score"]
    combined  = combined[cols_out].sort_values(["target", "rank"])

    path = out / "combined_ranking.csv"
    combined.to_csv(path, index=False)
    print(f"  → {path}")
    return combined


def write_summary_report(desc_df, corr_df, mi_df, lgbm_df, shap_df, combined, out: Path):
    """Schreibt einen lesbaren Markdown-Bericht mit den Top-10-Features je Methode."""
    print("Schreibe Summary-Report …")
    lines = [
        "# Feature Importance Analysis – AUTO_final_enriched.parquet",
        "",
        f"Analysiert: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"Datei: `data/processed/AUTO_final_enriched.parquet`  ",
        f"Features: {len(FEATURE_COLS)} | Targets: {TARGET_PRICE}, {TARGET_DURATION}",
        "",
    ]

    # Missingness Summary
    high_miss = desc_df[desc_df["pct_missing"] > 5][["feature", "pct_missing"]].sort_values(
        "pct_missing", ascending=False
    )
    lines += ["## Missingness (> 5 %)", ""]
    if high_miss.empty:
        lines.append("Keine Features mit mehr als 5 % fehlenden Werten.")
    else:
        lines.append(high_miss.to_markdown(index=False))
    lines.append("")

    for target in [TARGET_PRICE, TARGET_DURATION]:
        lines += [f"## Target: `{target}`", ""]

        # Korrelation Top 10
        sub = corr_df[corr_df["target"] == target].copy()
        sub["abs_spearman"] = sub["spearman"].abs()
        top_corr = sub.nlargest(10, "abs_spearman")[["feature", "pearson", "spearman"]]
        lines += ["### Top-10 Spearman-Korrelation", "", top_corr.to_markdown(index=False), ""]

        # MI Top 10
        sub_mi = mi_df[mi_df["target"] == target].nlargest(10, "mutual_info")[["feature", "mutual_info"]]
        lines += ["### Top-10 Mutual Information", "", sub_mi.to_markdown(index=False), ""]

        # LightGBM Top 10
        sub_lgbm = lgbm_df[lgbm_df["target"] == target].nlargest(10, "gain_norm")[["feature", "gain_norm", "split_norm"]]
        lines += ["### Top-10 LightGBM Gain-Importance", "", sub_lgbm.to_markdown(index=False), ""]

        # SHAP Top 10
        sub_shap = shap_df[shap_df["target"] == target].nlargest(10, "shap_mean_abs")[["feature", "shap_mean_abs", "shap_norm"]]
        lines += ["### Top-10 SHAP Mean |SHAP|", "", sub_shap.to_markdown(index=False), ""]

        # Combined Top 10
        sub_comb = combined[combined["target"] == target].nsmallest(10, "rank")[
            ["rank", "feature", "combined_score"]
        ]
        lines += ["### Top-10 Kombiniertes Ranking", "", sub_comb.to_markdown(index=False), ""]

    report_path = out / "feature_importance_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → {report_path}")


def main():
    out = setup_output()
    df  = load_data()

    desc_df  = compute_descriptives(df, out)
    corr_df  = compute_correlations(df, out)
    mi_df    = compute_mutual_information(df, out)
    lgbm_df  = compute_lgbm_importance(df, out)
    shap_df  = compute_shap(df, out)
    combined = build_combined_ranking(mi_df, lgbm_df, shap_df, out)
    write_summary_report(desc_df, corr_df, mi_df, lgbm_df, shap_df, combined, out)

    print("\n✓ Analyse abgeschlossen.")
    print(f"  Alle Ergebnisse unter: {out}")


if __name__ == "__main__":
    main()
