# ============================================================
#  ASTRA Cloud -- Step 24: Radio SHAP Explanation
#  File   : ml/radio_shap_explanation.py
#  Purpose: Calculates SHAP (SHapley Additive exPlanations)
#           feature attributions for usable radio observations
#           that completed model inference. If inference was halted
#           due to missing features, this step documents the
#           bypassed status scientifically.
#  Inputs : models/random_forest_htru2.pkl
#           models/htru2_features.pkl
#           reports/radio_predictions.csv
#           reports/radio_htru2_compatible.csv
#  Outputs: reports/radio_shap/
#           reports/radio_shap_summary.csv
# ============================================================

import sys
import io
import csv
from pathlib import Path

import joblib
import pandas as pd
import numpy as np

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT          = Path(__file__).resolve().parent.parent
MODELS_DIR         = REPO_ROOT / "models"
REPORTS_DIR        = REPO_ROOT / "reports"
SHAP_DIR           = REPORTS_DIR / "radio_shap"

MODEL_FILE         = MODELS_DIR / "random_forest_htru2.pkl"
FEATURES_FILE      = MODELS_DIR / "htru2_features.pkl"
PREDICTIONS_CSV    = REPORTS_DIR / "radio_predictions.csv"
COMPAT_CSV         = REPORTS_DIR / "radio_htru2_compatible.csv"
MASTER_CSV         = REPORTS_DIR / "radio_master_features.csv"
SHAP_SUMMARY_CSV   = REPORTS_DIR / "radio_shap_summary.csv"

CSV_FIELDS = [
    "file_name",
    "feature_name",
    "shap_value",
    "feature_value",
]


def run_radio_shap() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 24: Radio SHAP Explanation")
    print("=" * 68)

    SHAP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load predictions to check which observations received valid predictions
    if not PREDICTIONS_CSV.exists():
        raise FileNotFoundError(f"Predictions file not found: {PREDICTIONS_CSV}")

    pred_df = pd.read_csv(PREDICTIONS_CSV)
    usable_preds = pred_df[pred_df["prediction"] != "INFERENCE_HALTED"]
    num_usable = len(usable_preds)

    print(f"Total observations in prediction table: {len(pred_df)}")
    print(f"Observations with active model predictions: {num_usable}")

    rows = []

    if num_usable > 0:
        import shap
        print("Loading model and features for SHAP TreeExplainer...")
        model = joblib.load(MODEL_FILE)
        features = joblib.load(FEATURES_FILE)

        compat_df = pd.read_csv(COMPAT_CSV)
        explainer = shap.TreeExplainer(model)

        for _, pred_row in usable_preds.iterrows():
            fn = pred_row["file_name"]
            obs_match = compat_df[compat_df["file_name"] == fn]
            if obs_match.empty:
                continue

            x_vec = obs_match[features].values.astype(float)
            shap_values = explainer.shap_values(x_vec)

            # In binary classification, class 1 (pulsar) SHAP values
            if isinstance(shap_values, list) and len(shap_values) == 2:
                s_vals = shap_values[1][0]
            elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
                s_vals = shap_values[0, :, 1]
            else:
                s_vals = shap_values[0]

            for feat_name, s_val, f_val in zip(features, s_vals, x_vec[0]):
                rows.append({
                    "file_name": fn,
                    "feature_name": feat_name,
                    "shap_value": f"{s_val:.6f}",
                    "feature_value": f"{f_val:.4f}",
                })

        print(f"[OK] Computed SHAP feature contributions for {num_usable} observation(s).")
    else:
        print("[SCIENTIFIC INTEGRITY NOTICE]")
        print("  SHAP computes feature attributions for model predictions on input feature vectors.")
        print("  Because zero (0) real radio observations possessed complete HTRU2 search-mode DM features,")
        print("  model inference was safely halted in Step 23.")
        print("  Consequently, SHAP feature attribution cannot be computed on non-existent predictions.")
        print("  Documenting halted status transparently across all observations.")

        # Create documentation log
        status_txt_file = SHAP_DIR / "radio_shap_status.txt"
        with open(status_txt_file, "w", encoding="utf-8") as f:
            f.write("ASTRA Cloud -- Radio SHAP Explanation Status\n")
            f.write("=" * 60 + "\n")
            f.write("Status: SHAP_EXPLANATION_HALTED\n")
            f.write("Reason: Zero real radio observations qualified for Random Forest inference.\n")
            f.write("Observations lacked DM-SNR curve statistical moments (DM_Mean, DM_Std, DM_Skewness, DM_Kurtosis).\n")
            f.write("In accordance with scientific integrity guidelines, no synthetic feature vectors were imputed,\n")
            f.write("and no invalid model predictions were generated. Therefore, SHAP explanations are uncomputed.\n")
            f.write("\nMethodology Note:\n")
            f.write("SHAP explains the model's prediction mechanism; it does NOT constitute physical proof of a pulsar.\n")

        print(f"[OK] Status report written to {status_txt_file}")

        # Populate summary rows for all files
        for _, pred_row in pred_df.iterrows():
            fn = pred_row["file_name"]
            rows.append({
                "file_name": fn,
                "feature_name": "ALL_FEATURES",
                "shap_value": "NOT_AVAILABLE",
                "feature_value": "INCOMPATIBLE_DATA (Inference Halted)",
            })

    # Save summary table
    with open(SHAP_SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] SHAP summary report saved → {SHAP_SUMMARY_CSV}")
    print("=" * 68)


if __name__ == "__main__":
    run_radio_shap()
