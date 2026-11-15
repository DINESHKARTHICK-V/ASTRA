# ml/preprocessing.py
# ASTRA Cloud — HTRU2 Data Preprocessing
# Handles loading, validation, feature scaling, and train/test splitting.
# Scientific logic is intentionally isolated from backend/frontend code.

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

# ── Column definitions ──────────────────────────────────────────────────────
HTRU2_COLUMNS = [
    "mean_ip",        # Mean of the integrated profile
    "std_ip",         # Standard deviation of the integrated profile
    "excess_kurtosis_ip",  # Excess kurtosis of the integrated profile
    "skewness_ip",    # Skewness of the integrated profile
    "mean_dmsnr",     # Mean of the DM-SNR curve
    "std_dmsnr",      # Standard deviation of the DM-SNR curve
    "excess_kurtosis_dmsnr",  # Excess kurtosis of the DM-SNR curve
    "skewness_dmsnr", # Skewness of the DM-SNR curve
    "label",          # Class label: 1 = pulsar, 0 = non-pulsar
]

FEATURE_COLS = HTRU2_COLUMNS[:-1]
LABEL_COL = "label"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "htru2")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def load_htru2(filepath: str | None = None) -> pd.DataFrame:
    """
    Load the HTRU2 dataset from a CSV file.

    The dataset is available at:
    https://archive.ics.uci.edu/ml/datasets/HTRU2

    Parameters
    ----------
    filepath : str, optional
        Absolute or relative path to HTRU_2.csv.
        Defaults to data/htru2/HTRU_2.csv relative to project root.

    Returns
    -------
    pd.DataFrame
        DataFrame with named columns.
    """
    if filepath is None:
        filepath = os.path.join(DATA_DIR, "HTRU_2.csv")

    filepath = os.path.abspath(filepath)
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"HTRU2 dataset not found at: {filepath}\n"
            "Download it from https://archive.ics.uci.edu/ml/datasets/HTRU2 "
            "and place HTRU_2.csv in data/htru2/"
        )

    df = pd.read_csv(filepath, header=None, names=HTRU2_COLUMNS)
    print(f"[preprocessing] Loaded HTRU2: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


def validate_dataset(df: pd.DataFrame) -> None:
    """
    Basic sanity checks on the loaded dataset.
    Raises ValueError on unexpected structure or missing values.
    """
    assert list(df.columns) == HTRU2_COLUMNS, "Unexpected column names."
    if df.isnull().values.any():
        raise ValueError("Dataset contains missing values — check the source file.")
    class_counts = df[LABEL_COL].value_counts()
    print(f"[preprocessing] Class distribution:\n{class_counts.to_string()}")


def split_and_scale(
    df: pd.DataFrame,
    test_size: float = 0.30,
    random_state: int = 42,
    save_scaler: bool = True,
    scaler_path: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
    """
    Apply a 70/30 stratified train/test split and StandardScaler.

    The scaler is fitted ONLY on training data to prevent data leakage.

    Parameters
    ----------
    df          : Loaded HTRU2 DataFrame.
    test_size   : Fraction of data for the test set (default 0.30).
    random_state: Seed for reproducibility.
    save_scaler : If True, persist the fitted scaler to disk.
    scaler_path : Where to save the scaler (.joblib). Defaults to models/.

    Returns
    -------
    X_train, X_test, y_train, y_test, scaler
    """
    X = df[FEATURE_COLS].values
    y = df[LABEL_COL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,  # preserve class ratio
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)           # transform only, never fit

    print(f"[preprocessing] Train set: {X_train.shape}, Test set: {X_test.shape}")

    if save_scaler:
        if scaler_path is None:
            scaler_path = os.path.join(MODELS_DIR, "scaler.joblib")
        os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
        joblib.dump(scaler, scaler_path)
        print(f"[preprocessing] Scaler saved to {scaler_path}")

    return X_train, X_test, y_train, y_test, scaler


def load_scaler(scaler_path: str | None = None) -> StandardScaler:
    """Load a previously saved StandardScaler from disk."""
    if scaler_path is None:
        scaler_path = os.path.join(MODELS_DIR, "scaler.joblib")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler not found at {scaler_path}. Run preprocessing first.")
    return joblib.load(scaler_path)
