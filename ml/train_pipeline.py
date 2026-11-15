# ============================================================
#  ASTRA Cloud -- HTRU2 Training Pipeline
#  File   : ml/train_pipeline.py
#  Purpose: Train a RandomForestClassifier on HTRU2 benchmark
#           data, calculate performance metrics on a 70/30 split,
#           and serialize the model and feature names.
# ============================================================

import os
import sys
import io
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

# UTF-8 output formatting for Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ------------------------------------------------------------------
# Paths and Column Definitions
# ------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_PATH   = REPO_ROOT / "data" / "htru2" / "HTRU_2.csv"
MODELS_DIR  = REPO_ROOT / "models"
MODEL_OUT   = MODELS_DIR / "random_forest_pipeline.pkl"
FEATURES_OUT = MODELS_DIR / "htru2_features.pkl"

COLUMNS = [
    "Profile_Mean",
    "Profile_Std",
    "Profile_Skewness",
    "Profile_Kurtosis",
    "DM_Mean",
    "DM_Std",
    "DM_Skewness",
    "DM_Kurtosis",
    "Target",
]

FEATURE_COLS = COLUMNS[:-1]
TARGET_COL   = COLUMNS[-1]


def run_pipeline() -> None:
    print("=" * 60)
    print("  ASTRA Cloud -- HTRU2 Training Pipeline")
    print("=" * 60)

    # ── 1. Load Dataset ───────────────────────────────────────────
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"HTRU2 dataset not found at: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH, header=None, names=COLUMNS)

    # Print dataset shape
    print(f"\nDataset shape : {df.shape}")

    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    # ── 2. Train / Test Split ─────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.30,
        stratify=y,
        random_state=42,
    )

    # Print split sizes
    print(f"Training size : {X_train.shape[0]} samples")
    print(f"Testing size  : {X_test.shape[0]} samples")

    # ── 3. Train Classifier ───────────────────────────────────────
    print("\nTraining RandomForestClassifier (random_state=42) ...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    # ── 4. Evaluate on Test Set ───────────────────────────────────
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    accuracy  = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall    = recall_score(y_test, y_pred)
    f1        = f1_score(y_test, y_pred)
    roc_auc   = roc_auc_score(y_test, y_prob)

    print("-" * 60)
    print(f"Accuracy  : {accuracy:.4f}")
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1        : {f1:.4f}")
    print(f"ROC-AUC   : {roc_auc:.4f}")
    print("-" * 60)

    # ── 5. Save Artifacts ─────────────────────────────────────────
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    with open(MODEL_OUT, "wb") as f:
        pickle.dump(clf, f)
    print(f"\nSaved trained model to : {MODEL_OUT}")

    with open(FEATURES_OUT, "wb") as f:
        pickle.dump(FEATURE_COLS, f)
    print(f"Saved feature names to : {FEATURES_OUT}")

    print("\nPipeline execution completed successfully.\n")


if __name__ == "__main__":
    run_pipeline()
