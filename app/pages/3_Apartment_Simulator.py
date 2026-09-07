import streamlit as st
import numpy as np
import pandas as pd
import shap
import plotly.graph_objects as go
import joblib
import importlib
import sys
import os
from pathlib import Path

# app/pages/ → app/ → project root
_APP_DIR = os.path.join(os.path.dirname(__file__), "..")
_ROOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.abspath(_APP_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))
sys.path.append(str(Path(__file__).parent.parent.parent / "immo-scraper"))

from utils import load_model, MODEL_REGISTRY, is_model_available
from src.data.preprocessing import FEATURE_COLS, NUMERICAL_FEATURES, CATEGORICAL_FEATURES, LR_DROP_FEATURES

SIMULATOR_MODELS = [
    "Linear Regression",
    "XGBoost",
    "LightGBM",
    "EBM",
]

LEGACY_EXTRA_FEATURES = [
    "dist_park",
    "dens_park",
    "ausstattung",
    "energieeffizienzklasse",
    "parkplatz",
    "rollstuhlgerecht",
    "denkmalobjekt",
]

# ── Scraper-Integration ──────────────────────────────────────────────────────
try:
    _scraper_mod = importlib.import_module("scraper")
    SCRAPER_AVAILABLE = True
except (ModuleNotFoundError, ImportError):
    _scraper_mod = None
    SCRAPER_AVAILABLE = False


def scrape_listing(url: str) -> dict | None:
    if not SCRAPER_AVAILABLE:
        return None
    return _scraper_mod.scrape_listing(url)


def plz_to_bundesland(plz: str) -> str | None:
    if not plz or len(plz) < 2:
        return None
    prefix = int(plz[:2])
    mapping = {
        range(1, 7):    "Sachsen",
        range(7, 10):   "Thüringen",
        range(10, 15):  "Berlin",
        range(15, 20):  "Brandenburg",
        range(20, 23):  "Hamburg",
        range(23, 28):  "Schleswig-Holstein",
        range(28, 30):  "Bremen",
        range(30, 32):  "Niedersachsen",
        range(32, 34):  "Nordrhein-Westfalen",
        range(34, 37):  "Hessen",
        range(37, 39):  "Niedersachsen",
        range(39, 40):  "Sachsen-Anhalt",
        range(40, 53):  "Nordrhein-Westfalen",
        range(53, 57):  "Rheinland-Pfalz",
        range(57, 60):  "Nordrhein-Westfalen",
        range(60, 66):  "Hessen",
        range(66, 67):  "Saarland",
        range(67, 68):  "Rheinland-Pfalz",
        range(68, 80):  "Baden-Württemberg",
        range(80, 88):  "Bayern",
        range(88, 90):  "Baden-Württemberg",
        range(90, 98):  "Bayern",
        range(98, 100): "Thüringen",
    }
    for rng, land in mapping.items():
        if prefix in rng:
            return land
    return None


def map_scraped_to_features(data: dict) -> dict:
    attr = data.get("attributes", {})
    plz = str(attr.get("plz", "")).strip()
    # M1-Fix: JSON-LD-Pfad schreibt 'wohnflaeche'/'baujahr'/'anzahl_zimmer',
    # HTML-Pfad schreibt 'floor_size_m2'/'year_built'/'num_rooms' → Fallback auf beide
    wohnflaeche = attr.get("floor_size_m2") or attr.get("wohnflaeche")
    zimmeranzahl = attr.get("num_rooms") or attr.get("anzahl_zimmer")
    baujahr = attr.get("year_built") or attr.get("baujahr")
    return {
        "wohnflaeche":  wohnflaeche,
        "zimmeranzahl": zimmeranzahl,
        "baujahr":      baujahr,
        "etage":        None,
        "bundesland":   plz_to_bundesland(plz),
        "balkon":       bool(attr.get("balkon", 0)),
        "keller":       bool(attr.get("keller", 0)),
        "aufzug":       None,
        "einbaukueche": bool(attr.get("einbaukueche", 0)),
        "name":         attr.get("name", ""),
        "kaltmiete":    attr.get("kaltmiete", ""),
        "city":         attr.get("city", ""),
        "strasse":      attr.get("strasse", ""),
        "url":          data.get("url", ""),
    }

ROOMS_OPTIONS = [1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6]

# ── Session-State ────────────────────────────────────────────────────────────
if "scraped" not in st.session_state:
    st.session_state.scraped = None

# ── Seite ────────────────────────────────────────────────────────────────────
st.title("🏠 Apartment Simulator")
st.markdown("Configure an apartment and get price & time-to-let predictions with explanations.")

# ── Eingabe-Modus ─────────────────────────────────────────────────────────────
modus = st.radio(
    "Data input mode",
    ["✏️ Enter manually", "🔗 Load from ImmoScout24"],
    horizontal=True,
)

# M3-Fix: Gescrapte Daten zurücksetzen wenn User in manuellen Modus wechselt
if modus == "✏️ Enter manually" and st.session_state.scraped is not None:
    if st.button("❌ Clear pre-filled listing data", type="secondary"):
        st.session_state.scraped = None
        st.rerun()

if modus == "🔗 Load from ImmoScout24":
    if not SCRAPER_AVAILABLE:
        st.warning("Scraper module not found (`immo-scraper/scraper.py`). Please enter values manually.")
    else:
        url_col, btn_col = st.columns([4, 1])
        with url_col:
            url_input = st.text_input(
                "ImmoScout24 URL",
                placeholder="https://www.immobilienscout24.de/expose/123456789",
                label_visibility="collapsed",
            )
        with btn_col:
            laden = st.button("Load listing", use_container_width=True)

        if laden and url_input:
            with st.spinner("Loading listing..."):
                raw = scrape_listing(url_input)
            if raw:
                st.session_state.scraped = map_scraped_to_features(raw)
                st.success("Listing loaded! Check the values in the sidebar.")
            else:
                st.error("Scraping failed — please enter values manually.")

        if st.session_state.scraped and st.session_state.scraped.get("url"):
            with st.expander("📄 Listing Preview", expanded=False):
                s_prev = st.session_state.scraped
                st.markdown(
                    f"**{s_prev.get('name', '')}**  \n"
                    f"{s_prev.get('strasse', '')}, {s_prev.get('city', '')}  \n"
                    f"Cold rent per listing: **{s_prev.get('kaltmiete', '?')} €**"
                )
                st.markdown(f"[Open on ImmoScout24 ↗]({s_prev['url']})")

# ── Default-Helpers (Scraper → Sidebar pre-fill) ──────────────────────────────
s = st.session_state.scraped or {}


def _dv(key, fallback):
    val = s.get(key)
    return val if val is not None else fallback


def _default_federal_state_index():
    bl = s.get("bundesland")
    keys = list(BUNDESLAND_BLID.keys())
    if bl and bl in keys:
        return keys.index(bl)
    return 8  # Bayern default


def _default_rooms_index():
    raw = s.get("zimmeranzahl")
    if raw is not None:
        try:
            return ROOMS_OPTIONS.index(float(raw))
        except ValueError:
            pass
    return 4  # 3 Zimmer default


# Bundesland → blid Mapping (RWI-GEO-RED Kodierung)
BUNDESLAND_BLID = {
    "Schleswig-Holstein": 1, "Hamburg": 2, "Niedersachsen": 3,
    "Bremen": 4, "Nordrhein-Westfalen": 5, "Hessen": 6,
    "Rheinland-Pfalz": 7, "Baden-Württemberg": 8, "Bayern": 9,
    "Saarland": 10, "Berlin": 11, "Brandenburg": 12,
    "Mecklenburg-Vorpommern": 13, "Sachsen": 14, "Sachsen-Anhalt": 15,
    "Thüringen": 16,
}

HEIZUNGSART_LABELS = {
    -1: "Unknown", 1: "CHP Plant", 2: "Electric", 3: "Floor Heating System",
    4: "District Heating", 5: "Underfloor Heating", 6: "Gas", 7: "Wood Pellets",
    8: "Night Storage", 9: "Stove", 10: "Oil", 11: "Solar",
    12: "Heat Pump", 13: "Central Heating",
}

OBJEKTZUSTAND_LABELS = {
    -1: "Unknown", 1: "First Occupancy", 2: "First Occupancy after Renovation",
    3: "As New", 4: "Renovated", 5: "Modernised",
    6: "Fully Refurbished", 7: "Well Maintained",
    8: "Needs Renovation", 9: "By Arrangement", 10: "Dilapidated",
}

# ── Sidebar Inputs ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Apartment Configuration")

    if st.session_state.scraped:
        st.info("⚡ Fields pre-filled from listing. Complete missing values (⚠️) manually.")

    living_area    = st.slider("Living Area (m²)", 20, 200, int(_dv("wohnflaeche", 70)))
    rooms          = st.selectbox("Number of Rooms", ROOMS_OPTIONS, index=_default_rooms_index())
    year_built     = st.slider("Year Built", 1900, 2024, int(_dv("baujahr", 1990)))
    floor          = st.selectbox("Floor" + (" ⚠️" if s and s.get("etage") is None else ""), list(range(0, 15)), index=int(_dv("etage", 2)))
    num_floors     = st.selectbox("Floors in Building", list(range(1, 20)), index=4)
    bedrooms       = st.selectbox("Bedrooms", [0, 1, 2, 3, 4, 5], index=1)
    bathrooms      = st.selectbox("Bathrooms", [1, 2, 3], index=0)
    federal_state  = st.selectbox("Federal State", list(BUNDESLAND_BLID.keys()), index=_default_federal_state_index())
    listing_year   = st.slider("Listing Year", 2007, 2026, 2024)
    listing_month  = st.selectbox("Listing Month", list(range(1, 13)), index=0)

    st.subheader("Amenities")
    has_balcony    = st.checkbox("Balcony",          value=bool(_dv("balkon", False)))
    has_basement   = st.checkbox("Basement",         value=bool(_dv("keller", False)))
    has_elevator   = st.checkbox("Elevator" + (" ⚠️" if s and s.get("aufzug") is None else ""), value=bool(_dv("aufzug", False)))
    has_kitchen    = st.checkbox("Built-in Kitchen", value=bool(_dv("einbaukueche", False)))
    has_garden     = st.checkbox("Garden")
    has_guest_wc   = st.checkbox("Guest WC")
    has_parking    = st.checkbox("Parking Space")

    st.subheader("Property Details")
    heating_key    = st.selectbox("Heating Type", list(HEIZUNGSART_LABELS.keys()),
                                  format_func=lambda k: HEIZUNGSART_LABELS[k], index=0)
    condition_key  = st.selectbox("Condition", list(OBJEKTZUSTAND_LABELS.keys()),
                                  format_func=lambda k: OBJEKTZUSTAND_LABELS[k], index=0)

    st.subheader("Additional Features")
    subsidized             = st.checkbox("Social Housing (Förderung)")
    pets_allowed           = st.checkbox("Pets Allowed")
    was_renovated          = st.checkbox("Recently Modernised")
    has_energy_certificate = st.checkbox("Energy Certificate Available")

    available_simulator_models = [m for m in SIMULATOR_MODELS if m in MODEL_REGISTRY]
    selected_model = st.selectbox("Model", available_simulator_models)

# ── Verfügbarkeits-Check ────────────────────────────────────────────────────
price_available    = is_model_available(selected_model, "price")
duration_available = is_model_available(selected_model, "duration")

if not price_available and not duration_available:
    st.warning(f"⏳ Coming Soon — {selected_model} models not yet trained.")
    st.stop()

# ── Feature-Vektor bauen — vollständig gemäß FEATURE_COLS (V1.5) ─────────────
# Räumliche Features (dist_*/dens_*) sind ohne Geocoding nicht konfigurierbar.
# Baummodelle (XGBoost, LightGBM) tolerieren NaN nativ.
# Für Gruppe-2-Modelle (EBM, IGANN, LinReg) ist Imputer-Integration geplant.
NaN = float("nan")
input_dict = {
    # Numerisch — vom Nutzer konfiguriert
    "wohnflaeche":         living_area,
    "zimmeranzahl":        rooms,
    "alter_bauwerk":       listing_year - year_built,   # FIX: engineered aus ajahr - baujahr
    "completeness_score":  0.8,                          # Standardwert (Listing vollständig ausgefüllt)
    "etage":               floor,
    "anzahletagen":        num_floors,
    "schlafzimmer":        bedrooms,
    "badezimmer":          bathrooms,
    "freiab_monate":       NaN,                          # nicht konfigurierbar → NaN
    # Räumlich — nicht ohne Geocoding bestimmbar → NaN
    "dist_transit":        NaN,
    "dens_transit":        NaN,
    "dist_supermarket":    NaN,
    "dens_supermarket":    NaN,
    "dist_park":           NaN,
    "dens_park":           NaN,
    "dist_to_center":      NaN,
    # Kategorial
    "objektzustand":       condition_key,
    "heizungsart":         heating_key,
    "kategorie_Wohnung":   NaN,                          # 27.6% NaN im Datensatz
    "blid":                BUNDESLAND_BLID[federal_state],
    "erg_amd":             NaN,                          # Arbeitsmarktregion → NaN
    "ausstattung":         NaN,
    "energieeffizienzklasse": NaN,
    "ajahr":               listing_year,
    "amonat":              listing_month,
    # Binär
    "balkon":              int(has_balcony),
    "einbaukueche":        int(has_kitchen),
    "keller":              int(has_basement),
    "aufzug":              int(has_elevator),
    "garten":              int(has_garden),
    "gaestewc":            int(has_guest_wc),
    "hat_parkplatz":       int(has_parking),
    "parkplatz":           int(has_parking),
    "foerderung":          int(subsidized),
    "rollstuhlgerecht":    0,
    "denkmalobjekt":       0,
    "haustier_erlaubt":    int(pets_allowed),
    "wurde_modernisiert":  int(was_renovated),
    "hat_energieausweis":  int(has_energy_certificate),
}
# Volle Feature-Tabelle (neu + legacy), spätere Ausrichtung je Modell
X_input = pd.DataFrame([input_dict])

# ── Imputer laden und NaN-Werte auffüllen ────────────────────────────────────
@st.cache_resource
def load_imputers(target):
    _models_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
    num_path = os.path.join(_models_dir, f"num_imputer_{target}.joblib")
    cat_path = os.path.join(_models_dir, f"cat_imputer_{target}.joblib")
    num_imp = joblib.load(num_path) if os.path.exists(num_path) else None
    cat_imp = joblib.load(cat_path) if os.path.exists(cat_path) else None
    return num_imp, cat_imp


@st.cache_resource
def load_transformers(target):
    _models_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
    ord_path = os.path.join(_models_dir, f"ord_encoder_{target}.joblib")
    ohe_path = os.path.join(_models_dir, f"ohe_encoder_{target}.joblib")
    scaler_path = os.path.join(_models_dir, f"igann_scaler_{target}.joblib")
    ord_enc = joblib.load(ord_path) if os.path.exists(ord_path) else None
    ohe_enc = joblib.load(ohe_path) if os.path.exists(ohe_path) else None
    scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None
    return ord_enc, ohe_enc, scaler

def apply_imputers(X, target):
    """Wendet num/cat Imputer auf den Feature-Vektor an und erhält stabile Datentypen."""
    X = X.copy()
    num_imp, cat_imp = load_imputers(target)
    # Nur die Spalten imputen, auf denen der Imputer trainiert wurde
    if num_imp is not None and hasattr(num_imp, 'feature_names_in_'):
        num_cols = [c for c in num_imp.feature_names_in_ if c in X.columns]
        if num_cols:
            X[num_cols] = num_imp.transform(X[num_cols])
    if cat_imp is not None and hasattr(cat_imp, 'feature_names_in_'):
        cat_cols = [c for c in cat_imp.feature_names_in_ if c in X.columns]
        if cat_cols:
            X[cat_cols] = cat_imp.transform(X[cat_cols])

    # Numerische NaN auf 0; kategoriale NaN auf Marker (kein int/str-Mix)
    numeric_cols = X.select_dtypes(include=[np.number, "bool"]).columns
    if len(numeric_cols) > 0:
        X[numeric_cols] = X[numeric_cols].fillna(0)

    cat_cols = [c for c in X.columns if c not in numeric_cols]
    if cat_cols:
        X[cat_cols] = X[cat_cols].where(~X[cat_cols].isna(), "__missing__")

    return X


def prepare_categorical_columns(X: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Kategoriale Spalten robust auf string normalisieren (Encoder-stabil)."""
    Xp = X.copy()
    for c in cols:
        if c in Xp.columns:
            Xp[c] = Xp[c].astype("string").fillna("__missing__").astype(str)
    return Xp


def align_to_expected_features(X: pd.DataFrame, model) -> pd.DataFrame:
    """Richtet Feature-Matrix auf exakt die beim Fit erwarteten Spalten aus."""
    if not hasattr(model, "feature_names_in_"):
        return X
    expected = list(model.feature_names_in_)
    X_aligned = X.copy()
    for col in expected:
        if col not in X_aligned.columns:
            X_aligned[col] = 0
    return X_aligned[expected]


def apply_model_specific_pipeline(X: pd.DataFrame, target: str, model_name: str, model):
    """Modellspezifische Inferenz-Pipeline analog zum Training."""
    X_ready = apply_imputers(X, target)
    ord_enc, ohe_enc, igann_scaler = load_transformers(target)

    if model_name in ["XGBoost", "LightGBM"]:
        if ord_enc is not None and hasattr(ord_enc, "feature_names_in_"):
            ord_cols = [c for c in ord_enc.feature_names_in_ if c in X_ready.columns]
            if ord_cols:
                X_ready = prepare_categorical_columns(X_ready, ord_cols)
                X_ready[ord_cols] = ord_enc.transform(X_ready[ord_cols])
        X_ready = align_to_expected_features(X_ready, model)
        return X_ready

    if model_name in ["IGANN", "Linear Regression"]:
        X_lr = X_ready.copy()
        drop_cols = [c for c in LR_DROP_FEATURES if c in X_lr.columns]
        if drop_cols:
            X_lr = X_lr.drop(columns=drop_cols)

        if ohe_enc is not None and hasattr(ohe_enc, "feature_names_in_"):
            ohe_cols = [c for c in ohe_enc.feature_names_in_ if c in X_lr.columns]
            other_cols = [c for c in X_lr.columns if c not in ohe_cols]
            if ohe_cols:
                X_lr = prepare_categorical_columns(X_lr, ohe_cols)
                ohe_arr = ohe_enc.transform(X_lr[ohe_cols])
                ohe_df = pd.DataFrame(
                    ohe_arr,
                    columns=ohe_enc.get_feature_names_out(ohe_cols),
                    index=X_lr.index,
                )
                X_lr = pd.concat([X_lr[other_cols], ohe_df], axis=1)

        # Restliche numerische NaN nach OHE schließen
        X_lr = X_lr.replace([np.inf, -np.inf], np.nan)
        numeric_cols = X_lr.select_dtypes(include=[np.number, "bool"]).columns
        if len(numeric_cols) > 0:
            X_lr[numeric_cols] = X_lr[numeric_cols].fillna(0)

        if model_name == "IGANN" and igann_scaler is not None and hasattr(igann_scaler, "feature_names_in_"):
            sc_cols = list(igann_scaler.feature_names_in_)
            for c in sc_cols:
                if c not in X_lr.columns:
                    X_lr[c] = 0
            X_lr = X_lr[sc_cols]
            X_lr = pd.DataFrame(
                igann_scaler.transform(X_lr),
                columns=sc_cols,
                index=X_lr.index,
            )
        X_lr = align_to_expected_features(X_lr, model)
        return X_lr

    if model_name == "EBM":
        X_ebm = align_to_expected_features(X_ready, model)
        # interpret/EBM akzeptiert StringDtype nicht, nur object
        str_cols = X_ebm.select_dtypes(include="string").columns.tolist()
        if str_cols:
            X_ebm[str_cols] = X_ebm[str_cols].astype(object)
        return X_ebm

    # Linear Regression / EBM / andere: nur auf erwartete Features ausrichten
    X_ready = align_to_expected_features(X_ready, model)
    return X_ready

# ── Predictions & Output ─────────────────────────────────────────────────────
col_price, col_duration = st.columns(2)

for col, target, label, unit, transform in [
    (col_price,    "price",    "Rental Price",   "€/m²", lambda x: x),
    (col_duration, "duration", "Time-to-Let",    "days", np.expm1),
]:
    with col:
        st.subheader(f"Model A — {label}" if target == "price" else f"Model B — {label}")
        try:
            model = load_model(selected_model, target)
        except ModuleNotFoundError as e:
            st.error(
                f"Model dependency missing for {selected_model}: {e}. "
                "Install package in environment, then restart app."
            )
            continue
        except Exception as e:
            st.error(f"Model loading failed: {e}")
            continue

        if model is None:
            st.info(f"⏳ Coming Soon — {selected_model} ({target}) not yet trained.")
            continue

        try:
            X_ready = apply_model_specific_pipeline(X_input, target, selected_model, model)
            pred_raw = model.predict(X_ready)[0]
        except Exception as e:
            st.error(f"Prediction failed: {e}")
            continue

        pred = transform(pred_raw)

        if target == "price":
            monthly = pred * living_area
            st.metric("Expected Rent", f"{pred:.2f} {unit}", f"≈ €{monthly:.0f}/month")
        else:
            st.metric("Expected Time-to-Let", f"{pred:.0f} {unit}")

        # SHAP Waterfall (nur für SHAP-kompatible Modelle — XGBoost, LightGBM)
        if selected_model in ["XGBoost", "LightGBM"]:
            try:
                explainer   = shap.TreeExplainer(model)
                shap_values = explainer(X_ready)
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
            st.caption(
                f"Feature contributions are embedded in the {selected_model} shape functions "
                "(see Shape Explorer)."
            )
