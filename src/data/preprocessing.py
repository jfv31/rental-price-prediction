import pandas as pd
import numpy as np

# ============================================================
# FEATURE-GRUPPEN
# Verifiziert gegen AUTO_final_enriched.parquet V1.5 (42 Spalten, 11.5 Mio. Zeilen)
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
    # dist_park, dens_park entfernt (V1.5 — OSM-Daten zu lückenhaft)
    "dist_to_center",
    "etage",
    "anzahletagen",
    "schlafzimmer",
    "badezimmer",
    "freiab_monate",
    # Zeitlicher Anker für Makro-Trend/Inflation; ordinale Bedeutung → NUMERICAL (V1.5)
    "ajahr",
    "amonat",   # Monat als zyklisches numerisches Signal (V1.5)
]

CATEGORICAL_FEATURES = [
    # ajahr, amonat verschoben nach NUMERICAL (V1.5 — ordinale/kontinuierliche Bedeutung,
    # kein OHE gewünscht, LR soll linearen Jahrestrend direkt lernen)
    # ausstattung entfernt (V1.5 — 52.5% Missing, starker Bias)
    # energieeffizienzklasse entfernt (V1.5 — 88.7% Missing)
    "objektzustand",
    "heizungsart",
    "kategorie_Wohnung",
    "blid",
    "erg_amd",
]

BINARY_FEATURES = [
    "balkon",
    "einbaukueche",
    "keller",
    "aufzug",
    "garten",
    "gaestewc",
    # parkplatz entfernt (V1.5 — ersetzt durch hat_parkplatz)
    # rollstuhlgerecht entfernt (V1.5 — nicht im Datensatz)
    "foerderung",
    # denkmalobjekt entfernt (V1.5 — nicht im Datensatz)
    "haustier_erlaubt",
    "wurde_modernisiert",
    "hat_energieausweis",
    "hat_parkplatz",    # Neu V1.5 — engineered aus parkplatz + parkplatzpreis
]

FEATURE_COLS = NUMERICAL_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES

FEATURES_WITH_NAN = [
    "etage",
    "anzahletagen",
    "schlafzimmer",
    "badezimmer",
    "freiab_monate",
    "zimmeranzahl",
    "objektzustand",
    "heizungsart",
    # ausstattung entfernt (V1.5)
    # energieeffizienzklasse entfernt (V1.5)
    "kategorie_Wohnung",
    "erg_amd",
]

# ============================================================
# ENCODING-KONSTANTEN (V1.5)
# ============================================================
# Alle 5 string-typisierten Kategorie-Spalten (defensives Encoding V1.5).
# XGBoost, LightGBM, Decision Tree können keine str-Spalten verarbeiten → OrdinalEncoder nötig.
CAT_STRING_COLS = ["objektzustand", "heizungsart",
                   "kategorie_Wohnung", "blid", "erg_amd"]

# Für LR & IGANN: OHE nur auf diese 4 nominalen Spalten.
# erg_amd wird weggelassen (141 Kategorien → zu viele Dimensionen für LR/IGANN).
OHE_FEATURES = ["objektzustand", "heizungsart", "kategorie_Wohnung", "blid"]

# Für LR + IGANN: erg_amd aus der Feature-Matrix entfernen
LR_DROP_FEATURES = ["erg_amd"]

TARGET_PRICE = "mietepro_m2"
TARGET_DURATION = "log_laufzeittage"

# ============================================================
# HILFSFUNKTIONEN
# ============================================================


def load_parquet(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Fehlende Spalten im Parquet: {missing}")
    X = df[FEATURE_COLS].copy()
    # Outlier-Clipping für numerische Features mit bekannten Datenfehler-Extremwerten
    # alter_bauwerk: negative Werte = Neubauten vor Fertigstellung; >150 = fehlerhafte baujahr-Einträge
    X["alter_bauwerk"] = X["alter_bauwerk"].clip(lower=0, upper=150)
    # freiab_monate: >24 Monate sind entweder Projektentwicklungen oder Datenfehler
    X["freiab_monate"] = X["freiab_monate"].clip(lower=0, upper=24)
    return X


def prepare_target_price(df: pd.DataFrame) -> pd.Series:
    return df[TARGET_PRICE].copy()


def prepare_target_duration(df: pd.DataFrame) -> pd.Series:
    # log_laufzeittage ist im Parquet V1.5 bereits vorberechnet → direkt verwenden
    return df[TARGET_DURATION].copy()


def stratified_sample(df: pd.DataFrame, frac: float, seed: int = 42) -> pd.DataFrame:
    parts = [grp.sample(frac=frac, random_state=seed)
             for _, grp in df.groupby("ajahr")]
    return pd.concat(parts).reset_index(drop=True)


def prepare_features_for_trees(X_train_imp: pd.DataFrame, X_test_imp: pd.DataFrame):
    """
    OrdinalEncoder für die 5 string-typisierten Kategorie-Spalten (V1.5).
    Nötig für XGBoost, LightGBM, Decision Tree (können keine str-Spalten verarbeiten).
    Fit ausschliesslich auf X_train_imp — kein Leakage.

    Returns: (X_train_tree, X_test_tree, ord_encoder)
    """
    from sklearn.preprocessing import OrdinalEncoder

    enc = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        encoded_missing_value=np.nan,
    )
    X_tr = X_train_imp.copy()
    X_te = X_test_imp.copy()
    X_tr[CAT_STRING_COLS] = enc.fit_transform(X_train_imp[CAT_STRING_COLS])
    X_te[CAT_STRING_COLS] = enc.transform(X_test_imp[CAT_STRING_COLS])
    return X_tr, X_te, enc


def prepare_features_for_linear(X_train_imp: pd.DataFrame, X_test_imp: pd.DataFrame):
    """
    OHE für nominale String-Kategorien (objektzustand, heizungsart, kategorie_Wohnung, blid).
    erg_amd wird gedroppt (141 Kategorien — zu hohe Dimensionalität für LR/IGANN).
    Fit ausschliesslich auf X_train_imp — kein Leakage.

    Returns: (X_train_lr, X_test_lr, ohe_encoder)
    """
    from sklearn.preprocessing import OneHotEncoder

    drop_cols = [c for c in LR_DROP_FEATURES if c in X_train_imp.columns]
    X_tr = X_train_imp.drop(columns=drop_cols)
    X_te = X_test_imp.drop(columns=drop_cols)

    ohe_cols = [c for c in OHE_FEATURES if c in X_tr.columns]
    other_cols = [c for c in X_tr.columns if c not in ohe_cols]

    ohe = OneHotEncoder(
        handle_unknown="ignore",
        drop="first",
        sparse_output=False,
        dtype=np.float64,
    )

    ohe_tr = ohe.fit_transform(X_tr[ohe_cols])
    ohe_te = ohe.transform(X_te[ohe_cols])
    feature_names = ohe.get_feature_names_out(ohe_cols)

    X_train_lr = pd.concat(
        [X_tr[other_cols].reset_index(drop=True), pd.DataFrame(
            ohe_tr, columns=feature_names)],
        axis=1,
    )
    X_test_lr = pd.concat(
        [X_te[other_cols].reset_index(drop=True), pd.DataFrame(
            ohe_te, columns=feature_names)],
        axis=1,
    )
    return X_train_lr, X_test_lr, ohe
