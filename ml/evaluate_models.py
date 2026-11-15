# ml/evaluate_models.py
# ASTRA Cloud — Model Evaluation & Explainability
# Computes accuracy, precision, recall, F1-score, and ROC-AUC for each model.
# Generates SHAP explanations and saves all plots to reports/.

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    roc_curve,
    confusion_matrix,
    classification_report,
)
import shap

from preprocessing import load_htru2, validate_dataset, split_and_scale
from train_models import load_model, MODEL_REGISTRY

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
MODELS_DIR  = os.path.join(os.path.dirname(__file__), "..", "models")


# ── Metric computation ───────────────────────────────────────────────────────

def compute_metrics(clf, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    """
    Compute the five evaluation metrics for a single classifier.

    Returns a dict with keys:
        accuracy, precision, recall, f1, roc_auc
    """
    y_pred  = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]

    return {
        "accuracy":  round(accuracy_score(y_test, y_pred),          4),
        "precision": round(precision_score(y_test, y_pred),         4),
        "recall":    round(recall_score(y_test, y_pred),            4),
        "f1":        round(f1_score(y_test, y_pred),                4),
        "roc_auc":   round(roc_auc_score(y_test, y_proba),         4),
    }


# ── Plot helpers ─────────────────────────────────────────────────────────────

def plot_roc_curves(models: dict, X_test: np.ndarray, y_test: np.ndarray,
                    save_path: str | None = None) -> None:
    """Overlay ROC curves for all models on a single axes."""
    fig, ax = plt.subplots(figsize=(8, 6))
    for name, clf in models.items():
        y_proba = clf.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        auc = roc_auc_score(y_test, y_proba)
        ax.plot(fpr, tpr, label=f"{name} (AUC={auc:.4f})")

    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves — HTRU2 Test Set")
    ax.legend(loc="lower right")
    fig.tight_layout()

    if save_path is None:
        save_path = os.path.join(REPORTS_DIR, "roc_curves.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"[evaluate] ROC curves saved -> {save_path}")


def plot_confusion_matrix(clf, name: str, X_test: np.ndarray, y_test: np.ndarray,
                           save_dir: str | None = None) -> None:
    """Save a confusion-matrix heatmap for a single classifier."""
    y_pred = clf.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)

    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Non-pulsar", "Pulsar"],
                yticklabels=["Non-pulsar", "Pulsar"], ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(f"Confusion Matrix — {name}")
    fig.tight_layout()

    if save_dir is None:
        save_dir = REPORTS_DIR
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"cm_{name}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[evaluate] Confusion matrix saved -> {path}")


# ── SHAP explainability ──────────────────────────────────────────────────────

FEATURE_NAMES = [
    "mean_ip", "std_ip", "excess_kurtosis_ip", "skewness_ip",
    "mean_dmsnr", "std_dmsnr", "excess_kurtosis_dmsnr", "skewness_dmsnr",
]

def compute_shap(clf, name: str, X_train: np.ndarray,
                 X_test: np.ndarray, save_dir: str | None = None) -> None:
    """
    Compute SHAP values and save a summary bar plot.

    Uses TreeExplainer for tree-based models (RF, XGBoost) and
    KernelExplainer (with a small background sample) for SVM and MLP.
    """
    if save_dir is None:
        save_dir = REPORTS_DIR
    os.makedirs(save_dir, exist_ok=True)

    print(f"[shap] Computing SHAP values for {name} …")

    try:
        if name in ("random_forest", "xgboost"):
            explainer = shap.TreeExplainer(clf)
            shap_values = explainer.shap_values(X_test)
            # For binary classifiers, TreeExplainer may return a list
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
        else:
            # KernelExplainer is model-agnostic but slower;
            # use a small background summary to keep it feasible.
            background = shap.sample(X_train, 100, random_state=42)
            explainer = shap.KernelExplainer(clf.predict_proba, background)
            shap_values = explainer.shap_values(X_test[:200], nsamples=100)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]

        fig, ax = plt.subplots(figsize=(8, 5))
        shap.summary_plot(
            shap_values, X_test if name not in ("svm", "mlp") else X_test[:200],
            feature_names=FEATURE_NAMES,
            plot_type="bar",
            show=False,
        )
        plt.tight_layout()
        path = os.path.join(save_dir, f"shap_{name}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[shap] SHAP plot saved -> {path}")

    except Exception as exc:
        print(f"[shap] WARNING: SHAP computation failed for {name}: {exc}")


# ── Main evaluation pipeline ─────────────────────────────────────────────────

def evaluate_all(data_filepath: str | None = None,
                 models_dir: str | None = None,
                 reports_dir: str | None = None) -> dict:
    """
    Load all trained models and evaluate against the held-out test set.

    Steps:
        1. Reconstruct the identical train/test split (same random_state).
        2. Compute the 5-metric table for every model.
        3. Save metrics to reports/metrics.json.
        4. Generate ROC, confusion matrices, and SHAP plots.

    Returns
    -------
    dict : { model_name: { metric: value, ... }, ... }
    """
    if models_dir  is None: models_dir  = MODELS_DIR
    if reports_dir is None: reports_dir = REPORTS_DIR
    os.makedirs(reports_dir, exist_ok=True)

    # Reconstruct split with the SAME seed used during training
    df = load_htru2(data_filepath)
    validate_dataset(df)
    X_train, X_test, y_train, y_test, _ = split_and_scale(
        df, save_scaler=False  # scaler already saved during training
    )

    all_metrics = {}
    loaded_models = {}

    for name in MODEL_REGISTRY:
        try:
            clf = load_model(name, models_dir)
            loaded_models[name] = clf
        except FileNotFoundError as e:
            print(f"[evaluate] SKIP {name}: {e}")
            continue

        metrics = compute_metrics(clf, X_test, y_test)
        all_metrics[name] = metrics
        print(f"\n[evaluate] {name}:")
        for k, v in metrics.items():
            print(f"    {k:12s}: {v}")
        print(classification_report(y_test, clf.predict(X_test),
                                    target_names=["Non-pulsar", "Pulsar"]))
        plot_confusion_matrix(clf, name, X_test, y_test, save_dir=reports_dir)

    # ROC overlay
    if loaded_models:
        plot_roc_curves(loaded_models, X_test, y_test,
                        save_path=os.path.join(reports_dir, "roc_curves.png"))

    # SHAP
    for name, clf in loaded_models.items():
        compute_shap(clf, name, X_train, X_test, save_dir=reports_dir)

    # Save metrics JSON
    metrics_path = os.path.join(reports_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\n[evaluate] Metrics saved -> {metrics_path}")

    return all_metrics


if __name__ == "__main__":
    evaluate_all()
