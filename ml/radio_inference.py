# ============================================================
#  ASTRA Cloud -- Step 23: Safe Radio Inference Pipeline
#  File   : ml/radio_inference.py
#  Purpose: Executes Random Forest inference ONLY on feature-
#           compatible radio observations. If observations lack
#           required features (e.g. search-mode DM curves),
#           inference is safely halted to prevent unscientific
#           extrapolation or forced dummy imputation.
#  Inputs : models/random_forest_htru2.pkl
#           models/htru2_features.pkl
#           reports/radio_htru2_compatible.csv
#           reports/radio_distribution_check.csv
#  Outputs: reports/radio_predictions.csv
# ============================================================

import sys
import io
import csv
from pathlib import Path

import joblib
import pandas as pd

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT          = Path(__file__).resolve().parent.parent
MODELS_DIR         = REPO_ROOT / "models"
REPORTS_DIR        = REPO_ROOT / "reports"

MODEL_FILE         = MODELS_DIR / "random_forest_htru2.pkl"
FEATURES_FILE      = MODELS_DIR / "htru2_features.pkl"
COMPAT_CSV         = REPORTS_DIR / "radio_htru2_compatible.csv"
DIST_CHECK_CSV     = REPORTS_DIR / "radio_distribution_check.csv"
MASTER_CSV         = REPORTS_DIR / "radio_master_features.csv"
PREDICTIONS_CSV    = REPORTS_DIR / "radio_predictions.csv"

CSV_FIELDS = [
    "file_name",
    "prediction",
    "prediction_probability",
    "distribution_warning",
]


def run_safe_inference() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 23: Safe Radio Inference Pipeline")
    print("=" * 68)

    # 1. Verify and load trained model artifacts
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_FILE}")
    if not FEATURES_FILE.exists():
        raise FileNotFoundError(f"Features file not found: {FEATURES_FILE}")

    try:
        model = joblib.load(MODEL_FILE)
        print(f"[OK] Loaded trained model: {type(model).__name__} from {MODEL_FILE.name}")
    except Exception as e:
        raise RuntimeError(f"Failed to load model with joblib: {e}")

    try:
        features = joblib.load(FEATURES_FILE)
        print(f"[OK] Loaded expected HTRU2 features ({len(features)}): {features}")
    except Exception as e:
        raise RuntimeError(f"Failed to load feature list: {e}")

    # 2. Load distribution check warnings for reporting context
    dist_warnings = {}
    if DIST_CHECK_CSV.exists():
        dist_df = pd.read_csv(DIST_CHECK_CSV)
        for _, row in dist_df.iterrows():
            dist_warnings[str(row["file_name"])] = str(row["distribution_warning"])

    # 3. Read compatible radio observations
    if not COMPAT_CSV.exists():
        raise FileNotFoundError(f"Compatible radio dataset not found: {COMPAT_CSV}")

    compat_df = pd.read_csv(COMPAT_CSV)
    num_compatible = len(compat_df)
    print(f"Compatible radio observation count: {num_compatible}")

    results = []

    if num_compatible > 0:
        print(f"Executing Random Forest inference on {num_compatible} compatible observation(s)...")
        X = compat_df[features].values
        preds = model.predict(X)
        probs = model.predict_proba(X)[:, 1]

        for i, row in compat_df.iterrows():
            fn = row["file_name"]
            pred_label = "PULSAR" if preds[i] == 1 else "NON_PULSAR"
            prob_val = f"{probs[i]:.4f}"
            warn = dist_warnings.get(fn, "NONE")
            results.append({
                "file_name": fn,
                "prediction": pred_label,
                "prediction_probability": prob_val,
                "distribution_warning": warn,
            })
    else:
        print("[CRITICAL SCIENTIFIC STOP RULE ENFORCED]")
        print("  Zero (0) real radio observations possess all 8 HTRU2 features.")
        print("  Missing features: DM_Mean, DM_Std, DM_Skewness, DM_Kurtosis (absent in single-epoch folded archives).")
        print("  Profile scale shift: Profile_Mean and Profile_Std are unnormalized instrumental counts.")
        print("  Inference safely HALTED to avoid false extrapolation and unscientific data fabrication.")

        # Read master file list to populate structured halted status
        if MASTER_CSV.exists():
            master_df = pd.read_csv(MASTER_CSV)
            all_files = master_df["file_name"].tolist()
        elif dist_warnings:
            all_files = list(dist_warnings.keys())
        else:
            all_files = []

        for fn in all_files:
            warn = dist_warnings.get(fn, "HIGH_DOMAIN_SHIFT: Missing search-mode DM features")
            results.append({
                "file_name": fn,
                "prediction": "INFERENCE_HALTED",
                "prediction_probability": "NOT_AVAILABLE",
                "distribution_warning": warn,
            })

    # 4. Save results to reports/radio_predictions.csv
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PREDICTIONS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print(f"[OK] Inference report saved → {PREDICTIONS_CSV}")
    print(f"  Total records logged : {len(results)}")
    halted_cnt = sum(1 for r in results if r["prediction"] == "INFERENCE_HALTED")
    pred_cnt   = sum(1 for r in results if r["prediction"] != "INFERENCE_HALTED")
    print(f"  Predictions generated: {pred_cnt}")
    print(f"  Inferences halted    : {halted_cnt}")
    print("=" * 68)


if __name__ == "__main__":
    run_safe_inference()
