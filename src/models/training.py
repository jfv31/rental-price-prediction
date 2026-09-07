import joblib
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
import xgboost as xgb
import lightgbm as lgb

MODELS_DIR = Path(__file__).parent.parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

TEMPORAL_CUTOFF = 2021  # Train: ajahr <= 2021, Test: ajahr >= 2022


def temporal_split(df: pd.DataFrame, target: str, year_col: str = "ajahr"):
    """Echter temporaler Split: Train 2016–2021, Test 2022–2023.
    Kein Data Leakage durch zufällige Mischung von Zeitperioden.
    """
    mask_train = df[year_col] <= TEMPORAL_CUTOFF
    mask_test  = df[year_col] >  TEMPORAL_CUTOFF
    X = df.drop(columns=[target])
    y = df[target]
    return X[mask_train], X[mask_test], y[mask_train], y[mask_test]


def train_linear(X_train, y_train):
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model


def train_decision_tree(X_train, y_train, **kwargs):
    model = DecisionTreeRegressor(random_state=42, **kwargs)
    model.fit(X_train, y_train)
    return model


def train_xgboost(X_train, y_train, **kwargs):
    model = xgb.XGBRegressor(random_state=42, n_jobs=-1, **kwargs)
    model.fit(X_train, y_train)
    return model


def train_lightgbm(X_train, y_train, **kwargs):
    model = lgb.LGBMRegressor(random_state=42, n_jobs=-1, **kwargs)
    model.fit(X_train, y_train)
    return model


def save_model(model, name: str):
    path = MODELS_DIR / f"{name}.joblib"
    joblib.dump(model, path)
    return path
