# ml/train_models.py
# ASTRA Cloud — Model Training Orchestration
# Trains Random Forest, XGBoost, SVM, and MLP on the HTRU2 dataset.
# All trained models are serialized to the models/ directory.

import os
import time
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier

from preprocessing import load_htru2, validate_dataset, split_and_scale

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

# ── Model registry ───────────────────────────────────────────────────────────
# Add or modify classifiers here; the training loop handles the rest.
MODEL_REGISTRY: dict = {
    "random_forest": RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
    ),
    "xgboost": XGBClassifier(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=6,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    ),
    "svm": CalibratedClassifierCV(
        __import__("sklearn.svm", fromlist=["SVC"]).SVC(
            kernel="rbf",
            C=1.0,
            gamma="scale",
            random_state=42,
        ),
        ensemble=False,
    ),
    "mlp": MLPClassifier(
        hidden_layer_sizes=(128, 64),
        activation="relu",
        max_iter=300,
        early_stopping=True,
        random_state=42,
    ),
}


def train_all(
    data_filepath: str | None = None,
    models_dir: str | None = None,
) -> dict:
    """
    Full training pipeline:
      1. Load and validate HTRU2 dataset.
      2. Apply 70/30 stratified split and StandardScaler.
      3. Train each classifier in MODEL_REGISTRY.
      4. Save each trained model as <name>.joblib in models/.

    Parameters
    ----------
    data_filepath : Path to HTRU_2.csv. Defaults to data/htru2/HTRU_2.csv.
    models_dir    : Directory to save trained models. Defaults to models/.

    Returns
    -------
    dict : Mapping of model name → trained estimator.
    """
    if models_dir is None:
        models_dir = MODELS_DIR
    os.makedirs(models_dir, exist_ok=True)

    # Step 1 — Load data
    df = load_htru2(data_filepath)
    validate_dataset(df)

    # Step 2 — Preprocess
    X_train, X_test, y_train, y_test, _ = split_and_scale(df, save_scaler=True)

    trained_models = {}

    # Step 3 — Train loop
    for name, clf in MODEL_REGISTRY.items():
        print(f"\n[train] Training {name} …")
        t0 = time.time()
        clf.fit(X_train, y_train)
        elapsed = time.time() - t0
        print(f"[train] {name} trained in {elapsed:.2f}s")

        # Step 4 — Save model
        model_path = os.path.join(models_dir, f"{name}.joblib")
        joblib.dump(clf, model_path)
        print(f"[train] Model saved -> {model_path}")

        trained_models[name] = clf

    print("\n[train] All models trained and saved successfully.")
    return trained_models


def load_model(name: str, models_dir: str | None = None):
    """
    Load a trained model from disk by name.

    Parameters
    ----------
    name       : One of 'random_forest', 'xgboost', 'svm', 'mlp'.
    models_dir : Directory containing saved .joblib files.

    Returns
    -------
    Trained scikit-learn compatible estimator.
    """
    if models_dir is None:
        models_dir = MODELS_DIR
    model_path = os.path.join(models_dir, f"{name}.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model '{name}' not found at {model_path}. Run train_all() first."
        )
    return joblib.load(model_path)


if __name__ == "__main__":
    train_all()
